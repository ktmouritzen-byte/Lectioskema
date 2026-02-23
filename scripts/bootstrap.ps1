$ErrorActionPreference = 'Stop'

<#
Bootstrap (NO VENV)

This repo intentionally does NOT auto-create virtual environments.

What this script does:
- Finds a Python launcher (`py` preferred on Windows)
- Prints Python executable + version
- Checks that required imports are available
- If missing, prints the install command you can run (but does NOT install unless -Install is passed)

Usage:
  .\scripts\bootstrap.ps1
  .\scripts\bootstrap.ps1 -Install
#>

param(
  [switch]$Install
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$pythonLauncher = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Write-Host "Using Python launcher: $pythonLauncher"
& $pythonLauncher -c "import sys; print('Python:', sys.version.replace('\n',' ')); print('Executable:', sys.executable)"

$requiredImports = @(
  "bs4",
  "lxml",
  "dateutil"
)

$missing = @()
foreach ($mod in $requiredImports) {
  $ok = $true
  try {
    & $pythonLauncher -c "import $mod" | Out-Null
  } catch {
    $ok = $false
  }

  if (-not $ok) {
    $missing += $mod
  }
}

if ($missing.Count -eq 0) {
  Write-Host "All required Python imports are available."
  exit 0
}

Write-Warning ("Missing Python modules: " + ($missing -join ", "))
Write-Host ""
Write-Host "This repo does not create virtual environments automatically."
Write-Host "Install dependencies into your CURRENT Python environment (venv optional) with:"
Write-Host "  $pythonLauncher -m pip install -e ."

if ($Install) {
  Write-Host ""
  Write-Host "-Install specified; installing now..."
  & $pythonLauncher -m pip install -e .
}
