<#
.SYNOPSIS
    Removes mod IDs that no longer exist from Caves of Qud save metadata, so the
    "One or more mods enabled in this save are not available" prompt stops.

.DESCRIPTION
    The save loader (XRLCore.RestoreModsLoadedAsync) compares each save's
    ModsEnabled list (Primary.json / Checkpoint.json / other *.json next to the
    .sav.gz) against installed mods. Workshop items that were taken down are
    deleted by Steam, so saves keep flagging them.

    This only edits the JSON mod lists. Content those mods put in the world is
    still gone; the game drops it on load.

    Dry run by default. Pass -Apply to write; a zip backup of the whole Saves
    folder is made first.

.EXAMPLE
    .\Remove-MissingModsFromSaves.ps1            # preview
    .\Remove-MissingModsFromSaves.ps1 -Apply     # back up, then edit
#>
[CmdletBinding()]
param(
    [string]$SavesPath = (Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud\Synced\Saves'),

    # Default: the six Workshop mods removed from Steam on 2026-11-14.
    #   3832703055 Bigger Water Containers   3832717057 Relics of the Salt
    #   3832731425 Wayfarer's Lights         3833071990 The Frillborn
    #   3833426760 The Parliament of Owls    3833443361 Kiboko
    [string[]]$ModId = @('3832703055', '3832717057', '3832731425', '3833071990', '3833426760', '3833443361'),

    [switch]$Apply,

    [string]$BackupDir = (Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud\_backups')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $SavesPath)) { throw "Saves folder not found: $SavesPath" }

$idPattern = '^\s*"(' + (($ModId | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')"\s*,?\s*$'
$targets = @()

foreach ($file in Get-ChildItem -LiteralPath $SavesPath -Recurse -Filter *.json -File) {
    $bytes = [IO.File]::ReadAllBytes($file.FullName)
    $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    if ($hasBom) { $text = $text.Substring(1) }
    if ($text -notmatch '"ModsEnabled"\s*:') { continue }

    $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }
    $lines = $text -split '\r?\n'
    $out = New-Object System.Collections.Generic.List[string]
    $inList = $false
    $removed = @()
    foreach ($line in $lines) {
        if (-not $inList -and $line -match '"ModsEnabled"\s*:\s*\[') { $inList = $true; $out.Add($line); continue }
        if ($inList) {
            if ($line -match '^\s*\]') {
                # Drop a trailing comma left on the new last element.
                if ($out.Count -gt 0) { $out[$out.Count - 1] = $out[$out.Count - 1] -replace ',(\s*)$', '$1' }
                $inList = $false
            }
            elseif ($line -match $idPattern) { $removed += $Matches[1]; continue }
        }
        $out.Add($line)
    }
    if ($removed.Count -eq 0) { continue }

    $targets += [pscustomobject]@{
        File    = $file.FullName.Substring($SavesPath.Length).TrimStart('\')
        Removed = ($removed -join ', ')
        Path    = $file.FullName
        Text    = ($out -join $newline)
        Bom     = $hasBom
    }
}

if ($targets.Count -eq 0) { Write-Host 'No save lists any of these mod IDs. Nothing to do.'; return }

$targets | Format-Table File, Removed -AutoSize -Wrap | Out-String -Width 220 | Write-Host
Write-Host "$($targets.Count) file(s) list missing mods."

if (-not $Apply) { Write-Host 'Dry run. Re-run with -Apply to back up and edit.'; return }

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$zip = Join-Path $BackupDir ("Saves_before_modlist_fix_{0:yyyyMMdd_HHmmss}.zip" -f (Get-Date))
Compress-Archive -Path (Join-Path $SavesPath '*') -DestinationPath $zip
Write-Host "Backup: $zip"

foreach ($t in $targets) {
    # Validate before writing so a malformed result never replaces a save file.
    $null = $t.Text | ConvertFrom-Json
    [IO.File]::WriteAllText($t.Path, $t.Text, (New-Object Text.UTF8Encoding($t.Bom)))
}
Write-Host "Edited $($targets.Count) file(s)."
