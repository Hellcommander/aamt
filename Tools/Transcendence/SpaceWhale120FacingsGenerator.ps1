# Space Whale / CrossMod 120 Facings Generator
# Vanilla path: Shared PBR skins → real 3D mesh → Common/blender_ship_spritesheet_export
# (same method as Commonwealth/Sapphire / Export-AamtShipSpritesheet — NOT sketch/2D rotation)

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "C:\Output\SpaceWhale120Facings",

    [Parameter(Mandatory=$false)]
    [string]$ShipId = "",

    [Parameter(Mandatory=$false)]
    [ValidateSet("draft", "standard", "high", "ultra")]
    [string]$Quality = "standard",

    [Parameter(Mandatory=$false)]
    [switch]$NoSd,

    [Parameter(Mandatory=$false)]
    [switch]$SkinsOnly,

    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",

    # Legacy flags kept so old callers don't break; ignored (sketch path removed).
    [Parameter(Mandatory=$false)]
    [string]$TextureDir = "",

    [Parameter(Mandatory=$false)]
    [int]$Columns = 12,

    [Parameter(Mandatory=$false)]
    [int]$Rows = 10,

    [Parameter(Mandatory=$false)]
    [int]$AnimationFrames = 16,

    [Parameter(Mandatory=$false)]
    [switch]$SkipBlender,

    [Parameter(Mandatory=$false)]
    [int]$RenderTimeoutSec = 7200,

    [Parameter(Mandatory=$false)]
    [switch]$LegacyBlobRenderer
)

$ErrorActionPreference = "Stop"
$ToolsDir = $PSScriptRoot

Write-Host "Space Whale / CrossMod 120 Facings" -ForegroundColor Cyan
Write-Host "Method: PBR skins → 3D mesh → ortho spritesheet (vanilla / AAMT)" -ForegroundColor Gray
Write-Host ""

if ($LegacyBlobRenderer) {
    Write-Host "WARNING: -LegacyBlobRenderer uses old blender_space_whale_120_facings.py" -ForegroundColor Yellow
    Write-Host "Prefer the default AAMT mesh path unless debugging." -ForegroundColor Yellow
}

if ($SkipBlender -and -not $SkinsOnly) {
    $SkinsOnly = $true
    Write-Host "SkipBlender set → skins-only mode" -ForegroundColor Yellow
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

$pipe = Join-Path $ToolsDir "tx_ai_pipeline.py"
if (Test-Path -LiteralPath $pipe) {
    & $py $pipe probe
}

$gen = Join-Path $ToolsDir "generate_crossmod_ship_skins.py"
if (-not (Test-Path -LiteralPath $gen)) {
    throw "Missing $gen"
}

$reg = if ($RegistryPath) { $RegistryPath } else {
    Join-Path $ToolsDir "crossmod_ship_skins_registry.json"
}

$pyArgs = @(
    $gen,
    "--out-dir", $OutputDir,
    "--registry", $reg,
    "--quality", $Quality
)
if ($ShipId) { $pyArgs += @("--ship-id", $ShipId) }
if ($NoSd) { $pyArgs += "--no-use-sd" } else { $pyArgs += "--use-sd" }
if ($SkinsOnly) { $pyArgs += "--skins-only" }
if ($BlenderPath) { $pyArgs += @("--blender", $BlenderPath) }

Write-Host "Output: $OutputDir" -ForegroundColor Cyan
Write-Host "Registry: $reg" -ForegroundColor Gray
Write-Host ""

& $py @pyArgs
$code = $LASTEXITCODE
if (Test-Path -LiteralPath $pipe) {
    & $py $pipe release
}
if ($code -ne 0) {
    Write-Host "Generation failed (exit $code)" -ForegroundColor Red
    exit $code
}

Write-Host ""
Write-Host "120 facings generation complete!" -ForegroundColor Green
Write-Host "Expected under $OutputDir :" -ForegroundColor Yellow
Write-Host "  <Ship>/Meshes/<Ship>.fbx          (Source/Models copy after export)" -ForegroundColor Gray
Write-Host "  <Ship>/Skins/*_diffuse.png         (Shared PBR / SD skins)" -ForegroundColor Gray
Write-Host "  <Ship>.jpg + <Ship>Mask.bmp        (vanilla ortho sheet)" -ForegroundColor Gray
Write-Host "  <Ship>_120facings.jpg              (root preview copy)" -ForegroundColor Gray
exit 0
