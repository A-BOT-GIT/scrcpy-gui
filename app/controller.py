"""AppController：逻辑层核心（MVP Presenter）。

职责：
- 持有 state 字典（来自 ``app.signals.default_state`` 的深拷贝）。
- 编排 ``AdbWorker``（QThread 子线程）执行所有 adb 操作，结果经信号回主线程。
- 驱动 ``ConnectionStateMachine`` 做无线连接 5 态迁移。
- 管 ``QProcess`` 拉起 scrcpy 并解析其日志（fps / 码率）。
- 通过 ``PresetManager`` 做预设增删改查。
- 对外复用 ``ControllerSignals`` 的 8 个信号（直接多继承，信号签名完全一致）。

硬约束：
- 所有 adb 调用必须经 ``AdbWorker`` 子线程，UI 线程绝不同步 subprocess。
- 信号 / 枚举 / state 键一律从 ``app.signals`` 导入，禁止硬编码。
- 日志正则解析放本层（``_parse_log``），视图层（T4 的 LogPanel）只 append_line + 着色。
"""

import os
import re
from datetime import datetime

from PyQt6.QtCore import (
    QObject,
    QThread,
    QMetaObject,
    Qt,
    Q_ARG,
    QProcess,
    QTimer,
)

from app.signals import ControllerSignals, ConnState, default_state
from app.connection_fsm import ConnectionStateMachine
from workers.adb_worker import AdbWorker
from core.presets import PRESETTABLE_KEYS, PresetManager, is_presettable
from core.launcher import build_args, launch_qprocess


# 日志解析正则（放逻辑层，视图层不解析）
_BR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*Mbps")
_FPS_RE = re.compile(r"(\d+)\s*fps")

# 会话级运行日志落盘目录（位于 scrcpy-gui/logs/），断流后可事后排查
_LOGS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
)


def _exit_reason(code: int, status_name: str) -> str:
    """把 scrcpy 退出码 + 退出状态映射成中文可读原因（用于运行日志）。

    scrcpy 退出码语义（见 scrcpy 源码）：
      - 0 = 正常（用户关闭 / 设备断开 / 达到退出条件）
      - 1 = 启动 / 参数错误（如不支持的编码名、无效参数）
      - 2 = 设备 / 运行时错误（如设备无该编码器、初始化失败）
    注意：经由 subprocess 包装拿到的非 0 都是 scrcpy **主动 exit**，并非被信号
    杀死；仅当 status_name 为 CrashExit 且退出码不在 {0,1,2} 时才视作真异常终止。
    """
    if code == 0:
        return "正常退出（设备断开 / 用户关闭 / 达到退出条件）"
    if code == 1:
        return "启动失败：参数无效或设备/编码不支持（详见上方 SCRCPY 日志）"
    if code == 2:
        return "运行错误：设备不支持所选编码或配置（详见上方 SCRCPY 日志）"
    if status_name == "CrashExit":
        return "进程被异常终止（可能被系统/连接层杀死）"
    return f"未知退出码 {code}"


class AppController(ControllerSignals):
    """逻辑层核心控制器。

    信号直接继承 ``ControllerSignals``（其已继承 ``QObject``），因此 8 个
    ``pyqtSignal`` 天然成为实例信号，controller 可直接 ``self.xxx.emit(...)``，
    信号签名与 ``app.signals.ControllerSignals`` 完全一致。
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # —— 状态字典（每次 default_state() 都是全新 dict）——
        self.state: dict = default_state()
        # —— 子组件 ——
        self.fsm = ConnectionStateMachine(self)
        self.presets = PresetManager()
        self.worker = AdbWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        # —— 运行期对象 ——
        self._proc: QProcess | None = None
        self._scrcpy_log: list = []  # 本次会话累积的 SCRCPY 原始行（退出时提炼报错）
        # —— 会话级运行日志（更底层：时间戳 + 落盘 + 设备掉线监听）——
        self._log_fp = None            # 会话日志文件句柄（None=未打开）
        self._device_was_online = True  # 设备掉线去抖：只在「在线→离线」跳变时记一次
        self._user_stopping = False     # 用户主动停止标记：避免「停止」被误报为崩溃
        # 设备掉线监听器：每 2s 经 worker 子线程查 adb 在线状态
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(2000)
        self._log_timer.timeout.connect(self._poll_device_online)
        # —— 异步编排内部状态 ——
        self._pending_op: str | None = None  # 当前在途的 worker 操作类型
        self._wifi_ip: str = ""
        self._wifi_port: int = 5555
        # —— 信号接线（跨线程自动 QueuedConnection）——
        self.worker.finished.connect(self._on_worker_done)
        self.worker.error.connect(self._on_worker_error)
        self.worker.online_checked.connect(self._on_device_online_checked)
        self.thread.start()

    # ======================= public slots（T4 接入契约） =======================

    def set_value(self, key: str, value) -> None:
        """更新 state 并广播命令预览（commandChanged）。"""
        self.state[key] = value
        self.commandChanged.emit(self._build_command_preview())

    def refresh_devices(self) -> None:
        """经 worker 子线程刷新设备列表。"""
        self._pending_op = "list"
        self.worker.serial = self.state.get("device", "")
        QMetaObject.invokeMethod(
            self.worker, "run_list_devices", Qt.ConnectionType.QueuedConnection
        )

    def connect_wireless(self) -> None:
        """异步编排无线连接：tcpip → connecting → ready。"""
        if self.fsm.current not in (ConnState.IDLE, ConnState.FAILED):
            # 已在进行中，忽略重复触发
            return
        ip = self.state.get("ip", "")
        port = self.state.get("port", "") or 5555
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = 5555
        if not ip:
            self.errorOccurred.emit("无线连接失败", "未填写 IP 地址")
            return
        self._wifi_ip = ip
        self._wifi_port = port
        self.worker.serial = self.state.get("device", "")
        self._pending_op = "wifi_tcpip"
        self.fsm.to_tcpip("正在开启 TCP/IP 监听")
        QMetaObject.invokeMethod(
            self.worker,
            "run_tcpip",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, port),
        )

    def back_to_usb(self) -> None:
        """经 worker 子线程切回 USB。"""
        self.worker.serial = self.state.get("device", "")
        self._pending_op = "usb"
        QMetaObject.invokeMethod(
            self.worker, "run_usb", Qt.ConnectionType.QueuedConnection
        )

    def auto_connect_wireless(self) -> None:
        """真·一键自动无线投屏：探测 WiFi IP → adb tcpip → adb connect → launch()。

        目标设备 = 当前下拉选中的 serial（state["device"]）。全程无需手填 IP、
        无需二次点击。多设备时 device 即目标，tcpip 模式下 build_args 跳过 -s device
        （无线参数覆盖 serial），device（USB serial）原值保留。
        """
        if self.fsm.current not in (ConnState.IDLE, ConnState.FAILED):
            # 已在进行中，忽略重复触发
            return
        serial = self.state.get("device", "")
        if not serial:
            self.errorOccurred.emit("自动无线投屏失败", "未选择设备")
            return
        self.worker.serial = serial
        self._pending_op = "auto_get_ip"
        self.fsm.to_tcpip("正在探测设备 WiFi IP")
        QMetaObject.invokeMethod(
            self.worker, "run_get_ip", Qt.ConnectionType.QueuedConnection
        )

    def launch(self) -> "QProcess | None":
        """拼参并拉起 scrcpy（QProcess 异步，主线程调用不阻塞）。

        健壮性（修复点击「启动」时的
        ``AttributeError: 'NoneType' object has no attribute
        'readyReadStandardOutput'`` 崩溃）：
        - 进入时若上一次拉起的进程仍在运行，先 ``kill()`` 再置
          ``None``，避免覆盖 ``self._proc`` 导致旧进程变孤儿（stderr
          报 "QProcess: Destroyed while process is still running"）。
        - ``launch_qprocess`` 返回 ``None``（极端情况下 QProcess 未能
          创建/启动）时，发射错误信号并 ``return None``，不再访问
          ``None`` 属性而崩溃。
        """
        # 1) 清理上一次未结束的投屏进程：先 kill 再置 None，
        #    杜绝孤儿进程 + 消除竞态窗口
        self._user_stopping = False  # 新会话：清除「用户停止」标记
        if self._proc is not None:
            if self._proc.state() != QProcess.ProcessState.NotRunning:
                try:
                    self._proc.kill()
                except Exception:  # noqa: BLE001
                    pass
            self._proc = None

        args = build_args(self.state)
        proc = launch_qprocess(args)
        # 2) 守卫：QProcess 未成功创建时不崩溃，改发错误信号
        if proc is None:
            self.runStateChanged.emit(False, "", "")
            self.errorOccurred.emit(
                "启动失败",
                "未找到 scrcpy。请运行 scripts/setup-scrcpy.ps1，设置 SCRCPY_HOME，"
                "或将官方 scrcpy 加入 PATH。",
            )
            return None
        self._proc = proc
        self._proc.readyReadStandardOutput.connect(self._on_proc_output)
        self._proc.finished.connect(self._on_proc_finished)
        self._proc.errorOccurred.connect(self._on_proc_error)
        self._start_session_logging()
        self.runStateChanged.emit(True, "", "")
        return self._proc

    def stop(self) -> None:
        """停止 scrcpy（用户主动停止：不应误报为崩溃红条）。"""
        if self._proc is not None:
            self._user_stopping = True
            if self._proc.state() != QProcess.ProcessState.NotRunning:
                self._proc.kill()
            # 保留 _proc 引用直到 _on_proc_finished 处理完（避免丢失退出缓冲 / 状态）
        self._stop_session_logging()
        self.runStateChanged.emit(False, "", "")

    def load_preset(self, name: str) -> None:
        """加载预设到 state（**纯净覆盖**语义：未包含字段先重置为默认，再应用预设）。

        - 仅把预设 ``params`` 中可入预设的键合并进当前 ``state``；
        - 预设**未包含**的可入预设键先重置为 ``default_state()`` 默认值，
          消除「上一个预设 / 手动调整」的残留参数（如从带 bitrate 的预设切到
          不含 bitrate 的预设，bitrate 应回到默认而非残留）；
        - 连接/运行时键（device / ip / connMode / port / preset_name 等）
          一律保持不变，彻底解决「选预设冲掉已选设备/连接模式」；
        - 设置 ``state["preset_name"] = name`` 并广播 stateChanged / commandChanged。
        """
        loaded = self.presets.load(name)
        if loaded is None:
            self.errorOccurred.emit("加载预设失败", f"预设不存在：{name}")
            return
        params = loaded.get("params", {})
        base = default_state()
        for k in PRESETTABLE_KEYS:
            if k in base and k not in params:
                self.state[k] = base[k]      # 未含字段回到默认，消除残留
        for k, v in params.items():
            if is_presettable(k):
                self.state[k] = v
        # 设备/环境相关字段跨设备可能失效，给出软提示（不阻断加载）
        soft = []
        if params.get("displayId"):
            soft.append("副屏编号 displayId 将在启动时校验，若设备无副屏会报错")
        if params.get("recPath"):
            soft.append("录制路径 recPath 跨设备/目录可能不存在，请确认有效")
        if soft:
            self.statusMessage.emit("；".join(soft))
        self.state["preset_name"] = name
        self.stateChanged.emit(self.state)
        self.commandChanged.emit(self._build_command_preview())

    def save_preset(
        self,
        name: str,
        include_keys=None,
        description: str = "",
        *,
        overwrite: bool = True,
    ) -> None:
        """保存当前 state 的指定字段为预设（默认全部可入预设键）。

        ``include_keys`` 为本次要纳入的键集合（即「设置」勾选结果）；
        仅其中可入预设且存在于 state 的键会被写入，连接键被静默丢弃。
        """
        include = list(include_keys) if include_keys else list(PRESETTABLE_KEYS)
        params = {
            k: self.state[k]
            for k in include
            if is_presettable(k) and k in self.state
        }
        self.presets.save(name, params, description, overwrite=overwrite)

    def update_preset(self, name: str, include_keys, description: str = "", from_current: bool = False) -> None:
        """编辑既有预设。

        - ``from_current=False``（默认，安全）：保留预设**原参数值**，仅按 ``include_keys``
          调整「包含哪些字段」并刷新描述；不会用当前主窗口 state 覆盖预设，
          避免「只改描述却把参数冲掉」的污染。
        - ``from_current=True``：用当前主窗口 state 的勾选字段覆盖预设参数
          （= 把当前界面配置存回预设），由对话框「用界面更新」按钮显式触发。
        """
        if from_current:
            self.save_preset(name, include_keys, description, overwrite=True)
            return
        rec = self.presets.load(name)
        orig = (rec or {}).get("params", {}) if rec is not None else {}
        params = {k: orig[k] for k in include_keys if k in orig and is_presettable(k)}
        self.presets.save(name, params, description, overwrite=True)

    def rename_preset(self, old: str, new: str) -> None:
        """重命名预设；若当前活动预设命中，同步迁移 ``state["preset_name"]``。"""
        self.presets.rename(old, new)
        if self.state.get("preset_name") == old:
            self.state["preset_name"] = new
            self.stateChanged.emit(self.state)

    def delete_preset(self, name: str) -> None:
        """删除预设；若删除的是当前活动预设，清空 ``state["preset_name"]`` 并广播。"""
        self.presets.delete(name)
        if self.state.get("preset_name") == name:
            self.state["preset_name"] = ""
            self.stateChanged.emit(self.state)

    # ============================ 私有：worker 回调 ============================

    def _on_worker_done(self, result: tuple) -> None:
        """worker.finished 回主线程的统一步骤分发器。"""
        code, out, err = result
        op = self._pending_op
        self._pending_op = None

        if op == "list":
            devices = out if isinstance(out, list) else []
            self.devicesChanged.emit(devices, err or "")
            return

        if op == "wifi_tcpip":
            if code != 0:
                self.fsm.to_failed(err or "adb tcpip 失败")
                self.errorOccurred.emit("无线连接失败", err or "adb tcpip 失败")
                self.refresh_devices()
                return
            # tcpip 成功 -> 进入 connecting 并触发 connect
            self._pending_op = "wifi_connect"
            self.fsm.to_connecting("正在 adb connect")
            QMetaObject.invokeMethod(
                self.worker,
                "run_connect",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self._wifi_ip),
                Q_ARG(int, self._wifi_port),
            )
            return

        if op == "wifi_connect":
            if code != 0:
                self.fsm.to_failed(err or "adb connect 失败")
                self.errorOccurred.emit("无线连接失败", err or "adb connect 失败")
                self.refresh_devices()
                return
            self.fsm.to_ready("无线连接就绪")
            serial = self.state.get("device", "")
            self.connStateChanged.emit(serial, ConnState.READY.value, "无线连接就绪")
            self.refresh_devices()
            return

        if op == "usb":
            if code != 0:
                self.errorOccurred.emit("切回 USB 失败", err or "adb usb 失败")
                self.refresh_devices()
                return
            self.fsm.reset()
            self.connStateChanged.emit(
                self.state.get("device", ""), ConnState.IDLE.value, "已切回 USB"
            )
            self.statusMessage.emit("已切回 USB 模式")
            self.refresh_devices()
            return

        if op == "auto_get_ip":
            code, ip, err = result
            if code != 0:
                self.fsm.to_failed(err or "探测 IP 失败")
                self.errorOccurred.emit("自动无线投屏失败", err or "探测 IP 失败")
                self.refresh_devices()
                return
            self._wifi_ip = ip
            # 复用现有 port 解析套路：空串回退 5555，非数字回退 5555
            port_raw = self.state.get("port", "") or 5555
            try:
                port = int(port_raw)
            except (TypeError, ValueError):
                port = 5555
            self._wifi_port = port
            self._pending_op = "auto_tcpip"
            self.fsm.to_tcpip("正在开启 TCP/IP 监听")
            QMetaObject.invokeMethod(
                self.worker,
                "run_tcpip",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, port),
            )
            return

        if op == "auto_tcpip":
            code, out, err = result
            if code != 0:
                self.fsm.to_failed(err or "adb tcpip 失败")
                self.errorOccurred.emit("自动无线投屏失败", err or "adb tcpip 失败")
                self.refresh_devices()
                return
            self._pending_op = "auto_connect"
            self.fsm.to_connecting("正在 adb connect")
            QMetaObject.invokeMethod(
                self.worker,
                "run_connect",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self._wifi_ip),
                Q_ARG(int, self._wifi_port),
            )
            return

        if op == "auto_connect":
            code, out, err = result
            if code != 0:
                self.fsm.to_failed(err or "adb connect 失败")
                self.errorOccurred.emit("自动无线投屏失败", err or "adb connect 失败")
                self.refresh_devices()
                return
            self.fsm.to_ready("无线连接就绪")
            serial = self.state.get("device", "")
            self.connStateChanged.emit(serial, ConnState.READY.value, "无线连接就绪")
            # 回填 tcpip/ip/port（不回填空 connMode、不回填空 device —— 见拍板 #2/#4）
            self.set_value("tcpip", True)
            self.set_value("ip", self._wifi_ip)
            self.set_value("port", self._wifi_port)
            self.refresh_devices()
            self.launch()  # 直接拉起投屏
            return

    def _on_worker_error(self, msg: str) -> None:
        """worker.error 回主线程：统一转 errorOccurred。"""
        self._pending_op = None
        self.errorOccurred.emit("adb 失败", msg)
        self.statusMessage.emit(f"adb 错误：{msg}")

    def _parse_log(self, line: str) -> tuple[str, str]:
        """解析 scrcpy 日志中的 fps / 码率，命中时发射 runStateChanged。

        返回 ``(fps, br)``，未命中返回 ``("", "")``。正则来自共享知识约定：
        ``(\\d+(?:\\.\\d+)?)\\s*Mbps``、``(\\d+)\\s*fps``。

        视图层（T4 LogPanel）只 ``append_line`` + 着色，不解析。
        """
        if not line:
            return "", ""
        m_br = _BR_RE.search(line)
        m_fps = _FPS_RE.search(line)
        br = m_br.group(1) if m_br else ""
        fps = m_fps.group(1) if m_fps else ""
        if br or fps:
            self.runStateChanged.emit(True, fps, br)
        return fps, br

    # ============================ 私有：会话级运行日志 ============================
    # 目标（更底层的运行日志）：
    # - 每行带 [时:分:秒.毫秒] + [级别] 前缀，便于定位「断在哪个时刻」；
    # - 同时进日志面板（logLine 信号）与落盘文件（logs/session_*.log），
    #   后者在崩溃/关闭后仍能事后排查；
    # - 捕获 QProcess.errorOccurred（进程层崩溃/连接错误，原完全缺失）；
    # - 退出时记录退出码 + 退出状态（NormalExit/CrashExit）+ 可读原因；
    # - 会话期间每 2s 经 worker 子线程查 adb 在线状态，设备先于
    #   scrcpy 在传输层掉线时立即记 DEVICE 事件。

    def _emit_log(self, level: str, text: str) -> None:
        """统一日志出口：带时间戳 + 级别，进面板 + 落盘。"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] [{level}] {text}"
        self.logLine.emit(line)
        if self._log_fp is not None:
            try:
                self._log_fp.write(line + "\n")
                self._log_fp.flush()
            except Exception:  # noqa: BLE001 - 落盘失败不影响投屏
                pass

    def _on_proc_output(self) -> None:
        """读取 QProcess 合并流（stdout+stderr 已 MergedChannels），逐行记 SCRCPY 级。

        零参签名：直接 connect 到 ``readyReadStandardOutput`` 信号
        （该信号不传参），读取动作在方法内从 ``self._proc`` 取。
        """
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in data.splitlines():
            if not line.strip():
                continue
            self._parse_log(line)  # 保留 fps/码率解析 → 状态栏指示灯
            self._emit_log("SCRCPY", line)
            self._scrcpy_log.append(line)
            if len(self._scrcpy_log) > 500:  # 防内存膨胀
                del self._scrcpy_log[: len(self._scrcpy_log) - 500]

    def _on_proc_error(self, err) -> None:
        """QProcess 进程级错误（崩溃/启动失败/读写错误）—— 原完全缺失。"""
        name = getattr(err, "name", str(err))
        self._emit_log("PROC-ERR", f"{name}：{err}")

    def _on_proc_finished(self, exit_code: int, exit_status) -> None:
        """scrcpy 退出：先抓取退出时刷出的缓冲输出，再记录退出原因。

        关键：scrcpy 的 stdout 在非 TTY（QProcess 管道）下为**块缓冲**，
        运行期不 flush，进程退出时才一次性刷出——其中恰好包含最关键的
        ``WARN: Device disconnected`` 等断流线索。必须在 ``_proc`` 置 None
        之前读取，否则缓冲随进程销毁而丢失。
        """
        if self._proc is not None:
            try:
                # 趁 _proc 未置空，抓取退出时刷出的块缓冲（含断流 WARN）。
                # _on_proc_output 现在零参、自读 self._proc，与信号契约一致。
                self._on_proc_output()
            except Exception:  # noqa: BLE001 - 读取失败不影响退出处理
                pass
        if self._user_stopping:
            # 用户主动停止：stop() 已置位此标记。Windows 上 kill 经 TerminateProcess
            # 返回退出码 1（POSIX 为 -signal），这是正常关闭，绝不可填
            # 「启动失败 / 进程崩溃」误导日志与状态。
            status_name = "NormalExit"
            reason = "用户主动停止（正常关闭）"
        else:
            status_name = (
                "NormalExit" if exit_status == QProcess.ExitStatus.NormalExit
                else "CrashExit"
            )
            reason = _exit_reason(exit_code, status_name)
        self._emit_log(
            "SESSION",
            f"scrcpy 退出 码={exit_code} 状态={status_name} 原因={reason}",
        )
        if exit_code != 0 and not self._user_stopping:
            # 提炼 scrcpy 报错行，给出可读红条提示（而非笼统「进程崩溃」）。
            # _scrcpy_log 在上方 _on_proc_output 抓取缓冲时已补全退出时的 ERROR 行。
            # 用户主动「停止」(kill → 退出码 -1) 属于正常关闭，不弹红条。
            errs = [l for l in self._scrcpy_log if "ERROR" in l.upper()]
            snippet = (
                "；".join(errs[-2:]) if errs else _exit_reason(exit_code, status_name)
            )
            title = "启动失败" if exit_code in (1, 2) else "scrcpy 异常退出"
            self.errorOccurred.emit(title, snippet)
        self._stop_session_logging()
        self.runStateChanged.emit(False, "", "")
        self.statusMessage.emit(f"scrcpy 已退出（退出码 {exit_code}）")
        self._user_stopping = False
        self._proc = None

    # ----- 会话日志落盘 / 设备掉线监听 -----

    def _wifi_addr(self) -> str:
        """当前无线连接地址（ip:port）；非无线模式返回空串。"""
        if self.state.get("connMode") != "wifi":
            return ""
        ip = self.state.get("ip", "")
        if not ip:
            return ""
        port = self.state.get("port", "") or 5555
        return f"{ip}:{port}"

    def _start_session_logging(self) -> None:
        """打开会话日志文件（logs/session_<时间戳>.log），写会话头，启动掉线监听。"""
        try:
            os.makedirs(_LOGS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(_LOGS_DIR, f"session_{ts}.log")
            self._log_fp = open(path, "a", encoding="utf-8")
        except Exception:  # noqa: BLE001 - 落盘失败则用纯面板日志
            self._log_fp = None
        self._device_was_online = True
        self._scrcpy_log = []  # 新会话：清空上一轮 scrcpy 日志
        self._emit_log(
            "SESSION",
            f"投屏启动 cmd: scrcpy {' '.join(build_args(self.state))}",
        )
        self._emit_log(
            "SESSION",
            f"设备 serial={self.state.get('device', '')} "
            f"connMode={self.state.get('connMode', 'usb')} addr={self._wifi_addr()}",
        )
        if not self._log_timer.isActive():
            self._log_timer.start()

    def _stop_session_logging(self) -> None:
        """停止掉线监听并关闭会话日志文件（写结束脚注）。"""
        self._log_timer.stop()
        if self._log_fp is not None:
            try:
                self._log_fp.write("=== 投屏会话结束 ===\n")
                self._log_fp.close()
            except Exception:  # noqa: BLE001
                pass
            self._log_fp = None

    def _poll_device_online(self) -> None:
        """定时器回调（UI 线程）：经 worker 子线程查 adb 在线状态，不阻塞 UI。"""
        if self._proc is None:
            return
        QMetaObject.invokeMethod(
            self.worker,
            "run_check_online",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.state.get("device", "")),
            Q_ARG(str, self._wifi_addr()),
        )

    def _on_device_online_checked(self, online: bool) -> None:
        """worker 回传在线检查结果：在线→离线跳变时记 DEVICE 事件（去抖只记一次）。"""
        if self._proc is None:
            return
        if online:
            self._device_was_online = True
            return
        if self._device_was_online:
            self._device_was_online = False
            self._emit_log(
                "DEVICE",
                "设备已在 adb 层离线/断开（连接传输层中断，scrcpy 随后退出）",
            )

    # ============================ 工具 ============================

    def _build_command_preview(self) -> str:
        """组装命令预览文本：``scrcpy`` + 空格 + 拼装参数。"""
        return "scrcpy " + " ".join(build_args(self.state))

    def shutdown(self) -> None:
        """释放 worker 线程与 QProcess（测试 / 应用退出时调用）。

        关键点（防 pytest 挂死）：
        - 先让 worker 线程处理自身 ``deleteLater``，再退出线程事件循环，
          保证对象在所属线程内被销毁，避免跨线程析构告警 / 泄漏。
        - ``thread.wait(3000)`` 带超时，防止极端情况下子线程不退出导致的
          无限阻塞（pytest 进程不退出）。
        """
        if self._proc is not None:
            try:
                self._proc.kill()
            except Exception:  # noqa: BLE001
                pass
            self._proc = None
        self._stop_session_logging()
        if self.thread is not None:
            # 先让 worker 线程处理自身销毁，再退出线程事件循环
            self.worker.deleteLater()
            self.thread.quit()
            # 带超时等待，防止子线程异常不退出导致 pytest 进程挂死
            self.thread.wait(3000)
            self.thread.deleteLater()
            self.thread = None
