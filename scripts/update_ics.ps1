$ErrorActionPreference = 'Stop'

# Usage:
#   .\scripts\update_ics.ps1 -HtmlPath "C:\path\to\lectio.html"
# Optional:
#   -OutPath "docs\calendar.ics" (default)
#   -Timezone "Europe/Copenhagen" (default)
#   -AssignmentsHtmlPath "C:\path\to\opgaver.html"
#   -AssignmentsOutPath "docs\assignments.ics" (default when AssignmentsHtmlPath is given)

param(
  [Parameter(Mandatory = $true)]
  [string]$HtmlPath,

  [string]$OutPath = "docs\\calendar.ics",

  [string]$Timezone = "Europe/Copenhagen",

  [string]$AssignmentsHtmlPath = "",

  [string]$AssignmentsOutPath = "docs\\assignments.ics"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

# Requires dependencies installed in your current Python environment (venv optional):
#   py -m pip install -e .
$pythonLauncher = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if ($AssignmentsHtmlPath -ne "") {
  & $pythonLauncher -m lectio_sync `
    --html $HtmlPath `
    --out $OutPath `
    --tz $Timezone `
    --assignments-html $AssignmentsHtmlPath `
    --assignments-out $AssignmentsOutPath
} else {
  & $pythonLauncher -m lectio_sync --html $HtmlPath --out $OutPath --tz $Timezone
}
