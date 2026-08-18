"""预设管理：把 UI 状态的可复用「参数」保存/读取为 JSON。

重构后（Preset Refactor Plan）：
- 预设只存「参数键」（``PRESETTABLE_KEYS``），**不存**连接/运行时键
  （``connMode`` / ``device`` / ``ip`` / ``port`` / ``preset_name`` / ``running`` 等）。
- 单一 schema：
  ``{"version":1,"name":<str>,"meta":{"description":...,"created":...,"updated":...},
    "params":{<仅参数键>:...}}``。
- 旧版整态 JSON 兼容读取：无 ``params`` 键时，剥离排除键后包成新 schema，
  下次 ``save`` 自动迁移。
- 单一可信路径：``PresetManager`` 类实现全部 IO；模块级仅保留
  ``presets_dir()`` 与 ``list_presets()`` 薄壳（向后兼容测试与旧调用方）。
"""

import json
import os
import re
import sys
from datetime import datetime

# ======================= 字段白名单 =======================
# 可入预设的「参数键」，来自各 Tab 的 register 审计（不含连接/运行时键）。
# 注：方案白名单为 35 键；``wifiOpt`` 虽被 launcher 使用，但未纳入方案枚举，
# 此处严格按方案实现，若需包含请另行确认。
PRESETTABLE_KEYS: tuple[str, ...] = (
    # 画质 7
    "vcodec", "maxSize", "bitrate", "maxFps", "crop", "capOri", "noVideo",
    # 音频 5
    "audio", "noAudioPlay", "acodec", "abitrate", "abuffer",
    # 控制 9
    "control", "otg", "keyboard", "mouse", "gamepad",
    "showTouches", "turnOff", "stayAwake", "powerOff",
    # 录制 3
    "record", "recPath", "recFmt",
    # 窗口 10
    "fullscreen", "ontop", "borderless", "noWindow", "noSaver",
    "winTitle", "renderFit", "winX", "winY", "winW", "winH",
    # 副屏 1
    "displayId",
)

# 环境/设备相关字段：**默认不纳入**预设（新建时默认不勾）。
# 窗口坐标/尺寸与具体屏幕分辨率绑定、录制路径与具体磁盘绑定、
# 窗口标题多为场景相关、副屏编号与设备的屏幕配置绑定——跨设备易失效或属噪音。
# 用户仍可在「包含字段」中显式勾选它们后存入。
PRESETTABLE_ENV_KEYS: frozenset[str] = frozenset(
    {
        "winX", "winY", "winW", "winH",   # 窗口坐标/尺寸
        "recPath",                          # 录制路径
        "winTitle",                         # 窗口标题
        "displayId",                        # 副屏编号
    }
)


def default_include_keys() -> list[str]:
    """新建预设时默认勾选的键：配置参数（排除环境/设备相关键）。

    即「配置参数默认勾、环境/设备参数默认不勾」，避免预设混入机器噪音字段。
    """
    return [k for k in PRESETTABLE_KEYS if k not in PRESETTABLE_ENV_KEYS]


# 连接/运行时键：**永不**入预设；load 旧文件时也会被剥离。
EXCLUDED_KEYS: frozenset[str] = frozenset(
    {
        "connMode", "device", "ip", "port",
        "preset_name", "running", "tcpip",
    }
)

# 供 GUI 分组渲染复选框（=「设置」核心）。
PRESETTABLE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("画质", ("vcodec", "maxSize", "bitrate", "maxFps", "crop", "capOri", "noVideo")),
    ("音频", ("audio", "noAudioPlay", "acodec", "abitrate", "abuffer")),
    (
        "控制",
        (
            "control", "otg", "keyboard", "mouse", "gamepad",
            "showTouches", "turnOff", "stayAwake", "powerOff",
        ),
    ),
    ("录制", ("record", "recPath", "recFmt")),
    (
        "窗口",
        (
            "fullscreen", "ontop", "borderless", "noWindow", "noSaver",
            "winTitle", "renderFit", "winX", "winY", "winW", "winH",
        ),
    ),
    ("副屏", ("displayId",)),
)


def is_presettable(key: str) -> bool:
    """判断某个 state 键是否可入预设（在白名单内）。"""
    return key in PRESETTABLE_KEYS


_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    """清洗预设名：去除文件名非法字符与首尾空白；空名抛 ``ValueError``。

    仅清洗文件名层面的非法字符，不限制中文/空格等合法内容。
    """
    cleaned = _ILLEGAL.sub("", name).strip()
    if not cleaned:
        raise ValueError("预设名称不能为空")
    return cleaned


def presets_dir() -> str:
    """预设存储目录。

    frozen（打包单文件）→ ``~/.scrcpy-gui/presets``（用户目录可写）；
    源码 → ``presets/``（项目内）。
    """
    if getattr(sys, "frozen", False):
        base = os.path.join(os.path.expanduser("~"), ".scrcpy-gui")
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        base = os.path.join(here, "..", "presets")
    d = os.path.abspath(base)
    os.makedirs(d, exist_ok=True)
    return d


# ======================= 内部工具 =======================
def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _strip_excluded(state: dict) -> dict:
    """剥离连接/运行时键，仅留可入预设的参数键。"""
    return {k: v for k, v in state.items() if k not in EXCLUDED_KEYS}


def _load_raw(directory: str, name: str) -> dict | None:
    path = os.path.join(directory, f"{name}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _dump(record: dict, directory: str, name: str) -> str:
    d = os.path.abspath(directory)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return path


# ======================= 单一管理器 =======================
class PresetManager:
    """预设增删改查的唯一可信路径（类接口，供 AppController / GUI 使用）。

    默认目录沿用 ``presets_dir()`` 约定；传入 ``base_dir`` 时使用自定义目录
    （测试隔离用）。
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = base_dir

    def _dir(self) -> str:
        if self._base_dir:
            return os.path.abspath(self._base_dir)
        return presets_dir()

    def _path(self, name: str) -> str:
        return os.path.join(self._dir(), f"{name}.json")

    # ---- 查询 ----
    def list(self) -> list[str]:
        d = self._dir()
        if not os.path.isdir(d):
            return []
        return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))

    def exists(self, name: str) -> bool:
        return os.path.isfile(self._path(name))

    def load(self, name: str) -> dict | None:
        """读取预设，返回完整记录 ``{version,name,meta,params}``。

        - 新 schema（含 ``params`` 键）→ 原样返回。
        - 旧版整态（无 ``params``）→ 剥离排除键后包成新 schema，
          下次 ``save`` 自动迁移。
        """
        raw = _load_raw(self._dir(), name)
        if raw is None:
            return None
        if isinstance(raw.get("params"), dict):
            return raw
        # 旧版整态：剥离连接/运行时键
        return {
            "version": 1,
            "name": name,
            "meta": {},
            "params": _strip_excluded(raw),
        }

    # ---- 写入 ----
    def save(
        self,
        name: str,
        params: dict,
        description: str = "",
        *,
        overwrite: bool = True,
    ) -> str:
        """保存预设：仅写 ``PRESETTABLE_KEYS`` 内的键，连接键被静默丢弃。

        ``name`` 会被 ``sanitize_name`` 清洗；当 ``overwrite=False`` 时，重名会
        抛 ``FileExistsError``，用于“新建预设”等不能静默覆盖用户数据的操作。
        编辑既有预设则显式传入 ``overwrite=True``。
        """
        name = sanitize_name(name)
        filtered = {k: v for k, v in params.items() if is_presettable(k)}
        existing = _load_raw(self._dir(), name)
        if existing is not None and not overwrite:
            raise FileExistsError(f"预设“{name}”已存在")
        now = _now_iso()
        if isinstance(existing, dict) and isinstance(existing.get("params"), dict):
            # 更新既有：保留未改的 meta，刷新 updated / description
            meta = dict(existing.get("meta") or {})
            meta["updated"] = now
            if description:
                meta["description"] = description
            record = {
                "version": 1,
                "name": name,
                "meta": meta,
                "params": filtered,
            }
        else:
            record = {
                "version": 1,
                "name": name,
                "meta": {
                    "description": description,
                    "created": now,
                    "updated": now,
                },
                "params": filtered,
            }
        return _dump(record, self._dir(), name)

    def rename(self, old: str, new: str) -> None:
        """重命名预设；同步记录内的 ``name`` 字段。"""
        old = sanitize_name(old)
        new = sanitize_name(new)
        old_p = self._path(old)
        new_p = self._path(new)
        if not os.path.isfile(old_p):
            raise FileNotFoundError(f"预设不存在：{old}")
        if old_p == new_p:
            return
        if os.path.exists(new_p):
            raise FileExistsError(f"目标预设已存在：{new}")
        # 同步记录内的 name 字段，避免文件名与内容不一致
        try:
            with open(old_p, "r", encoding="utf-8") as f:
                rec = json.load(f)
            rec["name"] = new
            with open(old_p, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, OSError):
            pass
        os.rename(old_p, new_p)

    def delete(self, name: str) -> None:
        """删除预设；不存在时不报错。"""
        name = sanitize_name(name)
        p = self._path(name)
        if os.path.isfile(p):
            os.remove(p)


# ======================= 模块级薄壳（向后兼容） =======================
def list_presets() -> list[str]:
    """薄壳：等价于 ``PresetManager().list()``（沿用 ``presets_dir()``）。"""
    return PresetManager().list()
