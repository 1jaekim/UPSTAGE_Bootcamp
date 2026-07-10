from backend.app.relation_presenter import apply_relationship_presentation
from backend.app.schemas import Entity, GraphJson, Relationship


def _entity(entity_id: str, name: str) -> Entity:
    return Entity(id=entity_id, name=name, type="person", color="blue")


def test_presenter_builds_korean_role_pair_from_structured_story_relation():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[
            _entity("e_stapleton", "스태플턴"),
            _entity("e_charles", "찰스 배스커빌 경"),
        ],
        relationships=[
            Relationship(
                id="r1",
                source="e_stapleton",
                target="e_charles",
                label="사건",
                tone="tense",
                description="원문 문장입니다. " * 50,
                revision_offset=100,
                relation_category="crime",
                relation_role="crime",
                is_story_relation=True,
                event_name="찰스 배스커빌 사망 사건",
                event_summary="스태플턴은 찰스 경의 죽음에 관여했다.",
                related_events=[
                    {
                        "event_name": "찰스 배스커빌 사망 사건",
                        "event_summary": "스태플턴은 찰스 경의 죽음에 관여했다.",
                        "evidence": "긴 원문 근거입니다. " * 40,
                    }
                ],
            )
        ],
    )

    presented = apply_relationship_presentation(graph)
    relationship = presented.relationships[0]

    assert relationship.role_pair_label == "가해자 → 피해자"
    assert relationship.display_label == "가해자 → 피해자"
    assert relationship.event_name == "찰스 배스커빌 사망 사건"
    assert "원문 문장입니다" not in relationship.relationship_summary
    assert "스태플턴" in relationship.relationship_summary
    assert len(relationship.evidence) == 2
    assert len(relationship.evidence[0]) <= 220
    assert "가해와 피해 맥락" not in relationship.relationship_summary
    assert "사건 관련 인물" not in relationship.relationship_summary


def test_presenter_separates_evidence_from_summary():
    raw_evidence = "모티머 박사가 소리쳤다. 그는 안경을 밀어올리며 길게 설명했다. " * 20
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_mortimer", "제임스 모티머"), _entity("e_holmes", "셜록 홈즈")],
        relationships=[
            Relationship(
                id="r1",
                source="e_mortimer",
                target="e_holmes",
                label="의뢰",
                tone="neutral",
                description=raw_evidence,
                revision_offset=100,
                relation_category="work",
                detail=raw_evidence,
            )
        ],
    )

    relationship = apply_relationship_presentation(graph).relationships[0]

    assert relationship.relationship_summary
    assert raw_evidence not in relationship.relationship_summary
    assert relationship.evidence
    assert "모티머 박사" in relationship.evidence[0]


def test_presenter_creates_short_legacy_summary():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_watson", "존 H. 왓슨"), _entity("e_henry", "헨리 배스커빌")],
        relationships=[
            Relationship(
                id="r1",
                source="e_watson",
                target="e_henry",
                label="동행",
                tone="ally",
                description="왓슨은 헨리와 동행했다.",
                revision_offset=100,
                relation_category="ally",
            )
        ],
    )

    relationship = apply_relationship_presentation(graph).relationships[0]

    assert relationship.role_pair_label == "조력자 → 동료"
    assert relationship.display_label == "동행"
    assert relationship.relationship_summary
    assert len(relationship.relationship_summary) < 180


def test_presenter_uses_specific_doctor_patient_context():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_mortimer", "제임스 모티머"), _entity("e_charles", "찰스 배스커빌 경")],
        relationships=[
            Relationship(
                id="r1",
                source="e_mortimer",
                target="e_charles",
                label="증언",
                tone="neutral",
                description="모티머 박사는 찰스 경의 주치의였고 그의 죽음을 이상하게 여겼다.",
                revision_offset=100,
                relation_category="mystery",
                event_name="찰스 배스커빌 사망 사건",
                event_summary="모티머 박사는 찰스 경의 주치의였고 그의 죽음을 이상하게 여겼다.",
            )
        ],
    )

    relationship = apply_relationship_presentation(graph).relationships[0]

    assert relationship.role_pair_label == "주치의 → 환자"
    assert "주치의" in relationship.relationship_summary
    assert "조사 대상" not in relationship.role_pair_label


def test_presenter_uses_specific_client_investigator_context():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_mortimer", "제임스 모티머"), _entity("e_holmes", "셜록 홈즈")],
        relationships=[
            Relationship(
                id="r1",
                source="e_mortimer",
                target="e_holmes",
                label="의뢰",
                tone="neutral",
                description="모티머는 홈즈에게 조사를 부탁했다.",
                revision_offset=100,
                relation_category="work",
                relation_role="work",
                event_name="배스커빌 사건 의뢰",
            )
        ],
    )

    relationship = apply_relationship_presentation(graph).relationships[0]

    assert relationship.role_pair_label == "의뢰인 → 조사자"
    assert "홈즈에게" in relationship.relationship_summary


def test_presenter_uses_specific_inheritance_context():
    graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_charles", "찰스 배스커빌 경"), _entity("e_henry", "헨리 배스커빌")],
        relationships=[
            Relationship(
                id="r1",
                source="e_charles",
                target="e_henry",
                label="상속",
                tone="neutral",
                description="찰스 경이 사망한 뒤 헨리가 재산과 작위를 상속했다.",
                revision_offset=100,
                relation_category="family",
                event_name="배스커빌 상속",
                event_summary="찰스 경이 사망한 뒤 헨리가 재산과 작위를 상속했다.",
            )
        ],
    )

    relationship = apply_relationship_presentation(graph).relationships[0]

    assert relationship.role_pair_label == "삼촌 → 상속인"
    assert "재산과 작위" in relationship.relationship_summary


def test_presenter_avoids_mechanical_labels_for_same_category_different_contexts():
    investigation_graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_holmes", "셜록 홈즈"), _entity("e_stapleton", "스태플턴")],
        relationships=[
            Relationship(
                id="r1",
                source="e_holmes",
                target="e_stapleton",
                label="조사",
                tone="neutral",
                description="홈즈는 스태플턴을 추적했다.",
                revision_offset=100,
                relation_category="investigation",
                relation_role="investigation",
                event_name="스태플턴 추적",
            )
        ],
    )
    protection_graph = GraphJson(
        offset=100,
        spoiler_safe=True,
        entities=[_entity("e_watson", "존 H. 왓슨"), _entity("e_henry", "헨리 배스커빌")],
        relationships=[
            Relationship(
                id="r2",
                source="e_watson",
                target="e_henry",
                label="보호",
                tone="ally",
                description="왓슨은 헨리를 보호하며 동행했다.",
                revision_offset=100,
                relation_category="protection",
                relation_role="protection",
                event_name="헨리 보호",
            )
        ],
    )

    investigation = apply_relationship_presentation(investigation_graph).relationships[0]
    protection = apply_relationship_presentation(protection_graph).relationships[0]

    assert investigation.role_pair_label == "조사자 → 용의자"
    assert protection.role_pair_label == "보호자 → 보호 대상"
    assert investigation.relationship_summary != protection.relationship_summary
    forbidden = ("조사 대상", "사건 관련 인물", "조사와 의심의 맥락")
    assert not any(phrase in investigation.relationship_summary for phrase in forbidden)
    assert not any(phrase in protection.relationship_summary for phrase in forbidden)
