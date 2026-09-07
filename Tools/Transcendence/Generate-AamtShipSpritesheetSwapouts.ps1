<#
.SYNOPSIS
    Masked hull/shield spritesheet swapouts for AAMT ships.

.DESCRIPTION
    Composites armor plating under the ship Mask.bmp and a shield ring overlay
    (dilated mask minus hull). Writes:
      Source\Models\Alt\Sheets\Hull\{family}.jpg
      Source\Models\Alt\Sheets\Shield\{family}.jpg[+Mask]
    Then optionally applies equipped armor+shield onto {Name}.jpg
    (preserves {Name}_base.jpg).

.EXAMPLE
    .\Generate-AamtShipSpritesheetSwapouts.ps1 -PackDir "...\AAMT_HdFrigate" -Name HdFrigate -DeployTx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$PackDir,
    [string]$Name = "",
    [string]$ArmorItem = "",
    [string]$ShieldItem = "",
    [string]$ArmorFamily = "",
    [string]$ShieldFamily = "",
    [switch]$Force,
    [switch]$NoApply,
    [switch]$Defs,
    [switch]$DeployTx,
    [string]$TxRoot = "D:\games\Steam\steamapps\common\Transcendence"
)

$ErrorActionPreference = "Stop"
$shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
$pyScript = Join-Path $shared "ship_spritesheet_swapouts.py"
$py = (Get-Command python).Source
$pack = (Resolve-Path -LiteralPath $PackDir).Path

if (-not $Name) {
    $fbx = Get-ChildItem (Join-Path $pack "Source\Models") -Filter "*.fbx" -File -EA SilentlyContinue | Select-Object -First 1
    if ($fbx) { $Name = $fbx.BaseName }
    else {
        $j = Get-ChildItem $pack -Filter "*.jpg" -File | Where-Object { $_.Name -notmatch "Large|Armor|Shield|base" } | Select-Object -First 1
        if ($j) { $Name = [IO.Path]::GetFileNameWithoutExtension($j.Name) }
    }
}
if (-not $Name) { throw "Pass -Name" }

$args = @($pyScript, "--pack-dir", $pack, "--name", $Name, "--tx-root", $TxRoot)
if ($ArmorItem) { $args += @("--armor-item", $ArmorItem) }
if ($ShieldItem) { $args += @("--shield-item", $ShieldItem) }
if ($ArmorFamily) { $args += @("--armor-family", $ArmorFamily) }
if ($ShieldFamily) { $args += @("--shield-family", $ShieldFamily) }
if ($Force) { $args += "--force" }
if ($NoApply) { $args += "--no-apply" }

Write-Host "Masked spritesheet swapouts: $Name" -ForegroundColor Cyan
& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Defs) {
    Write-Host "Rewriting ship XML defs from pack ..." -ForegroundColor Cyan
    & $py -c "import sys; from pathlib import Path; sys.path.insert(0, r'$shared'); from game_asset_defs import rewrite_ship_defs_from_pack; print(rewrite_ship_defs_from_pack(Path(r'$pack'), '$Name', theme='$Name'))"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($DeployTx) {
    & (Join-Path $PSScriptRoot "Deploy-AamtTranscendence.ps1") -SourceDir $pack -TxRoot $TxRoot
}
