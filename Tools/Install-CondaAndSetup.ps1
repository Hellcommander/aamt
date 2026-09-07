# Install-CondaAndSetup.ps1
# AI-Assisted Modding Tools (AAMT)
# Installs Miniconda to E:\tools\miniconda3 and sets up stable-diffusion-api-server environment

$ErrorActionPreference = "Stop"

# Configuration
$toolsDir = "E:\tools"
$condaInstallPath = "$toolsDir\miniconda3"
$serverPath = "$toolsDir\stable-diffusion-api-server"
$envName = "sd-api-server"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Conda & Stable Diffusion Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if conda is already installed
Write-Host "[STEP 1] Checking for existing conda installation..." -ForegroundColor Yellow
$condaExists = $false
$condaPath = $null

if (Get-Command conda -ErrorAction SilentlyContinue) {
    $condaBase = & conda info --base 2>&1
    if ($LASTEXITCODE -eq 0) {
        $condaBase = $condaBase.Trim()
        Write-Host "  [OK] Found conda at: $condaBase" -ForegroundColor Green
        $condaExists = $true
        $condaPath = $condaBase
    }
} elseif (Test-Path $condaInstallPath) {
    Write-Host "  [OK] Found conda installation at: $condaInstallPath" -ForegroundColor Green
    $condaExists = $true
    $condaPath = $condaInstallPath
    # Add to PATH for this session
    $env:Path = "$condaInstallPath;$condaInstallPath\Scripts;$condaInstallPath\Library\bin;$env:Path"
}

# Step 2: Install Miniconda if needed
if (-not $condaExists) {
    Write-Host "[STEP 2] Installing Miniconda to $condaInstallPath..." -ForegroundColor Yellow
    
    # Create tools directory if it doesn't exist
    if (-not (Test-Path $toolsDir)) {
        New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
        Write-Host "  Created directory: $toolsDir" -ForegroundColor Gray
    }
    
    # Download Miniconda installer
    $minicondaUrl = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
    $installerPath = "$env:TEMP\Miniconda3-latest-Windows-x86_64.exe"
    
    Write-Host "  Downloading Miniconda installer..." -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $minicondaUrl -OutFile $installerPath -UseBasicParsing
        Write-Host "  [OK] Download complete" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Failed to download Miniconda: $_" -ForegroundColor Red
        Write-Host "  Please download manually from: https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Yellow
        exit 1
    }
    
    # Install Miniconda silently
    Write-Host "  Installing Miniconda (this may take a few minutes)..." -ForegroundColor Gray
    $installArgs = @(
        "/InstallationType=JustMe",
        "/RegisterPython=0",
        "/S",
        "/D=$condaInstallPath"
    )
    
    $process = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
    
    if ($process.ExitCode -eq 0) {
        Write-Host "  [OK] Miniconda installed successfully" -ForegroundColor Green
        $condaPath = $condaInstallPath
        # Add to PATH for this session
        $env:Path = "$condaInstallPath;$condaInstallPath\Scripts;$condaInstallPath\Library\bin;$env:Path"
    } else {
        Write-Host "  [FAIL] Installation failed with exit code: $($process.ExitCode)" -ForegroundColor Red
        exit 1
    }
    
    # Clean up installer
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "[STEP 2] Conda already installed, skipping..." -ForegroundColor Gray
}

# Step 3: Initialize conda for PowerShell
Write-Host "[STEP 3] Initializing conda for PowerShell..." -ForegroundColor Yellow
$condaExe = Join-Path $condaPath "Scripts\conda.exe"
if (Test-Path $condaExe) {
    # Initialize conda
    & $condaExe init powershell 2>&1 | Out-Null
    Write-Host "  [OK] Conda initialized" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find conda.exe at expected location" -ForegroundColor Yellow
}

# Step 4: Verify conda works
Write-Host "[STEP 4] Verifying conda installation..." -ForegroundColor Yellow
# Try to use conda directly
$condaVersion = $null
if (Test-Path $condaExe) {
    $condaVersion = & $condaExe --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Conda version: $condaVersion" -ForegroundColor Green
    }
} 

# Also try conda command if in PATH
if (-not $condaVersion) {
    $condaVersion = & conda --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Conda version: $condaVersion" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Conda command not in PATH" -ForegroundColor Yellow
        Write-Host "  Using conda.exe directly from: $condaExe" -ForegroundColor Gray
        # Set conda function for this session
        $script:condaCmd = $condaExe
    }
}

# Step 5: Check if server directory exists
Write-Host "[STEP 5] Checking for stable-diffusion-api-server..." -ForegroundColor Yellow
if (-not (Test-Path $serverPath)) {
    Write-Host "  [WARN] Server directory not found at: $serverPath" -ForegroundColor Yellow
    Write-Host "  Please clone the repository first:" -ForegroundColor Yellow
    Write-Host "    git clone https://github.com/cantrell/stable-diffusion-api-server.git $serverPath" -ForegroundColor Gray
    exit 1
}

$envYaml = Join-Path $serverPath "environment.yaml"
if (-not (Test-Path $envYaml)) {
    Write-Host "  [WARN] environment.yaml not found at: $envYaml" -ForegroundColor Yellow
    Write-Host "  Please ensure you have cloned the stable-diffusion-api-server repository" -ForegroundColor Yellow
    exit 1
}

Write-Host "  [OK] Server found at: $serverPath" -ForegroundColor Green

# Step 6: Accept conda Terms of Service (required for newer conda versions)
Write-Host "[STEP 6] Accepting conda Terms of Service..." -ForegroundColor Yellow
$condaCmd = if (Get-Command conda -ErrorAction SilentlyContinue) { "conda" } else { $condaExe }

$tosChannels = @(
    "https://repo.anaconda.com/pkgs/main",
    "https://repo.anaconda.com/pkgs/r",
    "https://repo.anaconda.com/pkgs/msys2"
)

foreach ($channel in $tosChannels) {
    if ($condaCmd -eq "conda") {
        & conda tos accept --override-channels --channel $channel 2>&1 | Out-Null
    } else {
        & $condaCmd tos accept --override-channels --channel $channel 2>&1 | Out-Null
    }
}
Write-Host "  [OK] Terms of Service accepted" -ForegroundColor Green

# Step 7: Create conda environment
Write-Host "[STEP 7] Creating conda environment '$envName'..." -ForegroundColor Yellow

# Check if environment already exists
$envList = if ($condaCmd -eq "conda") { 
    & conda env list 2>&1 
} else { 
    & $condaCmd env list 2>&1 
}
$envExists = $envList | Select-String $envName
if ($envExists) {
    Write-Host "  [INFO] Environment '$envName' already exists" -ForegroundColor Gray
    # Non-interactive safe: default to NON-destructive (keep existing env) so
    # unattended runs never hang and never destroy an existing environment.
    $__interactive = ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and $env:AAMT_NONINTERACTIVE -ne '1')
    if ($__interactive) {
        $response = Read-Host "  Do you want to recreate it? (y/N)"
    } else {
        Write-Host "  Non-interactive: keeping existing environment (no recreate)." -ForegroundColor Gray
        $response = 'N'
    }
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "  Removing existing environment..." -ForegroundColor Gray
        if ($condaCmd -eq "conda") {
            & conda env remove -n $envName -y 2>&1 | Out-Null
        } else {
            & $condaCmd env remove -n $envName -y 2>&1 | Out-Null
        }
    } else {
        Write-Host "  [OK] Using existing environment" -ForegroundColor Green
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  Setup Complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To start the server, run:" -ForegroundColor Yellow
        Write-Host "  .\Start-StableDiffusionServer.ps1" -ForegroundColor Cyan
        exit 0
    }
}

Push-Location $serverPath
Write-Host "  Creating environment from environment.yaml..." -ForegroundColor Gray
if ($condaCmd -eq "conda") {
    $createResult = & conda env create -f environment.yaml 2>&1
} else {
    $createResult = & $condaCmd env create -f environment.yaml 2>&1
}
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Environment created successfully" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Failed to create environment" -ForegroundColor Red
    Write-Host $createResult -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Step 8: Verify environment
Write-Host "[STEP 8] Verifying environment..." -ForegroundColor Yellow
if ($condaCmd -eq "conda") {
    $verifyResult = & conda run -n $envName python --version 2>&1
} else {
    $verifyResult = & $condaCmd run -n $envName python --version 2>&1
}
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Environment verified: $verifyResult" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not verify environment" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Conda installed to: $condaPath" -ForegroundColor Gray
Write-Host "Environment created: $envName" -ForegroundColor Gray
Write-Host ""
Write-Host "To start the server, run:" -ForegroundColor Yellow
Write-Host "  .\Start-StableDiffusionServer.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: You may need to restart PowerShell for conda to be fully available." -ForegroundColor Yellow
