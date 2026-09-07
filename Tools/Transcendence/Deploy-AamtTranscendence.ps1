<#
.SYNOPSIS
    Copy AAMT TranscendenceExtension XML (+ referenced bitmaps) into Extensions/.

.DESCRIPTION
    Finds *_transcendence.xml / *_ship_transcendence.xml under SourceDir, then installs
    each pack as Extensions/AAMT_{Name}/ with relative bitmap paths preserved.

.EXAMPLE
    .\Deploy-AamtTranscendence.ps1 -SourceDir "$env:TEMP\aamt_tx_smoke"
.EXAMPLE
    .\Deploy-AamtTranscendence.ps1 -SourceDir ".\Out\PlasmaBolt" -TxRoot "D:\games\Steam\steamapps\common\Transcendence"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$SourceDir,

    [string]$TxRoot = "D:\games\Steam\steamapps\common\Transcendence",

    [string]$ExtensionsRel = "Extensions"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "SourceDir not found: $SourceDir"
}

$extRoot = Join-Path $TxRoot $ExtensionsRel
if (-not (Test-Path -LiteralPath $extRoot)) {
    New-Item -ItemType Directory -Force -Path $extRoot | Out-Null
}

$xmlFiles = @(
    Get-ChildItem -LiteralPath $SourceDir -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "*_transcendence.xml" -or $_.Name -like "*_ship_transcendence.xml"
        }
)
if ($xmlFiles.Count -eq 0) {
    Write-Warning "No *_transcendence.xml under $SourceDir"
    exit 0
}

function Get-BitmapRels([string]$XmlPath) {
    $text = Get-Content -LiteralPath $XmlPath -Raw -Encoding UTF8
    $rels = New-Object System.Collections.Generic.HashSet[string]
    foreach ($attr in @('bitmap', 'bitmask')) {
        foreach ($m in [regex]::Matches($text, "$attr=`"([^`"]+)`"")) {
            [void]$rels.Add($m.Groups[1].Value.Replace('/', '\'))
        }
    }
    return @($rels)
}

$deployed = 0
foreach ($xf in $xmlFiles) {
    $stem = $xf.BaseName `
        -replace '_ship_transcendence$', '' `
        -replace '_transcendence$', ''
    $packName = "AAMT_$stem"
    $destDir = Join-Path $extRoot $packName
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    Copy-Item -Force -LiteralPath $xf.FullName -Destination (Join-Path $destDir $xf.Name)
    Write-Host "  xml   $($xf.Name) -> $packName\" -ForegroundColor Gray

    $packDir = $xf.DirectoryName
    foreach ($rel in (Get-BitmapRels $xf.FullName)) {
        $srcBmp = Join-Path $packDir $rel
        if (-not (Test-Path -LiteralPath $srcBmp)) {
            Write-Host "  miss  $rel" -ForegroundColor DarkYellow
            continue
        }
        $destBmp = Join-Path $destDir $rel
        $parent = Split-Path -Parent $destBmp
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        Copy-Item -Force -LiteralPath $srcBmp -Destination $destBmp
        Write-Host "  bmp   $rel" -ForegroundColor Gray
    }

    $readmeSrc = Join-Path $packDir "AAMT_TRANSCENDENCE_README.txt"
    if (Test-Path -LiteralPath $readmeSrc) {
        Copy-Item -Force -LiteralPath $readmeSrc -Destination (Join-Path $destDir "AAMT_TRANSCENDENCE_README.txt")
    }

    # Ship rotation assets (mask/hero) may not appear in bitmap="..." attrs
    Get-ChildItem -LiteralPath $packDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -match '^\.(jpg|jpeg|bmp|png)$' -and $_.Name -notlike '*.info.txt' } |
        ForEach-Object {
            $dest = Join-Path $destDir $_.Name
            if (-not (Test-Path -LiteralPath $dest)) {
                Copy-Item -Force -LiteralPath $_.FullName -Destination $dest
                Write-Host "  art   $($_.Name)" -ForegroundColor Gray
            }
        }

    # Preserve Source/Models for in-extension touch-ups / re-export
    $srcModels = Join-Path $packDir "Source\Models"
    if (Test-Path -LiteralPath $srcModels) {
        $destModels = Join-Path $destDir "Source\Models"
        New-Item -ItemType Directory -Force -Path $destModels | Out-Null
        Copy-Item -Force -Recurse -Path (Join-Path $srcModels "*") -Destination $destModels
        Write-Host "  models Source\Models\" -ForegroundColor Gray
    }

    $deployed++
}

Write-Host "Deployed $deployed Transcendence pack(s) -> $extRoot" -ForegroundColor Green
exit 0
