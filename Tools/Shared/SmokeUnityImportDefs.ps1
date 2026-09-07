<#
.SYNOPSIS
    Generate a spell/projectile/ship pack with defs, then Unity-import to ScriptableObjects.

.EXAMPLE
    .\SmokeUnityImportDefs.ps1
#>
[CmdletBinding()]
param(
    [string]$ProjectPath = "",
    [string]$RequiredVersion = "2021.3.45f2",
    [string]$ManualUnityPath = "E:\tools\Unity_Editor\2021.3.45f2\Editor\Unity.exe",
    [string]$SystemName = "NatureMagic",
    [int]$TimeoutSeconds = 900,
    [switch]$SkipUnity
)

$ErrorActionPreference = "Stop"
$shared = $PSScriptRoot
Import-Module (Join-Path $shared "UnityVersionResolver.psm1") -Force
Import-Module (Join-Path $shared "UnityAssetExport.psm1") -Force

if (-not $ProjectPath) {
    $ProjectPath = Join-Path $env:TEMP ("aamt_unity_defs_smoke_" + $RequiredVersion.Replace(".", "_"))
}

Write-Host "=== AAMT Unity def import smoke ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectPath"

[void](Initialize-AamtUnityProject -ProjectPath $ProjectPath -EditorVersion $RequiredVersion)

$gen = Join-Path $shared "GenerateGameAsset.ps1"
& $gen -Kind spell -Theme "verdant life pulse" -Name VerdantPulse -ModPath $ProjectPath -SystemName $SystemName -Mesh -NoSd -NoOllama -Defs -FxFrames 2 -ProjFrames 2
if ($LASTEXITCODE -ne 0) { throw "spell pack failed" }
& $gen -Kind projectile -Theme "plasma bolt" -Name PlasmaBolt -ModPath $ProjectPath -SystemName $SystemName -NoSd -NoOllama -Defs
if ($LASTEXITCODE -ne 0) { throw "projectile pack failed" }

# Ensure JSON readable as text on disk (Unity TextAsset)
Get-ChildItem (Join-Path $ProjectPath "Assets\Resources") -Recurse -Filter "*_def.json" | ForEach-Object {
    Write-Host "  def: $($_.FullName)" -ForegroundColor Gray
}

if ($SkipUnity) {
    Write-Host "SkipUnity set - packs written only." -ForegroundColor Yellow
    exit 0
}

$ok = Invoke-AamtUnityImportDefs `
    -ProjectPath $ProjectPath `
    -RequiredVersion $RequiredVersion `
    -ManualUnityPath $ManualUnityPath `
    -TimeoutSeconds $TimeoutSeconds

$so = Join-Path $ProjectPath "Assets\Resources\$SystemName\Spells\VerdantPulse\VerdantPulse_AamtDef.asset"
Write-Host "`n=== Results ===" -ForegroundColor Cyan
Write-Host ("[{0}] ScriptableObject: {1}" -f ($(if (Test-Path $so) {"OK"} else {"MISS"}), $so))
if (-not $ok -or -not (Test-Path $so)) {
    Write-Host "Smoke FAILED (check %TEMP%\aamt_unity_*.log)" -ForegroundColor Red
    exit 1
}
Write-Host "Smoke PASSED." -ForegroundColor Green
exit 0
