<#
.SYNOPSIS
    Harvest CS0618 obsolete warnings and apply curated CoQ API auto-fixes (no game launch).

.EXAMPLE
    .\Resolve-Cs0618.ps1 -ModFolder "D:\games\Steam\steamapps\workshop\content\333640\1207623704"
.EXAMPLE
    .\Resolve-Cs0618.ps1 -ModFolder "...\UD_FleshGolems" -Apply -NoBackup
.EXAMPLE
    .\Resolve-Cs0618.ps1 -FromLog ".\warnings.txt" -ModFolder "...\SomeMod" -NoCompile
#>
[CmdletBinding()]
param(
    [string]$ModFolder,
    [string]$FromLog,
    [string]$Managed = "D:\games\Steam\steamapps\common\Caves of Qud\CoQ_Data\Managed",
    [switch]$Compile,
    [switch]$NoCompile,
    [switch]$Apply,
    [switch]$NoBackup,
    [string]$Report
)

$ErrorActionPreference = 'Stop'
$cli = Join-Path $PSScriptRoot 'src\ApiMigrator.Cli\ApiMigrator.Cli.csproj'
if (-not (Test-Path $cli)) { throw "CLI project not found: $cli" }

$argsList = @('--project', $cli, '-c', 'Release', '--', 'resolve-cs0618')
if ($ModFolder) { $argsList += @('--mod', $ModFolder) }
if ($FromLog) { $argsList += @('--from-log', $FromLog) }
if ($Managed) { $argsList += @('--managed', $Managed) }
if ($NoCompile) { $argsList += '--no-compile' }
elseif ($Compile) { $argsList += '--compile' }
if ($Apply) { $argsList += '--apply' }
if ($NoBackup) { $argsList += '--no-backup' }
if ($Report) { $argsList += @('--report', $Report) }

dotnet @argsList
