"""AdbWorker：纯搬运 Worker，把 ``core.adb`` 的同步函数搬到子线程执行。

设计约束（硬）：
- 本 Worker **不持有 state、不解析日志、不发射业务信号**；只调用 ``core.adb.*``
  并把 ``(code, out, err)`` 经 ``finished`` 回传主线程，异常经 ``error`` 回传。
- 所有 adb 调用必须经本 Worker（或等价子线程封装），严禁 UI 线程同步 subprocess。
- ``serial`` 由 controller 在调用前通过 ``worker.serial`` 属性传入，保证多设备隔离。
- 异常兜底：``try/except`` 包住 ``core.adb.*``，异常 ``emit error(str(e))``，
  绝不抛到线程外。
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

import core.adb as adb


class AdbWorker(QObject):
    """在 QThread 上运行的 adb 搬运工。

    用法（由 ``AppController`` 编排）：
        worker = AdbWorker()
        worker.moveToThread(thread)
        QMetaObject.invokeMethod(worker, "run_list_devices", Qt.QueuedConnection)
    """

    # (code, out, err)：与 core.adb 各函数返回三元组对齐
    finished = pyqtSignal(tuple)
    # 异常信息字符串
    error = pyqtSignal(str)
    # 在线检查结果（设备掉线监听器专用）：当前 serial / wifi 地址是否仍在 adb 在线列表
    online_checked = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # 多设备隔离用的 serial；由 controller 在调用前设置（默认 None = 单设备）
        self.serial: str | None = None

    @pyqtSlot()
    def run_get_ip(self) -> None:
        """调用 ``core.adb.get_device_ip(self.serial)`` -> emit finished((code, ip, err))。

        与 ``run_*`` 同风格：``out`` 槽位承载 IP 字符串，满足控制器三元解包。
        """
        try:
            ip, err = adb.get_device_ip(self.serial)
            code = 0 if ip else 1
            self.finished.emit((code, ip, err))
        except Exception as e:  # noqa: BLE001 - 异常兜底，转信号回主线程
            self.error.emit(str(e))

    @pyqtSlot()
    def run_list_devices(self) -> None:
        """调用 ``core.adb.list_devices()`` -> emit finished((code, devices, err))。"""
        try:
            devices, err = adb.list_devices()
            code = 0 if not err else 1
            self.finished.emit((code, devices, err))
        except Exception as e:  # noqa: BLE001 - 异常兜底，转信号回主线程
            self.error.emit(str(e))

    @pyqtSlot(int)
    def run_tcpip(self, port: int = 5555) -> None:
        """调用 ``core.adb.tcpip(port, serial=...)`` -> emit finished。"""
        try:
            code, out, err = adb.tcpip(port, serial=self.serial)
            self.finished.emit((code, out, err))
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))

    @pyqtSlot(str, int)
    def run_connect(self, ip: str, port: int = 5555) -> None:
        """调用 ``core.adb.connect(ip, port, serial=...)`` -> emit finished。"""
        try:
            code, out, err = adb.connect(ip, port, serial=self.serial)
            self.finished.emit((code, out, err))
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))

    @pyqtSlot()
    def run_usb(self) -> None:
        """调用 ``core.adb.usb(serial=...)`` -> emit finished。"""
        try:
            code, out, err = adb.usb(serial=self.serial)
            self.finished.emit((code, out, err))
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))

    @pyqtSlot(str, str)
    def run_check_online(self, serial: str, wifi_addr: str) -> None:
        """设备掉线检测：检查 ``serial`` 与 ``wifi_addr``（二选一）是否仍在
        ``adb devices`` 在线列表（status=="device"）。结果经 ``online_checked``
        回传，绝不参与 ``finished``/``_pending_op`` 派发，避免与无线连接等操作互斥。
        """
        try:
            devices, _err = adb.list_devices()
            cands = [c for c in (serial, wifi_addr) if c]
            online = any(
                s in cands and status == "device"
                for (s, status, _info) in devices
            )
            self.online_checked.emit(online)
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))
