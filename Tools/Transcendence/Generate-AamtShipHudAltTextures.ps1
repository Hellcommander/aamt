<#
.SYNOPSIS
    Generate alt Armor/Shield HUD textures from current game + DLC + mod ItemTypes.

.DESCRIPTION
    Scans Transcendence armor/shield content and writes UI textures under:
      <Pack>\Source\Models\Alt\Textures\{Armor|Shield}\*.png

    Re-run after adding mods or DLC — only missing textures are created unless -Force.
    Uses Stable Diffusion when available; otherwise procedural textures from item families.
    Unique ship HUD composition picks these up automatically.

.EXAMPLE
    .\Generate-AamtShipHudAltTextures.ps1 -PackDir "D:\...\Extensions\AAMT_HdFrigate" -NoSd

.EXAMPLE
    # Full catalog regenerate with SD + Ollama prompts, then rebuild HUD XML
    .\Generate-AamtShipHudAltTextures.ps1 -PackDir "C:\temp\aamt_ship_hd" -Force -Ollama -RebuildHud -DeployTx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [Alias("OutDir", "SourceDir")]
    [string]$PackDir,

    [string]$Name = "",
    [string]$Hero = "",
    [string]$Mesh = "",
    [string]$TxRoot = "D:\games\Steam\steamapps\common\Transcendence",
    [switch]$Force,
    [switch]$NoSd,
    [switch]$Ollama,
    [string]$Model = "qwen2.5-coder:7b",
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [int]$MaxPerKind = 0,
    [int]$Size = 256,
    [switch]$ArmorOnly,
    [switch]$ShieldOnly,
    [switch]$RebuildHud,
    [switch]$Defs,
    [switch]$DeployTx
)

$ErrorActionPreference = "Stop"
$shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
$pyScript = Join-Path $shared "ship_hud_alt_textures.py"
if (-not (Test-Path -LiteralPath $pyScript)) { throw "Missing $pyScript" }

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

$pack = (Resolve-Path -LiteralPath $PackDir).Path
$pyArgs = @($pyScript, "--pack-dir", $pack, "--tx-root", $TxRoot, "--size", "$Size", "--model", $Model, "--ollama-url", $OllamaUrl)
if ($Name) { $pyArgs += @("--name", $Name) }
if ($Hero) { $pyArgs += @("--hero", (Resolve-Path -LiteralPath $Hero).Path) }
if ($Mesh) { $pyArgs += @("--mesh", (Resolve-Path -LiteralPath $Mesh).Path) }
if ($Force) { $pyArgs += "--force" }
if ($NoSd) { $pyArgs += "--no-sd" }
if ($Ollama) { $pyArgs += "--ollama" }
if ($MaxPerKind -gt 0) { $pyArgs += @("--max-per-kind", "$MaxPerKind") }
if ($ArmorOnly) { $pyArgs += "--armor-only" }
if ($ShieldOnly) { $pyArgs += "--shield-only" }

Write-Host "Generate alt HUD textures from current content -> $pack" -ForegroundColor Cyan
& $py @pyArgs
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

if ($RebuildHud -or $Defs) {
    $shipName = $Name
    if (-not $shipName) {
        $fbx = Get-ChildItem -LiteralPath (Join-Path $pack "Source\Models") -Filter "*.fbx" -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Directory.Name -eq "Models" } | Select-Object -First 1
        if ($fbx) { $shipName = $fbx.BaseName }
    }
    if (-not $shipName) {
        $jpg = Get-ChildItem -LiteralPath $pack -Filter "*Large.jpg" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($jpg) { $shipName = $jpg.BaseName -replace "Large$", "" }
    }
    if (-not $shipName) { throw "Could not infer ship -Name for HUD rebuild" }

    Write-Host "Rebuilding unique HUD for $shipName ..." -ForegroundColor Cyan
    $hudPy = @"
import sys
from pathlib import Path
sys.path.insert(0, r'$shared')
from ship_hud_export import export_unique_ship_hud
from game_asset_defs import rewrite_ship_defs_from_pack
pack = Path(r'$pack')
name = '$shipName'
hero = pack / f'{name}Large.jpg'
mesh = pack / 'Source' / 'Models' / f'{name}.fbx'
export_unique_ship_hud(pack, name, hero=hero if hero.is_file() else None,
    base_mesh=mesh if mesh.is_file() else None, unique_hud=True,
    spec={'no_sd': True, 'ensure_alt_textures': False})
try:
    from ship_spritesheet_swapouts import generate_spritesheet_swapouts
    sheet = pack / f'{name}.jpg'
    mask = pack / f'{name}Mask.bmp'
    base = pack / f'{name}_base.jpg'
    src = base if base.is_file() else sheet
    if src.is_file() and mask.is_file():
        generate_spritesheet_swapouts(pack, name, sheet=src, mask=mask, apply_active=True, only_missing=True)
except Exception as exc:
    print('swapouts skip', exc)
xml = rewrite_ship_defs_from_pack(pack, name, theme=name)
print('ok', xml)
"@
    & $py -c $hudPy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($DeployTx) {
    $deploy = Join-Path $PSScriptRoot "Deploy-AamtTranscendence.ps1"
    & $deploy -SourceDir $pack -TxRoot $TxRoot
}

Write-Host "Alt HUD textures ready under Source\Models\Alt\Textures\" -ForegroundColor Green
