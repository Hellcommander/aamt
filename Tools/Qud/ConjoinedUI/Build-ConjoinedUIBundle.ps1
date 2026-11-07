#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the Conjoined Extended picker bundle. Thin wrapper over the Spring UI pipeline (..\SpringUI\New-QudSpringUI.ps1).

.DESCRIPTION
    Equivalent to:
        ..\SpringUI\New-QudSpringUI.ps1 -Spec ..\SpringUI\specs\conjoined_picker.springui.json -Build -Install

    The window layout is the spec (SpringUI\specs\conjoined_picker.springui.json); edit it, not the generated prefab.
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
$pipeline = Join-Path (Split-Path -Parent $here) "SpringUI"
if (-not $Spec) { $Spec = Join-Path $pipeline "specs\conjoined_picker.springui.json" }
$p = @{ Spec = $Spec; TimeoutSeconds = $TimeoutSeconds }
if ($OutDir) { $p.OutDir = $OutDir }
if ($UnityPath) { $p.UnityPath = $UnityPath }
if ($AllowMismatchedUnity) { $p.AllowMismatchedUnity = $true }
if ($OpenProject) { $p.OpenProject = $true } else { $p.Build = $true; if (-not $NoInstall) { $p.Install = $true } }
& (Join-Path $pipeline "New-QudSpringUI.ps1") @p
exit $LASTEXITCODE
