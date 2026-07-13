"""Supabase(Postgres)의 book_cfi_index 조회 계층.

CFI 통합의 핵심 아이디어: 지금까지 시스템 곳곳에 흩어져 있던 "offset"의 정의를
하나로 통일한다 — 여기서 offset 이란 `book_cfi_index`를 cfi_path 기준으로 정렬했을 때
해당 문단의 0부터 시작하는 순번(global_index)이다. BuildAgent의 chunk 순번, 스포일러
경계선, 프론트 페이지네이션이 전부 이 정수를 그대로 공유한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import psycopg2
import psycopg2.extras

from .cfi_utils import cfi_to_path
from .config import SUPABASE_DB_URL


@dataclass(frozen=True)
class CfiParagraph:
    global_index: int
    chapter_index: int
    chapter_title: str
    paragraph_index: int
    cfi_raw: str
    cfi_path: list[int]
    text_preview: str


def _connect():
    if not SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL 환경변수가 설정되어 있지 않습니다.")
    return psycopg2.connect(SUPABASE_DB_URL, connect_timeout=10)


# maxsize=8이었을 때는 등록된 책이 8권을 넘으면 /api/books가 전체 책을 순회할 때마다
# LRU 캐시가 계속 밀려나서(스래싱) 캐시가 사실상 안 먹혀 매 요청마다 Supabase에 새
# 연결을 맺느라 몇 초씩 걸렸다 — 책 수가 작고 자연히 유계라 무제한으로 둔다.
@lru_cache(maxsize=None)
def get_paragraphs(book_id: str) -> tuple[CfiParagraph, ...]:
    """book_id의 전체 문단을 cfi_path 순서(=global_index)로 반환. 결과는 캐시됨."""
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT chapter_index, chapter_title, paragraph_index, cfi_raw, cfi_path, text_preview
                FROM book_cfi_index
                WHERE book_id = %s
                ORDER BY cfi_path
                """,
                (book_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return tuple(
        CfiParagraph(
            global_index=i,
            chapter_index=row["chapter_index"],
            chapter_title=row["chapter_title"] or f"Chapter {row['chapter_index']}",
            paragraph_index=row["paragraph_index"],
            cfi_raw=row["cfi_raw"],
            cfi_path=list(row["cfi_path"]),
            text_preview=row["text_preview"],
        )
        for i, row in enumerate(rows)
    )


def cfi_for_global_index(book_id: str, global_index: int) -> str | None:
    """global_index -> 원본 CFI 문자열 (역방향 조회, 새로고침 시 위치 복원용)."""
    paragraphs = get_paragraphs(book_id)
    if not paragraphs:
        return None
    clamped = max(0, min(global_index, len(paragraphs) - 1))
    return paragraphs[clamped].cfi_raw


def _normalize_live_cfi_path(path: list[int]) -> list[int]:
    """epub.js가 실시간으로 주는 CFI와 book_cfi_index에 저장된 CFI는 트리 깊이가
    다르다 — book_cfi_index는 `epub-cfi-resolver`(Node) 라이브러리로 오프라인
    생성했는데, 이 라이브러리는 `<html>`이 `#document`의 몇 번째 자식인지까지
    스텝으로 넣는다(항상 첫 문서 자식이라 값은 늘 2로 고정). 반면 epub.js 자신의
    `EpubCFI.pathTo()`(epubjs/src/epubcfi.js)는 `currentNode.parentNode`가
    `#document`가 되는 순간(=currentNode가 `<html>`) 루프를 멈추고 `<html>`용
    스텝을 아예 안 만든다 — 그래서 epub.js가 준 실시간 CFI는 저장된 CFI보다
    스텝이 정확히 하나(spine indirection 뒤, 첫 스텝) 적다.

    이 어긋남을 그냥 두면 이진탐색이 실시간 CFI를 해당 챕터의 "모든 문단보다
    뒤"로 취급해버려서(스텝 하나가 부족한 만큼 첫 비교 자리에서 항상 더 크게
    비교됨), 챕터 안 어느 위치를 읽어도 그 챕터/책의 맨 끝 문단으로 잘못
    매칭된다 — 실제로 심청전 하권에서 이 버그로 재현 확인함 (스포일러 경계선이
    책 끝까지 튀어서 다시 안 내려오는 사고로 이어짐, spoiler_boundary는
    단조증가라 한 번 튀면 계속 최댓값에 고정됨).

    spine indirection(`/6/{spine_pos}`)은 정확히 앞 두 정수(스텝+오프셋)이므로,
    그 바로 뒤에 book_cfi_index 쪽 관례와 맞춰 `<html>` 스텝(2, 0)을 끼워 넣는다.
    """
    if len(path) < 4:
        return path
    return path[:4] + [2, 0] + path[4:]


def find_global_index_by_cfi(book_id: str, raw_cfi: str) -> int:
    """epub.js가 준 원본 CFI 문자열을 이 책의 global_index로 변환한다.

    정확히 일치하는 문단이 없으면(문단 사이의 임의 위치를 가리키는 CFI일 수 있음)
    그 위치보다 앞선 문단 중 가장 마지막 것의 global_index를 반환한다(cfi_path 배열의
    사전식 비교가 곧 문서 순서와 같다는 성질 이용, book_cfi_index README에서 검증됨).
    """
    target = _normalize_live_cfi_path(cfi_to_path(raw_cfi))
    paragraphs = get_paragraphs(book_id)
    if not paragraphs:
        return 0

    lo, hi = 0, len(paragraphs) - 1
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if paragraphs[mid].cfi_path <= target:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return paragraphs[best].global_index


def total_paragraphs(book_id: str) -> int:
    return len(get_paragraphs(book_id))


def paragraphs_up_to(book_id: str, boundary: int) -> tuple[CfiParagraph, ...]:
    """global_index <= boundary 인 문단만 반환 (스포일러 경계선 게이팅)."""
    return tuple(p for p in get_paragraphs(book_id) if p.global_index <= boundary)


def clear_cache() -> None:
    get_paragraphs.cache_clear()


# ── 쓰기 경로 (업로드 파이프라인용) ──────────────────────────────────────

def find_book_by_hash(content_hash: str) -> str | None:
    """같은 content_hash의 책이 이미 있으면 book_id를, 없으면 None을 반환."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT book_id FROM books WHERE content_hash = %s", (content_hash,))
            row = cur.fetchone()
            return str(row[0]) if row else None
    finally:
        conn.close()


def set_storage_path(book_id: str, storage_path: str) -> None:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE books SET storage_path=%s WHERE book_id=%s", (storage_path, book_id))
        conn.commit()
    finally:
        conn.close()


def list_books() -> list[dict]:
    """status='ready'인 책 목록을 (book_id, title, storage_path)로 반환."""
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT book_id, title, storage_path FROM books WHERE status='ready'")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def has_paragraphs(book_id: str) -> bool:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM book_cfi_index WHERE book_id = %s", (book_id,))
            return cur.fetchone()[0] > 0
    finally:
        conn.close()


def insert_book(content_hash: str, title: str, storage_path: str) -> str:
    """books row 생성(이미 있으면 기존 row 재사용). book_id 반환."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO books (content_hash, title, storage_path, status)
                VALUES (%s, %s, %s, 'processing')
                ON CONFLICT (content_hash) DO UPDATE SET title = EXCLUDED.title
                RETURNING book_id
                """,
                (content_hash, title, storage_path),
            )
            book_id = str(cur.fetchone()[0])
        conn.commit()
        return book_id
    finally:
        conn.close()


def insert_paragraphs(book_id: str, rows: list[dict]) -> int:
    """CFI 생성 스크립트 결과(rows)를 book_cfi_index에 적재. 적재된 행 수 반환."""
    if not rows:
        return 0
    conn = _connect()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO book_cfi_index
                    (book_id, chapter_index, chapter_title, paragraph_index, cfi_raw, cfi_path, text_preview)
                VALUES %s
                """,
                [
                    (
                        book_id,
                        r["chapter_index"],
                        r["chapter_title"],
                        r["paragraph_index"],
                        r["cfi_raw"],
                        r["cfi_path"],
                        r["text_preview"],
                    )
                    for r in rows
                ],
            )
            cur.execute("UPDATE books SET status='ready' WHERE book_id=%s", (book_id,))
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def delete_book(book_id: str) -> bool:
    """books row를 삭제한다. book_cfi_index/build_agent_snapshots/user_reading_position은
    전부 book_id에 ON DELETE CASCADE가 걸려있어 자동으로 같이 삭제된다.
    실제로 삭제된 행이 있었으면 True, 애초에 없던 book_id면 False.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            except psycopg2.errors.InvalidTextRepresentation:
                # book_id가 UUID 형식이 아니면(존재할 수 없는 id) 그냥 "없음"으로 취급.
                conn.rollback()
                return False
            deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()
