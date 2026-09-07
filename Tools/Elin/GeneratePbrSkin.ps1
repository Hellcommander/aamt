<#
.SYNOPSIS
    Generate PBR skin maps (and optional skinned FBX) for Elin Unity mods.

.DESCRIPTION
    Wraps Shared/pbr_skin_generator.py and Shared/mesh_skin_export.py
    (real Blender pipeline: displaced / armor_panel / organic / silhouette — not a plane stub).
    Writes under Assets/Resources/{System}/Textures/Skins by default.

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName DragonMagic -Theme "dragon scale" -Quality high

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName BloodMagic -ExportMesh -Shape armor_panel

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName IconMagic -ExportMesh -Shape silhouette -Sketch ".\icon.png"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ModPath,
    [Parameter(Mandatory)][string]$SystemName,
    [string]$Theme = "",
    [string]$Colors = "",
    [ValidateSet("draft", "standard", "high", "ultra")]
    [string]$Quality = "standard",
    [int]$Size = 0,
    [switch]$NoSd,
    [switch]$Glow,
    [switch]$ExportMesh,
    [ValidateSet("plane", "cube", "sphere", "cylinder", "panel", "armor", "armor_panel", "displaced", "organic", "extruded", "silhouette", "sketch", "cutout", "heightmap")]
    [string]$Shape = "displaced",
    [string]$Sketch = "",
    [double]$AlphaThreshold = -1,
    [int]$SilhouetteRes = -1,
    [int]$Subdivisions = -1,
    [double]$DisplaceStrength = -1,
    [double]$SolidifyThickness = -1,
    [double]$BevelAmount = -1,
    [switch]$AlsoObj,
    [string]$BlenderPath = ""
)

$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSScriptRoot "ElinAssetRender.psm1") -Force
$shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $pyCmd) { throw "python not found on PATH" }

$safe = ($SystemName -replace '[^A-Za-z0-9_]', '_')
$skinDir = Join-Path $ModPath "Assets\Resources\$SystemName\Textures\Skins"
New-Item -ItemType Directory -Path $skinDir -Force | Out-Null

$spec = @{
    theme = $(if ($Theme) { $Theme } else { "$SystemName fantasy material" })
    system = $SystemName
    shape = $Shape
}
if ($Colors) { $spec.colors = @($Colors.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
if ($Glow) { $spec.glow = $true }

Write-Host "PBR skin -> $skinDir ($safe, quality=$Quality)" -ForegroundColor Cyan
$ok = Invoke-ElinPbrSkin -OutputDir $skinDir -Name $safe -Spec $spec -Quality $Quality -Size $Size -NoSd:$NoSd -Glow:$Glow
if (-not $ok) {
    Write-Error "PBR skin generation failed"
    exit 1
}
Write-Host "[OK] PBR maps written" -ForegroundColor Green

if ($ExportMesh) {
    $meshScript = Join-Path $shared "mesh_skin_export.py"
    $meshDir = Join-Path $ModPath "Assets\Resources\$SystemName\Meshes"
    $fbx = Join-Path $meshDir "${safe}.fbx"
    New-Item -ItemType Directory -Path $meshDir -Force | Out-Null
    $py = $pyCmd.Source
    $meshArgs = @($meshScript, "--skin-dir", $skinDir, "--name", $safe, "--fbx", $fbx, "--shape", $Shape)
    if ($BlenderPath) { $meshArgs += @("--blender", $BlenderPath) }
    if ($Subdivisions -ge 0) { $meshArgs += @("--subdivisions", "$Subdivisions") }
    if ($DisplaceStrength -ge 0) { $meshArgs += @("--displace-strength", "$DisplaceStrength") }
    if ($SolidifyThickness -ge 0) { $meshArgs += @("--solidify-thickness", "$SolidifyThickness") }
    if ($BevelAmount -ge 0) { $meshArgs += @("--bevel-amount", "$BevelAmount") }
    if ($Sketch) { $meshArgs += @("--sketch", $Sketch) }
    if ($AlphaThreshold -ge 0) { $meshArgs += @("--alpha-threshold", "$AlphaThreshold") }
    if ($SilhouetteRes -gt 0) { $meshArgs += @("--silhouette-res", "$SilhouetteRes") }
    if ($AlsoObj) { $meshArgs += @("--obj", (Join-Path $meshDir "${safe}.obj")) }
    Write-Host "Mesh export ($Shape) -> $fbx" -ForegroundColor Cyan
    & $py @meshArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Real Blender mesh export finished" -ForegroundColor Green
    } elseif ($LASTEXITCODE -eq 2) {
        Write-Warning "Mesh export: Blender missing — PBR skins written, no FBX"
    } else {
        Write-Warning "Mesh export returned $LASTEXITCODE (skins still valid)"
    }
}

Write-Host "Done. Import/refresh Unity project to pick up Skins (+ Meshes)." -ForegroundColor Green
