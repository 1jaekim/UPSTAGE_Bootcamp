"""데모 시드 데이터 (SPEC §1 / MOCKS.md). FE mock ↔ BE 시드 ↔ 에이전트 동일 사용."""
from __future__ import annotations

from .schemas import (
    Book,
    Chapter,
    Entity,
    GraphJson,
    Part,
    ReminderLine,
    Reminders,
    Relationship,
)

BOOK_ID = "b_mist"

BOOK_MIST = Book(
    id="b_mist",
    title="안개 궤도",
    author="—",
    total_offset=430,
    parts=[
        Part(id="p1", index=1, title="", start_offset=0, end_offset=199),
        Part(id="p2", index=2, title="은폐", start_offset=200, end_offset=430),
    ],
    chapters=[
        Chapter(id="ch1", part_id="p1", index=1, title="신호", start_offset=0, end_offset=99),
        Chapter(id="ch2", part_id="p1", index=2, title="균열", start_offset=100, end_offset=199),
        Chapter(id="ch3", part_id="p2", index=3, title="추적자들의 전조", start_offset=200, end_offset=430),
    ],
)

CHAPTER_CONTENT: dict[int, str] = {
    1: (
        "민우는 심야의 통제실에서 홀로 수신 로그를 넘기고 있었다. 잡음 사이로 낯선 규칙성이 스쳤다.\n\n"
        "서현이 커피 두 잔을 들고 들어와 옆자리에 앉았다. 두 사람은 오래된 동료 연구원이었다.\n\n"
        "화면 끝에서, 오래전 실종된 탐사선 아틀라스 호의 고유 신호가 희미하게 깜빡였다."
    ),
    2: (
        "신호는 매일 밤 조금씩 또렷해졌다. 민우는 좌표를 역산했고 서현은 로그를 백업했다.\n\n"
        "어느 새벽, 서현은 신호 헤더 속에서 낯익은 보안 서명 하나를 발견했다. 그것은 상부의 것이었다.\n\n"
        "두 사람은 자신들이 무엇을 건드렸는지 아직 알지 못했다."
    ),
    3: (
        "로그 차단이 끝난 지 얼마 지나지 않아 통제소 하부 출입문이 거칠게 열렸다. "
        "방전 마스크를 착용한 무장 요원들이 통로를 가로질러 들어섰다.\n\n"
        "그들 사이로 걸어 들어온 인물은 강 국장의 직속 집행관인 윤 팀장이였다. "
        "그는 민우의 콘솔 앞으로 다가가 스크린을 내려다봤다.\n\n"
        "서현은 태연하게 모니터를 가려 서며 백업 디스크를 주머니 깊은 곳으로 밀어 넣었다."
    ),
}


def chapter_with_content(index: int) -> Chapter:
    base = next(c for c in BOOK_MIST.chapters if c.index == index)
    return base.model_copy(update={"content": CHAPTER_CONTENT.get(index)})


# ── graph 픽스처 (청크 경계별 누적) ──────────────────────────────
_E_MINU = Entity(id="e_minu", name="민우", type="person", color="blue")
_E_SEOHYUN = Entity(id="e_seohyun", name="서현", type="person", color="blue")
_E_ATLAS = Entity(id="e_atlas", name="아틀라스 호", type="ship", color="blue")
_E_KANG = Entity(id="e_kang", name="강 국장", type="person", color="dark")
_E_YOON = Entity(id="e_yoon", name="윤 팀장", type="person", color="dark")

_R1 = Relationship(id="r1", source="e_minu", target="e_seohyun", label="동료 연구원", tone="ally",
                   description="통제실에서 함께 아틀라스 호 신호를 확인함.", revision_offset=40)
_R2 = Relationship(id="r2", source="e_minu", target="e_atlas", label="신호 추적", tone="neutral",
                   description="민우가 실종 탐사선의 고유 신호를 포착함.", revision_offset=120)
_R3 = Relationship(id="r3", source="e_seohyun", target="e_kang", label="은폐 의혹", tone="tense",
                   description="서현이 신호 속 강 국장의 보안 서명을 확인함.", revision_offset=260)
_R4A = Relationship(id="r4a", source="e_yoon", target="e_minu", label="압박 조사", tone="tense",
                    description="윤 팀장이 무장 요원들과 통제실에 진입함.", revision_offset=370)
_R4B = Relationship(id="r4b", source="e_yoon", target="e_seohyun", label="압박 조사", tone="tense",
                    description="윤 팀장이 무장 요원들과 통제실에 진입함.", revision_offset=370)

# 청크 c1(≤215): 개체3·관계2 / c2(≤320): +강국장,r3 / c3(≤380): +윤팀장,r4a,r4b
GRAPH_C1 = GraphJson(offset=215, spoiler_safe=True,
                     entities=[_E_MINU, _E_SEOHYUN, _E_ATLAS],
                     relationships=[_R1, _R2])
GRAPH_C2 = GraphJson(offset=320, spoiler_safe=True,
                     entities=[_E_MINU, _E_SEOHYUN, _E_ATLAS, _E_KANG],
                     relationships=[_R1, _R2, _R3])
GRAPH_C3 = GraphJson(offset=380, spoiler_safe=True,
                     entities=[_E_MINU, _E_SEOHYUN, _E_ATLAS, _E_KANG, _E_YOON],
                     relationships=[_R1, _R2, _R3, _R4A, _R4B])
GRAPH_EMPTY = GraphJson(offset=0, spoiler_safe=True, entities=[], relationships=[])


# ── reminders 픽스처 (경계별 누적) ──────────────────────────────
_RL_R1 = ReminderLine(text="민우와 서현은 통제실에서 아틀라스 호의 신호를 함께 확인했다.",
                      entity_ids=["e_minu", "e_seohyun"])
_RL_R2 = ReminderLine(text="민우가 실종 탐사선 아틀라스 호의 고유 신호를 포착했다.",
                      entity_ids=["e_minu", "e_atlas"])
_RL_R3 = ReminderLine(text="서현은 신호 속에서 강 국장의 보안 서명을 발견해 은폐 의혹을 품었다.",
                      entity_ids=["e_seohyun", "e_kang"])
_RL_R4 = ReminderLine(text="강 국장의 집행관 윤 팀장이 무장 요원들과 통제실에 진입해 압박을 시작했다.",
                      entity_ids=["e_yoon", "e_minu", "e_seohyun"])

REMINDERS_C1 = [_RL_R1, _RL_R2]
REMINDERS_C2 = [_RL_R1, _RL_R3]
REMINDERS_C3 = [_RL_R1, _RL_R3, _RL_R4]
