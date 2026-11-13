<#
.SYNOPSIS
    Lists the game checks that failed in the last D2RLoader session (see README.md).
.EXAMPLE
    .\Get-D2RLoaderLog.ps1 -Root 'D:\games\Diablo II Resurrected'
.EXAMPLE
    .\Get-D2RLoaderLog.ps1 -Root 'D:\games\Diablo II Resurrected' -All -Plugins
#>
[CmdletBinding()]
param(
    [string]$Root = $env:D2R_PATH,
    [switch]$All,
    [switch]$Plugins
)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not (Test-Path $Root)) { throw 'Pass -Root (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'LoaderLog.py'), '--game', $Root)
if ($All) { $arguments += '--all' }
if ($Plugins) { $arguments += '--plugins' }
& $python @arguments
exit $LASTEXITCODE
