#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Spring UI spec -> Caves of Qud modern-UI window prefab: lint, preview, build the bundle with Unity, install into the mod.

.DESCRIPTION
    One command for the whole pipeline (each step can be run alone):

      generate   qud_spring_ui.py validates the spec (schema, unique names, rects, layout groups, the runtime
                 object-name contract), inlines the theme colors into <Prefab>.resolved.json and writes contract.txt
      preview    Pillow draws a PNG mock-up of the layout at the spec's reference size (no Unity)
      build      stages a Unity project matched to the game's version (6000.0.77f1) with com.unity.ugui, drops in
                 Editor\BuildQudUI.cs and runs it headless: the resolved spec becomes Assets\QudUI\<Prefab>.prefab
                 and one asset bundle per platform under <OutDir>\Bundles
      install    copies the bundles into the mod's Bundles folder (COQ_MODS_ROOT or %USERPROFILE%\AppData\LocalLow\
                 Freehold Games\CavesOfQud\Mods\<modFolder>)

    The prefab is plain uGUI; the mod's C# wires text, scrollers and icons at runtime by object name. Keep the names
    (lint checks them against the runtime contract for kind springmenu / conjoined_picker).

.PARAMETER Spec
    A *.springui.json spec. See specs\ for the two shipped windows and QUD_SPRING_UI_PIPELINE.md for the fields.

.PARAMETER OutDir
    Working/output folder. Default: Tools\Output\QudSpringUI\<bundle>.

.PARAMETER Build
    Run the Unity bundle build (needs the game-matched editor; a few minutes the first time).

.PARAMETER Install
    Copy the built bundles into the mod (-ModPath overrides the spec's modFolder).

.PARAMETER OpenProject
    Stage the Unity project and open it in the editor (GUI) instead of building, to inspect the generated prefab.

.PARAMETER NoLint / NoPreview
    Skip those steps.

.EXAMPLE
    .\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json
    .\New-QudSpringUI.ps1 -Spec specs\springmenu.springui.json -Build -Install
    .\New-QudSpringUI.ps1 -Spec specs\conjoined_picker.springui.json -Build -Install
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Spec,
    [string]$OutDir = "",
    [switch]$Build,
    [switch]$Install,
    [string]$ModPath = "",
    [switch]$Force,
    [switch]$NoLint,
    [switch]$NoPreview,
    [double]$PreviewScale = 1.0,
    [switch]$OpenProject,
    [string]$ProjectDir = "",
    [string]$UnityPath = "",
    [switch]$AllowMismatchedUnity,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent (Split-Path -Parent $here)
$shared = Join-Path $toolsRoot "Shared"
$py = Join-Path $here "qud_spring_ui.py"
Import-Module (Join-Path $shared "UnityVersionResolver.psm1") -Force
Import-Module (Join-Path $shared "UnityAssetExport.psm1") -Force
. (Join-Path (Split-Path -Parent $here) "GetQudSettings.ps1")

function Write-Log {
    param([string]$Message, [ValidateSet("Info", "Warning", "Error", "Success")][string]$Level = "Info")
    $color = @{ Info = "Gray"; Warning = "Yellow"; Error = "Red"; Success = "Green" }[$Level]
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw "python not found on PATH" }

function Invoke-Py {
    param([string[]]$ArgList)
    & $python -I $py @ArgList | Out-Host
    return $LASTEXITCODE
}

if (-not (Test-Path $Spec)) { throw "spec not found: $Spec" }
$Spec = (Resolve-Path $Spec).Path
$specJson = (Get-Content $Spec -Raw) | ConvertFrom-Json
if (-not $OutDir) { $OutDir = Join-Path $toolsRoot ("Output\QudSpringUI\" + $specJson.bundle) }
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

# --- generate (+ lint, preview) ---------------------------------------------------------------------------------
$a = @("generate", $Spec, "--out", $OutDir, "--scale", ("{0}" -f $PreviewScale))
if ($NoLint) { $a += "--no-lint" }
if (-not $NoPreview) { $a += "--preview" }
$rc = Invoke-Py $a
if ($rc -ne 0) { throw "generate failed (exit $rc)" }
$resolved = Join-Path $OutDir ("{0}.resolved.json" -f $specJson.prefab)

if (-not $Build -and -not $OpenProject) {
    Write-Host ""
    Write-Host "Output: $OutDir" -ForegroundColor Green
    Write-Host "Next: add -Build to make the prefab + bundles with Unity, -Install to drop them into the mod." -ForegroundColor Cyan
    exit 0
}

# --- Unity editor matching the game -----------------------------------------------------------------------------
$settings = Get-QudSettings
$requiredVersion = $null
if ($settings -and $settings.UnityVersion) { $requiredVersion = $settings.UnityVersion }
if (-not $requiredVersion) { $requiredVersion = "6000.0.77f1" }
$match = Find-MatchingUnityEditor -RequiredVersion $requiredVersion -ManualPath $UnityPath -PassThru -AllowMismatchedManual:$AllowMismatchedUnity
if (-not $match -or -not $match.EditorExe) {
    Write-Log "No Unity $requiredVersion editor found. $($match.InstallHint)" -Level Error
    exit 3
}
$unityExe = $match.EditorExe
Write-Log "Unity $($match.MatchedVersion): $unityExe"

# --- stage the shared project -----------------------------------------------------------------------------------
if (-not $ProjectDir) { $ProjectDir = Join-Path $toolsRoot "Output\QudSpringUI\_unity" }
Initialize-AamtUnityProject -ProjectPath $ProjectDir -EditorVersion $match.MatchedVersion | Out-Null
$editorDir = Join-Path $ProjectDir "Assets\Editor"
New-Item -ItemType Directory -Path $editorDir -Force | Out-Null
Copy-Item (Join-Path $here "Editor\BuildQudUI.cs") (Join-Path $editorDir "BuildQudUI.cs") -Force

$manifestPath = Join-Path $ProjectDir "Packages\manifest.json"
$deps = @{}
if (Test-Path $manifestPath) {
    try {
        $parsed = (Get-Content $manifestPath -Raw) | ConvertFrom-Json
        if ($parsed.dependencies) { $parsed.dependencies.PSObject.Properties | ForEach-Object { $deps[$_.Name] = $_.Value } }
    } catch { Write-Log "manifest.json unreadable, rewriting it" -Level Warning }
}
$changed = $false
foreach ($pkg in @(@("com.unity.ugui", "2.0.0"), @("com.unity.modules.ui", "1.0.0"), @("com.unity.modules.assetbundle", "1.0.0"), @("com.unity.modules.imageconversion", "1.0.0"))) {
    if (-not $deps.ContainsKey($pkg[0])) { $deps[$pkg[0]] = $pkg[1]; $changed = $true }
}
if ($changed -or -not (Test-Path $manifestPath)) {
    $json = @{ dependencies = $deps } | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding $false))
    Write-Log "Packages/manifest.json updated (com.unity.ugui added)"
}
Write-Log "Staged project: $ProjectDir"

if ($OpenProject) {
    Write-Log "Opening the staged project in Unity. Generated prefabs live under Assets/QudUI; edit the SPEC (not the prefab) to keep changes."
    Start-Process -FilePath $unityExe -ArgumentList @("-projectPath", ('"' + $ProjectDir + '"')) | Out-Null
    exit 0
}

# --- build ------------------------------------------------------------------------------------------------------
$bundleOut = Join-Path $OutDir "Bundles"
New-Item -ItemType Directory -Path $bundleOut -Force | Out-Null
$logDir = Join-Path $toolsRoot "Logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("QudSpringUI_{0}_{1:yyyyMMdd_HHmmss}.log" -f $specJson.bundle, (Get-Date))
$argList = @(
    "-batchmode", "-nographics", "-quit",
    "-projectPath", ('"' + $ProjectDir + '"'),
    "-executeMethod", "BuildQudUI.Build",
    "-spec", ('"' + $resolved + '"'),
    "-out", ('"' + $bundleOut + '"'),
    "-bundle", [string]$specJson.bundle,
    "-logFile", ('"' + $logFile + '"')
)
Write-Log "Building '$($specJson.prefab)' into bundle '$($specJson.bundle)' (log: $logFile) ..."
$proc = Start-Process -FilePath $unityExe -ArgumentList ($argList -join " ") -PassThru -WindowStyle Hidden
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { $proc.Kill() } catch { }
    Write-Log "Unity timed out after ${TimeoutSeconds}s" -Level Error
    exit 4
}

$log = if (Test-Path $logFile) { Get-Content $logFile -Raw } else { "" }
$errors = [regex]::Matches($log, "QUDUI error[^\r\n]*") | ForEach-Object { $_.Value } | Select-Object -Unique
foreach ($e in $errors) { Write-Log $e -Level Error }
$warnings = [regex]::Matches($log, "QUDUI warning[^\r\n]*") | ForEach-Object { $_.Value } | Select-Object -Unique
foreach ($w in $warnings) { Write-Log $w -Level Warning }
$compileErrors = [regex]::Matches($log, "error CS\d{4}[^\r\n]*") | ForEach-Object { $_.Value } | Select-Object -Unique
foreach ($e in $compileErrors) { Write-Log "editor script: $e" -Level Error }
$skipped = [regex]::Matches($log, "QUDUI skipping (\w+)") | ForEach-Object { $_.Groups[1].Value }
foreach ($s in $skipped) { Write-Log "skipped $s (build support not installed in Unity Hub)" -Level Warning }

Get-ChildItem -Path $bundleOut -Recurse -Filter *.manifest -File -ErrorAction SilentlyContinue | Remove-Item -Force
$produced = @()
foreach ($plat in @("windows", "osx", "linux")) {
    $stray = Join-Path $bundleOut "$plat\$plat"
    if (Test-Path $stray) { Remove-Item $stray -Force }
    $f = Join-Path $bundleOut ("$plat\{0}_$plat" -f $specJson.bundle)
    if (Test-Path $f) { $produced += $f }
}
if ($proc.ExitCode -ne 0 -or $errors.Count -gt 0 -or $compileErrors.Count -gt 0 -or $produced.Count -eq 0) {
    Write-Log "Bundle build failed (Unity exit $($proc.ExitCode), $($errors.Count + $compileErrors.Count) error(s), $($produced.Count) bundle file(s)). See $logFile" -Level Error
    exit 5
}
foreach ($p in $produced) { Write-Log "built $p ($([math]::Round((Get-Item $p).Length / 1KB)) KB)" -Level Success }

# --- install ----------------------------------------------------------------------------------------------------
if ($Install) {
    $a = @("install", $OutDir)
    if ($ModPath) { $a += @("--mod-path", $ModPath) }
    if ($Force) { $a += "--force" }
    if ((Invoke-Py $a) -ne 0) { throw "install failed" }
}

Write-Host ""
Write-Host "Output: $OutDir" -ForegroundColor Green
if (-not $Install) { Write-Host "Next: add -Install to copy the bundles into the mod (restart the game afterwards)." -ForegroundColor Cyan }
exit 0
