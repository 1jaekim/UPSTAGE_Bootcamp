"""통합 계약 스키마 (SPEC §0.5). FE/BE/에이전트가 오직 이 형태로만 주고받는다."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

EntityType = Literal["person", "ship", "org", "place"]
NodeColor = Literal["blue", "dark"]
RelationTone = Literal["neutral", "ally", "tense"]


class Entity(BaseModel):
    id: str
    name: str
    type: EntityType
    color: NodeColor
    importance_score: int = 1
    importance_level: Literal["major", "minor"] = "minor"


class Relationship(BaseModel):
    id: str
    source: str
    target: str
    label: str
    tone: RelationTone
    description: str
    revision_offset: int
    display_label: str | None = None
    relation_category: Literal[
        "ally",
        "family",
        "conflict",
        "crime",
        "investigation",
        "deception",
        "protection",
        "romance",
        "work",
        "mystery",
        "neutral",
    ] = "neutral"
    directionality: Literal["directed", "undirected"] = "undirected"
    relation_importance_score: int = 1
    relation_importance_level: Literal["major", "minor"] = "minor"
    first_seen_global_index: int | None = None
    first_seen_boundary: int | None = None
    is_new_at_current_position: bool = False
    detail: str | None = None
    event_name: str | None = None
    event_summary: str | None = None
    relation_role: str | None = None
    role_label: str | None = None
    role_pair_label: str | None = None
    relationship_summary: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    is_story_relation: bool = False
    last_seen_global_index: int | None = None
    related_events: list[dict[str, Any]] = Field(default_factory=list)


class EventParticipant(BaseModel):
    character_name: str
    role: Literal[
        "perpetrator",
        "victim",
        "investigator",
        "suspect",
        "accomplice",
        "witness",
        "target",
        "protector",
        "deceiver",
        "deceived",
        "helper",
        "beneficiary",
        "heir",
        "employer",
        "employee",
        "informant",
        "pursuer",
        "pursued",
        "threatened",
        "threatener",
        "concealer",
        "exposed",
    ]
    confidence: float = 0.7


class StoryEvent(BaseModel):
    event_id: str
    event_name: str
    event_summary: str
    participants: list[EventParticipant] = Field(default_factory=list)
    evidence: str = ""
    first_seen_chunk_offset: int | None = None
    last_seen_chunk_offset: int | None = None
    first_seen_global_index: int | None = None
    last_seen_global_index: int | None = None
    confidence: float = 0.7


class GraphJson(BaseModel):
    """계약 graph_json"""
    offset: int
    spoiler_safe: bool
    entities: list[Entity]
    relationships: list[Relationship]
    events: list[StoryEvent] = Field(default_factory=list)


class ReminderLine(BaseModel):
    text: str
    entity_ids: list[str]


class Reminders(BaseModel):
    """계약 reminders"""
    offset: int
    lines: list[ReminderLine]


# ── 서빙 메타 (계약 외 부수 리소스) ──────────────────────────────
class Part(BaseModel):
    id: str
    index: int
    title: str
    start_offset: int
    end_offset: int


class Chapter(BaseModel):
    id: str
    part_id: Optional[str] = None
    index: int
    title: str
    start_offset: int
    end_offset: int
    content: Optional[str] = None


class Book(BaseModel):
    id: str
    title: str
    author: str
    total_offset: int
    parts: list[Part]
    chapters: list[Chapter]


class BookSummary(BaseModel):
    id: str
    title: str
    author: str
    total_offset: int


class Progress(BaseModel):
    user_id: str
    book_id: str
    reading_offset: int
    spoiler_boundary: int
    # reading_offset(global_index)에 해당하는 문단의 원본 CFI. 새로고침 시 프론트(epub.js)가
    # 이 값으로 rendition.display(cfi)를 호출해 마지막으로 읽던 위치로 복원한다.
    cfi: str | None = None


class ProgressUpdate(BaseModel):
    # reading_offset은 epub.js 연동 전 구버전 클라이언트 호환용. cfi가 오면 그쪽을 우선한다.
    reading_offset: int = 0
    # epub.js의 rendition.on('relocated') 이벤트가 주는 원본 CFI 문자열.
    # 서버에서 book_cfi_index 기준 global_index로 변환한다 (프론트/백엔드 CFI 파싱 로직
    # 이중 구현으로 어긋나는 걸 피하기 위해, 변환은 항상 서버에서만 한다).
    cfi: str | None = None
    user_id: str = "local"
    # true면 단조증가 규칙을 무시하고 spoiler_boundary를 reading_offset으로 강제 설정한다.
    # 재독(다시 읽기) 모드: 이미 도달한 지점보다 앞으로 되돌아가 스포일러를 다시 가리고 싶을 때 사용.
    force: bool = False
