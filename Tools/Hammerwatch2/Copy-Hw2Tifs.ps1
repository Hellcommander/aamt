param(
	[Parameter(Mandatory = $true)]
	[string[]]$RelativePaths,

	[string]$ModRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2\Druidic_Warden",

	[string]$TifsRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2\hw2_tgas",

	[switch]$WhatIf
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $TifsRoot)) {
	throw "HW2 TIFS folder not found: $TifsRoot (wiki 'Replacement' / HW2 TIFS ZIP)"
}
if (-not (Test-Path -LiteralPath $ModRoot)) {
	throw "Mod root not found: $ModRoot"
}

Write-Host "Source (correct planar TIFs): $TifsRoot"
Write-Host "Dest mod: $ModRoot"
Write-Host "Never copy TIFs from unpacked_assets - use this folder instead."

$copied = 0
foreach ($rel in $RelativePaths) {
	$rel = $rel -replace "/", "\"
	$rel = $rel.TrimStart("\")
	$src = Join-Path $TifsRoot $rel
	$dst = Join-Path $ModRoot $rel

	if (-not (Test-Path -LiteralPath $src)) {
		Write-Warning "Missing in hw2_tgas: $rel"
		continue
	}

	$dstDir = Split-Path -Parent $dst
	if ($WhatIf) {
		Write-Host "WhatIf: $src -> $dst"
		continue
	}

	New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
	Copy-Item -LiteralPath $src -Destination $dst -Force
	Write-Host "  $rel"
	$copied++
}

Write-Host ("Copied {0} file(s)." -f $copied)
