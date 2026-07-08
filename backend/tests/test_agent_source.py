"""에이전트 어댑터 + AgentResultSource 계약 테스트.

BuildAgent 형태(이름 기반)를 계약(id 기반)으로 변환하고, precompute→로드→서빙이
FixtureSource 와 동일한 게이팅 시맨틱을 유지하는지 검증한다.
"""
from __future__ import annotations

from backend.app import agent_adapter as ad
from backend.app.content_source import AgentResultSource
from backend.app.precompute import build_entries, write_store
from backend.scripts.make_demo_store import BOOK_ID, DEMO_BUILD_RESULTS


def test_adapter_maps_names_to_ids():
    result = DEMO_BUILD_RESULTS[0][1]
    graph = ad.to_graph_json(result, boundary=215)
    # 인물 3 + 관계 2
    assert len(graph.entities) == 3
    assert len(graph.relationships) == 2
    # source/target 은 entity id (이름이 아님)
    ids = {e.id for e in graph.entities}
    for rel in graph.relationships:
        assert rel.source in ids and rel.target in ids
    # 아틀라스 호는 optional type=ship 존중
    atlas = next(e for e in graph.entities if e.name == "아틀라스 호")
    assert atlas.type == "ship"


def test_adapter_id_is_stable():
    assert ad.entity_id("민우") == ad.entity_id(" 민우 ")


def test_reminders_from_events():
    lines = ad.to_reminder_lines(DEMO_BUILD_RESULTS[0][1])
    assert len(lines) == 2
    assert all(l.entity_ids for l in lines)


def test_revision_offset_is_first_seen():
    entries = build_entries(DEMO_BUILD_RESULTS)
    # 강 국장 관계(r3)는 320 에서 처음 등장 → 380 에서도 revision_offset=320 유지
    by_boundary = {e["boundary"]: e for e in entries}
    g380 = by_boundary[380]["graph"]
    kang_id = ad.entity_id("강 국장")
    seohyun_id = ad.entity_id("서현")
    rel = next(r for r in g380["relationships"]
               if {r["source"], r["target"]} == {seohyun_id, kang_id})
    assert rel["revision_offset"] == 320


def test_agent_source_gating(tmp_path):
    entries = build_entries(DEMO_BUILD_RESULTS)
    write_store(BOOK_ID, entries, store_dir=tmp_path)
    src = AgentResultSource.from_json_file(tmp_path / f"{BOOK_ID}.json")

    # 215 미만: precompute 지점 없음 → 빈 그래프
    assert src.get_graph(BOOK_ID, 200, reveal_all=False).entities == []
    # 215: 인물 3
    assert len(src.get_graph(BOOK_ID, 215, reveal_all=False).entities) == 3
    # 379 (c3 경계 380 직전): 윤 팀장 미공개 → 여전히 320 스냅샷(인물 4)
    g379 = src.get_graph(BOOK_ID, 379, reveal_all=False)
    assert ad.entity_id("윤 팀장") not in {e.id for e in g379.entities}
    # 380: 인물 5
    assert len(src.get_graph(BOOK_ID, 380, reveal_all=False).entities) == 5
