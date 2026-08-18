from __future__ import annotations

import json

from core.appearance import (
    Appearance,
    AppearanceStore,
    CUSTOM_THEME,
    DEFAULT_THEME,
    normalize_color,
    tokens_for,
)


def test_default_theme_preserves_existing_palette() -> None:
    tokens = tokens_for(Appearance())

    assert tokens.bg == "#0F0F12"
    assert tokens.card == "#16161A"
    assert tokens.panel == "#0A0A0D"
    assert tokens.accent == "#34D399"


def test_custom_light_background_uses_dark_readable_tokens() -> None:
    tokens = tokens_for(Appearance(CUSTOM_THEME, "#F4F1EA"))

    assert tokens.bg == "#F4F1EA"
    assert tokens.text == "#18181B"
    assert tokens.accent == "#047857"


def test_normalize_color_rejects_invalid_values() -> None:
    assert normalize_color("#abc123") == "#ABC123"
    assert normalize_color("#1234") is None
    assert normalize_color("blue") is None
    assert normalize_color(None) is None


def test_store_round_trip_and_invalid_config_fallback(tmp_path) -> None:
    path = tmp_path / "appearance.json"
    store = AppearanceStore(path)
    selected = Appearance(CUSTOM_THEME, "#ABC123")

    assert store.save(selected) is True
    assert store.load() == selected

    path.write_text(json.dumps({"version": 1, "theme": CUSTOM_THEME, "custom_bg": "bad"}), encoding="utf-8")
    assert store.load() == Appearance(DEFAULT_THEME)
