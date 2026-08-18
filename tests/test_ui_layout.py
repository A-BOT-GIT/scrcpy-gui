from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.signals import default_state
from ui.cards import build_all_cards
from core.appearance import Appearance, CUSTOM_THEME, tokens_for
from ui.panels import CommandPanel
from ui.app_qss import build_qss


_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_cards_keep_controller_state_keys_and_mode_groups() -> None:
    _app()
    registered = {}
    cards = build_all_cards(lambda key, widget: registered.setdefault(key, widget), default_state())

    assert {"vcodec", "maxSize", "bitrate", "maxFps", "recPath", "recFmt"} <= registered.keys()
    assert "video_codec" not in registered
    assert cards["video"].kind == "basic"
    assert cards["record"].kind == "basic"
    assert cards["audio"].kind == "expert"


def test_command_panel_counts_log_lines() -> None:
    _app()
    panel = CommandPanel()
    panel.log.append_line("[设备] 发现 0 台设备")

    assert panel.log_header.badge.text() == "1 行"


def test_command_panel_recolors_existing_logs_for_light_theme() -> None:
    _app()
    panel = CommandPanel()
    panel.log.append_line("ERROR: connection failed")
    panel.set_theme_tokens(tokens_for(Appearance(CUSTOM_THEME, "#F8F8F8")))

    assert panel.log._colors["error"] == "#B91C1C"
    assert panel.log_header.label.text() == "实时日志"


def test_theme_contains_shell_card_and_right_panel_rules() -> None:
    qss = build_qss()

    assert "QWidget#window_shell" in qss
    assert "QWidget#device_bar, QWidget#card" in qss
    assert "QWidget#right" in qss
    assert 'font-family: "Courier New"' in qss
    assert "monospace" not in qss
    assert 'QWidget#app[maximized="true"]' in qss
    assert 'QWidget#window_shell[maximized="true"]' in qss
    assert "QWidget#command_section" in qss
    assert "QWidget#log_section" in qss
