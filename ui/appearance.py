"""标题栏外观入口与锚定主题选择面板。"""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.appearance import Appearance, CUSTOM_THEME, PRESET_THEMES, normalize_color, tokens_for


class AppearancePopover(QFrame):
    """贴近标题栏入口展示的轻量外观选择器。"""

    appearanceSelected = pyqtSignal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("appearance_popup")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._buttons: dict[str, QPushButton] = {}
        self._current = Appearance()
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("外观")
        title.setObjectName("appearance_title")
        root.addWidget(title)

        hint = QLabel("选择应用背景主题")
        hint.setObjectName("appearance_hint")
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for index, theme in enumerate(PRESET_THEMES):
            button = QPushButton(theme.label)
            button.setCheckable(True)
            button.setFixedSize(104, 34)
            button.setAccessibleName(f"选择 {theme.label} 主题")
            button.setToolTip(theme.label)
            button.clicked.connect(
                lambda _checked=False, theme_key=theme.key: self.appearanceSelected.emit(theme_key, None)
            )
            self._buttons[theme.key] = button
            grid.addWidget(button, index // 2, index % 2)
        root.addLayout(grid)

        self.custom_button = QPushButton("自定义颜色…")
        self.custom_button.setObjectName("appearance_custom")
        self.custom_button.setAccessibleName("选择自定义背景色")
        self.custom_button.clicked.connect(self._choose_custom_color)
        root.addWidget(self.custom_button)

    def set_current(self, appearance: Appearance) -> None:
        """更新当前选中主题的视觉状态。"""
        self._current = appearance
        active_tokens = tokens_for(appearance)
        for theme in PRESET_THEMES:
            button = self._buttons[theme.key]
            selected = appearance.theme == theme.key
            button.setChecked(selected)
            button.setText(f"✓ {theme.label}" if selected else theme.label)
            text_color = "#18181B" if _is_light(theme.bg) else "#E8E8ED"
            border = active_tokens.accent if selected else active_tokens.border
            button.setStyleSheet(
                "QPushButton {"
                f"background:{theme.bg}; color:{text_color}; border:2px solid {border};"
                "border-radius:6px; padding:0 8px; text-align:left;}"
                f"QPushButton:hover {{ border-color:{active_tokens.accent_hover}; }}"
                f"QPushButton:focus {{ border-color:{active_tokens.accent_hover}; }}"
            )

        custom_color = normalize_color(appearance.custom_bg)
        selected_custom = appearance.theme == CUSTOM_THEME and custom_color is not None
        self.custom_button.setText(
            f"✓ 自定义 {custom_color}" if selected_custom else "自定义颜色…"
        )
        if selected_custom:
            text_color = "#18181B" if _is_light(custom_color) else "#E8E8ED"
            self.custom_button.setStyleSheet(
                "QPushButton {"
                f"background:{custom_color}; color:{text_color}; border:2px solid {active_tokens.accent};"
                "border-radius:6px; padding:0 10px; text-align:left;}"
            )
        else:
            self.custom_button.setStyleSheet("")

    def show_for(self, anchor: QWidget, appearance: Appearance) -> None:
        """按锚点定位并显示面板。"""
        self.set_current(appearance)
        self.adjustSize()
        offset = max(0, anchor.width() - self.width())
        self.move(anchor.mapToGlobal(QPoint(offset, anchor.height() + 6)))
        self.show()
        self.raise_()

    def _choose_custom_color(self) -> None:
        current = normalize_color(self._current.custom_bg) or "#0F0F12"
        color = QColorDialog.getColor(QColor(current), self, "选择背景色")
        if color.isValid():
            self.appearanceSelected.emit(CUSTOM_THEME, color.name().upper())


def _is_light(color: str) -> bool:
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    return (red * 299 + green * 587 + blue * 114) / 1000 >= 150
