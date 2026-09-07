# Download-RequiredTools.ps1
# Downloads and sets up required tools for UncensoredCharacterImageGenerator

param(
    [switch]$InstallOllama,
    [switch]$InstallStableDiffusion,
    [switch]$InstallPythonDependencies,
    [switch]$All
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Required Tools Downloader" -ForegroundColor Cyan
Write-Host "  For UncensoredCharacterImageGenerator" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Determine what to install
if ($All) {
    $InstallOllama = $true
    $InstallStableDiffusion = $true
    $InstallPythonDependencies = $true
}

if (-not ($InstallOllama -or $InstallStableDiffusion -or $InstallPythonDependencies)) {
    Write-Host "No installation options specified. Use -All to install everything, or specify:" -ForegroundColor Yellow
    Write-Host "  -InstallOllama              Install Ollama" -ForegroundColor Gray
    Write-Host "  -InstallStableDiffusion     Install Stable Diffusion API server" -ForegroundColor Gray
    Write-Host "  -InstallPythonDependencies Install Python dependencies" -ForegroundColor Gray
    Write-Host "`nExample: .\Download-RequiredTools.ps1 -All" -ForegroundColor Cyan
    exit 0
}

# ============================================================
# 1. OLLAMA INSTALLATION
# ============================================================

if ($InstallOllama) {
    Write-Host "`n[1/3] Checking Ollama installation..." -ForegroundColor Cyan
    
    # Check if Ollama is already installed
    $ollamaInstalled = $false
    $ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaExe) {
        try {
            $ollamaVersion = ollama --version 2>&1
            if ($LASTEXITCODE -eq 0 -or $ollamaVersion -match "version") {
                Write-Host "  ✓ Ollama is already installed: $ollamaVersion" -ForegroundColor Green
                $ollamaInstalled = $true
            }
        } catch {
            # Ollama command failed - not installed
        }
    }
    
    if (-not $ollamaInstalled) {
        Write-Host "  Ollama not found. Downloading installer..." -ForegroundColor Yellow
        
        $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
        $ollamaInstaller = Join-Path $env:TEMP "OllamaSetup.exe"
        
        try {
            Write-Host "  Downloading from: $ollamaUrl" -ForegroundColor Gray
            Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaInstaller -UseBasicParsing
            
            Write-Host "  ✓ Download complete: $ollamaInstaller" -ForegroundColor Green
            Write-Host "`n  Please run the installer manually:" -ForegroundColor Yellow
            Write-Host "    $ollamaInstaller" -ForegroundColor White
            Write-Host "`n  After installation, download required models:" -ForegroundColor Yellow
            Write-Host "    ollama pull llama3.1:8b" -ForegroundColor White
            Write-Host "    ollama pull wizardlm-uncensored:latest" -ForegroundColor White
            Write-Host "    ollama pull deepseek-r1:7b" -ForegroundColor White
        } catch {
            Write-Host "  ✗ Failed to download Ollama: $_" -ForegroundColor Red
            Write-Host "  Please download manually from: https://ollama.com" -ForegroundColor Yellow
        }
    }
    
    if ($ollamaInstalled) {
        # Check if required models are available
        Write-Host "`n  Checking for required Ollama models..." -ForegroundColor Cyan
        $requiredModels = @("llama3.1:8b", "wizardlm-uncensored:latest", "deepseek-r1:7b")
        $missingModels = @()
        
        foreach ($model in $requiredModels) {
            try {
                $result = ollama list 2>&1 | Select-String $model
                if ($result) {
                    Write-Host "    ✓ $model" -ForegroundColor Green
                } else {
                    Write-Host "    ✗ $model (missing)" -ForegroundColor Yellow
                    $missingModels += $model
                }
            } catch {
                Write-Host "    ? $model (could not check)" -ForegroundColor Gray
            }
        }
        
        if ($missingModels.Count -gt 0) {
            Write-Host "`n  Download missing models with:" -ForegroundColor Yellow
            foreach ($model in $missingModels) {
                Write-Host "    ollama pull $model" -ForegroundColor White
            }
        }
    }
}

# ============================================================
# 2. STABLE DIFFUSION API SERVER
# ============================================================

if ($InstallStableDiffusion) {
    Write-Host "`n[2/3] Setting up Stable Diffusion API server..." -ForegroundColor Cyan
    
    # Check if Python is available
    $pythonAvailable = $false
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
            $pythonAvailable = $true
        }
    } catch {
        Write-Host "  ✗ Python not found" -ForegroundColor Red
    }
    
    if (-not $pythonAvailable) {
        Write-Host "`n  Python is required for Stable Diffusion API server." -ForegroundColor Yellow
        Write-Host "  Download Python from: https://www.python.org/downloads/" -ForegroundColor White
        Write-Host "  Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    } else {
        # Check if stable-diffusion-api-server is already installed
        $sdApiInstalled = $false
        try {
            $result = python -m pip show stable-diffusion-api-server 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ stable-diffusion-api-server is installed" -ForegroundColor Green
                $sdApiInstalled = $true
            }
        } catch {
            # Not installed
        }
        
        if (-not $sdApiInstalled) {
            Write-Host "  Installing stable-diffusion-api-server..." -ForegroundColor Yellow
            try {
                python -m pip install stable-diffusion-api-server
                Write-Host "  ✓ Installation complete" -ForegroundColor Green
            } catch {
                Write-Host "  ✗ Installation failed: $_" -ForegroundColor Red
                Write-Host "  Try manually: python -m pip install stable-diffusion-api-server" -ForegroundColor Yellow
            }
        }
        
        # Determine best drive for model storage (not C: or D:)
        $availableDrives = Get-PSDrive -PSProvider FileSystem | Where-Object { 
            $_.Name -ne "C" -and $_.Name -ne "D" -and $_.Free -gt 10GB 
        } | Sort-Object Free -Descending
        
        if ($availableDrives) {
            $bestDrive = $availableDrives[0].Name
            $modelPath = "${bestDrive}:\StableDiffusion\Models"
            
            Write-Host "`n  Configuring model storage location..." -ForegroundColor Cyan
            Write-Host "    Selected drive: $bestDrive (Free: $([math]::Round($availableDrives[0].Free/1GB, 2)) GB)" -ForegroundColor Green
            Write-Host "    Model path: $modelPath" -ForegroundColor White
            
            # Create directory if it doesn't exist
            if (-not (Test-Path $modelPath)) {
                try {
                    New-Item -ItemType Directory -Path $modelPath -Force | Out-Null
                    Write-Host "    ✓ Created directory: $modelPath" -ForegroundColor Green
                } catch {
                    Write-Host "    ⚠ Could not create directory: $_" -ForegroundColor Yellow
                }
            }
            
            # Set HF_HOME for current session
            $env:HF_HOME = $modelPath
            Write-Host "    ✓ Set HF_HOME for current session: $modelPath" -ForegroundColor Green
            
            # Offer to set permanently
            Write-Host "`n  To set permanently (run as Administrator):" -ForegroundColor Yellow
            Write-Host "    [System.Environment]::SetEnvironmentVariable('HF_HOME', '$modelPath', 'User')" -ForegroundColor White
            
            # Create startup script
            $startupScript = Join-Path $PSScriptRoot "Start-StableDiffusionServer.ps1"
            $startupScriptContent = @"
# Start-StableDiffusionServer.ps1
# Starts Stable Diffusion API server with model storage on non-C/D drive

`$env:HF_HOME = "$modelPath"

Write-Host "Starting Stable Diffusion API server..." -ForegroundColor Cyan
Write-Host "Model storage: `$env:HF_HOME" -ForegroundColor Gray

stable-diffusion-api-server
"@
            Set-Content -Path $startupScript -Value $startupScriptContent -Encoding UTF8
            Write-Host "    ✓ Created startup script: $startupScript" -ForegroundColor Green
        } else {
            Write-Host "`n  ⚠ WARNING: No suitable drive found (need >10GB free, not C: or D:)" -ForegroundColor Red
            Write-Host "     Models will download to default location (usually C: or D:)" -ForegroundColor Yellow
        }
        
        Write-Host "`n  To start the API server, run:" -ForegroundColor Yellow
        Write-Host "    .\Start-StableDiffusionServer.ps1" -ForegroundColor White
        Write-Host "`n  Or manually:" -ForegroundColor Gray
        Write-Host "    stable-diffusion-api-server" -ForegroundColor White
        Write-Host "`n  Or with custom port:" -ForegroundColor Gray
        Write-Host "    stable-diffusion-api-server --port 8000" -ForegroundColor White
        Write-Host "`n  ⚠ IMPORTANT: Stable Diffusion models can be several GB each" -ForegroundColor Red
        Write-Host "     Make sure to use the startup script or set HF_HOME before downloading models" -ForegroundColor Yellow
        Write-Host "`n  The server will be available at: http://localhost:8000" -ForegroundColor Cyan
    }
}

# ============================================================
# 3. PYTHON DEPENDENCIES
# ============================================================

if ($InstallPythonDependencies) {
    Write-Host "`n[3/3] Installing Python dependencies..." -ForegroundColor Cyan
    
    # Check if Python is available
    $pythonAvailable = $false
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Python found: $pythonVersion" -ForegroundColor Green
            $pythonAvailable = $true
        }
    } catch {
        Write-Host "  ✗ Python not found" -ForegroundColor Red
        Write-Host "  Download Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
    
    if ($pythonAvailable) {
        $sharedPath = Join-Path $PSScriptRoot "Shared"
        $requirementsFile = Join-Path $sharedPath "requirements.txt"
        
        # Create requirements.txt if it doesn't exist
        if (-not (Test-Path $requirementsFile)) {
            Write-Host "  Creating requirements.txt..." -ForegroundColor Yellow
            $requirements = @(
                "requests>=2.31.0",
                "typing-extensions>=4.8.0"
            )
            $requirements | Out-File -FilePath $requirementsFile -Encoding UTF8
            Write-Host "  ✓ Created requirements.txt" -ForegroundColor Green
        }
        
        Write-Host "  Installing dependencies from requirements.txt..." -ForegroundColor Yellow
        try {
            python -m pip install -r $requirementsFile
            Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ Installation failed: $_" -ForegroundColor Red
            Write-Host "  Try manually: python -m pip install requests typing-extensions" -ForegroundColor Yellow
        }
    }
}

# ============================================================
# SUMMARY
# ============================================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Setup Summary" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Required tools:" -ForegroundColor Yellow
Write-Host "  1. Ollama (http://localhost:11434)" -ForegroundColor White
Write-Host "     - Download: https://ollama.com" -ForegroundColor Gray
Write-Host "     - Models: llama3.1:8b, wizardlm-uncensored:latest, deepseek-r1:7b" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Stable Diffusion API Server (http://localhost:8000)" -ForegroundColor White
Write-Host "     - Install: python -m pip install stable-diffusion-api-server" -ForegroundColor Gray
Write-Host "     - Run: stable-diffusion-api-server" -ForegroundColor Gray
Write-Host "     - Setup: https://github.com/cantrell/stable-diffusion-api-server" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Python dependencies" -ForegroundColor White
Write-Host "     - requests, typing-extensions" -ForegroundColor Gray
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Install Ollama and download models (if not done)" -ForegroundColor White
Write-Host "  2. Start Stable Diffusion API server" -ForegroundColor White
Write-Host "  3. Run UncensoredCharacterImageGenerator.ps1" -ForegroundColor White
Write-Host ""
