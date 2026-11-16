<#
.SYNOPSIS
    ModOrder: sorts and checks your D2RMM mod list, like LOOT (see README.md, "Mod list sorter").
.EXAMPLE
    .\Sort-D2RMods.ps1                 # report and the sorted order; changes nothing
.EXAMPLE
    .\Sort-D2RMods.ps1 apply           # put the sorted order into D2RMM (the old list is saved first)
.EXAMPLE
    .\Sort-D2RMods.ps1 gui             # the same in a browser window
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][ValidateSet('check', 'apply', 'gui', 'audit', 'restore', 'bestof-rules')][string]$Command = 'check',
    [Parameter(Position = 1)][string]$File,
    [string]$D2rmmPath = $env:D2RMM_PATH,
    [switch]$Restart,
    [switch]$Sorted,
    [switch]$Json
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 22 or later is needed: https://nodejs.org/' }
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
if (-not $D2rmmPath) { try { $D2rmmPath = Resolve-D2RMMPath $null (Resolve-D2RGamePath $null) } catch { } }
$arguments = @((Join-Path $PSScriptRoot 'ModOrder\ModOrder.js'), $Command)
if ($File) { $arguments += $File }
if ($D2rmmPath) { $arguments += @('--d2rmm', $D2rmmPath) }
if ($Restart) { $arguments += '--restart' }
if ($Sorted) { $arguments += '--sorted' }
if ($Json) { $arguments += '--json' }
& node @arguments
exit $LASTEXITCODE
