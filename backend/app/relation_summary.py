from __future__ import annotations

from collections import Counter, defaultdict

from .schemas import Entity, GraphJson, Relationship


_CATEGORY_HINTS = {
    "ally": ("친구", "동료", "조력", "신뢰", "협력", "동행", "도움"),
    "family": ("가족", "부인", "남편", "아내", "후계자", "가문", "형제", "남매", "부부", "딸", "아들"),
    "conflict": ("갈등", "의심", "적대", "추적", "살해", "위협", "공격", "범인", "고발"),
    "crime": ("살인", "살해", "죽", "사망", "시체", "범인", "피해자", "독살", "공격"),
    "investigation": ("조사", "수사", "추적", "의심", "용의", "단서", "탐문", "밝히"),
    "deception": ("속", "기만", "위장", "거짓", "은폐", "숨김", "비밀", "협박", "함정"),
    "protection": ("보호", "도움", "돕", "동행", "구출", "지키", "경호"),
    "romance": ("사랑", "연인", "약혼", "질투", "청혼", "결혼"),
    "work": ("의뢰", "고용", "조사", "업무", "주치의", "집사", "하인", "고용인"),
    "mystery": ("정체", "비밀", "단서", "미스터리", "수수께끼", "숨김", "은폐"),
}

_CATEGORY_PRIORITY = (
    "crime",
    "investigation",
    "deception",
    "protection",
    "family",
    "romance",
    "conflict",
    "work",
    "ally",
    "mystery",
    "neutral",
)
_DIRECTED_HINTS = ("의뢰", "고용", "추적", "살해", "위협", "공격", "고발", "조사", "도움", "보냄", "지시", "속임", "보호")
_STORY_CATEGORIES = {"crime", "investigation", "deception", "protection"}


def _relation_text(relationship: Relationship) -> str:
    return " ".join(
        part
        for part in [
            relationship.label,
            relationship.description,
            relationship.display_label or "",
            relationship.detail or "",
        ]
        if part
    )


def _category_for(relationships: list[Relationship]) -> str:
    story_categories = [
        relationship.relation_category
        for relationship in relationships
        if relationship.is_story_relation and relationship.relation_category in _STORY_CATEGORIES
    ]
    if story_categories:
        return max(
            _CATEGORY_PRIORITY,
            key=lambda category: (story_categories.count(category), -_CATEGORY_PRIORITY.index(category)),
        )

    text = " ".join(_relation_text(relationship) for relationship in relationships)
    counts = {
        category: sum(1 for hint in hints if hint in text)
        for category, hints in _CATEGORY_HINTS.items()
    }
    if not any(counts.values()):
        return "neutral"
    return max(_CATEGORY_PRIORITY, key=lambda category: (counts.get(category, 0), -_CATEGORY_PRIORITY.index(category)))


def _directionality_for(relationships: list[Relationship], category: str) -> str:
    text = " ".join(_relation_text(relationship) for relationship in relationships)
    if category in {"crime", "investigation", "deception", "protection"}:
        return "directed"
    if category in {"family", "romance", "ally"}:
        return "undirected"
    if any(hint in text for hint in _DIRECTED_HINTS):
        return "directed"
    return "undirected"


def _display_label_for(relationships: list[Relationship], category: str) -> str:
    story_labels = [
        (relationship.display_label or relationship.label).strip()
        for relationship in relationships
        if relationship.is_story_relation and (relationship.display_label or relationship.label).strip()
    ]
    if story_labels:
        label, _ = Counter(story_labels).most_common(1)[0]
        return label[:12]

    labels = [relationship.label.strip() for relationship in relationships if relationship.label.strip()]
    if labels:
        label, _ = Counter(labels).most_common(1)[0]
        return label[:12]
    return {
        "ally": "협력",
        "family": "가족",
        "conflict": "갈등",
        "crime": "사건",
        "investigation": "조사",
        "deception": "속임",
        "protection": "보호",
        "romance": "관계",
        "work": "업무",
        "mystery": "단서",
        "neutral": "관련",
    }[category]


def _importance_for(
    relationships: list[Relationship],
    entities_by_id: dict[str, Entity],
    reminder_entity_ids: set[str],
) -> int:
    source = relationships[0].source
    target = relationships[0].target
    score = 1
    if len(relationships) >= 2:
        score += 1
    if len(relationships) >= 4:
        score += 1
    if entities_by_id.get(source) and entities_by_id[source].importance_level == "major":
        score += 1
    if entities_by_id.get(target) and entities_by_id[target].importance_level == "major":
        score += 1
    if source in reminder_entity_ids and target in reminder_entity_ids:
        score += 1
    if any((relationship.description or "").strip() for relationship in relationships):
        score += 1
    if any(relationship.is_story_relation for relationship in relationships):
        score += 2
    if any(relationship.relation_category in {"crime", "investigation", "deception"} for relationship in relationships):
        score += 1
    return max(1, min(5, score))


def _pair_key(relationship: Relationship) -> tuple[str, str]:
    return tuple(sorted([relationship.source, relationship.target]))


def summarize_relationships(
    graph: GraphJson,
    *,
    current_boundary_global_index: int,
    reminder_entity_ids: list[str],
) -> GraphJson:
    grouped: dict[tuple[str, str], list[Relationship]] = defaultdict(list)
    for relationship in graph.relationships:
        first_seen = relationship.first_seen_global_index or relationship.revision_offset
        if first_seen > current_boundary_global_index:
            continue
        grouped[_pair_key(relationship)].append(relationship)

    entities_by_id = {entity.id: entity for entity in graph.entities}
    reminder_ids = set(reminder_entity_ids)
    summarized: list[Relationship] = []

    for relationships in grouped.values():
        relationships = sorted(
            relationships,
            key=lambda relationship: (
                not relationship.is_story_relation,
                relationship.revision_offset,
            ),
        )
        first = relationships[0]
        category = _category_for(relationships)
        directionality = _directionality_for(relationships, category)
        display_label = _display_label_for(relationships, category)
        first_seen = min(
            relationship.first_seen_global_index or relationship.revision_offset
            for relationship in relationships
        )
        last_seen = max(
            relationship.last_seen_global_index
            or relationship.first_seen_global_index
            or relationship.revision_offset
            for relationship in relationships
        )
        importance_score = _importance_for(relationships, entities_by_id, reminder_ids)
        detail_parts = []
        related_events = []
        for relationship in relationships:
            detail = relationship.detail or relationship.description or relationship.label
            if detail and detail not in detail_parts:
                detail_parts.append(detail)
            for related_event in relationship.related_events:
                if related_event not in related_events:
                    related_events.append(related_event)
        if len(detail_parts) > 6:
            detail_parts = detail_parts[:6]
        detail = "\n".join(detail_parts)
        story_relation = next((relationship for relationship in relationships if relationship.is_story_relation), None)

        summarized.append(
            first.model_copy(
                update={
                    "label": display_label,
                    "display_label": display_label,
                    "relation_category": category,
                    "directionality": directionality,
                    "relation_importance_score": importance_score,
                    "relation_importance_level": "major" if importance_score >= 4 else "minor",
                    "first_seen_global_index": first_seen,
                    "first_seen_boundary": first_seen,
                    "is_new_at_current_position": first_seen == current_boundary_global_index,
                    "detail": detail,
                    "description": detail or first.description,
                    "revision_offset": first_seen,
                    "event_name": story_relation.event_name if story_relation else first.event_name,
                    "event_summary": story_relation.event_summary if story_relation else first.event_summary,
                    "relation_role": story_relation.relation_role if story_relation else first.relation_role,
                    "confidence": max((relationship.confidence or 0.5) for relationship in relationships),
                    "is_story_relation": any(relationship.is_story_relation for relationship in relationships),
                    "last_seen_global_index": last_seen,
                    "related_events": related_events,
                }
            )
        )

    summarized.sort(
        key=lambda relationship: (
            relationship.relation_importance_level != "major",
            -(relationship.relation_importance_score or 1),
            relationship.revision_offset,
        )
    )
    return graph.model_copy(update={"relationships": summarized})
