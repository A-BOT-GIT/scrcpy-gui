"""scrcpy 启动器：把 UI 状态拼装成命令行参数，并拉起本地 scrcpy.exe。

GUI 不内嵌 scrcpy，只作为启动器调用同目录（或 PATH）里的官方二进制，
保证与官方行为一致、可独立升级。
"""
import subprocess
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal, QProcess

from core.runtime import find_executable, missing_tool_message


def find_scrcpy():
    return find_executable("scrcpy")


def build_args(s):
    """把状态字典 s 转成 scrcpy 参数列表（不含 'scrcpy' 本身）。"""
    a = []

    # 连接
    device = s.get("device")
    if device and not s.get("tcpip"):
        # tcpip 模式下无线参数（--tcpip=ip:port）覆盖 serial，故跳过 -s device；
        # device（USB serial）原值保留，多设备源与重跑能力无损。
        a += ["-s", device]
    if s.get("tcpip"):
        ip = s.get("ip") or "192.168.1.10"
        port = s.get("port") or 5555
        a += [f"--tcpip={ip}:{port}"]
    if s.get("displayId"):
        a += ["--display-id", str(s["displayId"])]

    # 显示
    if s.get("wifiOpt"):  # 无线优化预设：覆盖码率/分辨率
        a += ["-b", "2M", "-m", "800"]
    else:
        if s.get("maxSize"):
            a += ["-m", str(s["maxSize"])]
        if s.get("bitrate"):
            a += ["-b", f'{s["bitrate"]}M']
    if s.get("vcodec"):
        a += ["--video-codec", s["vcodec"]]
    if s.get("maxFps"):
        a += ["--max-fps", str(s["maxFps"])]
    if s.get("crop"):
        a += ["--crop", s["crop"]]
    if s.get("capOri"):
        a += ["--capture-orientation", s["capOri"]]
    if s.get("noVideo"):
        a += ["--no-video"]

    # 音频（需 Android 11+）
    if not s.get("audio", True):
        a += ["--no-audio"]
    if s.get("noAudioPlay"):
        a += ["--no-audio-playback"]
    if s.get("acodec"):
        a += ["--audio-codec", s["acodec"]]
    if s.get("abitrate"):
        # scrcpy 4.0 参数为 --audio-bit-rate（带连字符）；单位 K/M 受支持
        a += ["--audio-bit-rate", f'{s["abitrate"]}K']
    if s.get("abuffer"):
        a += ["--audio-buffer", str(s["abuffer"])]

    # 控制
    if not s.get("control", True):
        a += ["--no-control"]
    if s.get("otg"):
        a += ["--otg"]
    # OTG 模式下 scrcpy 仅接受 keyboard/mouse = aoa 或 disabled，
    # uhid/sdk 会被拒绝；aoa 是 OTG 下的物理键鼠等价模式，保留用户“物理键鼠”意图。
    def _input_mode(val, otg):
        if not isinstance(val, str):
            val = "uhid"
        if otg and val not in ("aoa", "disabled"):
            val = "aoa"
        return val
    if s.get("keyboard"):
        a += ["--keyboard", _input_mode(s["keyboard"], s.get("otg"))]
    if s.get("mouse"):
        a += ["--mouse", _input_mode(s["mouse"], s.get("otg"))]
    if s.get("gamepad"):
        a += ["--gamepad", "uhid"]
    if s.get("showTouches"):
        a += ["--show-touches"]
    if s.get("turnOff"):
        a += ["--turn-screen-off"]
    if s.get("stayAwake"):
        a += ["--stay-awake"]
    if s.get("powerOff"):
        a += ["--power-off-on-close"]

    # 录制
    if s.get("record"):
        path = s.get("recPath") or "record.mp4"
        a += ["--record", path, "--record-format", s.get("recFmt") or "mp4"]

    # 窗口
    if s.get("fullscreen"):
        a += ["--fullscreen"]
    if s.get("ontop"):
        a += ["--always-on-top"]
    if s.get("borderless"):
        a += ["--window-borderless"]
    if s.get("noWindow"):
        a += ["--no-window"]
    if s.get("winTitle"):
        a += ["--window-title", s["winTitle"]]
    if s.get("renderFit"):
        a += ["--render-fit", s["renderFit"]]
    if s.get("noSaver"):
        a += ["--disable-screensaver"]
    if s.get("winX"):  # 真值判断：空串/None 均跳过，避免拼出 --window-x 空值
        a += ["--window-x", str(s["winX"])]
    if s.get("winY"):
        a += ["--window-y", str(s["winY"])]
    if s.get("winW"):
        a += ["--window-width", str(s["winW"])]
    if s.get("winH"):
        a += ["--window-height", str(s["winH"])]

    return a


def launch(scrcpy_path=None, args=None):
    """拉起 scrcpy。返回 Popen 进程对象。

    注意：此函数让 scrcpy 独立窗口运行（CREATE_NO_WINDOW 抑制黑控制台，
    scrcpy 自身的镜像窗口不受影响）。需要 GUI 实时捕获日志请用 launch_qprocess()。
    """
    exe = scrcpy_path or find_scrcpy()
    if not exe:
        raise FileNotFoundError(missing_tool_message("scrcpy"))
    cmd = [exe, *(args or [])]
    if sys.platform == "win32":
        # CREATE_NO_WINDOW：从 windowed GUI 拉起时不弹黑控制台窗口；
        # 仅抑制控制台分配，scrcpy 的 SDL 镜像窗口仍正常显示。
        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        proc = subprocess.Popen(cmd)
    return proc


class _SubprocessProc(QObject):
    """QProcess 兼容外观：底层用 ``subprocess.Popen``（win32 带 ``CREATE_NO_WINDOW``）。

    PyQt6 **未暴露** ``QProcess.setCreateProcessArgumentsModifier``（它依赖
    C++ 的 ``std::function`` 回调，SIP 无法绑定），所以原先用该方法的
    写法在 PyQt6 运行时必然 ``AttributeError`` 崩溃。改为 subprocess 底层实现，
    既能在 win32 抑制 scrcpy（console 子系统）的 conhost 黑框，又保持
    controller 依赖的 QProcess 接口不变（信号 / readAllStandardOutput / state / kill）。

    暴露接口：
    - 信号 ``readyReadStandardOutput`` / ``finished(int, ExitStatus)`` / ``errorOccurred(ProcessError)``
    - ``readAllStandardOutput() -> bytes``（读取并清空内部缓冲，等价 QProcess）
    - ``state() -> QProcess.ProcessState``
    - ``kill()`` / ``terminate()``

    ``finished`` 的退出状态引用 ``QProcess.ExitStatus``、``state()`` 引用
    ``QProcess.ProcessState``，方便 controller 的枚举比较（``NormalExit`` 等）原样生效。
    """

    readyReadStandardOutput = pyqtSignal()
    finished = pyqtSignal(int, QProcess.ExitStatus)
    errorOccurred = pyqtSignal(QProcess.ProcessError)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._proc = None
        self._buf = b""
        self._lock = threading.Lock()
        self._running = False
        self._exit_code = 0

    def start(self, exe: str, args=None) -> None:
        cmd = [exe, *(args or [])]
        flags = 0
        if sys.platform == "win32":
            # CREATE_NO_WINDOW：从 --windowed GUI 拉起时不弹 conhost 黑框；
            # scrcpy 的 SDL 镜像窗口仍正常显示。
            flags |= subprocess.CREATE_NO_WINDOW
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout（等价 MergedChannels）
                creationflags=flags,
                bufsize=0,
            )
        except Exception:  # noqa: BLE001 - 启动失败转 errorOccurred，由 controller 接住
            self.errorOccurred.emit(QProcess.ProcessError.FailedToStart)
            return
        self._running = True
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        """后台读线程：边读边放缓冲并发射 readyRead；进程结束后发射 finished。"""
        try:
            assert self._proc is not None and self._proc.stdout is not None
            for chunk in iter(lambda: self._proc.stdout.read(4096), b""):
                with self._lock:
                    self._buf += chunk
                self.readyReadStandardOutput.emit()
            self._proc.stdout.close()
        except Exception:  # noqa: BLE001 - 管道异常不致命
            pass
        rc = self._proc.wait() if self._proc is not None else -1
        with self._lock:
            self._running = False
            self._exit_code = rc if isinstance(rc, int) else -1
        # 把退出时残留在管道缓冲的最后字节刷出（scrcpy 块缓冲关键路径）
        with self._lock:
            tail = self._buf
        if tail:
            self.readyReadStandardOutput.emit()
        status = (
            QProcess.ExitStatus.NormalExit
            if self._exit_code == 0
            else QProcess.ExitStatus.CrashExit
        )
        self.finished.emit(self._exit_code, status)

    def readAllStandardOutput(self):
        """读取并清空内部缓冲（等价 QProcess.readAllStandardOutput 语义）。"""
        with self._lock:
            data = self._buf
            self._buf = b""
        return data

    def state(self):
        """返回 ``QProcess.ProcessState``。"""
        if self._proc is None:
            return QProcess.ProcessState.NotRunning
        if self._running:
            return QProcess.ProcessState.Running
        return QProcess.ProcessState.NotRunning

    def kill(self) -> None:
        if self._proc is not None:
            try:
                self._proc.kill()
            except Exception:  # noqa: BLE001
                pass

    def terminate(self) -> None:
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:  # noqa: BLE001
                pass


def launch_qprocess(args=None, scrcpy_path=None):
    """拉起 scrcpy，返回 QProcess 兼容对象，合并 stdout/stderr 以便 GUI 实时捕获日志。

    实现改用 ``subprocess.Popen``（win32 带 ``CREATE_NO_WINDOW``），包装为
    ``_SubprocessProc`` 暴露 QProcess 兼容接口——因 PyQt6 未暴露
    ``QProcess.setCreateProcessArgumentsModifier``，原写法在运行时崩溃。
    调用方（controller）按 QProcess 契约连接
    readyReadStandardOutput / finished / errorOccurred 信号即可。
    """
    exe = scrcpy_path or find_scrcpy()
    if not exe:
        return None
    proc = _SubprocessProc()
    proc.start(exe, args or [])
    return proc
