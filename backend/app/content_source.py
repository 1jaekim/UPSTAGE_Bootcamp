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

# 청크 경계 (strict_chunk_end): 해당 청크를 '끝까지' 읽어야 fact 공개
CHUNK_C1_END = 215
CHUNK_C2_END = 320
CHUNK_C3_END = 380
CHUNK_C4_END = 430


class ContentSource(ABC):
    """graph_json / reminders 공급자."""

    @abstractmethod
    def get_graph(self, book_id: str, boundary: int, reveal_all: bool) -> GraphJson: ...

    @abstractmethod
    def get_reminders(self, book_id: str, boundary: int, entity_id: str | None) -> Reminders: ...


class FixtureSource(ContentSource):
    """정적 시드 픽스처 소스 (초기). 경계선 기준 strict_chunk_end 게이팅."""

    def get_graph(self, book_id: str, boundary: int, reveal_all: bool) -> GraphJson:
        if reveal_all:
            # 안심 모드 OFF: 데모에선 c4가 없으므로 c3(전체)와 동일.
            graph = fx.GRAPH_C3
        elif boundary >= CHUNK_C3_END:
            graph = fx.GRAPH_C3
        elif boundary >= CHUNK_C2_END:
            graph = fx.GRAPH_C2
        elif boundary >= CHUNK_C1_END:
            graph = fx.GRAPH_C1
        else:
            graph = fx.GRAPH_EMPTY
        # 계약 offset 은 요청 경계선을 반영
        return graph.model_copy(update={"offset": boundary})

    def get_reminders(self, book_id: str, boundary: int, entity_id: str | None) -> Reminders:
        if boundary >= CHUNK_C3_END:
            lines = fx.REMINDERS_C3
        elif boundary >= CHUNK_C2_END:
            lines = fx.REMINDERS_C2
        elif boundary >= CHUNK_C1_END:
            lines = fx.REMINDERS_C1
        else:
            lines = []
        if entity_id:
            lines = [ln for ln in lines if entity_id in ln.entity_ids]
        return Reminders(offset=boundary, lines=list(lines))


class AgentResultSource(ContentSource):
    """에이전트 precompute 결과 조회 소스 (B2에서 연동).

    외부 에이전트 담당자가 (book, boundary)별로 미리 계산해 둔 계약 JSON을 저장소에서
    읽어 반환한다. 계약이 동일하므로 라우트/스키마 변경 없이 주입만 교체하면 된다.
    """

    def __init__(self, store: dict | None = None):
        # store[(book_id, boundary)] = {"graph": GraphJson, "reminders": list[ReminderLine]}
        self._store = store or {}

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

    def _lookup(self, book_id: str, boundary: int):
        # 경계선 이하 중 가장 큰 precompute 지점을 사용 (없으면 빈 결과)
        keys = sorted(b for (bk, b) in self._store if bk == book_id and b <= boundary)
        return self._store.get((book_id, keys[-1])) if keys else None

    def get_graph(self, book_id: str, boundary: int, reveal_all: bool) -> GraphJson:
        entry = self._lookup(book_id, CHUNK_C4_END if reveal_all else boundary)
        if not entry:
            return fx.GRAPH_EMPTY.model_copy(update={"offset": boundary})
        graph: GraphJson = entry["graph"]
        return graph.model_copy(update={"offset": boundary})

    def get_reminders(self, book_id: str, boundary: int, entity_id: str | None) -> Reminders:
        entry = self._lookup(book_id, boundary)
        lines: list[ReminderLine] = entry["reminders"] if entry else []
        if entity_id:
            lines = [ln for ln in lines if entity_id in ln.entity_ids]
        return Reminders(offset=boundary, lines=list(lines))
