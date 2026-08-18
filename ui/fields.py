"""参数字段构件与控制器 state 的统一读写。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QWidget


CONTROL_HEIGHT = 34


def make_checkbox(key: str, text: str, checked: bool = False) -> QCheckBox:
    checkbox = QCheckBox(text)
    checkbox.setObjectName(key)
    checkbox.setChecked(checked)
    checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
    return checkbox


def make_combo(key: str, options, current: str = "") -> QComboBox:
    combo = QComboBox()
    combo.setObjectName(key)
    combo.setFixedHeight(CONTROL_HEIGHT)
    if not any(value == "" for _label, value in options):
        combo.addItem("默认", "")
    for label, value in options:
        combo.addItem(label, value)
    index = combo.findData(current)
    combo.setCurrentIndex(index if index >= 0 else 0)
    return combo


def make_line(key: str, placeholder: str = "", current: str = "") -> QLineEdit:
    line = QLineEdit()
    line.setObjectName(key)
    line.setFixedHeight(CONTROL_HEIGHT)
    line.setPlaceholderText(placeholder)
    line.setText("" if current is None else str(current))
    return line


def read_value(widget: QWidget):
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, QComboBox):
        return widget.currentData() or ""
    if isinstance(widget, QLineEdit):
        return widget.text()
    return None


def write_value(widget: QWidget, value) -> None:
    if isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, QComboBox):
        index = widget.findData("" if value is None else value)
        widget.setCurrentIndex(index if index >= 0 else 0)
    elif isinstance(widget, QLineEdit):
        widget.setText("" if value is None else str(value))


def field_row(label: str, widget: QWidget, label_width: int = 112) -> QHBoxLayout:
    """构造 Demo 的紧凑横向“标签 + 控件”字段。"""
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    label_widget = QLabel(label)
    label_widget.setObjectName("fieldLabel")
    label_widget.setFixedWidth(label_width)
    row.addWidget(label_widget)
    row.addWidget(widget, 1)
    return row
