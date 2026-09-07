<#
.SYNOPSIS
    Ollama mesh+skin design → PBR maps → real Blender FBX for Unity mods.

.DESCRIPTION
    Uses Shared/ollama_mesh_spec.py (prefer 7B models) then mesh_skin_export /
    blender_aamt_mesh (displaced / armor_panel / silhouette / organic).

.EXAMPLE
    .\GenerateMeshFromTheme.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName DragonMagic -Theme "dragon scale pauldron" -NoSd
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ModPath,
    [Parameter(Mandatory)][string]$SystemName,
    [Parameter(Mandatory)][string]$Theme,
    [string]$Model = "qwen2.5-coder:7b",
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [ValidateSet("draft", "standard", "high", "ultra")]
    [string]$Quality = "draft",
    [switch]$NoSd,
    [string]$Shape = "",
    [switch]$AlsoObj,
    [string]$BlenderPath = "",
    [ValidateSet("Elin", "Qud")]
    [string]$Layout = "Elin"
)

$ErrorActionPreference = "Stop"
$shared = Join-Path $PSScriptRoot "."
if (-not (Test-Path (Join-Path $shared "ollama_mesh_spec.py"))) {
    $shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
}
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not found on PATH" }

$safe = ($SystemName -replace '[^A-Za-z0-9_]', '_')
if ($Layout -eq "Elin") {
    $skinDir = Join-Path $ModPath "Assets\Resources\$SystemName\Textures\Skins"
    $meshDir = Join-Path $ModPath "Assets\Resources\$SystemName\Meshes"
} else {
    $skinDir = Join-Path $ModPath "Assets\Resources\Textures\Skins"
    $meshDir = Join-Path $ModPath "Assets\Resources\Meshes"
}
New-Item -ItemType Directory -Path $skinDir, $meshDir -Force | Out-Null
$fbx = Join-Path $meshDir "$safe.fbx"

$script = Join-Path $shared "ollama_mesh_spec.py"
$pyArgs = @(
    $script,
    "--theme", $Theme,
    "--name", $safe,
    "--out-dir", $skinDir,
    "--fbx", $fbx,
    "--model", $Model,
    "--ollama-url", $OllamaUrl,
    "--quality", $Quality
)
if ($NoSd) { $pyArgs += "--no-sd" }
if ($Shape) { $pyArgs += @("--shape", $Shape) }
if ($AlsoObj) { $pyArgs += @("--obj", (Join-Path $meshDir "$safe.obj")) }
if ($BlenderPath) { $pyArgs += @("--blender", $BlenderPath) }

Write-Host "Ollama → PBR → Blender mesh ($Layout)..." -ForegroundColor Cyan
& $py @pyArgs
if ($LASTEXITCODE -ne 0) {
    Write-Warning "GenerateMeshFromTheme exited $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "[OK] $fbx" -ForegroundColor Green
