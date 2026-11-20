<#
.SYNOPSIS
    Shared part of the drag-and-drop batch files in this folder: takes the files or folders
    dropped on a .bat and runs the matching toolkit tool with them (see README.md, "Drag and drop").
.DESCRIPTION
    Each .bat here calls:  _drop.ps1 <action> <dropped paths...>
    Paths and tools come from ..\D2RToolPaths.ps1 (game folder, D2RMM folder, Python), the same
    way the other launchers find them. A .bat started without anything dropped on it says what
    to drop.
#>
param(
    [Parameter(Mandatory, Position = 0)][string]$Action,
    [Parameter(Position = 1, ValueFromRemainingArguments)][string[]]$Paths
)
$ErrorActionPreference = 'Stop'
$Tools = Split-Path $PSScriptRoot -Parent
. (Join-Path $Tools 'D2RToolPaths.ps1')

$help = @{
    'test'            = 'Drop one or more D2RMM mod folders: they run together, in the order dropped, in the mod test harness.'
    'merge'           = 'Drop D2RMM mod folders that copy whole tables or string files: they are converted to merge them row by row.'
    'convert-data'    = 'Drop a data mod (a <Name>.mpq folder, a mod folder, a packed .mpq, .zip, .7z or .rar): it becomes a D2RMM mod that patches tables.'
    'update-converted'= 'Drop converted mod folders (from D2RMM''s mods folder): each is converted again from its saved download.'
    'install'         = 'Drop a mod download (.zip, .7z, .rar or folder) that already is a D2RMM mod: it is installed into D2RMM''s mods folder.'
    'model-index'     = 'Drop D2RMM mod folders that add HD models: their model index is rebuilt.'
    'extract-mpq'     = 'Drop .mpq archives: each is extracted next to itself (<name>-extracted).'
    'check-list'      = 'Drop a saved mod list (.json, e.g. from modorder-backups): ModOrder sorts and checks it, nothing is changed.'
    'restore-list'    = 'Drop a saved mod list (.json from modorder-backups): it is put back into D2RMM.'
    'bot-test'        = 'Drop a bot script (.txt): the game starts with the bot harness and runs it.'
    'hdmatch'         = 'Drop a merged mod data folder (a data\ folder with global\ and hd\, e.g. ModHarness --out): HD Art Match is rebuilt from it.'
}
if (-not $help.ContainsKey($Action)) { throw "unknown action $Action" }
$Paths = @($Paths | Where-Object { $_ } | ForEach-Object { $_.Trim('"') })
if (-not $Paths.Count) {
    Write-Host $help[$Action]
    Write-Host 'Nothing was dropped on this file.' -ForegroundColor Yellow
    exit 1
}
foreach ($p in $Paths) { if (-not (Test-Path -LiteralPath $p)) { throw "not found: $p" } }

function Need-Folder([string]$p, [string]$what) {
    if (-not (Test-Path -LiteralPath $p -PathType Container)) { throw "$p is not a folder ($what expected)" }
}
function Need-ModFolder([string]$p) {
    Need-Folder $p 'a D2RMM mod folder'
    if (-not (Test-Path -LiteralPath (Join-Path $p 'mod.json'))) { throw "$p is not a D2RMM mod (no mod.json)" }
}
function Run([string]$script, [hashtable]$named, [object[]]$positional = @()) {
    & (Join-Path $Tools $script) @positional @named
    if ($LASTEXITCODE) { $script:failed = $LASTEXITCODE }
}
$failed = 0
function Game { [string](Resolve-D2RGamePath $null | Select-Object -Last 1) }
function D2rmmFolder([string]$game) { [string](Resolve-D2RMMPath $null $game | Select-Object -Last 1) }
function Python { [string](Resolve-D2RPython | Select-Object -Last 1) }

switch ($Action) {
    'test' {
        $Paths | ForEach-Object { Need-ModFolder $_ }
        Run 'Test-D2RMod.ps1' @{ Mod = $Paths; GamePath = (Game); KeepGoing = $true }
    }
    'merge' {
        $Paths | ForEach-Object { Need-ModFolder $_ }
        Run 'Convert-D2RReplaceMod.ps1' @{ Mod = $Paths }
    }
    'convert-data' {
        $game = Game
        $d2rmm = D2rmmFolder $game
        $mods = (Resolve-Path (Join-Path $d2rmm 'mods')).Path
        foreach ($p in $Paths) {
            $full = (Resolve-Path -LiteralPath $p).Path
            if ($full.StartsWith($mods + '\', [StringComparison]::OrdinalIgnoreCase)) {
                Run 'Convert-D2RDataMod.ps1' @{ GamePath = $game; Mod = $full; Check = $true }
            } else {
                $name = [IO.Path]::GetFileNameWithoutExtension($full.TrimEnd('\'))
                $name = ($name -replace '\.mpq$', '' -replace '[^A-Za-z0-9_-]+', '')
                $answer = Read-Host "D2RMM folder name for it [$name]"
                if ($answer.Trim()) { $name = $answer.Trim() }
                Run 'Convert-D2RDataMod.ps1' @{ GamePath = $game; Source = $full; Mod = $name }
            }
        }
    }
    'update-converted' {
        $Paths | ForEach-Object { Need-ModFolder $_ }
        Run 'Update-D2RConvertedMod.ps1' @{ Mod = @($Paths | ForEach-Object { Split-Path $_ -Leaf }) }
    }
    'install' {
        foreach ($p in $Paths) { Run 'Update-D2RNativeMod.ps1' @{ Install = $p } }
    }
    'model-index' {
        foreach ($p in $Paths) { Need-ModFolder $p; Run 'Update-D2RModelIndex.ps1' @{ Mod = $p } }
    }
    'extract-mpq' {
        $python = Python
        foreach ($p in $Paths) {
            $full = (Resolve-Path -LiteralPath $p).Path
            $out = (Join-Path (Split-Path $full -Parent) ([IO.Path]::GetFileNameWithoutExtension($full) + '-extracted'))
            Write-Host "extracting $full -> $out"
            & $python (Join-Path $Tools 'MpqArchive.py') extract $full $out
            if ($LASTEXITCODE) { $failed = $LASTEXITCODE }
        }
    }
    'check-list' {
        foreach ($p in $Paths) {
            & node (Join-Path $Tools 'ModOrder\ModOrder.js') check --from $p
            if ($LASTEXITCODE) { $failed = $LASTEXITCODE }
        }
    }
    'restore-list' {
        if ($Paths.Count -ne 1) { throw 'drop one saved list' }
        Write-Host "This replaces the mod list open in D2RMM with $($Paths[0])."
        if ((Read-Host 'Type yes to go on') -ne 'yes') { Write-Host 'Nothing changed.'; exit 1 }
        Run 'Sort-D2RMods.ps1' @{ Command = 'restore'; File = $Paths[0] }
    }
    'bot-test' {
        if ($Paths.Count -ne 1) { throw 'drop one bot script' }
        Run 'Invoke-D2RBotTest.ps1' @{ Root = (Game); Script = $Paths[0] }
    }
    'hdmatch' {
        if ($Paths.Count -ne 1) { throw 'drop one merged data folder' }
        Need-Folder $Paths[0] 'a merged data folder'
        $game = Game
        $d2rmm = D2rmmFolder $game
        $python = Python
        & $python (Join-Path $Tools 'HdMatch.py') build --game $game --data $Paths[0] --out (Join-Path $d2rmm 'mods\HdArtMatch')
        if ($LASTEXITCODE) { $failed = $LASTEXITCODE }
    }
}
exit $failed
