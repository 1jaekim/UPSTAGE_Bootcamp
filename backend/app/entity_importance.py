from __future__ import annotations

from collections import Counter, defaultdict

from agents.character_aliases import load_character_alias_map

from .schemas import GraphJson


_CORE_CHARACTER_NAMES = {
    "셜록 홈즈",
    "존 H. 왓슨",
    "헨리 배스커빌",
    "제임스 모티머",
}


def _core_names_for_book(book_id: str) -> set[str]:
    alias_map = load_character_alias_map(book_id)
    return _CORE_CHARACTER_NAMES | {name for name in alias_map.values() if name in _CORE_CHARACTER_NAMES}


def apply_entity_importance(book_id: str, graph: GraphJson, reminder_entity_ids: list[str]) -> GraphJson:
    relation_mentions: Counter[str] = Counter()
    connected_neighbors: dict[str, set[str]] = defaultdict(set)

    for relationship in graph.relationships:
        relation_mentions[relationship.source] += 1
        relation_mentions[relationship.target] += 1
        connected_neighbors[relationship.source].add(relationship.target)
        connected_neighbors[relationship.target].add(relationship.source)

    reminder_mentions = Counter(reminder_entity_ids)
    core_names = _core_names_for_book(book_id)

    entities = []
    for entity in graph.entities:
        relation_count = relation_mentions[entity.id]
        degree = len(connected_neighbors[entity.id])
        reminder_count = reminder_mentions[entity.id]

        raw_score = 1
        if relation_count >= 1:
            raw_score += 1
        if relation_count >= 3 or degree >= 3:
            raw_score += 1
        if reminder_count >= 1:
            raw_score += 1
        if reminder_count >= 3:
            raw_score += 1
        if entity.name in core_names:
            raw_score += 2

        importance_score = max(1, min(5, raw_score))
        entities.append(
            entity.model_copy(
                update={
                    "importance_score": importance_score,
                    "importance_level": "major" if importance_score >= 4 else "minor",
                }
            )
        )

    return graph.model_copy(update={"entities": entities})
