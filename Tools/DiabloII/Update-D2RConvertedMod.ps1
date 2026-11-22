<#
.SYNOPSIS
    Updates data mods converted into D2RMM mods (ConvertDataMod.py) from a new download, with the
    settings each was converted with. Same as Update in Start-D2RModConverter, without the page.
.DESCRIPTION
    - A normal conversion (Reimagined, Rebirth...): the new mod files go in place, the old ones
      stay in <mod>\d2rmm\previous until the new conversion passed its check, then ConvertDataMod.py
      runs again. Plugins and patches in the download's other d2rloader folder (the one beside mods\
      in a D2RLoader setup) become D2RMM packages in <D2RMM>\d2rloader, unless installed already.
    - A mod made from compiled tables (<mod>\d2rmm\update.json, method merge-compiled: Rebirth): the
      new Rebirth.mpq is extracted and merged onto the game's tables (MergeCompiledMod.py) first.
    -Source can be a folder, a .zip/.7z/.rar download or a packed .mpq. Without it, the download the
    mod was converted from (d2rmm\convert.json) is used, which also redoes the conversion after a
    game patch.
    Row matching (-MatchTrim, -Duplicates, -Deleted): left out, each mod keeps what it was converted
    with (or the defaults on, content, disable when it was converted before these existed).
    Load order (-Conflicts, -Files, -BaseRows): the defaults of the mod's Load order settings in
    D2RMM; left out, as converted (else mod, overwrite, stubs). Rows keep/rebuild is a setting there
    too. -BaseRows stubs gives missiles.txt rows that only the main table has a stub row in
    global\excel\base, so both tables number their rows the same (HD missile effects go by row).
.EXAMPLE
    .\Update-D2RConvertedMod.ps1 -Mod Rebirth -Conflicts earlier -Files keep
.EXAMPLE
    .\Update-D2RConvertedMod.ps1 -Mod Reimagined, Rebirth
.EXAMPLE
    .\Update-D2RConvertedMod.ps1 -Mod Reimagined -Duplicates order -Deleted leave
.EXAMPLE
    .\Update-D2RConvertedMod.ps1 -Mod Rebirth -Source "$env:USERPROFILE\Downloads\Rebirth-Re.zip"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$Mod,
    [string]$Source,
    [string]$GamePath = $env:D2R_PATH,
    [string]$D2RMM,
    [Nullable[bool]]$MatchTrim,
    [ValidateSet('content', 'order')][string]$Duplicates,
    [ValidateSet('disable', 'leave')][string]$Deleted,
    [ValidateSet('mod', 'earlier')][string]$Conflicts,
    [ValidateSet('overwrite', 'keep')][string]$Files,
    [ValidateSet('stubs', 'leave')][string]$BaseRows
)
$ErrorActionPreference = 'Stop'
if ($Source -and $Mod.Count -gt 1) { throw '-Source goes with one -Mod.' }
. (Join-Path $PSScriptRoot 'D2RToolPaths.ps1')
$GamePath = Resolve-D2RGamePath $GamePath
$D2RMM = Resolve-D2RMMPath $D2RMM $GamePath
$python = Resolve-D2RPython

$arguments = @((Join-Path $PSScriptRoot 'ModConverter.py'), '--game', $GamePath, '--d2rmm', $D2RMM)
foreach ($m in $Mod) { $arguments += @('--update', $m) }
if ($Source) { $arguments += @('--source', $Source) }
if ($null -ne $MatchTrim) { $arguments += $(if ($MatchTrim) { '--match-trim' } else { '--no-match-trim' }) }
if ($Duplicates) { $arguments += @('--duplicates', $Duplicates) }
if ($Deleted) { $arguments += @('--deleted', $Deleted) }
if ($Conflicts) { $arguments += @('--conflicts', $Conflicts) }
if ($Files) { $arguments += @('--files', $Files) }
if ($BaseRows) { $arguments += @('--base-rows', $BaseRows) }
& $python @arguments
exit $LASTEXITCODE
