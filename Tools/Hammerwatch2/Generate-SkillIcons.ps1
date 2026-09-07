<#
.SYNOPSIS
  Generate HW2 skill/UI icons via local SD3.5 (icons only).

.DESCRIPTION
  SD is for icons only. Projectiles use Vortex + Blender projectile tools
  (see README.md).

.EXAMPLE
  .\Generate-SkillIcons.ps1 -Name "soulburst" -Description "violet necrotic soul explosion, warlock skill icon"
#>
[CmdletBinding()]
param(
	[Parameter(Mandatory = $true)]
	[string]$Name,

	[Parameter(Mandatory = $true)]
	[string]$Description,

	[ValidateSet("draft", "standard", "high", "ultra")]
	[string]$Quality = "standard",

	[int]$Size = 32,

	[int]$Seed = 42,

	[string]$OutDir = "",

	[switch]$DeployToMod,

	[string]$ModRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2\eldritchsoul"
)

$ErrorActionPreference = "Stop"
if (-not $OutDir) {
	$OutDir = Join-Path $PSScriptRoot "GeneratedAssets\icons"
}

$py = Join-Path $PSScriptRoot "generate_hw2_icons.py"
Write-Host "Generating HW2 skill icon '$Name'..." -ForegroundColor Cyan
& python $py --name $Name --description $Description --out-dir $OutDir --size $Size --quality $Quality --seed $Seed
if ($LASTEXITCODE -ne 0) { throw "generate_hw2_icons.py failed" }

$safe = ($Name -replace '[^\w\-]+', '_').ToLowerInvariant()
$outPath = Join-Path $OutDir "$safe.png"

if ($DeployToMod -and (Test-Path $outPath)) {
	$dest = Join-Path $ModRoot "players\eldritchsoul\icons"
	New-Item -ItemType Directory -Force -Path $dest | Out-Null
	Copy-Item $outPath $dest -Force
	Write-Host "Deployed to $dest" -ForegroundColor Green
}

Write-Host "Done: $outPath" -ForegroundColor Green
