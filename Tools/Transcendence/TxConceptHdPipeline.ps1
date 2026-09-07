# Cursor 3D concept → TRELLIS GLB → backup .blend → Transcendence HD 120-facings
# Highest practical TX ship format: 256px cells, 120 facings, 12 columns, JPG + Mask.bmp
# (capital-whale HD; EarthSlaverHD is 128. Sheet is 3072×2560.)

param(
    [Parameter(Mandatory=$false)]
    [string]$Id = "",

    [Parameter(Mandatory=$false)]
    [switch]$All,

    [Parameter(Mandatory=$false)]
    [string]$Concept = "",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",

    [Parameter(Mandatory=$false)]
    [string]$BackupDir = "",

    [Parameter(Mandatory=$false)]
    [ValidateSet(128, 256, 320)]
    [int]$FrameSize = 256,

    [Parameter(Mandatory=$false)]
    [int]$Facings = 120,

    [Parameter(Mandatory=$false)]
    [int]$Supersample = 4,

    [Parameter(Mandatory=$false)]
    [switch]$SkipTrellis,

    [Parameter(Mandatory=$false)]
    [string]$Glb = ""
)

$ErrorActionPreference = "Stop"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

$script = Join-Path $PSScriptRoot "tx_concept_hd_pipeline.py"
if (-not (Test-Path -LiteralPath $script)) { throw "Missing $script" }

Write-Host "Transcendence HD concept pipeline" -ForegroundColor Cyan
Write-Host "  3D Cursor concept → TRELLIS mesh → backup .blend → 120-facing JPG+BMP" -ForegroundColor Gray
Write-Host "  Frame: ${FrameSize}px  Facings: $Facings  SS×$Supersample" -ForegroundColor Gray
Write-Host ""

$argsList = @(
    $script,
    "--frame-size", "$FrameSize",
    "--facings", "$Facings",
    "--supersample", "$Supersample"
)
if ($All) { $argsList += "--all" }
elseif ($Id) { $argsList += @("--id", $Id) }
else { throw "Pass -Id scSpaceWhale or -All" }

if ($Concept) { $argsList += @("--concept", $Concept) }
if ($OutputDir) { $argsList += @("--out-dir", $OutputDir) }
if ($BackupDir) { $argsList += @("--backup-dir", $BackupDir) }
if ($SkipTrellis) { $argsList += "--skip-trellis" }
if ($Glb) { $argsList += @("--glb", $Glb) }

& $py @argsList
exit $LASTEXITCODE
