import json
from langchain_upstage import ChatUpstage
from langchain_core.messages import SystemMessage, HumanMessage

from agents.config import UPSTAGE_API_KEY
from agents.character_entity_filter import filter_generic_role_entities


BUILD_AGENT_SYSTEM_PROMPT = """
당신은 SpoKeeper의 BuildAgent입니다.

역할:
- 소설 본문에서 현재 읽은 위치까지 확인된 정보만 추출합니다.
- 인물, 관계, 사건을 JSON 형태로 정리합니다.
- 추측, 예측, 해석은 금지합니다.
- 원문에 근거가 없는 정보는 출력하지 않습니다.

characters에 포함할지 판단하는 기준 (매우 중요, 반드시 지키세요):
- **실존하는 개별 인물(사람 한 명)만** characters에 넣습니다.
- 다음은 인물이 아니므로 절대 characters에 넣지 마세요:
  - 가문/가족/혈통 이름 (예: "배스커빌 가문", "○○ 가"). 가문 구성원 개인(예: "헨리 배스커빌")은
    인물이지만, 가문 자체는 인물이 아닙니다.
  - 기관/조직/장소 이름 (예: "차링 크로스 병원", "런던 경찰청", "베이커가")
  - 집단을 가리키는 일반명사 (예: "술꾼들", "마을 사람들", "하인들")
  - 특정 개인을 가리키지 않는 일반명사 (예: "처녀", "목동", "농부" — 실제 이름이나 뚜렷한
    호칭 없이 막연히 등장하는 경우. 단, 이후 본문에서 그 인물을 계속 가리키는 유일한
    표현이라면(예: 이름이 끝까지 안 나오는 조연) 예외적으로 포함 가능)
  - 동물, 사물, 탈것 (사람이 아닌 것은 전부 제외)

출력은 반드시 아래 JSON 형식을 따르세요.

{
  "characters": [
    {
      "name": "인물명",
      "entity_kind": "named_character | generic_role | important_unknown",
      "keep_as_character": true,
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

    readable_chunks = chunks

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

    build_result = {
        "current_offset": current_offset,
        "used_chunk_count": len(readable_chunks),
        "characters": result.get("characters", []),
        "relations": result.get("relations", []),
        "events": result.get("events", []),
        "parse_error": result.get("parse_error", False),
        "raw_response": response.content,
    }
    return filter_generic_role_entities(build_result)

def incremental_build_agent(
    chunks: list[dict],
    current_offset: int,
    last_built_offset: int,
    previous_results: dict,
    ) -> dict:
    """
    마지막으로 분석한 offset 이후의 chunk만 분석하고,
    기존 결과에 새 결과를 누적한다.
    """
    new_chunks = [
        chunk for chunk in chunks
        if last_built_offset < chunk["offset"] <= current_offset
    ]

    MAX_NEW_CHUNKS = 5

    new_chunks = new_chunks[:MAX_NEW_CHUNKS]

    if not new_chunks:
        return {
            "current_offset": current_offset,
            "last_built_offset": last_built_offset,
            "used_chunk_count": 0,
            "characters": previous_results.get("characters", []),
            "relations": previous_results.get("relations", []),
            "events": previous_results.get("events", []),
            "message": "새로 분석할 chunk가 없습니다.",
        }

    partial_result = build_agent(
    chunks=new_chunks,
    current_offset=max(chunk["offset"] for chunk in new_chunks),
    )

    merged_result = merge_build_results(
        previous_results=previous_results,
        new_result=partial_result,
    )

    return {
        "current_offset": current_offset,
        "last_built_offset": current_offset,
        "used_chunk_count": len(new_chunks),
        "characters": merged_result["characters"],
        "relations": merged_result["relations"],
        "events": merged_result["events"],
        "message": "증분 분석 완료",
    }


def merge_build_results(previous_results: dict, new_result: dict) -> dict:
    """
    기존 인물/관계/사건 결과에 새 결과를 병합한다.
    완전한 동일성 판단은 아직 하지 않고, 단순 중복 제거만 수행한다.
    (표기가 다른 동일 인물 병합은 이름 유사도로는 오탐이 커서, VerifierAgent의
    LLM 판단으로 옮겼다 — agents/verifier_agent.py의 canonicalize_character_names 참고.)
    """
    characters = deduplicate_by_key(
        previous_results.get("characters", []) + new_result.get("characters", []),
        key="name",
    )

    relations = deduplicate_relation(
        previous_results.get("relations", []) + new_result.get("relations", [])
    )

    events = deduplicate_by_key(
        previous_results.get("events", []) + new_result.get("events", []),
        key="summary",
    )

    return filter_generic_role_entities({
        "characters": characters,
        "relations": relations,
        "events": events,
    })


def deduplicate_by_key(items: list[dict], key: str) -> list[dict]:
    seen = set()
    result = []

    for item in items:
        value = item.get(key)

        if not value:
            result.append(item)
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(item)

    return result


def deduplicate_relation(relations: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for relation in relations:
        source = relation.get("source", "")
        target = relation.get("target", "")
        rel = relation.get("relation", "")

        key = (source, target, rel)

        if key in seen:
            continue

        seen.add(key)
        result.append(relation)

    return result
