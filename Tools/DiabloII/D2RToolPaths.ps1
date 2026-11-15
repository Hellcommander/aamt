<#
.SYNOPSIS
    Dot-sourced by the mod converter launchers: finds Python, the game folder and D2RMM's folder.
.DESCRIPTION
    Order for each: the launcher's parameter, an environment variable (D2R_PYTHON, D2R_PATH,
    D2RMM_PATH), what was found or typed in before (%LOCALAPPDATA%\D2RModAssets\paths.json), a
    search (Python on PATH / the py launcher; the game in the Steam and Battle.net uninstall entries;
    D2RMM in and beside the game folder), and last a question in the console. What is found is
    remembered for the next run.
#>

$script:D2RPathsFile = Join-Path $env:LOCALAPPDATA 'D2RModAssets\paths.json'

function Get-D2RSavedPath([string]$Name) {
    if (-not (Test-Path $script:D2RPathsFile)) { return $null }
    try { return (Get-Content $script:D2RPathsFile -Raw | ConvertFrom-Json).$Name } catch { return $null }
}

function Save-D2RPath([string]$Name, [string]$Value) {
    $data = @{}
    if (Test-Path $script:D2RPathsFile) {
        try { (Get-Content $script:D2RPathsFile -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $data[$_.Name] = $_.Value } } catch { }
    }
    if ($data[$Name] -eq $Value) { return }
    $data[$Name] = $Value
    New-Item -ItemType Directory -Force (Split-Path $script:D2RPathsFile) | Out-Null
    $data | ConvertTo-Json | Set-Content $script:D2RPathsFile -Encoding UTF8
}

function Read-D2RFolder([string]$What, [scriptblock]$Valid) {
    for ($i = 0; $i -lt 3; $i++) {
        $answer = (Read-Host "Folder of $What (paste the path, Enter to cancel)").Trim().Trim('"')
        if (-not $answer) { break }
        if (& $Valid $answer) { return $answer }
        Write-Host "  not $What`: $answer" -ForegroundColor Yellow
    }
    return $null
}

function Resolve-D2RPython {
    # the toolkit's own setting, when these tools run from the toolkit
    $ini = Join-Path (Split-Path $PSScriptRoot -Parent) 'TranscendenceTools.ini'
    if (Test-Path $ini) {
        $line = Select-String -Path $ini -Pattern '^PythonPath=' | Select-Object -First 1
        if ($line) { return $line.Line.Split('=', 2)[1].Trim() }
    }
    if ($env:D2R_PYTHON) { return $env:D2R_PYTHON }
    # python.exe in WindowsApps is the Microsoft Store stub, not a Python
    $cmd = Get-Command python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch '\\WindowsApps\\' } | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    $py = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($py) { return $py.Source }
    throw 'Python 3 not found. Install it from https://www.python.org/downloads/windows/ (tick "Add python.exe to PATH"), or set D2R_PYTHON.'
}

function Resolve-D2RGamePath([string]$GamePath) {
    $isGame = { param($p) $p -and (Test-Path (Join-Path $p 'D2R.exe')) }
    $found = @($GamePath, $env:D2R_PATH, (Get-D2RSavedPath 'game')) | Where-Object { & $isGame $_ } | Select-Object -First 1
    if (-not $found) {
        $keys = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
                'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
                'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
        $found = Get-ItemProperty $keys -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -match '^Diablo II: Resurrected' -and (& $isGame $_.InstallLocation) } |
            Select-Object -ExpandProperty InstallLocation -First 1
    }
    if (-not $found) { $found = Read-D2RFolder 'Diablo II: Resurrected (the one with D2R.exe)' $isGame }
    if (-not $found) { throw 'Game folder not found: pass -GamePath (or set D2R_PATH) to the folder that contains D2R.exe.' }
    Save-D2RPath 'game' $found
    return $found
}

function Resolve-D2RMMPath([string]$D2RMM, [string]$GamePath) {
    $isD2RMM = { param($p) $p -and (Test-Path (Join-Path $p 'mods') -PathType Container) -and
        @('D2RMM Custom.exe', 'D2RMM.exe', 'types.d.ts' | Where-Object { Test-Path (Join-Path $p $_) }).Count }
    $found = @($D2RMM, $env:D2RMM_PATH, (Get-D2RSavedPath 'd2rmm')) | Where-Object { & $isD2RMM $_ } | Select-Object -First 1
    if (-not $found -and $GamePath) {
        $near = @($GamePath) + @(Get-ChildItem $GamePath -Directory -ErrorAction SilentlyContinue | ForEach-Object FullName) +
                @(Get-ChildItem (Split-Path $GamePath) -Directory -ErrorAction SilentlyContinue | ForEach-Object FullName)
        $found = $near | Where-Object { & $isD2RMM $_ } | Select-Object -First 1
    }
    if (-not $found) { $found = Read-D2RFolder 'D2RMM (the one with D2RMM.exe and mods)' $isD2RMM }
    if (-not $found) { throw "D2RMM's folder not found: pass -D2RMM (or set D2RMM_PATH) to the folder with D2RMM.exe and mods\." }
    Save-D2RPath 'd2rmm' $found
    return $found
}
