# -*- coding: utf-8 -*-
"""L3 真实窗口点击遍历 + 实机端到端测试（可独立运行，无需 pytest）。

方法论（对齐旧项目 docs/l3_real_click_test_report.md）：
- 真实 Windows 窗口后端（非 offscreen），QTest 发送**真实鼠标/键盘事件**驱动控件，
  而非直接改 state 字典 —— 验证「控件 → state → scrcpy 参数 → UI 反馈」完整链路。
- 选项矩阵：对每个 state 键、每个取值，先用真实点击切到所属分层，再真实驱动控件，
  断言 widget 值 / controller.state / 命令预览三处一致，并经 controller.launch() 跑一轮
  （FakeProc 确定性退出）断言 GUI 呈现层（红条 / 运行态 / 安全态）。
- 场景测试：A 成功→停止、B AV1 失败→红条、实机 USB 拉起→停止。
- 失败截图：win.grab() 落盘 tests/screenshots/。

运行：
    python tests/l3_real_click_test.py
"""
from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import traceback

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QProcess, QTimer, QPoint
from PyQt6.QtWidgets import QApplication, QScrollArea, QWidget, QMessageBox
from PyQt6.QtTest import QTest

# —— 路径 ——
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app.controller import AppController
from app.signals import default_state
from ui.main_window import MainWindow
from ui.fields import read_value
from core.launcher import launch_qprocess as REAL_LAUNCH
from core.adb import find_adb


# ============================================================ FakeProc
class FakeProc(QObject):
    """模拟 core.launcher._SubprocessProc 的 QProcess 兼容接口，供矩阵/场景确定性驱动。"""

    readyReadStandardOutput = pyqtSignal()
    finished = pyqtSignal(int, QProcess.ExitStatus)
    errorOccurred = pyqtSignal(QProcess.ProcessError)

    def __init__(self, exit_code=0, out_lines=None, persist=False, linger_ms=20, parent=None):
        super().__init__(parent)
        self._exit = exit_code
        self._buf = ("\n".join(out_lines) if out_lines else "").encode("utf-8", "replace")
        self._persist = persist
        self._linger_ms = linger_ms
        self._running = False
        self._finished_emitted = False

    def start(self, exe, args=None):
        self._running = True
        if self._buf:
            QTimer.singleShot(0, self.readyReadStandardOutput.emit)
        if not self._persist:
            QTimer.singleShot(self._linger_ms, self._emit_finished)

    def _emit_finished(self, code=None, status=None):
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self._running = False
        code = self._exit if code is None else code
        if status is None:
            status = QProcess.ExitStatus.NormalExit if code == 0 else QProcess.ExitStatus.CrashExit
        self.finished.emit(code, status)

    def readAllStandardOutput(self):
        b = self._buf
        self._buf = b""
        return b

    def state(self):
        return QProcess.ProcessState.Running if self._running else QProcess.ProcessState.NotRunning

    def kill(self):
        if self._running:
            self._running = False
            QTimer.singleShot(20, lambda: self._emit_finished(1, QProcess.ExitStatus.CrashExit))

    def terminate(self):
        self.kill()


def make_factory(exit_code=0, out_lines=None, persist=False, linger_ms=20):
    def _factory(args=None, scrcpy_path=None):
        p = FakeProc(exit_code, out_lines, persist, linger_ms)
        p.start(scrcpy_path or "scrcpy", args)  # 必须启动，否则进程永不结束
        return p
    return _factory


# ============================================================ 选项矩阵定义
# (key, layer, ctype, values)
KEY_MATRIX = [
    # —— 基础层 ——
    ("vcodec", "basic", "combo", ["h265", "h264", "av1", ""]),
    ("maxSize", "basic", "combo", ["1920", "1280", ""]),
    ("bitrate", "basic", "combo", ["8", "4", "2", "1", ""]),
    ("maxFps", "basic", "combo", ["60", "30", ""]),
    ("capOri", "basic", "combo", ["", "@0", "@90", "@180", "@270"]),
    ("noVideo", "basic", "check", [True, False]),
    ("record", "basic", "check", [True, False]),
    ("recPath", "basic", "line", ["screen_2026", "rec_demo", ""]),
    ("recFmt", "basic", "combo", ["mp4", "mkv", ""]),
    # —— 专家层 ——
    ("audio", "expert", "check", [False, True]),
    ("noAudioPlay", "expert", "check", [True, False]),
    ("acodec", "expert", "combo", ["aac", "flac", ""]),
    ("abitrate", "expert", "line", ["64", "128", ""]),
    ("abuffer", "expert", "line", ["100", "200", ""]),
    ("control", "expert", "check", [False, True]),
    ("otg", "expert", "check", [True, False]),
    ("keyboard", "expert", "combo", ["uhid"]),
    ("mouse", "expert", "combo", ["uhid"]),
    ("gamepad", "expert", "check", [True, False]),
    ("showTouches", "expert", "check", [True, False]),
    ("turnOff", "expert", "check", [True, False]),
    ("stayAwake", "expert", "check", [True, False]),
    ("powerOff", "expert", "check", [True, False]),
    ("fullscreen", "expert", "check", [True, False]),
    ("ontop", "expert", "check", [True, False]),
    ("borderless", "expert", "check", [True, False]),
    ("noWindow", "expert", "check", [True, False]),
    ("noSaver", "expert", "check", [True, False]),
    ("winTitle", "expert", "line", ["MatrixTest", ""]),
    ("renderFit", "expert", "combo", ["", "stretched", "unscaled"]),
    ("winX", "expert", "line", ["100", "0"]),
    ("winY", "expert", "line", ["100"]),
    ("winW", "expert", "line", ["800"]),
    ("winH", "expert", "line", ["600"]),
    ("displayId", "expert", "line", ["1", "2", ""]),
]


def expected_token(key, v):
    """返回该取值在命令预览中应出现的片段；无片段返回 None。"""
    if v in ("", None, False):
        return None
    special = {
        "audio": "--no-audio" if v is False else None,
        "control": "--no-control" if v is False else None,
    }
    if key in special:
        return special[key]
    m = {
        "vcodec": f"--video-codec {v}", "maxSize": f"-m {v}", "bitrate": f"-b {v}M",
        "maxFps": f"--max-fps {v}", "capOri": f"--capture-orientation {v}",
        "noVideo": "--no-video", "record": "--record", "recPath": f"--record {v}",
        "recFmt": f"--record-format {v}", "noAudioPlay": "--no-audio-playback",
        "acodec": f"--audio-codec {v}", "abitrate": f"--audio-bit-rate {v}K",
        "abuffer": f"--audio-buffer {v}", "otg": "--otg", "keyboard": f"--keyboard {v}",
        "mouse": f"--mouse {v}", "gamepad": "--gamepad uhid", "showTouches": "--show-touches",
        "turnOff": "--turn-screen-off", "stayAwake": "--stay-awake",
        "powerOff": "--power-off-on-close", "fullscreen": "--fullscreen",
        "ontop": "--always-on-top", "borderless": "--window-borderless",
        "noWindow": "--no-window", "noSaver": "--disable-screensaver",
        "winTitle": f"--window-title {v}", "renderFit": f"--render-fit {v}",
        "winX": f"--window-x {v}", "winY": f"--window-y {v}", "winW": f"--window-width {v}",
        "winH": f"--window-height {v}", "displayId": f"--display-id {v}",
    }
    return m.get(key)


# ============================================================ 真实点击驱动
def find_control(win, key):
    w = win.findChild(QWidget, key)
    if w is None:
        raise RuntimeError(f"控件未找到: {key}")
    return w


def scroll_into_view(win, w):
    sa = win.findChild(QScrollArea, "left_scroll")
    if sa is not None:
        try:
            sa.ensureWidgetVisible(w)
        except Exception:
            pass


def drive_check(win, cb, target):
    if read_value(cb) != target:
        QTest.mouseClick(cb, Qt.MouseButton.LeftButton, pos=QPoint(10, cb.height() // 2))
        QApplication.processEvents()
        QTest.qWait(15)


def drive_combo(win, combo, value):
    target = combo.findData(value) if value else 0
    QTest.mouseClick(combo, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    QTest.qWait(40)
    if not combo.view().isVisible():
        combo.showPopup()
        QApplication.processEvents()
        QTest.qWait(20)
    cur = combo.currentIndex()
    delta = target - cur
    if delta != 0:
        key = Qt.Key.Key_Down if delta > 0 else Qt.Key.Key_Up
        for _ in range(abs(delta)):
            QTest.keyClick(combo, key)
            QApplication.processEvents()
    QTest.keyClick(combo, Qt.Key.Key_Enter)
    QApplication.processEvents()
    QTest.qWait(20)


def drive_line(win, le, value):
    QTest.mouseClick(le, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    QTest.keyClick(le, "a", Qt.KeyboardModifier.ControlModifier)  # 全选
    if value == "":
        QTest.keyClick(le, Qt.Key.Key_Backspace)
    else:
        QTest.keyClicks(le, value)
    QApplication.processEvents()
    QTest.qWait(10)


def reset_baseline(win, controller):
    base = default_state()
    base["maxSize"] = "1920"
    base["bitrate"] = "8"
    base["maxFps"] = "60"
    base["audio"] = True
    base["control"] = True
    base["device"] = "FAKE123"  # 矩阵启动用占位 serial，避免「未选设备」拦截
    controller.state.clear()
    controller.state.update(base)
    win._on_state_changed(controller.state)
    QApplication.processEvents()
    QTest.qWait(10)


def ensure_record_on(win, controller):
    cb = find_control(win, "record")
    if read_value(cb) is not True:
        drive_check(win, cb, True)


# ============================================================ 断言辅助
def safe_state(win):
    return (win.stop_btn.isEnabled(), win.launch_btn.isEnabled(),
            win.device_bar.autoBtn.isEnabled())


# ============================================================ 阶段：选项真实点击遍历矩阵
def phase_matrix(app):
    print("\n=== 阶段 1：L3 真实点击遍历矩阵 ===")
    controller = AppController()
    win = MainWindow(controller)
    win.show()
    app.processEvents()
    QTest.qWait(60)

    results = []          # {key,value,ok,msg}
    cur_layer = "basic"
    launched = 0

    try:
        for (key, layer, ctype, values) in KEY_MATRIX:
            # 切分层
            if layer != cur_layer:
                seg = win.segExpert if layer == "expert" else win.segBasic
                QTest.mouseClick(seg, Qt.MouseButton.LeftButton)
                app.processEvents(); QTest.qWait(20)
                cur_layer = layer

            for v in values:
                try:
                    reset_baseline(win, controller)
                    if key in ("recPath", "recFmt"):
                        ensure_record_on(win, controller)

                    w = find_control(win, key)
                    scroll_into_view(win, w)

                    if ctype == "check":
                        drive_check(win, w, v)
                    elif ctype == "combo":
                        drive_combo(win, w, v)
                    else:
                        drive_line(win, w, v)

                    # 1) widget 值
                    got = read_value(w)
                    assert got == v, f"widget 值 {got!r} != 目标 {v!r}"
                    # 2) controller.state
                    assert controller.state.get(key) == v, \
                        f"state {controller.state.get(key)!r} != {v!r}"
                    # 3) 命令预览
                    cmd = win.command_panel.cmd.text()
                    tok = expected_token(key, v)
                    if tok:
                        assert tok in cmd, f"命令预览缺少 {tok!r}：{cmd}"

                    # 4) 经 controller.launch() 完整链路（FakeProc 确定性退出）
                    is_av1 = (key == "vcodec" and v == "av1")
                    if is_av1:
                        import app.controller as CTRL
                        CTRL.launch_qprocess = make_factory(
                            2, ["ERROR: Could not create default video encoder for av1"], False)
                    else:
                        import app.controller as CTRL
                        CTRL.launch_qprocess = make_factory(0, None, False)

                    errors = []
                    conn = controller.errorOccurred.connect(
                        lambda t, d, e=errors: e.append((t, d)))
                    try:
                        QTest.mouseClick(win.launch_btn, Qt.MouseButton.LeftButton)
                        app.processEvents(); QTest.qWait(90)
                    finally:
                        controller.errorOccurred.disconnect(conn)

                    if is_av1:
                        assert win.banner.isVisible(), "AV1 应弹出错误红条"
                        assert "启动失败" in win.banner.text.text(), \
                            f"红条标题异常：{win.banner.text.text()!r}"
                        assert "av1" in win.banner.text.text(), \
                            f"红条详情缺 av1：{win.banner.text.text()!r}"
                    else:
                        assert not win.banner.isVisible(), \
                            f"成功场景不应弹红条：{win.banner.text.text()!r}"
                    # 安全态回收
                    sb, lb, _ = safe_state(win)
                    assert sb is False and lb is True, f"运行态未回收：stop={sb} launch={lb}"
                    win.banner.clear()
                    launched += 1
                    results.append((key, v, True, ""))
                except Exception as e:
                    msg = f"{type(e).__name__}: {e}"
                    results.append((key, v, False, msg))
                    try:
                        p = os.path.join(HERE, "screenshots", f"fail_{key}_{v}.png")
                        win.grab().save(p)
                    except Exception:
                        pass
    finally:
        try:
            controller.shutdown()
        except Exception:
            pass
        win.close()
        app.processEvents()

    passed = sum(1 for r in results if r[2])
    failed = len(results) - passed
    print(f"矩阵组合 {len(results)} 项：PASS {passed} / FAIL {failed}；经 launch() 真实启动 {launched} 次")
    for (k, v, ok, m) in results:
        if not ok:
            print(f"  [FAIL] {k}={v!r} -> {m}")
    return results


# ============================================================ 阶段：场景 A/B（真实点击链路）
def phase_scenarios(app):
    print("\n=== 阶段 2：场景 A/B（真实点击 → 启动 → 停止 / 红条）===")
    controller = AppController()
    win = MainWindow(controller)
    win.show(); app.processEvents(); QTest.qWait(60)
    out = []

    try:
        import app.controller as CTRL

        # —— 场景 A：成功启动 → 运行中 → 真实点击停止 → 安全态 ——
        # 关键：不用 persist=True（会留下永久挂起的 QTimer + Running 态，触发沙箱看门狗 EXIT=127）。
        # 改用「可自愈长驻工厂」：linger_ms 给断言运行态留窗口，超时后自动 NormalExit 回收。
        print("  step: reset_baseline A")
        reset_baseline(win, controller)
        CTRL.launch_qprocess = make_factory(0, None, persist=False, linger_ms=1500)
        print("  step: click launch A")
        QTest.mouseClick(win.launch_btn, Qt.MouseButton.LeftButton)
        app.processEvents(); QTest.qWait(120)
        a_running = win.run_label.text().startswith("运行中")
        a_stop_en = win.stop_btn.isEnabled()
        a_launch_dis = not win.launch_btn.isEnabled()
        print(f"  step: assert running A (running={a_running} stop_en={a_stop_en})")
        # 真实点击「停止 ■」
        QTest.mouseClick(win.stop_btn, Qt.MouseButton.LeftButton)
        app.processEvents(); QTest.qWait(120)
        a_safe = (not win.stop_btn.isEnabled()) and win.launch_btn.isEnabled()
        a_no_banner = not win.banner.isVisible()
        okA = a_running and a_stop_en and a_launch_dis and a_safe and a_no_banner
        out.append(("A 成功→停止", okA,
                    f"running={a_running} stop_en={a_stop_en} launch_dis={a_launch_dis} "
                    f"safe={a_safe} no_banner={a_no_banner}"))
        win.banner.clear()
        print(f"  step: A done ok={okA}")

        # —— 场景 B：选 AV1 → 真实点击启动 → 错误红条（不含误报）——
        print("  step: reset_baseline B")
        reset_baseline(win, controller)
        # 真实点击视频编解码器切到 AV1
        vc = find_control(win, "vcodec")
        scroll_into_view(win, vc)
        drive_combo(win, vc, "av1")
        CTRL.launch_qprocess = make_factory(
            2, ["ERROR: Could not create default video encoder for av1"], False)
        print("  step: click launch B")
        QTest.mouseClick(win.launch_btn, Qt.MouseButton.LeftButton)
        app.processEvents(); QTest.qWait(120)
        b_banner = win.banner.isVisible()
        b_title = "启动失败" in win.banner.text.text()
        b_av1 = "av1" in win.banner.text.text()
        b_no_crash = "被系统/连接层杀死" not in win.banner.text.text()
        b_safe = (not win.stop_btn.isEnabled()) and win.launch_btn.isEnabled()
        okB = b_banner and b_title and b_av1 and b_no_crash and b_safe
        out.append(("B AV1→红条", okB,
                    f"banner={b_banner} title={b_title} av1={b_av1} "
                    f"no_crash_misreport={b_no_crash} safe={b_safe}"))
        print(f"  step: B done ok={okB}")
    except Exception as e:
        out.append(("场景异常", False, traceback.format_exc()))
        print("  step: EXCEPTION in scenarios")
    finally:
        try:
            controller.shutdown()
        except Exception:
            pass
        win.close(); app.processEvents()

    for name, ok, detail in out:
        print(f"  {'[PASS]' if ok else '[FAIL]'} {name}：{detail}")
    return out


# ============================================================ 阶段：实机 USB 端到端
def detect_device():
    try:
        adb = find_adb()
        out = subprocess.check_output([adb, "devices"], text=True, timeout=15)
        serials = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            s, st = line.split("\t", 1)
            if st.strip() == "device":
                serials.append(s.strip())
        return serials
    except Exception:
        return []


def phase_real_device(app):
    print("\n=== 阶段 3：实机 USB 端到端（真实 scrcpy 拉起）===")
    serials = detect_device()
    if not serials:
        print("  [SKIP] 未检测到在线设备，实机用例 SKIP（不影响门禁）")
        return [("实机 USB 拉起", "SKIP", "无在线设备")]
    serial = serials[0]
    print(f"  检测到设备：{serial}")

    controller = AppController()
    win = MainWindow(controller)
    win.show(); app.processEvents(); QTest.qWait(60)
    out = []
    try:
        import app.controller as CTRL
        CTRL.launch_qprocess = REAL_LAUNCH  # 恢复真实启动

        # 干净状态（禁用录制/熄屏/关机，避免副作用）
        base = default_state()
        base["device"] = serial
        controller.state.clear(); controller.state.update(base)
        win._on_state_changed(controller.state)
        app.processEvents(); QTest.qWait(10)

        # 真实点击「启动 ▶」
        QTest.mouseClick(win.launch_btn, Qt.MouseButton.LeftButton)
        app.processEvents()

        # 轮询运行态
        running = False
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents(); QTest.qWait(250)
            if controller._proc is not None and controller._proc.state() == QProcess.ProcessState.Running:
                running = True
                break
        lbl = win.run_label.text()
        stop_en = win.stop_btn.isEnabled()
        out.append(("启动后运行态", running,
                    f"run_label={lbl!r} stop_enabled={stop_en} proc_alive={running}"))

        if running:
            # 真实点击「停止 ■」
            QTest.mouseClick(win.stop_btn, Qt.MouseButton.LeftButton)
            app.processEvents()
            safe = False
            deadline = time.time() + 6
            while time.time() < deadline:
                app.processEvents(); QTest.qWait(250)
                if controller._proc is None:
                    safe = True
                    break
            no_banner = not win.banner.isVisible()
            out.append(("停止后安全态", safe and no_banner,
                        f"proc_cleared={safe} no_banner={no_banner} "
                        f"launch_enabled={win.launch_btn.isEnabled()}"))
        else:
            out.append(("停止后安全态", "SKIP", "启动未进入运行态，跳过停止验证"))
    except Exception as e:
        out.append(("实机异常", False, traceback.format_exc()))
    finally:
        try:
            controller.shutdown()
        except Exception:
            pass
        win.close(); app.processEvents()

    for name, ok, detail in out:
        mark = "[PASS]" if ok is True else ("[SKIP]" if ok == "SKIP" else "[FAIL]")
        print(f"  {mark} {name}：{detail}")
    return out


# ============================================================ 阶段：交互控件真实点击遍历
def phase_interactions(app):
    """连接栏 / 预设 / 分层 / 窗口 chrome / 红条 等**非配置类**按钮与选项的真实点击遍历。

    覆盖此前 phase 1 矩阵（仅 6 卡片 scrcpy 参数）未触及的全部可交互控件：
    分段切换、一键投屏/刷新/无线连接、IP/端口输入、无线优化、设备下拉、
    预设下拉/管理弹窗（保存/复制/删除）/编辑弹窗（分组勾选/保存）、红条✕、标题✕。
    每项均为**真实鼠标/键盘事件**驱动，断言可观察行为（state / 可见性 / 落盘 / 回调）。
    """
    print("\n=== 阶段 4：交互控件真实点击遍历（连接/预设/分层/chrome）===")
    from PyQt6.QtWidgets import QPushButton, QLabel
    from ui.preset_panel import PresetManageDialog, PresetEditDialog

    controller = AppController()
    win = MainWindow(controller)
    win.show(); app.processEvents(); QTest.qWait(60)
    out = []
    created_presets = []

    def case(name, fn):
        try:
            ok, detail = fn()
            out.append((name, bool(ok), detail))
        except Exception as e:
            out.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))

    def find_row_button(dlg, pname, text):
        for wrap in dlg.findChildren(QWidget, "preset_row"):
            if any(l.text() == pname for l in wrap.findChildren(QLabel)):
                for b in wrap.findChildren(QPushButton):
                    if text in b.text():
                        return b
        return None

    try:
        d = win.device_bar

        # —— 分层分段：专家 / 基础 ——
        def c_seg_expert():
            QTest.mouseClick(win.segExpert, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            vis = any(getattr(c, "kind", "") == "expert" and c.isVisible()
                      for c in win._cards.values())
            return (controller.state.get("expertMode") is True and vis,
                    f"expertMode={controller.state.get('expertMode')} expert_card_vis={vis}")
        case("分段·专家", c_seg_expert)

        def c_seg_basic():
            QTest.mouseClick(win.segBasic, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            hid = all(getattr(c, "kind", "") != "expert" or not c.isVisible()
                      for c in win._cards.values())
            return (controller.state.get("expertMode") is False and hid,
                    f"expertMode={controller.state.get('expertMode')} expert_card_hidden={hid}")
        case("分段·基础", c_seg_basic)

        # —— 连接模式：无线 / USB ——
        def c_mode_wifi():
            QTest.mouseClick(d.segWifi, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (controller.state.get("connMode") == "wifi" and d.wifiRow.isVisible(),
                    f"connMode={controller.state.get('connMode')} wifiRow_vis={d.wifiRow.isVisible()}")
        case("连接·无线段", c_mode_wifi)

        # —— 无线 IP / 端口 真实输入 ——
        def c_ip():
            drive_line(win, d.ipLine, "192.168.1.66")
            return (controller.state.get("ip") == "192.168.1.66",
                    f"ip={controller.state.get('ip')!r}")
        case("连接·IP 输入", c_ip)

        def c_port():
            drive_line(win, d.portLine, "5566")
            return (controller.state.get("port") == "5566",
                    f"port={controller.state.get('port')!r}")
        case("连接·端口输入", c_port)

        # —— 无线优化预设（可勾选按钮，覆盖码率/分辨率）——
        def c_wifiopt():
            if not d.wifiOpt.isChecked():
                # QCheckBox 的 Fusion 指示器是其稳定点击目标；点标签中央在部分
                # Windows 后端不会切换，因而按真实指示器坐标发送鼠标事件。
                QTest.mouseClick(d.wifiOpt, Qt.MouseButton.LeftButton,
                                 Qt.KeyboardModifier.NoModifier, QPoint(8, 9))
                app.processEvents(); QTest.qWait(20)
            st = controller.state
            return (st.get("wifiOpt") is True and st.get("bitrate") == "2" and st.get("maxSize") == "800",
                    f"wifiOpt={st.get('wifiOpt')} bitrate={st.get('bitrate')!r} maxSize={st.get('maxSize')!r}")
        case("连接·无线优化", c_wifiopt)

        # —— 无线连接按钮（真实点击，spy 网络入口避免真连 adb 挂起）——
        def c_connect():
            hit = []
            try:
                d.connectWirelessRequested.disconnect(controller.connect_wireless)
            except TypeError:
                pass
            d.connectWirelessRequested.connect(lambda *a, **k: hit.append(1))
            QTest.mouseClick(d.connectBtn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (len(hit) == 1, f"connect_wireless 调用次数={len(hit)}")
        case("连接·无线连接按钮", c_connect)

        # —— 切回 USB 段 ——
        def c_mode_usb():
            QTest.mouseClick(d.segUsb, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (controller.state.get("connMode") == "usb" and not d.wifiRow.isVisible(),
                    f"connMode={controller.state.get('connMode')} wifiRow_vis={d.wifiRow.isVisible()}")
        case("连接·USB 段", c_mode_usb)

        # —— 设备下拉（注入假设备后真实选中）——
        def c_devcombo():
            d.set_devices([("FAKESER", "device", "FakePhone")])
            app.processEvents(); QTest.qWait(10)
            drive_combo(win, d.deviceCombo, "FAKESER")
            return (controller.state.get("device") == "FAKESER",
                    f"device={controller.state.get('device')!r}")
        case("连接·设备下拉", c_devcombo)

        # —— 刷新按钮（spy adb 列表入口）——
        def c_refresh():
            hit = []
            try:
                d.refreshRequested.disconnect(controller.refresh_devices)
            except TypeError:
                pass
            d.refreshRequested.connect(lambda *a, **k: hit.append(1))
            QTest.mouseClick(d.refreshBtn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (len(hit) == 1, f"refresh_devices 调用次数={len(hit)}")
        case("连接·刷新按钮", c_refresh)

        # —— 一键无线投屏（spy 自动编排入口）——
        def c_auto():
            hit = []
            try:
                d.autoWirelessRequested.disconnect(controller.auto_connect_wireless)
            except TypeError:
                pass
            d.autoWirelessRequested.connect(lambda *a, **k: hit.append(1))
            QTest.mouseClick(d.autoBtn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (len(hit) == 1, f"auto_connect_wireless 调用次数={len(hit)}")
        case("连接·一键投屏按钮", c_auto)

        # —— 预设下拉真实选中（先落盘一个预设）——
        def c_preset_select():
            name = "L3IX_sel"
            controller.save_preset(name, include_keys=["vcodec", "bitrate"])
            created_presets.append(name)
            win.preset_panel.set_presets(controller.presets.list())
            app.processEvents(); QTest.qWait(10)
            drive_combo(win, win.preset_panel.combo, name)
            return (controller.state.get("preset_name") == name,
                    f"preset_name={controller.state.get('preset_name')!r}")
        case("预设·下拉选中", c_preset_select)

        # —— 「管理」按钮（真实点击验证信号链路；先摘除会 exec 模态阻塞的原始槽）——
        def c_manage_btn():
            hit = []
            # 关键：原始 manageRequested 已 connect 到 win._open_manage（内部 dlg.exec() 会
            # 模态阻塞测试）。信号连接绑定的是连接时的 bound method，替换 win._open_manage
            # 无效，必须先 disconnect 再接 spy，才能既验证真实点击链路又不阻塞。
            try:
                win.preset_panel.manageRequested.disconnect()
            except Exception:
                pass
            win.preset_panel.manageRequested.connect(lambda *a, **k: hit.append(1))
            QTest.mouseClick(win.preset_panel.manageBtn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (len(hit) == 1, f"manageRequested 触发次数={len(hit)}")
        case("预设·管理按钮", c_manage_btn)

        # —— 管理弹窗：新建保存 ——
        mdlg = PresetManageDialog(controller, win)
        mdlg.show(); app.processEvents(); QTest.qWait(30)

        def c_mng_save():
            name = "L3IX_new"
            created_presets.append(name)
            drive_line(win, mdlg.newName, name)
            btn = next((b for b in mdlg.findChildren(QPushButton) if "保存当前配置" in b.text()), None)
            assert btn is not None, "未找到管理弹窗保存按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            return (controller.presets.exists(name), f"exists({name})={controller.presets.exists(name)}")
        case("管理·新建保存", c_mng_save)

        # —— 管理弹窗：复制 ——
        def c_mng_copy():
            btn = find_row_button(mdlg, "L3IX_new", "复制")
            assert btn is not None, "未找到 L3IX_new 的复制按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            copy_name = "L3IX_new 副本"
            if controller.presets.exists(copy_name):
                created_presets.append(copy_name)
            return (controller.presets.exists(copy_name), f"exists({copy_name})={controller.presets.exists(copy_name)}")
        case("管理·复制", c_mng_copy)

        # —— 管理弹窗：删除确认取消（不应误删）——
        def c_mng_delete_cancel():
            btn = find_row_button(mdlg, "L3IX_new 副本", "删除")
            assert btn is not None, "未找到副本的删除按钮"
            seen = []
            def cancel_delete():
                box = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QMessageBox)), None)
                if box is not None:
                    seen.append(True)
                    cancel = box.button(QMessageBox.StandardButton.Cancel)
                    if cancel is not None:
                        cancel.click()
            QTimer.singleShot(20, cancel_delete)
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            kept = controller.presets.exists("L3IX_new 副本")
            return (kept and bool(seen), f"confirm_seen={bool(seen)} preserved={kept}")
        case("管理·删除取消", c_mng_delete_cancel)

        # —— 管理弹窗：删除确认 ——
        def c_mng_delete():
            btn = find_row_button(mdlg, "L3IX_new 副本", "删除")
            assert btn is not None, "未找到副本的删除按钮"
            seen = []
            def confirm_delete():
                box = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QMessageBox)), None)
                if box is not None:
                    seen.append(True)
                    yes = box.button(QMessageBox.StandardButton.Yes)
                    if yes is not None:
                        yes.click()
            QTimer.singleShot(20, confirm_delete)
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            gone = not controller.presets.exists("L3IX_new 副本")
            return (gone and bool(seen), f"confirm_seen={bool(seen)} deleted={gone}")
        case("管理·删除", c_mng_delete)

        # —— 管理弹窗：关闭 ——
        def c_mng_close():
            btn = next((b for b in mdlg.findChildren(QPushButton)
                        if b.objectName() == "banner_close"), None)
            assert btn is not None, "未找到管理弹窗关闭按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (not mdlg.isVisible(), f"visible={mdlg.isVisible()}")
        case("管理·关闭", c_mng_close)

        # —— 编辑弹窗：分组勾选 + 字段 + 保存 ——
        def c_edit_save():
            name = "L3IX_edit"
            created_presets.append(name)
            edlg = PresetEditDialog(controller, "", win)
            edlg.show(); app.processEvents(); QTest.qWait(30)
            drive_line(win, edlg.nameEdit, name)
            # 真实点击「视频」分组开关
            QTest.mouseClick(edlg._group_cbs["video"], Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            # 真实驱动码率下拉到 4
            drive_combo(win, edlg._editors["bitrate"], "4")
            btn = next((b for b in edlg.findChildren(QPushButton)
                        if b.text() in ("创建预设", "保存修改")), None)
            assert btn is not None, "未找到编辑弹窗保存按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            rec = controller.presets.load(name)
            got = (rec or {}).get("params", {}).get("bitrate")
            return (rec is not None and got == "4",
                    f"saved={rec is not None} params.bitrate={got!r}")
        case("编辑·分组勾选+保存", c_edit_save)

        # —— 红条关闭 ——
        def c_banner_close():
            win.banner.show_error("测试标题", "测试详情")
            app.processEvents(); QTest.qWait(10)
            btn = next((b for b in win.banner.findChildren(QPushButton)
                        if b.objectName() == "banner_close"), None)
            assert btn is not None, "未找到红条关闭按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (not win.banner.isVisible(), f"banner_visible={win.banner.isVisible()}")
        case("红条·关闭", c_banner_close)

        # —— 标题栏最小化 / 还原 ——
        def c_title_minimize():
            QTest.mouseClick(win.minimize_btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(30)
            minimized = bool(win.windowState() & Qt.WindowState.WindowMinimized)
            win.showNormal()
            app.processEvents(); QTest.qWait(20)
            return (minimized and win.isVisible(), f"minimized={minimized} restored_visible={win.isVisible()}")
        case("标题栏·最小化/还原", c_title_minimize)

        # —— 标题栏关闭（放最后，会关窗）——
        def c_title_close():
            btn = next((b for b in win.findChildren(QPushButton, "title_btn")
                        if b.text() == "×"), None)
            assert btn is not None, "未找到标题栏关闭按钮"
            QTest.mouseClick(btn, Qt.MouseButton.LeftButton)
            app.processEvents(); QTest.qWait(20)
            return (not win.isVisible(), f"win_visible={win.isVisible()}")
        case("标题栏·关闭", c_title_close)

    except Exception:
        out.append(("交互阶段异常", False, traceback.format_exc()))
    finally:
        # 清理测试预设
        for n in created_presets:
            try:
                controller.presets.delete(n)
            except Exception:
                pass
        try:
            controller.shutdown()
        except Exception:
            pass
        try:
            win.close()
        except Exception:
            pass
        app.processEvents()

    for name, ok, detail in out:
        print(f"  {'[PASS]' if ok else '[FAIL]'} {name}：{detail}")
    return out


# ============================================================ 主入口
def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("scrcpy-gui · L3 测试")

    phases = sys.argv[1:] or ["all"]
    run_all = "all" in phases

    matrix = phase_matrix(app) if (run_all or "matrix" in phases) else []
    scenarios = phase_scenarios(app) if (run_all or "scenarios" in phases) else []
    interactions = phase_interactions(app) if (run_all or "interact" in phases) else []
    realdev = phase_real_device(app) if (run_all or "realdev" in phases) else []

    # 汇总
    m_fail = [r for r in matrix if not r[2]]
    s_fail = [s for s in scenarios if s[1] is not True]
    ix_fail = [i for i in interactions if i[1] is not True]
    rd_fail = [r for r in realdev if r[1] is False]
    rd_skip = any(r[1] == "SKIP" for r in realdev)

    print("\n================ 汇总 ================")
    print(f"矩阵：{len(matrix)} 组合，失败 {len(m_fail)}")
    print(f"场景：{len(scenarios)} 项，失败 {len(s_fail)}")
    print(f"交互：{len(interactions)} 项，失败 {len(ix_fail)}")
    print(f"实机：{len(realdev)} 项，失败 {len(rd_fail)}，跳过 {int(rd_skip)}")
    print("=======================================")

    report = {
        "matrix_total": len(matrix),
        "matrix_fail": len(m_fail),
        "matrix_failures": [{"key": k, "value": v, "msg": m} for (k, v, _, m) in m_fail],
        "scenarios": [{"name": n, "ok": bool(o), "detail": d} for (n, o, d) in scenarios],
        "interactions": [{"name": n, "ok": bool(o), "detail": d} for (n, o, d) in interactions],
        "interactions_total": len(interactions),
        "interactions_fail": len(ix_fail),
        "real_device": [{"name": n, "result": str(o), "detail": d} for (n, o, d) in realdev],
    }
    with open(os.path.join(HERE, "l3_matrix_results.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"结果已落盘：{os.path.join(HERE, 'l3_matrix_results.json')}")

    core_fail = len(m_fail) + len(s_fail) + len(ix_fail) + len(rd_fail)
    sys.exit(1 if core_fail else 0)


if __name__ == "__main__":
    main()
