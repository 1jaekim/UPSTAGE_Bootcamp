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


def verify_build_result(build_result: dict) -> dict:
    """
    build_result(누적된 characters/relations/events)를 검증해서,
    근거가 확인된 relations/events만 남긴 결과를 반환한다.
    characters는 검증 대상이 아니라 그대로 통과시킨다(이름 자체는 근거 검증 불필요).
    """
    relations = build_result.get("relations", [])
    events = build_result.get("events", [])

    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    if not relations and not events:
        return {**build_result, "verifier_raw_response": None}

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
