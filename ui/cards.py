"""与 Demo 对齐的参数卡片，所有字段使用控制器既有 state 键。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from ui.fields import field_row, make_checkbox, make_combo, make_line


class Card(QWidget):
    def __init__(self, title: str, kind: str, columns: int = 1, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._columns = columns
        self._grid_column = 0
        self._grid_row = 0
        self.setObjectName("card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        root.addWidget(heading)

        if columns > 1:
            self.body = QGridLayout()
            self.body.setContentsMargins(0, 0, 0, 0)
            self.body.setHorizontalSpacing(18)
            self.body.setVerticalSpacing(10)
            for column in range(columns):
                self.body.setColumnStretch(column, 1)
        else:
            self.body = QVBoxLayout()
            self.body.setContentsMargins(0, 0, 0, 0)
            self.body.setSpacing(10)
        root.addLayout(self.body)

    def add_combo(self, register, key: str, label: str, options, current: str = "") -> None:
        widget = make_combo(key, options, current)
        self._add_field(label, widget)
        register(key, widget)

    def add_line(self, register, key: str, label: str, placeholder: str = "", current: str = "") -> None:
        widget = make_line(key, placeholder, current)
        self._add_field(label, widget)
        register(key, widget)

    def add_check(self, register, key: str, text: str, checked: bool = False) -> None:
        widget = make_checkbox(key, text, checked)
        if self._columns > 1:
            self._advance_grid_row()
            self.body.addWidget(widget, self._grid_row, 0, 1, self._columns)
            self._grid_row += 1
        else:
            self.body.addWidget(widget)
        register(key, widget)

    def add_hint(self, text: str) -> None:
        hint = QLabel(text)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        if self._columns > 1:
            self._advance_grid_row()
            self.body.addWidget(hint, self._grid_row, 0, 1, self._columns)
            self._grid_row += 1
        else:
            self.body.addWidget(hint)

    def _add_field(self, label: str, widget: QWidget) -> None:
        if self._columns == 1:
            self.body.addLayout(field_row(label, widget))
            return

        field = QWidget()
        field.setLayout(field_row(label, widget, label_width=104))
        self.body.addWidget(field, self._grid_row, self._grid_column)
        self._grid_column += 1
        if self._grid_column == self._columns:
            self._grid_column = 0
            self._grid_row += 1

    def _advance_grid_row(self) -> None:
        if self._grid_column:
            self._grid_column = 0
            self._grid_row += 1


def build_all_cards(register, state: dict) -> dict[str, Card]:
    value = lambda key, default="": state.get(key, default)

    video = Card("视频", "basic", columns=2)
    video.add_combo(register, "vcodec", "视频编解码器", [("默认 (h264)", ""), ("H.265", "h265"), ("AV1", "av1")], value("vcodec"))
    video.add_combo(register, "maxSize", "最大尺寸 (-m)", [("1080p (1920×1080)", "1920"), ("720p (1280×720)", "1280"), ("不限制", "")], value("maxSize"))
    video.add_combo(register, "bitrate", "码率 Mbps (-b)", [("默认 (8M)", "8"), ("4 Mbps", "4"), ("2 Mbps", "2"), ("1 Mbps", "1"), ("自定义", "")], value("bitrate"))
    video.add_combo(register, "maxFps", "帧率上限", [("60 fps", "60"), ("30 fps", "30"), ("不限制", "")], value("maxFps"))
    video.add_combo(register, "crop", "裁剪 (--crop)", [("不裁剪（全屏）", "")], value("crop"))
    video.add_combo(register, "capOri", "捕获方向", [("不锁定", ""), ("@0 竖", "@0"), ("@90", "@90"), ("@180", "@180"), ("@270", "@270")], value("capOri"))
    video.add_check(register, "noVideo", "关闭视频（仅音频）", bool(value("noVideo")))
    video.add_hint("降低分辨率可显著提升性能（如 -m 1024）。H.265 画质更好，H.264 延迟更低。")

    record = Card("录制", "basic")
    record.add_check(register, "record", "启用录制", bool(value("record")))
    record.add_line(register, "recPath", "输出文件", "screen_2026", value("recPath"))
    record.add_combo(register, "recFmt", "格式", [("MP4", "mp4"), ("MKV", "mkv")], value("recFmt") or "mp4")
    record.add_hint("仅录制不显示：勾选“窗口”页的“无窗口”并启用录制即可后台录像。")

    audio = Card("音频精细（需 Android 11+）", "expert", columns=2)
    audio.add_check(register, "audio", "转发音频", bool(value("audio", True)))
    audio.add_check(register, "noAudioPlay", "不播放音频（--no-audio-playback）", bool(value("noAudioPlay")))
    audio.add_combo(register, "acodec", "音频编解码器", [("默认 (opus)", ""), ("AAC", "aac"), ("FLAC", "flac")], value("acodec"))
    audio.add_line(register, "abitrate", "音频码率 kbps", "自动", value("abitrate"))
    audio.add_line(register, "abuffer", "缓冲 ms", "自动", value("abuffer"))

    control = Card("控制精细", "expert", columns=2)
    control.add_check(register, "control", "启用控制", bool(value("control", True)))
    control.add_check(register, "otg", "OTG 模式（无需投屏）", bool(value("otg")))
    control.add_combo(register, "keyboard", "键盘模拟", [("SDK (默认)", ""), ("UHID（物理键盘）", "uhid")], value("keyboard") if isinstance(value("keyboard"), str) else "")
    control.add_combo(register, "mouse", "鼠标模拟", [("SDK (默认)", ""), ("UHID（物理鼠标）", "uhid")], value("mouse") if isinstance(value("mouse"), str) else "")
    control.add_check(register, "gamepad", "游戏手柄", bool(value("gamepad")))
    control.add_check(register, "showTouches", "显示触摸点", bool(value("showTouches")))
    control.add_check(register, "turnOff", "关闭设备屏幕", bool(value("turnOff")))
    control.add_check(register, "stayAwake", "保持唤醒", bool(value("stayAwake")))
    control.add_check(register, "powerOff", "关闭时关机", bool(value("powerOff")))

    window = Card("窗口定位与渲染", "expert", columns=2)
    window.add_check(register, "fullscreen", "启动即全屏 (-f)", bool(value("fullscreen")))
    window.add_check(register, "ontop", "置顶", bool(value("ontop")))
    window.add_check(register, "borderless", "无边框", bool(value("borderless")))
    window.add_check(register, "noWindow", "无窗口（仅录制/音频）", bool(value("noWindow")))
    window.add_check(register, "noSaver", "禁用屏保", bool(value("noSaver")))
    window.add_line(register, "winTitle", "窗口标题", "scrcpy", value("winTitle"))
    window.add_combo(register, "renderFit", "渲染适配", [("letterbox", ""), ("stretched", "stretched"), ("unscaled", "unscaled")], value("renderFit"))
    window.add_line(register, "winX", "X", "0", value("winX"))
    window.add_line(register, "winY", "Y", "0", value("winY"))
    window.add_line(register, "winW", "宽", "0", value("winW"))
    window.add_line(register, "winH", "高", "0", value("winH"))

    display = Card("副屏 / 其他", "expert")
    display.add_line(register, "displayId", "指定显示 ID", "0", value("displayId"))
    display.add_hint("多屏设备可选副屏（副屏控制需 Android 10+）。")

    return {"video": video, "record": record, "audio": audio, "control": control, "window": window, "display": display}
