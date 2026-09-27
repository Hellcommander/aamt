<#
.SYNOPSIS
  Compact ApiMigrator digest for local LLMs (no AI suggest / no full Markdown dump).

.DESCRIPTION
  Runs ApiMigrator.Cli migrate --compact against LocalLow Mods (or -Path / -Mod).
  stdout is a short agent-facing summary: auto-fix counts + remaining hit list.
  Use this instead of loading whole mods into context or calling ollama-suggest.

.EXAMPLE
  .\ApiMigrate-Compact.ps1 -Mod Broodmother
.EXAMPLE
  .\ApiMigrate-Compact.ps1 -Path "$env:USERPROFILE\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\MyMod" -Apply
#>
[CmdletBinding()]
param(
    [string[]]$Path,
    [string]$Mod,
    [switch]$Apply,
    [switch]$NoBackup,
    [switch]$IncludeWorkshop
)

$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
if (-not (Test-Path (Join-Path $tools 'src\ApiMigrator.Cli\ApiMigrator.Cli.csproj'))) {
    throw "Run from Tools\Qud (ApiMigrator.Cli not found under $tools)"
}

$modsDefault = Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud\Mods'
$argsList = @('run', '--project', (Join-Path $tools 'src\ApiMigrator.Cli'), '-c', 'Release', '--', 'migrate', '--compact')

if ($Path -and $Path.Count -gt 0) {
    $argsList += '--path'
    $argsList += $Path
} elseif (-not $Mod) {
    $argsList += '--path'
    $argsList += $modsDefault
}

if ($Mod) { $argsList += @('--mod', $Mod) }
if ($Apply) { $argsList += '--apply' }
if ($NoBackup) { $argsList += '--no-backup' }
if ($IncludeWorkshop) { $argsList += '--include-workshop' }

$reportDir = Join-Path $tools 'reports'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$report = Join-Path $reportDir ("ApiMigration_compact_{0:yyyyMMdd_HHmmss}.md" -f (Get-Date))
$argsList += @('--report', $report)

Write-Host "ApiMigrate-Compact (programmatic only — no ollama/AI suggest)" -ForegroundColor Cyan
& dotnet @argsList
exit $LASTEXITCODE
