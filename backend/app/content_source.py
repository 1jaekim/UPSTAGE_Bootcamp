"""ContentSource 추상화 (SPEC §3).

계약(graph_json·reminders)의 소스를 인터페이스 뒤에 두어, 초기 FixtureSource →
이후 AgentResultSource 로 '주입만 바꿔' 교체한다. 스포일러 게이팅(strict_chunk_end)은
서버에서 수행한다 (CLAUDE.md 불변 규칙 2·6: 경계선 뒤 데이터는 클라이언트로 보내지 않는다).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from . import fixtures as fx
from .schemas import GraphJson, ReminderLine, Reminders


class ContentSource(ABC):
    """graph_json / reminders 공급자."""

    @abstractmethod
    def get_graph(
        self,
        book_id: str,
        boundary_global_index: int,
        reveal_all: bool,
    ) -> GraphJson: ...

    @abstractmethod
    def get_reminders(
        self,
        book_id: str,
        boundary_global_index: int,
        entity_id: str | None,
    ) -> Reminders: ...


class FixtureSource(ContentSource):
    """정적 시드 픽스처 소스 (초기). 경계선 기준 strict_chunk_end 게이팅."""

    def _fixture_graphs(self) -> list[GraphJson]:
        return [fx.GRAPH_C1, fx.GRAPH_C2, fx.GRAPH_C3]

    def _fixture_reminders(self) -> list[tuple[int, list[ReminderLine]]]:
        return [
            (fx.GRAPH_C1.offset, fx.REMINDERS_C1),
            (fx.GRAPH_C2.offset, fx.REMINDERS_C2),
            (fx.GRAPH_C3.offset, fx.REMINDERS_C3),
        ]

    def get_graph(
        self,
        book_id: str,
        boundary_global_index: int,
        reveal_all: bool,
    ) -> GraphJson:
        if reveal_all:
            graph = max(self._fixture_graphs(), key=lambda g: g.offset)
            return graph.model_copy(update={"offset": boundary_global_index})

        visible_graphs = [
            graph
            for graph in self._fixture_graphs()
            if graph.offset <= boundary_global_index
        ]
        graph = max(visible_graphs, key=lambda g: g.offset) if visible_graphs else fx.GRAPH_EMPTY
        # 계약 offset 은 요청 경계선을 반영
        return graph.model_copy(update={"offset": boundary_global_index})

    def get_reminders(
        self,
        book_id: str,
        boundary_global_index: int,
        entity_id: str | None,
    ) -> Reminders:
        visible_reminders = [
            (boundary, lines)
            for boundary, lines in self._fixture_reminders()
            if boundary <= boundary_global_index
        ]
        lines = max(visible_reminders, key=lambda item: item[0])[1] if visible_reminders else []
        if entity_id:
            lines = [ln for ln in lines if entity_id in ln.entity_ids]
        return Reminders(offset=boundary_global_index, lines=list(lines))


class AgentResultSource(ContentSource):
    """에이전트 precompute 결과 조회 소스 (B2에서 연동).

    외부 에이전트 담당자가 (book, boundary)별로 미리 계산해 둔 계약 JSON을 저장소에서
    읽어 반환한다. 계약이 동일하므로 라우트/스키마 변경 없이 주입만 교체하면 된다.
    """

    def __init__(self, store: dict | None = None):
        # store[(book_id, boundary)] = {"graph": GraphJson, "reminders": list[ReminderLine]}
        self._store = store or {}

    @classmethod
    def from_supabase(cls) -> "AgentResultSource":
        """Supabase build_agent_snapshots 테이블에서 전체 책의 스냅샷을 로드한다.

        로컬 JSON 파일과 달리 여러 책이 한 테이블에 같이 있으므로, book_id 필터 없이
        전부 읽어서 (book_id, boundary) 복합키 store 하나로 합친다.
        """
        import psycopg2
        import psycopg2.extras

        from .config import SUPABASE_DB_URL

        store: dict = {}
        if not SUPABASE_DB_URL:
            return cls(store)

        conn = psycopg2.connect(SUPABASE_DB_URL, connect_timeout=10)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT book_id, boundary, graph, reminders FROM build_agent_snapshots")
                rows = cur.fetchall()
        finally:
            conn.close()

        for row in rows:
            store[(str(row["book_id"]), int(row["boundary"]))] = {
                "graph": GraphJson.model_validate(row["graph"]),
                "reminders": [ReminderLine.model_validate(l) for l in row["reminders"]],
            }
        return cls(store)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "AgentResultSource":
        """precompute 가 만든 계약 JSON 파일에서 store 를 로드한다.

        파일 형식: {"book_id": str, "entries": [{"boundary": int, "graph": {...},
        "reminders": [{...}]}]}. schemas 로 검증하며 읽으므로 계약 위반 시 즉시 실패.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        book_id = data["book_id"]
        store: dict = {}
        for entry in data.get("entries", []):
            boundary = int(entry["boundary"])
            store[(book_id, boundary)] = {
                "graph": GraphJson.model_validate(entry["graph"]),
                "reminders": [ReminderLine.model_validate(l) for l in entry.get("reminders", [])],
            }
        return cls(store)

    def _lookup(self, book_id: str, boundary_global_index: int):
        # 경계선 이하 중 가장 큰 precompute 지점을 사용 (없으면 빈 결과)
        keys = sorted(
            boundary
            for (bk, boundary) in self._store
            if bk == book_id and boundary <= boundary_global_index
        )
        return self._store.get((book_id, keys[-1])) if keys else None

    def _max_snapshot_boundary_global_index(self, book_id: str) -> int | None:
        boundaries = [boundary for (bk, boundary) in self._store if bk == book_id]
        return max(boundaries) if boundaries else None

    def _book_last_global_index(self, book_id: str) -> int:
        from . import cfi_db

        try:
            total = cfi_db.total_paragraphs(book_id)
        except Exception:
            return 0
        return max(0, total - 1)

    def _reveal_all_boundary_global_index(self, book_id: str) -> int:
        snapshot_boundary_global_index = self._max_snapshot_boundary_global_index(book_id)
        if snapshot_boundary_global_index is not None:
            return snapshot_boundary_global_index
        return self._book_last_global_index(book_id)

    def get_graph(
        self,
        book_id: str,
        boundary_global_index: int,
        reveal_all: bool,
    ) -> GraphJson:
        spoiler_boundary_global_index = (
            self._reveal_all_boundary_global_index(book_id)
            if reveal_all
            else boundary_global_index
        )
        entry = self._lookup(book_id, spoiler_boundary_global_index)
        if not entry:
            return fx.GRAPH_EMPTY.model_copy(update={"offset": boundary_global_index})
        graph: GraphJson = entry["graph"]
        return graph.model_copy(update={"offset": boundary_global_index})

    def get_reminders(
        self,
        book_id: str,
        boundary_global_index: int,
        entity_id: str | None,
    ) -> Reminders:
        entry = self._lookup(book_id, boundary_global_index)
        lines: list[ReminderLine] = entry["reminders"] if entry else []
        if entity_id:
            lines = [ln for ln in lines if entity_id in ln.entity_ids]
        return Reminders(offset=boundary_global_index, lines=list(lines))
