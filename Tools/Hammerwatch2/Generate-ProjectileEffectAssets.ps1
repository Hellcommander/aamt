<#
.SYNOPSIS
  Generate HW2/HoH2 projectile & VFX sprite sheets WITHOUT Stable Diffusion.

.DESCRIPTION
  Runs reference-compose (generate_hw2_vfx_nonsd.py / generate_hw2_vfx.py).
  Optionally converts output PNGs to planar TIFs via Convert-PngToPlanarTif.ps1.

  Icons still use SD: .\Generate-SkillIcons.ps1

.EXAMPLE
  .\Generate-ProjectileEffectAssets.ps1
  .\Generate-ProjectileEffectAssets.ps1 -Preset soul_skull -ConvertTif
  .\Generate-ProjectileEffectAssets.ps1 -Preset all
#>
[CmdletBinding()]
param(
	[string]$Preset = "soul_skull",
	[string]$OutDir = "",
	[int]$FrameSize = 0,
	[int]$Frames = 0,
	[switch]$ConvertTif,
	[switch]$List
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$py = Join-Path $here "generate_hw2_vfx.py"

if (-not (Test-Path -LiteralPath $py)) {
	throw "Missing $py"
}

$python = $null
foreach ($cand in @("python", "py")) {
	$cmd = Get-Command $cand -ErrorAction SilentlyContinue
	if ($cmd) {
		$python = $cmd.Source
		break
	}
}
if (-not $python) {
	throw "Python not found on PATH."
}

$argv = @($py)
if ($List) {
	$argv += "--list"
} else {
	$argv += @("--preset", $Preset)
	if ($OutDir) { $argv += @("--out", $OutDir) }
	if ($FrameSize -gt 0) { $argv += @("--frame-size", "$FrameSize") }
	if ($Frames -gt 0) { $argv += @("--frames", "$Frames") }
}

Write-Host "Non-SD HW2 VFX: $($argv -join ' ')" -ForegroundColor Cyan
& $python @argv
if ($LASTEXITCODE -ne 0) {
	throw "generate_hw2_vfx.py failed with exit $LASTEXITCODE"
}

if ($ConvertTif -and -not $List) {
	$convert = Join-Path $here "Convert-PngToPlanarTif.ps1"
	if (-not (Test-Path -LiteralPath $convert)) {
		Write-Warning "Convert-PngToPlanarTif.ps1 not found; skipping TIF."
		exit 0
	}
	$target = if ($OutDir) {
		if ([System.IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $here $OutDir }
	} else {
		switch ($Preset) {
			"stone_spikes" { Join-Path $here "GeneratedAssets\druidic_earth" }
			"tremor_ring" { Join-Path $here "GeneratedAssets\druidic_earth" }
			"all" { Join-Path $here "GeneratedAssets" }
			default { Join-Path $here "GeneratedAssets\eldritchsoul" }
		}
	}
	if (Test-Path -LiteralPath $target) {
		Write-Host "Converting PNGs under $target to planar TIF..." -ForegroundColor Cyan
		& $convert -Path $target -Recurse
	} else {
		Write-Warning "Out path not found for TIF convert: $target"
	}
}

Write-Host "Done. Stage sheets from GeneratedAssets/ into your mod after review." -ForegroundColor Green
