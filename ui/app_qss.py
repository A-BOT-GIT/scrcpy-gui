"""原生窗口主题 QSS，由应用外观令牌驱动。"""
from __future__ import annotations

from core.appearance import Appearance, tokens_for


def build_qss(tokens=None) -> str:
    tokens = tokens or tokens_for(Appearance())
    return f"""
QWidget {{
    color: {tokens.text};
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QWidget#app {{ background: {tokens.panel}; }}
QWidget#app[maximized="true"] {{ background: {tokens.bg}; }}
QWidget#window_shell {{
    background: {tokens.bg};
    border: 1px solid {tokens.border};
    border-radius: 12px;
}}
QWidget#window_shell[maximized="true"] {{ border: none; border-radius: 0; }}
QWidget#title_bar {{
    background: {tokens.bar};
    border-bottom: 1px solid {tokens.border};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QWidget#window_shell[maximized="true"] QWidget#title_bar {{
    border-top-left-radius: 0;
    border-top-right-radius: 0;
}}
QLabel#dot {{ border-radius: 6px; }}
QLabel#title_text {{ color: {tokens.text}; font-size: 14px; font-weight: 600; }}
QLabel#ver_text {{ color: {tokens.text_dim}; font-size: 12px; }}
QPushButton#title_btn {{
    background: transparent; border: none; border-radius: 6px; color: {tokens.text_dim};
    font-size: 15px; padding: 0;
}}
QPushButton#title_btn:hover {{ background: {tokens.surface_hover}; color: {tokens.text}; }}
QPushButton#appearance_trigger {{
    background: transparent; border: 1px solid {tokens.border}; border-radius: 6px;
    color: {tokens.text_dim}; min-height: 28px; padding: 0 10px; font-size: 12px;
}}
QPushButton#appearance_trigger:hover,
QPushButton#appearance_trigger:focus {{
    background: {tokens.surface_hover}; border-color: {tokens.border_hover}; color: {tokens.text};
}}
QWidget#banner {{
    background: rgba(248,113,113,0.12); border-bottom: 1px solid #F87171; color: #F87171;
}}
QPushButton#banner_close {{ background: transparent; border: none; color: #F87171; font-size: 16px; }}

QWidget#device_bar, QWidget#card {{
    background: {tokens.card}; border: 1px solid {tokens.border}; border-radius: 10px;
}}
QLabel#db_title {{
    color: {tokens.text_dim}; font-weight: 600; font-size: 12px;
}}
QWidget#segmented, QWidget#seg_wrap {{
    background: {tokens.panel}; border: 1px solid {tokens.border}; border-radius: 8px;
}}
QPushButton#seg_item {{
    background: transparent; border: none; border-radius: 6px; color: {tokens.text_dim};
    min-height: 30px; padding: 0 18px;
}}
QPushButton#seg_item:hover {{ color: {tokens.text}; }}
QPushButton#seg_item:checked {{
    background: {tokens.accent}; color: {tokens.accent_ink}; font-weight: 600;
}}
QPushButton {{
    background: transparent; border: 1px solid {tokens.border}; border-radius: 8px;
    color: {tokens.text}; min-height: 32px; padding: 0 12px;
}}
QPushButton:hover {{ background: {tokens.surface_hover}; border-color: {tokens.border_hover}; }}
QPushButton:pressed {{ background: {tokens.panel}; }}
QPushButton:disabled {{
    background: {tokens.disabled_bg}; border-color: {tokens.border}; color: {tokens.disabled_text};
}}
QPushButton#auto_wifi, QPushButton#launch_btn {{
    background: {tokens.accent}; border-color: {tokens.accent}; color: {tokens.accent_ink}; font-weight: 600;
}}
QPushButton#auto_wifi:hover, QPushButton#launch_btn:hover {{
    background: {tokens.accent_hover}; border-color: {tokens.accent_hover};
}}
QPushButton#stop_btn {{
    border-color: #EF4444; color: {tokens.text}; background: transparent;
}}
QPushButton#stop_btn:hover {{ border-color: #F87171; color: #F87171; }}
QPushButton#btn_secondary, QPushButton.btn_secondary {{
    background: transparent; border-color: {tokens.border}; color: {tokens.text};
}}
QPushButton#btn_ghost {{ background: transparent; border-color: {tokens.border}; color: {tokens.text_dim}; }}
QPushButton#btn_danger_text {{ background: transparent; border-color: transparent; color: #F87171; }}

QComboBox, QLineEdit {{
    background: {tokens.panel}; border: 1px solid {tokens.border}; border-radius: 8px;
    color: {tokens.text}; min-height: 20px; padding: 6px 10px;
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {tokens.border_hover}; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {tokens.accent}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {tokens.card}; color: {tokens.text}; border: 1px solid {tokens.border};
    selection-background-color: {tokens.selection};
}}
QCheckBox {{ color: {tokens.text_mid}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid {tokens.checkbox_border};
    background: {tokens.panel};
}}
QCheckBox::indicator:checked {{ background: {tokens.accent}; border-color: {tokens.accent}; }}
QLabel#toolbar_label, QLabel#preset_label, QLabel#fieldLabel {{ color: {tokens.text_mid}; }}
QLabel#hint {{ color: {tokens.text_dim}; font-size: 12px; }}
QLabel#cardTitle {{ color: {tokens.text}; font-size: 14px; font-weight: 600; }}

QScrollArea#left_scroll {{ border: none; background: transparent; }}
QWidget#scroll_content {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 13px 0 4px 0; }}
QScrollBar::handle:vertical {{ background: {tokens.border}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {tokens.border_hover}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QWidget#right {{ background: {tokens.card}; border-left: 1px solid {tokens.border}; }}
QWidget#command_section {{ background: {tokens.card}; }}
QWidget#panel_header {{
    background: transparent;
}}
QLabel#panel_h {{ color: {tokens.text}; font-size: 14px; font-weight: 600; }}
QLabel#panel_badge {{
    color: {tokens.accent}; background: {tokens.selection}; border: 1px solid {tokens.accent};
    border-radius: 10px; padding: 2px 8px; font-family: "Courier New"; font-size: 11px;
}}
QLabel#cmd_caption {{
    color: {tokens.text_dim}; margin: 0 18px 8px; font-size: 11px; font-weight: 600;
}}
QLabel#cmd {{
    background: {tokens.panel}; border: 1px solid {tokens.border}; border-radius: 8px;
    margin: 0 18px; padding: 10px 12px; color: {tokens.accent};
    font-family: "Courier New"; font-size: 12px;
}}
QWidget#log_section {{ background: {tokens.card}; border-top: 1px solid {tokens.border}; }}
QTextEdit#log {{
    background: {tokens.bg}; border: 1px solid {tokens.border}; border-radius: 8px;
    margin: 0 14px; padding: 10px 12px; color: {tokens.text_mid};
    font-family: "Courier New"; font-size: 12px;
}}
QWidget#statusbar {{
    background: {tokens.bar}; border-top: 1px solid {tokens.border};
    border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;
}}
QLabel#run_label {{ color: {tokens.text_dim}; }}
QWidget#statusbar[running="true"] QLabel#run_label,
QWidget#statusbar[running="true"] QLabel#run_dot {{ color: {tokens.accent}; }}
QWidget#toast {{
    background: {tokens.card}; border: 1px solid {tokens.accent}; border-radius: 8px; padding: 8px 12px;
}}

QFrame#appearance_popup {{
    background: {tokens.card}; border: 1px solid {tokens.border}; border-radius: 10px;
}}
QLabel#appearance_title {{ color: {tokens.text}; font-size: 14px; font-weight: 600; }}
QLabel#appearance_hint {{ color: {tokens.text_dim}; font-size: 12px; }}
QPushButton#appearance_custom {{
    background: transparent; border: 1px solid {tokens.border}; border-radius: 6px;
    color: {tokens.text_mid}; min-height: 32px; padding: 0 10px; text-align: left;
}}
QPushButton#appearance_custom:hover,
QPushButton#appearance_custom:focus {{
    border-color: {tokens.border_hover}; background: {tokens.surface_hover}; color: {tokens.text};
}}

QDialog {{ background: {tokens.bg}; color: {tokens.text}; }}
QDialog#manage_dialog, QDialog#edit_dialog {{
    background: {tokens.card}; border: 1px solid {tokens.border}; border-radius: 10px;
}}
QWidget#dialog_header {{
    background: {tokens.bar}; border-bottom: 1px solid {tokens.border};
    border-top-left-radius: 10px; border-top-right-radius: 10px;
}}
QLabel#dlg_title {{ color: {tokens.text}; font-size: 14px; font-weight: 600; }}
QLabel#dlg_subtitle, QLabel#dlg_label, QLabel#fld_label {{ color: {tokens.text_dim}; font-size: 12px; }}
QLabel#dialog_notice {{ color: {tokens.text_dim}; font-size: 12px; min-height: 18px; }}
QLabel#dialog_notice[severity="error"] {{ color: #F87171; }}
QLabel#dialog_notice[severity="success"] {{ color: {tokens.accent}; }}
QScrollArea#preset_list, QScrollArea#preset_editor_scroll {{ border: none; background: transparent; }}
QWidget#preset_list_content {{ background: transparent; }}
QWidget#preset_row {{
    background: {tokens.bg}; border: 1px solid {tokens.border}; border-radius: 8px;
}}
QWidget#preset_row[active="true"] {{ background: {tokens.selected_card}; border-color: {tokens.accent}; }}
QLabel#preset_row_title {{ color: {tokens.text}; font-weight: 600; }}
QLabel#preset_row_meta {{ color: {tokens.text_dim}; font-size: 11px; }}
QLabel#preset_active_badge {{
    color: {tokens.accent}; background: {tokens.selection}; border-radius: 8px; padding: 2px 6px; font-size: 10px;
}}
QWidget#preset_compose {{ border-top: 1px solid {tokens.border}; background: {tokens.card}; }}
QPushButton#preset_edit {{ background: transparent; border-color: {tokens.border}; color: {tokens.text}; }}
QPushButton#preset_copy {{ background: transparent; border-color: transparent; color: {tokens.text_dim}; }}
QPushButton#preset_delete {{ background: transparent; border-color: transparent; color: #F87171; }}
QPushButton#preset_delete:hover {{ background: rgba(248,113,113,0.12); border-color: rgba(248,113,113,0.28); }}
QPushButton#preset_group_toggle {{
    background: transparent; border-color: {tokens.border}; color: {tokens.text_mid}; text-align: left;
}}
QPushButton#preset_group_toggle:checked {{
    background: {tokens.selection}; border-color: {tokens.accent}; color: {tokens.text}; font-weight: 600;
}}
QWidget#dlg_group_card {{
    background: {tokens.bg}; border: 1px solid {tokens.border}; border-radius: 8px;
}}
QWidget#dlg_group_card[checked="true"] {{
    background: {tokens.selected_card}; border-color: {tokens.accent};
}}
"""
