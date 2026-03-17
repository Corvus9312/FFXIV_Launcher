$ErrorActionPreference = "Stop"

function Clear-DirSafe {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  if (-not (Test-Path $Path)) { return }

  $maxRetries = 5
  for ($i = 1; $i -le $maxRetries; $i++) {
    try {
      Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
      return
    } catch {
      if ($i -lt $maxRetries) {
        Start-Sleep -Milliseconds 600
      } else {
        # If files are locked (e.g., cv2.pyd), rename the folder and continue.
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backup = "${Path}.old.${stamp}"
        Write-Host "Warning: failed to delete $Path (likely locked). Renaming to $backup" -ForegroundColor Yellow
        Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $backup) -ErrorAction Stop
        return
      }
    }
  }
}

function Ensure-Venv {
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv not found. Install: irm https://astral.sh/uv/install.ps1 | iex"
  }

  if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating venv with uv..." -ForegroundColor Gray
    uv venv .venv
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed" }
  }

  Write-Host "Installing PyInstaller with uv..." -ForegroundColor Gray
  uv pip install --python .\.venv\Scripts\python.exe -U pyinstaller
  if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }
}

Write-Host "== FFXIV_Launcher build (onedir) ==" -ForegroundColor Cyan

Ensure-Venv

Clear-DirSafe ".\\build"
Clear-DirSafe ".\\dist"

& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean .\FFXIV_Launcher.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed (exit=$LASTEXITCODE)" }

Write-Host ""
Write-Host "Build output:" -ForegroundColor Green
Write-Host "  .\\dist\\FFXIV_Launcher\\FFXIV_Launcher.exe"
