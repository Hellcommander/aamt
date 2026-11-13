<#
.SYNOPSIS
    Raises D2RMM's 512 MiB D2RLoader package limit; rerun after every D2RMM update (see README.md).
.EXAMPLE
    .\Set-D2rmmLimit.ps1 -Root 'D:\games\Diablo II Resurrected'
.EXAMPLE
    .\Set-D2rmmLimit.ps1 -Root 'D:\games\Diablo II Resurrected' -Check
#>
[CmdletBinding()]
param(
    [string]$Root = $env:D2R_PATH,
    [string[]]$Install,
    [long]$Limit = 4000000000,
    [switch]$Check,
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'
if (-not $Install -and (-not $Root -or -not (Test-Path $Root))) { throw 'Pass -Root (or set D2R_PATH) to a folder that contains the D2RMM install, or -Install.' }
if ($Check -and $Restore) { throw 'Use -Check or -Restore, not both.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'D2rmmLimit.py'), '--limit', $Limit)
if ($Root) { $arguments += @('--root', $Root) }
foreach ($i in $Install) { $arguments += @('--install', $i) }
if ($Check) { $arguments += '--check' }
if ($Restore) { $arguments += '--restore' }
& $python @arguments
exit $LASTEXITCODE
