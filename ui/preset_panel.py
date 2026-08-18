"""预设选择、管理和编辑界面。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.controller import AppController
from core.presets import PRESETTABLE_KEYS, default_include_keys, sanitize_name
from ui.fields import make_checkbox, make_combo, make_line, read_value, write_value


_GROUP_FIELDS = {
    "video": {
        "label": "视频",
        "keys": ["vcodec", "maxSize", "bitrate", "maxFps", "crop", "capOri", "noVideo"],
    },
    "audio": {
        "label": "音频",
        "keys": ["audio", "noAudioPlay", "acodec", "abitrate", "abuffer"],
    },
    "control": {
        "label": "控制",
        "keys": ["control", "otg", "keyboard", "mouse", "gamepad", "showTouches", "turnOff", "stayAwake", "powerOff"],
    },
    "record": {
        "label": "录制",
        "keys": ["record", "recPath", "recFmt"],
    },
    "window": {
        "label": "窗口",
        "keys": ["fullscreen", "ontop", "borderless", "noWindow", "noSaver", "winTitle", "renderFit", "winX", "winY", "winW", "winH"],
    },
    "display": {"label": "副屏", "keys": ["displayId"]},
}

_FIELD_SPEC = {
    "vcodec": ("视频编解码器", "combo", [("默认 (H.264)", ""), ("H.265", "h265"), ("AV1", "av1")]),
    "maxSize": ("最大尺寸", "combo", [("1080p", "1920"), ("720p", "1280"), ("不限制", "")]),
    "bitrate": ("码率 Mbps", "combo", [("默认 (8M)", "8"), ("4 Mbps", "4"), ("2 Mbps", "2"), ("1 Mbps", "1")]),
    "maxFps": ("帧率上限", "combo", [("60 fps", "60"), ("30 fps", "30"), ("不限制", "")]),
    "crop": ("裁剪", "line", None),
    "capOri": ("捕获方向", "combo", [("不锁定", ""), ("竖屏", "@0"), ("横屏 90°", "@90"), ("横屏 180°", "@180"), ("横屏 270°", "@270")]),
    "noVideo": ("关闭视频（仅音频）", "check", None),
    "audio": ("转发音频", "check", None),
    "noAudioPlay": ("不播放音频", "check", None),
    "acodec": ("音频编解码器", "combo", [("默认 (opus)", ""), ("AAC", "aac"), ("FLAC", "flac")]),
    "abitrate": ("音频码率 kbps", "line", None),
    "abuffer": ("缓冲 ms", "line", None),
    "control": ("启用控制", "check", None),
    "otg": ("OTG 模式", "check", None),
    "keyboard": ("键盘模拟", "combo", [("SDK（默认）", ""), ("UHID", "uhid")]),
    "mouse": ("鼠标模拟", "combo", [("SDK（默认）", ""), ("UHID", "uhid")]),
    "gamepad": ("游戏手柄", "check", None),
    "showTouches": ("显示触摸点", "check", None),
    "turnOff": ("关闭设备屏幕", "check", None),
    "stayAwake": ("保持唤醒", "check", None),
    "powerOff": ("关闭时关机", "check", None),
    "record": ("启用录制", "check", None),
    "recPath": ("输出文件", "line", None),
    "recFmt": ("录制格式", "combo", [("MP4", "mp4"), ("MKV", "mkv")]),
    "fullscreen": ("启动即全屏", "check", None),
    "ontop": ("窗口置顶", "check", None),
    "borderless": ("无边框", "check", None),
    "noWindow": ("无窗口", "check", None),
    "noSaver": ("禁用屏保", "check", None),
    "winTitle": ("窗口标题", "line", None),
    "renderFit": ("渲染适配", "combo", [("letterbox", ""), ("stretched", "stretched"), ("unscaled", "unscaled")]),
    "winX": ("窗口 X", "line", None),
    "winY": ("窗口 Y", "line", None),
    "winW": ("窗口宽", "line", None),
    "winH": ("窗口高", "line", None),
    "displayId": ("显示 ID", "line", None),
}

_GROUP_ORDER = ["video", "audio", "control", "record", "window", "display"]


class PresetPanel(QWidget):
    presetChosen = pyqtSignal(str)
    manageRequested = pyqtSignal()

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        label = QLabel("预设")
        label.setObjectName("preset_label")
        lay.addWidget(label)
        self.combo = QComboBox()
        self.combo.setAccessibleName("选择预设")
        self.combo.addItem("（无 / 自定义）", "")
        self.combo.currentIndexChanged.connect(lambda _: self.presetChosen.emit(self.combo.currentData() or ""))
        lay.addWidget(self.combo, 1)
        self.manageBtn = QPushButton("管理")
        self.manageBtn.setObjectName("btn_secondary")
        self.manageBtn.setFixedSize(56, 32)
        self.manageBtn.setAccessibleName("管理预设")
        self.manageBtn.clicked.connect(self.manageRequested.emit)
        lay.addWidget(self.manageBtn)

    def set_presets(self, names: list[str]) -> None:
        cur = self.combo.currentData() or ""
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem("（无 / 自定义）", "")
        for name in names:
            self.combo.addItem(name, name)
        idx = self.combo.findData(cur)
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo.blockSignals(False)

    def set_current(self, name: str) -> None:
        idx = self.combo.findData(name or "")
        self.combo.setCurrentIndex(idx if idx >= 0 else 0)

    def set_selectable(self, enabled: bool) -> None:
        self.combo.setEnabled(enabled)


class DialogHeader(QWidget):
    """无边框对话框的标题行，保留可拖动的原生操作习惯。"""

    def __init__(self, dialog: QDialog, title: str) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_offset = None
        self.setObjectName("dialog_header")
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        title_label = QLabel(title)
        title_label.setObjectName("dlg_title")
        layout.addWidget(title_label)
        layout.addStretch(1)
        close = QPushButton("×")
        close.setObjectName("banner_close")
        close.setFixedSize(32, 28)
        close.setToolTip("关闭")
        close.clicked.connect(dialog.reject)
        layout.addWidget(close)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        event.accept()


class ThemedDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class PresetListRow(QWidget):
    editRequested = pyqtSignal(str)
    copyRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)

    def __init__(self, name: str, record: dict, active: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("preset_row")
        self.setProperty("active", "true" if active else "false")
        self.setFixedHeight(62)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 8, 8)
        layout.setSpacing(8)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(name)
        title.setObjectName("preset_row_title")
        text.addWidget(title)
        params = record.get("params", {}) if isinstance(record, dict) else {}
        description = (record.get("meta", {}) or {}).get("description", "") if isinstance(record, dict) else ""
        meta = f"包含 {len(params)} 项设置"
        if description:
            meta = f"{meta}  ·  {description}"
        subtitle = QLabel(meta)
        subtitle.setObjectName("preset_row_meta")
        text.addWidget(subtitle)
        layout.addLayout(text, 1)
        if active:
            badge = QLabel("当前")
            badge.setObjectName("preset_active_badge")
            layout.addWidget(badge)
        for label, object_name, signal in (
            ("编辑", "preset_edit", self.editRequested),
            ("复制", "preset_copy", self.copyRequested),
            ("删除", "preset_delete", self.deleteRequested),
        ):
            button = QPushButton(label)
            button.setObjectName(object_name)
            button.setFixedSize(52, 30)
            button.clicked.connect(lambda _=False, n=name, s=signal: s.emit(n))
            layout.addWidget(button)


class PresetManageDialog(ThemedDialog):
    presetsChanged = pyqtSignal()

    def __init__(self, controller: AppController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self.setObjectName("manage_dialog")
        self.setWindowTitle("预设管理")
        self.setMinimumSize(620, 470)
        self.resize(680, 560)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(DialogHeader(self, "预设管理"))

        subtitle = QLabel("选择可复用配置。复制会创建新预设，删除前会再次确认。")
        subtitle.setObjectName("dlg_subtitle")
        subtitle.setWordWrap(True)
        subtitle.setContentsMargins(18, 14, 18, 10)
        root.addWidget(subtitle)

        self.list_scroll = QScrollArea()
        self.list_scroll.setObjectName("preset_list")
        self.list_scroll.setWidgetResizable(True)
        self.list_content = QWidget()
        self.list_content.setObjectName("preset_list_content")
        self.list = QVBoxLayout(self.list_content)
        self.list.setContentsMargins(18, 4, 18, 12)
        self.list.setSpacing(8)
        self.list_scroll.setWidget(self.list_content)
        root.addWidget(self.list_scroll, 1)

        compose = QWidget()
        compose.setObjectName("preset_compose")
        compose_layout = QVBoxLayout(compose)
        compose_layout.setContentsMargins(18, 12, 18, 14)
        compose_layout.setSpacing(8)
        self.notice = QLabel()
        self.notice.setObjectName("dialog_notice")
        self.notice.setVisible(False)
        compose_layout.addWidget(self.notice)
        new_row = QHBoxLayout()
        new_row.setSpacing(8)
        self.newName = QLineEdit()
        self.newName.setPlaceholderText("将当前配置保存为新预设")
        self.newName.setAccessibleName("新预设名称")
        self.newName.returnPressed.connect(self._on_save_new)
        new_row.addWidget(self.newName, 1)
        save = QPushButton("保存当前配置")
        save.setObjectName("launch_btn")
        save.setFixedHeight(34)
        save.clicked.connect(self._on_save_new)
        new_row.addWidget(save)
        compose_layout.addLayout(new_row)
        root.addWidget(compose)
        self._build_list()

    def _show_notice(self, text: str, severity: str = "error") -> None:
        self.notice.setText(text)
        self.notice.setProperty("severity", severity)
        self.notice.setVisible(True)
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)

    def _build_list(self) -> None:
        while self.list.count():
            item = self.list.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        names = self._controller.presets.list()
        active = self._controller.state.get("preset_name", "")
        if not names:
            empty = QLabel("还没有预设。输入名称后即可保存当前配置。")
            empty.setObjectName("dlg_subtitle")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list.addWidget(empty)
        for name in names:
            row = PresetListRow(name, self._controller.presets.load(name) or {}, name == active)
            row.editRequested.connect(self._on_edit)
            row.copyRequested.connect(self._on_copy)
            row.deleteRequested.connect(self._on_delete)
            self.list.addWidget(row)
        self.list.addStretch(1)

    def _on_save_new(self) -> None:
        try:
            name = sanitize_name(self.newName.text())
        except ValueError as exc:
            self._show_notice(str(exc))
            return
        try:
            self._controller.save_preset(name, include_keys=default_include_keys(), overwrite=False)
        except (FileExistsError, ValueError, OSError) as exc:
            self._show_notice(str(exc))
            return
        self.newName.clear()
        self._show_notice(f"已保存“{name}”", "success")
        self._build_list()
        self.presetsChanged.emit()
        self._controller.statusMessage.emit(f"已保存预设：{name}")

    def _on_edit(self, name: str) -> None:
        dialog = PresetEditDialog(self._controller, name, self)
        if dialog.exec():
            self._show_notice(f"已更新“{dialog.saved_name}”", "success")
            self._build_list()
            self.presetsChanged.emit()
            self._controller.statusMessage.emit(f"已更新预设：{dialog.saved_name}")

    def _on_copy(self, name: str) -> None:
        loaded = self._controller.presets.load(name)
        if loaded is None:
            self._show_notice("原预设不存在，无法复制")
            return
        new_name = f"{name} 副本"
        index = 1
        while self._controller.presets.exists(new_name):
            index += 1
            new_name = f"{name} 副本{index}"
        try:
            description = (loaded.get("meta", {}) or {}).get("description", "")
            self._controller.presets.save(new_name, loaded.get("params", {}), description, overwrite=False)
        except (ValueError, OSError) as exc:
            self._show_notice(f"复制失败：{exc}")
            return
        self._show_notice(f"已复制为“{new_name}”", "success")
        self._build_list()
        self.presetsChanged.emit()
        self._controller.statusMessage.emit(f"已复制预设：{new_name}")

    def _on_delete(self, name: str) -> None:
        answer = QMessageBox.question(
            self,
            "删除预设",
            f"确定删除预设“{name}”？此操作无法撤销。",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._controller.delete_preset(name)
        except (ValueError, OSError) as exc:
            self._show_notice(f"删除失败：{exc}")
            return
        self._show_notice(f"已删除“{name}”", "success")
        self._build_list()
        self.presetsChanged.emit()
        self._controller.statusMessage.emit(f"已删除预设：{name}")


class PresetEditDialog(ThemedDialog):
    def __init__(self, controller: AppController, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._name = name
        self.saved_name = name
        self.setObjectName("edit_dialog")
        self.setWindowTitle("编辑预设" if name else "新建预设")
        self.setMinimumSize(650, 520)
        self.resize(720, 640)
        self._editors: dict[str, QWidget] = {}
        self._group_cbs: dict[str, QPushButton] = {}
        self._group_fields: dict[str, QWidget] = {}
        self._group_cards: dict[str, QWidget] = {}
        self._build()
        self._prefill()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(DialogHeader(self, self.windowTitle()))

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(18, 14, 18, 12)
        body_layout.setSpacing(10)
        name_row = QHBoxLayout()
        label = QLabel("预设名称")
        label.setObjectName("dlg_label")
        name_row.addWidget(label)
        self.nameEdit = QLineEdit(self._name)
        self.nameEdit.setPlaceholderText("输入预设名称")
        self.nameEdit.setAccessibleName("预设名称")
        name_row.addWidget(self.nameEdit, 1)
        body_layout.addLayout(name_row)
        hint = QLabel("勾选需要保存的分组。未勾选的分组不会写入预设。")
        hint.setObjectName("hint")
        body_layout.addWidget(hint)
        root.addWidget(body)

        scroll = QScrollArea()
        scroll.setObjectName("preset_editor_scroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 4, 18, 12)
        content_layout.setSpacing(8)
        for group in _GROUP_ORDER:
            self._add_group(content_layout, group)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QWidget()
        footer.setObjectName("preset_compose")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(18, 10, 18, 12)
        self.notice = QLabel()
        self.notice.setObjectName("dialog_notice")
        self.notice.setVisible(False)
        footer_layout.addWidget(self.notice, 1)
        cancel = QPushButton("取消")
        cancel.setObjectName("btn_secondary")
        cancel.clicked.connect(self.reject)
        footer_layout.addWidget(cancel)
        save = QPushButton("保存修改" if self._name else "创建预设")
        save.setObjectName("launch_btn")
        save.clicked.connect(self._on_save)
        footer_layout.addWidget(save)
        root.addWidget(footer)

    def _add_group(self, layout: QVBoxLayout, group: str) -> None:
        spec = _GROUP_FIELDS[group]
        card = QWidget()
        card.setObjectName("dlg_group_card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(8)
        toggle = QPushButton(f"保存{spec['label']}设置")
        toggle.setObjectName("preset_group_toggle")
        toggle.setCheckable(True)
        toggle.setFixedHeight(30)
        toggle.setAccessibleName(f"保存{spec['label']}设置")
        toggle.toggled.connect(lambda checked, g=group: self._set_group_selected(g, checked))
        card_layout.addWidget(toggle)
        fields = QWidget()
        fields_layout = QVBoxLayout(fields)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(6)
        for key in spec["keys"]:
            label, kind, options = _FIELD_SPEC[key]
            if kind == "combo":
                editor = make_combo(key, options)
            elif kind == "line":
                editor = make_line(key)
            else:
                editor = make_checkbox(key, label)
            row = QHBoxLayout()
            row.setSpacing(10)
            if kind != "check":
                field_label = QLabel(label)
                field_label.setObjectName("fld_label")
                field_label.setMinimumWidth(132)
                row.addWidget(field_label)
            row.addWidget(editor, 1)
            fields_layout.addLayout(row)
            self._editors[key] = editor
        card_layout.addWidget(fields)
        layout.addWidget(card)
        self._group_cbs[group] = toggle
        self._group_fields[group] = fields
        self._group_cards[group] = card
        self._set_group_selected(group, False)

    def _set_group_selected(self, group: str, selected: bool) -> None:
        self._group_fields[group].setEnabled(selected)
        card = self._group_cards[group]
        card.setProperty("checked", "true" if selected else "false")
        card.style().unpolish(card)
        card.style().polish(card)

    def _show_notice(self, text: str) -> None:
        self.notice.setText(text)
        self.notice.setProperty("severity", "error")
        self.notice.setVisible(True)
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)

    def _prefill(self) -> None:
        if not self._name:
            return
        loaded = self._controller.presets.load(self._name)
        if loaded is None:
            self._show_notice("预设不存在，已按新建预设处理")
            return
        params = loaded.get("params", {})
        for group, spec in _GROUP_FIELDS.items():
            self._group_cbs[group].setChecked(any(key in params for key in spec["keys"]))
        for key, editor in self._editors.items():
            if key in params:
                write_value(editor, params[key])

    def _on_save(self) -> None:
        try:
            name = sanitize_name(self.nameEdit.text())
        except ValueError as exc:
            self._show_notice(str(exc))
            return
        selected_groups = [group for group, box in self._group_cbs.items() if box.isChecked()]
        if not selected_groups:
            self._show_notice("至少选择一个要保存的分组")
            return
        params: dict[str, object] = {}
        for group in selected_groups:
            for key in _GROUP_FIELDS[group]["keys"]:
                params[key] = read_value(self._editors[key])
        try:
            if self._name:
                if name != self._name:
                    self._controller.rename_preset(self._name, name)
                self._controller.presets.save(name, params, overwrite=True)
            else:
                self._controller.presets.save(name, params, overwrite=False)
        except (FileExistsError, FileNotFoundError, ValueError, OSError) as exc:
            self._show_notice(str(exc))
            return
        self.saved_name = name
        self.accept()
