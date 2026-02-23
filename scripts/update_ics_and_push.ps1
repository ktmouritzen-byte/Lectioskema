$ErrorActionPreference = 'Stop'

# Generates docs/calendar.ics and commits + pushes it.
# Usage:
#   .\scripts\update_ics_and_push.ps1 -HtmlPath "C:\path\to\lectio.html"

param(
  [Parameter(Mandatory = $true)]
  [string]$HtmlPath,

  [string]$Branch = "main"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

.\scripts\update_ics.ps1 -HtmlPath $HtmlPath

git add docs/calendar.ics
$changed = git status --porcelain
if (-not $changed) {
  Write-Host "No changes to commit."
  exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Update calendar.ics ($stamp)"
git push origin $Branch
