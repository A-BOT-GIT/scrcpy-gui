"""scrcpy-gui 统一组件库（T2 产物）。

本模块是**纯视图原子构件库**，仅为 T4（6 个 Tab / 面板）与 T6（内联校验）提供可复用零件：
  (A) 字段构造工厂：make_check / make_combo / make_line / make_int / make_group
  (B) LogHighlighter —— scrcpy 日志级别语法高亮器
  (C) TitleBar —— 无边框自定义标题栏

设计红线（来自 SOP T2）：
  * 零 controller 依赖：导入链只允许 PyQt6.* + ui.theme，绝不依赖 app 逻辑层。
  * 零硬编码色值：任何颜色一律引用 ui.theme 的 COLOR_* token；本文件不出现裸 hex。
  * 颜色转 QColor 统一走 ``QColor.fromString(token)``，避免直接构造 QColor 字面量。
  * 工厂把 state key 挂在返回控件上（``widget._state_key``），供 T4 的
    ``BaseTab.register(key, widget)`` 取用；本文件不 import BaseTab（T4 产物）。
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.theme import (
    COLOR_ACCENT,
    COLOR_DEBUG,
    COLOR_ERROR,
    COLOR_TEXT,
    COLOR_WARN,
)


def _color(token: str) -> QColor:
    """把 ui.theme 的 hex token 转成 QColor。

    统一用 ``QColor.fromString`` 而非直接构造 QColor，确保本文件不出现
    裸 hex 字面量（T2 红线：颜色仅来自 ui.theme）。
    """
    return QColor.fromString(token)


def _tag_key(widget: QWidget, key: str) -> QWidget:
    """把 state key 挂到控件上，供 T4 ``BaseTab.register(key, widget)`` 取用。

    key 仅作为数据随控件携带，本模块不消费它（解耦 state 字典）。
    """
    widget._state_key = key  # type: ignore[attr-defined]
    return widget


# ---------------------------------------------------------------------------
# (A) 字段构造工厂
# 约定：每个工厂返回 ``(row, widget)``。
#   * row 是一个可直接 addLayout/addWidget 进父布局的 QHBoxLayout / QVBoxLayout；
#   * widget 已通过 ``_tag_key`` 挂上 ``_state_key``，T4 可取出 key 做注册/回填。
# 控件本身的背景/文字/聚焦/选中颜色全部由 ui.theme 的 THEME_QSS 统一上色，
# 工厂不再手动设色，避免散落硬编码。
# ---------------------------------------------------------------------------


def make_check(text: str, key: str, checked: bool = False) -> Tuple[QHBoxLayout, QCheckBox]:
    """构造一行复选框。

    Args:
        text: 复选框文案。
        key: 对应 state 字典的键，挂到返回的 QCheckBox._state_key。
        checked: 初始是否勾选。

    Returns:
        (row, checkbox)，row 为 QHBoxLayout，可直接 addLayout 进父布局。
    """
    row = QHBoxLayout()
    cb = QCheckBox(text)
    cb.setChecked(checked)
    row.addWidget(cb)
    _tag_key(cb, key)
    return row, cb


def make_combo(
    label: str,
    key: str,
    opts: Sequence[Union[str, Tuple[str, str]]],
) -> Tuple[QVBoxLayout, QComboBox]:
    """构造带标签的下拉框。

    Args:
        label: 标签文案。
        key: 对应 state 字典的键，挂到返回的 QComboBox._state_key。
        opts: 选项列表。每项可为：
            * 字符串 —— 同时作为显示文案与存储值（data）；
            * (显示文案, 值) 二元组 —— 显示与存储分离（兼容原 main_window 的
              (label, val) 写法，如 "默认 (h264)" -> ""）。

    Returns:
        (row, combo)，row 为 QVBoxLayout，可直接 addLayout 进父布局。
    """
    row = QVBoxLayout()
    row.addWidget(QLabel(label))
    cb = QComboBox()
    for opt in opts:
        if isinstance(opt, (tuple, list)) and len(opt) == 2:
            cb.addItem(str(opt[0]), opt[1])
        else:
            cb.addItem(str(opt), str(opt))
    row.addWidget(cb)
    _tag_key(cb, key)
    return row, cb


def make_line(
    label: str,
    key: str,
    placeholder: str = "",
) -> Tuple[QVBoxLayout, QLineEdit]:
    """构造带标签的文本输入框。

    Args:
        label: 标签文案。
        key: 对应 state 字典的键，挂到返回的 QLineEdit._state_key。
        placeholder: 占位提示文字（可选）。

    Returns:
        (row, line_edit)，row 为 QVBoxLayout，可直接 addLayout 进父布局。
    """
    row = QVBoxLayout()
    row.addWidget(QLabel(label))
    le = QLineEdit()
    if placeholder:
        le.setPlaceholderText(placeholder)
    row.addWidget(le)
    _tag_key(le, key)
    return row, le


def make_int(
    label: str,
    key: str,
    default: Union[int, None] = None,
    minimum: int = 0,
    maximum: int = 999999,
) -> Tuple[QVBoxLayout, QSpinBox]:
    """构造带标签的整数微调框。

    Args:
        label: 标签文案。
        key: 对应 state 字典的键，挂到返回的 QSpinBox._state_key。
        default: 初始值；为 None 时留在下限。
        minimum: 下限。
        maximum: 上限。

    Returns:
        (row, spin_box)，row 为 QVBoxLayout，可直接 addLayout 进父布局。
    """
    row = QVBoxLayout()
    row.addWidget(QLabel(label))
    sb = QSpinBox()
    sb.setRange(minimum, maximum)
    if default is not None:
        sb.setValue(int(default))
    row.addWidget(sb)
    _tag_key(sb, key)
    return row, sb


def make_group(parent: Union[QWidget, QVBoxLayout], title: str) -> QVBoxLayout:
    """构造带标题的分组卡片，返回其内层 QVBoxLayout。

    标题/底色/边框由 ui.theme 的 THEME_QSS（QGroupBox / QGroupBox::title）统一上色，
    本函数不手动设色。

    Args:
        parent: 接收分组卡片的父布局（QVBoxLayout）或父控件（QWidget）。
        title: 分组标题。

    Returns:
        分组内层 QVBoxLayout，可直接 addWidget / addLayout 放入子控件。
    """
    box = QGroupBox(title)
    layout = QVBoxLayout()
    box.setLayout(layout)
    # 兼容 parent 为 None（仅返回布局，稍后自行挂父）/ 布局（QVBoxLayout 等，
    # 原始 main_window._group 即传入 QVBoxLayout）/ 控件（挂到其已有 layout）。
    if parent is None:
        return layout
    if hasattr(parent, "addWidget"):
        parent.addWidget(box)
    elif parent.layout() is not None:
        parent.layout().addWidget(box)
    return layout


def make_expert_group(parent: Union[QWidget, QVBoxLayout], title: str) -> QGroupBox:
    """构造可整体显隐的“专家选项”分组，返回 QGroupBox 本身（供 set_expert_mode 显隐）。

    与 ``make_group`` 不同，本函数返回 QGroupBox（而非内层 layout），以便
    ``BaseTab.set_expert_mode`` 直接 ``setVisible``。默认隐藏（基础层）。
    """
    box = QGroupBox(title)
    layout = QVBoxLayout()
    box.setLayout(layout)
    if hasattr(parent, "addWidget"):
        parent.addWidget(box)
    elif parent.layout() is not None:
        parent.layout().addWidget(box)
    box.setVisible(False)
    return box


# ---------------------------------------------------------------------------
# (A2) 内联校验构件（T6）：ValidatedLineEdit / ValidatedSpinBox + 字段工厂
#   * 校验失败时显示旁边红字错误标签（仅用 theme 的 COLOR_ERROR，零裸 hex）。
#   * 所有校验控件暴露 is_valid() -> bool，供 MainWindow 启动前拦截。
#   * 颜色统一来自 ui.theme；导入链仅 PyQt6.* + ui.theme，不依赖 app 逻辑层。
# ---------------------------------------------------------------------------

#: IPv4 校验：四段，每段 0–255
_IP_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
#: 裁剪 W:H:X:Y 校验
_CROP_RE = re.compile(r"^\d+:\d+:\d+:\d+$")


def _validate_ip(text: str) -> "tuple[bool, str]":
    """IPv4 格式校验：空串视为合法（USB 模式允许留空，wifi 留空由启动逻辑单独拦截）。"""
    t = (text or "").strip()
    if not t:
        return True, ""
    m = _IP_RE.match(t)
    if not m:
        return False, "IPv4 格式应为 1.2.3.4"
    for part in m.groups():
        if int(part) > 255:
            return False, "每段 IP 必须在 0–255 之间"
    return True, ""


def _validate_crop(text: str) -> "tuple[bool, str]":
    """裁剪 W:H:X:Y 校验：空串合法（不裁剪），W/H 必须大于 0。"""
    t = (text or "").strip()
    if not t:
        return True, ""
    m = _CROP_RE.match(t)
    if not m:
        return False, "格式应为 W:H:X:Y（如 100:200:10:20）"
    parts = [int(x) for x in m.group().split(":")]
    w, h = parts[0], parts[1]
    if w <= 0 or h <= 0:
        return False, "宽度与高度必须大于 0"
    return True, ""


class ValidatedLineEdit(QLineEdit):
    """带内联校验的输入框：非法时在下方显示红字错误标签，并暴露 ``is_valid()``。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 错误标签：默认隐藏，仅校验失败时显示（颜色走 theme 的 COLOR_ERROR）
        self._error_label = QLabel("")
        self._error_label.setObjectName("error_label")
        self._error_label.setStyleSheet(f"color:{COLOR_ERROR};")
        self._error_label.setVisible(False)
        self._validator = None  # type: ignore[var-annotated]
        self.textChanged.connect(self._revalidate)

    # ------------------------------------------------------------------
    def set_validator(self, fn) -> None:
        """设置校验函数 ``(text) -> (ok, msg)`` 并立即复验。"""
        self._validator = fn
        self._revalidate(self.text())

    def _revalidate(self, text: str) -> bool:
        if self._validator is None:
            self._set_error("")
            return True
        ok, msg = self._validator(text)
        self._set_error("" if ok else msg)
        return ok

    def is_valid(self) -> bool:
        """当前文本是否通过校验。"""
        if self._validator is None:
            return True
        return self._validator(self.text())[0]

    def set_error(self, msg: str) -> None:
        """手动设置错误文案（如启动拦截时提示“请填写无线 IP”）。"""
        self._set_error(msg)

    def _set_error(self, msg: str) -> None:
        self._error_label.setText(str(msg))
        self._error_label.setVisible(bool(msg))


class ValidatedSpinBox(QSpinBox):
    """带内联校验的整数微调框：默认按 [minimum, maximum] 校验，暴露 ``is_valid()``。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        minimum: int = 0,
        maximum: int = 999999,
    ) -> None:
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self._error_label = QLabel("")
        self._error_label.setObjectName("error_label")
        self._error_label.setStyleSheet(f"color:{COLOR_ERROR};")
        self._error_label.setVisible(False)
        self._validator = None  # type: ignore[var-annotated]
        self.valueChanged[int].connect(self._revalidate)

    def set_validator(self, fn) -> None:
        """设置校验函数 ``(value) -> (ok, msg)`` 并立即复验。"""
        self._validator = fn
        self._revalidate(self.value())

    def _revalidate(self, value: int) -> bool:
        if self._validator is None:
            self._set_error("")
            return True
        ok, msg = self._validator(value)
        self._set_error("" if ok else msg)
        return ok

    def is_valid(self) -> bool:
        """当前值是否通过校验。"""
        if self._validator is None:
            return True
        return self._validator(self.value())[0]

    def _set_error(self, msg: str) -> None:
        self._error_label.setText(str(msg))
        self._error_label.setVisible(bool(msg))


def make_ip_field(
    label: str,
    key: str,
    placeholder: str = "",
) -> "tuple[QVBoxLayout, ValidatedLineEdit]":
    """构造带内联 IPv4 校验的输入框（返回 (row, field)，field 即 ValidatedLineEdit）。"""
    row = QVBoxLayout()
    if label:
        row.addWidget(QLabel(label))
    field = ValidatedLineEdit()
    if placeholder:
        field.setPlaceholderText(placeholder)
    field.set_validator(_validate_ip)
    row.addWidget(field)
    row.addWidget(field._error_label)
    _tag_key(field, key)
    return row, field


def make_crop_field(
    label: str,
    key: str,
    placeholder: str = "",
) -> "tuple[QVBoxLayout, ValidatedLineEdit]":
    """构造带内联裁剪校验的输入框（W:H:X:Y，W/H>0）。"""
    row = QVBoxLayout()
    if label:
        row.addWidget(QLabel(label))
    field = ValidatedLineEdit()
    if placeholder:
        field.setPlaceholderText(placeholder)
    field.set_validator(_validate_crop)
    row.addWidget(field)
    row.addWidget(field._error_label)
    _tag_key(field, key)
    return row, field


def make_int_range_field(
    label: str,
    key: str,
    default: "int | None" = None,
    minimum: int = 0,
    maximum: int = 999999,
) -> "tuple[QVBoxLayout, ValidatedSpinBox]":
    """构造带内联范围校验的整数微调框（返回 (row, ValidatedSpinBox)）。

    与 ``make_int`` 接口一致，仅控件升级为 ``ValidatedSpinBox``（暴露 is_valid()）。
    """
    row = QVBoxLayout()
    row.addWidget(QLabel(label))
    sb = ValidatedSpinBox(minimum=minimum, maximum=maximum)
    if default is not None:
        sb.setValue(int(default))
    sb.set_validator(
        lambda v, lo=minimum, hi=maximum: (
            lo <= v <= hi,
            f"请输入 {lo}–{hi} 之间的整数",
        )
    )
    row.addWidget(sb)
    row.addWidget(sb._error_label)
    _tag_key(sb, key)
    return row, sb


# ---------------------------------------------------------------------------
# (B) LogHighlighter —— 从 main_window.py 搬移并重用
# ---------------------------------------------------------------------------


class LogHighlighter(QSyntaxHighlighter):
    """按日志级别给行着色（颜色全部来自 ui.theme）：

    成功绿(COLOR_ACCENT) / INFO 白(COLOR_TEXT) / WARN 琥珀(COLOR_WARN) /
    DEBUG 灰(COLOR_DEBUG) / ERROR 红(COLOR_ERROR)。

    规则按列表顺序匹配，命中即应用并停止（首命中优先）。颜色经 ``_color``
    由 theme token 转换，本类零硬编码色值。
    """

    def __init__(self, doc):
        """构造高亮器并编译各级别正则。

        Args:
            doc: 目标 QTextDocument（如 log_view.document()）。
        """
        super().__init__(doc)
        self._rules: List[Tuple[re.Pattern, QColor]] = [
            (re.compile(r"▶|已连接|已建立|成功|就绪", re.I), _color(COLOR_ACCENT)),
            (re.compile(r"WARN|警告", re.I), _color(COLOR_WARN)),
            (re.compile(r"\bDEBUG\b", re.I), _color(COLOR_DEBUG)),
            (re.compile(r"ERROR|✖|✗|失败", re.I), _color(COLOR_ERROR)),
            (re.compile(r"\bINFO\b", re.I), _color(COLOR_TEXT)),
        ]

    def highlightBlock(self, text: str) -> None:
        """为单行文本应用级别着色。"""
        for rx, color in self._rules:
            if rx.search(text):
                fmt = QTextCharFormat()
                fmt.setForeground(color)
                self.setFormat(0, len(text), fmt)
                break


# ---------------------------------------------------------------------------
# (C) TitleBar —— 从 main_window.py 搬移并重用
# ---------------------------------------------------------------------------


class TitleBar(QWidget):
    """无边框自定义标题栏：支持拖拽移动 + 最小化/关闭（无系统边框）。

    底色与按钮态由 ui.theme 的 THEME_QSS（#title_bar / #title_btn /
    #title_close）统一上色，本类不手动设色。
    """

    def __init__(self, parent: Union[QWidget, None] = None):
        """构造标题栏：标题文字 + 最小化 + 关闭按钮 + 拖拽逻辑。"""
        super().__init__(parent)
        self.setObjectName("title_bar")
        self.setFixedHeight(40)
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 0, 8, 0)
        h.setSpacing(8)
        h.addWidget(QLabel("scrcpy-gui"))
        h.addStretch(1)
        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("title_btn")
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())
        h.addWidget(self.min_btn)
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("title_close")
        self.close_btn.clicked.connect(lambda: self.window().close())
        h.addWidget(self.close_btn)
        self._drag_start = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_start = e.globalPosition().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_start is not None and e.buttons() & Qt.MouseButton.LeftButton:
            w = self.window()
            w.move(w.pos() + e.globalPosition().toPoint() - self._drag_start)
            self._drag_start = e.globalPosition().toPoint()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_start = None
        super().mouseReleaseEvent(e)


if __name__ == "__main__":
    # 轻量自检：仅验证符号可被取到、工厂能产出控件并携带 key。
    # 不启动 QApplication，避免导入即拉起 GUI 事件循环。
    assert callable(make_check) and callable(make_combo)
    assert callable(make_line) and callable(make_int) and callable(make_group)
    assert "LogHighlighter" in globals() and "TitleBar" in globals()
    assert callable(make_ip_field) and callable(make_crop_field)
    assert callable(make_int_range_field)
    assert hasattr(ValidatedLineEdit, "is_valid") and hasattr(ValidatedSpinBox, "is_valid")
    _r, _cb = make_check("测试", "wifiOpt")
    assert _cb._state_key == "wifiOpt"
    _ri, _ip = make_ip_field("IP", "ip")
    assert _ip._state_key == "ip" and _ip.is_valid()
    print("widgets.py 自检通过：工厂 + 校验控件 + LogHighlighter + TitleBar 符号齐全。")
