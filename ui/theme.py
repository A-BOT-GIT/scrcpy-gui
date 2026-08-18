"""scrcpy GUI 统一深色主题（对齐 Ardot 画布设计稿 706401111686711）。

设计 token 来源：Dark Pure Minimal —— 柔和深色底 #0f0f12 / 降饱和翠绿强调 #34d399 /
1px 发丝线、Sarasa Gothic SC（程序环境通常无 Sarasa，用 Microsoft YaHei UI 替代）。
所有颜色集中在此，避免代码里散落硬编码色值。
"""

# ---- 颜色 token ----
COLOR_BG = "#0f0f12"          # 主窗口底（提亮，降低与强调色对比度）
COLOR_CARD = "#16161a"        # 卡片/分组（提亮，层次更柔和）
COLOR_PANEL = "#0a0a0d"       # 命令预览 / 日志面板内嵌底
COLOR_BAR = "#0e0e11"         # 标题栏 / 状态栏底
COLOR_TEXT = "#e8e8ed"        # 主文字
COLOR_TEXT_MID = "#d4d4db"    # 次级文字
COLOR_TEXT_DIM = "#9ca3af"    # 标签 / 说明（压暗，让主文字更突出）
COLOR_BORDER = "#252529"      # 控件边框（随底色同步提亮）
COLOR_HAIRLINE = "#252529"    # 发丝线 / 分隔
COLOR_ACCENT = "#34d399"      # 强调翠绿（降饱和+提亮，减少刺眼感）
COLOR_ACCENT_HOVER = "#4ade80"
COLOR_WARN = "#F59E0B"        # WARN 日志
COLOR_DEBUG = "#9ca3af"       # DEBUG 日志
COLOR_STOP_HOVER = "#ef4444"  # 停止按钮悬停红
COLOR_ERROR = "#f87171"       # ERROR 日志 / 错误红

# ---- 字体 ----
FONT_UI = '"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif'
FONT_MONO = "Consolas, Menlo, monospace"

# ---- 统一 QSS ----
THEME_QSS = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: {FONT_UI};
    font-size: 13px;
}}

QLabel {{
    background: transparent;
    color: {COLOR_TEXT_MID};
}}

/* 分组卡片 */
QGroupBox {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_HAIRLINE};
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    color: {COLOR_TEXT_DIM};
    padding: 0 4px;
}}

/* 输入类 */
QComboBox, QLineEdit, QSpinBox {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 5px 8px;
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_ACCENT};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLOR_ACCENT};
}}
QComboBox QAbstractItemView {{
    background: {COLOR_CARD};
    color: {COLOR_TEXT};
    selection-background-color: {COLOR_ACCENT};
    border: 1px solid {COLOR_BORDER};
}}

/* 文本面板（命令预览 / 日志） */
QPlainTextEdit {{
    background: {COLOR_PANEL};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_HAIRLINE};
    border-radius: 8px;
    font-family: {FONT_MONO};
    font-size: 12px;
    padding: 8px;
}}

/* 按钮 */
QPushButton {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 7px 14px;
    color: {COLOR_TEXT};
}}
QPushButton:hover {{
    background: #222228;
    border-color: #3d3d45;
}}
QPushButton:pressed {{
    background: {COLOR_BORDER};
}}
QPushButton:disabled {{
    color: #52525b;
    background: {COLOR_CARD};
}}

/* 启动（实心绿） */
QPushButton#launch_btn {{
    background: {COLOR_ACCENT};
    color: #052e16;
    font-weight: 600;
    border: none;
}}
QPushButton#launch_btn:hover {{ background: {COLOR_ACCENT_HOVER}; }}
QPushButton#launch_btn:disabled {{ color: #1a3a28; background: #1a2e22; }}

/* 停止（描边灰，悬停红） */
QPushButton#stop_btn {{
    background: transparent;
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
}}
QPushButton#stop_btn:hover {{ border-color: {COLOR_STOP_HOVER}; color: {COLOR_ERROR}; }}

/* 标签页 */
QTabWidget::pane {{
    border: 1px solid {COLOR_HAIRLINE};
    border-radius: 10px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLOR_TEXT_DIM};
    padding: 8px 14px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {COLOR_ACCENT};
    border-bottom: 2px solid {COLOR_ACCENT};
}}
QTabBar::tab:hover {{ color: {COLOR_TEXT_MID}; }}

/* 状态栏 */
QStatusBar {{
    background: {COLOR_BAR};
    color: {COLOR_TEXT_DIM};
}}
QStatusBar::item {{ border: none; }}

/* 复选框（开关观感） */
QCheckBox {{
    spacing: 6px;
    color: {COLOR_TEXT_MID};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {COLOR_BORDER};
    background: {COLOR_CARD};
}}
QCheckBox::indicator:checked {{
    background: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT};
}}

/* 自定义标题栏 */
QWidget#title_bar {{
    background: {COLOR_BAR};
    border-bottom: 1px solid {COLOR_HAIRLINE};
}}
QPushButton#title_btn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    color: {COLOR_TEXT_DIM};
    font-size: 14px;
}}
QPushButton#title_btn:hover {{ background: {COLOR_BORDER}; color: {COLOR_TEXT}; }}
QPushButton#title_close:hover {{ background: {COLOR_STOP_HOVER}; color: #fff; }}

/* 分段控件（连接页） */
QWidget#segmented {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_HAIRLINE};
    border-radius: 8px;
    padding: 3px;
}}
QPushButton#seg_item {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 22px;
    color: {COLOR_TEXT_DIM};
}}
QPushButton#seg_item:hover {{ color: {COLOR_TEXT_MID}; }}
QPushButton#seg_item[active="true"] {{
    background: {COLOR_ACCENT};
    color: #052e16;
    font-weight: 600;
}}

/* 设备栏卡片（redesign：垂直卡片容器） */
QWidget#device_bar {{
    background-color: {COLOR_CARD};
    border: 1px solid {COLOR_HAIRLINE};
    border-radius: 8px;
}}
QLabel#device_bar_title {{
    color: {COLOR_TEXT_DIM};
    font-weight: 600;
    letter-spacing: 0.04em;
}}

/* 一键无线投屏：固定尺寸绿色主操作按钮（对齐 redesign.html .btn-auto-wifi） */
QPushButton#auto_wifi_btn {{
    background: {COLOR_ACCENT};
    color: {COLOR_TEXT};
    font-weight: 600;
    border: 1px solid {COLOR_ACCENT};
    padding: 9px 18px;
    border-radius: 8px;
}}
QPushButton#auto_wifi_btn:hover {{ background: {COLOR_ACCENT_HOVER}; border-color: {COLOR_ACCENT_HOVER}; }}
QPushButton#auto_wifi_btn:disabled {{ background: #1a2e22; color: #1a3a28; border-color: transparent; }}

/* 条件提示小字 */
QLabel#conn_opt {{
    color: {COLOR_TEXT_DIM};
    font-size: 12px;
}}

/* 内容滚动区（去 Tab，平铺卡片） */
QScrollArea#content_scroll {{
    background: transparent;
    border: none;
}}
QScrollArea#content_scroll viewport {{
    background: {COLOR_BG};
    border: none;
}}
"""
