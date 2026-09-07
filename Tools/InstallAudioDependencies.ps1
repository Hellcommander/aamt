<#
.SYNOPSIS
    Installs required Python dependencies for audio generation across all toolsets.

.DESCRIPTION
    This script installs all required and optional dependencies for:
    - Elin Spell Audio Generator
    - Qud Audio Generator
    - Terraria Portal Audio Generator
    - Starbound Audio Generator
    - Shared Audio Quality Assessment System

.PARAMETER InstallOptional
    Also install optional dependencies (torch, transformers, whisper) for advanced quality assessment.

.PARAMETER PythonPath
    Path to Python executable (auto-detected if not specified).

.PARAMETER InstallPath
    Custom installation directory for packages (avoids C: and D: drives).
    If not specified, packages install to default Python site-packages.

.PARAMETER UseVirtualEnv
    Create a virtual environment in InstallPath instead of installing to system Python.

.EXAMPLE
    .\InstallAudioDependencies.ps1

.EXAMPLE
    .\InstallAudioDependencies.ps1 -InstallOptional

.EXAMPLE
    .\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages"

.EXAMPLE
    .\InstallAudioDependencies.ps1 -InstallPath "E:\PythonPackages" -UseVirtualEnv
#>

[CmdletBinding()]
param(
    [switch]$InstallOptional,
    [string]$PythonPath = "",
    [string]$InstallPath = "",
    [switch]$UseVirtualEnv
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Audio Generation Dependencies Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Import unified tool detection
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
$toolDetectionPath = Join-Path $sharedPath "ToolDetection.psm1"
if (Test-Path $toolDetectionPath) {
    Import-Module $toolDetectionPath -ErrorAction SilentlyContinue
}

# Detect Python
if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonPath = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $PythonPath = "python3"
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonPath = "py"
    } else {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Python 3.8 or later from:" -ForegroundColor Yellow
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Or specify Python path with -PythonPath parameter" -ForegroundColor Yellow
        exit 1
    }
}

# Verify Python version
Write-Host "Detected Python: $PythonPath" -ForegroundColor Green
$pythonVersion = & $PythonPath --version 2>&1
Write-Host "Version: $pythonVersion" -ForegroundColor Gray
Write-Host ""

# Handle custom installation path
$originalPythonPath = $PythonPath
$virtualEnvPath = $null
if (-not [string]::IsNullOrWhiteSpace($InstallPath)) {
    $InstallPath = [System.IO.Path]::GetFullPath($InstallPath)
    
    if ($UseVirtualEnv) {
        Write-Host "Creating virtual environment in: $InstallPath" -ForegroundColor Cyan
        if (-not (Test-Path $InstallPath)) {
            New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        }
        
        # Create virtual environment
        & $PythonPath -m venv $InstallPath 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to create virtual environment!" -ForegroundColor Red
            exit 1
        }
        
        # Use virtual environment's Python
        if ($IsWindows -or $env:OS -like "*Windows*") {
            $PythonPath = Join-Path $InstallPath "Scripts\python.exe"
        } else {
            $PythonPath = Join-Path $InstallPath "bin\python"
        }
        
        if (-not (Test-Path $PythonPath)) {
            Write-Host "ERROR: Virtual environment Python not found at: $PythonPath" -ForegroundColor Red
            exit 1
        }
        
        $virtualEnvPath = $InstallPath
        Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
        Write-Host "  Using Python: $PythonPath" -ForegroundColor Gray
    } else {
        Write-Host "Installing packages to custom directory: $InstallPath" -ForegroundColor Cyan
        if (-not (Test-Path $InstallPath)) {
            New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
        }
        Write-Host "  Note: You may need to add this directory to PYTHONPATH" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Check pip
Write-Host "Checking pip..." -ForegroundColor Cyan
try {
    $pipVersion = & $PythonPath -m pip --version 2>&1
    Write-Host "  $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: pip not available!" -ForegroundColor Red
    Write-Host "Please install pip or reinstall Python with pip included." -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Cyan
try {
    & $PythonPath -m pip install --upgrade pip --quiet
    Write-Host "  ✓ pip upgraded" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Warning: Could not upgrade pip (continuing anyway)" -ForegroundColor Yellow
}
Write-Host ""

# Required packages
$requiredPackages = @(
    @{Name="numpy"; MinVersion="1.20.0"},
    @{Name="soundfile"; MinVersion="0.10.0"}
)

# Optional but recommended packages
$recommendedPackages = @(
    @{Name="scipy"; MinVersion="1.7.0"}
)

# Optional packages for quality assessment
$optionalPackages = @(
    @{Name="librosa"; MinVersion="0.9.0"},
    @{Name="requests"; MinVersion="2.25.0"}
)

# Advanced optional packages (large downloads)
$advancedPackages = @(
    @{Name="torch"; MinVersion="2.0.0"},
    @{Name="torchaudio"; MinVersion="2.0.0"},
    @{Name="transformers"; MinVersion="4.20.0"},
    @{Name="openai-whisper"; MinVersion="20230314"}
)

function Install-Package {
    param(
        [string]$PackageName,
        [string]$MinVersion = ""
    )
    
    Write-Host "Installing $PackageName..." -ForegroundColor Cyan
    
    try {
        $installArgs = @()
        if ($MinVersion) {
            $installArgs += "${PackageName}>=${MinVersion}"
        } else {
            $installArgs += $PackageName
        }
        
        # Use custom install path if specified (and not using virtual env)
        if (-not [string]::IsNullOrWhiteSpace($InstallPath) -and -not $UseVirtualEnv) {
            $installArgs += "--target", $InstallPath
        }
        
        & $PythonPath -m pip install $installArgs 2>&1 | Out-Null
        
        # Verify installation
        $result = & $PythonPath -c "import $($PackageName.Replace('-', '_')); print($($PackageName.Replace('-', '_')).__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $PackageName installed (version: $result)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ⚠ $PackageName installed but version check failed" -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  ✗ Failed to install $PackageName" -ForegroundColor Red
        Write-Host "    Error: $_" -ForegroundColor Gray
        return $false
    }
}

# Install required packages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Required Packages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$requiredFailed = @()
foreach ($package in $requiredPackages) {
    if (-not (Install-Package -PackageName $package.Name -MinVersion $package.MinVersion)) {
        $requiredFailed += $package.Name
    }
}

if ($requiredFailed.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to install required packages: $($requiredFailed -join ', ')" -ForegroundColor Red
    Write-Host "Please install them manually:" -ForegroundColor Yellow
    Write-Host "  $PythonPath -m pip install $($requiredFailed -join ' ')" -ForegroundColor Cyan
    exit 1
}

Write-Host ""

# Install recommended packages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Recommended Packages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($package in $recommendedPackages) {
    Install-Package -PackageName $package.Name -MinVersion $package.MinVersion | Out-Null
}

Write-Host ""

# Install optional packages
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Optional Packages" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($package in $optionalPackages) {
    Install-Package -PackageName $package.Name -MinVersion $package.MinVersion | Out-Null
}

Write-Host ""

# Install advanced packages if requested
if ($InstallOptional) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Installing Advanced Packages" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Warning: These packages are large (several GB) and may take a while to download." -ForegroundColor Yellow
    Write-Host ""
    
    # Non-interactive safe: if there's no interactive console, proceed (the caller
    # already opted in via -InstallOptional) rather than hanging on a prompt.
    $__interactive = ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and $env:AAMT_NONINTERACTIVE -ne '1')
    if ($__interactive) {
        $continue = Read-Host "Continue with advanced package installation? (y/N)"
    } else {
        Write-Host "Non-interactive: proceeding with advanced packages (-InstallOptional was set)." -ForegroundColor Gray
        $continue = 'y'
    }
    if ($continue -eq 'y' -or $continue -eq 'Y') {
        foreach ($package in $advancedPackages) {
            Install-Package -PackageName $package.Name -MinVersion $package.MinVersion | Out-Null
        }
    } else {
        Write-Host "Skipping advanced packages." -ForegroundColor Gray
    }
    Write-Host ""
} else {
    Write-Host "Advanced packages (torch, transformers, whisper) skipped." -ForegroundColor Gray
    Write-Host "Use -InstallOptional to install them (large downloads)." -ForegroundColor Gray
    Write-Host ""
}

# Verify installation
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verifying Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$verificationScript = @"
import sys
packages = {
    'numpy': 'numpy',
    'soundfile': 'soundfile',
    'scipy': 'scipy',
    'librosa': 'librosa',
    'requests': 'requests'
}

print('Required packages:')
for name, import_name in packages.items():
    try:
        mod = __import__(import_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f'  ✓ {name}: {version}')
    except ImportError:
        print(f'  ✗ {name}: NOT INSTALLED')

# Check optional advanced packages
advanced = {
    'torch': 'torch',
    'transformers': 'transformers',
    'whisper': 'whisper'
}

print('\nAdvanced packages (optional):')
for name, import_name in advanced.items():
    try:
        mod = __import__(import_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f'  ✓ {name}: {version}')
    except ImportError:
        print(f'  ⚠ {name}: not installed (optional)')
"@

$verificationScript | & $PythonPath -
$verifyExitCode = $LASTEXITCODE

Write-Host ""

if ($verifyExitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    # Show installation location info
    if (-not [string]::IsNullOrWhiteSpace($InstallPath)) {
        if ($UseVirtualEnv) {
            Write-Host "Virtual environment created at: $InstallPath" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "To use this virtual environment, activate it first:" -ForegroundColor Yellow
            if ($IsWindows -or $env:OS -like "*Windows*") {
                Write-Host "  & '$InstallPath\Scripts\Activate.ps1'" -ForegroundColor Gray
            } else {
                Write-Host "  source $InstallPath/bin/activate" -ForegroundColor Gray
            }
            Write-Host ""
        } else {
            Write-Host "Packages installed to: $InstallPath" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "To use these packages, add to PYTHONPATH:" -ForegroundColor Yellow
            Write-Host "  `$env:PYTHONPATH = `"$InstallPath`"" -ForegroundColor Gray
            Write-Host ""
            Write-Host "Or set it permanently:" -ForegroundColor Yellow
            Write-Host "  [Environment]::SetEnvironmentVariable('PYTHONPATH', '$InstallPath', 'User')" -ForegroundColor Gray
            Write-Host ""
        }
    }
    
    Write-Host "You can now use audio generators for:" -ForegroundColor Cyan
    Write-Host "  - Elin Spell Audio Generator" -ForegroundColor Gray
    Write-Host "  - Qud Audio Generator" -ForegroundColor Gray
    Write-Host "  - Terraria Portal Audio Generator" -ForegroundColor Gray
    Write-Host "  - Starbound Audio Generator" -ForegroundColor Gray
    Write-Host ""
    Write-Host "For advanced quality assessment, install optional packages with:" -ForegroundColor Yellow
    if (-not [string]::IsNullOrWhiteSpace($InstallPath)) {
        Write-Host "  .\InstallAudioDependencies.ps1 -InstallOptional -InstallPath `"$InstallPath`"" -ForegroundColor Cyan
        if ($UseVirtualEnv) {
            Write-Host "    (or activate virtual env and run: pip install torch transformers openai-whisper)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  .\InstallAudioDependencies.ps1 -InstallOptional" -ForegroundColor Cyan
    }
} else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Installation completed with warnings" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Some packages may not be properly installed." -ForegroundColor Yellow
    Write-Host "Please check the output above for errors." -ForegroundColor Yellow
}

Write-Host ""
