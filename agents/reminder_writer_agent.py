import json
from langchain_upstage import ChatUpstage
from langchain_core.messages import SystemMessage, HumanMessage

from agents.config import UPSTAGE_API_KEY
from agents.build_agent import extract_json_from_text


REMINDER_WRITER_SYSTEM_PROMPT = """
당신은 SpoKeeper의 ReminderWriterAgent입니다 (읽기 경로 2차 가드).

역할:
- 검증된 인물/관계/사건 그래프를 받아, 독자가 지금까지 읽은 내용을 다시 떠올릴 수
  있도록 서술형 리마인드 문장을 작성합니다.
- 오직 주어진 evidence/description에 근거해서만 서술합니다.
- 추측, 예측, 해석, 앞으로 벌어질 일에 대한 암시는 절대 포함하지 않습니다.
- 각 문장은 자연스러운 한국어 한 문장으로, 관련된 인물 이름을 포함해 작성합니다.

출력은 반드시 아래 JSON 형식으로만 작성하세요.

{
  "lines": [
    {"text": "서술형 리마인드 문장", "entity_names": ["관련 인물명", ...]}
  ]
}
"""


def write_reminders(build_result: dict) -> dict:
    """
    검증된 build_result(characters/relations/events)를 바탕으로
    서술형 리마인드 문장 목록을 생성한다.
    """
    events = build_result.get("events", [])
    relations = build_result.get("relations", [])

    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    if not events and not relations:
        return {"lines": [], "raw_response": None}

    llm = ChatUpstage(
        model="solar-pro2",
        api_key=UPSTAGE_API_KEY,
        temperature=0,
    )

    payload = {
        "events": [
            {"summary": e.get("summary", ""), "participants": e.get("participants", [])}
            for e in events
        ],
        "relations": [
            {
                "source": r.get("source", ""),
                "target": r.get("target", ""),
                "relation": r.get("relation", ""),
                "description": r.get("evidence") or r.get("description", ""),
            }
            for r in relations
        ],
    }

    response = llm.invoke(
        [
            SystemMessage(content=REMINDER_WRITER_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
다음 사건/관계 정보를 바탕으로 독자를 위한 리마인드 문장을 작성하세요.

{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
            ),
        ]
    )

    result = extract_json_from_text(response.content)

    return {
        "lines": result.get("lines", []),
        "parse_error": result.get("parse_error", False),
        "raw_response": response.content,
    }
