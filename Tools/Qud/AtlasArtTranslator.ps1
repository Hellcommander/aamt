# AtlasArtTranslator.ps1
# Atlas of Qud Automap/tiles → non-tile illustrated art via SD img2img (+ optional Ollama caption)

[CmdletBinding()]
param(
    [ValidateSet("List", "Prepare", "Generate", "Gui")]
    [string]$Action = "List",

    [string]$Path,

    [string]$UserData = "$env:USERPROFILE\AppData\LocalLow\Freehold Games\CavesOfQud",

    [ValidateSet("cartography", "landscape", "dream")]
    [string]$Style = "landscape",

    [string]$Parasang = "",

    [string]$Output,

    [switch]$OllamaCaption,

    [string]$OllamaUrl = "http://localhost:11434",

    [double]$Strength = -1,

    [switch]$AllowStartServer
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyHelper = Join-Path $here "qud_atlas_art.py"
$shared = Join-Path (Split-Path $here -Parent) "Shared"
$sdModule = Join-Path $shared "StableDiffusionIntegration.psm1"

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try { return (Get-Command $c -ErrorAction Stop).Source } catch {}
    }
    throw "Python not found on PATH."
}

function Invoke-AtlasPy([string[]]$PyArgs) {
    $py = Get-PythonExe
    & $py $pyHelper @PyArgs
    if ($LASTEXITCODE -ne 0) { throw "qud_atlas_art.py failed (exit $LASTEXITCODE)" }
}

if ($Action -eq "Gui") {
    $gui = Join-Path $here "AtlasArtTranslator-GUI.ps1"
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File $gui
    exit $LASTEXITCODE
}

if ($Action -eq "List") {
    Invoke-AtlasPy @("--userdata", $UserData, "list", "--tiles")
    exit 0
}

if ($Action -eq "Prepare") {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "Prepare requires -Path (PNG or tiles dir)" }
    $args = @("--userdata", $UserData, "prepare", $Path, "--style", $Style)
    if ($OllamaCaption) { $args += "--ollama"; $args += @("--ollama-url", $OllamaUrl) }
    if ($Parasang) { $args += @("--parasang", $Parasang) }
    if ($Output) { $args += @("-o", $Output) }
    Invoke-AtlasPy $args
    exit 0
}

if ($Action -eq "Generate") {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "Generate requires -Path (Atlas PNG, tiles dir, or job JSON)" }

    $jobPath = $null
    $job = $null
    if ($Path -like "*.json") {
        $job = Get-Content -Raw $Path | ConvertFrom-Json
    } else {
        $tmpDir = Join-Path $here "..\Output\AtlasArt\_jobs"
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
        $jobPath = Join-Path $tmpDir ("job_{0}.json" -f [Guid]::NewGuid().ToString("N").Substring(0, 8))
        $prep = @("--userdata", $UserData, "prepare", $Path, "--style", $Style, "-o", $jobPath)
        if ($OllamaCaption) { $prep += "--ollama"; $prep += @("--ollama-url", $OllamaUrl) }
        if ($Parasang) { $prep += @("--parasang", $Parasang) }
        if ($Output) {
            $outDir = if (Test-Path $Output -PathType Container) { $Output } else { Split-Path -Parent $Output }
            if ($outDir) { $prep += @("--out-dir", $outDir) }
        }
        Invoke-AtlasPy $prep
        $job = Get-Content -Raw $jobPath | ConvertFrom-Json
    }

    $strength = if ($Strength -ge 0) { $Strength } else { [double]$job.strength }
    $outImage = if ($Output -and $Output -like "*.png") { $Output } else { [string]$job.outputImage }
    $outDir = Split-Path -Parent $outImage
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null

    if (-not (Test-Path $sdModule)) { throw "Missing SD module: $sdModule" }
    Import-Module $sdModule -Force

    Write-Host "Atlas → Art [$($job.style)] strength=$strength" -ForegroundColor Cyan
    Write-Host "  Source: $($job.sourceImage)" -ForegroundColor Gray
    Write-Host "  Output: $outImage" -ForegroundColor Gray

    $genParams = @{
        Prompt              = [string]$job.prompt
        NegativePrompt      = [string]$job.negativePrompt
        OutputPath          = $outImage
        Width               = [int]$job.width
        Height              = [int]$job.height
        ReferenceImagePath  = [string]$job.sourceImage
        ImageStrength       = $strength
        EnhanceWithOllama   = $false
        AutoStartServer     = [bool]$AllowStartServer
    }
    Generate-AssetImageWithSD3 @genParams

    $meta = Join-Path $outDir (([IO.Path]::GetFileNameWithoutExtension($outImage)) + ".json")
    ($job | ConvertTo-Json -Depth 8) | Set-Content -Path $meta -Encoding UTF8
    Write-Host "Done: $outImage" -ForegroundColor Green
    exit 0
}
