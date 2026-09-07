<#
.SYNOPSIS
    Shared Unity asset export helpers for AAMT (Elin / Qud).

.DESCRIPTION
    - Writes PNG .meta via Shared/unity_meta.py (no Editor required)
    - Invokes version-matched Unity Editor in batchmode for materials / prefabs / AssetBundles / def import
    - C# sources live under Shared/UnityScripts/ (no embedded here-strings; PS 5.1 safe)
    - Requires UnityVersionResolver.psm1 (strict game-version matching)

.EXAMPLE
    Import-Module (Join-Path $PSScriptRoot "UnityAssetExport.psm1") -Force
    Invoke-AamtUnityImportDefs -ProjectPath $mod -RequiredVersion 2021.3.45f2
#>

$script:ThisShared = $PSScriptRoot
Import-Module (Join-Path $script:ThisShared "UnityVersionResolver.psm1") -Force

function Get-AamtPython {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if ($cmd) { return $cmd.Source }
    return $null
}

function Read-AamtUnityScriptFile {
    param([Parameter(Mandatory)][string]$FileName)
    $path = Join-Path $script:ThisShared (Join-Path "UnityScripts" $FileName)
    if (-not (Test-Path $path)) {
        throw "Missing Unity script: $path"
    }
    return [System.IO.File]::ReadAllText($path)
}

function Write-AamtUtf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Start-AamtUnityProcess {
    param(
        [Parameter(Mandatory)][string]$UnityExe,
        [Parameter(Mandatory)][string]$ProjectPath,
        [Parameter(Mandatory)][string]$ExecuteMethod,
        [Parameter(Mandatory)][string]$LogFile,
        [switch]$NoGraphics
    )
    # Single Arguments string with quoted paths - PS 5.1 safe for spaced paths
    $parts = New-Object System.Collections.Generic.List[string]
    [void]$parts.Add("-batchmode")
    [void]$parts.Add("-quit")
    if ($NoGraphics) { [void]$parts.Add("-nographics") }
    [void]$parts.Add("-projectPath")
    [void]$parts.Add('"' + ($ProjectPath -replace '"', '') + '"')
    [void]$parts.Add("-executeMethod")
    [void]$parts.Add($ExecuteMethod)
    [void]$parts.Add("-logFile")
    [void]$parts.Add('"' + ($LogFile -replace '"', '') + '"')
    $argString = ($parts -join " ")
    return Start-Process -FilePath $UnityExe -ArgumentList $argString -PassThru -WindowStyle Hidden
}

function Write-AamtUnityTextureMeta {
    param(
        [Parameter(Mandatory)][string]$Path,
        [ValidateSet("default", "sprite", "normal", "gui")]
        [string]$Kind = "default",
        [switch]$Overwrite
    )
    $py = Get-AamtPython
    $script = Join-Path $script:ThisShared "unity_meta.py"
    if (-not $py -or -not (Test-Path $script)) {
        Write-Warning "Write-AamtUnityTextureMeta: python or unity_meta.py missing"
        return $false
    }
    if (-not (Test-Path $Path)) {
        Write-Warning "Write-AamtUnityTextureMeta: file not found: $Path"
        return $false
    }
    $pyArgs = @($script, $Path, "--kind", $Kind)
    if ($Overwrite) { $pyArgs += "--overwrite" }
    & $py @pyArgs 2>&1 | Out-Host
    return ($LASTEXITCODE -eq 0 -and (Test-Path ($Path + ".meta")))
}

function Invoke-AamtUnityBatch {
    param(
        [Parameter(Mandatory)][string]$ProjectPath,
        [Parameter(Mandatory)][string]$ExecuteMethod,
        [string]$GameRoot = "",
        [string]$RequiredVersion = "",
        [string]$ManualUnityPath = "",
        [string]$EditorScriptContent = "",
        [string]$EditorScriptName = "AamtAssetGeneratorEditor.cs",
        [int]$TimeoutSeconds = 300,
        [switch]$NoGraphics
    )

    if (-not (Test-Path (Join-Path $ProjectPath "Assets"))) {
        Write-Warning "Invoke-AamtUnityBatch: no Assets folder under $ProjectPath"
        return $false
    }

    $match = $null
    if ($GameRoot) {
        $match = Resolve-UnityEditorForGame -GameRoot $GameRoot -ManualPath $ManualUnityPath
        $RequiredVersion = $match.RequiredVersion
        $unityExe = $match.EditorExe
    } elseif ($RequiredVersion) {
        $match = Find-MatchingUnityEditor -RequiredVersion $RequiredVersion -ManualPath $ManualUnityPath -PassThru
        $unityExe = $match.EditorExe
    } else {
        Write-Warning "Invoke-AamtUnityBatch: provide -GameRoot or -RequiredVersion"
        return $false
    }

    if (-not $unityExe) {
        Write-Host "  [Unity] Skipping batch ($ExecuteMethod) - matching Editor not installed." -ForegroundColor Yellow
        if ($match) { Write-Host "          $($match.InstallHint)" -ForegroundColor Cyan }
        return $false
    }

    if ($EditorScriptContent) {
        $editorDir = Join-Path $ProjectPath "Assets\Editor"
        New-Item -ItemType Directory -Path $editorDir -Force | Out-Null
        $csPath = Join-Path $editorDir $EditorScriptName
        Write-AamtUtf8NoBom -Path $csPath -Content $EditorScriptContent
    }

    $logFile = Join-Path $env:TEMP ("aamt_unity_" + [guid]::NewGuid().ToString("N") + ".log")

    Write-Host "  [Unity] $($match.MatchedVersion) batch: $ExecuteMethod" -ForegroundColor Cyan
    $proc = Start-AamtUnityProcess -UnityExe $unityExe -ProjectPath $ProjectPath -ExecuteMethod $ExecuteMethod -LogFile $logFile -NoGraphics:$NoGraphics
    $ok = $proc.WaitForExit($TimeoutSeconds * 1000)
    if (-not $ok) {
        try { $proc.Kill() } catch { }
        Write-Warning "Invoke-AamtUnityBatch: timed out after ${TimeoutSeconds}s (log: $logFile)"
        return $false
    }
    if ($proc.ExitCode -ne 0) {
        Write-Warning "Invoke-AamtUnityBatch: Unity exit $($proc.ExitCode) (log: $logFile)"
        return $false
    }
    Write-Host "  [Unity] OK ($ExecuteMethod)" -ForegroundColor Green
    return $true
}

function Get-AamtAssetBundleEditorScript {
    return (Read-AamtUnityScriptFile -FileName "AamtAssetBundleBuilder.cs")
}

function Get-AamtMeshPrefabEditorScript {
    param(
        [Parameter(Mandatory)][string]$SystemName,
        [string]$PrefabName = ""
    )
    if (-not $PrefabName) { $PrefabName = "${SystemName}_Prefab" }
    $sys = $SystemName -replace '[^A-Za-z0-9_]', '_'
    $pref = $PrefabName -replace '[^A-Za-z0-9_]', '_'
    $tpl = Read-AamtUnityScriptFile -FileName "AamtMeshPrefabBuilder.cs"
    return $tpl.Replace('__SYS__', $sys).Replace('__PREF__', $pref)
}

function Initialize-AamtUnityProject {
    param(
        [Parameter(Mandatory)][string]$ProjectPath,
        [Parameter(Mandatory)][string]$EditorVersion
    )
    $assets = Join-Path $ProjectPath "Assets"
    $ps = Join-Path $ProjectPath "ProjectSettings"
    $packages = Join-Path $ProjectPath "Packages"
    New-Item -ItemType Directory -Path $assets -Force | Out-Null
    New-Item -ItemType Directory -Path $ps -Force | Out-Null
    New-Item -ItemType Directory -Path $packages -Force | Out-Null

    $versionTxt = Join-Path $ps "ProjectVersion.txt"
    $verContent = "m_EditorVersion: $EditorVersion`r`nm_EditorVersionWithRevision: $EditorVersion (aamt-scaffold)`r`n"
    Write-AamtUtf8NoBom -Path $versionTxt -Content $verContent

    $manifest = Join-Path $packages "manifest.json"
    if (-not (Test-Path $manifest)) {
        Write-AamtUtf8NoBom -Path $manifest -Content '{"dependencies":{}}'
    }

    $psAsset = Join-Path $ps "ProjectSettings.asset"
    if (-not (Test-Path $psAsset)) {
        $lines = @(
            '%YAML 1.1',
            '%TAG !u! tag:unity3d.com,2011:',
            ('--- !u!129 ' + [char]38 + '1'),
            'PlayerSettings:',
            '  m_ObjectHideFlags: 0',
            '  serializedVersion: 24',
            '  productName: AamtSmoke',
            '  companyName: AAMT',
            '  defaultScreenWidth: 1024',
            '  defaultScreenHeight: 768'
        )
        Write-AamtUtf8NoBom -Path $psAsset -Content (($lines -join "`r`n") + "`r`n")
    }
    return $true
}

function Invoke-AamtUnityAssetBundles {
    param(
        [Parameter(Mandatory)][string]$ProjectPath,
        [string]$GameRoot = "",
        [string]$RequiredVersion = "",
        [string]$ManualUnityPath = "",
        [int]$TimeoutSeconds = 600,
        [switch]$EnsureProject
    )
    if ($EnsureProject) {
        $ver = $RequiredVersion
        if (-not $ver -and $GameRoot) {
            $ver = Get-GameUnityVersion -GameRoot $GameRoot
        }
        if ($ver) {
            [void](Initialize-AamtUnityProject -ProjectPath $ProjectPath -EditorVersion $ver)
        }
    }
    return Invoke-AamtUnityBatch `
        -ProjectPath $ProjectPath `
        -ExecuteMethod "AamtAssetBundleBuilder.BuildBundles" `
        -GameRoot $GameRoot `
        -RequiredVersion $RequiredVersion `
        -ManualUnityPath $ManualUnityPath `
        -EditorScriptContent (Get-AamtAssetBundleEditorScript) `
        -EditorScriptName "AamtAssetBundleBuilder.cs" `
        -TimeoutSeconds $TimeoutSeconds `
        -NoGraphics
}

function Invoke-AamtUnityMeshPrefab {
    param(
        [Parameter(Mandatory)][string]$ProjectPath,
        [Parameter(Mandatory)][string]$SystemName,
        [string]$PrefabName = "",
        [string]$GameRoot = "",
        [string]$RequiredVersion = "",
        [string]$ManualUnityPath = "",
        [int]$TimeoutSeconds = 600,
        [switch]$EnsureProject
    )
    if ($EnsureProject) {
        $ver = $RequiredVersion
        if (-not $ver -and $GameRoot) {
            $ver = Get-GameUnityVersion -GameRoot $GameRoot
        }
        if ($ver) {
            [void](Initialize-AamtUnityProject -ProjectPath $ProjectPath -EditorVersion $ver)
        }
    }
    $cs = Get-AamtMeshPrefabEditorScript -SystemName $SystemName -PrefabName $PrefabName
    return Invoke-AamtUnityBatch `
        -ProjectPath $ProjectPath `
        -ExecuteMethod "AamtMeshPrefabBuilder.Build" `
        -GameRoot $GameRoot `
        -RequiredVersion $RequiredVersion `
        -ManualUnityPath $ManualUnityPath `
        -EditorScriptContent $cs `
        -EditorScriptName "AamtMeshPrefabBuilder.cs" `
        -TimeoutSeconds $TimeoutSeconds `
        -NoGraphics
}

function Install-AamtUnityScripts {
    param(
        [Parameter(Mandatory)][string]$ProjectPath
    )
    $src = Join-Path $script:ThisShared "UnityScripts"
    if (-not (Test-Path $src)) {
        Write-Warning "Install-AamtUnityScripts: missing $src"
        return $false
    }
    $runtime = Join-Path $ProjectPath "Assets\Aamt\Runtime"
    $editor = Join-Path $ProjectPath "Assets\Aamt\Editor"
    New-Item -ItemType Directory -Path $runtime, $editor -Force | Out-Null

    foreach ($f in @("AamtGameAssetDef.cs", "AamtDefDatabase.cs")) {
        $from = Join-Path $src $f
        if (Test-Path $from) {
            Copy-Item $from (Join-Path $runtime $f) -Force
        }
    }
    foreach ($f in @("AamtDefImporter.cs", "AamtAssetBundleBuilder.cs")) {
        $from = Join-Path $src $f
        if (Test-Path $from) {
            Copy-Item $from (Join-Path $editor $f) -Force
        }
    }
    Write-Host "  [Unity] Installed AAMT scripts under Assets/Aamt" -ForegroundColor Green
    return $true
}

function Invoke-AamtUnityImportDefs {
    param(
        [Parameter(Mandatory)][string]$ProjectPath,
        [string]$GameRoot = "",
        [string]$RequiredVersion = "",
        [string]$ManualUnityPath = "",
        [int]$TimeoutSeconds = 900,
        [switch]$EnsureProject
    )
    if ($EnsureProject) {
        $ver = $RequiredVersion
        if (-not $ver -and $GameRoot) {
            $ver = Get-GameUnityVersion -GameRoot $GameRoot
        }
        if ($ver) {
            [void](Initialize-AamtUnityProject -ProjectPath $ProjectPath -EditorVersion $ver)
        }
    }
    [void](Install-AamtUnityScripts -ProjectPath $ProjectPath)
    $driver = Read-AamtUnityScriptFile -FileName "AamtDefImportDriver.cs"
    return Invoke-AamtUnityBatch `
        -ProjectPath $ProjectPath `
        -ExecuteMethod "AamtDefImportDriver.Run" `
        -GameRoot $GameRoot `
        -RequiredVersion $RequiredVersion `
        -ManualUnityPath $ManualUnityPath `
        -EditorScriptContent $driver `
        -EditorScriptName "AamtDefImportDriver.cs" `
        -TimeoutSeconds $TimeoutSeconds `
        -NoGraphics
}

Export-ModuleMember -Function `
    Write-AamtUtf8NoBom,
    Start-AamtUnityProcess,
    Write-AamtUnityTextureMeta,
    Invoke-AamtUnityBatch,
    Get-AamtAssetBundleEditorScript,
    Get-AamtMeshPrefabEditorScript,
    Initialize-AamtUnityProject,
    Invoke-AamtUnityAssetBundles,
    Invoke-AamtUnityMeshPrefab,
    Install-AamtUnityScripts,
    Invoke-AamtUnityImportDefs,
    Read-AamtUnityScriptFile
