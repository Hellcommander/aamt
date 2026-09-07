# Setup-StableAudio.ps1
# Installs Stable Audio 3 (medium) for Transcendence / AAMT sound-effect generation.

param(
    [string]$InstallPath = "E:\tools\stable-audio",
    [string]$PythonPath = "",
    [string]$Model = "medium",
    [switch]$SkipModelDownload,
    [switch]$SkipDeps,
    [switch]$SkipFlashAttn
)

$ErrorActionPreference = "Continue"
$ToolsRoot = $PSScriptRoot
$RepoUrl = "https://github.com/Stability-AI/stable-audio-3.git"
$RepoPath = Join-Path $InstallPath "stable-audio-3"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Stable Audio 3 Setup (Transcendence SFX)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Model: $Model  (HF: stabilityai/stable-audio-3-$Model)" -ForegroundColor Gray
Write-Host ""

function Resolve-AudioPython {
    param([string]$Preferred)
    if ($Preferred -and (Test-Path $Preferred)) { return $Preferred }
    if ($env:AAMT_STABLE_AUDIO_PYTHON -and (Test-Path $env:AAMT_STABLE_AUDIO_PYTHON)) {
        return $env:AAMT_STABLE_AUDIO_PYTHON
    }
    $candidates = @(
        "E:\tools\miniconda3\python.exe",
        "C:\Python312\python.exe",
        "C:\Python313\python.exe",
        "C:\Python314\python.exe"
    )
    foreach ($c in $candidates) {
        if (-not (Test-Path $c)) { continue }
        $cuda = & $c -c "import torch; print('1' if torch.cuda.is_available() else '0')" 2>$null
        if ($cuda -eq "1") {
            Write-Host "  [OK] CUDA Python: $c" -ForegroundColor Green
            return $c
        }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python not found."
}

try {
    $pythonCmd = Resolve-AudioPython -Preferred $PythonPath
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    exit 1
}

$pyVer = & $pythonCmd --version 2>&1
Write-Host "  Using: $pythonCmd ($pyVer)" -ForegroundColor Gray
& $pythonCmd -c "import torch,torchaudio; print('torch', torch.__version__, 'torchaudio', torchaudio.__version__, 'cuda', torch.cuda.is_available())" 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  [ERROR] Git required to clone stable-audio-3" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
}

# Keep HF cache on the install drive (C: often too small for ~9GB medium weights)
# IMPORTANT: do NOT override HF_HOME — that hides the login token under %USERPROFILE%\.cache\huggingface
$hfHub = Join-Path $InstallPath "hub"
New-Item -ItemType Directory -Path $hfHub -Force | Out-Null
$env:HUGGINGFACE_HUB_CACHE = $hfHub
$env:HF_HUB_CACHE = $hfHub
Remove-Item Env:HF_HOME -ErrorAction SilentlyContinue
Write-Host "  HF model cache: $hfHub (token stays in user profile)" -ForegroundColor Gray
# Optional: mirror token into install dir for tools that set HF_HOME locally
$userToken = Join-Path $env:USERPROFILE ".cache\huggingface\token"
$localHfHome = Join-Path $InstallPath "hf-home"
New-Item -ItemType Directory -Path $localHfHome -Force | Out-Null
if (Test-Path $userToken) {
    Copy-Item $userToken (Join-Path $localHfHome "token") -Force -ErrorAction SilentlyContinue
}

# Auto-switch to media download token by name (SD3.5 Token)
$tokenSwitch = Join-Path $ToolsRoot "Shared\HfTokenSwitch.psm1"
if (Test-Path $tokenSwitch) {
    Import-Module $tokenSwitch -Force
    try {
        Use-AamtHfMediaToken | Out-Null
    } catch {
        Write-Host "  [WARN] Could not auto-switch HF token: $_" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Step 1: Clone Stability-AI/stable-audio-3 ..." -ForegroundColor Cyan
if (Test-Path (Join-Path $RepoPath ".git")) {
    Write-Host "  Updating existing repo..." -ForegroundColor Gray
    Push-Location $RepoPath
    git pull --ff-only 2>&1 | Out-Host
    Pop-Location
} elseif (Test-Path $RepoPath) {
    Write-Host "  [WARN] $RepoPath exists but is not a git repo" -ForegroundColor Yellow
} else {
    git clone $RepoUrl $RepoPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] git clone failed" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  [OK] $RepoPath" -ForegroundColor Green

if (-not $SkipDeps) {
    Write-Host ""
    Write-Host "Step 2: Install stable-audio-3 into Python env..." -ForegroundColor Cyan
    Write-Host "  Keeping existing torch/torchaudio (do not overwrite CUDA builds)" -ForegroundColor Gray
    Push-Location $RepoPath
    & $pythonCmd -m pip install -U pip wheel
    & $pythonCmd -m pip install -e . --no-deps 2>&1 | Out-Host

    $depHelper = Join-Path $ToolsRoot "Shared\sa3_install_deps.py"
    Copy-Item $depHelper (Join-Path $RepoPath "sa3_install_deps.py") -Force
    & $pythonCmd (Join-Path $RepoPath "sa3_install_deps.py")
    & $pythonCmd -m pip install -U soundfile einops huggingface_hub safetensors transformers tqdm scipy numpy
    Pop-Location
    Write-Host "  [OK] Package install attempted" -ForegroundColor Green
} else {
    Write-Host "Step 2: Skipping deps (-SkipDeps)" -ForegroundColor Gray
}

if (-not $SkipFlashAttn -and $Model -eq "medium") {
    Write-Host ""
    Write-Host "Step 3: Flash Attention (required for medium)..." -ForegroundColor Cyan
    $fa = & $pythonCmd -c "import flash_attn; print(flash_attn.__version__)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $fa) {
        Write-Host "  [OK] flash_attn $fa already installed" -ForegroundColor Green
    } else {
        Write-Host "  Trying pip install flash-attn (may fail on Windows / Turing GPUs)..." -ForegroundColor Yellow
        & $pythonCmd -m pip install flash-attn --no-build-isolation 2>&1 | Select-Object -Last 20 | Out-Host
        $fa2 = & $pythonCmd -c "import flash_attn; print(flash_attn.__version__)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] flash_attn $fa2" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] flash-attn not installed. Medium may fail." -ForegroundColor Yellow
            Write-Host "  Fallback for Transcendence SFX: use -Model small-sfx" -ForegroundColor Yellow
            Write-Host "  https://huggingface.co/stabilityai/stable-audio-3-small-sfx" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "Step 3: Skipping flash-attn" -ForegroundColor Gray
}

if (-not $SkipModelDownload) {
    Write-Host ""
    Write-Host "Step 4: Prefetch HF weights for '$Model'..." -ForegroundColor Cyan
    Write-Host "  Accept license first:" -ForegroundColor Yellow
    Write-Host "    https://huggingface.co/stabilityai/stable-audio-3-$Model" -ForegroundColor Cyan

    # Prefetch: token from user profile, weights into E: hub cache
    $prefetchPath = Join-Path $env:TEMP "sa3_prefetch.py"
    @"
import os, sys
sys.path.insert(0, r'$RepoPath')
os.environ['AAMT_STABLE_AUDIO_DIR'] = r'$InstallPath'
os.environ.pop('HF_HOME', None)  # keep default so login token is found
os.environ['HUGGINGFACE_HUB_CACHE'] = r'$hfHub'
os.environ['HF_HUB_CACHE'] = r'$hfHub'
from huggingface_hub.utils import get_token
print('token=', bool(get_token()))
print('HUGGINGFACE_HUB_CACHE=', os.environ['HUGGINGFACE_HUB_CACHE'])
try:
    from stable_audio_3 import StableAudioModel
    print('Downloading / loading model "$Model" into E: cache...')
    m = StableAudioModel.from_pretrained('$Model')
    print('OK: model ready', type(m))
except Exception as e:
    print('ERROR:', e, file=sys.stderr)
    sys.exit(1)
"@ | Set-Content -Path $prefetchPath -Encoding UTF8

    & $pythonCmd $prefetchPath
    $ok = ($LASTEXITCODE -eq 0)
    Remove-Item $prefetchPath -ErrorAction SilentlyContinue
    if ($ok) {
        Write-Host "  [OK] Model cached under $hfHub" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Model prefetch failed - check HF login / license accept." -ForegroundColor Red
        Write-Host "  https://huggingface.co/stabilityai/stable-audio-3-$Model" -ForegroundColor Yellow
    }
} else {
    Write-Host "Step 4: Skipping model download" -ForegroundColor Gray
}

$envHint = @"
`$env:AAMT_STABLE_AUDIO_DIR = "$InstallPath"
`$env:AAMT_STABLE_AUDIO_PYTHON = "$pythonCmd"
`$env:AAMT_STABLE_AUDIO_MODEL = "$Model"
`$env:HUGGINGFACE_HUB_CACHE = "$hfHub"
`$env:HF_HUB_CACHE = "$hfHub"
`$env:TRANSFORMERS_CACHE = "$(Join-Path $InstallPath 'transformers')"
# Do not set HF_HOME — token stays in %USERPROFILE%\.cache\huggingface
`$env:PYTHONPATH = if (`$env:PYTHONPATH) { "$RepoPath;`$(`$env:PYTHONPATH)" } else { "$RepoPath" }
"@
Set-Content -Path (Join-Path $InstallPath "aamt_stable_audio_env.ps1") -Value $envHint -Encoding UTF8

Write-Host ""
Write-Host "Step 5: Verify generator..." -ForegroundColor Cyan
$env:AAMT_STABLE_AUDIO_DIR = $InstallPath
$env:AAMT_STABLE_AUDIO_MODEL = $Model
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$RepoPath;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $RepoPath
}
$gen = Join-Path $ToolsRoot "Shared\stable_audio_generate.py"
& $pythonCmd $gen --check-only
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Generator ready" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Generator check failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Stable Audio 3 setup finished" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Generate Transcendence SFX:" -ForegroundColor Cyan
Write-Host '  .\Generate-StableAudio.ps1 -Prompt "spaceship laser shot, short punchy" -Output ".\TestOutput\laser.wav" -Seconds 2' -ForegroundColor Gray
Write-Host ""
Write-Host "If medium fails (flash-attn / VRAM), use Small-SFX:" -ForegroundColor Yellow
Write-Host '  .\Generate-StableAudio.ps1 -Model small-sfx -Prompt "metal hatch clang" -Output ".\TestOutput\hatch.wav" -Seconds 2' -ForegroundColor Gray
Write-Host "Stop SD image server first if VRAM is tight." -ForegroundColor Yellow
Write-Host ""
