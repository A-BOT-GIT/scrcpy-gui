# scrcpy-gui

English | [简体中文](README.md)

An unofficial Windows GUI launcher for scrcpy. It organizes common connection,
video, audio, control, recording, and window options into a desktop interface
while preserving a live command preview and runtime logs.

> This project is not affiliated with or endorsed by Genymobile. Mirroring and
> device control are provided by the official
> [Genymobile/scrcpy](https://github.com/Genymobile/scrcpy) project.

![scrcpy-gui main window](docs/assets/main-window.png)

## Features

- USB device discovery with unauthorized and offline states
- USB and wireless TCP/IP workflows
- Video size, bitrate, frame rate, codec, and crop options
- Audio forwarding, input control, recording, and window settings
- Basic/expert modes and JSON presets
- Live scrcpy command preview, logs, and start/stop controls
- Dark, light, and custom background themes

## For users

Download `scrcpy-gui-v0.1.0-windows-x64.zip` from
[Releases](https://github.com/A-BOT-GIT/scrcpy-gui/releases), extract it, and run
`scrcpy-gui.exe`. The package includes the unmodified official scrcpy v4.1
Windows x64 distribution, so Python is not required.

Enable Developer options and USB debugging on the Android device. Accept the
debugging authorization prompt on the first connection.

## Run from source

Requirements: Windows 10/11, Python 3.12+, and PowerShell 5.1+.

```powershell
git clone https://github.com/A-BOT-GIT/scrcpy-gui.git
cd scrcpy-gui
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
.\scripts\setup-scrcpy.ps1
python main.py
```

The setup script downloads the official `scrcpy-win64-v4.1.zip`, verifies its
SHA-256 digest, and installs it into the ignored `vendor/scrcpy` directory. You
may instead set `SCRCPY_HOME` to an existing official scrcpy directory or place
`scrcpy` and `adb` on PATH.

Lookup order: release directory, `SCRCPY_HOME`, `vendor/scrcpy`, project root,
then PATH.

## Development and packaging

```powershell
python -m compileall -q app core ui workers main.py tests
python -m pytest
.\scripts\build-release.ps1 -Version 0.1.0
```

The package and its SHA-256 file are written under `build/`.

## Troubleshooting

**scrcpy or adb cannot be found**

Run `.\scripts\setup-scrcpy.ps1` or configure `SCRCPY_HOME`.

**The device list is empty**

Confirm USB debugging is enabled, run `adb devices -l`, and accept the device
authorization prompt.

**Control does not work on Xiaomi/Redmi devices**

Some devices also require "USB debugging (Security settings)" and a reboot.

**Wireless connection fails**

Authorize once over USB and ensure the computer and device are on the same LAN.

## License and third-party software

scrcpy-gui is licensed under the [Apache License 2.0](LICENSE). Windows releases
redistribute the official scrcpy v4.1 package; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for copyright, license, source,
and verification details.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before contributing. Report security
issues privately as described in [SECURITY.md](SECURITY.md).

## Current limitations

- The first release targets Windows x64 only
- Newer scrcpy features such as camera mirroring are not all exposed in the GUI
- Device compatibility depends on the vendor, Android version, and scrcpy
