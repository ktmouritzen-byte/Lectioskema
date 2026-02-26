$ErrorActionPreference = 'Stop'

# Generates docs/calendar.ics (and optionally docs/assignments.ics) and commits + pushes them.
# Usage:
#   .\scripts\update_ics_and_push.ps1 -HtmlPath "C:\path\to\lectio.html"
# Optional:
#   -AssignmentsHtmlPath "C:\path\to\opgaver.html"
#   -Branch "main" (default)

param(
  [Parameter(Mandatory = $true)]
  [string]$HtmlPath,

  [string]$AssignmentsHtmlPath = "",

  [string]$Branch = "main"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if ($AssignmentsHtmlPath -ne "") {
  .\scripts\update_ics.ps1 -HtmlPath $HtmlPath -AssignmentsHtmlPath $AssignmentsHtmlPath
} else {
  .\scripts\update_ics.ps1 -HtmlPath $HtmlPath
}

git add docs/calendar.ics
if ($AssignmentsHtmlPath -ne "") {
  git add docs/assignments.ics
}
$changed = git status --porcelain
if (-not $changed) {
  Write-Host "No changes to commit."
  exit 0
}

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Update calendars ($stamp)"
git push origin $Branch
