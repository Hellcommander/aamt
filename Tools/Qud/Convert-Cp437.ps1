<#
.SYNOPSIS
  Convert legacy CP437 code points in mod .cs / .xml to UTF-16 (CoQ post-UTF16 strings).

.DESCRIPTION
  Thin wrapper around ApiMigrator.Core.Cp437Converter. Dry-run by default.
  Mapping matches ConsoleLib.Console.CP437.FromCP437 (+ \u000d -> music note).

  Apply mode loads Core in-process (PowerShell) so Steam Workshop paths that deny
  writes from `dotnet.exe` still succeed.

  Never writes under game StreamingAssets / Managed - mods and Workshop only.

.EXAMPLE
  .\Convert-Cp437.ps1 -Path @("C:\...\Mods") -Report .\reports\cp437.md

.EXAMPLE
  .\Convert-Cp437.ps1 -IncludeWorkshop -Apply -NoBackup
#>
[CmdletBinding()]
param(
    [string[]] $Path,
    [string] $Mod,
    [switch] $Apply,
    [switch] $NoBackup,
    [switch] $IncludeWorkshop,
    [switch] $ConvertAmbiguous,
    [switch] $ForceXmlUtf8,
    [switch] $NoXmlEncoding,
    [string] $Report
)

$ErrorActionPreference = "Stop"
$toolsRoot = $PSScriptRoot
$ApiMigratorToolsRoot = $toolsRoot
. (Join-Path $toolsRoot 'scripts\CoqPaths.ps1')
. (Join-Path $toolsRoot 'scripts\ApiMigrator.Isolated.ps1')
$coreProject = Join-Path $toolsRoot "src\ApiMigrator.Core\ApiMigrator.Core.csproj"
$modsRoot = Get-CoqModsRoot -ToolsRoot $toolsRoot

if (-not (Test-Path $coreProject)) {
    throw "ApiMigrator.Core project not found at $coreProject"
}

[void](Ensure-ApiMigratorCoreDll -ToolsRoot $toolsRoot)
$workshop = [ApiMigrator.Core.SteamInstall]::WorkshopContentDirOrFallback

$opts = New-Object ApiMigrator.Core.Cp437Converter+Options
$opts.Paths = New-Object 'System.Collections.Generic.List[string]'
if ($Path -and $Path.Count -gt 0) {
    foreach ($p in $Path) { [void]$opts.Paths.Add($p) }
}
else {
    if (-not (Test-Path -LiteralPath $modsRoot)) {
        throw "Default Mods folder not found at $modsRoot - pass -Path explicitly."
    }
    [void]$opts.Paths.Add($modsRoot)
}
if ($IncludeWorkshop) { [void]$opts.Paths.Add($workshop) }
if ($Mod) { $opts.ModFilter = $Mod }
$opts.Apply = [bool]$Apply
$opts.Backup = -not $NoBackup
$opts.ConvertAmbiguousEscapes = [bool]$ConvertAmbiguous
$opts.ForceXmlUtf8Encoding = [bool]$ForceXmlUtf8
if ($NoXmlEncoding) { $opts.EnsureXmlUtf8Encoding = $false }
if (-not $Report) {
    $Report = Join-Path $toolsRoot ("reports\Cp437_{0:yyyyMMdd_HHmmss}.md" -f (Get-Date))
}
$opts.ReportPath = $Report

Write-Host "CP437 -> UTF-16 converter (no game launch required)"
Write-Host "Scan roots:"
foreach ($p in $opts.Paths) { Write-Host "  $p" }
Write-Host "Apply: $($opts.Apply)  Ambiguous escapes: $($opts.ConvertAmbiguousEscapes)"

$log = [Action[string]]{ param($m) Write-Host $m }
$report = [ApiMigrator.Core.Cp437Converter]::Run($opts, $log, $null)
$written = @($report.FileResults | Where-Object { $_.Changed }).Count

Write-Host ""
Write-Host "=== Summary ==="
Write-Host ("Mode:           {0}" -f ($(if ($opts.Apply) { "APPLY" } else { "DRY-RUN" })))
Write-Host "Files scanned:  $($report.FilesScanned)"
Write-Host "Files w/ hits:  $($report.FileResults.Count)"
Write-Host "Files written:  $written"
Write-Host "Auto-fixes:     $($report.TotalAutoFixes)"
Write-Host "Needs review:   $($report.TotalReviewHits)"
Write-Host "Report:         $Report"
