from __future__ import annotations

import pytest

from core.presets import PresetManager, sanitize_name


def test_new_preset_cannot_silently_overwrite_existing_record(tmp_path) -> None:
    manager = PresetManager(str(tmp_path))
    manager.save("演示", {"bitrate": "8"}, overwrite=False)

    with pytest.raises(FileExistsError):
        manager.save("演示", {"bitrate": "4"}, overwrite=False)

    assert manager.load("演示")["params"]["bitrate"] == "8"


def test_explicit_overwrite_updates_existing_record(tmp_path) -> None:
    manager = PresetManager(str(tmp_path))
    manager.save("演示", {"bitrate": "8"}, overwrite=False)
    manager.save("演示", {"bitrate": "4"}, overwrite=True)

    assert manager.load("演示")["params"]["bitrate"] == "4"


def test_name_normalization_has_one_shared_result_for_ui_and_storage() -> None:
    assert sanitize_name("  画质/低延迟  ") == "画质低延迟"
