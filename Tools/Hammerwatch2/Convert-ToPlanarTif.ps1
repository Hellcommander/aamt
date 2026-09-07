param(
	[Parameter(Mandatory = $true)]
	[string]$Path,

	[string]$OutDir = "",

	[string]$GimpRoot = "D:\tools\GIMP",

	[switch]$Recurse,

	[switch]$InPlace
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $scriptDir "convert_to_planar_tif.py"

if (-not (Test-Path -LiteralPath $py)) {
	throw "Missing $py"
}

$argsList = @($py, $Path, "--gimp-root", $GimpRoot)
if ($OutDir) { $argsList += @("--out-dir", $OutDir) }
if ($Recurse) { $argsList += "--recurse" }
if ($InPlace) { $argsList += "--in-place" }

Write-Host "GIMP export (contiguous) -> planar post-process (ImageMagick/tiffcp)"
Write-Host "GIMP does not write PlanarConfiguration=2; that step is magick/tiffcp."
& python @argsList
if ($LASTEXITCODE -ne 0) {
	throw "convert_to_planar_tif.py failed ($LASTEXITCODE)"
}
