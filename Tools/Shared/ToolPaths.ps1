# Shared INI path helpers for PowerShell tools.
# Dot-source:  . (Join-Path $PSScriptRoot '..\Shared\ToolPaths.ps1')
# Or from Tools root: . .\Shared\ToolPaths.ps1

function Get-AamtToolsRoot {
    if ($PSScriptRoot -and (Split-Path $PSScriptRoot -Leaf) -eq 'Shared') {
        return (Split-Path $PSScriptRoot -Parent)
    }
    if ($PSScriptRoot) {
        $candidate = Split-Path $PSScriptRoot -Parent
        if (Test-Path (Join-Path $candidate 'Shared')) { return $candidate }
        if (Test-Path (Join-Path $PSScriptRoot 'Shared')) { return $PSScriptRoot }
    }
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-AamtIniPath {
    if ($env:AAMT_TOOLS_INI -and (Test-Path $env:AAMT_TOOLS_INI)) {
        return $env:AAMT_TOOLS_INI
    }
    return (Join-Path (Get-AamtToolsRoot) 'TranscendenceTools.ini')
}

function Get-AamtIniValue {
    param(
        [Parameter(Mandatory = $true)][string]$Key,
        [string]$Default = $null
    )
    $ini = Get-AamtIniPath
    if (-not (Test-Path $ini)) { return $Default }

    $want = $Key.ToLowerInvariant()
    foreach ($line in Get-Content -LiteralPath $ini -ErrorAction SilentlyContinue) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#') -or $t.StartsWith(';') -or $t.StartsWith('[')) { continue }
        if ($t -match '^\s*([^=]+?)\s*=\s*(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim().Trim('"').Trim("'")
            if ($k.ToLowerInvariant() -eq $want -and $v) {
                return [System.Environment]::ExpandEnvironmentVariables($v)
            }
        }
    }
    return $Default
}

function Get-AamtBlenderPath {
    param([string]$Explicit = '')

    if ($Explicit -and (Test-Path $Explicit)) { return $Explicit }
    foreach ($envName in @('BLENDER', 'BLENDER_PATH', 'BLENDER_EXE')) {
        $raw = [Environment]::GetEnvironmentVariable($envName)
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        $raw = [System.Environment]::ExpandEnvironmentVariables($raw.Trim().Trim('"'))
        if (Test-Path $raw) {
            if ((Get-Item $raw).PSIsContainer) {
                $exe = Join-Path $raw 'blender.exe'
                if (Test-Path $exe) { return $exe }
            } else { return $raw }
        }
    }

    $fromIni = Get-AamtIniValue -Key 'BlenderPath'
    if ($fromIni) {
        if (Test-Path $fromIni) {
            if ((Get-Item $fromIni).PSIsContainer) {
                $exe = Join-Path $fromIni 'blender.exe'
                if (Test-Path $exe) { return $exe }
            } else { return $fromIni }
        }
    }

    $roots = Get-AamtIniValue -Key 'BlenderRoots'
    if ($roots) {
        foreach ($root in ($roots -split '[,;]')) {
            $root = $root.Trim()
            if (-not $root -or -not (Test-Path $root)) { continue }
            $hit = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending |
                ForEach-Object { Join-Path $_.FullName 'blender.exe' } |
                Where-Object { Test-Path $_ } |
                Select-Object -First 1
            if ($hit) { return $hit }
        }
    }

    # Last resort: python Shared/tool_paths.py
    $py = Join-Path (Get-AamtToolsRoot) 'Shared\tool_paths.py'
    if (Test-Path $py) {
        try {
            $out = & python $py 2>$null | Select-String '^Blender:\s*(.+)$'
            if ($out) {
                $path = $out.Matches[0].Groups[1].Value.Trim()
                if ($path -and $path -ne 'None' -and (Test-Path $path)) { return $path }
            }
        } catch {}
    }
    return $null
}

function Get-AamtTranscendencePath {
    $fromIni = Get-AamtIniValue -Key 'TranscendencePath'
    if ($fromIni -and (Test-Path $fromIni)) { return $fromIni }
    return $null
}

function Get-AamtPixeloramaPath {
    $candidates = @(
        (Get-AamtIniValue -Key 'PixeloramaExe')
        (Get-AamtIniValue -Key 'PixeloramaRoot')
        $env:AAMT_PIXELORAMA
        $env:PIXELORAMA
        'D:\tools\Orama Interactive\Pixelorama\Pixelorama.exe'
        'D:\tools\Orama Interactive\Pixelorama'
    )
    foreach ($c in $candidates) {
        if (-not $c) { continue }
        if (Test-Path -LiteralPath $c -PathType Leaf) { return $c }
        $exe = Join-Path $c 'Pixelorama.exe'
        if (Test-Path -LiteralPath $exe -PathType Leaf) { return $exe }
    }
    return $null
}

function Get-AamtSDRoot {
    return (Get-AamtIniValue -Key 'SDRoot' -Default 'E:\tools\sd3.5\sd3.5')
}

function Get-AamtSDPython {
    $p = Get-AamtIniValue -Key 'SDPython' -Default 'E:\tools\miniconda3\python.exe'
    if ($p -and (Test-Path $p)) { return $p }
    $p2 = Get-AamtIniValue -Key 'PythonPath'
    if ($p2 -and (Test-Path $p2)) { return $p2 }
    return 'python'
}
