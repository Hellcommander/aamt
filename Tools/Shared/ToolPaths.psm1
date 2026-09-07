<#
.SYNOPSIS
    Canonical AAMT tool-path resolver.

.DESCRIPTION
    After OrganizeTools.ps1 relocated shared scripts into Common\ (and shared
    libraries into Shared\), many per-game orchestrators kept calling tools at
    their old $PSScriptRoot-relative locations and silently broke.

    This module gives every script ONE reliable way to locate the Tools root and
    its Common\ / Shared\ / per-game folders, plus Resolve-ToolScript to find a
    script by name no matter which folder it now lives in.

    Import from anywhere:
        Import-Module (Join-Path $PSScriptRoot "..\Shared\ToolPaths.psm1") -Force
        # or, if depth is unknown, let it find itself:
        Import-Module (Get-ChildItem -Path $PSScriptRoot -Recurse -Filter ToolPaths.psm1 | Select -First 1).FullName
#>

function Get-ToolsRoot {
    <# Walk up from this module until we hit the folder named 'Tools' (or a folder
       that contains both Shared and Common). Falls back to Shared's parent. #>
    $dir = $PSScriptRoot  # = ...\Tools\Shared
    while ($dir) {
        $leaf = Split-Path -Leaf $dir
        if ($leaf -eq "Tools") { return $dir }
        if ((Test-Path (Join-Path $dir "Shared")) -and (Test-Path (Join-Path $dir "Common"))) {
            return $dir
        }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    # Fallback: Shared's parent is the Tools root by construction.
    return (Split-Path -Parent $PSScriptRoot)
}

function Get-SharedDir { return $PSScriptRoot }
function Get-CommonDir { return (Join-Path (Get-ToolsRoot) "Common") }
function Get-GameDir {
    param([Parameter(Mandatory)][string]$Name)
    return (Join-Path (Get-ToolsRoot) $Name)
}

function Resolve-ToolScript {
    <#
    .SYNOPSIS
        Find a tool script/file by name across the canonical locations.
    .PARAMETER Name
        File name to find, e.g. "bake_texture.py" or "CrossGameSpritesheet.ps1".
    .PARAMETER SearchDirs
        Optional extra directories to check FIRST (e.g. the caller's own folder).
    .OUTPUTS
        Full path to the first match, or $null. Emits a warning on miss.
    #>
    param(
        [Parameter(Mandatory)][string]$Name,
        [string[]]$SearchDirs = @()
    )
    $root = Get-ToolsRoot
    $candidates = @()
    $candidates += $SearchDirs
    $candidates += (Get-CommonDir)
    $candidates += (Get-SharedDir)
    $candidates += $root
    foreach ($d in $candidates) {
        if (-not $d) { continue }
        $p = Join-Path $d $Name
        if (Test-Path $p) { return (Resolve-Path $p).Path }
    }
    # Last resort: recursive search under Tools root (bounded, first hit wins).
    $hit = Get-ChildItem -Path $root -Recurse -Filter $Name -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($hit) { return $hit.FullName }
    Write-Warning "Resolve-ToolScript: '$Name' not found under $root"
    return $null
}

Export-ModuleMember -Function Get-ToolsRoot, Get-SharedDir, Get-CommonDir, Get-GameDir, Resolve-ToolScript
