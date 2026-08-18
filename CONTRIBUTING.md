# Contributing / 贡献指南

Contributions are welcome. By submitting a contribution, you agree that it is
licensed under the repository's Apache License 2.0.

欢迎提交问题和改进。提交贡献即表示你同意按本仓库 Apache License 2.0 授权。

## Development / 开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
.\scripts\setup-scrcpy.ps1
python main.py
```

Before opening a pull request, run:

```powershell
python -m compileall -q app core ui workers main.py tests
python -m pytest
```

Keep changes focused, add tests for behavior changes, and do not commit device
serials, local paths, recordings, logs, downloaded binaries, or credentials.
