from __future__ import annotations

from pathlib import Path

import core.runtime as runtime
from app import __version__


def _tool_name(name: str) -> str:
    return f"{name}.exe" if runtime.sys.platform == "win32" else name


def test_version_matches_first_public_release() -> None:
    assert __version__ == "0.1.0"


def test_scrcpy_home_precedes_vendor(monkeypatch, tmp_path) -> None:
    configured = tmp_path / "configured"
    vendor = tmp_path / "project" / "vendor" / "scrcpy"
    configured.mkdir()
    vendor.mkdir(parents=True)
    (configured / _tool_name("scrcpy")).touch()
    (vendor / _tool_name("scrcpy")).touch()

    monkeypatch.setenv(runtime.SCRCPY_HOME_ENV, str(configured))
    monkeypatch.setattr(runtime, "project_root", lambda: tmp_path / "project")
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)

    assert runtime.find_executable("scrcpy") == str((configured / _tool_name("scrcpy")).resolve())


def test_vendor_is_used_without_configured_home(monkeypatch, tmp_path) -> None:
    vendor = tmp_path / "vendor" / "scrcpy"
    vendor.mkdir(parents=True)
    tool = vendor / _tool_name("adb")
    tool.touch()

    monkeypatch.delenv(runtime.SCRCPY_HOME_ENV, raising=False)
    monkeypatch.setattr(runtime, "project_root", lambda: tmp_path)
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)

    assert runtime.find_executable("adb") == str(tool.resolve())


def test_path_is_final_fallback(monkeypatch, tmp_path) -> None:
    path_tool = str((tmp_path / _tool_name("scrcpy")).resolve())
    monkeypatch.delenv(runtime.SCRCPY_HOME_ENV, raising=False)
    monkeypatch.setattr(runtime, "project_root", lambda: tmp_path / "empty")
    monkeypatch.setattr(runtime.shutil, "which", lambda name: path_tool if "scrcpy" in name else None)

    assert runtime.find_executable("scrcpy") == path_tool


def test_missing_tool_returns_actionable_message(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv(runtime.SCRCPY_HOME_ENV, raising=False)
    monkeypatch.setattr(runtime, "project_root", lambda: tmp_path)
    monkeypatch.setattr(runtime.shutil, "which", lambda _name: None)

    assert runtime.find_executable("scrcpy") is None
    assert "scripts/setup-scrcpy.ps1" in runtime.missing_tool_message("scrcpy")
