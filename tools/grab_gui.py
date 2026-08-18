"""真实窗口后端抓取 GUI 截图，用于和 demo 视觉对比。

用法：python tools/grab_gui.py
环境：QT_QPA_PLATFORM=windows（真实窗口，能看到真实渲染结果）
输出：tests/shots/main_full.png、tests/shots/device_bar.png、tests/shots/preset_row.png
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

# —— 路径（同 l3 测试：把项目根加入 sys.path）——
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtTest import QTest


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    from app.controller import AppController
    from ui.main_window import MainWindow

    controller = AppController()
    win = MainWindow(controller)
    win.resize(1180, 760)  # 默认尺寸
    win.show()
    app.processEvents()
    QTest.qWait(300)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "tests", "shots")
    os.makedirs(out_dir, exist_ok=True)

    # 全窗口截图
    full = win.grab()
    full_path = os.path.join(out_dir, "main_full.png")
    full.save(full_path, "PNG")

    # 设备栏区域特写
    db = win.device_bar
    db_pix = db.grab()
    db_path = os.path.join(out_dir, "device_bar.png")
    db_pix.save(db_path, "PNG")

    # 预设行 + 基础/专家 特写（包含整个 toolbar 行）
    # geometry() 是相对于父 widget 的，需要 mapTo(win) 转窗口绝对坐标
    pp_topleft = win.preset_panel.mapTo(win, win.preset_panel.rect().topLeft())
    es_topleft = win.expert_seg.mapTo(win, win.expert_seg.rect().topLeft())
    pp_br = win.preset_panel.mapTo(win, win.preset_panel.rect().bottomRight())
    es_br = win.expert_seg.mapTo(win, win.expert_seg.rect().bottomRight())
    left = max(0, min(pp_topleft.x(), es_topleft.x()) - 4)
    top = max(0, min(pp_topleft.y(), es_topleft.y()) - 4)
    right = min(win.width(), max(pp_br.x(), es_br.x()) + 4)
    bottom = min(win.height(), max(pp_br.y(), es_br.y()) + 4)
    row_rect = QRect(left, top, right - left, bottom - top)
    row_pix = win.grab(row_rect)
    row_path = os.path.join(out_dir, "preset_row.png")
    row_pix.save(row_path, "PNG")
    print(f"preset_row 区域：x={left} y={top} w={right-left} h={bottom-top}")

    # 外观面板特写：验证标题栏入口和锚定浮层的真实渲染。
    win.appearance_btn.click()
    app.processEvents()
    QTest.qWait(80)
    popup = win._appearance_popup
    if popup is not None and popup.isVisible():
        appearance_path = os.path.join(out_dir, "appearance_popover.png")
        popup.grab().save(appearance_path, "PNG")
        print(f"外观面板特写: {os.path.abspath(appearance_path)}")
        popup.hide()

    # 打印关键控件实测尺寸（真实渲染）
    def sz(w):
        return f"{w.width()}x{w.height()}"

    print("=== 真实窗口控件尺寸（window=1180x760）===")
    print(f"autoBtn={sz(win.device_bar.autoBtn)} （全宽目标）")
    print(f"refreshBtn={sz(win.device_bar.refreshBtn)}")
    print(f"manageBtn={sz(win.preset_panel.manageBtn)}")
    print(f"preset_panel={sz(win.preset_panel)} expert_seg={sz(win.expert_seg)}")
    # 检查 preset 与 expert 是否同行
    pp_y, es_y = win.preset_panel.y(), win.expert_seg.y()
    same_row = abs(pp_y - es_y) < 4
    print(f"preset_row 同高={same_row}（preset.y={pp_y} expert.y={es_y}）")
    print(f"全窗={sz(win)}")
    print(f"截图已保存: {os.path.abspath(full_path)}")
    print(f"设备栏特写: {os.path.abspath(db_path)}")
    print(f"预设行特写: {os.path.abspath(row_path)}")
    print("GRAB_DONE")

    # 给窗口一点时间完成绘制后退出
    QTimer.singleShot(200, app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
