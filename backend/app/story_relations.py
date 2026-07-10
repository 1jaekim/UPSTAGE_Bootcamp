from __future__ import annotations

import hashlib
from itertools import combinations

from .schemas import GraphJson, Relationship, ReminderLine


STORY_CATEGORIES = {
    "crime": (
        "살인",
        "살해",
        "죽",
        "사망",
        "시체",
        "범인",
        "피해자",
        "죄",
        "독살",
        "공격",
    ),
    "investigation": (
        "조사",
        "수사",
        "추적",
        "의심",
        "용의",
        "단서",
        "밝히",
        "찾",
        "탐문",
    ),
    "deception": (
        "속",
        "기만",
        "위장",
        "거짓",
        "은폐",
        "숨김",
        "비밀",
        "협박",
        "함정",
    ),
    "protection": (
        "보호",
        "돕",
        "도움",
        "동행",
        "구출",
        "지키",
        "경호",
    ),
    "work": (
        "의뢰",
        "고용",
        "부탁",
        "임무",
    ),
    "family": (
        "가족",
        "부인",
        "남편",
        "아내",
        "후계자",
        "상속",
        "가문",
        "형제",
        "남매",
        "부부",
    ),
    "ally": (
        "친구",
        "동료",
        "협력",
        "조력",
        "신뢰",
    ),
    "romance": (
        "사랑",
        "연인",
        "약혼",
        "질투",
        "결혼",
    ),
    "mystery": (
        "정체",
        "미스터리",
        "수수께끼",
        "의문",
    ),
}

STORY_PRIORITY = (
    "crime",
    "investigation",
    "deception",
    "protection",
    "work",
    "family",
    "romance",
    "ally",
    "mystery",
)

STORY_LABELS = {
    "crime": "사건",
    "investigation": "조사",
    "deception": "속임",
    "protection": "보호",
    "work": "의뢰",
    "family": "가족",
    "ally": "협력",
    "romance": "관계",
    "mystery": "단서",
}

STORY_ROLES = {
    "crime": "사건 관련",
    "investigation": "조사/추적",
    "deception": "속임/은폐",
    "protection": "보호/도움",
    "work": "의뢰/업무",
    "family": "가족/상속",
    "ally": "협력",
    "romance": "애정 관계",
    "mystery": "미스터리 단서",
}

INVESTIGATOR_HINTS = (
    "홈즈",
    "왓슨",
    "그레그슨",
    "레스트레이드",
    "경찰",
    "수사관",
    "탐정",
)

CORE_STORY_CATEGORIES = {"crime", "investigation", "deception", "protection"}


def _story_id(source: str, target: str, category: str, event_summary: str) -> str:
    raw = f"{source}|{target}|{category}|{event_summary}".encode("utf-8")
    return f"sr_{hashlib.md5(raw).hexdigest()[:10]}"


def _structured_story_id(source: str, target: str, category: str, event_id: str, role: str) -> str:
    raw = f"{source}|{target}|{category}|{event_id}|{role}".encode("utf-8")
    return f"sr_{hashlib.md5(raw).hexdigest()[:10]}"


def _category_for_text(text: str) -> str | None:
    counts = {
        category: sum(1 for hint in hints if hint in text)
        for category, hints in STORY_CATEGORIES.items()
    }
    if not any(counts.values()):
        return None
    return max(STORY_PRIORITY, key=lambda category: (counts.get(category, 0), -STORY_PRIORITY.index(category)))


def _is_directed(category: str) -> bool:
    return category in {"crime", "investigation", "deception", "protection", "work"}


def _event_payload(summary: str, category: str, boundary_global_index: int, confidence: float) -> dict:
    return {
        "event_name": summary[:40],
        "event_summary": summary,
        "relation_category": category,
        "first_seen_global_index": boundary_global_index,
        "last_seen_global_index": boundary_global_index,
        "confidence": confidence,
    }


def _structured_event_payload(event, category: str, relation_role: str, confidence: float) -> dict:
    first_seen = event.first_seen_global_index or event.first_seen_chunk_offset or 0
    last_seen = event.last_seen_global_index or event.last_seen_chunk_offset or first_seen
    return {
        "event_id": event.event_id,
        "event_name": event.event_name,
        "event_summary": event.event_summary,
        "relation_category": category,
        "relation_role": relation_role,
        "first_seen_global_index": first_seen,
        "last_seen_global_index": last_seen,
        "confidence": confidence,
        "evidence": event.evidence,
    }


def _ordered_pair(source: str, target: str, category: str, names_by_id: dict[str, str]) -> tuple[str, str]:
    if category in {"family", "ally", "romance", "mystery"}:
        return source, target

    source_name = names_by_id.get(source, "")
    target_name = names_by_id.get(target, "")
    source_is_investigator = any(hint in source_name for hint in INVESTIGATOR_HINTS)
    target_is_investigator = any(hint in target_name for hint in INVESTIGATOR_HINTS)
    if category == "investigation":
        if target_is_investigator and not source_is_investigator:
            return target, source
        return source, target
    if category in {"protection", "work"}:
        if target_is_investigator and not source_is_investigator:
            return target, source
    return source, target


def _make_story_relationship(
    source: str,
    target: str,
    *,
    category: str,
    event_summary: str,
    boundary_global_index: int,
    names_by_id: dict[str, str],
    confidence: float,
) -> Relationship:
    source, target = _ordered_pair(source, target, category, names_by_id)
    label = STORY_LABELS.get(category, "사건")
    related_event = _event_payload(event_summary, category, boundary_global_index, confidence)
    return Relationship(
        id=_story_id(source, target, category, event_summary),
        source=source,
        target=target,
        label=label,
        tone="tense" if category in {"crime", "deception"} else "neutral",
        description=event_summary,
        revision_offset=boundary_global_index,
        display_label=label,
        relation_category=category,
        directionality="directed" if _is_directed(category) else "undirected",
        relation_importance_score=5 if category in {"crime", "investigation", "deception"} else 4,
        relation_importance_level="major",
        first_seen_global_index=boundary_global_index,
        first_seen_boundary=boundary_global_index,
        is_new_at_current_position=False,
        detail=event_summary,
        event_name=event_summary[:40],
        event_summary=event_summary,
        relation_role=STORY_ROLES.get(category, "사건 관련"),
        confidence=confidence,
        is_story_relation=True,
        last_seen_global_index=boundary_global_index,
        related_events=[related_event],
    )


def _make_structured_story_relationship(
    source: str,
    target: str,
    *,
    category: str,
    relation_role: str,
    event,
    confidence: float,
) -> Relationship:
    first_seen = event.first_seen_global_index or event.first_seen_chunk_offset or 0
    last_seen = event.last_seen_global_index or event.last_seen_chunk_offset or first_seen
    label = STORY_LABELS.get(category, "사건")
    related_event = _structured_event_payload(event, category, relation_role, confidence)
    return Relationship(
        id=_structured_story_id(source, target, category, event.event_id, relation_role),
        source=source,
        target=target,
        label=label,
        tone="tense" if category in {"crime", "deception"} else "neutral",
        description=event.event_summary,
        revision_offset=first_seen,
        display_label=label,
        relation_category=category,
        directionality="directed" if _is_directed(category) else "undirected",
        relation_importance_score=5 if category in {"crime", "investigation", "deception"} else 4,
        relation_importance_level="major",
        first_seen_global_index=first_seen,
        first_seen_boundary=first_seen,
        is_new_at_current_position=False,
        detail=event.event_summary,
        event_name=event.event_name,
        event_summary=event.event_summary,
        relation_role=relation_role,
        confidence=confidence,
        is_story_relation=True,
        last_seen_global_index=last_seen,
        related_events=[related_event],
    )


def _participants_by_role(event) -> dict[str, list]:
    by_role: dict[str, list] = {}
    for participant in event.participants:
        by_role.setdefault(participant.role, []).append(participant)
    return by_role


def _add_role_pairs(
    relationships: list[Relationship],
    seen_story_ids: set[str],
    event,
    names_to_ids: dict[str, str],
    source_roles: tuple[str, ...],
    target_roles: tuple[str, ...],
    *,
    category: str,
    relation_role: str,
) -> None:
    by_role = _participants_by_role(event)
    for source_role in source_roles:
        for target_role in target_roles:
            for source_participant in by_role.get(source_role, []):
                for target_participant in by_role.get(target_role, []):
                    source = names_to_ids.get(source_participant.character_name)
                    target = names_to_ids.get(target_participant.character_name)
                    if not source or not target or source == target:
                        continue
                    confidence = min(
                        event.confidence,
                        source_participant.confidence,
                        target_participant.confidence,
                    )
                    relationship = _make_structured_story_relationship(
                        source,
                        target,
                        category=category,
                        relation_role=relation_role,
                        event=event,
                        confidence=confidence,
                    )
                    if relationship.id in seen_story_ids:
                        continue
                    seen_story_ids.add(relationship.id)
                    relationships.append(relationship)


def _relationships_from_structured_events(
    graph: GraphJson,
    *,
    current_boundary_global_index: int,
) -> list[Relationship]:
    names_to_ids = {entity.name: entity.id for entity in graph.entities}
    relationships: list[Relationship] = []
    seen_story_ids: set[str] = set()

    for event in graph.events:
        first_seen = event.first_seen_global_index or event.first_seen_chunk_offset or 0
        if first_seen > current_boundary_global_index:
            continue

        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("perpetrator", "accomplice"),
            ("victim",),
            category="crime",
            relation_role="crime",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("perpetrator", "threatener", "deceiver"),
            ("target", "threatened"),
            category="crime",
            relation_role="threat",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("investigator", "pursuer"),
            ("suspect", "perpetrator", "accomplice", "deceiver", "concealer", "pursued"),
            category="investigation",
            relation_role="investigation",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("protector", "helper"),
            ("target", "victim", "threatened", "pursued"),
            category="protection",
            relation_role="protection",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("helper",),
            ("beneficiary",),
            category="protection",
            relation_role="help",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("deceiver", "concealer", "threatener"),
            ("deceived", "exposed", "threatened"),
            category="deception",
            relation_role="deception",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("concealer",),
            ("pursued",),
            category="deception",
            relation_role="concealment",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("witness",),
            ("victim",),
            category="mystery",
            relation_role="witness",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("employer",),
            ("employee", "investigator", "helper"),
            category="work",
            relation_role="work",
        )
        _add_role_pairs(
            relationships,
            seen_story_ids,
            event,
            names_to_ids,
            ("beneficiary", "heir"),
            ("victim", "employer"),
            category="family",
            relation_role="inheritance",
        )

    return relationships


def _enrich_existing_relationship(
    relationship: Relationship,
    *,
    current_boundary_global_index: int,
) -> Relationship | None:
    if relationship.revision_offset > current_boundary_global_index:
        return None

    text = " ".join(
        part
        for part in [
            relationship.label,
            relationship.description,
            relationship.display_label or "",
            relationship.detail or "",
        ]
        if part
    )
    category = _category_for_text(text)
    if not category:
        return relationship

    is_story = category in CORE_STORY_CATEGORIES
    event_summary = relationship.detail or relationship.description or relationship.label
    update = {
        "relation_category": category,
        "directionality": "directed" if _is_directed(category) else relationship.directionality,
        "event_name": relationship.event_name or event_summary[:40],
        "event_summary": relationship.event_summary or event_summary,
        "relation_role": relationship.relation_role or STORY_ROLES.get(category, "사건 관련"),
        "confidence": max(relationship.confidence or 0.5, 0.75 if is_story else 0.6),
        "is_story_relation": relationship.is_story_relation or is_story,
        "first_seen_global_index": relationship.first_seen_global_index or relationship.revision_offset,
        "first_seen_boundary": relationship.first_seen_boundary or relationship.revision_offset,
        "last_seen_global_index": relationship.last_seen_global_index or relationship.revision_offset,
    }
    if is_story and not relationship.related_events:
        update["related_events"] = [
            _event_payload(event_summary, category, relationship.revision_offset, update["confidence"])
        ]
    return relationship.model_copy(update=update)


def expand_story_relationships(
    graph: GraphJson,
    reminders: list[ReminderLine],
    *,
    current_boundary_global_index: int,
) -> GraphJson:
    names_by_id = {entity.id: entity.name for entity in graph.entities}
    valid_ids = set(names_by_id)
    relationships: list[Relationship] = _relationships_from_structured_events(
        graph,
        current_boundary_global_index=current_boundary_global_index,
    )

    for relationship in graph.relationships:
        enriched = _enrich_existing_relationship(
            relationship,
            current_boundary_global_index=current_boundary_global_index,
        )
        if enriched is not None:
            relationships.append(enriched)

    seen_story_ids = {relationship.id for relationship in relationships}
    for line in reminders:
        participant_ids = [entity_id for entity_id in dict.fromkeys(line.entity_ids) if entity_id in valid_ids]
        if len(participant_ids) < 2:
            continue
        category = _category_for_text(line.text)
        if category not in CORE_STORY_CATEGORIES:
            continue
        confidence = 0.85 if category in {"crime", "investigation"} else 0.75
        for source, target in combinations(participant_ids, 2):
            story_relationship = _make_story_relationship(
                source,
                target,
                category=category,
                event_summary=line.text,
                boundary_global_index=min(graph.offset, current_boundary_global_index),
                names_by_id=names_by_id,
                confidence=confidence,
            )
            if story_relationship.id in seen_story_ids:
                continue
            seen_story_ids.add(story_relationship.id)
            relationships.append(story_relationship)

    return graph.model_copy(update={"relationships": relationships})
