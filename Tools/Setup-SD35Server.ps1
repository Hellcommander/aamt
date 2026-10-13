# Setup-SD35Server.ps1
# Downloads and sets up SD3.5 from GitHub and Hugging Face to replace current SD server

param(
    [string]$InstallPath = "E:\tools\sd3.5",
    [switch]$SkipModelDownload
)

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "SD3.5 Server Setup and Installation" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
    $pythonVersion = python3 --version 2>&1
    Write-Host "  [OK] Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Python not found!" -ForegroundColor Red
    Write-Host "  Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check Git
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] Git found" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Git not found - will need to download manually" -ForegroundColor Yellow
}

# Check Hugging Face CLI (optional, for model download)
$hfCliAvailable = $false
$hfCliCmd = $null
if (Get-Command hf -ErrorAction SilentlyContinue) {
    $hfCliAvailable = $true
    $hfCliCmd = "hf"
    Write-Host "  [OK] Hugging Face CLI found (hf)" -ForegroundColor Green
} elseif (Get-Command huggingface-cli -ErrorAction SilentlyContinue) {
    $hfCliAvailable = $true
    $hfCliCmd = "huggingface-cli"
    Write-Host "  [OK] Hugging Face CLI found (huggingface-cli)" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Hugging Face CLI not found (will use Python to download)" -ForegroundColor Gray
    Write-Host "  [INFO] Install with: pip install -U huggingface-hub" -ForegroundColor Gray
}

# Auto-switch to media download token by name (SD3.5 Token)
$tokenSwitch = Join-Path $PSScriptRoot "Shared\HfTokenSwitch.psm1"
if (Test-Path $tokenSwitch) {
    Import-Module $tokenSwitch -Force
    try {
        Use-AamtHfMediaToken | Out-Null
    } catch {
        Write-Host "  [WARN] Could not auto-switch HF token: $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# Create installation directory
Write-Host "Setting up installation directory..." -ForegroundColor Yellow
if (-not (Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Host "  [OK] Created directory: $InstallPath" -ForegroundColor Green
} else {
    Write-Host "  [OK] Directory exists: $InstallPath" -ForegroundColor Green
}

# Step 1: Clone/download GitHub repository
Write-Host ""
Write-Host "Step 1: Downloading SD3.5 code from GitHub..." -ForegroundColor Cyan
$repoPath = Join-Path $InstallPath "sd3.5"
$repoUrl = "https://github.com/Stability-AI/sd3.5.git"

if (Test-Path $repoPath) {
    Write-Host "  [INFO] Repository directory exists, checking if it's a git repo..." -ForegroundColor Gray
    Push-Location $repoPath
    $isGitRepo = git rev-parse --git-dir 2>&1
    Pop-Location
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Git repository found, updating..." -ForegroundColor Green
        Push-Location $repoPath
        git pull
        Pop-Location
    } else {
        Write-Host "  [WARN] Directory exists but is not a git repo, removing..." -ForegroundColor Yellow
        Remove-Item -Path $repoPath -Recurse -Force
    }
}

if (-not (Test-Path $repoPath)) {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "  Cloning repository..." -ForegroundColor Gray
        git clone $repoUrl $repoPath
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Repository cloned successfully" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] Failed to clone repository" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  [ERROR] Git not available. Please install Git or download manually:" -ForegroundColor Red
        Write-Host "    1. Download from: $repoUrl" -ForegroundColor Yellow
        Write-Host "    2. Extract to: $repoPath" -ForegroundColor Yellow
        exit 1
    }
}

# Step 2: Install Python dependencies
Write-Host ""
Write-Host "Step 2: Installing Python dependencies..." -ForegroundColor Cyan
Write-Host "  Installing Diffusers library and dependencies..." -ForegroundColor Gray
& $pythonCmd -m pip install -U diffusers transformers accelerate safetensors
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Diffusers dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Some dependencies may have failed to install" -ForegroundColor Yellow
}

# Also install requirements.txt if it exists (for compatibility)
$requirementsFile = Join-Path $repoPath "requirements.txt"
if (Test-Path $requirementsFile) {
    Write-Host "  Installing additional requirements from requirements.txt..." -ForegroundColor Gray
    & $pythonCmd -m pip install -r $requirementsFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Additional dependencies installed" -ForegroundColor Green
    }
}

# Step 3: Download SD3.5 Medium model using Hugging Face CLI
Write-Host ""
Write-Host "Step 3: SD3.5 Medium Model Download" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "Before continuing, make sure you have:" -ForegroundColor Yellow
Write-Host "  1. Installed Hugging Face CLI (hf or huggingface-cli)" -ForegroundColor Gray
Write-Host "  2. Logged in locally using: hf auth login" -ForegroundColor Gray
Write-Host "  3. Accepted the SD3.5 Medium license on HuggingFace" -ForegroundColor Gray
Write-Host ""
Write-Host "Press ENTER to continue..." -ForegroundColor Yellow
$null = Read-Host

# Ensure model directory exists
$modelsPath = Join-Path $repoPath "models"
if (-not (Test-Path $modelsPath)) {
    New-Item -ItemType Directory -Path $modelsPath -Force | Out-Null
}

# Detect Hugging Face CLI
$hfCliCmd = $null
if (Get-Command hf -ErrorAction SilentlyContinue) {
    $hfCliCmd = "hf"
} elseif (Get-Command huggingface-cli -ErrorAction SilentlyContinue) {
    $hfCliCmd = "huggingface-cli"
} else {
    Write-Host "  [ERROR] Hugging Face CLI not installed." -ForegroundColor Red
    Write-Host "  Install it with:" -ForegroundColor Yellow
    Write-Host "    pip install hf-cli" -ForegroundColor Gray
    Write-Host "    or: pip install huggingface_hub" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "Using Hugging Face CLI: $hfCliCmd" -ForegroundColor Gray
Write-Host "Downloading SD3.5 Medium model files..." -ForegroundColor Cyan

# Correct filenames from the SD3.5 Medium repo
$files = @(
    "sd3.5-medium.safetensors",
    "sd3.5-medium-vae.safetensors",
    "text_encoder_1.safetensors",
    "text_encoder_2.safetensors"
)

foreach ($file in $files) {
    Write-Host "  Downloading: $file" -ForegroundColor Gray
    & $hfCliCmd download stabilityai/stable-diffusion-3.5-medium $file --local-dir $modelsPath

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to download: $file" -ForegroundColor Red
        Write-Host "  Make sure you ran: hf auth login" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "  [OK] SD3.5 Medium model downloaded successfully." -ForegroundColor Green
Write-Host "  Model directory: $modelsPath" -ForegroundColor Gray

# Step 4: Create API server wrapper
Write-Host ""
Write-Host "Step 4: Creating API server wrapper..." -ForegroundColor Cyan
$serverPy = Join-Path $repoPath "server.py"

# Read the actual sd3_infer.py to understand the interface
$inferPy = Join-Path $repoPath "sd3_infer.py"
if (Test-Path $inferPy) {
    Write-Host "  Reading sd3_infer.py to understand interface..." -ForegroundColor Gray
    # We'll create a wrapper that calls sd3_infer.py as a subprocess or imports it
}

$serverContent = @'
#!/usr/bin/env python3
"""
SD3.5 API Server
Wraps SD3.5 inference code to provide HTTP API compatible with OpenAI-style API
Uses HTTP/2 support for compatibility
"""
import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import base64
from io import BytesIO
import traceback

# Add repo path to Python path
repo_path = Path(__file__).parent
sys.path.insert(0, str(repo_path))

class SD35APIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # Will be upgraded to HTTP/2 by client if supported
    
    def __init__(self, *args, **kwargs):
        self.models_path = repo_path / "models"
        self.model_path = self.models_path / "sd3.5_medium.safetensors"
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests (health check, etc.)"""
        if self.path == "/" or self.path == "/health" or self.path == "/ping":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok", 
                "model": "stable-diffusion-3.5-medium",
                "version": "1.0"
            }).encode())
        elif self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "data": [{"id": "stable-diffusion-3.5-medium", "object": "model"}]
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests (image generation)"""
        if self.path == "/v1/images/generations":
            self.handle_image_generation()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_image_generation(self):
        """Handle image generation requests using sd3_infer.py"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode("utf-8"))
            
            prompt = request_data.get("prompt", "")
            width = request_data.get("width", 1024)
            height = request_data.get("height", 1024)
            steps = request_data.get("steps", 40)
            guidance_scale = request_data.get("guidance_scale", 4.5)
            num_outputs = request_data.get("n", 1)
            seed = request_data.get("seed", -1)
            
            # Validate model exists
            if not self.model_path.exists():
                self.send_error(500, "Model file not found. Please download the model.")
                return
            
            print(f"Generating image: {prompt[:50]}... (width={width}, height={height}, steps={steps})")
            
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "output.png"
                
                # Call sd3_infer.py as subprocess
                infer_script = repo_path / "sd3_infer.py"
                cmd = [
                    sys.executable,
                    str(infer_script),
                    "--prompt", prompt,
                    "--model", str(self.model_path),
                    "--width", str(width),
                    "--height", str(height),
                    "--steps", str(steps),
                    "--output", str(output_path)
                ]
                
                if seed != -1:
                    cmd.extend(["--seed", str(seed)])
                
                # Run inference
                result = subprocess.run(
                    cmd,
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode != 0:
                    error_msg = f"Generation failed: {result.stderr}"
                    print(error_msg)
                    self.send_error(500, error_msg)
                    return
                
                # Read generated image
                if not output_path.exists():
                    # Check if output went to default outputs directory
                    outputs_dir = repo_path / "outputs"
                    if outputs_dir.exists():
                        output_files = list(outputs_dir.glob("**/*.png"))
                        if output_files:
                            output_path = output_files[-1]  # Get most recent
                
                if not output_path.exists():
                    self.send_error(500, "Generated image file not found")
                    return
                
                # Read image and convert to base64
                with open(output_path, "rb") as f:
                    image_data = f.read()
                
                img_base64 = base64.b64encode(image_data).decode()
                
                # Create response
                response_data = {
                    "data": [{
                        "b64_json": img_base64,
                        "url": None
                    }]
                }
                
                # Send response
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                
                print(f"Image generated successfully ({len(image_data)} bytes)")
            
        except subprocess.TimeoutExpired:
            self.send_error(504, "Image generation timed out")
        except Exception as e:
            error_msg = f"Image generation failed: {str(e)}"
            print(f"Error: {error_msg}")
            print(traceback.format_exc())
            self.send_error(500, error_msg)
    
    def log_message(self, format, *args):
        """Override to use print instead of stderr"""
        print(f"[{self.address_string()}] {format % args}")

def main():
    parser = argparse.ArgumentParser(description="SD3.5 API Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=1337, help="Port to bind to")
    args = parser.parse_args()
    
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, SD35APIHandler)
    
    print(f"SD3.5 API Server starting on http://{args.host}:{args.port}")
    print("Model: SD3.5 Medium")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    main()
'@

$serverContent | Out-File -FilePath $serverPy -Encoding UTF8
Write-Host "  [OK] Created server.py" -ForegroundColor Green

# Step 5: Update Start-StableDiffusionServer.ps1 to use new location
Write-Host ""
Write-Host "Step 5: Updating server startup script..." -ForegroundColor Cyan
# Script is in Tools directory, Start-StableDiffusionServer.ps1 is also in Tools
$startScriptPath = Join-Path $PSScriptRoot "Start-StableDiffusionServer.ps1"
if (Test-Path $startScriptPath) {
    # Backup original
    $backupPath = "$startScriptPath.backup"
    Copy-Item $startScriptPath $backupPath -Force
    Write-Host "  [OK] Backed up original script to: $backupPath" -ForegroundColor Gray
    
    # Update the script to prioritize SD3.5
    $newStartScript = @"
# Start-StableDiffusionServer.ps1
# AI-Assisted Modding Tools (AAMT)
# Starts SD3.5 API server (updated to use SD3.5 from GitHub)

# SD3.5 installation path
`$sd35Path = "$repoPath"
`$sd35Server = Join-Path `$sd35Path "server.py"

# Check if SD3.5 server exists
if (Test-Path `$sd35Server) {
    Write-Host "Starting SD3.5 API Server..." -ForegroundColor Cyan
    Write-Host "Server: `$sd35Server" -ForegroundColor Gray
    Write-Host ""
    
    # Check if Python is available
    `$pythonCmd = `$null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        `$pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        `$pythonCmd = "python3"
    } else {
        Write-Host "❌ ERROR: Python not found!" -ForegroundColor Red
        exit 1
    }
    
    Push-Location `$sd35Path
    & `$pythonCmd server.py --host localhost --port 1337
    Pop-Location
    exit 0
}

# Fallback to old server detection (from original script)
Write-Host "SD3.5 server not found, trying legacy server..." -ForegroundColor Yellow

# Determine best drive for model storage (not C: or D:)
`$availableDrives = Get-PSDrive -PSProvider FileSystem | Where-Object { 
    `$_.Name -ne "C" -and `$_.Name -ne "D" -and `$_.Free -gt 10GB 
} | Sort-Object Free -Descending

if (`$availableDrives) {
    `$bestDrive = `$availableDrives[0].Name
    `$modelPath = "`${bestDrive}:\StableDiffusion\Models"
    
    if (-not (Test-Path `$modelPath)) {
        New-Item -ItemType Directory -Path `$modelPath -Force | Out-Null
    }
    
    `$env:HF_HOME = `$modelPath
    Write-Host "Model storage: `$env:HF_HOME" -ForegroundColor Gray
}

# Try to find legacy server
`$serverStarted = `$false
`$commonPaths = @(
    "E:\tools\stable-diffusion-api-server",
    "`$env:USERPROFILE\stable-diffusion-api-server"
)

foreach (`$path in `$commonPaths) {
    `$serverPy = Join-Path `$path "server.py"
    if (Test-Path `$serverPy) {
        Write-Host "Found legacy server at: `$serverPy" -ForegroundColor Green
        Push-Location `$path
        & `$pythonCmd server.py
        Pop-Location
        `$serverStarted = `$true
        break
    }
}

if (-not `$serverStarted) {
    Write-Host "❌ ERROR: No SD server found!" -ForegroundColor Red
    Write-Host "Run Setup-SD35Server.ps1 to install SD3.5" -ForegroundColor Yellow
    exit 1
}
"@
    
    $newStartScript | Out-File -FilePath $startScriptPath -Encoding UTF8
    Write-Host "  [OK] Updated Start-StableDiffusionServer.ps1" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Start-StableDiffusionServer.ps1 not found at expected location" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "SD3.5 Server Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installation location: $repoPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the server, run:" -ForegroundColor Yellow
Write-Host "  .\Start-StableDiffusionServer.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or manually:" -ForegroundColor Yellow
Write-Host "  cd $repoPath" -ForegroundColor White
Write-Host "  python server.py --host localhost --port 1337" -ForegroundColor White
Write-Host ""
