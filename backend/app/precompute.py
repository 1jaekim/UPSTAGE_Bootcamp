"""에이전트 결과 → 계약 JSON precompute 파이프라인.

'다음 에이전트' 담당자의 진입점:
- (A) 이미 계산된 build 결과 시퀀스가 있으면 `build_entries()` 로 계약 JSON 생성.
- (B) EPUB 원본에서 바로 돌리려면 `precompute_from_epub()` (UPSTAGE_API_KEY 필요).

산출물은 `AgentResultSource.from_json_file()` 이 읽는 형식이며, 이를 로드해
`main.py` 의 `content_source` 로 주입하면 라우트/스키마 변경 없이 실데이터 서빙이 된다.

핵심: 각 관계의 `revision_offset` 은 그 관계가 '처음 등장한 경계선' 으로 고정된다
(누적 그래프에서 이후 경계선에도 계속 보이지만 최초 등장 시점을 유지).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import agent_adapter as ad

# precompute 결과 저장 위치
STORE_DIR = Path(__file__).resolve().parent.parent / "data" / "precomputed"


def build_entries(boundary_results: list[tuple[int, dict]]) -> list[dict]:
    """(boundary, accumulated_build_result) 시퀀스 → 계약 entries.

    boundary_results 는 경계선 오름차순. build_result 는 해당 경계선까지 '누적된'
    characters/relations/events (incremental_build_agent 반환 형태).

    각 경계선마다 VerifierAgent → ReminderWriterAgent → IndirectLeakageJudge 순으로
    체이닝한다 (BuildAgent는 이미 incremental_build_agent 단계에서 끝난 상태로 들어옴).
    """
    from agents.indirect_leakage_judge import judge_reminders
    from agents.reminder_writer_agent import write_reminders
    from agents.verifier_agent import verify_build_result

    ordered = sorted(boundary_results, key=lambda x: x[0])
    first_seen: dict[str, int] = {}
    entries: list[dict] = []

    for boundary, result in ordered:
        # 1차 가드: 근거 없는 relations/events 제거
        verified = verify_build_result(result)

        # 이 경계선에서 처음 보이는 관계의 revision_offset 을 boundary 로 고정
        for rid in ad.build_relation_ids(verified):
            first_seen.setdefault(rid, boundary)

        graph = ad.to_graph_json(verified, boundary, revision_offsets=first_seen)

        # 2차 가드: 서술형으로 재작성 → 3차 가드: 암시/복선 판정 후 최종 확정
        written = write_reminders(verified)
        entity_name_to_id = {e.name: e.id for e in graph.entities}
        judged_lines = judge_reminders(written.get("lines", []))
        reminders = [
            {
                "text": line.get("text", ""),
                "entity_ids": [
                    entity_name_to_id[n]
                    for n in line.get("entity_names", [])
                    if n in entity_name_to_id
                ],
            }
            for line in judged_lines
            if line.get("text")
        ]

        entries.append(
            {
                "boundary": boundary,
                "graph": graph.model_dump(),
                "reminders": reminders,
            }
        )
    return entries


def remap_boundaries_to_global_index(
    book_id: str, epub_path: str | Path, entries: list[dict]
) -> list[dict]:
    """entries의 boundary(청크 순번)를 CFI global_index로 재매핑한다.

    BuildAgent의 chunk_tool은 epub_parser 기준 문자 단위로 청크를 만드는데, 실제
    스포일러 게이팅은 book_cfi_index 기준 global_index로 이뤄지므로 두 단위를 반드시
    맞춰줘야 한다 (안 맞으면 책의 일부만 읽었는데 전체 스포일러가 노출되는 버그가 남).
    """
    from . import cfi_db
    from .config import PARSER_CHAPTER_OFFSET
    from agents.parsers.epub_parser import parse_epub
    from agents.tools.chunk_tool import make_chunks

    parsed = parse_epub(epub_path)
    chapters = parsed["chapters"]
    chunks = make_chunks(chapters)
    chunk_by_offset = {c["offset"]: c for c in chunks}
    chapter_charcount = {c["chapter_index"]: c["char_count"] for c in chapters}

    cfi_db.clear_cache()
    paragraphs = cfi_db.get_paragraphs(book_id)
    by_cfi_chapter: dict[int, list] = {}
    for p in paragraphs:
        by_cfi_chapter.setdefault(p.chapter_index, []).append(p)
    cfi_chapter_range = {
        idx: (ps[0].global_index, ps[-1].global_index) for idx, ps in by_cfi_chapter.items()
    }

    # 1챕터 제목으로 이 책의 실제 파서 오프셋을 자동 계산 (책마다 표지·목차 개수가 다름)
    ch1_title = next(
        (ps[0].chapter_title for idx, ps in sorted(by_cfi_chapter.items()) if idx == 1), None
    )
    import re

    def normalize(t: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", t.lower())

    computed_offset = PARSER_CHAPTER_OFFSET
    if ch1_title:
        target = normalize(ch1_title)
        for c in chapters:
            if target and target in normalize(c["title"]):
                computed_offset = c["chapter_index"] - 1
                break

    def remap(old_boundary: int) -> int:
        chunk = chunk_by_offset.get(old_boundary)
        if chunk is None:
            return old_boundary
        cfi_chapter_index = max(0, chunk["chapter_index"] - computed_offset)
        if cfi_chapter_index not in cfi_chapter_range:
            cfi_chapter_index = max(cfi_chapter_range.keys())
        start, end = cfi_chapter_range[cfi_chapter_index]
        total_chars = chapter_charcount.get(chunk["chapter_index"], 1) or 1
        frac = min(1.0, chunk["end_char"] / total_chars)
        return round(start + frac * (end - start))

    remapped = []
    for entry in entries:
        new_boundary = remap(entry["boundary"])
        entry = {**entry, "boundary": new_boundary}
        entry["graph"] = {**entry["graph"], "offset": new_boundary}
        remapped.append(entry)
    remapped.sort(key=lambda e: e["boundary"])
    return remapped


def upload_snapshots_to_supabase(book_id: str, entries: list[dict]) -> int:
    """entries를 Supabase build_agent_snapshots 테이블에 적재. 적재 행 수 반환."""
    import json as _json

    import psycopg2
    import psycopg2.extras

    from .config import SUPABASE_DB_URL

    if not SUPABASE_DB_URL or not entries:
        return 0

    conn = psycopg2.connect(SUPABASE_DB_URL, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            rows = [
                (
                    book_id,
                    e["boundary"],
                    _json.dumps(e["graph"], ensure_ascii=False),
                    _json.dumps(e["reminders"], ensure_ascii=False),
                )
                for e in entries
            ]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO build_agent_snapshots (book_id, boundary, graph, reminders)
                VALUES %s
                ON CONFLICT (book_id, boundary)
                DO UPDATE SET graph = EXCLUDED.graph, reminders = EXCLUDED.reminders
                """,
                rows,
                template="(%s, %s, %s::jsonb, %s::jsonb)",
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def write_store(book_id: str, entries: list[dict], store_dir: Path = STORE_DIR) -> Path:
    """계약 JSON 을 `<store_dir>/<book_id>.json` 으로 저장하고 경로를 반환."""
    store_dir.mkdir(parents=True, exist_ok=True)
    path = store_dir / f"{book_id}.json"
    payload = {"book_id": book_id, "entries": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def store_path(book_id: str, store_dir: Path = STORE_DIR) -> Path:
    return store_dir / f"{book_id}.json"


def precompute_from_epub(
    epub_path: str | Path,
    book_id: str,
    boundaries: list[int],
    store_dir: Path = STORE_DIR,
    upload_to_supabase: bool = True,
) -> Path:
    """EPUB → chunk → 경계선별 incremental build → 계약 JSON 저장 + Supabase 적재.

    UPSTAGE_API_KEY 가 필요하다 (실제 LLM 호출). boundaries 는 청크 offset(정수) 리스트.
    agents 패키지는 지연 import — 어댑터/서빙 경로가 langchain 에 의존하지 않게 하기 위함.
    """
    from agents.build_agent import incremental_build_agent  # 지연 import
    from agents.parsers.epub_parser import parse_epub
    from agents.tools.chunk_tool import make_chunks

    parsed = parse_epub(epub_path)
    chunks = make_chunks(parsed["chapters"])

    boundary_results: list[tuple[int, dict]] = []
    previous: dict = {"characters": [], "relations": [], "events": []}
    last_built = -1
    for boundary in sorted(boundaries):
        result = incremental_build_agent(
            chunks=chunks,
            current_offset=boundary,
            last_built_offset=last_built,
            previous_results=previous,
        )
        previous = result
        last_built = boundary
        boundary_results.append((boundary, result))

    entries = build_entries(boundary_results)
    entries = remap_boundaries_to_global_index(book_id, epub_path, entries)

    path = write_store(book_id, entries, store_dir)
    if upload_to_supabase:
        upload_snapshots_to_supabase(book_id, entries)
    return path


if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="SpoKeeper precompute (EPUB → 계약 JSON)")
    p.add_argument("epub", help="EPUB 경로")
    p.add_argument("book_id", help="책 id (예: b_mist)")
    p.add_argument("boundaries", help="쉼표구분 경계선 offset (예: 5,10,20)")
    args = p.parse_args()
    out = precompute_from_epub(
        args.epub, args.book_id, [int(x) for x in args.boundaries.split(",") if x.strip()]
    )
    print(f"wrote {out}")
