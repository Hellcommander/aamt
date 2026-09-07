#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Move Magi-Tech asset-generation libraries into Transcendence Tools/Starbound.

.DESCRIPTION
    Relocates GeneratorAgent, MeshToSpritePipeline, Lua generation helpers, and
    the vendor download script. Leaves README/CMake shims in the mod so in-game
    includes can still resolve via MAGITECH_STARBOUND_TOOLS.
#>
[CmdletBinding()]
param(
    [string]$ModRoot = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    [string]$ToolsStarbound = ""
)

$ErrorActionPreference = "Stop"
if (-not $ToolsStarbound) {
    $ToolsStarbound = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$destRoot = Join-Path $ToolsStarbound "cpp_generators"
$destAgent = Join-Path $destRoot "GeneratorAgent"
$destMesh = Join-Path $destRoot "mesh_to_sprite"
$destLua = Join-Path $ToolsStarbound "lua_tools"

New-Item -ItemType Directory -Force -Path $destRoot, $destMesh, $destLua | Out-Null

function Move-Tree($src, $dst) {
    if (-not (Test-Path $src)) {
        Write-Host "  skip missing $src" -ForegroundColor Yellow
        return $false
    }
    $srcItem = Get-Item $src
    if ($srcItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Host "  already a link: $src" -ForegroundColor Blue
        return $false
    }
    if ((Test-Path $dst) -and (Get-ChildItem $dst -Force -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
        Write-Host "  dest already populated: $dst" -ForegroundColor Blue
        return $false
    }
    Write-Host "  moving $src -> $dst" -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    # Cross-drive: robocopy /MOVE then remove empty source
    $null = robocopy $src $dst /E /MOVE /NFL /NDL /NJH /NJS /NP
    $code = $LASTEXITCODE
    if ($code -ge 8) { throw "robocopy failed ($code) $src -> $dst" }
    if (Test-Path $src) {
        Remove-Item $src -Recurse -Force -ErrorAction SilentlyContinue
    }
    return $true
}

function Move-File($src, $dstDir) {
    if (-not (Test-Path $src)) { return $false }
    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
    $dst = Join-Path $dstDir (Split-Path $src -Leaf)
    if (Test-Path $dst) {
        Write-Host "  dest file exists: $dst" -ForegroundColor Blue
        Remove-Item $src -Force -ErrorAction SilentlyContinue
        return $true
    }
    Write-Host "  moving file $(Split-Path $src -Leaf)" -ForegroundColor Cyan
    Move-Item -LiteralPath $src -Destination $dst -Force
    return $true
}

Write-Host "Moving Magi-Tech generators into $ToolsStarbound" -ForegroundColor Cyan

$agentSrc = Join-Path $ModRoot "cpp_backend\agents\GeneratorAgent"
Move-Tree $agentSrc $destAgent | Out-Null

$meshH = Join-Path $ModRoot "cpp_backend\core\animation\MeshToSpritePipeline.hpp"
$meshC = Join-Path $ModRoot "cpp_backend\core\animation\MeshToSpritePipeline.cpp"
$meshEx = Join-Path $ModRoot "MeshToSpriteExample.cpp"
Move-File $meshH $destMesh | Out-Null
Move-File $meshC $destMesh | Out-Null
Move-File $meshEx $destMesh | Out-Null

$luaSrc = Join-Path $ModRoot "scripts\tools"
if (Test-Path $luaSrc) {
    foreach ($f in Get-ChildItem $luaSrc -File) {
        $dst = Join-Path $destLua $f.Name
        if (-not (Test-Path $dst)) {
            Copy-Item $f.FullName $dst
            Write-Host "  copied Lua tool $($f.Name)" -ForegroundColor Cyan
        }
    }
}

$ollama = Join-Path $ModRoot "cpp_backend\agents\GeneratorAgent\OllamaLuaHelper.lua"
# After move, Ollama helper lives with GeneratorAgent; also copy into lua_tools
$ollamaMoved = Join-Path $destAgent "OllamaLuaHelper.lua"
if (Test-Path $ollamaMoved) {
    Copy-Item $ollamaMoved (Join-Path $destLua "OllamaLuaHelper.lua") -Force
}

$dl = Join-Path $ModRoot "download_essential_libraries.ps1"
if (Test-Path $dl) {
    $dstDl = Join-Path $destRoot "download_essential_libraries.mod.ps1"
    if (-not (Test-Path $dstDl)) {
        Move-Item $dl $dstDl -Force
        Write-Host "  moved download_essential_libraries.ps1" -ForegroundColor Cyan
    }
}

Write-Host "Move complete." -ForegroundColor Green
Write-Host "  GeneratorAgent: $destAgent"
Write-Host "  MeshToSprite:   $destMesh"
Write-Host "  Lua tools:      $destLua"
