from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ALIAS_DIR = Path(__file__).resolve().parent.parent / "backend" / "data" / "character_aliases"


def _load_alias_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    alias_map: dict[str, str] = {}
    characters = data.get("characters", [])
    if not isinstance(characters, list):
        return alias_map

    for character in characters:
        if not isinstance(character, dict):
            continue

        canonical_name = _clean_name(character.get("canonical_name"))
        if not canonical_name:
            continue

        alias_map[canonical_name] = canonical_name
        aliases = character.get("aliases", [])
        if not isinstance(aliases, list):
            continue

        for alias in aliases:
            alias_name = _clean_name(alias)
            if alias_name:
                alias_map[alias_name] = canonical_name

    return alias_map


def _clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def load_character_alias_map(book_id: str | None) -> dict[str, str]:
    """Load default aliases, then book-specific aliases if present.

    The returned mapping is always alias -> canonical_name. Missing files or
    malformed entries are ignored so the existing verifier flow keeps working.
    """
    alias_map = _load_alias_file(ALIAS_DIR / "default.json")

    if book_id:
        alias_map.update(_load_alias_file(ALIAS_DIR / f"{book_id}.json"))

    return alias_map
