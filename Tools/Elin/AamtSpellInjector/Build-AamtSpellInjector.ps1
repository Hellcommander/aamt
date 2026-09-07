# Build and deploy AAMT Spell Injector to Elin BepInEx/plugins.
param(
  [string]$ElinRoot = "E:\SteamLibrary\steamapps\common\Elin",
  [switch]$NoDeploy,
  [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$csproj = Join-Path $here "AamtSpellInjector.csproj"
$outDir = Join-Path $here "bin\$Configuration"
$deployDir = Join-Path $ElinRoot "BepInEx\plugins\AamtSpellInjector"

Write-Host "Building AamtSpellInjector ($Configuration)..."
dotnet build $csproj -c $Configuration -p:ElinRoot="$ElinRoot"
if ($LASTEXITCODE -ne 0) { throw "dotnet build failed ($LASTEXITCODE)" }

$dll = Join-Path $outDir "AamtSpellInjector.dll"
if (-not (Test-Path $dll)) { throw "Missing output: $dll" }

if ($NoDeploy) {
  Write-Host "Built: $dll (deploy skipped)"
  exit 0
}

New-Item -ItemType Directory -Force -Path $deployDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $deployDir "defs") | Out-Null
Copy-Item -Force $dll (Join-Path $deployDir "AamtSpellInjector.dll")

$sampleSrc = Join-Path $here "defs"
if (Test-Path $sampleSrc) {
  Copy-Item -Force -Recurse (Join-Path $sampleSrc "*") (Join-Path $deployDir "defs") -ErrorAction SilentlyContinue
}

Write-Host "Deployed -> $deployDir"
Write-Host "Place *_elin_ability.json under: $(Join-Path $deployDir 'defs')"
