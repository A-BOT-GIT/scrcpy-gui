"""Resolve the external scrcpy and adb executables."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


SCRCPY_HOME_ENV = "SCRCPY_HOME"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def candidate_directories() -> list[Path]:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(Path(bundle_dir))

    configured_home = os.environ.get(SCRCPY_HOME_ENV)
    if configured_home:
        candidates.append(Path(configured_home).expanduser())

    root = project_root()
    candidates.extend((root / "vendor" / "scrcpy", root))

    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def find_executable(name: str) -> str | None:
    platform_name = f"{name}.exe" if sys.platform == "win32" else name
    for directory in candidate_directories():
        candidate = directory / platform_name
        if candidate.is_file():
            return str(candidate)
    return shutil.which(platform_name) or shutil.which(name)


def missing_tool_message(name: str) -> str:
    return (
        f"未找到 {name}。请运行 scripts/setup-scrcpy.ps1，设置 {SCRCPY_HOME_ENV}，"
        "或将官方 scrcpy 工具加入 PATH。"
    )
