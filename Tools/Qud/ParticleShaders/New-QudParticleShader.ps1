#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Particle spec -> Qud Shader Library effects: generate, lint, preview, build the bundle, install into the mod.

.DESCRIPTION
    One command for the whole pipeline (each step can be run alone):

      generate   qud_particle_shader.py writes one .shader per effect (ShaderKit contract), a ShaderEffects
                 fragment with a <preset> per effect, a C# usage snippet and manifest.json
      lint       fxc (Windows SDK) compiles each fragment program offline, no Unity needed
      preview    numpy renders the same maths to GIFs (over a `shader mapshot` PNG when given)
      build      Build-QudShaderBundle.ps1 stages a Unity project and builds Bundles\windows\<bundle>_windows
      install    copies the bundle into the mod and merges the presets into its ShaderEffects.xml

    -Describe "..." lets Ollama draft the spec first (then you edit it and rerun).

.PARAMETER Spec
    A *.particles.json spec. See specs\ for the five mod samples and QUD_PARTICLE_SHADERS.md for the fields.

.PARAMETER OutDir
    Working/output folder. Default: Tools\Output\QudShaderForge\<bundle>.

.PARAMETER Build
    Run the Unity bundle build (needs the game-matched editor; a few minutes the first time).

.PARAMETER Install
    Copy the built bundle into the mod and merge presets. Uses -ModPath, else the spec's modPath/modFolder under
    the game's Mods folder (COQ_MODS_ROOT or %USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods).

.PARAMETER NoLint / NoPreview
    Skip those steps.

.PARAMETER Describe
    Draft the spec from a description with Ollama and write it to -Spec (which must not exist yet).

.EXAMPLE
    .\New-QudParticleShader.ps1 -Spec specs\broodmother.particles.json
    .\New-QudParticleShader.ps1 -Spec specs\broodmother.particles.json -Build -Install
    .\New-QudParticleShader.ps1 -Spec my.particles.json -Describe "green spores drifting up from a nest" -Mod Arendeth_Broodmother -Prefix BM_
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
    [string]$Mapshot = "",
    [int]$Frames = 24,
    [string]$Describe = "",
    [string]$Mod = "",
    [string]$Bundle = "",
    [string]$Prefix = "",
    [string]$OllamaModel = "",
    [string]$UnityPath = "",
    [string]$ShaderLibraryPath = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent (Split-Path -Parent $here)
$py = Join-Path $here "qud_particle_shader.py"

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command python3 -ErrorAction SilentlyContinue).Source }
if (-not $python) { throw "python not found on PATH" }

function Invoke-Py {
    param([string[]]$ArgList)
    # stream python's output to the console; only the exit code is returned
    & $python -I $py @ArgList | Out-Host
    return $LASTEXITCODE
}

# --- optional: draft with Ollama --------------------------------------------------------------------------------
if ($Describe) {
    if (Test-Path $Spec) { throw "-Describe writes a new spec; $Spec already exists" }
    $a = @("draft", "--describe", $Describe, "--out", $Spec)
    if ($Mod) { $a += @("--mod", $Mod) }
    if ($Bundle) { $a += @("--bundle", $Bundle) }
    if ($Prefix) { $a += @("--prefix", $Prefix) }
    if ($OllamaModel) { $a += @("--model", $OllamaModel) }
    if ((Invoke-Py $a) -ne 0) { throw "draft failed" }
    Write-Host "Drafted $Spec - review the values, then rerun without -Describe to generate." -ForegroundColor Cyan
}

if (-not (Test-Path $Spec)) { throw "spec not found: $Spec" }
$Spec = (Resolve-Path $Spec).Path
$specJson = (Get-Content $Spec -Raw) | ConvertFrom-Json
if (-not $OutDir) { $OutDir = Join-Path $toolsRoot ("Output\QudShaderForge\" + $specJson.bundle) }

# --- generate (+ lint, preview) ---------------------------------------------------------------------------------
$a = @("generate", $Spec, "--out", $OutDir, "--frames", "$Frames")
if (-not $NoLint) { $a += "--lint" }
if (-not $NoPreview) { $a += "--preview" }
if ($Mapshot) { $a += @("--mapshot", $Mapshot) }
if ($ShaderLibraryPath) { $a += @("--shader-library", $ShaderLibraryPath) }
$rc = Invoke-Py $a
if ($rc -ne 0) { throw "generate failed (exit $rc)" }

# --- build ------------------------------------------------------------------------------------------------------
if ($Build) {
    # a hashtable splat: named parameters (an array would bind them positionally)
    $b = @{ ShaderDir = (Join-Path $OutDir "shaders"); Bundle = [string]$specJson.bundle; OutDir = (Join-Path $OutDir "Bundles") }
    if ($UnityPath) { $b.UnityPath = $UnityPath }
    if ($ShaderLibraryPath) { $b.ShaderLibraryPath = $ShaderLibraryPath }
    & (Join-Path $here "Build-QudShaderBundle.ps1") @b
    if ($LASTEXITCODE -ne 0) { throw "bundle build failed (exit $LASTEXITCODE)" }
}

# --- install ----------------------------------------------------------------------------------------------------
if ($Install) {
    $a = @("install", $OutDir)
    if ($ModPath) { $a += @("--mod-path", $ModPath) }
    if ($Force) { $a += "--force" }
    if ((Invoke-Py $a) -ne 0) { throw "install failed" }
}

Write-Host ""
Write-Host "Output: $OutDir" -ForegroundColor Green
if (-not $Build) { Write-Host "Next: add -Build to compile the bundle with Unity, -Install to drop it into the mod." -ForegroundColor Cyan }
