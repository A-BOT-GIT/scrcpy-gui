"""无线连接状态机（ConnectionStateMachine）。

与 GUI 解耦的纯逻辑组件：持有 5 态 ``ConnState`` 枚举，每次迁移先更新
``self.current``，再发射 ``stateChanged(state_value, msg)``。状态枚举一律从
``app.signals`` 导入，禁止在此文件重定义。

本组件不持有 state 字典、不解析日志、不调用 adb —— 只做状态迁移与信号发射，
由 ``AppController`` 订阅 ``stateChanged`` 来驱动业务（如 T6 的持久状态展示）。
"""

from PyQt6.QtCore import QObject, pyqtSignal

from app.signals import ConnState


class ConnectionStateMachine(QObject):
    """无线连接状态机：IDLE → TCPIP → CONNECTING → READY / FAILED。

    迁移规则（硬约束）：
    - 每次迁移先更新 ``self.current``，再 ``emit stateChanged(self.current.value, msg)``。
    - ``reset()`` 回到 IDLE，用于连接结束 / 切回 USB。
    """

    # (state_value:str, msg:str)
    stateChanged = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.current: ConnState = ConnState.IDLE

    def to_tcpip(self, msg: str = "") -> None:
        """进入 TCPIP 态（已执行 adb tcpip，等待 connect）。"""
        self.current = ConnState.TCPIP
        self.stateChanged.emit(self.current.value, msg)

    def to_connecting(self, msg: str = "") -> None:
        """进入 CONNECTING 态（正在 adb connect）。"""
        self.current = ConnState.CONNECTING
        self.stateChanged.emit(self.current.value, msg)

    def to_ready(self, msg: str = "") -> None:
        """进入 READY 态（已就绪，可拔线启动）。"""
        self.current = ConnState.READY
        self.stateChanged.emit(self.current.value, msg)

    def to_failed(self, msg: str) -> None:
        """进入 FAILED 态（失败，附带错误信息）。"""
        self.current = ConnState.FAILED
        self.stateChanged.emit(self.current.value, msg)

    def reset(self) -> None:
        """回到 IDLE 态。"""
        self.current = ConnState.IDLE
        self.stateChanged.emit(self.current.value, "")
