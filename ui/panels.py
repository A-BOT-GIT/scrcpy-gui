"""右侧命令/日志面板与运行状态视图。"""
from __future__ import annotations

import html

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from core.appearance import Appearance, ThemeTokens, tokens_for


class PanelHeader(QWidget):
    """一体化侧栏中的紧凑标题行。"""

    def __init__(self, title: str, badge: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel_header")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(8)
        self.label = QLabel(title)
        self.label.setObjectName("panel_h")
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.badge = QLabel(badge)
        self.badge.setObjectName("panel_badge")
        self.badge.setFixedHeight(24)
        layout.addWidget(self.badge)


class LogPanel(QTextEdit):
    """受主题驱动且有上限的只读日志阅读区。"""

    linesChanged = pyqtSignal(int)
    _MAX_ENTRIES = 500

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("log")
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self._entries: list[tuple[str, str]] = []
        self._colors: dict[str, str] = {}
        self.set_theme_tokens(tokens_for(Appearance()))

    def set_theme_tokens(self, tokens: ThemeTokens) -> None:
        """切换主题后重绘已有日志，避免旧的内联色在新主题中失去对比度。"""
        light_surface = tokens.text == "#18181B"
        self._colors = {
            "default": tokens.text_mid,
            "success": tokens.accent,
            "info": tokens.text_dim,
            "warning": "#B45309" if light_surface else "#F59E0B",
            "error": "#B91C1C" if light_surface else "#F87171",
        }
        self._render_entries()

    def append_line(self, text: str) -> None:
        level = self._classify(text)
        self._entries.append((level, text))
        if len(self._entries) > self._MAX_ENTRIES:
            del self._entries[: len(self._entries) - self._MAX_ENTRIES]
            self._render_entries()
        else:
            self._append_entry(level, text)
        self.linesChanged.emit(len(self._entries))

    def _classify(self, text: str) -> str:
        lowered = text.lower()
        if "error" in lowered or "失败" in text or "崩溃" in text or "异常" in text:
            return "error"
        if "warn" in lowered or "警告" in text:
            return "warning"
        if "scrcpy" in lowered or "完成" in text or "已" in text or "就绪" in text:
            return "success"
        if "info" in lowered or "提示" in text:
            return "info"
        return "default"

    def _append_entry(self, level: str, text: str) -> None:
        escaped = html.escape(text)
        color = self._colors.get(level, self._colors["default"])
        self.append(f'<span style="color:{color}">› {escaped}</span>')

    def _render_entries(self) -> None:
        scroll = self.verticalScrollBar()
        at_bottom = scroll.value() >= scroll.maximum()
        self.clear()
        for level, text in self._entries:
            self._append_entry(level, text)
        if at_bottom:
            scroll.setValue(scroll.maximum())


class CommandPanel(QWidget):
    """连续的命令与日志侧栏，避免两组无关联的卡片堆叠。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("right")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.command_section = QWidget()
        self.command_section.setObjectName("command_section")
        command_layout = QVBoxLayout(self.command_section)
        command_layout.setContentsMargins(0, 0, 0, 18)
        command_layout.setSpacing(0)
        self.command_header = PanelHeader("命令预览", "实时")
        command_layout.addWidget(self.command_header)
        caption = QLabel("当前将执行")
        caption.setObjectName("cmd_caption")
        command_layout.addWidget(caption)
        self.cmd = QLabel("scrcpy")
        self.cmd.setObjectName("cmd")
        self.cmd.setWordWrap(True)
        self.cmd.setMinimumHeight(58)
        command_layout.addWidget(self.cmd)
        layout.addWidget(self.command_section)

        self.log_section = QWidget()
        self.log_section.setObjectName("log_section")
        log_layout = QVBoxLayout(self.log_section)
        log_layout.setContentsMargins(0, 0, 0, 16)
        log_layout.setSpacing(0)
        self.log_header = PanelHeader("实时日志", "0 行")
        log_layout.addWidget(self.log_header)
        self.log = LogPanel()
        self.log.linesChanged.connect(lambda count: self.log_header.badge.setText(f"{count} 行"))
        log_layout.addWidget(self.log, 1)
        layout.addWidget(self.log_section, 1)

    def set_command(self, text: str) -> None:
        self.cmd.setText(text or "scrcpy")

    def set_theme_tokens(self, tokens: ThemeTokens) -> None:
        self.log.set_theme_tokens(tokens)


class StatusBanner(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("banner")
        self.setVisible(False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)
        self.text = QLabel()
        self.text.setWordWrap(True)
        layout.addWidget(self.text, 1)
        close = QPushButton("×")
        close.setObjectName("banner_close")
        close.clicked.connect(self.hide)
        layout.addWidget(close)

    def show_error(self, title: str, detail: str) -> None:
        self.text.setText(f"{title}：{detail}")
        self.setVisible(True)

    def clear(self) -> None:
        self.setVisible(False)


class Toast(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel()
        layout.addWidget(self.label)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, msec: int = 2600) -> None:
        self.label.setText(message)
        parent = self.parentWidget()
        if parent is not None:
            self.adjustSize()
            self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 24)
        self.show()
        self.raise_()
        self._timer.start(msec)
