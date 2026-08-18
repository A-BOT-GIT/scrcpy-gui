"""adb 辅助：设备发现、无线连接、切回 USB。

scrcpy 通过 adb 与设备通信，本模块封装常见的 adb 调用。
优先使用与 scrcpy.exe 同目录的 adb.exe，其次回退到系统 PATH。
"""
import re
import subprocess
import sys

from core.runtime import find_executable, missing_tool_message


def find_adb():
    return find_executable("adb")


def _run(args, timeout=20):
    adb = find_adb()
    if not adb:
        return -1, "", missing_tool_message("adb")
    try:
        kwargs = dict(
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        # windowed 打包（--windowed）后父进程无控制台；若不显式抑制，
        # Windows 会为每个 adb.exe 子进程分配新黑框，轮询时表现为“一直闪”。
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        r = subprocess.run([adb, *args], **kwargs)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:  # 超时 / 找不到 adb 等
        return -1, "", str(e)


def list_devices():
    """返回 (设备列表, 错误信息)。设备列表项为 (serial, status, info)。

    status 取值：``device``（已授权可用）/ ``unauthorized``（已连接但未在手机上
    授权 USB 调试）/ ``offline``（连接异常）。

    旧实现只收 ``device`` 行，导致手机第一次插上、用户还没点「允许」时 adb 报
    ``unauthorized``，被静默丢弃——用户看到下拉永远空、毫无提示，误以为程序识别
    不到设备。现改为：``unauthorized``/``offline`` 设备也返回，并带明确 err 提示，
    由 UI 在日志/状态栏告知用户去手机上授权或重插 USB。
    """
    code, out, err = _run(["devices", "-l"])
    devices = []
    if code != 0:
        return devices, err.strip() or "adb 执行失败"
    n_unauth = 0
    n_offline = 0
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial = parts[0]
        status = parts[1] if len(parts) > 1 else "unknown"
        info = " ".join(parts[2:]) if len(parts) > 2 else ""
        if status == "device":
            devices.append((serial, status, info))
        elif status == "unauthorized":
            n_unauth += 1
            devices.append((serial, status, info))
        elif status == "offline":
            n_offline += 1
            devices.append((serial, status, info))
    msg = ""
    if n_unauth:
        msg = f"发现 {n_unauth} 台设备但未授权 USB 调试，请在手机上点击「允许」"
    elif n_offline:
        msg = f"发现 {n_offline} 台离线设备，请重新插拔 USB 线或检查驱动"
    return devices, msg


def tcpip(port=5555, serial=None):
    """让设备进入 TCP 监听模式。serial 用于多设备隔离（-s 指定目标）。"""
    args = (["-s", serial] if serial else []) + ["tcpip", str(port)]
    return _run(args)


def connect(ip, port=5555, serial=None):
    """通过 TCP 连接设备。serial 仅用于多设备场景下的显式指定。"""
    args = (["-s", serial] if serial else []) + ["connect", f"{ip}:{port}"]
    return _run(args)


def usb(serial=None):
    """切回 USB 模式。serial 用于多设备隔离。"""
    args = (["-s", serial] if serial else []) + ["usb"]
    return _run(args)


_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _is_loopback(ip: str) -> bool:
    """判断 IP 是否为回环地址（127.x 或 0.0.0.0）。"""
    return ip.startswith("127.") or ip == "0.0.0.0"


def get_device_ip(serial):
    """返回 (ip, err)。err 非空表示失败。

    取设备 WiFi（wlan0）IPv4 地址：
    1) 主：``ip -o -4 addr show wlan0`` 取 inet 地址（最可靠）；
    2) 辅：``ip -o route`` 中 wlan0 链路的 src IP（排除回环）；
    3) 兜：任意非回环 src IP（仍排除 127.x / 0.0.0.0）。

    不再使用 ``ip route get 0.0.0.0``：在 Android 上该命令常返回
    ``local 0.0.0.0 dev lo src 127.0.0.1`` 这类回环本地路由，
    会被误当成设备 IP，导致无线投屏连到 127.0.0.1 被拒绝。
    """
    if not serial:
        return "", "未提供设备 serial"
    # 1) 主：wlan0 接口地址（来自实测证据，最可靠）
    code, out, _e = _run(["-s", serial, "shell", "ip", "-o", "-4", "addr", "show", "wlan0"])
    if code == 0 and out.strip():
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m and not _is_loopback(m.group(1)):
            return m.group(1), ""
    # 2) 辅：ip -o route 中 wlan0 链路的 src IP（排除回环）
    code2, out2, _e2 = _run(["-s", serial, "shell", "ip", "-o", "route"])
    if code2 == 0 and out2.strip():
        for line in out2.splitlines():
            toks = line.split()
            if "wlan0" in toks and "src" in toks:
                i = toks.index("src")
                if i + 1 < len(toks):
                    cand = toks[i + 1]
                    if _IP_RE.match(cand) and not _is_loopback(cand):
                        return cand, ""
    # 3) 兜：任意非回环 src（仍排除 127.x / 0.0.0.0）
    if code2 == 0 and out2.strip():
        for line in out2.splitlines():
            toks = line.split()
            if "src" in toks:
                i = toks.index("src")
                if i + 1 < len(toks):
                    cand = toks[i + 1]
                    if _IP_RE.match(cand) and not _is_loopback(cand):
                        return cand, ""
    return "", "无法获取设备 WiFi IP（请确认设备已连 Wi-Fi）"
