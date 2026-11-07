#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build a folder of Qud Shader Library .shader files into a per-platform asset bundle with Unity.

.DESCRIPTION
    Stages a throwaway Unity project (version matched to the game's own Unity build via Shared/UnityVersionResolver,
    6000.0.77f1 today), copies in the library's ShaderKit (QudFX.cginc, BuildQudFX.cs) and your shaders, and runs
    Unity in batch mode:

        Unity.exe -batchmode -nographics -quit -projectPath <project> -executeMethod BuildQudFX.Build
                  -out <OutDir> -bundle <Bundle> -shaders Assets/QudFX/<Bundle>

    Output: <OutDir>\windows\<Bundle>_windows (osx/linux too when those build modules are installed). Stray
    .manifest files are removed. Shader compile errors from the Unity log are printed and fail the build.

    Works for any ShaderKit-style shader, not only the particle generator's output.

.PARAMETER ShaderDir
    Folder with the .shader files (for example <out>\shaders from qud_particle_shader.py generate).

.PARAMETER Bundle
    Bundle name, lower case: the file becomes <Bundle>_windows and ShaderEffects.xml loads it with <bundle Name="<Bundle>" />.

.PARAMETER OutDir
    Where the Bundles tree goes. Default: <ShaderDir>\..\Bundles.

.PARAMETER ProjectDir
    The staging Unity project. Default: Tools\Output\QudShaderForge\_unity\<Bundle>. Reused between runs (faster imports).

.PARAMETER ShaderLibraryPath
    The Qud Shader Library mod folder (holds ShaderKit\). Default: QUD_SHADER_LIBRARY, settings.json shaderLibraryPath,
    then the Steam workshop item 3822020203 next to the game.

.PARAMETER UnityPath
    Manual Unity.exe (or editor folder). Must match the game's Unity version unless -AllowMismatchedUnity.

.EXAMPLE
    .\Build-QudShaderBundle.ps1 -ShaderDir "..\..\Output\QudShaderForge\bm_fx\shaders" -Bundle bm_fx
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ShaderDir,
    [Parameter(Mandatory = $true)][string]$Bundle,
    [string]$OutDir = "",
    [string]$ProjectDir = "",
    [string]$ShaderLibraryPath = "",
    [string]$UnityPath = "",
    [switch]$AllowMismatchedUnity,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent (Split-Path -Parent $here)
$shared = Join-Path $toolsRoot "Shared"
Import-Module (Join-Path $shared "UnityVersionResolver.psm1") -Force
Import-Module (Join-Path $shared "UnityAssetExport.psm1") -Force
. (Join-Path (Split-Path -Parent $here) "GetQudSettings.ps1")

function Write-Log {
    param([string]$Message, [ValidateSet("Info", "Warning", "Error", "Success")][string]$Level = "Info")
    $color = @{ Info = "Gray"; Warning = "Yellow"; Error = "Red"; Success = "Green" }[$Level]
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

if ($Bundle -cne $Bundle.ToLowerInvariant() -or $Bundle -notmatch '^[a-z0-9_]+$') {
    throw "Bundle must be lower-case letters, digits and _ (got '$Bundle')"
}
$ShaderDir = (Resolve-Path $ShaderDir).Path
$shaders = Get-ChildItem -Path $ShaderDir -Filter *.shader -File
if ($shaders.Count -eq 0) { throw "No .shader files under $ShaderDir" }
if (-not $OutDir) { $OutDir = Join-Path (Split-Path -Parent $ShaderDir) "Bundles" }
if (-not $ProjectDir) { $ProjectDir = Join-Path $toolsRoot "Output\QudShaderForge\_unity\$Bundle" }

# --- the library's ShaderKit -------------------------------------------------------------------------------------
$settings = Get-QudSettings
$libCandidates = @()
if ($ShaderLibraryPath) { $libCandidates += $ShaderLibraryPath }
if ($env:QUD_SHADER_LIBRARY) { $libCandidates += $env:QUD_SHADER_LIBRARY }
try {
    $raw = [System.IO.File]::ReadAllText((Join-Path (Split-Path -Parent $here) "settings.json"))
    $j = $raw.TrimStart([char]0xFEFF) | ConvertFrom-Json
    if ($j.shaderLibraryPath) { $libCandidates += [string]$j.shaderLibraryPath }
} catch { }
if ($settings -and $settings.GameRoot) {
    $libCandidates += (Join-Path (Split-Path -Parent (Split-Path -Parent $settings.GameRoot)) "workshop\content\333640\3822020203")
}
$libCandidates += "D:\games\Steam\steamapps\workshop\content\333640\3822020203"
$libCandidates += (Join-Path $env:USERPROFILE "AppData\LocalLow\Freehold Games\CavesOfQud\Mods\QudShaderLibrary")
$library = $null
foreach ($c in $libCandidates) {
    if ($c -and (Test-Path (Join-Path $c "ShaderKit\QudFX.cginc"))) { $library = $c; break }
}
if (-not $library) { throw "Qud Shader Library not found (ShaderKit\QudFX.cginc). Set QUD_SHADER_LIBRARY or settings.json shaderLibraryPath." }
Write-Log "Qud Shader Library: $library"

# --- Unity editor matching the game -----------------------------------------------------------------------------
$requiredVersion = $null
if ($settings -and $settings.UnityVersion) { $requiredVersion = $settings.UnityVersion }
if (-not $requiredVersion) { $requiredVersion = "6000.0.77f1" }
$match = Find-MatchingUnityEditor -RequiredVersion $requiredVersion -ManualPath $UnityPath -PassThru -AllowMismatchedManual:$AllowMismatchedUnity
if (-not $match -or -not $match.EditorExe) {
    Write-Log "No Unity $requiredVersion editor found. $($match.InstallHint)" -Level Error
    Write-Log "Shaders are staged under $ProjectDir; install the editor and rerun." -Level Warning
    exit 3
}
$unityExe = $match.EditorExe
Write-Log "Unity $($match.MatchedVersion): $unityExe"

# --- stage the project ------------------------------------------------------------------------------------------
Initialize-AamtUnityProject -ProjectPath $ProjectDir -EditorVersion $match.MatchedVersion | Out-Null
# The built-in AssetBundle module must be enabled in the staging project. Without it Unity still writes the bundle
# file but leaves out its AssetBundle object, and the game's AssetBundle.LoadFromFile returns null with "not
# compatible with this newer version of the Unity runtime" (found 2026-11-04: every Oct 29 FX bundle).
$manifestPath = Join-Path $ProjectDir "Packages\manifest.json"
$deps = [ordered]@{}
if (Test-Path $manifestPath) {
    try {
        $parsed = (Get-Content $manifestPath -Raw) | ConvertFrom-Json
        if ($parsed.dependencies) { $parsed.dependencies.PSObject.Properties | ForEach-Object { $deps[$_.Name] = $_.Value } }
    } catch { Write-Log "Packages/manifest.json unreadable, rewriting it" -Level Warning }
}
if (-not $deps.Contains("com.unity.modules.assetbundle")) {
    $deps["com.unity.modules.assetbundle"] = "1.0.0"
    $json = @{ dependencies = $deps } | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding $false))
    Write-Log "Packages/manifest.json: enabled com.unity.modules.assetbundle"
}
$qudfx = Join-Path $ProjectDir "Assets\QudFX"
$shaderFolder = Join-Path $qudfx $Bundle
$editorDir = Join-Path $ProjectDir "Assets\Editor"
New-Item -ItemType Directory -Path $shaderFolder, $editorDir -Force | Out-Null
Copy-Item (Join-Path $library "ShaderKit\QudFX.cginc") (Join-Path $qudfx "QudFX.cginc") -Force
Copy-Item (Join-Path $library "ShaderKit\BuildQudFX.cs.txt") (Join-Path $editorDir "BuildQudFX.cs") -Force
Get-ChildItem -Path $shaderFolder -Filter *.shader -File | Remove-Item -Force
foreach ($s in $shaders) { Copy-Item $s.FullName (Join-Path $shaderFolder $s.Name) -Force }
Write-Log "Staged $($shaders.Count) shader(s) into $shaderFolder"

# --- run Unity --------------------------------------------------------------------------------------------------
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$logDir = Join-Path $toolsRoot "Logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("QudShaderBundle_{0}_{1:yyyyMMdd_HHmmss}.log" -f $Bundle, (Get-Date))
$argList = @(
    "-batchmode", "-nographics", "-quit",
    "-projectPath", ('"' + $ProjectDir + '"'),
    "-executeMethod", "BuildQudFX.Build",
    "-out", ('"' + $OutDir + '"'),
    "-bundle", $Bundle,
    "-shaders", ("Assets/QudFX/" + $Bundle),
    "-logFile", ('"' + $logFile + '"')
)
Write-Log "Building bundle '$Bundle' (log: $logFile) ..."
$proc = Start-Process -FilePath $unityExe -ArgumentList ($argList -join " ") -PassThru -WindowStyle Hidden
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { $proc.Kill() } catch { }
    Write-Log "Unity timed out after ${TimeoutSeconds}s" -Level Error
    exit 4
}

$log = if (Test-Path $logFile) { Get-Content $logFile -Raw } else { "" }
$errors = [regex]::Matches($log, "QUDFX shader error in [^\r\n]+") | ForEach-Object { $_.Value } | Select-Object -Unique
foreach ($e in $errors) { Write-Log $e -Level Error }
if ($log -match "module AssetBundle is disabled") {
    $errors = @($errors) + "AssetBundle module disabled in the staging project"
    Write-Log "Unity reported the AssetBundle module disabled; the bundles would not load in game. Check $ProjectDir\Packages\manifest.json" -Level Error
}
$built = [regex]::Matches($log, "QUDFX built (\w+)") | ForEach-Object { $_.Groups[1].Value }
$skipped = [regex]::Matches($log, "QUDFX skipping (\w+)") | ForEach-Object { $_.Groups[1].Value }
foreach ($s in $skipped) { Write-Log "skipped $s (build support not installed in Unity Hub)" -Level Warning }

# tidy and verify: drop the .manifest files and Unity's folder-level manifest bundle (a file named after the folder)
Get-ChildItem -Path $OutDir -Recurse -Filter *.manifest -File -ErrorAction SilentlyContinue | Remove-Item -Force
$produced = @()
foreach ($plat in @("windows", "osx", "linux")) {
    $stray = Join-Path $OutDir "$plat\$plat"
    if (Test-Path $stray) { Remove-Item $stray -Force }
    $f = Join-Path $OutDir "$plat\${Bundle}_$plat"
    if (Test-Path $f) { $produced += $f }
}
if ($proc.ExitCode -ne 0 -or $errors.Count -gt 0 -or $produced.Count -eq 0) {
    Write-Log "Bundle build failed (Unity exit $($proc.ExitCode), $($errors.Count) shader error(s), $($produced.Count) bundle file(s)). See $logFile" -Level Error
    exit 5
}
foreach ($p in $produced) { Write-Log "built $p ($([math]::Round((Get-Item $p).Length / 1KB)) KB)" -Level Success }
Write-Log "Done: $($built -join ', ')" -Level Success
exit 0
