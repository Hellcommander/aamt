# Shared CoQ / ApiMigrator path helpers. Dot-source from toolkit scripts.
# Resolves local Mods even when this toolkit is not a sibling of CavesOfQud\_tools.

function Get-CoqLocalLowRoot {
    Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud'
}

function Get-CoqModsRoot {
    param([string]$ToolsRoot)

    if ($env:COQ_MODS_ROOT -and (Test-Path -LiteralPath $env:COQ_MODS_ROOT)) {
        return [System.IO.Path]::GetFullPath($env:COQ_MODS_ROOT)
    }

    if ($ToolsRoot) {
        $sibling = Join-Path (Split-Path -Parent $ToolsRoot) 'Mods'
        if (Test-Path -LiteralPath $sibling) { return $sibling }
    }

    $localLow = Join-Path (Get-CoqLocalLowRoot) 'Mods'
    if (Test-Path -LiteralPath $localLow) { return $localLow }
    return $localLow
}

function Get-CoqSteamLibrary {
    # Autodetect: Steam registry → libraryfolders.vdf → common fallbacks.
    # Pick the library whose CoQ Assembly-CSharp.dll is newest (prefer ones that also host workshop/333640).
    $roots = [System.Collections.Generic.List[string]]::new()
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

    function Add-Root([string]$r) {
        if ([string]::IsNullOrWhiteSpace($r)) { return }
        $full = $r.Trim().TrimEnd('\', '/')
        try { $full = [System.IO.Path]::GetFullPath($full).TrimEnd('\', '/') } catch { }
        if ($seen.Add($full)) { [void]$roots.Add($full) }
    }

    foreach ($regPath in @(
        'HKCU:\Software\Valve\Steam'
        'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam'
        'HKLM:\SOFTWARE\Valve\Steam'
    )) {
        try {
            $p = (Get-ItemProperty -LiteralPath $regPath -ErrorAction Stop).SteamPath
            if (-not $p) { $p = (Get-ItemProperty -LiteralPath $regPath -ErrorAction Stop).InstallPath }
            if ($p) { Add-Root ($p -replace '/', '\') }
        } catch { }
    }

    function Add-VdfLibraries([string]$steamRoot) {
        foreach ($vdf in @(
            (Join-Path $steamRoot 'steamapps\libraryfolders.vdf')
            (Join-Path $steamRoot 'config\libraryfolders.vdf')
        )) {
            if (-not (Test-Path -LiteralPath $vdf)) { continue }
            try {
                $text = Get-Content -Raw -LiteralPath $vdf -ErrorAction Stop
                [regex]::Matches($text, '"path"\s+"([^"]+)"') | ForEach-Object {
                    Add-Root ($_.Groups[1].Value -replace '\\\\', '\')
                }
            } catch { }
        }
    }

    foreach ($r in @($roots.ToArray())) { Add-VdfLibraries $r }

    foreach ($r in @(
        'D:\games\Steam'
        'E:\SteamLibrary'
        'F:\SteamLibrary'
        'G:\SteamLibrary'
        'H:\SteamLibrary'
        "${env:ProgramFiles(x86)}\Steam"
        "$env:ProgramFiles\Steam"
    )) { Add-Root $r }

    foreach ($r in @($roots.ToArray())) { Add-VdfLibraries $r }

    $withGame = @()
    foreach ($r in $roots) {
        $dll = Join-Path $r 'steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll'
        if (-not (Test-Path -LiteralPath $dll)) { continue }
        $ws = Join-Path $r 'steamapps\workshop\content\333640'
        $write = (Get-Item -LiteralPath $dll).LastWriteTimeUtc
        $withGame += [pscustomobject]@{
            Root = $r
            DllWrite = $write
            HasWorkshop = [bool](Test-Path -LiteralPath $ws)
        }
    }

    if ($withGame.Count -gt 0) {
        $pool = @($withGame | Where-Object { $_.HasWorkshop })
        if ($pool.Count -eq 0) { $pool = $withGame }
        return ($pool | Sort-Object DllWrite -Descending | Select-Object -First 1).Root
    }

    return 'D:\games\Steam'
}
