from agents.verifier_agent import (
    _apply_character_name_map,
    _augment_identity_map_with_alias_rules,
)
from agents.character_aliases import load_character_alias_map


def test_load_default_character_alias_map():
    alias_map = load_character_alias_map(None)

    assert alias_map["셜록 홈스"] == "셜록 홈즈"
    assert alias_map["홈즈"] == "셜록 홈즈"
    assert alias_map["왓슨 박사"] == "존 H. 왓슨"


def test_load_book_character_alias_map_merges_default_and_book_specific_aliases():
    alias_map = load_character_alias_map("3fb1a332-ae08-450b-8b20-3567a4da4180")

    assert alias_map["셜록 홈스"] == "셜록 홈즈"
    assert alias_map["나(화자)"] == "존 H. 왓슨"
    assert alias_map["화자(왓슨)"] == "존 H. 왓슨"


def test_json_alias_map_resolves_names_before_llm_alias_rules():
    alias_map = load_character_alias_map("3fb1a332-ae08-450b-8b20-3567a4da4180")
    build_result = {
        "characters": [
            {"name": "셜록 홈스", "description": "탐정", "evidence": "셜록 홈스가 말했다."},
            {"name": "나(화자)", "description": "사건의 기록자", "evidence": "나는 홈즈와 만났다."},
        ],
        "relations": [
            {"source": "홈즈", "target": "화자(왓슨)", "relation": "동행", "evidence": "함께 움직였다."},
        ],
        "events": [
            {"summary": "조사 시작", "participants": ["셜록", "나(화자)"], "evidence": "조사가 시작되었다."},
        ],
    }

    _, characters, relations, events = _apply_character_name_map(build_result, alias_map)

    assert [character["name"] for character in characters] == ["셜록 홈즈", "존 H. 왓슨"]
    assert relations[0]["source"] == "셜록 홈즈"
    assert relations[0]["target"] == "존 H. 왓슨"
    assert events[0]["participants"] == ["셜록 홈즈", "존 H. 왓슨"]


def test_alias_rules_merge_sherlock_variants():
    characters = [
        {"name": "셜록 홈스", "description": "베이커가의 탐정", "evidence": "셜록 홈스가 말했다."},
        {"name": "셜록 홈즈", "description": "왓슨의 동료 탐정", "evidence": "셜록 홈즈와 왓슨"},
        {"name": "홈즈", "description": "탐정", "evidence": "홈즈가 의자를 밀었다."},
        {"name": "셜록", "description": "탐정", "evidence": "셜록은 단서를 보았다."},
        {"name": "나(셜록)", "description": "셜록을 가리키는 표기", "evidence": "나(셜록)는 말했다."},
    ]
    identity_map = {c["name"]: c["name"] for c in characters}

    name_map = _augment_identity_map_with_alias_rules(characters, identity_map)

    assert {name_map[c["name"]] for c in characters} == {"셜록 홈즈"}


def test_alias_rules_do_not_merge_family_role_names():
    characters = [
        {"name": "왓슨", "description": "홈즈의 동료 의사", "evidence": "왓슨이 말했다."},
        {"name": "왓슨 부인", "description": "왓슨의 아내", "evidence": "왓슨 부인이 말했다."},
    ]
    identity_map = {c["name"]: c["name"] for c in characters}

    name_map = _augment_identity_map_with_alias_rules(characters, identity_map)

    assert name_map["왓슨"] == "왓슨"
    assert name_map["왓슨 부인"] == "왓슨 부인"


def test_alias_rules_merge_watson_narrator_variants():
    characters = [
        {"name": "존 H. 왓슨", "description": "홈즈의 동료 의사", "evidence": "존 H. 왓슨"},
        {"name": "화자(왓슨)", "description": "사건을 서술하는 홈즈의 동료", "evidence": "화자(왓슨)"},
        {"name": "나(화자)", "description": "홈즈와 동행하는 의사", "evidence": "나는 홈즈와 함께 갔다."},
    ]
    identity_map = {c["name"]: c["name"] for c in characters}

    name_map = _augment_identity_map_with_alias_rules(characters, identity_map)

    assert {name_map[c["name"]] for c in characters} == {"존 H. 왓슨"}


def test_apply_name_map_deduplicates_relations_after_merge():
    build_result = {
        "characters": [
            {"name": "셜록 홈즈", "description": "탐정", "evidence": "셜록 홈즈"},
            {"name": "홈즈", "description": "탐정", "evidence": "홈즈"},
            {"name": "왓슨", "description": "의사", "evidence": "왓슨"},
        ],
        "relations": [
            {"source": "셜록 홈즈", "target": "왓슨", "relation": "동료", "evidence": "함께 조사"},
            {"source": "홈즈", "target": "왓슨", "relation": "동료", "evidence": "함께 조사"},
        ],
        "events": [
            {"summary": "조사", "participants": ["홈즈", "왓슨"], "evidence": "조사했다"},
            {"summary": "조사", "participants": ["셜록 홈즈", "왓슨"], "evidence": "조사했다"},
        ],
    }

    _, characters, relations, events = _apply_character_name_map(
        build_result,
        {"셜록 홈즈": "셜록 홈즈", "홈즈": "셜록 홈즈", "왓슨": "왓슨"},
    )

    assert [c["name"] for c in characters] == ["셜록 홈즈", "왓슨"]
    assert len(relations) == 1
    assert relations[0]["source"] == "셜록 홈즈"
    assert len(events) == 1
    assert events[0]["participants"] == ["셜록 홈즈", "왓슨"]


def test_apply_name_map_resolves_relation_only_aliases():
    build_result = {
        "characters": [
            {"name": "셜록 홈즈", "description": "탐정", "evidence": "셜록 홈즈"},
            {"name": "존 H. 왓슨", "description": "의사", "evidence": "존 H. 왓슨"},
        ],
        "relations": [
            {"source": "셜록 홈스", "target": "왓슨 박사", "relation": "동료", "evidence": "함께 조사"},
        ],
        "events": [
            {"summary": "조사", "participants": ["홈즈", "화자(왓슨)"], "evidence": "조사했다"},
        ],
    }

    _, _, relations, events = _apply_character_name_map(
        build_result,
        {"셜록 홈즈": "셜록 홈즈", "존 H. 왓슨": "존 H. 왓슨"},
    )

    assert relations[0]["source"] == "셜록 홈즈"
    assert relations[0]["target"] == "존 H. 왓슨"
    assert events[0]["participants"] == ["셜록 홈즈", "존 H. 왓슨"]
