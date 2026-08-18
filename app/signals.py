"""scrcpy-gui 信号 / 枚举 / state 键 唯一真源（接口契约）。

本文件是后续 T2–T7 阶段共享的**唯一契约真源**，包含三部分：

(A) ``ControllerSignals`` —— ``AppController`` 对外发射的全部信号，集中定义，避免散落。
(B) ``ConnState`` —— 无线连接状态机枚举（5 态）。
(C) state 字典键名常量 —— 按连接/画质/音频/控制/录制/窗口分组列出全部键。

规则（硬约束）：
- 后续任何阶段新增 / 修改信号或 state 键，**只能改本文件**，并通知主理人齐活林。
- 禁止在别处硬编码信号名或 state 键名，一律从此模块导入。

state 字典结构（共享知识，抄录自 ARCHITECTURE.md 第 7 节）：
- 连接：device, connMode(usb/wifi), tcpip, ip, port, displayId
- 画质：wifiOpt, vcodec, maxSize, bitrate, maxFps, crop, capOri, noVideo
- 音频：audio, noAudioPlay, acodec, abitrate, abuffer
- 控制：control, otg, keyboard, mouse, gamepad, showTouches, turnOff, stayAwake, powerOff
- 录制：record, recPath, recFmt
- 窗口：fullscreen, ontop, borderless, noWindow, winTitle, renderFit, noSaver, winX, winY, winW, winH
- 新增：preset_name（当前预设名）、expertMode（基础/专家，bool，默认 False）
- 注意：连接态 ``connState`` **不进** state 字典，由 ``ConnectionStateMachine.current`` 单独管理。
"""

from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal


# ---------------------------------------------------------------------------
# (A) ControllerSignals —— AppController 对外发射的全部信号
# ---------------------------------------------------------------------------
class ControllerSignals(QObject):
    """AppController 对外发射的全部信号，集中定义，避免散落。

    视图层（MainWindow / tabs / 子面板）在 ``MainWindow._wire_signals()`` 中
    connect 这些信号到各自的更新槽；Tab → controller 走 ``BaseTab.valueChanged``。
    """

    commandChanged = pyqtSignal(str)             # 命令预览变化：str = 拼装后的 scrcpy 命令行预览
    logLine = pyqtSignal(str)                     # 一行 scrcpy 日志：str = 单行日志文本
    connStateChanged = pyqtSignal(str, str, str)  # (serial, state, msg)：state 为 ConnState 值；
                                                   #   serial 为设备序列号，单设备可传空串，为多设备预留
    runStateChanged = pyqtSignal(bool, str, str)  # (running, fps, br)：running 运行态；
                                                   #   fps/br 为解析后的文本（如 "60"、"8.00"）
    devicesChanged = pyqtSignal(list, str)        # ([(serial, status, info)...], err)：设备列表 + 错误信息
    errorOccurred = pyqtSignal(str, str)          # (title, detail)：持久错误（→ StatusBanner 顶部红条）
    stateChanged = pyqtSignal(dict)               # 完整 state 字典回填（预设加载 / 分层切换后全量回填）
    statusMessage = pyqtSignal(str)               # 瞬态状态栏提示（非持久错误）


# ---------------------------------------------------------------------------
# (B) ConnState —— 无线连接状态机枚举（5 态）
# ---------------------------------------------------------------------------
class ConnState(str, Enum):
    """无线连接状态机状态枚举。

    继承 ``str`` 以便直接将枚举成员作为字符串序列化 / 比较（如存入日志或配置）。
    与 GUI 解耦，仅由 ``ConnectionStateMachine`` 驱动并发 ``connStateChanged``。
    """

    IDLE = "idle"           # 空闲（未连接）
    TCPIP = "tcpip"         # 已执行 adb tcpip，等待 connect
    CONNECTING = "connecting"  # 正在 adb connect
    READY = "ready"         # 已就绪，可拔线启动
    FAILED = "failed"       # 失败


# ---------------------------------------------------------------------------
# (C) state 字典键名常量（共享知识锚点，唯一真源）
# ---------------------------------------------------------------------------
#: 连接分组键
STATE_KEYS_CONN = (
    "device",       # 当前设备序列号
    "connMode",     # 连接模式：usb / wifi
    "tcpip",        # 是否已 adb tcpip（无线端口已开）
    "ip",           # 无线连接 IP
    "port",         # 无线连接端口
    "displayId",    # 显示 id（副屏）
)

#: 画质分组键
STATE_KEYS_VIDEO = (
    "wifiOpt",      # 无线优化（开启后静默覆盖手动码率/分辨率）
    "vcodec",       # 视频编解码器
    "maxSize",      # 最大尺寸
    "bitrate",      # 码率
    "maxFps",       # 最大帧率
    "crop",         # 裁剪 W:H:X:Y
    "capOri",       # 捕获方向
    "noVideo",      # 无视频
)

#: 音频分组键
STATE_KEYS_AUDIO = (
    "audio",        # 是否开音频
    "noAudioPlay",  # 不播放音频（仅采集）
    "acodec",       # 音频编解码器
    "abitrate",     # 音频码率
    "abuffer",      # 音频缓冲
)

#: 控制分组键
STATE_KEYS_CONTROL = (
    "control",      # 是否可控制
    "otg",          # OTG 模式
    "keyboard",     # 键盘
    "mouse",        # 鼠标
    "gamepad",      # 手柄
    "showTouches",  # 显示触摸点
    "turnOff",      # 息屏
    "stayAwake",    # 保持唤醒
    "powerOff",     # 关闭设备电源
)

#: 录制分组键
STATE_KEYS_RECORD = (
    "record",       # 是否录制
    "recPath",      # 录制路径
    "recFmt",       # 录制格式
)

#: 窗口分组键
STATE_KEYS_WINDOW = (
    "fullscreen",   # 全屏
    "ontop",        # 置顶
    "borderless",   # 无边框
    "noWindow",     # 无窗口（仅后台）
    "winTitle",     # 窗口标题
    "renderFit",    # 渲染适配
    "noSaver",      # 禁用屏保
    "winX",         # 窗口 X
    "winY",         # 窗口 Y
    "winW",         # 窗口宽
    "winH",         # 窗口高
)

#: 新增分组键（T5 预设 / T6 分层用）
STATE_KEYS_NEW = (
    "preset_name",  # 当前预设名
    "expertMode",   # 基础/专家，bool，默认 False
)

#: 全部 state 键（分组合并，供 T4 ``BaseTab.apply_state`` 全量遍历）
STATE_KEYS = (
    STATE_KEYS_CONN
    + STATE_KEYS_VIDEO
    + STATE_KEYS_AUDIO
    + STATE_KEYS_CONTROL
    + STATE_KEYS_RECORD
    + STATE_KEYS_WINDOW
    + STATE_KEYS_NEW
)

#: 当前预设名键（T5 预设交互：下拉默认展示 / 切换即回填）
PRESET_KEY = "preset_name"

#: 基础/专家分层键（T6 分层：首屏默认基础层）
EXPERT_KEY = "expertMode"

#: expertMode 默认值（False = 基础层；T6 首屏默认）
EXPERT_DEFAULT_FALSE = False

#: 连接态键名（明确不进 state 字典，仅作文档 / 校验引用；实际值由 ConnectionStateMachine.current 提供）
CONN_STATE_KEY = "connState"

#: state 键 → 默认值（共享知识锚点；与 core/launcher.build_args 的 ``.get`` 语义一致）。
#: 注意 winX/Y/W/H 默认 ``None``，因 build_args 用 ``is not None`` 判断；其余未设置项默认空串。
STATE_DEFAULTS = {
    "device": "",
    "connMode": "usb",
    "tcpip": False,
    "ip": "",
    "port": "",
    "displayId": "",
    "wifiOpt": False,
    "vcodec": "",
    "maxSize": "",
    "bitrate": "",
    "maxFps": "",
    "crop": "",
    "capOri": "",
    "noVideo": False,
    "audio": True,
    "noAudioPlay": False,
    "acodec": "",
    "abitrate": "",
    "abuffer": "",
    "control": True,
    "otg": False,
    "keyboard": True,
    "mouse": True,
    "gamepad": False,
    "showTouches": False,
    "turnOff": False,
    "stayAwake": False,
    "powerOff": False,
    "record": False,
    "recPath": "",
    "recFmt": "",
    "fullscreen": False,
    "ontop": False,
    "borderless": False,
    "noWindow": False,
    "winTitle": "",
    "renderFit": "",
    "noSaver": False,
    "winX": None,
    "winY": None,
    "winW": None,
    "winH": None,
    PRESET_KEY: "",
    EXPERT_KEY: EXPERT_DEFAULT_FALSE,
}


def default_state() -> dict:
    """返回一份新的默认 state 字典（深拷贝默认值，避免跨实例共享可变引用）。

    作为 ``AppController`` 初始化 state 的唯一来源；后续 T3/T5/T6 一律基于本字典。
    """
    return dict(STATE_DEFAULTS)


#: T7 布局断点（px）；``MainWindow.resizeEvent`` 用此判断候选 B（≥）/ 候选 A（<）。
#: 唯一真源，禁止在别处硬编码 1100（断点逻辑只从此模块导入）。
LAYOUT_BREAKPOINT_PX = 1100
