<#
.SYNOPSIS
    Opens the particle effect editor in the browser (see README.md).
.EXAMPLE
    .\Start-D2REffectEditor.ps1 -Root 'D:\games\Diablo II Resurrected' -OutDir 'D:\mods\MyMod'
#>
[CmdletBinding()]
param(
    [string]$Root = $env:D2R_PATH,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Port = 8765,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not (Test-Path $Root)) { throw 'Pass -Root (or set D2R_PATH) to the folder that contains D2R.exe.' }

$python = 'python'
$ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
if (Test-Path $ini) {
    $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
    if ($line) { $python = $line.Line.Split('=', 2)[1].Trim() }
}

$arguments = @((Join-Path $PSScriptRoot 'EffectEditor.py'), '--game', $Root, '--out', $OutDir, '--port', $Port)
if ($NoBrowser) { $arguments += '--no-browser' }
& $python @arguments
exit $LASTEXITCODE
