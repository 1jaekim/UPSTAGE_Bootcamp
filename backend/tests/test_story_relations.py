from backend.app.content_source import AgentResultSource
from backend.app.precompute import _remap_position_value_to_global_index
from backend.app.schemas import Entity, GraphJson, Relationship, ReminderLine
from agents.build_agent import merge_events


BOOK_ID = "29f8f4f6-1cff-4b13-95e3-5405a19f8b11"


def _entity(entity_id: str, name: str) -> Entity:
    return Entity(id=entity_id, name=name, type="person", color="blue")


def _relationship(
    relationship_id: str,
    source: str,
    target: str,
    label: str,
    description: str,
    revision_offset: int = 100,
    **extra,
) -> Relationship:
    return Relationship(
        id=relationship_id,
        source=source,
        target=target,
        label=label,
        tone="neutral",
        description=description,
        revision_offset=revision_offset,
        **extra,
    )


def _source(graph: GraphJson, reminders: list[ReminderLine], boundary: int = 100) -> AgentResultSource:
    return AgentResultSource({(BOOK_ID, boundary): {"graph": graph, "reminders": reminders}})


def test_reminder_only_pairs_without_original_relation_are_hidden():
    """"같은 문장에 같이 언급됐다"는 것만으로 만든 약한 추측성 관계(리마인드
    조합)는 원본 relations도, 구조화된 사건도 없으면 화면에서 숨긴다. 반면
    원본 relations에 실제로 있는 쌍(홈즈-왓슨)은 계속 노출되고, 리마인드에서
    나온 부가 정보로 importance 등이 보강된다.
    """
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes", "셜록 홈즈"),
            _entity("e_watson", "존 H. 왓슨"),
            _entity("e_stapleton", "스태플턴"),
        ],
        relationships=[
            _relationship("r1", "e_holmes", "e_watson", "동료", "홈즈와 왓슨은 함께 움직인다."),
        ],
    )
    reminders = [
        ReminderLine(
            text="셜록 홈즈와 존 H. 왓슨은 스태플턴을 조사하고 추적했다.",
            entity_ids=["e_holmes", "e_watson", "e_stapleton"],
        )
    ]

    normalized_graph = _source(graph, reminders).get_graph(BOOK_ID, 100, reveal_all=False)
    pairs = {frozenset((r.source, r.target)) for r in normalized_graph.relationships}

    # 홈즈-스태플턴, 왓슨-스태플턴은 원본 관계도 사건도 없는 순수 추측성 쌍이라 숨겨진다.
    assert frozenset(("e_holmes", "e_stapleton")) not in pairs
    assert frozenset(("e_watson", "e_stapleton")) not in pairs
    # 홈즈-왓슨은 원본 관계가 있으므로 그대로 노출되고, 라벨도 원본("동료")을 유지한다.
    assert frozenset(("e_holmes", "e_watson")) in pairs
    holmes_watson = next(
        r for r in normalized_graph.relationships if frozenset((r.source, r.target)) == frozenset(("e_holmes", "e_watson"))
    )
    assert holmes_watson.display_label == "동료"


def test_summary_preserves_multiple_relations_in_detail_and_related_events():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes", "셜록 홈즈"),
            _entity("e_stapleton", "스태플턴"),
        ],
        relationships=[
            _relationship("r1", "e_holmes", "e_stapleton", "의심", "홈즈는 스태플턴을 의심한다."),
            _relationship("r2", "e_holmes", "e_stapleton", "추적", "홈즈는 스태플턴의 행적을 추적한다."),
        ],
    )
    reminders = [
        ReminderLine(
            text="셜록 홈즈는 스태플턴을 조사하고 사건의 단서를 찾았다.",
            entity_ids=["e_holmes", "e_stapleton"],
        )
    ]

    normalized_graph = _source(graph, reminders).get_graph(BOOK_ID, 100, reveal_all=False)

    assert len(normalized_graph.relationships) == 1
    relationship = normalized_graph.relationships[0]
    assert relationship.is_story_relation
    assert "의심한다" in relationship.detail
    assert "행적을 추적" in relationship.detail
    assert relationship.related_events
    assert any("조사하고 사건의 단서" in event["event_summary"] for event in relationship.related_events)


def test_future_story_relationship_is_not_exposed_before_boundary():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes", "셜록 홈즈"),
            _entity("e_stapleton", "스태플턴"),
        ],
        relationships=[
            _relationship(
                "r_future",
                "e_holmes",
                "e_stapleton",
                "폭로",
                "미래 위치에서 밝혀지는 관계다.",
                revision_offset=200,
                first_seen_global_index=200,
                is_story_relation=True,
                relation_category="investigation",
            ),
        ],
    )

    normalized_graph = _source(graph, []).get_graph(BOOK_ID, 100, reveal_all=False)

    assert normalized_graph.relationships == []


def test_alias_and_generic_filter_apply_even_when_relations_are_hidden():
    """별칭 정규화("홈즈"→"셜록 홈즈")와 일반명사 필터("의사" 제외)는 관계 유무와
    무관하게 인물(entity) 목록에 그대로 적용된다. 이 케이스는 원본 관계도, 구조화된
    사건도 없는 순수 리마인드 조합뿐이라 관계 자체는 전부 숨겨진다.
    """
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes_alias", "홈즈"),
            _entity("e_watson", "왓슨"),
            _entity("e_stapleton", "스태플턴"),
            _entity("e_doctor", "의사"),
        ],
        relationships=[],
    )
    reminders = [
        ReminderLine(
            text="홈즈와 왓슨은 의사를 지나 스태플턴을 조사했다.",
            entity_ids=["e_holmes_alias", "e_watson", "e_doctor", "e_stapleton"],
        )
    ]

    normalized_graph = _source(graph, reminders).get_graph(BOOK_ID, 100, reveal_all=False)
    names = {entity.name for entity in normalized_graph.entities}

    assert "셜록 홈즈" in names
    assert "존 H. 왓슨" in names
    assert "의사" not in names
    assert normalized_graph.relationships == []


def test_structured_event_creates_perpetrator_victim_relation():
    graph = GraphJson(
        offset=300,
        spoiler_safe=True,
        entities=[
            _entity("e_stapleton", "스태플턴"),
            _entity("e_charles", "찰스 배스커빌 경"),
        ],
        relationships=[],
        events=[
            {
                "event_id": "ev_charles_death",
                "event_name": "찰스 배스커빌 사망",
                "event_summary": "스태플턴이 찰스 배스커빌 경의 죽음에 관여했다.",
                "participants": [
                    {"character_name": "스태플턴", "role": "perpetrator", "confidence": 0.9},
                    {"character_name": "찰스 배스커빌 경", "role": "victim", "confidence": 0.9},
                ],
                "evidence": "스태플턴의 범행이 드러났다.",
                "first_seen_global_index": 280,
                "last_seen_global_index": 300,
            }
        ],
    )

    normalized_graph = _source(graph, [], boundary=300).get_graph(BOOK_ID, 300, reveal_all=False)
    relationship = normalized_graph.relationships[0]

    assert relationship.source == "e_stapleton"
    assert relationship.target == "e_charles"
    assert relationship.relation_category == "crime"
    assert relationship.relation_role == "crime"
    assert relationship.is_story_relation
    assert relationship.related_events[0]["event_id"] == "ev_charles_death"


def test_structured_event_creates_investigator_suspect_relation():
    graph = GraphJson(
        offset=300,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes", "셜록 홈즈"),
            _entity("e_stapleton", "스태플턴"),
        ],
        relationships=[],
        events=[
            {
                "event_id": "ev_investigation",
                "event_name": "스태플턴 조사",
                "event_summary": "홈즈가 스태플턴을 용의자로 보고 추적했다.",
                "participants": [
                    {"character_name": "셜록 홈즈", "role": "investigator", "confidence": 0.9},
                    {"character_name": "스태플턴", "role": "suspect", "confidence": 0.8},
                ],
                "evidence": "홈즈가 스태플턴을 추적했다.",
                "first_seen_global_index": 300,
                "last_seen_global_index": 300,
            }
        ],
    )

    normalized_graph = _source(graph, [], boundary=300).get_graph(BOOK_ID, 300, reveal_all=False)
    relationship = normalized_graph.relationships[0]

    assert relationship.source == "e_holmes"
    assert relationship.target == "e_stapleton"
    assert relationship.relation_category == "investigation"
    assert relationship.relation_role == "investigation"


def test_structured_event_creates_deception_relation():
    graph = GraphJson(
        offset=300,
        spoiler_safe=True,
        entities=[
            _entity("e_stapleton", "스태플턴"),
            _entity("e_lyons", "로라 라이언스 부인"),
        ],
        relationships=[],
        events=[
            {
                "event_id": "ev_lyons_deceived",
                "event_name": "라이언스 부인 기만",
                "event_summary": "스태플턴은 로라 라이언스 부인을 속였다.",
                "participants": [
                    {"character_name": "스태플턴", "role": "deceiver", "confidence": 0.9},
                    {"character_name": "로라 라이언스 부인", "role": "deceived", "confidence": 0.9},
                ],
                "evidence": "라이언스 부인이 기만당한 사실이 드러났다.",
                "first_seen_global_index": 300,
                "last_seen_global_index": 300,
            }
        ],
    )

    normalized_graph = _source(graph, [], boundary=300).get_graph(BOOK_ID, 300, reveal_all=False)
    relationship = normalized_graph.relationships[0]

    assert relationship.source == "e_stapleton"
    assert relationship.target == "e_lyons"
    assert relationship.relation_category == "deception"
    assert relationship.relation_role == "deception"


def test_merge_events_updates_existing_event_instead_of_duplicating():
    merged = merge_events(
        [
            {
                "event_name": "찰스 배스커빌 사망",
                "event_summary": "찰스 배스커빌 경이 사망했다.",
                "participants": [{"character_name": "찰스 배스커빌 경", "role": "victim"}],
                "first_seen_chunk_offset": 10,
                "last_seen_chunk_offset": 10,
            },
            {
                "event_name": "찰스 배스커빌 사망",
                "event_summary": "찰스 배스커빌 경의 사망 사건이 다시 언급된다.",
                "participants": [
                    {"character_name": "찰스 배스커빌 경", "role": "victim"},
                    {"character_name": "스태플턴", "role": "suspect"},
                ],
                "first_seen_chunk_offset": 20,
                "last_seen_chunk_offset": 20,
            },
        ]
    )

    assert len(merged) == 1
    assert merged[0]["first_seen_chunk_offset"] == 10
    assert merged[0]["last_seen_chunk_offset"] == 20
    assert {participant["role"] for participant in merged[0]["participants"]} == {"victim", "suspect"}


def test_structured_future_event_is_blocked_by_boundary():
    graph = GraphJson(
        offset=300,
        spoiler_safe=True,
        entities=[
            _entity("e_stapleton", "스태플턴"),
            _entity("e_charles", "찰스 배스커빌 경"),
        ],
        relationships=[],
        events=[
            {
                "event_id": "ev_future",
                "event_name": "미래 폭로",
                "event_summary": "아직 읽지 않은 위치에서 밝혀지는 사건이다.",
                "participants": [
                    {"character_name": "스태플턴", "role": "perpetrator"},
                    {"character_name": "찰스 배스커빌 경", "role": "victim"},
                ],
                "first_seen_global_index": 500,
                "last_seen_global_index": 500,
            }
        ],
    )

    normalized_graph = _source(graph, [], boundary=300).get_graph(BOOK_ID, 300, reveal_all=False)

    assert normalized_graph.relationships == []


def test_structured_event_alias_and_generic_filter_before_relation_generation():
    graph = GraphJson(
        offset=300,
        spoiler_safe=True,
        entities=[
            _entity("e_holmes", "홈즈"),
            _entity("e_stapleton", "스태플턴"),
            _entity("e_doctor", "의사"),
        ],
        relationships=[],
        events=[
            {
                "event_id": "ev_alias",
                "event_name": "용의자 조사",
                "event_summary": "홈즈가 의사를 지나 스태플턴을 조사했다.",
                "participants": [
                    {"character_name": "홈즈", "role": "investigator"},
                    {"character_name": "의사", "role": "witness"},
                    {"character_name": "스태플턴", "role": "suspect"},
                ],
                "first_seen_global_index": 300,
                "last_seen_global_index": 300,
            }
        ],
    )

    normalized_graph = _source(graph, [], boundary=300).get_graph(BOOK_ID, 300, reveal_all=False)
    names = {entity.name for entity in normalized_graph.entities}
    relationship = normalized_graph.relationships[0]

    assert "셜록 홈즈" in names
    assert "의사" not in names
    assert relationship.source == "e_holmes"
    assert relationship.target == "e_stapleton"
    assert relationship.relation_category == "investigation"


def test_precompute_can_map_event_chunk_offsets_to_global_index():
    mapping = {10: 101, 20: 205}

    assert _remap_position_value_to_global_index(10, mapping) == 101
    assert _remap_position_value_to_global_index(20, mapping) == 205
