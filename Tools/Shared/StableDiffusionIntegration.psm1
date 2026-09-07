<#
.SYNOPSIS
    Shared Stable Diffusion 3.5 Integration Module for AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Provides Stable Diffusion 3.5 Medium integration for high-quality, uncensored asset generation.
    Works with Ollama to enhance prompts before generating images with SD3.5.
    
    Features:
    - Automatic server startup and connection testing
    - OpenAI-compatible API endpoint support (HTTP/2 compatible)
    - Integration with Ollama for prompt enhancement
    - High-quality, uncensored image generation with SD3.5 Medium
    - Supports mutant, creature, and fantasy asset generation without content restrictions
    - Automatic model storage on non-C/D drives
#>

# ============================================================
# CONFIGURATION
# ============================================================

# Common local Stable Diffusion setups and their configurations
$script:KnownSDSetups = @(
    @{
        Name = "AUTOMATIC1111 WebUI"
        Port = 7860
        BaseUrl = "http://localhost:7860"
        ApiEndpoint = "/sdapi/v1/txt2img"
        HealthEndpoint = "/sdapi/v1/sd-models"
        Type = "A1111"
    },
    @{
        Name = "ComfyUI"
        Port = 8188
        BaseUrl = "http://localhost:8188"
        ApiEndpoint = "/prompt"
        HealthEndpoint = "/system_stats"
        Type = "ComfyUI"
    },
    @{
        Name = "SD3.5 API Server"
        Port = 1338
        BaseUrl = "http://localhost:1338"
        ApiEndpoint = "/v1/images/generations"
        HealthEndpoint = "/ping"
        Type = "SD35Server"
    },
    @{
        Name = "Legacy Stable Diffusion API Server (Port 8000)"
        Port = 8000
        BaseUrl = "http://localhost:8000"
        ApiEndpoint = "/v1/images/generations"
        HealthEndpoint = "/ping"
        Type = "APIServer"
    },
    @{
        Name = "InvokeAI"
        Port = 9090
        BaseUrl = "http://localhost:9090"
        ApiEndpoint = "/api/v1/images/generate"
        HealthEndpoint = "/api/v1/app/version"
        Type = "InvokeAI"
    }
)

# Active configuration (will be set by auto-detection)
$script:ActiveSDSetup = $null
$script:StableDiffusionUrl = "http://localhost:1338"  # Default to SD3.5 (uncensored, best for game assets)
$script:StableDiffusionApiUrl = "$script:StableDiffusionUrl/v1/images/generations"
$script:ServerStartupScript = "Start-StableDiffusionServer.ps1"

# Default generation parameters optimized for SD3 Medium
$script:DefaultGenerationParams = @{
    Width = 1024
    Height = 1024
    Steps = 28
    GuidanceScale = 7.0
    NegativePrompt = "blurry, low quality, pixelated, distorted, deformed, bad anatomy, text, watermark, simple, basic"
}

# Generous FINITE read timeout for SD generations. SD3.5 Medium with CPU
# offload can take well over 10 minutes per image; the old 600s cap silently
# discarded slow-but-complete generations. Overridable via env var.
$script:SDHttpTimeoutSec = 3600
if ($env:AAMT_SD_HTTP_TIMEOUT_SEC -and ([int]::TryParse($env:AAMT_SD_HTTP_TIMEOUT_SEC, [ref]([int]$null)))) {
    $script:SDHttpTimeoutSec = [int]$env:AAMT_SD_HTTP_TIMEOUT_SEC
}

# On-disk output cache for the SD3.5 server (mirrors sd_http_client.py salvage).
$script:SDOutputsDir = if ($env:AAMT_SD_OUTPUTS_DIR) { $env:AAMT_SD_OUTPUTS_DIR } else { "E:\tools\sd3.5\sd3.5\outputs" }

# ============================================================
# CORE FUNCTIONS
# ============================================================

function Get-FreeVramMB {
    <#
    .SYNOPSIS
    Returns free GPU VRAM in MB via nvidia-smi, or $null if unavailable.
    .DESCRIPTION
    Lets callers make GPU-aware decisions (run on GPU when there's headroom,
    fall back to CPU offload when VRAM is tight) without starting anything.
    Non-interactive and safe: returns $null on any failure.
    #>
    param([switch]$Total)
    try {
        $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if (-not $smi) { return $null }
        $query = if ($Total) { "memory.total" } else { "memory.free" }
        $out = & nvidia-smi --query-gpu=$query --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        # If multiple GPUs, take the one with the most free memory.
        $vals = @($out | ForEach-Object { ($_ -replace '[^\d]', '') } | Where-Object { $_ } | ForEach-Object { [int]$_ })
        if ($vals.Count -eq 0) { return $null }
        return ($vals | Measure-Object -Maximum).Maximum
    } catch {
        return $null
    }
}

function Test-SdOomError {
    <#
    .SYNOPSIS
    Heuristically detects CUDA/GPU out-of-memory errors from an exception/message.
    #>
    param([string]$Message)
    if ([string]::IsNullOrWhiteSpace($Message)) { return $false }
    $m = $Message.ToLower()
    return ($m -match "out of memory") -or ($m -match "cuda" -and $m -match "memory") -or ($m -match "oom")
}

function Get-SalvagedSdOutput {
    <#
    .SYNOPSIS
    Recovers a finished SD image from the server's on-disk cache when the HTTP
    client timed out but generation actually completed server-side.
    Mirrors sd_http_client.py salvage_server_output (mtime + optional WxH guard).
    #>
    param(
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][datetime]$StartedAt,
        [int]$MaxAgeSec = 14400,
        [int]$Width = 0,
        [int]$Height = 0
    )
    try {
        if (-not (Test-Path $script:SDOutputsDir)) { return $null }
        $candidates = @()
        # Prefer gen_*.png (unique per job) over shared latest.png to avoid cross-batch contamination
        $candidates += Get-ChildItem -Path $script:SDOutputsDir -Filter "gen_*.png" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending
        $latest = Join-Path $script:SDOutputsDir "latest.png"
        if (Test-Path $latest) { $candidates += (Get-Item $latest) }
        $now = Get-Date
        $seen = @{}
        foreach ($src in $candidates) {
            if (-not $src) { continue }
            if ($seen.ContainsKey($src.FullName)) { continue }
            $seen[$src.FullName] = $true
            $age = ($now - $src.LastWriteTime).TotalSeconds
            if ($age -gt $MaxAgeSec) { continue }
            # Must have been (re)written at/after this generation began.
            if ($src.LastWriteTime -lt $StartedAt.AddSeconds(-5)) { continue }
            if ($Width -gt 0 -and $Height -gt 0) {
                try {
                    Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue
                    $img = [System.Drawing.Image]::FromFile($src.FullName)
                    try {
                        if ($img.Width -ne $Width -or $img.Height -ne $Height) { continue }
                    } finally {
                        $img.Dispose()
                    }
                } catch {
                    # If we can't read dimensions, still allow salvage by mtime
                }
            }
            try {
                $outDir = Split-Path -Parent $OutputPath
                if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
                Copy-Item -Path $src.FullName -Destination $OutputPath -Force
                Write-Host "  [OK] Salvaged SD output from server cache: $($src.FullName)" -ForegroundColor Green
                return $OutputPath
            } catch {
                continue
            }
        }
    } catch {
        return $null
    }
    return $null
}

function Find-LocalStableDiffusionServer {
    <#
    .SYNOPSIS
    Auto-detects running local Stable Diffusion servers (including background processes).
    #>
    param([switch]$Verbose)
    
    if ($Verbose) {
        Write-Host "`n  Scanning for local Stable Diffusion servers..." -ForegroundColor Cyan
    }
    
    # First, check for SD3.5 server specifically (priority)
    if ($Verbose) {
        Write-Host "    Checking for SD3.5 server (port 1338)..." -ForegroundColor Gray
    }
    $sd35Processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        $cmdLine -like "*sd3.5*server.py*" -or 
        ($cmdLine -like "*server.py*" -and $cmdLine -like "*1338*")
    }
    if ($sd35Processes) {
        if ($Verbose) {
            Write-Host "    [OK] Found SD3.5 server process" -ForegroundColor Green
        }
        return @{
            BaseUrl = "http://localhost:1338"
            ApiEndpoint = "/v1/images/generations"
            Port = 1338
            Type = "SD35Server"
            Name = "SD3.5 API Server"
        }
    }
    
    # Then check for other background Python processes that might be running SD servers
    # Also extract port numbers from command line arguments
    $detectedPorts = @()
    if ($Verbose) {
        Write-Host "    Checking for other background Python processes..." -ForegroundColor Gray
    }
    
    try {
        $pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
                if ($cmdLine) {
                    $isSDProcess = $cmdLine -like "*stable*diffusion*" -or 
                                   $cmdLine -like "*sd3*" -or
                                   $cmdLine -like "*stable_diffusion_api_server*" -or
                                   $cmdLine -like "*server.py*" -or
                                   $cmdLine -like "*webui*" -or
                                   $cmdLine -like "*comfyui*"
                    
                    if ($isSDProcess) {
                        # Try to extract port from command line arguments
                        # Common patterns: --port 8000, --port=8000, -p 8000, port=8000, :8000
                        if ($cmdLine -match '(?:--port|--port=|port=|:)(\d{4,5})') {
                            $extractedPort = [int]$matches[1]
                            if ($extractedPort -ge 1000 -and $extractedPort -le 65535) {
                                $detectedPorts += $extractedPort
                                if ($Verbose) {
                                    Write-Host "      Found port $extractedPort in process command line" -ForegroundColor Gray
                                }
                            }
                        }
                    }
                    
                    return $isSDProcess
                }
            } catch {
                $false
            }
        }
        
        if ($pythonProcesses) {
            if ($Verbose) {
                Write-Host "    Found $($pythonProcesses.Count) potential SD server process(es)" -ForegroundColor Gray
                if ($detectedPorts.Count -gt 0) {
                    Write-Host "    Detected ports from processes: $($detectedPorts -join ', ')" -ForegroundColor Gray
                }
            }
        }
    } catch {
        # Process detection failed, continue with port scanning
    }
    
    # Check all known ports using netstat (more reliable for background processes)
    # Also check ports detected from process command lines
    $commonPorts = @(7860, 8188, 1338, 8000, 9090, 7861, 7862, 8189, 1337, 8001)
    $allPortsToCheck = ($commonPorts + $detectedPorts) | Select-Object -Unique | Sort-Object
    
    $listeningPorts = @{}
    try {
        $netstatOutput = netstat -ano | Select-String "LISTENING"
        foreach ($line in $netstatOutput) {
            if ($line -match ':(\d+)\s+.*LISTENING') {
                $port = [int]$matches[1]
                # Check if it's a known SD port or a detected port
                if ($port -in $allPortsToCheck) {
                    $listeningPorts[$port] = $true
                    if ($Verbose) {
                        Write-Host "    Port $port is listening" -ForegroundColor Gray
                    }
                }
            }
        }
    } catch {
        # Netstat failed, continue with direct TCP checks
    }
    
    # Also check detected ports directly if they weren't in netstat
    foreach ($port in $detectedPorts) {
        if (-not $listeningPorts.ContainsKey($port)) {
            try {
                $tcpClient = New-Object System.Net.Sockets.TcpClient
                $connectResult = $tcpClient.BeginConnect("localhost", $port, $null, $null)
                $success = $connectResult.AsyncWaitHandle.WaitOne(200, $false)
                if ($success) {
                    try {
                        $tcpClient.EndConnect($connectResult)
                        $tcpClient.Close()
                        $listeningPorts[$port] = $true
                        if ($Verbose) {
                            Write-Host "    Port $port (from process) is listening" -ForegroundColor Gray
                        }
                    } catch {
                        $tcpClient.Close()
                    }
                } else {
                    $tcpClient.Close()
                }
            } catch {
                # Port not available
            }
        }
    }
    
    # Create dynamic setup entries for detected ports that aren't in known setups
    $dynamicSetups = @()
    foreach ($port in $listeningPorts.Keys) {
        $knownPort = $script:KnownSDSetups | Where-Object { $_.Port -eq $port }
        if (-not $knownPort) {
            # This port is listening but not in our known setups - might be a custom API server
            # Check if it responds to API Server endpoints
            $dynamicSetups += @{
                Name = "Stable Diffusion API Server (Port $port)"
                Port = $port
                BaseUrl = "http://localhost:$port"
                ApiEndpoint = "/v1/images/generations"
                HealthEndpoint = "/ping"
                Type = "APIServer"
            }
        }
    }
    
    # Combine known and dynamic setups
    $allSetups = $script:KnownSDSetups + $dynamicSetups
    
    # Now check each known setup (including dynamic ones)
    foreach ($setup in $allSetups) {
        if ($Verbose) {
            Write-Host "    Checking $($setup.Name) on port $($setup.Port)..." -ForegroundColor Gray
        }
        
        # Check if port is listening (from netstat or direct TCP check)
        $portListening = $false
        if ($listeningPorts.ContainsKey($setup.Port)) {
            $portListening = $true
        } else {
            # Direct TCP check
            try {
                $tcpClient = New-Object System.Net.Sockets.TcpClient
                $connectResult = $tcpClient.BeginConnect("localhost", $setup.Port, $null, $null)
                $success = $connectResult.AsyncWaitHandle.WaitOne(500, $false)
                
                if ($success) {
                    try {
                        $tcpClient.EndConnect($connectResult)
                        $tcpClient.Close()
                        $portListening = $true
                    } catch {
                        $tcpClient.Close()
                    }
                } else {
                    $tcpClient.Close()
                }
            } catch {
                # Port not available
            }
        }
        
        if ($portListening) {
            # Port is open, verify it's the right API
            $healthEndpoints = @($setup.HealthEndpoint)
            
            # Add fallback endpoints for API Server
            if ($setup.Type -eq "APIServer") {
                $healthEndpoints += @("/", "/v1/models", "/health", "/status")
            }
            
            foreach ($endpoint in $healthEndpoints) {
                try {
                    $healthUrl = "$($setup.BaseUrl)$endpoint"
                    $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 3 -ErrorAction Stop -UseBasicParsing
                    
                    if ($response.StatusCode -eq 200) {
                        $body = $response.Content
                        $looksLikeSd = ($body -match '"status"\s*:\s*"ok"') -or
                            ($body -match 'stable-diffusion') -or
                            ($body -match '"object"\s*:\s*"model"')
                        if (-not $looksLikeSd -and $setup.Type -eq "APIServer") {
                            if ($Verbose) {
                                Write-Host "    [SKIP] Port $($setup.Port) responded 200 but is not an SD API ($endpoint)" -ForegroundColor Yellow
                            }
                            continue
                        }
                        if ($Verbose) {
                            Write-Host "    [OK] Found $($setup.Name) at $($setup.BaseUrl)" -ForegroundColor Green
                        }
                        
                        # Set as active configuration
                        $script:ActiveSDSetup = $setup
                        $script:StableDiffusionUrl = $setup.BaseUrl
                        $script:StableDiffusionApiUrl = "$($setup.BaseUrl)$($setup.ApiEndpoint)"
                        
                        return $setup
                    }
                } catch {
                    # Try next endpoint
                }
            }
        }
    }
    
    if ($Verbose) {
        Write-Host "    [FAIL] No known Stable Diffusion servers detected" -ForegroundColor Yellow
        Write-Host "`n  Supported setups:" -ForegroundColor Gray
        foreach ($setup in $script:KnownSDSetups) {
            Write-Host "    - $($setup.Name) (port $($setup.Port))" -ForegroundColor Gray
        }
    }
    
    return $null
}

function Test-StableDiffusionConnection {
    <#
    .SYNOPSIS
    Tests if Stable Diffusion API server is available (with auto-detection).
    #>
    param(
        [string]$Url = "",
        [switch]$Verbose
    )
    
    # If no URL specified, try auto-detection first
    if ([string]::IsNullOrEmpty($Url)) {
        $detected = Find-LocalStableDiffusionServer -Verbose:$Verbose
        if ($detected) {
            return $true
        }
        
        # Fall back to configured URL
        $Url = $script:StableDiffusionUrl
    }
    
    if ($Verbose) {
        Write-Host "    Testing connection to $Url..." -ForegroundColor Gray
    }
    
    # Extract port from URL
    $uri = [System.Uri]$Url
    $port = $uri.Port
    if ($port -eq -1) {
        $port = 80
    }
    
    # Method 1: Check if port is listening
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $connectResult = $tcpClient.BeginConnect("localhost", $port, $null, $null)
        $success = $connectResult.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($success) {
            try {
                $tcpClient.EndConnect($connectResult)
                $tcpClient.Close()
                
                if ($Verbose) {
                    Write-Host "    [OK] Port $port is listening" -ForegroundColor Gray
                }
            } catch {
                $tcpClient.Close()
                if ($Verbose) {
                    Write-Host "    [FAIL] Port $port connection failed" -ForegroundColor Gray
                }
                return $false
            }
        } else {
            $tcpClient.Close()
            if ($Verbose) {
                Write-Host "    [FAIL] Port $port is not listening" -ForegroundColor Gray
            }
            return $false
        }
    } catch {
        if ($Verbose) {
            Write-Host "    [FAIL] Port $port is not accessible: $($_.Exception.Message)" -ForegroundColor Gray
        }
        return $false
    }
    
    # Method 2: Try health endpoints based on detected setup
    if ($script:ActiveSDSetup) {
        $healthUrl = "$($script:ActiveSDSetup.BaseUrl)$($script:ActiveSDSetup.HealthEndpoint)"
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 3 -ErrorAction Stop -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                if ($Verbose) {
                    Write-Host "    [OK] $($script:ActiveSDSetup.Name) is responding" -ForegroundColor Green
                }
                return $true
            }
        } catch {
            if ($Verbose) {
                Write-Host "    Health check failed: $($_.Exception.Message)" -ForegroundColor Gray
            }
        }
    }
    
    # Method 3: Try common health endpoints
    $healthEndpoints = @("/ping", "/", "/sdapi/v1/sd-models", "/system_stats", "/api/v1/app/version")
    
    foreach ($endpoint in $healthEndpoints) {
        try {
            $testUrl = "$Url$endpoint"
            $response = Invoke-WebRequest -Uri $testUrl -Method Get -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                if ($Verbose) {
                    Write-Host "    [OK] Server responded to $endpoint (Status: 200)" -ForegroundColor Green
                }
                return $true
            }
        } catch {
            # Try next endpoint
        }
    }
    
    if ($Verbose) {
        Write-Host "    [FAIL] Server is not responding to any known endpoints" -ForegroundColor Red
    }
    return $false
}

function Start-StableDiffusionServerIfNeeded {
    <#
    .SYNOPSIS
    Starts the Stable Diffusion API server if it's not running.
    #>
    param(
        [string]$ToolsRoot = $PSScriptRoot
    )
    
    Write-Host "`n  Checking SD3 server status..." -ForegroundColor Cyan
    
    # FIRST: Quick connection test with verbose output
    if (Test-StableDiffusionConnection -Verbose) {
        Write-Host "  [OK] SD3 server is already running and responding!" -ForegroundColor Green
        return $true
    }
    
    Write-Host "`n  Server not responding on port 1338" -ForegroundColor Yellow
    Write-Host "  Checking if port is in use by another process..." -ForegroundColor Gray
    
    # Check if port 1338 is in use using netstat
    try {
        $netstatLines = netstat -ano | Select-String ":1338"
        
        if ($netstatLines) {
            Write-Host "  Found connections on port 1338:" -ForegroundColor Yellow
            foreach ($line in $netstatLines) {
                Write-Host "    $line" -ForegroundColor Gray
            }
            
            # Look specifically for LISTENING state
            $listeningLine = $netstatLines | Select-String "LISTENING" | Select-Object -First 1
            
            if ($listeningLine) {
                # Extract PID from the line
                $lineText = $listeningLine.ToString().Trim()
                # Split by whitespace and get last element (PID)
                $parts = $lineText -split '\s+' | Where-Object { $_ -ne '' }
                $pid = $parts[-1]
                
                if ($pid -match '^\d+$') {
                    Write-Host "  Process listening on port 1338: PID $pid" -ForegroundColor Yellow
                    
                    try {
                        $process = Get-Process -Id $pid -ErrorAction Stop
                        Write-Host "  Process name: $($process.ProcessName)" -ForegroundColor Gray
                        Write-Host "  Process path: $($process.Path)" -ForegroundColor Gray
                        
                        Write-Host "`n  Port 1338 is in use but server isn't responding to API calls." -ForegroundColor Yellow
                        Write-Host "  Possible reasons:" -ForegroundColor Gray
                        Write-Host "    1. Server is still starting up (wait a moment)" -ForegroundColor Gray
                        Write-Host "    2. Server crashed or is in bad state (restart it)" -ForegroundColor Gray
                        Write-Host "    3. Another application is using port 1338 (close it)" -ForegroundColor Gray
                        
                        Write-Host "`n  Waiting 10 seconds for server to initialize..." -ForegroundColor Cyan
                        for ($i = 10; $i -gt 0; $i--) {
                            Write-Host "    $i..." -NoNewline -ForegroundColor Gray
                            Start-Sleep -Seconds 1
                        }
                        Write-Host ""
                        
                        if (Test-StableDiffusionConnection -Verbose) {
                            Write-Host "  [OK] Server is now ready!" -ForegroundColor Green
                            return $true
                        }
                        
                        Write-Host "`n  [ERROR] Port 1338 is blocked by PID $pid ($($process.ProcessName))" -ForegroundColor Red
                        Write-Host "  You have two options:" -ForegroundColor Yellow
                        Write-Host "    1. Close the application using port 1338 and try again" -ForegroundColor Gray
                        Write-Host "    2. Kill the process: Stop-Process -Id $pid -Force" -ForegroundColor Gray
                        return $false
                        
                    } catch {
                        Write-Host "  [WARN] Could not get process details for PID $pid" -ForegroundColor Yellow
                    }
                }
            }
        } else {
            Write-Host "  Port 1338 is not in use by any process" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  [WARN] Could not check port status: $_" -ForegroundColor Yellow
    }
    
    Write-Host "`n  [ERROR] SD server not running. Start Tools\Start-StableDiffusionServer.ps1 when needed." -ForegroundColor Red
    Write-Host "  It auto-stops after SD_IDLE_SHUTDOWN_SEC (default 180s) with no generations." -ForegroundColor Yellow
    return $false
}

function Stop-StableDiffusionServer {
    <#
    .SYNOPSIS
    Stops the SD3.5 server on port 1338 and frees GPU VRAM.
    #>
    param(
        [string]$ToolsRoot = (Split-Path $PSScriptRoot -Parent)
    )
    # Module lives in Tools\Shared — parent is Tools root
    if (-not $ToolsRoot -or -not (Test-Path (Join-Path $ToolsRoot "Stop-StableDiffusionServer.ps1"))) {
        $ToolsRoot = Split-Path $PSScriptRoot -Parent
    }
    $stop = Join-Path $ToolsRoot "Stop-StableDiffusionServer.ps1"
    if (Test-Path -LiteralPath $stop) {
        & $stop
        return ($LASTEXITCODE -eq 0)
    }
    Write-Host "Stop script missing: $stop" -ForegroundColor Red
    return $false
}

function Invoke-StableDiffusionGeneration {
    <#
    .SYNOPSIS
    Generates an image using Stable Diffusion 3 (supports multiple API formats).
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt,
        
        [string]$NegativePrompt = "",
        
        [int]$Width = 1024,
        
        [int]$Height = 1024,
        
        [int]$Steps = 28,
        
        [double]$GuidanceScale = 7.0,
        
        [int]$Seed = 0,
        
        [int]$NumOutputs = 1,
        
        [string]$ApiUrl = "",
        
        [switch]$AutoStartServer,
        
        [switch]$EnhanceWithOllama,
        
        [string]$OllamaUrl = "http://localhost:11434",
        
        [string]$ReferenceImagePath = "",
        
        [double]$ImageStrength = 0.7
    )
    
    # Enhance prompt with Ollama if requested
    if ($EnhanceWithOllama) {
        $ollamaModule = Join-Path $PSScriptRoot "OllamaIntegration.psm1"
        if (Test-Path $ollamaModule) {
            Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
                if (Test-OllamaConnection) {
                    Write-Host "  Enhancing prompt with Ollama..." -ForegroundColor Cyan
                    $enhancementPrompt = @"
You are a game asset designer. Enhance this asset description for high-quality image generation:

Original: $Prompt

Create a detailed, visually rich description optimized for Stable Diffusion 3 image generation. Include:
- Specific visual details (colors, textures, materials, lighting)
- Style and artistic direction
- Composition and framing
- Technical details (resolution, quality, detail level)
- Any game-specific context or requirements

Return ONLY the enhanced prompt, no introductory text.
"@
                    $enhanced = Invoke-OllamaRequest `
                        -Prompt $enhancementPrompt `
                        -TaskType "visual" `
                        -ResponseLength "detailed" `
                        -AutoEscalate:$true
                    
                    if ($enhanced -and $enhanced.Length -gt $Prompt.Length) {
                        $Prompt = $enhanced.Trim()
                        Write-Host "  [OK] Prompt enhanced ($($Prompt.Length) chars)" -ForegroundColor Green
                    }
                }
            }
        }
    }
    
    # Ensure server is running (auto-detect if needed)
    if (-not (Test-StableDiffusionConnection)) {
        throw "SD server already running or start manually"
    }

    # Always refresh detected server URL after connection test
    $null = Find-LocalStableDiffusionServer
    if ([string]::IsNullOrWhiteSpace($ApiUrl)) {
        $ApiUrl = $script:StableDiffusionApiUrl
    } elseif ($script:ActiveSDSetup -and $script:ActiveSDSetup.BaseUrl) {
        $detectedUrl = "$($script:ActiveSDSetup.BaseUrl)$($script:ActiveSDSetup.ApiEndpoint)"
        if ($ApiUrl -ne $detectedUrl) {
            Write-Host "    [INFO] Using detected SD API URL: $detectedUrl" -ForegroundColor Gray
            $ApiUrl = $detectedUrl
        }
    }
    
    # Use detected API URL if not specified
    if ([string]::IsNullOrEmpty($ApiUrl)) {
        $ApiUrl = $script:StableDiffusionApiUrl
    }
    
    # Validate ApiUrl is a valid string URL (not boolean or invalid)
    if ($ApiUrl -is [bool] -or [string]::IsNullOrWhiteSpace($ApiUrl) -or $ApiUrl -eq "True" -or $ApiUrl -eq "False") {
        # Force re-detection if URL is invalid
        Write-Host "    [WARN] Invalid API URL detected, re-detecting server..." -ForegroundColor Yellow
        $detected = Find-LocalStableDiffusionServer
        if ($detected -is [hashtable] -and $detected.ContainsKey("BaseUrl")) {
            $ApiUrl = "$($detected.BaseUrl)$($detected.ApiEndpoint)"
            Write-Host "    [OK] Re-detected API URL: $ApiUrl" -ForegroundColor Green
        } else {
            throw "Stable Diffusion API URL is invalid and could not be re-detected. Please ensure SD3 server is running."
        }
    }
    
    # Use default negative prompt if not provided
    if ([string]::IsNullOrWhiteSpace($NegativePrompt)) {
        $NegativePrompt = $script:DefaultGenerationParams.NegativePrompt
    }
    
    # Load reference image if provided
    $referenceImageBase64 = $null
    if ($ReferenceImagePath -and (Test-Path $ReferenceImagePath)) {
        try {
            $imageBytes = [System.IO.File]::ReadAllBytes($ReferenceImagePath)
            $referenceImageBase64 = [Convert]::ToBase64String($imageBytes)
            Write-Host "  Using reference image: $(Split-Path -Leaf $ReferenceImagePath)" -ForegroundColor Cyan
            Write-Host "    Image strength: $ImageStrength" -ForegroundColor Gray
        } catch {
            Write-Host "  [WARN] Failed to load reference image: $_" -ForegroundColor Yellow
        }
    }
    
    # Display generation info
    $setupName = if ($script:ActiveSDSetup) { $script:ActiveSDSetup.Name } else { "Stable Diffusion" }
    Write-Host "  Generating image with $setupName..." -ForegroundColor Cyan
    Write-Host "    Dimensions: ${Width}x${Height}" -ForegroundColor Gray
    Write-Host "    Steps: $Steps, Guidance: $GuidanceScale" -ForegroundColor Gray
    if ($referenceImageBase64) {
        Write-Host "    Mode: Image-to-Image (strength: $ImageStrength)" -ForegroundColor Gray
    } else {
        Write-Host "    Mode: Text-to-Image" -ForegroundColor Gray
    }
    
    try {
        # Prepare request body based on detected API type
        $body = @{}
        $apiType = if ($script:ActiveSDSetup) { $script:ActiveSDSetup.Type } else { "APIServer" }
        
        switch ($apiType) {
            "A1111" {
                # AUTOMATIC1111 WebUI format
                $body = @{
                    prompt = $Prompt
                    negative_prompt = $NegativePrompt
                    width = $Width
                    height = $Height
                    steps = $Steps
                    cfg_scale = $GuidanceScale
                    sampler_name = "DPM++ 2M"
                    sampler_index = "DPM++ 2M"
                }
                
                if ($referenceImageBase64) {
                    # Use img2img endpoint instead
                    $ApiUrl = $ApiUrl -replace "/txt2img", "/img2img"
                    $body.init_images = @($referenceImageBase64)
                    $body.denoising_strength = $ImageStrength
                }
                
                if ($Seed -ne 0) {
                    $body.seed = $Seed
                } else {
                    $body.seed = -1  # Random seed for A1111
                }
                
                if ($NumOutputs -gt 1) {
                    $body.n_iter = $NumOutputs
                }
            }
            
            "ComfyUI" {
                # ComfyUI requires workflow JSON - simplified approach
                throw "ComfyUI integration requires workflow configuration. Please use AUTOMATIC1111 or API Server."
            }
            
            default {
                # OpenAI-compatible format (API Server, InvokeAI, SD3)
                # Try OpenAI DALL-E 3 compatible format first
                $body = @{
                    model = "stable-diffusion-3"
                    prompt = $Prompt
                    n = $NumOutputs
                    size = "${Width}x${Height}"
                    quality = "standard"
                    response_format = "b64_json"
                }
                
                # Add optional parameters if provided
                if (-not [string]::IsNullOrWhiteSpace($NegativePrompt)) {
                    $body.negative_prompt = $NegativePrompt
                }
                
                if ($Steps -gt 0) {
                    $body.steps = $Steps
                }
                
                if ($GuidanceScale -gt 0) {
                    $body.guidance_scale = $GuidanceScale
                }
                
                if ($referenceImageBase64) {
                    $body.image = $referenceImageBase64
                    $body.strength = $ImageStrength
                }
                
                if ($Seed -ne 0) {
                    $body.seed = $Seed
                }
            }
        }
        
        $jsonBody = $body | ConvertTo-Json -Depth 10
        
        # Generate image(s)
        Write-Host "    Sending request to $ApiUrl..." -ForegroundColor Gray
        
        # Use .NET HttpClient exclusively for HTTP/2 support
        # PowerShell's Invoke-RestMethod only supports HTTP/1.1, which causes 426 errors
        $response = $null
        $useHttp2 = $false
        
        # Ensure System.Net.Http is loaded
        Add-Type -AssemblyName System.Net.Http -ErrorAction Stop
        
        # Create HttpClientHandler with proper configuration
        $httpClientHandler = New-Object System.Net.Http.HttpClientHandler
        
        # Allow self-signed certificates for HTTPS (common for local SD3 servers)
        if ($ApiUrl -like "https://*") {
            $httpClientHandler.ServerCertificateCustomValidationCallback = {
                param($sender, $cert, $chain, $errors)
                return $true  # Accept all certificates (for local servers)
            }
        }
        
        # Create HttpClient with HTTP/2 support
        $httpClient = New-Object System.Net.Http.HttpClient($httpClientHandler)
        
        # Set HTTP/2 as default version (required for SD3 servers)
        # Use reflection to get HttpVersion.Version20 (works across .NET versions)
        # Note: Version20 is a static property in .NET Core 2.1+ and .NET Framework 4.7.2+
        try {
            $httpVersionType = [System.Net.HttpVersion]
            # Get all static members and find Version20
            $bindingFlags = [System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::Static
            $allMembers = $httpVersionType.GetMembers($bindingFlags)
            $version20Member = $allMembers | Where-Object { $_.Name -eq "Version20" } | Select-Object -First 1
            
            if ($version20Member) {
                if ($version20Member.MemberType -eq [System.Reflection.MemberTypes]::Property) {
                    $version20 = $version20Member.GetValue($null)
                } elseif ($version20Member.MemberType -eq [System.Reflection.MemberTypes]::Field) {
                    $version20 = $version20Member.GetValue($null)
                } else {
                    throw "Version20 found but is not a property or field"
                }
                
                if ($version20) {
                    $httpClient.DefaultRequestVersion = $version20
                    $useHttp2 = $true
                    Write-Host "    Using HTTP/2 protocol (required for SD3)" -ForegroundColor Gray
                } else {
                    throw "Version20 member returned null"
                }
            } else {
                throw "Version20 member not found - HTTP/2 may not be supported in this .NET version"
            }
        } catch {
            # If HTTP/2 is not available, this will fail with 426
            Write-Host "    [WARN] HTTP/2 setup failed: $_" -ForegroundColor Yellow
            Write-Host "    [INFO] Attempting request anyway (may fail with 426 error)" -ForegroundColor Gray
            Write-Host "    [INFO] Ensure .NET 4.7.2+ or .NET Core 2.1+ is installed for HTTP/2 support" -ForegroundColor Gray
        }
        
        # Generous FINITE timeout so slow-but-complete generations are not discarded.
        $httpClient.Timeout = [TimeSpan]::FromSeconds($script:SDHttpTimeoutSec)
        $generationStartedAt = Get-Date
        
        try {
            $uri = [System.Uri]::new($ApiUrl)
            $content = New-Object System.Net.Http.StringContent($jsonBody, [System.Text.Encoding]::UTF8, "application/json")
            
            # Make the request
            $httpResponse = $httpClient.PostAsync($uri, $content).Result
            
            if ($httpResponse.IsSuccessStatusCode) {
                $responseBody = $httpResponse.Content.ReadAsStringAsync().Result
                $response = $responseBody | ConvertFrom-Json
                Write-Host "  [OK] Request succeeded with HTTP/2" -ForegroundColor Green
            } else {
                $statusCode = $httpResponse.StatusCode.value__
                $reasonPhrase = $httpResponse.ReasonPhrase
                $httpResponse.Dispose()
                throw "HTTP ${statusCode}: ${reasonPhrase}"
            }
            
            $httpResponse.Dispose()
        } catch {
            $statusCode = $null
            $errorMessage = $_.Exception.Message
            
            # Try to extract status code from exception
            try {
                if ($_.Exception -is [System.AggregateException] -and $_.Exception.InnerException) {
                    $innerEx = $_.Exception.InnerException
                    if ($innerEx.Response) {
                        $statusCode = [int]$innerEx.Response.StatusCode
                    }
                } elseif ($_.Exception.Response) {
                    $statusCode = [int]$_.Exception.Response.StatusCode
                }
            } catch {
                # Try to extract from error message
                if ($errorMessage -match '(\d{3})') {
                    $statusCode = [int]$matches[1]
                }
            }
            
            # Handle 426 Upgrade Required specifically
            if ($statusCode -eq 426) {
                Write-Host "  [WARN] HTTP 426 (Upgrade Required) - Server requires HTTP/2" -ForegroundColor Yellow
                Write-Host "  [INFO] HTTP/2 was set but server still rejected. Trying HTTPS..." -ForegroundColor Cyan
                
                # Try HTTPS if original was HTTP
                if ($ApiUrl -like "http://*") {
                    $httpsUrl = $ApiUrl -replace "^http://", "https://"
                    Write-Host "  [INFO] Retrying with HTTPS: $httpsUrl" -ForegroundColor Gray
                    
                    try {
                        # Create new handler for HTTPS with certificate validation disabled
                        $httpsHandler = New-Object System.Net.Http.HttpClientHandler
                        $httpsHandler.ServerCertificateCustomValidationCallback = {
                            param($sender, $cert, $chain, $errors)
                            return $true  # Accept all certificates (for local servers)
                        }
                        
                        $httpsClient = New-Object System.Net.Http.HttpClient($httpsHandler)
                        
                        # Set HTTP/2 again
                        try {
                            $httpVersionType = [System.Net.HttpVersion]
                            $bindingFlags = [System.Reflection.BindingFlags]::Public -bor [System.Reflection.BindingFlags]::Static
                            $allMembers = $httpVersionType.GetMembers($bindingFlags)
                            $version20Member = $allMembers | Where-Object { $_.Name -eq "Version20" } | Select-Object -First 1
                            if ($version20Member) {
                                if ($version20Member.MemberType -eq [System.Reflection.MemberTypes]::Property) {
                                    $version20 = $version20Member.GetValue($null)
                                } elseif ($version20Member.MemberType -eq [System.Reflection.MemberTypes]::Field) {
                                    $version20 = $version20Member.GetValue($null)
                                }
                                if ($version20) {
                                    $httpsClient.DefaultRequestVersion = $version20
                                }
                            }
                        } catch {
                            # HTTP/2 setup failed, continue anyway
                        }
                        
                        $httpsClient.Timeout = [TimeSpan]::FromSeconds($script:SDHttpTimeoutSec)
                        $httpsUri = [System.Uri]::new($httpsUrl)
                        $httpsContent = New-Object System.Net.Http.StringContent($jsonBody, [System.Text.Encoding]::UTF8, "application/json")
                        $httpsResponse = $httpsClient.PostAsync($httpsUri, $httpsContent).Result
                        
                        if ($httpsResponse.IsSuccessStatusCode) {
                            $responseBody = $httpsResponse.Content.ReadAsStringAsync().Result
                            $response = $responseBody | ConvertFrom-Json
                            Write-Host "  [OK] Request succeeded with HTTPS + HTTP/2" -ForegroundColor Green
                            # Update module variables
                            $script:StableDiffusionUrl = $httpsUrl -replace "/v1/images/generations.*$", ""
                            $script:StableDiffusionApiUrl = $httpsUrl
                            $httpsResponse.Dispose()
                            $httpsClient.Dispose()
                        } else {
                            $httpsResponse.Dispose()
                            $httpsClient.Dispose()
                            throw "HTTPS also failed: HTTP $($httpsResponse.StatusCode.value__)"
                        }
                    } catch {
                        Write-Host "  [ERROR] HTTPS retry also failed: $_" -ForegroundColor Red
                        Write-Host "  [INFO] This means:" -ForegroundColor Yellow
                        Write-Host "    - The SD3 server requires HTTP/2 protocol" -ForegroundColor Yellow
                        Write-Host "    - HTTP/2 may need to be configured differently" -ForegroundColor Yellow
                        Write-Host "  [INFO] Troubleshooting:" -ForegroundColor Cyan
                        Write-Host "    - Ensure .NET Framework 4.7.2+ or .NET Core 2.1+ is installed" -ForegroundColor Cyan
                        Write-Host "    - Check server documentation for HTTP/2 requirements" -ForegroundColor Cyan
                        Write-Host "    - Verify the API endpoint path is correct: $ApiUrl" -ForegroundColor Cyan
                        
                        throw "HTTP 426 Upgrade Required: Server requires HTTP/2. Both HTTP and HTTPS attempts failed."
                    }
                } else {
                    throw "HTTP 426 Upgrade Required: Server requires HTTP/2 protocol. HTTP/2 was configured but request still failed."
                }
            } else {
                # Other errors
                throw "HTTP request failed: $errorMessage"
            }
        } finally {
            # Clean up
            if ($httpClient) {
                $httpClient.Dispose()
            }
            if ($httpClientHandler) {
                $httpClientHandler.Dispose()
            }
        }
        
        # Legacy fallback code removed - PowerShell Invoke-RestMethod doesn't support HTTP/2
        # All requests must use .NET HttpClient for HTTP/2 support
        
        # Extract image data based on API type
        $images = @()
        
        if ($apiType -eq "A1111") {
            # A1111 returns images array directly
            if ($response.images -and $response.images.Count -gt 0) {
                $images = $response.images
            } else {
                throw "No images in A1111 response"
            }
        } else {
            # OpenAI-compatible format
            if ($response.data -and $response.data.Count -gt 0) {
                foreach ($item in $response.data) {
                    $imageData = $item.b64_json
                    if (-not $imageData) {
                        $imageData = $item.url
                        if ($imageData) {
                            # Download from URL
                            $imageBytes = Invoke-RestMethod -Uri $imageData -Method Get
                            $imageData = [Convert]::ToBase64String($imageBytes)
                        }
                    }
                    
                    if ($imageData) {
                        $images += $imageData
                    }
                }
            } else {
                throw "No image data in API response"
            }
        }
        
        if ($images.Count -eq 0) {
            throw "No images were generated"
        }
        
        Write-Host "  [OK] Generated $($images.Count) image(s)" -ForegroundColor Green
        return $images
        
    } catch {
        $errorMsg = "Image generation failed: $($_.Exception.Message)"
        Write-Host "  [ERROR] $errorMsg" -ForegroundColor Red
        if ($_.Exception.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $responseBody = $reader.ReadToEnd()
                Write-Host "  Response: $responseBody" -ForegroundColor Gray
            } catch {
                # Ignore error reading response
            }
        }
        throw
    }
}

function Save-StableDiffusionImage {
    <#
    .SYNOPSIS
    Saves a base64-encoded image from Stable Diffusion to a file.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Base64Image,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath
    )
    
    try {
        $payload = $Base64Image.Trim()
        if ($payload -match '^data:image/[^;]+;base64,') {
            $payload = $payload.Substring($payload.IndexOf(',') + 1)
        }
        $payload = $payload -replace '\s', ''
        $imageBytes = [Convert]::FromBase64String($payload)
        [System.IO.File]::WriteAllBytes($OutputPath, $imageBytes)
        Write-Host "  [OK] Image saved: $OutputPath" -ForegroundColor Green
        return $OutputPath
    } catch {
        throw "Failed to save image: $_"
    }
}

function Invoke-SdGenerationViaPython {
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$NegativePrompt = "",
        [int]$Width = 1024,
        [int]$Height = 1024,
        [int]$Steps = 28,
        [double]$GuidanceScale = 7.0,
        [int]$Seed = 0,
        [string]$ApiUrl = "",
        [double]$TimeoutSec = 0,
        [string]$ReferenceImagePath = "",
        [double]$ImageStrength = 0.65
    )

    $pythonClient = Join-Path $PSScriptRoot "sd_http_client.py"
    if (-not (Test-Path $pythonClient)) {
        throw "Python SD client not found: $pythonClient"
    }

    $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
                 elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
                 else { throw "Python not found in PATH" }

    $outDir = Split-Path -Parent $OutputPath
    if ($outDir -and -not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    $timeout = if ($TimeoutSec -gt 0) { $TimeoutSec } else { [double]$script:SDHttpTimeoutSec }
    $pyArgs = @(
        $pythonClient, "--prompt", $Prompt, "--output", $OutputPath,
        "--negative-prompt", $NegativePrompt,
        "--width", $Width, "--height", $Height,
        "--steps", $Steps, "--guidance-scale", $GuidanceScale, "--seed", $Seed,
        "--timeout", $timeout
    )
    if ($ApiUrl) { $pyArgs += @("--api-url", $ApiUrl) }
    if ($ReferenceImagePath) {
        $pyArgs += @("--reference-image", $ReferenceImagePath, "--image-strength", "$ImageStrength")
    }

    Write-Host "  Using Python SD client (HTTP/1.1 SD3.5 API, timeout=${timeout}s)..." -ForegroundColor Cyan
    & $pythonCmd @pyArgs
    if ($LASTEXITCODE -ne 0) { throw "Python SD client failed (exit $LASTEXITCODE)" }
    if (-not (Test-Path $OutputPath)) { throw "Python SD client did not create output: $OutputPath" }
    return $OutputPath
}

function Generate-AssetImageWithSD3 {
    <#
    .SYNOPSIS
    Complete workflow: Enhance prompt with Ollama, generate with SD3, save image.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath,
        
        [string]$NegativePrompt = "",
        
        [int]$Width = 1024,
        
        [int]$Height = 1024,
        
        [int]$Steps = 28,
        
        [double]$GuidanceScale = 7.0,
        
        [int]$Seed = 0,
        
        [switch]$EnhanceWithOllama = $true,
        
        [switch]$AutoStartServer = $false,
        
        [string]$ApiUrl = "",
        
        [string]$ReferenceImagePath = "",
        
        [double]$ImageStrength = 0.7
    )
    
    # Ollama prompt enhancement (optional)
    if ($EnhanceWithOllama) {
        $ollamaModule = Join-Path $PSScriptRoot "OllamaIntegration.psm1"
        if (Test-Path $ollamaModule) {
            Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
                if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
                    if (Test-OllamaConnection) {
                        Write-Host "  Enhancing prompt with Ollama..." -ForegroundColor Cyan
                        $enhancementPrompt = @"
You are a game asset designer. Enhance this asset description for high-quality image generation:

Original: $Prompt

Create a detailed, visually rich description optimized for Stable Diffusion image generation.
Return ONLY the enhanced prompt, no introductory text.
"@
                        $enhanced = Invoke-OllamaRequest -Prompt $enhancementPrompt -TaskType "visual" -ResponseLength "detailed" -AutoEscalate:$true
                        if ($enhanced -and $enhanced.Length -gt $Prompt.Length) {
                            $Prompt = $enhanced.Trim()
                            Write-Host "  [OK] Prompt enhanced ($($Prompt.Length) chars)" -ForegroundColor Green
                        }
                    }
                }
            }
        }
    }

    # Prefer Python HTTP/1.1 client for SD3.5 Diffusers server (reliable on Windows PowerShell 5.1+)
    $pythonClient = Join-Path $PSScriptRoot "sd_http_client.py"
    if (Test-Path $pythonClient) {
        try {
            if (-not (Test-StableDiffusionConnection)) {
                throw "SD server already running or start manually"
            }
            return Invoke-SdGenerationViaPython `
                -Prompt $Prompt `
                -OutputPath $OutputPath `
                -NegativePrompt $NegativePrompt `
                -Width $Width `
                -Height $Height `
                -Steps $Steps `
                -GuidanceScale $GuidanceScale `
                -Seed $Seed `
                -ApiUrl $ApiUrl `
                -ReferenceImagePath $ReferenceImagePath `
                -ImageStrength $ImageStrength
        } catch {
            Write-Host "  [WARN] Python SD client failed: $_" -ForegroundColor Yellow
            Write-Host "  [INFO] Falling back to PowerShell HTTP/2 client..." -ForegroundColor Gray
        }
    }

    # Fallback: PowerShell HTTP/2 client (OpenAI-style API servers).
    # Robustness: generous finite timeout (in Invoke-StableDiffusionGeneration),
    # OOM -> retry at reduced settings, and disk-salvage of slow-but-complete outputs.
    $generationStartedAt = Get-Date
    $images = @()
    try {
        $images = Invoke-StableDiffusionGeneration `
            -Prompt $Prompt `
            -NegativePrompt $NegativePrompt `
            -Width $Width `
            -Height $Height `
            -Steps $Steps `
            -GuidanceScale $GuidanceScale `
            -Seed $Seed `
            -EnhanceWithOllama:$EnhanceWithOllama `
            -AutoStartServer:$AutoStartServer `
            -ApiUrl $ApiUrl `
            -ReferenceImagePath $ReferenceImagePath `
            -ImageStrength $ImageStrength
    } catch {
        $errText = $_.Exception.Message
        # First, try to salvage a completed-but-slow generation from disk.
        $salvaged = Get-SalvagedSdOutput -OutputPath $OutputPath -StartedAt $generationStartedAt -Width $Width -Height $Height
        if ($salvaged) { return $salvaged }

        if (Test-SdOomError -Message $errText) {
            # CUDA OOM: retry once at reduced resolution/steps instead of hanging or failing hard.
            $redW = [Math]::Max(512, [int]($Width * 0.66))
            $redH = [Math]::Max(512, [int]($Height * 0.66))
            $redSteps = [Math]::Max(12, [int]($Steps * 0.6))
            Write-Host "  [SD] CUDA OOM detected; retrying at reduced settings ${redW}x${redH}@${redSteps}..." -ForegroundColor Yellow
            $generationStartedAt = Get-Date
            try {
                $images = Invoke-StableDiffusionGeneration `
                    -Prompt $Prompt -NegativePrompt $NegativePrompt `
                    -Width $redW -Height $redH -Steps $redSteps `
                    -GuidanceScale $GuidanceScale -Seed $Seed `
                    -EnhanceWithOllama:$false -AutoStartServer:$false `
                    -ApiUrl $ApiUrl -ReferenceImagePath $ReferenceImagePath -ImageStrength $ImageStrength
            } catch {
                $salvaged = Get-SalvagedSdOutput -OutputPath $OutputPath -StartedAt $generationStartedAt -Width $redW -Height $redH
                if ($salvaged) { return $salvaged }
                throw
            }
        } else {
            throw
        }
    }
    
    if ($images.Count -eq 0) {
        throw "No images were generated"
    }
    
    # Save first image
    $savedPath = Save-StableDiffusionImage -Base64Image $images[0] -OutputPath $OutputPath
    
    # Return additional images if multiple were generated
    if ($images.Count -gt 1) {
        $basePath = [System.IO.Path]::GetDirectoryName($OutputPath)
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($OutputPath)
        $extension = [System.IO.Path]::GetExtension($OutputPath)
        
        $additionalPaths = @($savedPath)
        for ($i = 1; $i -lt $images.Count; $i++) {
            $additionalPath = Join-Path $basePath "${baseName}_${i}${extension}"
            $additionalPaths += Save-StableDiffusionImage -Base64Image $images[$i] -OutputPath $additionalPath
        }
        return $additionalPaths
    }
    
    return $savedPath
}

# Export functions
Export-ModuleMember -Function Find-LocalStableDiffusionServer, Test-StableDiffusionConnection, Start-StableDiffusionServerIfNeeded, Stop-StableDiffusionServer, Invoke-StableDiffusionGeneration, Save-StableDiffusionImage, Invoke-SdGenerationViaPython, Generate-AssetImageWithSD3, Get-FreeVramMB, Get-SalvagedSdOutput, Test-SdOomError, Set-StableDiffusionGpuPreferredEnv, Get-StableDiffusionRuntimeStatus, Assert-StableDiffusionUsesGpu
