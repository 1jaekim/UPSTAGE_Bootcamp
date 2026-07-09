import json
import re
from langchain_upstage import ChatUpstage
from langchain_core.messages import SystemMessage, HumanMessage

from agents.config import UPSTAGE_API_KEY
from agents.build_agent import extract_json_from_text


VERIFIER_SYSTEM_PROMPT = """
당신은 SpoKeeper의 VerifierAgent입니다 (읽기 경로 1차 가드).

역할:
- BuildAgent가 추출한 인물/관계/사건 각 항목에 붙은 evidence(근거 문장)가
  실제로 그 항목의 내용을 뒷받침하는지 검증합니다.
- evidence가 비어있거나, 항목 내용과 무관하거나, evidence 자체가 추측/해석이면
  invalid로 판정합니다.
- 근거가 명확한 항목만 valid로 남깁니다. 새로운 정보를 추가하거나 추측하지 않습니다.

출력은 반드시 아래 JSON 형식으로만 작성하세요.

{
  "valid_relation_keys": ["source|target|relation", ...],
  "valid_event_summaries": ["사건 요약 원문", ...]
}
"""


CHARACTER_DEDUP_SYSTEM_PROMPT = """
당신은 SpoKeeper의 VerifierAgent입니다. 여기서 맡은 역할은 "인물 중복 판단"입니다.

배경:
BuildAgent가 같은 소설을 여러 구간으로 나눠서 반복 분석하다 보니, 같은 인물이
매번 다른 표기(애칭, 직함 유무, 성만/이름만 등)로 등장해서 그래프에 별개의
인물로 쪼개지는 문제가 있습니다. 당신의 역할은 이름 목록(설명·근거 포함)을 보고
실제로 같은 인물을 가리키는 항목들을 찾아 하나의 대표 이름으로 묶는 것입니다.

절대 규칙:
- 이름 문자열이 비슷하거나 겹친다는 이유만으로 병합하지 마세요. 반드시 각 이름에
  붙은 description/evidence 내용을 읽고, 실제로 같은 사람을 가리키는지 확인한
  뒤에만 병합하세요.
- 성이나 일부 음절이 겹치는 서로 다른 인물(예: 형제자매, 부부, 우연히 성이 같은
  타인)은 절대 병합하지 않습니다.
- 병합이 확실하지 않으면(애매하면) 병합하지 않는 쪽을 선택하세요 — 잘못 합치는
  것이 안 합치는 것보다 훨씬 나쁩니다.
- 대표 이름은 그 그룹 안에서 가장 완전하고 격식 있는 표기를 선택하세요
  (예: 성+이름+직함이 있으면 그것을 우선).

판단 예시 (참고용이며, 실제 판단은 항상 주어진 description/evidence를 따르세요):

예시 1 — 같은 인물, 직함 유무 차이
  입력: "제임스 모티머" (description: "지팡이를 두고 간 방문객, 의사"),
        "제임스 모티머 박사" (description: "M.R.C.S. 자격을 가진 의사, 지팡이 주인")
  판단: 같은 인물 (둘 다 지팡이 주인이자 의사라는 동일 맥락)
  결과: {"names": ["제임스 모티머", "제임스 모티머 박사"], "canonical_name": "제임스 모티머 박사"}

예시 2 — 같은 인물, 애칭/축약
  입력: "홈즈" (description: "추리하는 탐정"),
        "셜록 홈즈" (description: "베이커가에 사는 탐정, 왓슨의 동료")
  판단: 같은 인물 (둘 다 탐정이자 왓슨과 연관)
  결과: {"names": ["홈즈", "셜록 홈즈"], "canonical_name": "셜록 홈즈"}

예시 3 — 성만 겹치는 다른 인물 (병합 금지)
  입력: "존스 형사" (description: "런던 경찰청 소속 수사관"),
        "톰슨 존스" (description: "피해자의 이웃, 목격자")
  판단: 다른 인물 (직업과 역할이 전혀 다름, 성만 우연히 겹침)
  결과: 병합하지 않음 (groups에 포함시키지 않음)

예시 4 — 가족 관계 (병합 금지)
  입력: "왓슨" (description: "주인공의 동료 의사"),
        "왓슨 부인" (description: "왓슨의 아내")
  판단: 다른 인물 (부부 관계일 뿐 동일인이 아님)
  결과: 병합하지 않음

출력은 반드시 아래 JSON 형식으로만 작성하세요. 병합할 그룹이 없으면 groups를
빈 배열로 두세요.

{
  "groups": [
    {"names": ["원본이름1", "원본이름2", ...], "canonical_name": "대표이름"}
  ]
}
"""


_HONORIFIC_SUFFIXES = (
    "씨",
    "님",
    "군",
    "양",
    "경",
)
_TITLE_SUFFIXES = (
    "박사",
    "교수",
    "선생",
    "형사",
    "경감",
    "경위",
)
_FAMILY_OR_ROLE_WORDS = (
    "부인",
    "아내",
    "남편",
    "아버지",
    "어머니",
    "딸",
    "아들",
    "형",
    "누나",
    "언니",
    "동생",
    "가정부",
    "하인",
)
_GENERIC_REFERENCES = {"나", "화자", "서술자", "주인공"}
_SAFE_FIRST_NAME_ALIASES = {"셜록"}


def _normalize_alias_text(name: str) -> str:
    """표기 흔들림 비교용 이름 정규화. 표시 이름 자체는 바꾸지 않는다."""
    text = (name or "").strip()
    text = re.sub(r"[\"'“”‘’.,!?]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("홈스", "홈즈")
    return text.strip()


def _without_parentheses(name: str) -> str:
    return re.sub(r"\([^)]*\)", "", name or "").strip()


def _strip_suffixes(name: str) -> str:
    text = _without_parentheses(_normalize_alias_text(name))
    changed = True
    while changed:
        changed = False
        for suffix in _HONORIFIC_SUFFIXES + _TITLE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[: -len(suffix)].strip()
                changed = True
    return text


def _alias_key(name: str) -> str:
    return re.sub(r"\s+", "", _strip_suffixes(name)).lower()


def _parenthetical_aliases(name: str) -> list[str]:
    aliases: list[str] = []
    for raw in re.findall(r"\(([^)]*)\)", name or ""):
        alias = raw.strip()
        if alias and alias not in _GENERIC_REFERENCES:
            aliases.append(alias)
    return aliases


def _is_generic_reference(name: str) -> bool:
    return _strip_suffixes(name) in _GENERIC_REFERENCES


def _is_narrator_reference(name: str) -> bool:
    text = _normalize_alias_text(name)
    stripped = _strip_suffixes(name)
    return stripped in _GENERIC_REFERENCES or any(ref in text for ref in ("나(", "화자"))


def _has_family_or_role_word(name: str) -> bool:
    stripped = _strip_suffixes(name)
    return any(word in stripped for word in _FAMILY_OR_ROLE_WORDS)


def _canonical_score(name: str) -> tuple[int, int, int]:
    stripped = _without_parentheses(_normalize_alias_text(name))
    return (
        0 if _is_generic_reference(name) else 1,
        0 if "홈스" in name else 1,
        1 if " " in stripped else 0,
        len(stripped),
    )


def _preferred_canonical(names: list[str]) -> str:
    return max(names, key=_canonical_score)


def _normalize_canonical_display(name: str) -> str:
    text = (name or "").strip()
    text = text.replace("홈스", "홈즈")
    return text


def _deduplicate_relations(relations: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for relation in relations:
        key = (
            relation.get("source", ""),
            relation.get("target", ""),
            relation.get("relation", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(relation)

    return result


def _deduplicate_events(events: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for event in events:
        key = (
            event.get("summary", ""),
            tuple(event.get("participants", [])),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(event)

    return result


def _apply_transitive_map(name_map: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}

    for name in name_map:
        current = name
        visited = set()
        while current in name_map and name_map[current] != current and current not in visited:
            visited.add(current)
            current = name_map[current]
        resolved[name] = current

    return resolved


def _find_watson_canonical(name_map: dict[str, str]) -> str | None:
    candidates = [
        canonical
        for canonical in set(name_map.values())
        if "왓슨" in _normalize_alias_text(canonical)
    ]
    if not candidates:
        return None
    return _preferred_canonical(candidates)


def _looks_like_watson_narrator(character: dict) -> bool:
    name = character.get("name", "")
    if not _is_narrator_reference(name):
        return False

    text = " ".join(
        [
            name,
            character.get("description", ""),
            character.get("evidence", ""),
        ]
    )
    return any(
        hint in text
        for hint in ("왓슨", "의사", "군의관", "홈즈의 동료", "홈즈와 동행", "베이커 가")
    )


def _augment_identity_map_with_alias_rules(
    characters: list[dict],
    identity_map: dict[str, str],
) -> dict[str, str]:
    """
    LLM이 놓치기 쉬운 안전한 표기 차이를 보정한다.
    예: 셜록 홈스/셜록 홈즈, 홈즈/셜록 홈즈, 홈즈 씨/셜록 홈즈.
    """
    names = [c.get("name", "").strip() for c in characters if c.get("name")]
    if len(names) < 2:
        return identity_map

    result = dict(identity_map)
    alias_to_names: dict[str, list[str]] = {}

    for name in names:
        keys = {_alias_key(name)}
        keys.update(_alias_key(alias) for alias in _parenthetical_aliases(name))
        for key in keys:
            if key:
                alias_to_names.setdefault(key, []).append(name)

    for grouped_names in alias_to_names.values():
        unique_names = list(dict.fromkeys(grouped_names))
        if len(unique_names) < 2:
            continue
        canonical = _preferred_canonical([result.get(name, name) for name in unique_names])
        canonical = _normalize_canonical_display(canonical)
        for name in unique_names:
            result[name] = canonical

    for name, canonical in list(result.items()):
        normalized = _normalize_canonical_display(canonical)
        result[name] = normalized
        if normalized != canonical and canonical in result:
            result[canonical] = normalized

    canonical_names = sorted(set(result.values()), key=len, reverse=True)
    short_alias_to_canonical: dict[str, str | None] = {}

    for canonical in canonical_names:
        base = _strip_suffixes(canonical)
        parts = [part for part in base.split(" ") if part]
        if len(parts) < 2 or _has_family_or_role_word(canonical):
            continue

        aliases = {parts[-1]}
        if parts[0] in _SAFE_FIRST_NAME_ALIASES:
            aliases.add(parts[0])

        for alias in aliases:
            key = _alias_key(alias)
            existing = short_alias_to_canonical.get(key)
            if existing is None and key in short_alias_to_canonical:
                continue
            if existing and existing != canonical:
                short_alias_to_canonical[key] = None
            else:
                short_alias_to_canonical[key] = canonical

    for name in names:
        if result.get(name, name) != name:
            continue
        key = _alias_key(name)
        canonical = short_alias_to_canonical.get(key)
        if canonical and canonical != name:
            result[name] = canonical

    # "화자(왓슨)"처럼 괄호 안 별칭이 기존 인물명과 맞으면 연결한다.
    alias_key_to_canonical = {
        _alias_key(name): result.get(canonical, canonical)
        for name, canonical in result.items()
    }
    for name in names:
        if result.get(name, name) != name:
            continue
        for alias in _parenthetical_aliases(name):
            canonical = alias_key_to_canonical.get(_alias_key(alias))
            if canonical:
                result[name] = canonical
                break

    watson_canonical = _find_watson_canonical(result)
    if watson_canonical:
        by_name = {c.get("name", ""): c for c in characters if c.get("name")}
        for name in names:
            if result.get(name, name) != name:
                continue
            if _looks_like_watson_narrator(by_name.get(name, {})):
                result[name] = watson_canonical

    return _apply_transitive_map(result)


def canonicalize_character_names(characters: list[dict]) -> dict[str, str]:
    """
    characters(name/description/evidence 포함)를 LLM에게 보여주고, 표기만 다른
    동일 인물을 찾아 대표 이름으로 묶은 매핑을 반환한다.
    반환값: {원본 이름: 대표 이름} — 병합 대상이 없는 이름은 자기 자신에 매핑된다.
    이름 문자열 유사도만으로는 "존스 형사"와 "톰슨 존스" 같은 다른 인물을
    잘못 합칠 위험이 커서, description/evidence까지 같이 보여주고 LLM이
    맥락으로 판단하게 한다 (프롬프트에 판단 예시 다수 포함, CHARACTER_DEDUP_SYSTEM_PROMPT 참고).
    """
    identity_map = {c.get("name", ""): c.get("name", "") for c in characters if c.get("name")}

    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    if len(characters) < 2:
        return identity_map

    llm = ChatUpstage(
        model="solar-pro2",
        api_key=UPSTAGE_API_KEY,
        temperature=0,
    )

    payload = [
        {
            "name": c.get("name", ""),
            "description": c.get("description", ""),
            "evidence": c.get("evidence", ""),
        }
        for c in characters
    ]

    response = llm.invoke(
        [
            SystemMessage(content=CHARACTER_DEDUP_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
다음 인물 목록에서 같은 인물을 가리키는 항목이 있는지 판단하세요.

{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
            ),
        ]
    )

    result = extract_json_from_text(response.content)
    if not isinstance(result, dict):
        return _augment_identity_map_with_alias_rules(characters, identity_map)

    if result.get("parse_error"):
        return _augment_identity_map_with_alias_rules(characters, identity_map)

    for group in result.get("groups", []):
        canonical = group.get("canonical_name")
        if not canonical:
            continue
        for name in group.get("names", []):
            if name in identity_map:
                identity_map[name] = canonical

    return _augment_identity_map_with_alias_rules(characters, identity_map)


def _names_from_build_result(build_result: dict) -> list[dict]:
    seen = set()
    result: list[dict] = []

    def add(name: str, description: str = "", evidence: str = "") -> None:
        name = (name or "").strip()
        if not name or name in seen:
            return
        seen.add(name)
        result.append({"name": name, "description": description, "evidence": evidence})

    for character in build_result.get("characters", []):
        add(
            character.get("name", ""),
            character.get("description", ""),
            character.get("evidence", ""),
        )

    for relation in build_result.get("relations", []):
        evidence = relation.get("evidence", "")
        add(relation.get("source", ""), evidence=evidence)
        add(relation.get("target", ""), evidence=evidence)

    for event in build_result.get("events", []):
        evidence = event.get("evidence", "")
        for participant in event.get("participants", []):
            add(participant, evidence=evidence)

    return result


def _build_name_lookup(name_map: dict[str, str]) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for name, canonical in name_map.items():
        canonical = _normalize_canonical_display(canonical)
        keys = {_alias_key(name), _alias_key(canonical)}
        base = _strip_suffixes(canonical)
        parts = [part for part in base.split(" ") if part]
        if len(parts) >= 2 and not _has_family_or_role_word(canonical):
            keys.add(_alias_key(parts[-1]))
            if parts[0] in _SAFE_FIRST_NAME_ALIASES:
                keys.add(_alias_key(parts[0]))
        for key in keys:
            if key and key not in lookup:
                lookup[key] = canonical

    return lookup


def _resolve_name(name: str, name_map: dict[str, str], lookup: dict[str, str]) -> str:
    if not name:
        return name
    if name in name_map:
        return _normalize_canonical_display(name_map[name])
    direct = lookup.get(_alias_key(name))
    if direct:
        return direct
    for alias in _parenthetical_aliases(name):
        canonical = lookup.get(_alias_key(alias))
        if canonical:
            return canonical
    return _normalize_canonical_display(name)


def _apply_character_name_map(
    build_result: dict,
    name_map: dict[str, str],
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    characters = build_result.get("characters", [])
    relations = build_result.get("relations", [])
    events = build_result.get("events", [])
    lookup = _build_name_lookup(name_map)

    merged_characters: dict[str, dict] = {}
    for character in characters:
        name = character.get("name", "")
        canonical = _resolve_name(name, name_map, lookup)
        if canonical not in merged_characters:
            merged_characters[canonical] = {**character, "name": canonical}
            continue

        existing = merged_characters[canonical]
        if not existing.get("description") and character.get("description"):
            existing["description"] = character.get("description")
        if not existing.get("evidence") and character.get("evidence"):
            existing["evidence"] = character.get("evidence")

    characters = list(merged_characters.values())
    relations = _deduplicate_relations(
        [
            {
                **relation,
                "source": _resolve_name(relation.get("source", ""), name_map, lookup),
                "target": _resolve_name(relation.get("target", ""), name_map, lookup),
            }
            for relation in relations
        ]
    )
    events = _deduplicate_events(
        [
            {
                **event,
                "participants": [
                    _resolve_name(participant, name_map, lookup)
                    for participant in event.get("participants", [])
                ],
            }
            for event in events
        ]
    )

    build_result = {
        **build_result,
        "characters": characters,
        "relations": relations,
        "events": events,
    }
    return build_result, characters, relations, events


def verify_build_result(build_result: dict) -> dict:
    """
    build_result(누적된 characters/relations/events)를 검증해서,
    근거가 확인된 relations/events만 남기고, 표기만 다른 동일 인물을
    canonicalize_character_names로 병합한 결과를 반환한다.
    """
    characters = build_result.get("characters", [])
    relations = build_result.get("relations", [])
    events = build_result.get("events", [])

    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    # 인물 이름 정규화 (LLM 판단) — characters/relations/events 전부에 적용
    name_map = canonicalize_character_names(characters)
    name_map = _augment_identity_map_with_alias_rules(
        _names_from_build_result(build_result),
        name_map,
    )
    if name_map:
        build_result, characters, relations, events = _apply_character_name_map(
            build_result,
            name_map,
        )

    if not relations and not events:
        return {**build_result, "relations": relations, "events": events, "verifier_raw_response": None}

    llm = ChatUpstage(
        model="solar-pro2",
        api_key=UPSTAGE_API_KEY,
        temperature=0,
    )

    payload = {
        "relations": [
            {
                "key": f"{r.get('source', '')}|{r.get('target', '')}|{r.get('relation', '')}",
                "relation": r.get("relation", ""),
                "evidence": r.get("evidence", ""),
            }
            for r in relations
        ],
        "events": [
            {"summary": e.get("summary", ""), "evidence": e.get("evidence", "")}
            for e in events
        ],
    }

    response = llm.invoke(
        [
            SystemMessage(content=VERIFIER_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
다음 relations/events 각각의 evidence가 실제로 내용을 뒷받침하는지 검증하세요.

{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
            ),
        ]
    )

    result = extract_json_from_text(response.content)
    if not isinstance(result, dict):
        return {**build_result, "verifier_raw_response": response.content}

    valid_keys = set(result.get("valid_relation_keys", []))
    valid_summaries = set(result.get("valid_event_summaries", []))

    # 파싱 실패(parse_error)면 안전한 쪽으로 아무것도 버리지 않는다 (과도한 억제 방지).
    if result.get("parse_error"):
        return {**build_result, "verifier_raw_response": response.content}

    filtered_relations = [
        r
        for r in relations
        if f"{r.get('source', '')}|{r.get('target', '')}|{r.get('relation', '')}" in valid_keys
    ]
    filtered_events = [e for e in events if e.get("summary", "") in valid_summaries]

    return {
        **build_result,
        "relations": filtered_relations,
        "events": filtered_events,
        "verifier_raw_response": response.content,
    }
