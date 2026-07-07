import json
from langchain_upstage import ChatUpstage
from langchain_core.messages import SystemMessage, HumanMessage

from spokeeper.config import UPSTAGE_API_KEY


BUILD_AGENT_SYSTEM_PROMPT = """
당신은 SpoKeeper의 BuildAgent입니다.

역할:
- 소설 본문에서 현재 읽은 위치까지 확인된 정보만 추출합니다.
- 인물, 관계, 사건을 JSON 형태로 정리합니다.
- 추측, 예측, 해석은 금지합니다.
- 원문에 근거가 없는 정보는 출력하지 않습니다.

출력은 반드시 아래 JSON 형식을 따르세요.

{
  "characters": [
    {
      "name": "인물명",
      "description": "현재 본문에서 확인된 설명",
      "evidence": "근거 문장"
    }
  ],
  "relations": [
    {
      "source": "인물A",
      "target": "인물B",
      "relation": "관계",
      "evidence": "근거 문장"
    }
  ],
  "events": [
    {
      "summary": "사건 요약",
      "participants": ["인물A", "인물B"],
      "evidence": "근거 문장"
    }
  ]
}
"""


def extract_json_from_text(text: str) -> dict:
    """
    LLM 응답에서 JSON 부분만 안전하게 추출한다.
    JSON 파싱 실패 시에도 앱이 멈추지 않도록 빈 결과를 반환한다.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.find("```", start)

        if end != -1:
            json_text = text[start:end].strip()
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

    start = text.find("{")
    end = text.rfind("}") + 1

    if start != -1 and end > start:
        json_text = text[start:end]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return {
        "characters": [],
        "relations": [],
        "events": [],
        "parse_error": True,
        "raw_text": text,
    }


def build_agent(chunks: list[dict], current_offset: int) -> dict:
    """
    현재 offset까지의 chunk를 기반으로 인물, 관계, 사건을 추출한다.
    """
    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    readable_chunks = [
        chunk for chunk in chunks
        if chunk["offset"] <= current_offset
    ]

    context_text = "\n\n".join(
        [
            f"[offset={chunk['offset']} / chapter={chunk['chapter_index']}]\n{chunk['text']}"
            for chunk in readable_chunks
        ]
    )

    llm = ChatUpstage(
        model="solar-pro2",
        api_key=UPSTAGE_API_KEY,
        temperature=0,
    )

    response = llm.invoke(
        [
            SystemMessage(content=BUILD_AGENT_SYSTEM_PROMPT),
            HumanMessage(
                content=f"""
다음은 사용자가 현재까지 읽은 소설 본문입니다.

현재 offset: {current_offset}

본문:
{context_text}

위 본문에서 확인된 인물, 관계, 사건만 추출하세요.
"""
            ),
        ]
    )

    result = extract_json_from_text(response.content)

    return {
        "current_offset": current_offset,
        "used_chunk_count": len(readable_chunks),
        "characters": result.get("characters", []),
        "relations": result.get("relations", []),
        "events": result.get("events", []),
        "parse_error": result.get("parse_error", False),
        "raw_response": response.content,
}