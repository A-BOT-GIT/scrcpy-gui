"""Demo 规格的主窗口，视图层只经 AppController 驱动业务。"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app import __version__
from app.controller import AppController
from core.appearance import Appearance, AppearanceStore, tokens_for
from ui.appearance import AppearancePopover
from ui.cards import build_all_cards
from ui.device_bar import DeviceBar
from ui.fields import read_value, write_value
from ui.panels import CommandPanel, StatusBanner, Toast
from ui.preset_panel import PresetManageDialog, PresetPanel
from ui.app_qss import build_qss


class MainWindow(QWidget):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._controller = controller
        self._controls: dict[str, QWidget] = {}
        self._cards: dict[str, QWidget] = {}
        self._refilling = False
        self._drag_offset = None
        self._appearance_store = AppearanceStore()
        self._appearance = self._appearance_store.load()
        self._theme_tokens = tokens_for(self._appearance)
        self._appearance_popup: AppearancePopover | None = None

        self.setObjectName("app")
        self.setWindowTitle("scrcpy-gui")
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self.setStyleSheet(build_qss(self._theme_tokens))
        self._set_demo_defaults()
        self._build_shell()
        self._build_title_bar()
        self._build_banner()
        self._build_body()
        self._build_status_bar()
        self._build_toast()
        self._sync_window_chrome()
        self._wire_controller()
        self._wire_controls()
        self._init_command()
        self._apply_expert(False)
        self._controller.refresh_devices()

    def _set_demo_defaults(self) -> None:
        """Demo 首屏的安全默认值，同时移除多余的键鼠命令参数。"""
        state = self._controller.state
        state["vcodec"] = ""
        state["maxSize"] = "1920"
        state["bitrate"] = "8"
        state["maxFps"] = "60"
        state["recFmt"] = "mp4"
        state["expertMode"] = False
        state["keyboard"] = ""
        state["mouse"] = ""

    def _build_shell(self) -> None:
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(8, 8, 8, 8)
        self._root_layout.setSpacing(0)
        self.shell = QWidget()
        self.shell.setObjectName("window_shell")
        self.shell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._shell_layout = QVBoxLayout(self.shell)
        self._shell_layout.setContentsMargins(0, 0, 0, 0)
        self._shell_layout.setSpacing(0)
        self._root_layout.addWidget(self.shell)

    def _build_title_bar(self) -> None:
        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(44)
        layout = QHBoxLayout(self.title_bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(9)
        for color in ("#EF4444", "#F59E0B", "#34D399"):
            dot = QLabel()
            dot.setObjectName("dot")
            dot.setFixedSize(11, 11)
            dot.setStyleSheet(f"background:{color};")
            layout.addWidget(dot)
        title = QLabel("scrcpy-gui")
        title.setObjectName("title_text")
        layout.addWidget(title)
        version = QLabel(f"v{__version__}")
        version.setObjectName("ver_text")
        layout.addWidget(version)
        layout.addStretch(1)
        self.appearance_btn = QPushButton("外观")
        self.appearance_btn.setObjectName("appearance_trigger")
        self.appearance_btn.setFixedHeight(28)
        self.appearance_btn.setAccessibleName("切换应用外观")
        self.appearance_btn.clicked.connect(self._show_appearance_popup)
        layout.addWidget(self.appearance_btn)
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setObjectName("title_btn")
        self.minimize_btn.setFixedSize(32, 28)
        self.minimize_btn.setToolTip("最小化")
        self.minimize_btn.setAccessibleName("最小化窗口")
        self.minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.minimize_btn)
        self.maximize_btn = QPushButton("⤢")
        self.maximize_btn.setObjectName("title_btn")
        self.maximize_btn.setFixedSize(32, 28)
        self.maximize_btn.setToolTip("最大化")
        self.maximize_btn.setAccessibleName("最大化窗口")
        self.maximize_btn.clicked.connect(self._toggle_maximized)
        layout.addWidget(self.maximize_btn)
        close = QPushButton("×")
        close.setObjectName("title_btn")
        close.setFixedSize(32, 28)
        close.setToolTip("关闭")
        close.setAccessibleName("关闭窗口")
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self._appearance_popup = AppearancePopover(self)
        self._appearance_popup.appearanceSelected.connect(self._on_appearance_selected)
        self._appearance_popup.setStyleSheet(build_qss(self._theme_tokens))
        self._shell_layout.addWidget(self.title_bar)

    def _build_banner(self) -> None:
        self.banner = StatusBanner(self.shell)
        self._shell_layout.addWidget(self.banner)

    def _build_body(self) -> None:
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 0)
        header_layout.setSpacing(12)
        self.device_bar = DeviceBar()
        header_layout.addWidget(self.device_bar)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(12)
        self.preset_panel = PresetPanel(self._controller)
        toolbar.addWidget(self.preset_panel, 1)
        self.expert_seg = self._build_expert_segment()
        toolbar.addWidget(self.expert_seg)
        header_layout.addLayout(toolbar)
        left_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setObjectName("left_scroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("scroll_content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 0, 16)
        content_layout.setSpacing(12)
        self._cards = build_all_cards(self._register_control, self._controller.state)
        for card in self._cards.values():
            content_layout.addWidget(card)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        scroll_holder = QWidget()
        scroll_holder.setObjectName("left_scroll_holder")
        scroll_holder_layout = QHBoxLayout(scroll_holder)
        scroll_holder_layout.setContentsMargins(0, 0, 14, 0)
        scroll_holder_layout.setSpacing(0)
        scroll_holder_layout.addWidget(scroll)
        left_layout.addWidget(scroll_holder, 1)
        body_layout.addWidget(left, 1)

        self.command_panel = CommandPanel()
        self.command_panel.set_theme_tokens(self._theme_tokens)
        self.command_panel.setFixedWidth(400)
        body_layout.addWidget(self.command_panel)
        self._shell_layout.addWidget(body, 1)

    def _build_expert_segment(self) -> QWidget:
        segment = QWidget()
        segment.setObjectName("seg_wrap")
        segment.setFixedHeight(38)
        layout = QHBoxLayout(segment)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)
        self.segBasic = QPushButton("基础")
        self.segExpert = QPushButton("专家")
        for button in (self.segBasic, self.segExpert):
            button.setObjectName("seg_item")
            button.setCheckable(True)
            button.setFixedSize(60, 32)
        self.segBasic.setChecked(True)
        self.segBasic.clicked.connect(lambda: self._on_expert(False))
        self.segExpert.clicked.connect(lambda: self._on_expert(True))
        layout.addWidget(self.segBasic)
        layout.addWidget(self.segExpert)
        return segment

    def _build_status_bar(self) -> None:
        bar = QWidget()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)
        self.run_dot = QLabel("●")
        self.run_dot.setObjectName("run_dot")
        self.run_label = QLabel("已停止")
        self.run_label.setObjectName("run_label")
        layout.addWidget(self.run_dot)
        layout.addWidget(self.run_label)
        layout.addStretch(1)
        self.stop_btn = QPushButton("停止 ■")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setFixedSize(84, 34)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._controller.stop)
        self.launch_btn = QPushButton("启动 ▶")
        self.launch_btn.setObjectName("launch_btn")
        self.launch_btn.setFixedSize(84, 34)
        self.launch_btn.clicked.connect(self._on_launch)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.launch_btn)
        self._shell_layout.addWidget(bar)

    def _build_toast(self) -> None:
        self.toast = Toast(self.shell)

    def _wire_controller(self) -> None:
        controller = self._controller
        controller.commandChanged.connect(self.command_panel.set_command)
        controller.logLine.connect(self.command_panel.log.append_line)
        controller.runStateChanged.connect(self._on_run_state)
        controller.errorOccurred.connect(self._on_error)
        controller.statusMessage.connect(self.toast.show_message)
        controller.devicesChanged.connect(self._on_devices)
        controller.stateChanged.connect(self._on_state_changed)

    def _wire_controls(self) -> None:
        from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit

        for key, widget in self._controls.items():
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(lambda _checked=False, k=key, w=widget: self._on_control_changed(k, w))
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda _index=0, k=key, w=widget: self._on_control_changed(k, w))
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _text="", k=key, w=widget: self._on_control_changed(k, w))

        device = self.device_bar
        device.connModeChanged.connect(lambda mode: self._controller.set_value("connMode", mode))
        device.deviceChanged.connect(lambda serial: self._controller.set_value("device", serial))
        device.ipChanged.connect(lambda ip: self._controller.set_value("ip", ip))
        device.portChanged.connect(lambda port: self._controller.set_value("port", port))
        device.wifiOptChanged.connect(self._on_wifi_opt)
        device.refreshRequested.connect(self._controller.refresh_devices)
        device.connectWirelessRequested.connect(self._controller.connect_wireless)
        device.autoWirelessRequested.connect(self._controller.auto_connect_wireless)
        self.preset_panel.presetChosen.connect(self._on_preset_chosen)
        self.preset_panel.manageRequested.connect(self._open_manage)
        self.preset_panel.set_presets(self._controller.presets.list())

    def _register_control(self, key: str, widget: QWidget) -> None:
        self._controls[key] = widget

    def _init_command(self) -> None:
        self.command_panel.set_command(self._controller._build_command_preview())

    def _on_control_changed(self, key: str, widget: QWidget) -> None:
        if self._refilling:
            return
        self._controller.set_value(key, read_value(widget))
        self.preset_panel.set_current("")

    def _on_wifi_opt(self, checked: bool) -> None:
        self._controller.set_value("wifiOpt", checked)
        if checked:
            self._controller.set_value("bitrate", "2")
            self._controller.set_value("maxSize", "800")
            write_value(self._controls.get("bitrate"), "2")
            write_value(self._controls.get("maxSize"), "800")
            self.toast.show_message("无线优化已覆盖手动码率/分辨率")
            self.command_panel.log.append_line("[无线优化] 已覆盖手动参数：-b 2M -m 800")

    def _on_preset_chosen(self, name: str) -> None:
        if name:
            self._controller.load_preset(name)
            self.command_panel.log.append_line(f"[预设] 已加载：{name}")
            self.toast.show_message("已应用预设")

    def _on_expert(self, enabled: bool) -> None:
        self.segBasic.setChecked(not enabled)
        self.segExpert.setChecked(enabled)
        self._controller.set_value("expertMode", enabled)
        self._apply_expert(enabled)

    def _apply_expert(self, enabled: bool) -> None:
        for card in self._cards.values():
            card.setVisible(card.kind == "basic" or enabled)

    def _on_launch(self) -> None:
        state = self._controller.state
        if state.get("connMode") == "wifi" and not state.get("ip"):
            self.banner.show_error("请填写无线 IP", "无线模式需先填写 IP 后启动")
            return
        if state.get("connMode") == "usb" and not state.get("device"):
            self.banner.show_error("USB 模式请先选择设备", "未选择设备无法启动")
            return
        self.banner.clear()
        self.command_panel.log.append_line("[启动] 构建命令并拉起 scrcpy …")
        self.command_panel.log.append_line(f"[命令] {self._controller._build_command_preview()}")
        self._controller.launch()

    def _on_run_state(self, running: bool, fps: str, bitrate: str) -> None:
        self.stop_btn.setEnabled(running)
        self.launch_btn.setEnabled(not running)
        self.device_bar.set_running(running)
        bar = self.findChild(QWidget, "statusbar")
        if bar is not None:
            bar.setProperty("running", "true" if running else "false")
            bar.style().unpolish(bar)
            bar.style().polish(bar)
        self.run_label.setText(f"运行中 · {fps} fps · {bitrate} Mbps" if running and (fps or bitrate) else "运行中" if running else "已停止")

    def _on_error(self, title: str, detail: str) -> None:
        self.banner.show_error(title, detail)
        self.command_panel.log.append_line(f"[错误] {title}：{detail}")

    def _on_devices(self, devices, error: str) -> None:
        if error:
            self.command_panel.log.append_line(f"[设备] {error}")
            self.toast.show_message(error)
        self.device_bar.set_devices(devices or [])
        self.command_panel.log.append_line(f"[设备] 发现 {len(devices or [])} 台设备")

    def _on_state_changed(self, state: dict) -> None:
        self._refilling = True
        try:
            for key, widget in self._controls.items():
                write_value(widget, state.get(key))
            self.device_bar.set_conn_mode(state.get("connMode", "usb"))
            self.device_bar.set_ip(state.get("ip", ""))
            self.device_bar.set_port(state.get("port", ""))
            self.device_bar.set_wifi_opt(state.get("wifiOpt", False))
            self.preset_panel.set_current(state.get("preset_name", ""))
            self.segBasic.setChecked(not bool(state.get("expertMode", False)))
            self.segExpert.setChecked(bool(state.get("expertMode", False)))
            self._apply_expert(bool(state.get("expertMode", False)))
        finally:
            self._refilling = False

    def _show_appearance_popup(self) -> None:
        if self._appearance_popup is not None:
            self._appearance_popup.show_for(self.appearance_btn, self._appearance)

    def _on_appearance_selected(self, theme: str, custom_bg: object) -> None:
        appearance = Appearance(theme=theme, custom_bg=str(custom_bg) if custom_bg else None)
        self._apply_appearance(appearance)
        if not self._appearance_store.save(appearance):
            self.toast.show_message("外观已应用，但无法保存设置")
        if self._appearance_popup is not None:
            self._appearance_popup.hide()

    def _apply_appearance(self, appearance: Appearance) -> None:
        self._appearance = appearance
        self._theme_tokens = tokens_for(appearance)
        qss = build_qss(self._theme_tokens)
        self.setStyleSheet(qss)
        self.command_panel.set_theme_tokens(self._theme_tokens)
        if self._appearance_popup is not None:
            self._appearance_popup.setStyleSheet(qss)
            self._appearance_popup.set_current(appearance)

    def _open_manage(self) -> None:
        dialog = PresetManageDialog(self._controller, self)
        dialog.presetsChanged.connect(lambda: self.preset_panel.set_presets(self._controller.presets.list()))
        dialog.exec()

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _sync_window_chrome(self) -> None:
        """根据窗口状态调整外层留白，避免最大化后仍保留悬浮外框。"""
        maximized = self.isMaximized()
        margin = 0 if maximized else 8
        self._root_layout.setContentsMargins(margin, margin, margin, margin)
        state = "true" if maximized else "false"
        self.setProperty("maximized", state)
        self.shell.setProperty("maximized", state)
        self.maximize_btn.setText("❐" if maximized else "⤢")
        self.maximize_btn.setToolTip("还原窗口" if maximized else "最大化")
        self.maximize_btn.setAccessibleName("还原窗口" if maximized else "最大化窗口")
        for widget in (self, self.shell, self.title_bar):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_window_chrome()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 64:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        event.accept()

    def closeEvent(self, event) -> None:
        self._controller.shutdown()
        event.accept()


def main() -> None:
    import sys

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("scrcpy-gui")
    window = MainWindow(AppController())
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
