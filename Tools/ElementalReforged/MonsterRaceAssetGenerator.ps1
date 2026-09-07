<#
.SYNOPSIS
    Monster Race Gear Asset Generator for Elemental Reforged (AAMT)

.DESCRIPTION
    Wraps monster_race_tool.py and wires Shared AAMT tools:
      - Ollama (prompt enhancement)
      - Stable Diffusion 3.5 (icons/textures)
      - ImageMagick (postprocess)
      - Procedural Pillow fallbacks

.EXAMPLE
    .\MonsterRaceAssetGenerator.ps1 -Race All -Mode Both -InstallToMod -StartSD

.EXAMPLE
    .\MonsterRaceAssetGenerator.ps1 -Race Darkling -Mode AI -InstallToMod
#>

[CmdletBinding()]
param(
    [string]$Race = "All",
    [ValidateSet("Tools", "AI", "Both")]
    [string]$Mode = "Both",
    [string]$ModPath = "",
    [switch]$InstallToMod,
    [switch]$UseAI,
    [switch]$ScanOnly,
    [switch]$Doctor,
    [switch]$CheckMeshes,
    [switch]$StartSD,
    [switch]$SkipSD,
    [switch]$NoEnhance,
    [switch]$Force,
    [switch]$Banner,
    [switch]$BannerOnly,
    [string]$OutputDir = "",
    [string]$AiKinds = "clothes,armor,weapon",
    [int]$Jobs = 4,
    [int]$SdSteps = 28,
    [int]$SdWait = 180
)

$ErrorActionPreference = "Continue"
$ToolsRoot = Split-Path $PSScriptRoot -Parent
$SharedPath = Join-Path $ToolsRoot "Shared"
$PyTool = Join-Path $PSScriptRoot "monster_race_tool.py"
$configPath = Join-Path $PSScriptRoot "monster_race_config.json"

if (-not (Test-Path $PyTool)) {
    Write-Host "Missing monster_race_tool.py" -ForegroundColor Red
    exit 1
}

# Optional Shared status display
$settingsPath = Join-Path $ToolsRoot "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) { . $settingsPath }
Import-Module (Join-Path $SharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $SharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $SharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $SharedPath "StableDiffusionIntegration.psm1") -ErrorAction SilentlyContinue

if ($UseAI -and $Mode -eq "Tools") { $Mode = "Both" }

if (Get-Command Initialize-ToolsetTools -ErrorAction SilentlyContinue) {
    $null = Initialize-ToolsetTools -RequiredTools @("Python") -OptionalTools @("Ollama", "StableDiffusion", "ImageMagick", "Blender")
    if (Get-Command Show-ToolsetStatus -ErrorAction SilentlyContinue) {
        Show-ToolsetStatus -ToolsetName "ElementalReforged (Monster Gear AI)" `
            -RequiredTools @("Python") `
            -OptionalTools @("Ollama", "StableDiffusion", "ImageMagick", "Blender")
    }
}

$erConfig = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $ModPath) { $ModPath = [string]$erConfig.modDefaultPath }
if (-not $OutputDir) { $OutputDir = Join-Path $PSScriptRoot "Output" }

function Invoke-PyTool([string[]]$PyArgs) {
    Write-Host ("python monster_race_tool.py {0}" -f ($PyArgs -join ' ')) -ForegroundColor DarkGray
    & python $PyTool @PyArgs
    return $LASTEXITCODE
}

$common = @("--config", $configPath, "--mod", $ModPath)

if ($Doctor) {
    $doc = $common + @("doctor")
    if ($StartSD) { $doc += "--start-sd"; $doc += @("--sd-wait", "$SdWait") }
    exit (Invoke-PyTool $doc)
}
if ($ScanOnly) { exit (Invoke-PyTool ($common + @("scan"))) }
if ($CheckMeshes) {
    $mesh = $common + @("check-meshes")
    if ($Race -eq "All") { $mesh += "--all" } else { $mesh += @("--race", $Race) }
    exit (Invoke-PyTool $mesh)
}

function Invoke-Banner {
    # Banner quality floor: 40 steps / CFG 7.5 unless caller overrode -SdSteps
    $banSteps = if ($PSBoundParameters.ContainsKey("SdSteps")) { $SdSteps } else { 40 }
    $ban = $common + @(
        "banner", "--output", $OutputDir,
        "--sd-steps", "$banSteps", "--sd-wait", "$SdWait", "--guidance", "7.5"
    )
    if ($InstallToMod) { $ban += "--install" }
    if ($Force) { $ban += "--force" }
    if ($NoEnhance) { $ban += "--no-enhance" }
    if ($StartSD -or -not $SkipSD) { $ban += "--start-sd" }
    Write-Host "`n=== Mod Manager banner (local SD/Ollama, high quality) ===" -ForegroundColor Cyan
    return (Invoke-PyTool $ban)
}

if ($BannerOnly) {
    exit (Invoke-Banner)
}

# Ensure Ollama is up when AI requested
$modeLower = $Mode.ToLowerInvariant()
if ($modeLower -ne "tools") {
    if (Get-Command Use-OllamaIfAvailable -ErrorAction SilentlyContinue) {
        $null = Use-OllamaIfAvailable
    }
    if ($StartSD -or -not $SkipSD) {
        $startScript = Join-Path $ToolsRoot "Start-StableDiffusionServer.ps1"
        if (Test-Path $startScript) {
            # Fast TCP check — only launch if down
            $sdUp = $false
            try {
                $client = New-Object System.Net.Sockets.TcpClient
                $async = $client.BeginConnect("127.0.0.1", 1338, $null, $null)
                $sdUp = $async.AsyncWaitHandle.WaitOne(400, $false)
                if ($sdUp) { try { $client.EndConnect($async) } catch { $sdUp = $false } }
                $client.Close()
            } catch { $sdUp = $false }
            if (-not $sdUp) {
                Write-Host "Starting SD3.5 server..." -ForegroundColor Cyan
                Start-Process powershell -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $startScript) -WindowStyle Minimized
            } else {
                Write-Host "[OK] SD already listening on 1338" -ForegroundColor Green
            }
        }
    }
}

$gen = $common + @(
    "generate",
    "--output", $OutputDir,
    "--mode", $modeLower,
    "--jobs", "$Jobs",
    "--sd-steps", "$SdSteps",
    "--sd-wait", "$SdWait",
    "--ai-kinds", $AiKinds
)
if ($Race -eq "All") { $gen += "--all" } else { $gen += @("--race", $Race) }
if ($InstallToMod) { $gen += "--install" }
if ($StartSD -or ($modeLower -ne "tools" -and -not $SkipSD)) { $gen += "--start-sd" }
if ($SkipSD) { $gen += "--skip-sd-start" }
if ($NoEnhance) { $gen += "--no-enhance" }
if ($Force) { $gen += "--force-ai" }

Write-Host "`n=== Elemental Reforged Monster Gear (AAMT) ===" -ForegroundColor Cyan
Write-Host "Mode: $Mode | Race: $Race | Install: $InstallToMod | StartSD: $StartSD" -ForegroundColor Gray
$code = Invoke-PyTool $gen
if ($code -ne 0) { exit $code }

if ($Banner) {
    $bcode = Invoke-Banner
    if ($bcode -ne 0) { exit $bcode }
}

if ($InstallToMod) {
    Write-Host "`nHardening unit presentation (poses / UnitModelType / skeletons)..." -ForegroundColor Cyan
    $hcode = Invoke-PyTool ($common + @("harden-units", "--strict"))
    if ($hcode -ne 0) { exit $hcode }
    Write-Host "`nValidating..." -ForegroundColor Cyan
    exit (Invoke-PyTool ($common + @("validate")))
}
Write-Host "`nDone." -ForegroundColor Green
exit 0
