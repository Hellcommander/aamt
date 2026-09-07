param(
	[Parameter(Mandatory = $true)]
	[string[]]$Paths,

	[string]$GameRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2",

	[string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $OutDir) {
	$OutDir = Join-Path $PSScriptRoot "GeneratedAssets"
}

$assetsBin = Join-Path $GameRoot "res\assets.bin"
if (-not (Test-Path $assetsBin)) {
	throw "assets.bin not found: $assetsBin"
}

$extractPy = Join-Path $PSScriptRoot "extract_hw2_assets.py"
if (-not (Test-Path $extractPy)) {
	throw "Missing extract_hw2_assets.py next to this script."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$argList = @($extractPy, "--assets", $assetsBin, "--out", $OutDir) + ($Paths | ForEach-Object { @("--path", $_) })
Write-Host "Extracting $($Paths.Count) path(s) from assets.bin -> $OutDir"
& python @argList
if ($LASTEXITCODE -ne 0) {
	throw "extract_hw2_assets.py failed with exit code $LASTEXITCODE"
}
