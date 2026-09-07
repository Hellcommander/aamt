param(
	[Parameter(Mandatory = $true)]
	[string]$Path,

	[switch]$Recurse
)

$ErrorActionPreference = "Stop"

function Find-Magick {
	foreach ($cand in @(
		"E:\tools\ImageMagick\magick.exe",
		"D:\tools\ImageMagick\magick.exe",
		"magick",
		"convert"
	)) {
		if ($cand -match '[\\/]' -or $cand -match '\.exe$') {
			if (Test-Path -LiteralPath $cand) { return $cand }
		} else {
			$cmd = Get-Command $cand -ErrorAction SilentlyContinue
			if ($cmd) { return $cmd.Source }
		}
	}
	return $null
}

$magick = Find-Magick
if (-not $magick) {
	throw "ImageMagick not found. For vanilla TIFs use Copy-Hw2Tifs.ps1 (hw2_tgas). For custom: Convert-ToPlanarTif.ps1."
}

if (-not (Test-Path -LiteralPath $Path)) {
	throw "Path not found: $Path"
}

$item = Get-Item -LiteralPath $Path
if ($item.PSIsContainer) {
	$pngs = if ($Recurse) {
		Get-ChildItem -LiteralPath $Path -Filter *.png -Recurse -File
	} else {
		Get-ChildItem -LiteralPath $Path -Filter *.png -File
	}
} else {
	if ($item.Extension -ne ".png") {
		throw "Expected a .png file or a folder of PNGs: $Path"
	}
	$pngs = @($item)
}

if ($pngs.Count -eq 0) {
	Write-Host "No PNG files found under $Path"
	exit 0
}

Write-Host "PNG -> planar TIF via ImageMagick (-interlace plane). Masking/recolor may be lost."
Write-Host "Vanilla art: prefer Copy-Hw2Tifs.ps1 from hw2_tgas."

foreach ($png in $pngs) {
	$tif = Join-Path $png.DirectoryName ($png.BaseName + ".tif")
	& $magick $png.FullName -interlace plane $tif
	if ($LASTEXITCODE -ne 0) {
		throw "Failed converting $($png.FullName)"
	}
	Write-Host "  $($png.Name) -> $(Split-Path $tif -Leaf)"
}

Write-Host "Done."
