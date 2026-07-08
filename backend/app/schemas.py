"""통합 계약 스키마 (SPEC §0.5). FE/BE/에이전트가 오직 이 형태로만 주고받는다."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

EntityType = Literal["person", "ship", "org", "place"]
NodeColor = Literal["blue", "dark"]
RelationTone = Literal["neutral", "ally", "tense"]


class Entity(BaseModel):
    id: str
    name: str
    type: EntityType
    color: NodeColor


class Relationship(BaseModel):
    id: str
    source: str
    target: str
    label: str
    tone: RelationTone
    description: str
    revision_offset: int


class GraphJson(BaseModel):
    """계약 graph_json"""
    offset: int
    spoiler_safe: bool
    entities: list[Entity]
    relationships: list[Relationship]


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


class ProgressUpdate(BaseModel):
    reading_offset: int
    user_id: str = "local"
    # true면 단조증가 규칙을 무시하고 spoiler_boundary를 reading_offset으로 강제 설정한다.
    # 재독(다시 읽기) 모드: 이미 도달한 지점보다 앞으로 되돌아가 스포일러를 다시 가리고 싶을 때 사용.
    force: bool = False
