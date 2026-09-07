<#
.SYNOPSIS
    Copy AAMT *_elin_ability.json (+ icons) into the live Elin AamtSpellInjector defs folder.

.EXAMPLE
    .\Deploy-AamtElinAbility.ps1 -SourceDir "E:\mod\Assets\Resources\NatureMagic\Spells\VerdantPulse"
.EXAMPLE
    .\Deploy-AamtElinAbility.ps1 -SourceDir ".\ElinAssets" -ElinRoot "E:\SteamLibrary\steamapps\common\Elin"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SourceDir,

    [string]$ElinRoot = "E:\SteamLibrary\steamapps\common\Elin",

    [string]$PluginRel = "BepInEx\plugins\AamtSpellInjector"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "SourceDir not found: $SourceDir"
}

$defsDir = Join-Path $ElinRoot (Join-Path $PluginRel "defs")
$iconsDir = Join-Path $defsDir "icons"
New-Item -ItemType Directory -Force -Path $defsDir | Out-Null
New-Item -ItemType Directory -Force -Path $iconsDir | Out-Null

$jsonFiles = @(Get-ChildItem -LiteralPath $SourceDir -Recurse -Filter "*_elin_ability.json" -File -ErrorAction SilentlyContinue)
if ($jsonFiles.Count -eq 0) {
    Write-Warning "No *_elin_ability.json under $SourceDir"
    exit 0
}

$deployed = 0
foreach ($jf in $jsonFiles) {
    Copy-Item -Force -LiteralPath $jf.FullName -Destination (Join-Path $defsDir $jf.Name)
    $deployed++

    try {
        $obj = Get-Content -LiteralPath $jf.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Warning "Could not parse $($jf.Name): $_"
        continue
    }

    $alias = $null
    if ($obj.row -and $obj.row.alias) { $alias = [string]$obj.row.alias }
    if (-not $alias) { continue }

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($obj.assets -and $obj.assets.iconPath) {
        $rel = [string]$obj.assets.iconPath
        $candidates.Add((Join-Path $jf.DirectoryName $rel))
        $candidates.Add((Join-Path $SourceDir $rel))
    }
    # Common ElinSpellAssetGenerator layout
    $candidates.Add((Join-Path $SourceDir "icons\$($alias).png"))
    $stem = ($jf.BaseName -replace '_elin_ability$', '')
    $candidates.Add((Join-Path $SourceDir "icons\${stem}.png"))
    $candidates.Add((Join-Path $SourceDir "icons\${stem}_icon.png"))
    Get-ChildItem -LiteralPath (Join-Path $SourceDir "icons") -Filter "*.png" -File -ErrorAction SilentlyContinue |
        Where-Object { $_.BaseName -like "*$stem*" -or $_.BaseName -eq $alias } |
        ForEach-Object { $candidates.Add($_.FullName) }

    $iconSrc = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($iconSrc) {
        $destIcon = Join-Path $iconsDir "$alias.png"
        Copy-Item -Force -LiteralPath $iconSrc -Destination $destIcon
        Write-Host "  icon  $alias <- $iconSrc" -ForegroundColor Gray
    } else {
        Write-Host "  icon  $alias (missing - injector will use default)" -ForegroundColor DarkYellow
    }

    # FX frames -> defs/fx/{alias}/
    $fxDest = Join-Path $defsDir "fx\$alias"
    New-Item -ItemType Directory -Force -Path $fxDest | Out-Null
    $fxCopied = 0
    if ($obj.assets -and $obj.assets.fxPaths) {
        foreach ($rel in @($obj.assets.fxPaths)) {
            $src = Join-Path $jf.DirectoryName ([string]$rel)
            if (-not (Test-Path -LiteralPath $src)) { $src = Join-Path $SourceDir ([string]$rel) }
            if (Test-Path -LiteralPath $src) {
                Copy-Item -Force -LiteralPath $src -Destination (Join-Path $fxDest (Split-Path $src -Leaf))
                $fxCopied++
            }
        }
    }
    $fxSrcDir = Join-Path $SourceDir "fx"
    if (Test-Path -LiteralPath $fxSrcDir) {
        Get-ChildItem -LiteralPath $fxSrcDir -Filter "*.png" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Force -LiteralPath $_.FullName -Destination (Join-Path $fxDest $_.Name)
            $fxCopied++
        }
    }

    # Projectile frames -> defs/proj/{alias}/
    $projDest = Join-Path $defsDir "proj\$alias"
    New-Item -ItemType Directory -Force -Path $projDest | Out-Null
    $projCopied = 0
    if ($obj.assets -and $obj.assets.projectilePaths) {
        foreach ($rel in @($obj.assets.projectilePaths)) {
            $src = Join-Path $jf.DirectoryName ([string]$rel)
            if (-not (Test-Path -LiteralPath $src)) { $src = Join-Path $SourceDir ([string]$rel) }
            if (Test-Path -LiteralPath $src) {
                Copy-Item -Force -LiteralPath $src -Destination (Join-Path $projDest (Split-Path $src -Leaf))
                $projCopied++
            }
        }
    }
    $projSrcDir = Join-Path $SourceDir "projectiles"
    if (Test-Path -LiteralPath $projSrcDir) {
        Get-ChildItem -LiteralPath $projSrcDir -Filter "*.png" -File -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Force -LiteralPath $_.FullName -Destination (Join-Path $projDest $_.Name)
            $projCopied++
        }
    }

    Write-Host "  fx/proj $alias fx=$fxCopied proj=$projCopied" -ForegroundColor Gray
    Write-Host "  def   $($jf.Name) -> $defsDir" -ForegroundColor Gray
}

Write-Host "Deployed $deployed ability def(s) -> $defsDir" -ForegroundColor Green
Write-Host "Restart Elin (or reload sources) for AamtSpellInjector to pick them up." -ForegroundColor Yellow
