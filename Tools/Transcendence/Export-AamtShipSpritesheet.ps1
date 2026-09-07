<#
.SYNOPSIS
    Re-export Transcendence ship spritesheets from Source/Models meshes (no mesh regen).

.DESCRIPTION
    After AAMT generates a ship pack, the final FBX used for facings is copied to:
      <Pack>\Source\Models\<Name>.fbx
    Edit that model, then run this script to rebuild JPG / Mask.bmp / hero only.

.EXAMPLE
    # Re-export every model under a pack's Source/Models
    .\Export-AamtShipSpritesheet.ps1 -ReexportFrom "C:\temp\aamt_ship_hd\Source\Models" -Defs

.EXAMPLE
    # Pack root (auto-finds Source\Models) + deploy to Extensions
    .\Export-AamtShipSpritesheet.ps1 -ReexportFrom "C:\temp\aamt_ship_hd" -Defs -DeployTx

.EXAMPLE
    # Single model file
    .\Export-AamtShipSpritesheet.ps1 -ReexportFrom ".\Source\Models\ObsidianFrigate.fbx" -OutDir .
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [Alias("ModelsDir", "ModelPath")]
    [string]$ReexportFrom,

    [string]$OutDir = "",
    [string]$Name = "",
    [string]$Theme = "",
    [string]$BlenderPath = "",
    [int]$Facings = 120,
    [int]$Columns = 12,
    [int]$FrameWidth = 128,
    [switch]$Defs,
    [switch]$DeployTx,
    [string]$TxRoot = "D:\games\Steam\steamapps\common\Transcendence"
)

$ErrorActionPreference = "Stop"
$shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
$pyScript = Join-Path $shared "ship_spritesheet_export.py"
if (-not (Test-Path -LiteralPath $pyScript)) {
    throw "Missing $pyScript"
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

$src = (Resolve-Path -LiteralPath $ReexportFrom).Path
$pyArgs = @(
    $pyScript,
    "--reexport-from", $src,
    "--facings", "$Facings",
    "--columns", "$Columns",
    "--frame-width", "$FrameWidth"
)
if ($OutDir) {
    if (-not (Test-Path -LiteralPath $OutDir)) {
        New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    }
    $pyArgs += @("--out-dir", (Resolve-Path -LiteralPath $OutDir).Path)
}
if ($Name) { $pyArgs += @("--name", $Name) }
if ($Theme) { $pyArgs += @("--theme", $Theme) }
if ($BlenderPath) { $pyArgs += @("--blender", $BlenderPath) }
if ($Defs) { $pyArgs += "--defs" }

Write-Host "Re-export sprites from models: $src" -ForegroundColor Cyan
& $py @pyArgs
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

if ($DeployTx) {
    $deploy = Join-Path $PSScriptRoot "Deploy-AamtTranscendence.ps1"
    $search = if ($OutDir) { $OutDir } else {
        # Prefer pack root when Source/Models was passed
        $p = Get-Item -LiteralPath $src
        if ($p.PSIsContainer -and (Split-Path $p.Name -Leaf) -eq "Models" -and (Split-Path $p.Parent.Name -Leaf) -eq "Source") {
            $p.Parent.Parent.FullName
        } elseif ($p.PSIsContainer -and (Test-Path (Join-Path $p.FullName "Source\Models"))) {
            $p.FullName
        } elseif (-not $p.PSIsContainer) {
            # file under Source/Models
            $dir = $p.Directory
            if ($dir.Name -eq "Models" -and $dir.Parent.Name -eq "Source") { $dir.Parent.Parent.FullName } else { $dir.FullName }
        } else { $src }
    }
    Write-Host "Deploying Transcendence extension from $search ..." -ForegroundColor Cyan
    & $deploy -SourceDir $search -TxRoot $TxRoot
}

exit 0
