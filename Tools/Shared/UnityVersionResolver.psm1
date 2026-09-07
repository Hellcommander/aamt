<#
.SYNOPSIS
    Strict Unity version detection + Hub editor resolution for AAMT.

.DESCRIPTION
    Detects the Unity version a game binary was built with (from
    *_Data/globalgamemanagers) and finds a matching Editor under the Unity Hub
    install roots (E:\tools\Unity_Editor preferred; Hub secondaryInstallPath wins when set).

    Strict policy: no silent wrong-patch fallback. Letter-only siblings
    (f1 vs f2 for the same X.Y.Z) are accepted when Hub does not ship the
    exact letter. Missing editors return $null with an install hint.

.EXAMPLE
    Import-Module (Join-Path $PSScriptRoot "..\Shared\UnityVersionResolver.psm1") -Force
    $v = Get-GameUnityVersion -GameRoot "E:\SteamLibrary\steamapps\common\Elin"
    $exe = Find-MatchingUnityEditor -RequiredVersion $v
#>

function Get-UnityHubInstallHint {
    param([Parameter(Mandatory)][string]$RequiredVersion)
    $dest = "E:\tools\Unity_Editor"
    $secondaryCfg = Join-Path $env:APPDATA "UnityHub\secondaryInstallPath.json"
    if (Test-Path $secondaryCfg) {
        try {
            $raw = (Get-Content $secondaryCfg -Raw).Trim().Trim('"')
            if ($raw) { $dest = $raw }
        } catch { }
    }
    return "Install Unity $RequiredVersion via Unity Hub into $dest\$RequiredVersion\ (Editor\Unity.exe). Re-run export after install. PNG/.meta generation does not require the Editor."
}

function Get-UnityEditorSearchRoots {
    $roots = New-Object System.Collections.Generic.List[string]
    $secondaryCfg = Join-Path $env:APPDATA "UnityHub\secondaryInstallPath.json"
    if (Test-Path $secondaryCfg) {
        try {
            $raw = (Get-Content $secondaryCfg -Raw).Trim().Trim('"')
            if ($raw -and (Test-Path $raw)) { [void]$roots.Add($raw) }
        } catch { }
    }
    foreach ($r in @(
        "E:\tools\Unity_Editor",
        "H:\tools\Unity_Editor",
        "D:\tools\Unity_Editor",
        "C:\Program Files\Unity\Hub\Editor",
        (Join-Path $env:LOCALAPPDATA "Programs\Unity\Hub\Editor")
    )) {
        if ($r -and (Test-Path $r) -and -not $roots.Contains($r)) {
            [void]$roots.Add($r)
        }
    }
    return ,$roots.ToArray()
}

function Get-GameUnityVersion {
    <#
    .SYNOPSIS
        Read Unity version string from a game install's globalgamemanagers.
    #>
    param(
        [Parameter(Mandatory)][string]$GameRoot
    )
    if (-not (Test-Path $GameRoot)) {
        Write-Warning "Get-GameUnityVersion: game root not found: $GameRoot"
        return $null
    }
    $dataDirs = Get-ChildItem -Path $GameRoot -Directory -Filter "*_Data" -ErrorAction SilentlyContinue |
        Sort-Object { $_.Name.Length }, Name
    foreach ($dir in $dataDirs) {
        $ggm = Join-Path $dir.FullName "globalgamemanagers"
        if (-not (Test-Path $ggm)) { continue }
        try {
            $fs = [System.IO.File]::OpenRead($ggm)
            try {
                $buf = New-Object byte[] 8192
                $n = $fs.Read($buf, 0, $buf.Length)
                $text = [System.Text.Encoding]::ASCII.GetString($buf, 0, $n)
            } finally { $fs.Close() }
            if ($text -match '(\d+\.\d+\.\d+[a-z]\d+)') {
                return $Matches[1]
            }
        } catch {
            Write-Warning "Get-GameUnityVersion: failed reading $ggm : $_"
        }
    }
    Write-Warning "Get-GameUnityVersion: no version found under $GameRoot"
    return $null
}

function Get-InstalledUnityEditors {
    $list = @()
    foreach ($root in Get-UnityEditorSearchRoots) {
        Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Name -like "*-x86_64") { return }
            $ver = $null
            if ($_.Name -match '(\d+\.\d+\.\d+[a-z]\d+)') {
                $ver = $Matches[1]
            } else {
                return
            }
            $exe = Join-Path $_.FullName "Editor\Unity.exe"
            if (-not (Test-Path $exe)) {
                $alt = Join-Path $_.FullName "Unity.exe"
                if (Test-Path $alt) {
                    $exe = $alt
                } else {
                    $nested = Get-ChildItem -Path $_.FullName -Recurse -Filter "Unity.exe" -ErrorAction SilentlyContinue |
                        Where-Object { $_.Directory.Name -eq "Editor" } | Select-Object -First 1
                    if ($nested) { $exe = $nested.FullName } else { return }
                }
            }
            $list += [pscustomobject]@{ Version = $ver; Exe = $exe; Root = $root; Folder = $_.Name }
        }
    }
    # Deduplicate by version (first root wins)
    $seen = @{}
    $unique = @()
    foreach ($e in $list) {
        if ($seen.ContainsKey($e.Version)) { continue }
        $seen[$e.Version] = $true
        $unique += $e
    }
    return $unique
}

function Test-UnitySameXYZ {
    param([string]$A, [string]$B)
    if ($A -notmatch '^(\d+)\.(\d+)\.(\d+)([a-z])(\d+)$') { return $false }
    $ax, $ay, $az = $Matches[1], $Matches[2], $Matches[3]
    if ($B -notmatch '^(\d+)\.(\d+)\.(\d+)([a-z])(\d+)$') { return $false }
    return ($ax -eq $Matches[1] -and $ay -eq $Matches[2] -and $az -eq $Matches[3])
}

function Get-UnityVersionFromEditorPath {
    <#
    .SYNOPSIS
        Infer Unity version from an Editor\Unity.exe path (folder name).
    #>
    param([Parameter(Mandatory)][string]$EditorExe)
    $p = $EditorExe
    for ($i = 0; $i -lt 6; $i++) {
        $name = Split-Path $p -Leaf
        if ($name -match '(\d+\.\d+\.\d+[a-z]\d+)') {
            return $Matches[1]
        }
        $parent = Split-Path $p -Parent
        if (-not $parent -or $parent -eq $p) { break }
        $p = $parent
    }
    return $null
}

function Find-MatchingUnityEditor {
    <#
    .SYNOPSIS
        Resolve Unity.exe for a required game version (strict).
    .OUTPUTS
        Unity.exe path, or $null if missing (prints install hint).
    .NOTES
        Also sets script-scoped last-match info via return of PSCustomObject
        when -PassThru is set.
    #>
    param(
        [Parameter(Mandatory)][string]$RequiredVersion,
        [string]$ManualPath = "",
        [switch]$PassThru,
        [switch]$Quiet,
        [switch]$AllowMismatchedManual
    )

    $hint = Get-UnityHubInstallHint -RequiredVersion $RequiredVersion

    if ($ManualPath) {
        $candidate = $ManualPath
        if ((Test-Path $ManualPath) -and (Get-Item $ManualPath).PSIsContainer) {
            $candidate = Join-Path $ManualPath "Editor\Unity.exe"
        }
        if (Test-Path $candidate) {
            $manualVer = Get-UnityVersionFromEditorPath -EditorExe $candidate
            $exact = ($manualVer -and ($manualVer -eq $RequiredVersion))
            $sib = ($manualVer -and (Test-UnitySameXYZ $manualVer $RequiredVersion))
            if (-not $exact -and -not $sib -and -not $AllowMismatchedManual) {
                if (-not $Quiet) {
                    Write-Warning "Manual Unity path version '$manualVer' does not match required '$RequiredVersion' - refused. Use -AllowMismatchedManual to override."
                    Write-Host "          $hint" -ForegroundColor Cyan
                }
                if ($PassThru) {
                    return [pscustomobject]@{
                        RequiredVersion = $RequiredVersion
                        EditorExe = $null
                        MatchedVersion = $manualVer
                        Exact = $false
                        LetterSibling = $false
                        InstallHint = $hint
                    }
                }
                return $null
            }
            if (-not $Quiet -and $sib -and -not $exact) {
                Write-Host "  [Unity] Manual path is letter-sibling: need $RequiredVersion, using $manualVer" -ForegroundColor Yellow
            }
            if ($PassThru) {
                return [pscustomobject]@{
                    RequiredVersion = $RequiredVersion
                    EditorExe = $candidate
                    MatchedVersion = $(if ($manualVer) { $manualVer } else { $RequiredVersion })
                    Exact = [bool]$exact
                    LetterSibling = [bool]($sib -and -not $exact)
                    InstallHint = $hint
                }
            }
            return $candidate
        }
        if (-not $Quiet) {
            Write-Warning "Manual Unity path not found: $ManualPath"
        }
    }

    $installed = @(Get-InstalledUnityEditors)

    # Exact match
    $exact = $installed | Where-Object { $_.Version -eq $RequiredVersion } | Select-Object -First 1
    if ($exact) {
        if (-not $Quiet) {
            Write-Host "  [Unity] Exact match: $($exact.Version) -> $($exact.Exe)" -ForegroundColor Green
        }
        if ($PassThru) {
            return [pscustomobject]@{
                RequiredVersion = $RequiredVersion
                EditorExe = $exact.Exe
                MatchedVersion = $exact.Version
                Exact = $true
                LetterSibling = $false
                InstallHint = $hint
            }
        }
        return $exact.Exe
    }

    # Letter-sibling same X.Y.Z
    $sib = $installed | Where-Object { Test-UnitySameXYZ $_.Version $RequiredVersion } |
        Sort-Object Version | Select-Object -First 1
    if ($sib) {
        if (-not $Quiet) {
            Write-Host "  [Unity] Letter-sibling match: need $RequiredVersion, using $($sib.Version)" -ForegroundColor Yellow
            Write-Host "          (Hub often ships only one letter for X.Y.Z)" -ForegroundColor Gray
        }
        if ($PassThru) {
            return [pscustomobject]@{
                RequiredVersion = $RequiredVersion
                EditorExe = $sib.Exe
                MatchedVersion = $sib.Version
                Exact = $false
                LetterSibling = $true
                InstallHint = $hint
            }
        }
        return $sib.Exe
    }

    if (-not $Quiet) {
        Write-Host "  [Unity] No matching Editor for $RequiredVersion" -ForegroundColor Yellow
        Write-Host "          $hint" -ForegroundColor Cyan
        if ($installed.Count -gt 0) {
            $have = ($installed | ForEach-Object { $_.Version }) -join ", "
            Write-Host "          Installed: $have" -ForegroundColor Gray
        }
    }
    if ($PassThru) {
        return [pscustomobject]@{
            RequiredVersion = $RequiredVersion
            EditorExe = $null
            MatchedVersion = $null
            Exact = $false
            LetterSibling = $false
            InstallHint = $hint
        }
    }
    return $null
}

function Resolve-UnityEditorForGame {
    <#
    .SYNOPSIS
        Detect game Unity version then resolve matching Hub Editor.
    #>
    param(
        [Parameter(Mandatory)][string]$GameRoot,
        [string]$ManualPath = "",
        [switch]$Quiet
    )
    $ver = Get-GameUnityVersion -GameRoot $GameRoot
    if (-not $ver) {
        return [pscustomobject]@{
            GameRoot = $GameRoot
            RequiredVersion = $null
            EditorExe = $null
            MatchedVersion = $null
            Exact = $false
            LetterSibling = $false
            InstallHint = ('Could not detect Unity version under {0} (expected *_Data/globalgamemanagers).' -f $GameRoot)
        }
    }
    $m = Find-MatchingUnityEditor -RequiredVersion $ver -ManualPath $ManualPath -PassThru -Quiet:$Quiet
    return [pscustomobject]@{
        GameRoot = $GameRoot
        RequiredVersion = $ver
        EditorExe = $m.EditorExe
        MatchedVersion = $m.MatchedVersion
        Exact = $m.Exact
        LetterSibling = $m.LetterSibling
        InstallHint = $m.InstallHint
    }
}

Export-ModuleMember -Function `
    Get-UnityEditorSearchRoots,
    Get-UnityHubInstallHint,
    Get-GameUnityVersion,
    Get-InstalledUnityEditors,
    Test-UnitySameXYZ,
    Get-UnityVersionFromEditorPath,
    Find-MatchingUnityEditor,
    Resolve-UnityEditorForGame
