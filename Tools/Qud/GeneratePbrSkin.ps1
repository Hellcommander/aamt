<#
.SYNOPSIS
    Generate PBR skin maps (and optional skinned FBX) for Qud Unity mods.

.DESCRIPTION
    Wraps Shared/pbr_skin_generator.py and Shared/mesh_skin_export.py
    (real Blender pipeline: displaced / armor_panel / organic / silhouette).
    Writes under Assets/Resources/Textures/Skins by default.

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "C:\...\MyMod" -Theme "crystalline chitin" -Quality high

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "C:\...\MyMod" -Name Broodling -ExportMesh -Shape organic

.EXAMPLE
    .\GeneratePbrSkin.ps1 -ModPath "C:\...\MyMod" -Name IconCutout -ExportMesh -Shape silhouette -Sketch ".\icon.png"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ModPath,
    [string]$Name = "qud_mod",
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
$shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not found on PATH" }

$safe = ($Name -replace '[^A-Za-z0-9_]', '_')
$skinDir = Join-Path $ModPath "Assets\Resources\Textures\Skins"
New-Item -ItemType Directory -Path $skinDir -Force | Out-Null

$specPath = Join-Path $env:TEMP "qud_pbr_spec_$safe.json"
$spec = @{
    theme = $(if ($Theme) { $Theme } else { "$Name material" })
    system = $Name
    shape = $Shape
}
if ($Colors) { $spec.colors = @($Colors.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }) }
if ($Glow) { $spec.glow = $true }
[System.IO.File]::WriteAllText($specPath, ($spec | ConvertTo-Json -Compress), (New-Object System.Text.UTF8Encoding $false))

$pbr = Join-Path $shared "pbr_skin_generator.py"
$pbrArgs = @($pbr, "--output-dir", $skinDir, "--name", $safe, "--spec", $specPath, "--quality", $Quality)
if ($Size -gt 0) { $pbrArgs += @("--size", "$Size") }
if ($NoSd) { $pbrArgs += "--no-sd" }
if ($Glow) { $pbrArgs += "--glow" }

Write-Host "PBR skin -> $skinDir ($safe, quality=$Quality)" -ForegroundColor Cyan
& $py @pbrArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "PBR skin generation failed"
    exit 1
}
Write-Host "[OK] PBR maps written" -ForegroundColor Green

if ($ExportMesh) {
    $meshScript = Join-Path $shared "mesh_skin_export.py"
    $meshDir = Join-Path $ModPath "Assets\Resources\Meshes"
    $fbx = Join-Path $meshDir "${safe}.fbx"
    New-Item -ItemType Directory -Path $meshDir -Force | Out-Null
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

Write-Host "Done. Use export_textures_to_unity.py / QudUnityAssetGenerator for bundles." -ForegroundColor Green
