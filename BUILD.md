# 打包成 EXE（Windows / onedir）

## 一鍵打包（建議）

在專案根目錄開 PowerShell：

```powershell
.\build.ps1
```

輸出位置：

- `.\dist\FFXIV_Launcher\FFXIV_Launcher.exe`

## 用 spec 打包（想加 icon / 版本號時用）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip pyinstaller
python -m PyInstaller --noconfirm --clean .\FFXIV_Launcher.spec
```

## 常見問題

- **打包後缺 dll / 模組找不到**：優先用 `FFXIV_Launcher.spec` 方式打包（已收集常見 hidden-import）。
- **PyAutoGUI 在某些機器上被防毒/權限擋**：請以「一般權限」先測，或加入防毒白名單。
