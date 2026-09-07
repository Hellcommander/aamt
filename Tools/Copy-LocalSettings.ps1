#Requires -Version 5.1
<#
.SYNOPSIS
  Create machine-local AAMT settings from tracked *.example files.
.DESCRIPTION
  Safe for a fresh public clone. Skips files that already exist.
  Generated assets and third-party clones are not created here — see Fetch-ThirdParty.ps1.
#>
param(
    [switch]$Force,
    [string]$ToolsRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'

$pairs = @(
    @{ Example = 'AssetGenerationSettings.example.ps1'; Target = 'AssetGenerationSettings.ps1' }
    @{ Example = 'TranscendenceTools.ini.example'; Target = 'TranscendenceTools.ini' }
    @{ Example = 'HfTokenProfiles.example.ps1'; Target = 'HfTokenProfiles.local.ps1' }
    @{ Example = 'Qud\settings.example.json'; Target = 'Qud\settings.json' }
    @{ Example = 'apply_these.txt.example'; Target = 'apply_these.txt' }
    @{ Example = 'manual_review.txt.example'; Target = 'manual_review.txt' }
)

$created = 0
$skipped = 0

foreach ($pair in $pairs) {
    $src = Join-Path $ToolsRoot $pair.Example
    $dest = Join-Path $ToolsRoot $pair.Target
    if (-not (Test-Path $src)) {
        Write-Warning "Missing example: $($pair.Example)"
        continue
    }
    if ((Test-Path $dest) -and -not $Force) {
        Write-Host "Skip (exists): $($pair.Target)"
        $skipped++
        continue
    }
    $destDir = Split-Path -Parent $dest
    if ($destDir -and -not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }
    Copy-Item -LiteralPath $src -Destination $dest -Force
    Write-Host "Created: $($pair.Target)"
    $created++
}

Write-Host @"

Done. Created $created file(s), skipped $skipped existing.
Edit TranscendenceTools.ini and AssetGenerationSettings.ps1 for your game paths.
Optional: .\Fetch-ThirdParty.ps1
Qud Lab sim (if granted): .\Qud\QudLab\Fetch-PrivatePack.ps1

See ..\LICENSING.md and SETUP_REQUIRED_TOOLS.md
"@
