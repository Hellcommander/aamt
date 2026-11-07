#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the Arendeth_SpringUI window bundle. Thin wrapper over the Spring UI pipeline (New-QudSpringUI.ps1).

.DESCRIPTION
    Equivalent to:
        .\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json -Build -Install

    The window layout is the spec (specs\springmenu.springui.json); edit it, not the generated prefab.
    -OpenProject opens the staged Unity project to inspect the generated prefab.

.PARAMETER Regenerate
    Accepted for compatibility; the prefab is always regenerated from the spec.
#>
[CmdletBinding()]
param(
    [string]$Spec = "",
    [string]$OutDir = "",
    [switch]$Regenerate,
    [switch]$OpenProject,
    [switch]$NoInstall,
    [string]$UnityPath = "",
    [switch]$AllowMismatchedUnity,
    [int]$TimeoutSeconds = 1200
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Spec) { $Spec = Join-Path $here "specs\springmenu.springui.json" }
$p = @{ Spec = $Spec; TimeoutSeconds = $TimeoutSeconds }
if ($OutDir) { $p.OutDir = $OutDir }
if ($UnityPath) { $p.UnityPath = $UnityPath }
if ($AllowMismatchedUnity) { $p.AllowMismatchedUnity = $true }
if ($OpenProject) { $p.OpenProject = $true } else { $p.Build = $true; if (-not $NoInstall) { $p.Install = $true } }
& (Join-Path $here "New-QudSpringUI.ps1") @p
exit $LASTEXITCODE
