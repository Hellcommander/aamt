# Setup-SD35Server.ps1
# Installs / updates the SD3.5 image server environment for AAMT.
#
#   - Code:    clones/updates Stability-AI/sd3.5 into <InstallPath>\sd3.5 (the server's working dir)
#   - Server:  copies Shared\sd35_server.py (the canonical server) to <InstallPath>\sd3.5\server.py
#   - Weights: downloads stabilityai/stable-diffusion-3.5-medium (diffusers layout, incl. T5)
#              into the normal Hugging Face cache using the machine's existing `hf auth login`.
#   - Start:   Start-StableDiffusionServer.ps1 (unchanged; it re-syncs server.py on every start)
#
# Nothing here stores or copies a token; huggingface_hub reads the existing login itself.

param(
    [string]$InstallPath = "E:\tools\sd3.5",
    [switch]$SkipModelDownload,
    [switch]$SkipT5          # skip the ~9 GB T5 text encoder (CLIP-only prompts, lower prompt adherence)
)

$ErrorActionPreference = "Continue"
$ToolsRoot = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SD3.5 Server Setup / Update" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# --- Prerequisites -----------------------------------------------------------
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$pythonCmd = $null
if ($env:AAMT_PYTHON -and (Test-Path $env:AAMT_PYTHON)) {
    $pythonCmd = $env:AAMT_PYTHON
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "  [ERROR] Python not found! Install Python 3.10+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Python: $(& $pythonCmd --version 2>&1)" -ForegroundColor Green

$hasGit = [bool](Get-Command git -ErrorAction SilentlyContinue)
if ($hasGit) {
    Write-Host "  [OK] Git found" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Git not found - the sd3.5 repo cannot be cloned/updated (the server does not need it)" -ForegroundColor Yellow
}

# torch must be a CUDA build; pip falls back to a CPU wheel if the index has no match.
$torchLine = & $pythonCmd -c "import torch; print(torch.__version__, torch.cuda.is_available())" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [WARN] torch is not importable in this Python. Install a CUDA build:" -ForegroundColor Yellow
    Write-Host "         $pythonCmd -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126" -ForegroundColor Gray
} elseif ("$torchLine" -notmatch 'True$') {
    Write-Host "  [WARN] torch $torchLine - no CUDA support (CPU-only build). Fix with:" -ForegroundColor Yellow
    Write-Host "         $pythonCmd -m pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu126" -ForegroundColor Gray
} else {
    Write-Host "  [OK] torch $torchLine" -ForegroundColor Green
}

# Hugging Face login: the existing `hf auth login` (no profiles / token names).
$hfLoginOk = $false
$tokenSwitch = Join-Path $ToolsRoot "Shared\HfTokenSwitch.psm1"
if (Test-Path $tokenSwitch) {
    Import-Module $tokenSwitch -Force
    try {
        Use-AamtHfMediaToken -Quiet | Out-Null
        $hfLoginOk = $true
        Write-Host "  [OK] Hugging Face login found" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] No Hugging Face login found. Run: hf auth login" -ForegroundColor Yellow
    }
}
if (-not $SkipModelDownload -and -not $hfLoginOk) {
    Write-Host "  [ERROR] The model is gated; log in first (hf auth login), accept the license at" -ForegroundColor Red
    Write-Host "          https://huggingface.co/stabilityai/stable-diffusion-3.5-medium, then re-run." -ForegroundColor Red
    Write-Host "          (or pass -SkipModelDownload)" -ForegroundColor Gray
    exit 1
}

Write-Host ""

# --- Install directory -------------------------------------------------------
Write-Host "Setting up installation directory..." -ForegroundColor Yellow
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "  [OK] Created directory: $InstallPath" -ForegroundColor Green
} else {
    Write-Host "  [OK] Directory exists: $InstallPath" -ForegroundColor Green
}

# Same location Start-StableDiffusionServer.ps1 uses (override with AAMT_SD_HOME).
$repoPath = if ($env:AAMT_SD_HOME) { $env:AAMT_SD_HOME } else { Join-Path $InstallPath "sd3.5" }
$repoUrl = "https://github.com/Stability-AI/sd3.5.git"

# --- Step 1: code (clone or update) -----------------------------------------
Write-Host ""
Write-Host "Step 1: SD3.5 code from GitHub..." -ForegroundColor Cyan
if (-not $hasGit) {
    Write-Host "  [SKIP] Git not available" -ForegroundColor Yellow
} elseif (Test-Path (Join-Path $repoPath ".git")) {
    Write-Host "  Updating existing repo..." -ForegroundColor Gray
    Push-Location $repoPath
    git pull --ff-only 2>&1 | Out-Host
    Pop-Location
    Write-Host "  [OK] $repoPath" -ForegroundColor Green
} elseif (Test-Path $repoPath) {
    Write-Host "  [INFO] $repoPath exists and is not a git repo; leaving it untouched" -ForegroundColor Gray
} else {
    git clone $repoUrl $repoPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] git clone failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] Cloned to $repoPath" -ForegroundColor Green
}
if (-not (Test-Path $repoPath)) { New-Item -ItemType Directory -Path $repoPath -Force | Out-Null }

# --- Step 2: Python dependencies (never touches torch) -----------------------
Write-Host ""
Write-Host "Step 2: Python dependencies..." -ForegroundColor Cyan
Write-Host "  Installing diffusers stack (torch is left alone so a CUDA build is never replaced)" -ForegroundColor Gray
& $pythonCmd -m pip install -U diffusers transformers accelerate safetensors sentencepiece protobuf huggingface_hub pillow numpy
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Some dependencies may have failed to install" -ForegroundColor Yellow
}

# --- Step 3: model weights via the existing login ----------------------------
Write-Host ""
Write-Host "Step 3: SD3.5 Medium weights (existing Hugging Face login)" -ForegroundColor Cyan
if ($SkipModelDownload) {
    Write-Host "  [SKIP] -SkipModelDownload" -ForegroundColor Gray
} else {
    Write-Host "  License must be accepted once: https://huggingface.co/stabilityai/stable-diffusion-3.5-medium" -ForegroundColor Yellow
    if ($SkipT5) {
        Write-Host "  Skipping T5 text encoder (-SkipT5)" -ForegroundColor Gray
    } else {
        Write-Host "  Including the T5 text encoder (~9 GB, better prompt adherence)" -ForegroundColor Gray
    }

    $dlPy = Join-Path $env:TEMP "aamt_sd35_download.py"
    @'
import sys

skip_t5 = len(sys.argv) > 1 and sys.argv[1] == "1"
repo = "stabilityai/stable-diffusion-3.5-medium"
allow = [
    "model_index.json", "scheduler/*", "text_encoder/*", "text_encoder_2/*",
    "tokenizer/*", "tokenizer_2/*", "tokenizer_3/*", "transformer/*", "vae/*",
]
if not skip_t5:
    allow.append("text_encoder_3/*")

try:
    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError
except Exception as exc:  # pragma: no cover
    print("ERROR: huggingface_hub is not importable:", exc, file=sys.stderr)
    sys.exit(1)

try:
    # Uses the machine's existing login (HF_TOKEN env or `hf auth login`).
    path = snapshot_download(repo, allow_patterns=allow, ignore_patterns=["*.fp16*"])
    print("OK", path)
except GatedRepoError:
    print("ERROR: no access to the gated repo. Accept the license at "
          "https://huggingface.co/" + repo + " with the account you are logged in as.", file=sys.stderr)
    sys.exit(2)
except HfHubHTTPError as exc:
    print("ERROR:", exc, file=sys.stderr)
    print("If this is a 401, your login is invalid or expired: run `hf auth login` again.", file=sys.stderr)
    sys.exit(3)
except Exception as exc:
    print("ERROR:", exc, file=sys.stderr)
    sys.exit(1)
'@ | Set-Content -Path $dlPy -Encoding UTF8

    & $pythonCmd $dlPy $(if ($SkipT5) { "1" } else { "0" })
    $dlOk = ($LASTEXITCODE -eq 0)
    Remove-Item $dlPy -ErrorAction SilentlyContinue
    if ($dlOk) {
        Write-Host "  [OK] SD3.5 Medium weights are in the Hugging Face cache" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Model download failed - see message above." -ForegroundColor Red
        exit 1
    }
}

# --- Step 4: install the canonical server ------------------------------------
Write-Host ""
Write-Host "Step 4: Installing server.py..." -ForegroundColor Cyan
$canonical = Join-Path $ToolsRoot "Shared\sd35_server.py"
$serverPy = Join-Path $repoPath "server.py"
if (Test-Path -LiteralPath $canonical) {
    Copy-Item -LiteralPath $canonical -Destination $serverPy -Force
    Write-Host "  [OK] $canonical -> $serverPy" -ForegroundColor Green
    Write-Host "  (Start-StableDiffusionServer.ps1 re-syncs this on every start)" -ForegroundColor Gray
} else {
    Write-Host "  [ERROR] Missing canonical server: $canonical" -ForegroundColor Red
    exit 1
}

# --- Port check: 1338 is the AAMT SD port; warn if another program holds it --
$sdPort = 1338
$listener = Get-NetTCPConnection -LocalPort $sdPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $isAamt = $false
    try {
        $ping = Invoke-WebRequest -Uri "http://127.0.0.1:$sdPort/ping" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($ping.Content -match '"version"\s*:\s*"aamt-1338') { $isAamt = $true }
    } catch { }
    if ($isAamt) {
        Write-Host "[INFO] The AAMT SD3.5 server is already running on port $sdPort (restart it to pick up the new server.py)." -ForegroundColor Gray
    } else {
        $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "[WARN] Port $sdPort is held by another program: $($owner.ProcessName) (PID $($listener.OwningProcess))." -ForegroundColor Yellow
        Write-Host "       Stop it, or the SD server cannot start on $sdPort." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "SD3.5 Server Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Server location: $repoPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Start the server (port 1338):" -ForegroundColor Yellow
Write-Host "  .\Start-StableDiffusionServer.ps1" -ForegroundColor White
Write-Host "Stop it:" -ForegroundColor Yellow
Write-Host "  .\Stop-StableDiffusionServer.ps1" -ForegroundColor White
Write-Host ""
