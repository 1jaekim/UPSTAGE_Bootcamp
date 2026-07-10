from __future__ import annotations

import re

from .schemas import GraphJson, Relationship


ROLE_PAIR_LABELS = {
    "crime": ("가해자", "피해자"),
    "investigation": ("조사자", "용의자"),
    "protection": ("보호자", "보호 대상"),
    "deception": ("기만자", "기만당한 인물"),
    "threat": ("위협한 인물", "위협받은 인물"),
    "witness": ("목격자", "피해자"),
    "concealment": ("은닉자", "숨어 있는 인물"),
    "help": ("조력자", "수혜자"),
    "work": ("의뢰인", "조사자"),
    "inheritance": ("사망자", "상속인"),
    "family": ("가족", "가족"),
    "ally": ("조력자", "조력자"),
}

CATEGORY_LABELS = {
    "crime": ("가해자", "피해자"),
    "investigation": ("조사자", "용의자"),
    "deception": ("기만자", "기만당한 인물"),
    "protection": ("보호자", "보호 대상"),
    "work": ("의뢰인", "조사자"),
    "family": ("가족", "가족"),
    "ally": ("조력자", "동료"),
    "romance": ("관계 인물", "관계 인물"),
    "mystery": ("단서 제공자", "관련 인물"),
    "conflict": ("대립 인물", "대립 인물"),
    "neutral": ("관련 인물", "관련 인물"),
}

MECHANICAL_PHRASES = (
    "사건 관련 인물",
    "피해 인물",
    "조사하는 인물",
    "조사 대상",
    "가해와 피해 맥락",
    "조사와 의심의 맥락",
    "사건 맥락으로 연결",
    "같은 사건 안에서 관련 인물",
)


def _name_of(graph: GraphJson, entity_id: str) -> str:
    return next((entity.name for entity in graph.entities if entity.id == entity_id), entity_id)


def _clean_text(text: str | None, *, limit: int = 180) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _short_name(name: str) -> str:
    for suffix in (" 배스커빌 경", " 배스커빌", " 홈즈", " H. 왓슨", " 모티머"):
        if name.endswith(suffix):
            return name.replace("제임스 모티머", "모티머").replace("셜록 홈즈", "홈즈").replace("존 H. 왓슨", "왓슨").replace("찰스 배스커빌 경", "찰스 경").replace("헨리 배스커빌", "헨리")
    return name


def _context_text(relationship: Relationship) -> str:
    parts = [
        relationship.event_name or "",
        relationship.event_summary or "",
        relationship.detail or "",
        relationship.description or "",
    ]
    for event in relationship.related_events:
        parts.extend(
            str(event.get(key, ""))
            for key in ("event_name", "event_summary", "evidence", "relation_role")
        )
    return " ".join(part for part in parts if part)


def _event_name(relationship: Relationship) -> str:
    if relationship.event_name:
        return _clean_text(relationship.event_name, limit=48)
    for event in relationship.related_events:
        name = event.get("event_name")
        if name:
            return _clean_text(str(name), limit=48)
    return relationship.display_label or relationship.label or "관계"


def _role_pair(relationship: Relationship) -> tuple[str, str]:
    if relationship.relation_role and relationship.relation_role in ROLE_PAIR_LABELS:
        return ROLE_PAIR_LABELS[relationship.relation_role]
    category = relationship.relation_category or "neutral"
    return CATEGORY_LABELS.get(category, CATEGORY_LABELS["neutral"])


def _contextual_role_pair(relationship: Relationship, source_name: str, target_name: str) -> tuple[str, str]:
    text = _context_text(relationship)
    source = source_name
    target = target_name

    if "모티머" in source and "찰스" in target and any(hint in text for hint in ("주치의", "의사", "사망", "죽음")):
        return "주치의", "환자"
    if "모티머" in source and "홈즈" in target:
        return "의뢰인", "조사자"
    if "찰스" in source and "헨리" in target and any(hint in text for hint in ("상속", "후계", "재산", "작위")):
        return "삼촌", "상속인"
    if "배리모어" in source and any(name in target for name in ("셀든", "셀던", "선든")):
        return "은닉자", "탈주범"
    if "라이언스" in source and "스태플턴" in target:
        return "기만당한 인물", "기만자"

    return _role_pair(relationship)


def _evidence_items(relationship: Relationship) -> list[str]:
    candidates: list[str] = []
    for event in relationship.related_events:
        for key in ("evidence", "event_summary"):
            value = event.get(key)
            if value:
                candidates.append(str(value))
    candidates.extend(
        value
        for value in [relationship.event_summary, relationship.detail, relationship.description]
        if value
    )

    evidence: list[str] = []
    for candidate in candidates:
        cleaned = _clean_text(candidate, limit=220)
        if cleaned and cleaned not in evidence:
            evidence.append(cleaned)
        if len(evidence) >= 2:
            break
    return evidence


def _summary_from_event_text(text: str | None, *, source_name: str, target_name: str, limit: int = 150) -> str:
    cleaned = _clean_text(text, limit=limit)
    if not cleaned:
        return ""
    if len(cleaned) <= 120 and source_name in cleaned and target_name in cleaned:
        return cleaned
    return cleaned


def _summary_for(relationship: Relationship, source_name: str, target_name: str, role_pair_label: str, event_name: str) -> str:
    source_role, target_role = [part.strip() for part in role_pair_label.split("→", 1)]
    category = relationship.relation_category or "neutral"
    source = _short_name(source_name)
    target = _short_name(target_name)
    text = _context_text(relationship)

    if role_pair_label == "주치의 → 환자":
        return f"{source}는 {target}의 주치의로, 그의 죽음을 이상하게 여기고 사건 조사를 요청하는 계기가 된다."
    if role_pair_label == "의뢰인 → 조사자":
        return f"{source}는 {target}에게 찰스 경의 죽음과 가문의 저주에 대한 조사를 부탁한다."
    if role_pair_label == "삼촌 → 상속인":
        return f"{source}가 사망한 뒤 {target}가 배스커빌 가문의 재산과 작위를 이어받는다."
    if role_pair_label == "은닉자 → 탈주범":
        return f"{source}는 숨어 지내는 {target}을 돕거나 숨겨 주는 일로 사건에 얽힌다."
    if role_pair_label == "기만당한 인물 → 기만자":
        return f"{source}는 {target}의 말이나 계획에 속아 사건에 이용된다."
    if role_pair_label == "가해자 → 피해자":
        return f"{source}는 '{event_name}'에서 {target}에게 해를 끼친 핵심 인물로 드러난다."
    if role_pair_label == "조사자 → 용의자":
        return f"{source}는 '{event_name}'을 추적하며 {target}의 행동과 정체를 의심하고 조사한다."
    if role_pair_label == "보호자 → 보호 대상":
        return f"{source}는 위험에 놓인 {target}을 동행하거나 보호하며 사건에 관여한다."
    if role_pair_label == "기만자 → 기만당한 인물":
        return f"{source}는 {target}을 속이거나 잘못된 판단을 하게 만들어 사건을 자기 쪽으로 끌고 간다."
    if role_pair_label == "조력자 → 수혜자":
        return f"{source}는 {target}에게 도움을 주며 사건의 진행에 영향을 미친다."
    if role_pair_label == "목격자 → 피해자":
        return f"{source}는 {target}에게 벌어진 일을 목격하거나 증언하면서 사건의 실마리를 제공한다."

    event_summary = _summary_from_event_text(relationship.event_summary, source_name=source_name, target_name=target_name)
    if event_summary and not any(phrase in event_summary for phrase in MECHANICAL_PHRASES):
        return event_summary

    if category == "work":
        return f"{source}와 {target}은 의뢰나 조사 요청을 통해 사건 해결 과정에서 연결된다."
    if category == "family":
        return f"{source}와 {target}은 가족이나 상속 문제를 통해 사건의 배경과 연결된다."
    if category == "ally":
        return f"{source}와 {target}은 사건을 해결하거나 위험을 피하는 과정에서 서로 협력한다."
    if category == "deception":
        return f"{source}와 {target}은 속임수나 은폐가 드러나는 과정에서 연결된다."
    if category == "mystery":
        return f"{source}와 {target}은 사건의 단서나 의문을 밝히는 과정에서 연결된다."
    if text:
        return _clean_text(text, limit=150)
    return f"{source}와 {target}은 '{event_name}'을 통해 서로 관련된다."


def apply_relationship_presentation(graph: GraphJson) -> GraphJson:
    relationships: list[Relationship] = []
    for relationship in graph.relationships:
        source_name = _name_of(graph, relationship.source)
        target_name = _name_of(graph, relationship.target)
        source_role, target_role = _contextual_role_pair(relationship, source_name, target_name)
        role_pair_label = f"{source_role} → {target_role}"
        event_name = _event_name(relationship)
        display_label = role_pair_label if relationship.is_story_relation else (
            relationship.display_label or relationship.label or role_pair_label
        )
        summary = _summary_for(relationship, source_name, target_name, role_pair_label, event_name)
        evidence = _evidence_items(relationship)

        relationships.append(
            relationship.model_copy(
                update={
                    "role_label": source_role,
                    "role_pair_label": role_pair_label,
                    "event_name": event_name,
                    "display_label": display_label,
                    "relationship_summary": summary,
                    "evidence": evidence,
                }
            )
        )

    return graph.model_copy(update={"relationships": relationships})
