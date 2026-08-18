# scrcpy-gui v0.1.0

First public Windows x64 release of scrcpy-gui, an unofficial graphical
launcher for the official scrcpy project.

## Included

- USB and wireless connection workflows
- Video, audio, control, recording, and window options
- Basic/expert modes and reusable presets
- Live command preview and scrcpy logs
- Verified official scrcpy v4.1 Windows x64 distribution
- English and Simplified Chinese documentation

## Verification

- Python 3.12 and 3.13 CI passed
- 17 offline tests passed
- Windows package launched without a Python installation
- Bundled `scrcpy.exe` reported v4.1
- Bundled `adb.exe` reported Android Debug Bridge 1.0.41
- Release archive and dependency downloads are SHA-256 verified

## Known limitations

- No Android device was connected in the release environment, so USB mirroring,
  wireless mirroring, recording, and device-specific compatibility were not
  reverified for this release.
- This release supports Windows x64 only.
- Not every scrcpy command-line option is exposed in the GUI yet.

scrcpy-gui is not affiliated with or endorsed by Genymobile. See
`THIRD_PARTY_NOTICES.md` for upstream copyright, license, and source details.
