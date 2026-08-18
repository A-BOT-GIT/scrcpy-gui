"""Demo 结构的设备连接卡片，只负责视图和信号。"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class DeviceBar(QWidget):
    connModeChanged = pyqtSignal(str)
    deviceChanged = pyqtSignal(str)
    ipChanged = pyqtSignal(str)
    portChanged = pyqtSignal(str)
    wifiOptChanged = pyqtSignal(bool)
    refreshRequested = pyqtSignal()
    connectWirelessRequested = pyqtSignal()
    autoWirelessRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("device_bar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        heading = QLabel("连接")
        heading.setObjectName("db_title")
        root.addWidget(heading)

        segment = QWidget()
        segment.setObjectName("segmented")
        segment_layout = QHBoxLayout(segment)
        segment_layout.setContentsMargins(3, 3, 3, 3)
        segment_layout.setSpacing(0)
        self.segUsb = self._segment_button("USB")
        self.segWifi = self._segment_button("无线")
        self.segUsb.setChecked(True)
        self.segUsb.clicked.connect(lambda: self._select_mode("usb"))
        self.segWifi.clicked.connect(lambda: self._select_mode("wifi"))
        segment_layout.addWidget(self.segUsb)
        segment_layout.addWidget(self.segWifi)
        segment_row = QHBoxLayout()
        segment_row.setContentsMargins(0, 0, 0, 0)
        segment_row.addWidget(segment)
        segment_row.addStretch(1)
        root.addLayout(segment_row)

        auto_row = QHBoxLayout()
        auto_row.setContentsMargins(0, 0, 0, 0)
        self.autoBtn = QPushButton("一键无线投屏")
        self.autoBtn.setObjectName("auto_wifi")
        self.autoBtn.setFixedSize(172, 34)
        self.autoBtn.setToolTip("通过已选 USB 设备自动建立无线投屏")
        self.autoBtn.clicked.connect(self.autoWirelessRequested.emit)
        auto_row.addWidget(self.autoBtn)
        auto_row.addStretch(1)
        root.addLayout(auto_row)

        device_row = QHBoxLayout()
        device_row.setContentsMargins(0, 0, 0, 0)
        device_row.setSpacing(8)
        label = QLabel("设备")
        label.setObjectName("toolbar_label")
        label.setFixedWidth(40)
        device_row.addWidget(label)
        self.deviceCombo = QComboBox()
        self.deviceCombo.setFixedHeight(34)
        self.deviceCombo.addItem("（未选择）", "")
        self.deviceCombo.currentIndexChanged.connect(lambda _: self.deviceChanged.emit(self.deviceCombo.currentData() or ""))
        device_row.addWidget(self.deviceCombo, 1)
        self.refreshBtn = QPushButton("刷新")
        self.refreshBtn.setObjectName("btn_secondary")
        self.refreshBtn.setFixedSize(56, 34)
        self.refreshBtn.clicked.connect(self.refreshRequested.emit)
        device_row.addWidget(self.refreshBtn)
        root.addLayout(device_row)

        self.usbHint = QLabel("USB 直连：选中设备后直接点底部启动")
        self.usbHint.setObjectName("hint")
        root.addWidget(self.usbHint)

        self.wifiRow = QWidget()
        wifi_layout = QHBoxLayout(self.wifiRow)
        wifi_layout.setContentsMargins(0, 0, 0, 0)
        wifi_layout.setSpacing(8)
        wifi_layout.addWidget(QLabel("无线 IP"))
        self.ipLine = QLineEdit()
        self.ipLine.setFixedHeight(34)
        self.ipLine.setPlaceholderText("192.168.1.10")
        self.ipLine.textChanged.connect(lambda text: self.ipChanged.emit(text.strip()))
        wifi_layout.addWidget(self.ipLine, 1)
        wifi_layout.addWidget(QLabel("端口"))
        self.portLine = QLineEdit("5555")
        self.portLine.setFixedSize(72, 34)
        self.portLine.textChanged.connect(lambda text: self.portChanged.emit(text.strip()))
        wifi_layout.addWidget(self.portLine)
        self.connectBtn = QPushButton("无线连接")
        self.connectBtn.setObjectName("btn_secondary")
        self.connectBtn.setFixedHeight(34)
        self.connectBtn.clicked.connect(self.connectWirelessRequested.emit)
        wifi_layout.addWidget(self.connectBtn)
        root.addWidget(self.wifiRow)

        self.wifiOpt = QCheckBox("无线优化预设 (-b 2M -m 800)")
        self.wifiOpt.setObjectName("wifi_opt")
        self.wifiOpt.toggled.connect(self.wifiOptChanged.emit)
        self.wifiRow.setVisible(False)
        root.addWidget(self.wifiOpt)
        self.wifiOpt.setVisible(False)

    @staticmethod
    def _segment_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("seg_item")
        button.setCheckable(True)
        button.setFixedSize(104, 32)
        return button

    def _select_mode(self, mode: str) -> None:
        self.set_conn_mode(mode)
        self.connModeChanged.emit(mode)

    def set_conn_mode(self, mode: str) -> None:
        is_wifi = mode == "wifi"
        self.segUsb.setChecked(not is_wifi)
        self.segWifi.setChecked(is_wifi)
        self.usbHint.setVisible(not is_wifi)
        self.wifiRow.setVisible(is_wifi)
        self.wifiOpt.setVisible(is_wifi)

    def set_devices(self, devices) -> None:
        current = self.deviceCombo.currentData() or ""
        self.deviceCombo.blockSignals(True)
        self.deviceCombo.clear()
        self.deviceCombo.addItem("（未选择）", "")
        for serial, status, info in devices:
            if status == "device":
                label = f"{info} ({serial})" if info else serial
            elif status == "unauthorized":
                label = f"{serial}（未授权·请在手机点允许）"
            elif status == "offline":
                label = f"{serial}（离线·请重插 USB）"
            else:
                label = f"{serial}（{status}）"
            self.deviceCombo.addItem(label, serial)
        index = self.deviceCombo.findData(current)
        self.deviceCombo.setCurrentIndex(index if index >= 0 else 0)
        self.deviceCombo.blockSignals(False)

    def set_ip(self, text: str) -> None:
        if self.ipLine.text() != (text or ""):
            self.ipLine.setText(text or "")

    def set_port(self, text: str) -> None:
        value = text or "5555"
        if self.portLine.text() != value:
            self.portLine.setText(value)

    def set_wifi_opt(self, enabled: bool) -> None:
        self.wifiOpt.setChecked(bool(enabled))

    def set_running(self, running: bool) -> None:
        for widget in (self.autoBtn, self.connectBtn, self.deviceCombo, self.ipLine, self.portLine, self.wifiOpt):
            widget.setEnabled(not running)
