"""Capture a sanitized application screenshot for the public README."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from app.controller import AppController
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    controller = AppController()
    controller.refresh_devices = lambda: None
    window = MainWindow(controller)
    window.resize(1180, 760)
    window.show()
    app.processEvents()
    QTest.qWait(300)

    output = ROOT / "docs" / "assets" / "main-window.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(output), "PNG"):
        raise RuntimeError(f"Unable to save screenshot: {output}")

    window.close()
    controller.shutdown()
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
