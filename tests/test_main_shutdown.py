from __future__ import annotations

import main as app_main


def test_keyboard_interrupt_exits_cleanly_and_stops_controller(monkeypatch) -> None:
    calls: list[str] = []

    class FakeApplication:
        def __init__(self, _argv) -> None:
            calls.append("app")

        def setStyle(self, _style: str) -> None:
            pass

        def setApplicationName(self, _name: str) -> None:
            pass

        def exec(self) -> int:
            raise KeyboardInterrupt

    class FakeController:
        def shutdown(self) -> None:
            calls.append("shutdown")

    class FakeWindow:
        def __init__(self, _controller) -> None:
            pass

        def show(self) -> None:
            calls.append("show")

    monkeypatch.setattr(app_main, "QApplication", FakeApplication)
    monkeypatch.setattr(app_main, "AppController", FakeController)
    monkeypatch.setattr(app_main, "MainWindow", FakeWindow)

    assert app_main.main() == 0
    assert calls == ["app", "show", "shutdown"]
