"""scrcpy-gui 入口。

运行：在 scrcpy-gui/ 目录下 `python main.py`
"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.controller import AppController
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("scrcpy-gui")
    controller = AppController()
    win = MainWindow(controller)
    try:
        win.show()
        return app.exec()
    except KeyboardInterrupt:
        return 0
    finally:
        controller.shutdown()


if __name__ == "__main__":
    sys.exit(main())
