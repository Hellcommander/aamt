#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Export Magi-Tech Starbound sheets from Pixelorama .pxo (Shared pixels stage).

.DESCRIPTION
    Headless Godot CLI via Shared/pixelorama_client.py. Does not invent frames;
    author idle/charge/fire/cooldown in the .pxo first.

    Projects: <mod>/assets/magitech/pixelorama/<id>.pxo
#>
[CmdletBinding()]
param(
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    [int]$TileSize = 64,
    [int]$Limit = 0,
    [string[]]$AssetIds = @(),
    [switch]$SkipExisting,
    [switch]$List,
    [switch]$Status,
    [string]$OpenGui = "",
    [switch]$See
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = "E:\tools\miniconda3\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$producer = Join-Path $scriptDir "produce_pixelorama_sheets.py"
if (-not (Test-Path $producer)) { throw "Missing $producer" }

$argsList = @($producer)
if ($Status) {
    $argsList += "--status"
} elseif ($List) {
    $argsList += @("--list", "--mod-path", $ModPath)
} elseif ($See) {
    $argsList += "--see"
} elseif ($OpenGui -ne "") {
    $argsList += @("--open-gui", $OpenGui)
} else {
    $argsList += @("--mod-path", $ModPath, "--tile", "$TileSize")
    if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }
    if ($AssetIds.Count -gt 0) { $argsList += @("--ids", ($AssetIds -join ",")) }
    if ($SkipExisting) { $argsList += "--skip-existing" }
}

& $py @argsList
exit $LASTEXITCODE
