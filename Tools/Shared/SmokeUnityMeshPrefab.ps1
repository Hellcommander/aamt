<#
.SYNOPSIS
    End-to-end smoke: PBR skins + Blender FBX → Unity material + prefab (version-matched Editor).

.EXAMPLE
    .\SmokeUnityMeshPrefab.ps1
    .\SmokeUnityMeshPrefab.ps1 -RequiredVersion 6000.0.77f1 -Shape armor_panel
#>
[CmdletBinding()]
param(
    [string]$ProjectPath = "",
    [string]$SystemName = "SmokeMesh",
    [ValidateSet("displaced", "armor_panel", "organic", "silhouette", "extruded", "panel")]
    [string]$Shape = "armor_panel",
    [string]$RequiredVersion = "2021.3.45f2",
    [string]$ManualUnityPath = "",
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$shared = $PSScriptRoot
Import-Module (Join-Path $shared "UnityVersionResolver.psm1") -Force
Import-Module (Join-Path $shared "UnityAssetExport.psm1") -Force

if (-not $ProjectPath) {
    $ProjectPath = Join-Path $env:TEMP ("aamt_unity_mesh_prefab_smoke_" + $RequiredVersion.Replace(".", "_"))
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

Write-Host "=== AAMT Unity mesh+prefab smoke ===" -ForegroundColor Cyan
Write-Host "Project: $ProjectPath"
Write-Host "Editor:  $RequiredVersion"
Write-Host "Shape:   $Shape / System: $SystemName"

[void](Initialize-AamtUnityProject -ProjectPath $ProjectPath -EditorVersion $RequiredVersion)

$safe = ($SystemName -replace '[^A-Za-z0-9_]', '_')
$skinDir = Join-Path $ProjectPath "Assets\Resources\$SystemName\Textures\Skins"
$meshDir = Join-Path $ProjectPath "Assets\Resources\$SystemName\Meshes"
New-Item -ItemType Directory -Path $skinDir, $meshDir -Force | Out-Null
$fbx = Join-Path $meshDir "$safe.fbx"

Write-Host "`n[1/3] PBR + Blender mesh..." -ForegroundColor Cyan
& $py (Join-Path $shared "mesh_skin_export.py") `
    --skin-dir $skinDir `
    --name $safe `
    --fbx $fbx `
    --shape $Shape `
    --generate-skin `
    --theme "obsidian plate smoke" `
    --quality draft `
    --no-sd `
    --subdivisions 2 `
    --displace-strength 0.25 `
    --solidify-thickness 0.1
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2) {
    throw "mesh_skin_export failed ($LASTEXITCODE)"
}
if (-not (Test-Path $fbx)) { throw "FBX missing: $fbx" }

Write-Host "`n[2/3] Texture .meta for skins..." -ForegroundColor Cyan
Get-ChildItem $skinDir -Filter "*.png" | ForEach-Object {
    $kind = "default"
    if ($_.Name -match "_normal") { $kind = "normal" }
    & $py (Join-Path $shared "unity_meta.py") $_.FullName --kind $kind --overwrite | Out-Null
}

Write-Host "`n[3/3] Unity batch: material + prefab..." -ForegroundColor Cyan
$ok = Invoke-AamtUnityMeshPrefab `
    -ProjectPath $ProjectPath `
    -SystemName $SystemName `
    -RequiredVersion $RequiredVersion `
    -ManualUnityPath $ManualUnityPath `
    -TimeoutSeconds $TimeoutSeconds

$mat = Join-Path $ProjectPath "Assets\Resources\$SystemName\Materials\${SystemName}_Material.mat"
$prefab = Join-Path $ProjectPath "Assets\Resources\$SystemName\Prefabs\${SystemName}_Prefab.prefab"

Write-Host "`n=== Results ===" -ForegroundColor Cyan
@(
    @{ N = "FBX"; P = $fbx },
    @{ N = "FBX.meta"; P = "$fbx.meta" },
    @{ N = "Material"; P = $mat },
    @{ N = "Prefab"; P = $prefab }
) | ForEach-Object {
    $exists = Test-Path $_.P
    $color = if ($exists) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1}: {2}" -f ($(if ($exists) { "OK" } else { "MISS" }), $_.N, $_.P)) -ForegroundColor $color
}

if (-not $ok -or -not (Test-Path $mat) -or -not (Test-Path $prefab)) {
    Write-Host "Smoke FAILED. Check latest aamt_unity_*.log under %TEMP%." -ForegroundColor Red
    exit 1
}
Write-Host "Smoke PASSED." -ForegroundColor Green
exit 0
