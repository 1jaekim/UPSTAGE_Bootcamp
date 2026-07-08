import json
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
    if result.get("parse_error"):
        return identity_map

    for group in result.get("groups", []):
        canonical = group.get("canonical_name")
        if not canonical:
            continue
        for name in group.get("names", []):
            if name in identity_map:
                identity_map[name] = canonical

    return identity_map


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
    if name_map:
        merged_characters: dict[str, dict] = {}
        for c in characters:
            canon = name_map.get(c.get("name", ""), c.get("name", ""))
            if canon not in merged_characters:
                merged_characters[canon] = {**c, "name": canon}
        characters = list(merged_characters.values())
        relations = [
            {
                **r,
                "source": name_map.get(r.get("source", ""), r.get("source", "")),
                "target": name_map.get(r.get("target", ""), r.get("target", "")),
            }
            for r in relations
        ]
        events = [
            {**e, "participants": [name_map.get(p, p) for p in e.get("participants", [])]}
            for e in events
        ]
        build_result = {**build_result, "characters": characters}

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
