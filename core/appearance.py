"""应用外观主题、颜色令牌与本地偏好存储。"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys


CONFIG_VERSION = 1
DEFAULT_THEME = "charcoal"
CUSTOM_THEME = "custom"
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class Appearance:
    """用户选择的应用级外观，不包含 scrcpy 参数或运行时状态。"""

    theme: str = DEFAULT_THEME
    custom_bg: str | None = None


@dataclass(frozen=True)
class ThemeTokens:
    """生成 QSS 的语义色令牌。"""

    name: str
    bg: str
    card: str
    panel: str
    bar: str
    text: str
    text_mid: str
    text_dim: str
    border: str
    border_hover: str
    accent: str
    accent_hover: str
    accent_ink: str
    disabled_bg: str
    disabled_text: str
    surface_hover: str
    checkbox_border: str
    selection: str
    selected_card: str


@dataclass(frozen=True)
class PresetTheme:
    key: str
    label: str
    bg: str
    panel: str
    card: str


PRESET_THEMES: tuple[PresetTheme, ...] = (
    PresetTheme("charcoal", "原版深炭", "#0f0f12", "#0a0a0d", "#16161a"),
    PresetTheme("graphite", "石墨", "#131316", "#0d0d10", "#1b1b20"),
    PresetTheme("midnight_blue", "深夜蓝", "#0e1418", "#080c0f", "#16202a"),
    PresetTheme("warm_night", "暖夜", "#1a1410", "#120d0a", "#241c16"),
    PresetTheme("violet_night", "紫夜", "#15131c", "#0d0c13", "#1e1b29"),
    PresetTheme("neutral_gray", "中性灰", "#18181b", "#101012", "#222227"),
)
_PRESET_BY_KEY = {theme.key: theme for theme in PRESET_THEMES}


def normalize_color(value: object) -> str | None:
    """将合法颜色规范为大写 #RRGGBB，不合法时返回 None。"""
    if not isinstance(value, str):
        return None
    color = value.strip()
    if not _HEX_COLOR.fullmatch(color):
        return None
    return color.upper()


def theme_label(theme: str) -> str:
    """返回主题的人类可读名称。"""
    if theme == CUSTOM_THEME:
        return "自定义"
    preset = _PRESET_BY_KEY.get(theme)
    return preset.label if preset else _PRESET_BY_KEY[DEFAULT_THEME].label


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _mix(base: str, overlay: str, overlay_ratio: float) -> str:
    """将 overlay 按比例混入 base。"""
    br, bg, bb = _rgb(base)
    or_, og, ob = _rgb(overlay)
    ratio = max(0.0, min(1.0, overlay_ratio))
    return _hex(
        (
            round(br + (or_ - br) * ratio),
            round(bg + (og - bg) * ratio),
            round(bb + (ob - bb) * ratio),
        )
    )


def _luminance(color: str) -> float:
    def channel(value: int) -> float:
        normalized = value / 255
        return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _dark_tokens(name: str, bg: str, panel: str, card: str) -> ThemeTokens:
    return ThemeTokens(
        name=name,
        bg=bg,
        card=card,
        panel=panel,
        bar=_mix(bg, "#000000", 0.12),
        text="#E8E8ED",
        text_mid="#D4D4DB",
        text_dim="#9CA3AF",
        border=_mix(card, "#E8E8ED", 0.16),
        border_hover=_mix(card, "#E8E8ED", 0.24),
        accent="#34D399",
        accent_hover="#4ADE80",
        accent_ink="#052E16",
        disabled_bg=_mix(bg, "#34D399", 0.10),
        disabled_text=_mix(bg, "#34D399", 0.18),
        surface_hover=_mix(card, "#FFFFFF", 0.06),
        checkbox_border=_mix(card, "#E8E8ED", 0.20),
        selection=_mix(bg, "#34D399", 0.12),
        selected_card=_mix(panel, "#34D399", 0.05),
    )


def _light_tokens(name: str, bg: str) -> ThemeTokens:
    return ThemeTokens(
        name=name,
        bg=bg,
        card=_mix(bg, "#FFFFFF", 0.44),
        panel=_mix(bg, "#000000", 0.08),
        bar=_mix(bg, "#000000", 0.14),
        text="#18181B",
        text_mid="#27272A",
        text_dim="#52525B",
        border=_mix(bg, "#18181B", 0.24),
        border_hover=_mix(bg, "#18181B", 0.38),
        accent="#047857",
        accent_hover="#059669",
        accent_ink="#ECFDF5",
        disabled_bg=_mix(bg, "#047857", 0.12),
        disabled_text=_mix(bg, "#18181B", 0.46),
        surface_hover=_mix(bg, "#FFFFFF", 0.62),
        checkbox_border=_mix(bg, "#18181B", 0.30),
        selection=_mix(bg, "#047857", 0.13),
        selected_card=_mix(bg, "#047857", 0.07),
    )


def tokens_for(appearance: Appearance) -> ThemeTokens:
    """返回外观对应的完整颜色令牌，输入异常时安全回退默认主题。"""
    if appearance.theme == CUSTOM_THEME:
        custom_bg = normalize_color(appearance.custom_bg)
        if custom_bg:
            if _luminance(custom_bg) >= 0.34:
                return _light_tokens("自定义", custom_bg)
            return _dark_tokens(
                "自定义",
                custom_bg,
                _mix(custom_bg, "#000000", 0.42),
                _mix(custom_bg, "#FFFFFF", 0.07),
            )

    preset = _PRESET_BY_KEY.get(appearance.theme) or _PRESET_BY_KEY[DEFAULT_THEME]
    if preset.key == DEFAULT_THEME:
        return ThemeTokens(
            name=preset.label,
            bg="#0F0F12",
            card="#16161A",
            panel="#0A0A0D",
            bar="#0E0E11",
            text="#E8E8ED",
            text_mid="#D4D4DB",
            text_dim="#9CA3AF",
            border="#3A3A45",
            border_hover="#4A4A55",
            accent="#34D399",
            accent_hover="#4ADE80",
            accent_ink="#052E16",
            disabled_bg="#1A2E22",
            disabled_text="#52525B",
            surface_hover="#222228",
            checkbox_border="#3F3F46",
            selection="#1F2A24",
            selected_card="#0A0D0A",
        )
    return _dark_tokens(preset.label, preset.bg, preset.panel, preset.card)


def appearance_path() -> Path:
    """返回应用外观配置文件路径。"""
    if getattr(sys, "frozen", False):
        return Path.home() / ".scrcpy-gui" / "appearance.json"
    return Path(__file__).resolve().parents[1] / "appearance.json"


class AppearanceStore:
    """外观配置的单一读写入口。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else appearance_path()

    def load(self) -> Appearance:
        try:
            with self._path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
        except (OSError, json.JSONDecodeError):
            return Appearance()
        if not isinstance(raw, dict) or raw.get("version") != CONFIG_VERSION:
            return Appearance()

        theme = raw.get("theme")
        if theme in _PRESET_BY_KEY:
            return Appearance(theme=theme)
        if theme == CUSTOM_THEME:
            custom_bg = normalize_color(raw.get("custom_bg"))
            if custom_bg:
                return Appearance(theme=CUSTOM_THEME, custom_bg=custom_bg)
        return Appearance()

    def save(self, appearance: Appearance) -> bool:
        if appearance.theme in _PRESET_BY_KEY:
            record = {"version": CONFIG_VERSION, "theme": appearance.theme, "custom_bg": None}
        elif appearance.theme == CUSTOM_THEME and normalize_color(appearance.custom_bg):
            record = {
                "version": CONFIG_VERSION,
                "theme": CUSTOM_THEME,
                "custom_bg": normalize_color(appearance.custom_bg),
            }
        else:
            return False

        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(record, file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temporary, self._path)
            return True
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return False
