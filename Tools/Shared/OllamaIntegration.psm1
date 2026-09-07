<#
.SYNOPSIS
    Shared Ollama Integration Module for AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Provides high-performance Ollama integration with:
    - Automatic Ollama startup
    - Optimal thread usage (all available cores)
    - Large context window (256k)
    - Model auto-selection
    - Connection testing and retry logic
    - Resource-efficient request handling
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:OllamaUrl = "http://localhost:11434"
$script:OllamaApiUrl = "$script:OllamaUrl/api"

# GPU/CUDA detection cache
$script:GPUInfo = @{
    Detected = $false
    Library = $null
    VRAM = $null
    Compute = $null
    Driver = $null
    LastCheck = $null
    CacheTimeoutMinutes = 30  # Cache GPU info for 30 minutes
}

# High-performance AI configuration
$script:AIConfig = @{
    # Model preferences - ordered by preference (will auto-select available)
    # Optimized for asset generation pipeline: structured planning, creative concepting, hybrid tasks
    # Modern stack: Removed outdated CodeLlama variants, optimized routing for mech asset generation
    # Three-tier routing: Standard → Dark-tone → Escalation (for refusal handling)
    PreferredModels = @{
        "code" = @("qwen2.5-coder:14b", "qwen2.5-coder:7b", "deepseek-coder:6.7b")  # Tier 1: Structured asset planning (JSON, atlas layouts, segment definitions)
        "analysis" = @("qwen2.5-coder:14b", "deepseek-r1:7b", "deepseek-coder:6.7b", "qwen2.5-math:7b")  # Tier 1: Structured planning + hybrid tasks (physics, balancing, reasoning)
        "visual" = @("wizardlm-uncensored:latest", "llama3.1:8b", "llama3.1:3b", "llama3.1:70b", "mistral:7b")  # Tier 1: Uncensored creative first (biomutation / organic)
        "simple" = @("qwen2.5-coder:7b", "llama3.1:3b", "qwen2.5:1.5b", "phi3:mini", "gemma2:2b")  # Tier 1: Fast tasks, JSON repair, schema validation (removed llama3.2:1b - not available)
        "dark_tone" = @("wizardlm-uncensored:latest", "llama3.1:8b", "llama3.1:3b", "llama3.1:70b", "deepseek-r1:7b")  # Tier 2: Uncensored dark/organic first
        "escalation" = @("wizardlm-uncensored:latest", "llama3.1:8b", "llama3.1:3b")  # Tier 3: Escalation models (only when primary models refuse)
    }
    # Selected models (populated at runtime)
    SelectedModels = @{
        "code" = $null
        "analysis" = $null
        "visual" = $null
        "simple" = $null
        "dark_tone" = $null
        "escalation" = $null
    }
    # Performance settings - HIGH PERFORMANCE (tools run when game is not running)
    RequestTimeoutSec = 300             # 5 minutes max per request
    MaxTokensSimple = 512               # Short responses
    MaxTokensStandard = 2048            # Medium responses
    MaxTokensDetailed = 4096            # Detailed analysis
    MaxContextLength = 262144            # Maximum context window (256k)
    MinDelayBetweenRequests = 200       # ms between requests
    # GPU/RAM memory management
    UseGPU = $true                       # Enable GPU acceleration
    AutoRAMFallback = $true              # Automatically use RAM when VRAM is insufficient
    GPULayerReserve = 0.1                # Reserve 10% VRAM for system/overhead
    RAMFallbackEnabled = $true          # Allow offloading to RAM
}

# File operation cache to avoid repeated expensive scans
$script:FileCache = @{
    GetChildItem = @{}  # Cache Get-ChildItem results by path+filter
    LastCacheTime = @{} # Track when cache entries were created
    CacheTimeoutMinutes = 5  # Cache valid for 5 minutes
}

# Performance throttling settings
$script:PerformanceConfig = @{
    FileReadDelayMs = 10        # Delay between file reads (ms)
    FileScanBatchSize = 50      # Process files in batches
    ProgressUpdateInterval = 10 # Update progress every N files
    EnableThrottling = $true    # Enable CPU throttling
    TargetCPUUsage = 0.94      # Target 94% CPU usage (leave 6% free)
    ThrottleIntervalMs = 100    # Check/adjust throttling every 100ms
    LastThrottleTime = [datetime]::Now
    ThrottleCounter = 0
}

# ============================================================
# FILE OPERATION UTILITIES (CPU Throttling)
# ============================================================

function Get-CachedChildItem {
    <#
    .SYNOPSIS
    Cached wrapper for Get-ChildItem to avoid repeated expensive recursive scans.
    Prevents CPU burn by caching directory scan results.
    #>
    param(
        [string]$Path,
        [string]$Filter = "*",
        [switch]$Recurse,
        [switch]$File,
        [string[]]$Include
    )
    
    # Create cache key
    $filterStr = if ($Include) { $Include -join "," } else { $Filter }
    $cacheKey = "$Path|$filterStr|$Recurse|$File"
    
    # Check cache
    if ($script:FileCache.GetChildItem.ContainsKey($cacheKey)) {
        $cacheTime = $script:FileCache.LastCacheTime[$cacheKey]
        $ageMinutes = ([datetime]::Now - $cacheTime).TotalMinutes
        
        if ($ageMinutes -lt $script:FileCache.CacheTimeoutMinutes) {
            # Cache hit - return cached result
            return $script:FileCache.GetChildItem[$cacheKey]
        }
        else {
            # Cache expired - remove
            $script:FileCache.GetChildItem.Remove($cacheKey)
            $script:FileCache.LastCacheTime.Remove($cacheKey)
        }
    }
    
    # Cache miss - perform actual scan
    $params = @{
        Path = $Path
        ErrorAction = "SilentlyContinue"
    }
    
    if ($Filter -ne "*" -and -not $Include) {
        $params.Filter = $Filter
    }
    if ($Include) {
        $params.Include = $Include
    }
    if ($Recurse) {
        $params.Recurse = $true
    }
    if ($File) {
        $params.File = $true
    }
    
    $result = Get-ChildItem @params
    
    # Store in cache
    $script:FileCache.GetChildItem[$cacheKey] = $result
    $script:FileCache.LastCacheTime[$cacheKey] = [datetime]::Now
    
    return $result
}

function Invoke-CPUThrottle {
    <#
    .SYNOPSIS
    Adds strategic delays to maintain ~94% CPU usage (leaving 6% free).
    Call this periodically during intensive operations to prevent 100% CPU burn.
    #>
    if (-not $script:PerformanceConfig.EnableThrottling) {
        return
    }
    
    $now = [datetime]::Now
    $elapsed = ($now - $script:PerformanceConfig.LastThrottleTime).TotalMilliseconds
    
    # Throttle every ~100ms to maintain 94% CPU usage (6% idle time)
    if ($elapsed -ge $script:PerformanceConfig.ThrottleIntervalMs) {
        $script:PerformanceConfig.ThrottleCounter++
        
        # Add small delay to maintain ~94% CPU: 6% idle time = ~6ms delay per 100ms
        # This creates periodic idle time to prevent 100% CPU usage
        $idleTimeMs = [math]::Round($script:PerformanceConfig.ThrottleIntervalMs * (1 - $script:PerformanceConfig.TargetCPUUsage))
        if ($idleTimeMs -gt 0) {
            Start-Sleep -Milliseconds $idleTimeMs
        }
        
        $script:PerformanceConfig.LastThrottleTime = $now
    }
}

function Invoke-ThrottledFileProcessing {
    <#
    .SYNOPSIS
    Processes files with CPU throttling to prevent 100% CPU usage.
    #>
    param(
        [Parameter(Mandatory=$true)]
        [array]$Files,
        
        [Parameter(Mandatory=$true)]
        [scriptblock]$ProcessFile,
        
        [string]$Activity = "Processing Files",
        [string]$StatusPrefix = "Processing",
        [int]$BatchSize = 0,
        [int]$UpdateInterval = 0
    )
    
    if ($BatchSize -eq 0) {
        $BatchSize = $script:PerformanceConfig.FileScanBatchSize
    }
    if ($UpdateInterval -eq 0) {
        $UpdateInterval = $script:PerformanceConfig.ProgressUpdateInterval
    }
    
    $fileCount = $Files.Count
    $processedCount = 0
    $results = @()
    
    foreach ($file in $Files) {
        $processedCount++
        
        # CPU throttling to maintain ~94% usage (leave 6% free)
        Invoke-CPUThrottle
        
        # Throttle file operations to reduce CPU usage
        if ($script:PerformanceConfig.EnableThrottling -and $processedCount % $BatchSize -eq 0) {
            Start-Sleep -Milliseconds $script:PerformanceConfig.FileReadDelayMs
        }
        
        # Update progress periodically
        if ($processedCount % $UpdateInterval -eq 0 -or $processedCount -eq $fileCount) {
            # Ensure variables are single integers before division
            $processedInt = if ($processedCount -is [System.Array]) { [int]$processedCount[0] } else { [int]$processedCount }
            $fileCountInt = if ($fileCount -is [System.Array]) { [int]$fileCount[0] } else { [int]$fileCount }
            
            if ($fileCountInt -gt 0) {
                $percent = [math]::Min(100, [int](($processedInt / $fileCountInt) * 100))
                Write-Progress -Activity $Activity -Status "$StatusPrefix $processedInt/$fileCountInt files..." -PercentComplete $percent
            }
        }
        
        try {
            $result = & $ProcessFile $file
            if ($result) {
                $results += $result
            }
        }
        catch {
            # Skip files that can't be processed
            continue
        }
    }
    
    Write-Progress -Activity $Activity -Completed
    
    return $results
}

function Clear-FileCache {
    <#
    .SYNOPSIS
    Clears the file operation cache.
    #>
    $script:FileCache.GetChildItem.Clear()
    $script:FileCache.LastCacheTime.Clear()
}

# ============================================================
# CORE FUNCTIONS
# ============================================================

function Get-OptimalThreadCount {
    <#
    .SYNOPSIS
    Gets optimal thread count for Ollama - leaves 6% CPU headroom to prevent burn test behavior.
    #>
    $totalCores = [Environment]::ProcessorCount
    if ($totalCores -le 0) { $totalCores = 4 }
    
    # Leave 6% CPU headroom (use 94% of cores) to prevent system overload
    # This prevents the tool from acting like a CPU burn test
    $threads = [math]::Max(2, [math]::Floor($totalCores * 0.94))
    
    return $threads
}

function Get-GPUInfo {
    <#
    .SYNOPSIS
    Detects GPU/VRAM information from Ollama's inference-compute API.
    Returns hashtable with GPU details or null if not available.
    #>
    try {
        # Try the inference-compute endpoint
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/inference-compute" -Method Get -TimeoutSec 5 -ErrorAction Stop
        
        # The response can be in different formats:
        # 1. Direct string: "{Library:CUDA Variant: Compute:7.5 Driver:13.0 Name:CUDA0 VRAM:11.0 GiB}"
        # 2. Object with "inference compute" property (with space)
        # 3. Object with nested properties
        $computeInfo = $null
        $computeInfoStr = ""
        
        # Debug: Check response type
        if ($response -is [string]) {
            $computeInfoStr = $response
        }
        elseif ($response -is [PSCustomObject]) {
            # Try accessing as object properties
            $props = $response | Get-Member -MemberType NoteProperty, Property | Select-Object -ExpandProperty Name
            
            # Try different property name variations
            foreach ($prop in $props) {
                if ($prop -like "*inference*" -or $prop -like "*compute*") {
                    $val = $response.$prop
                    if ($val) {
                        $computeInfoStr = if ($val -is [string]) { $val } else { $val.ToString() }
                        break
                    }
                }
            }
            
            # If still not found, try direct property access with space
            if ([string]::IsNullOrWhiteSpace($computeInfoStr)) {
                try {
                    $computeInfoStr = $response."inference compute"
                } catch { }
            }
            
            # If still not found, convert entire object to string
            if ([string]::IsNullOrWhiteSpace($computeInfoStr)) {
                $computeInfoStr = ($response | ConvertTo-Json -Depth 10)
            }
        }
        elseif ($response -is [Hashtable]) {
            # Try hashtable access
            foreach ($key in $response.Keys) {
                if ($key -like "*inference*" -or $key -like "*compute*") {
                    $val = $response[$key]
                    if ($val) {
                        $computeInfoStr = if ($val -is [string]) { $val } else { $val.ToString() }
                        break
                    }
                }
            }
        }
        else {
            # Convert to string as fallback
            $computeInfoStr = $response.ToString()
        }
        
        if (-not [string]::IsNullOrWhiteSpace($computeInfoStr)) {
            # Parse VRAM from string like "VRAM:11.0 GiB" or "VRAM:11.0 GB"
            $vramGB = 0
            if ($computeInfoStr -match "VRAM:\s*([\d.]+)\s*(GiB|GB|gb|gib)") {
                $vramGB = [double]$matches[1]
            }
            
            # Extract other info
            $library = "Unknown"
            if ($computeInfoStr -match "Library:\s*(\w+)") {
                $library = $matches[1]
            }
            
            $name = "Unknown"
            if ($computeInfoStr -match "Name:\s*(\S+)") {
                $name = $matches[1]
            }
            
            # Check if GPU is actually available (not CPU)
            # CUDA, Metal, ROCm, OpenCL are GPU libraries
            $isGPU = ($library -ne "Unknown" -and $library -ne "CPU" -and 
                     ($library -match "CUDA|Metal|ROCm|OpenCL|Vulkan" -or $vramGB -gt 0))
            
            if ($isGPU) {
                return @{
                    Available = $true
                    Library = $library
                    Name = $name
                    VRAMGB = $vramGB
                    RawInfo = $computeInfoStr
                }
            }
        }
    }
    catch {
        # API might not be available or endpoint might be different
        # Try alternative detection method
    }
    
    # Fallback: Try to detect GPU from system if API doesn't work
    # This is a secondary check - the API method should work, but this provides backup
    try {
        # Check for NVIDIA GPU via nvidia-smi if available
        $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
        if ($nvidiaSmi) {
            $nvidiaOutput = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>&1
            if ($LASTEXITCODE -eq 0 -and $nvidiaOutput) {
                $vramMB = 0
                if ($nvidiaOutput -match "(\d+)") {
                    # Ensure we get a single integer value, not an array
                    $matchValue = $matches[1]
                    if ($matchValue -is [System.Array]) {
                        $vramMB = [int]$matchValue[0]
                    } else {
                        $vramMB = [int]$matchValue
                    }
                    $vramGB = [double]$vramMB / 1024.0
                    
                    if ($vramGB -gt 0) {
                        return @{
                            Available = $true
                            Library = "CUDA"
                            Name = "NVIDIA"
                            VRAMGB = $vramGB
                            RawInfo = "Detected via nvidia-smi: $vramMB MB"
                        }
                    }
                }
            }
        }
    }
    catch {
        # nvidia-smi not available or failed
    }
    
    # Default: CPU only
    return @{
        Available = $false
        Library = "CPU"
        Name = "CPU"
        VRAMGB = 0
        RawInfo = ""
    }
}

function Get-OptimalGPULayers {
    <#
    .SYNOPSIS
    Calculates optimal GPU layers based on model size and available VRAM.
    Returns the number of layers to put on GPU - remaining layers automatically use RAM simultaneously.
    This enables hybrid GPU/RAM operation where VRAM holds what fits, RAM holds the rest.
    #>
    param(
        [string]$ModelName,
        [double]$AvailableVRAMGB = 0,
        [switch]$PreferGPU
    )
    
    # If GPU not available or disabled, use CPU (0 layers = all in RAM)
    if (-not $script:AIConfig.UseGPU -or $AvailableVRAMGB -eq 0) {
        return 0
    }
    
    # Estimate model size and layer count from name
    $modelSizeGB = 0
    $estimatedTotalLayers = 32  # Default layer count for most models
    
    if ($ModelName -match ":(\d+)(b|B)") {
        $sizeParam = [int]$matches[1]
        
        # Rough estimate: parameter count * 2 bytes (FP16) = model size in GB
        # 7B ≈ 14GB, 8B ≈ 16GB, 14B ≈ 28GB, 70B ≈ 140GB
        $modelSizeGB = $sizeParam * 2.0
        
        # Estimate layer count based on model size
        # Typical layer counts: 3B=26, 7B=32, 8B=32, 13B=40, 14B=40, 70B=80
        $estimatedTotalLayers = switch ($sizeParam) {
            { $_ -le 3 } { 26 }
            { $_ -le 7 } { 32 }
            { $_ -le 8 } { 32 }
            { $_ -le 13 } { 40 }
            { $_ -le 14 } { 40 }
            { $_ -le 30 } { 60 }
            default { 80 }
        }
    }
    elseif ($ModelName -match ":(\d+\.\d+)(b|B)") {
        $sizeParam = [double]$matches[1]
        $modelSizeGB = $sizeParam * 2.0
        $estimatedTotalLayers = if ($sizeParam -le 3) { 26 } elseif ($sizeParam -le 7) { 32 } elseif ($sizeParam -le 13) { 40 } else { 60 }
    }
    else {
        # Default estimate for unknown models
        $modelSizeGB = 16.0
        $estimatedTotalLayers = 32
    }
    
    # Calculate available VRAM (reserve 10% for overhead/system)
    # Ensure variables are single values, not arrays
    $availableVRAM = if ($AvailableVRAMGB -is [System.Array]) { [double]$AvailableVRAMGB[0] } else { [double]$AvailableVRAMGB }
    $usableVRAMGB = $availableVRAM * (1 - $script:AIConfig.GPULayerReserve)
    
    # Calculate memory per layer (model size / total layers)
    $modelSize = if ($modelSizeGB -is [System.Array]) { [double]$modelSizeGB[0] } else { [double]$modelSizeGB }
    $totalLayers = if ($estimatedTotalLayers -is [System.Array]) { [int]$estimatedTotalLayers[0] } else { [int]$estimatedTotalLayers }
    
    if ($totalLayers -gt 0) {
        $memoryPerLayerGB = $modelSize / $totalLayers
    } else {
        $memoryPerLayerGB = 0.0
    }
    
    # Calculate how many layers can fit in available VRAM
    # Add some buffer for activations and context (roughly 20% overhead per layer)
    $effectiveMemoryPerLayerGB = $memoryPerLayerGB * 1.2
    if ($effectiveMemoryPerLayerGB -gt 0) {
        $maxLayersForVRAM = [math]::Floor($usableVRAMGB / $effectiveMemoryPerLayerGB)
    } else {
        $maxLayersForVRAM = 0
    }
    
    # Ensure we don't exceed total layers, and always use at least some GPU if available
    # Use the already-extracted $totalLayers variable
    $gpuLayers = [math]::Min($maxLayersForVRAM, $totalLayers)
    
    # If we can fit at least 1 layer in VRAM, use hybrid mode (GPU + RAM)
    # If we can fit all layers, still use hybrid mode (allows for context/activations)
    if ($gpuLayers -gt 0) {
        # Use calculated number of layers on GPU, rest automatically in RAM
        # This enables simultaneous GPU/RAM operation
        return $gpuLayers
    }
    else {
        # Not enough VRAM for even one layer, use CPU/RAM only
        return 0
    }
}

function Start-OllamaIfNeeded {
    <#
    .SYNOPSIS
    Attempts to start Ollama if it's not running.
    #>
    # Check if ollama command is available
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaCmd) {
        Write-Host "  Ollama command not found in PATH" -ForegroundColor Yellow
        return $false
    }
    
    # Check if Ollama is already running
    try {
        $null = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 1 -ErrorAction Stop
        return $true
    }
    catch {
        # Ollama is not running, try to start it
        Write-Host "  Starting Ollama in background..." -ForegroundColor Cyan
        try {
            $process = Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru -ErrorAction Stop
            Write-Host "  Ollama process started (PID: $($process.Id))" -ForegroundColor Gray
            
            # Wait for Ollama to become available (max 30 seconds)
            $maxWait = 30
            $waited = 0
            while ($waited -lt $maxWait) {
                Start-Sleep -Seconds 2
                $waited += 2
                try {
                    $null = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 1 -ErrorAction Stop
                    Write-Host "  Ollama is now available" -ForegroundColor Green
                    return $true
                }
                catch {
                    Write-Host "  Waiting for Ollama... ($waited/$maxWait seconds)" -ForegroundColor Gray
                }
            }
            
            Write-Host "  Ollama did not become available within $maxWait seconds" -ForegroundColor Yellow
            return $false
        }
        catch {
            Write-Host "  Failed to start Ollama: $($_.Exception.Message)" -ForegroundColor Yellow
            return $false
        }
    }
}

function Test-OllamaConnection {
    <#
    .SYNOPSIS
    Tests Ollama connection and auto-selects best available models.
    Automatically starts Ollama if it's not running.
    #>
    try {
        # Quick connection test with short timeout
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        
        if (-not $response.models -or $response.models.Count -eq 0) {
            Write-Host "  No models found in Ollama" -ForegroundColor Yellow
            Write-Host "  Please install at least one model: ollama pull llama3.1:3b" -ForegroundColor Gray
            return $false
        }
        
        $availableModels = $response.models | ForEach-Object { $_.name }
        Write-Host "  Available models: $($availableModels.Count)" -ForegroundColor Gray
        
        # Select best model for each task type (including dark_tone and escalation)
        $modelSelections = @()
        foreach ($taskType in $script:AIConfig.PreferredModels.Keys) {
            $preferences = $script:AIConfig.PreferredModels[$taskType]
            $selected = Select-BestAvailableModel -PreferredModels $preferences -AvailableModels $availableModels
            
            if ($selected) {
                $script:AIConfig.SelectedModels[$taskType] = $selected
                $tierLabel = if ($taskType -in @("code", "analysis", "visual", "simple")) { "Tier 1" } elseif ($taskType -eq "dark_tone") { "Tier 2" } else { "Tier 3" }
                $modelSelections += "  $taskType ($tierLabel) : $selected"
            }
        }
        
        if ($modelSelections.Count -gt 0) {
            Write-Host "  Model selection:" -ForegroundColor Cyan
            $modelSelections | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
        }
        
        # Show resource settings
        $threads = Get-OptimalThreadCount
        Write-Host "  Threads: $threads (of $([Environment]::ProcessorCount) cores)" -ForegroundColor Gray
        Write-Host "  Context: $($script:AIConfig.MaxContextLength) tokens" -ForegroundColor Gray
        
        # Detect and display GPU/RAM information (with retry for initial detection)
        $gpuInfo = Get-GPUInfo
        # Retry once if GPU not detected (Ollama may need a moment to detect GPU)
        if (-not $gpuInfo.Available -and $gpuInfo.VRAMGB -eq 0) {
            Start-Sleep -Milliseconds 500
            $gpuInfo = Get-GPUInfo
        }
        
        if ($gpuInfo.Available -and $gpuInfo.VRAMGB -gt 0) {
            Write-Host "  GPU: $($gpuInfo.Library) ($($gpuInfo.Name)) - $([math]::Round($gpuInfo.VRAMGB, 1)) GB VRAM" -ForegroundColor Green
            if ($script:AIConfig.AutoRAMFallback) {
                Write-Host "  Memory: Hybrid GPU/RAM mode (VRAM for layers that fit, RAM for rest)" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "  GPU: Not available - using CPU/RAM" -ForegroundColor Yellow
            if ($gpuInfo.RawInfo) {
                Write-Host "    (Raw info: $($gpuInfo.RawInfo))" -ForegroundColor DarkGray
            }
        }
        
        # Store GPU info for later use
        $script:AIConfig.GPUInfo = $gpuInfo
        
        return ($script:AIConfig.SelectedModels.Values | Where-Object { $_ }).Count -gt 0
    }
    catch {
        $errorMsg = $_.Exception.Message
        if ($errorMsg -match "timeout|connection|refused|unreachable") {
            Write-Host "  Ollama is not running" -ForegroundColor Yellow
            
            # Try to start Ollama automatically
            if (Start-OllamaIfNeeded) {
                # Retry connection after starting
                try {
                    $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
                    if ($response.models -and $response.models.Count -gt 0) {
                        # Process models (same logic as successful connection above)
                        $availableModels = $response.models | ForEach-Object { $_.name }
                        
                        # Select best model for each task type
                        $modelSelections = @()
                        foreach ($taskType in $script:AIConfig.PreferredModels.Keys) {
                            $preferences = $script:AIConfig.PreferredModels[$taskType]
                            $selected = Select-BestAvailableModel -PreferredModels $preferences -AvailableModels $availableModels
                            
                            if ($selected) {
                                $script:AIConfig.SelectedModels[$taskType] = $selected
                                $modelSelections += "  $taskType : $selected"
                            }
                        }
                        
                        if ($modelSelections.Count -gt 0) {
                            Write-Host "  Model selection:" -ForegroundColor Cyan
                            $modelSelections | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
                        }
                        
                        $threads = Get-OptimalThreadCount
                        Write-Host "  Threads: $threads (of $([Environment]::ProcessorCount) cores)" -ForegroundColor Gray
                        
                        # Detect and display GPU/RAM information (with retry for initial detection)
                        $gpuInfo = Get-GPUInfo
                        # Retry once if GPU not detected (Ollama may need a moment to detect GPU)
                        if (-not $gpuInfo.Available -and $gpuInfo.VRAMGB -eq 0) {
                            Start-Sleep -Milliseconds 500
                            $gpuInfo = Get-GPUInfo
                        }
                        
                        if ($gpuInfo.Available -and $gpuInfo.VRAMGB -gt 0) {
                            Write-Host "  GPU: $($gpuInfo.Library) ($($gpuInfo.Name)) - $([math]::Round($gpuInfo.VRAMGB, 1)) GB VRAM" -ForegroundColor Green
                            if ($script:AIConfig.AutoRAMFallback) {
                                Write-Host "  Memory: Hybrid GPU/RAM mode (VRAM for layers that fit, RAM for rest)" -ForegroundColor Gray
                            }
                        }
                        else {
                            Write-Host "  GPU: Not available - using CPU/RAM" -ForegroundColor Yellow
                            if ($gpuInfo.RawInfo) {
                                Write-Host "    (Raw info: $($gpuInfo.RawInfo))" -ForegroundColor DarkGray
                            }
                        }
                        
                        # Store GPU info for later use
                        $script:AIConfig.GPUInfo = $gpuInfo
                        
                        return ($script:AIConfig.SelectedModels.Values | Where-Object { $_ }).Count -gt 0
                    }
                }
                catch {
                    Write-Host "  Still cannot connect to Ollama after starting it" -ForegroundColor Red
                    return $false
                }
            }
            else {
                Write-Host "`n❌ ERROR: Ollama is required" -ForegroundColor Red
                Write-Host "  To fix this:" -ForegroundColor Cyan
                Write-Host "  1. Install Ollama from https://ollama.com" -ForegroundColor White
                Write-Host "  2. Start Ollama manually: ollama serve" -ForegroundColor White
                Write-Host "  3. Install at least one model: ollama pull llama3.1:3b" -ForegroundColor White
                Write-Host ""
                return $false
            }
        }
        else {
            Write-Host "  Connection error: $errorMsg" -ForegroundColor Yellow
            return $false
        }
    }
}

function Select-BestAvailableModel {
    <#
    .SYNOPSIS
    Selects the best available model from a preference list.
    Handles version variations (e.g., llama3.1:8b matches llama3.1:3b if 8b not available).
    #>
    param(
        [array]$PreferredModels,
        [array]$AvailableModels
    )
    
    foreach ($preferred in $PreferredModels) {
        # Check exact match first
        if ($AvailableModels -contains $preferred) {
            return $preferred
        }
        
        # Check partial match by base name (e.g., "codellama:7b" matches "codellama:7b-instruct")
        $baseName = $preferred.Split(':')[0]
        $matching = $AvailableModels | Where-Object { $_ -like "$baseName*" } | Select-Object -First 1
        if ($matching) {
            return $matching
        }
        
        # Check for version variations (e.g., if looking for llama3.1:8b but only llama3.1:3b is available)
        # This handles cases where a different size variant of the same model family is available
        if ($preferred -match '^(.+):(\d+[bkmg]?)$') {
            $modelFamily = $matches[1]
            $preferredVersion = $matches[2]
            
            # Look for any version of the same model family
            $familyMatch = $AvailableModels | Where-Object { $_ -like "$modelFamily*" } | Select-Object -First 1
            if ($familyMatch) {
                return $familyMatch
            }
        }
    }
    
    # Fallback: return first available model
    if ($AvailableModels.Count -gt 0) {
        return $AvailableModels[0]
    }
    
    return $null
}

# Refusal detection patterns (model responses that indicate blocking)
$script:RefusalPatterns = @(
    "i cannot (describe|generate|create|process|continue)",
    "i can't (describe|generate|create|process|continue)",
    "this content is blocked",
    "violates safety guidelines",
    "i cannot help with",
    "i'm not able to",
    "i'm unable to",
    "i cannot assist",
    "this request cannot be",
    "i cannot fulfill",
    "content policy",
    "safety policy",
    "inappropriate content",
    "cannot be generated",
    "refuse to",
    "decline to"
)

# Dark tone indicators (content that may need dark-tone routing)
# Organized by category for better detection and scoring
$script:DarkToneIndicators = @{
    "horror" = "\b(horror|horrific|terror|dread|fear|nightmare|macabre|grisly|gruesome)\b"
    "eldritch" = "\b(eldritch|lovecraft|cosmic\s+horror|unknowable|incomprehensible|maddening)\b"
    "corrupted" = "\b(corrupt(ed|ion)?|taint(ed)?|blight(ed)?|decay(ed|ing)?|rotten|putrid|foul)\b"
    "void" = "\b(void|abyss|darkness|shadow|netherworldly|otherworldly)\b"
    "gore" = "\b(blood|gore|gory|viscera|guts|entrails|innards|flesh|bone|skull)\b"
    "undead" = "\b(death|necrotic|undead|zombie|ghost|phantom|spirit|haunted|specter)\b"
    "demonic" = "\b(demon(ic)?|devil|hell|infernal|damned|cursed|unholy)\b"
    "monstrous" = "\b(abomination|monstrosity|grotesque|hideous|malformed|twisted)\b"
    "evil" = "\b(sinister|malicious|evil|wicked|malevolent|malignant|nefarious)\b"
    "glitch" = "\b(glitch(ed)?|corrupted\s+(data|code)|broken|malfunction|virus|infection|parasite|parasitic)\b"
    "organic_horror" = "\b(tentacle(d|s)?|tendril(s)?|writhing|pulsating|organic\s+(growth|mass))\b"
}

# Category weights for dark tone scoring
$script:DarkToneCategoryWeights = @{
    "eldritch" = 3.0        # Strong indicator
    "horror" = 2.0          # Strong indicator
    "gore" = 2.0            # Strong indicator
    "corrupted" = 2.0       # Strong indicator
    "monstrous" = 2.0       # Strong indicator
    "glitch" = 2.0          # Strong indicator (glitch horror)
    "organic_horror" = 2.0  # Strong indicator
    "body_horror" = 2.0     # Strong indicator (mutations, extra limbs, deformities)
    "void" = 1.5            # Moderate indicator
    "undead" = 1.5          # Moderate indicator
    "demonic" = 1.5         # Moderate indicator
    "evil" = 1.0            # Weak indicator (common in fantasy)
}

function Test-ModelRefusal {
    <#
    .SYNOPSIS
    Detects if a model response indicates refusal/blocking.
    #>
    param([string]$Response)
    
    if ([string]::IsNullOrWhiteSpace($Response)) {
        return $false
    }
    
    $responseLower = $Response.ToLower().Trim()
    
    # Check for refusal patterns
    foreach ($pattern in $script:RefusalPatterns) {
        if ($responseLower -match $pattern) {
            return $true
        }
    }
    
    # Check for very short responses that might be refusals
    if ($responseLower.Length -lt 50 -and ($responseLower -match "cannot|can't|unable|refuse|decline")) {
        return $true
    }
    
    return $false
}

function Test-DarkTone {
    <#
    .SYNOPSIS
    Detects if a prompt contains dark/horror tone indicators with weighted scoring.
    .OUTPUTS
    Hashtable with keys: ShouldRoute (bool), Score (double), Categories (array)
    #>
    param(
        [string]$Prompt,
        [switch]$Verbose
    )
    
    if ([string]::IsNullOrWhiteSpace($Prompt)) {
        return @{
            ShouldRoute = $false
            Score = 0.0
            Categories = @()
        }
    }
    
    $promptLower = $Prompt.ToLower()
    $score = 0.0
    $matchedCategories = @()
    
    # Score by category (weighted scoring)
    foreach ($category in $script:DarkToneIndicators.Keys) {
        $pattern = $script:DarkToneIndicators[$category]
        $matches = ([regex]::Matches($promptLower, $pattern)).Count
        
        if ($matches -gt 0) {
            $weight = $script:DarkToneCategoryWeights[$category]
            # Diminishing returns for multiple matches in same category
            $categoryScore = $weight * (1 + ($matches - 1) * 0.3)
            $score += $categoryScore
            $matchedCategories += @{
                Category = $category
                Matches = $matches
                Score = $categoryScore
            }
        }
    }
    
    # Threshold: score of 3.0+ indicates dark tone content
    # This typically means: 2+ strong indicators OR 1 strong + 2 moderate
    $shouldRoute = $score -ge 3.0
    
    if ($Verbose -and $shouldRoute) {
        $categoryNames = ($matchedCategories | ForEach-Object { $_.Category }) -join ", "
        Write-Host "  Dark tone score: $([math]::Round($score, 1)) - Categories: $categoryNames" -ForegroundColor Gray
    }
    
    return @{
        ShouldRoute = $shouldRoute
        Score = $score
        Categories = $matchedCategories
    }
}

function Invoke-OllamaRequest {
    <#
    .SYNOPSIS
    Sends a high-performance request to Ollama API with optimal settings.
    Supports three-tier routing: Standard → Dark-tone → Escalation (for refusal handling).
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt,
        
        [ValidateSet("code", "analysis", "visual", "simple")]
        [string]$TaskType = "analysis",
        
        [ValidateSet("short", "standard", "detailed")]
        [string]$ResponseLength = "standard",
        
        [string]$SystemPrompt = "",
        
        [string]$ModelName = "",
        
        [switch]$UseChatAPI,
        
        [switch]$AutoEscalate = $true
    )
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    # CPU throttling to maintain ~94% usage (leave 6% free)
    Invoke-CPUThrottle
    
    # Determine routing tier based on content tone
    $routingTier = $TaskType
    if ($AutoEscalate -and $TaskType -eq "visual") {
        # Check for dark tone indicators in prompt
        $toneResult = Test-DarkTone -Prompt $Prompt -Verbose
        if ($toneResult.ShouldRoute) {
            $routingTier = "dark_tone"
            Write-Host "  Dark tone detected (score: $([math]::Round($toneResult.Score, 1))), routing to Tier 2" -ForegroundColor Cyan
        }
    }
    
    # Get the appropriate model
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        # Try primary task type first
        $model = $script:AIConfig.SelectedModels[$routingTier]
        if (-not $model) {
            # Fallback to original task type
            $model = $script:AIConfig.SelectedModels[$TaskType]
            if (-not $model) {
                Write-Host "  No model available for task type: $TaskType" -ForegroundColor Yellow
                return $null
            }
        }
    }
    else {
        $model = $ModelName
    }
    
        # Determine max tokens based on response length
        $maxTokens = switch ($ResponseLength) {
            "short" { $script:AIConfig.MaxTokensSimple }
            "standard" { $script:AIConfig.MaxTokensStandard }
            "detailed" { $script:AIConfig.MaxTokensDetailed }
        }
        
        # Get optimal thread count
        $threads = Get-OptimalThreadCount
        
        # Get GPU layers (allows automatic RAM fallback when VRAM insufficient)
        $gpuLayers = 0
        if ($script:AIConfig.UseGPU -and $script:AIConfig.GPUInfo -and $script:AIConfig.GPUInfo.Available) {
            $gpuLayers = Get-OptimalGPULayers -ModelName $model -AvailableVRAMGB $script:AIConfig.GPUInfo.VRAMGB -PreferGPU
        }
        
        # Build request
        if ($UseChatAPI) {
            $messages = @()
            if (-not [string]::IsNullOrWhiteSpace($SystemPrompt)) {
                $messages += @{
                    role = "system"
                    content = $SystemPrompt
                }
            }
            $messages += @{
                role = "user"
                content = $Prompt
            }
            
            $options = @{
                num_thread = $threads
                num_predict = $maxTokens
                num_ctx = $script:AIConfig.MaxContextLength
                temperature = 0.7
                top_p = 0.9
            }
            
            # Add GPU layers if available (enables simultaneous GPU/RAM operation)
            # Setting num_gpu to a specific number means:
            # - First N layers run on GPU (using VRAM)
            # - Remaining layers run on CPU (using RAM)
            # This allows hybrid operation where both VRAM and RAM are used simultaneously
            if ($gpuLayers -gt 0) {
                $options.num_gpu = $gpuLayers
            }
            
            $body = @{
                model = $model
                messages = $messages
                stream = $false
                options = $options
            }
            
            $jsonBody = $body | ConvertTo-Json -Depth 10 -Compress
            
            try {
                $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" `
                    -Method Post `
                    -Body $jsonBody `
                    -ContentType "application/json; charset=utf-8" `
                    -TimeoutSec $script:AIConfig.RequestTimeoutSec
                
                if ($response.message -and $response.message.content) {
                    $responseText = $response.message.content.Trim()
                    
                    # Check for refusal and escalate if needed
                    if ($AutoEscalate -and (Test-ModelRefusal -Response $responseText)) {
                        Write-Host "  Model refusal detected, escalating to Tier 3..." -ForegroundColor Yellow
                        # Retry with escalation model
                        $escalationModel = $script:AIConfig.SelectedModels["escalation"]
                        if ($escalationModel -and $escalationModel -ne $model) {
                            Write-Host "  Retrying with escalation model: $escalationModel" -ForegroundColor Gray
                            # Recursive call with escalation model (prevent infinite loop)
                            return Invoke-OllamaRequest -Prompt $Prompt -TaskType $TaskType -ResponseLength $ResponseLength -SystemPrompt $SystemPrompt -ModelName $escalationModel -UseChatAPI:$UseChatAPI -AutoEscalate:$false
                        }
                        else {
                            # No escalation model available, return refusal
                            Write-Host "  No escalation model available" -ForegroundColor Yellow
                            return $responseText
                        }
                    }
                    
                    $stopwatch.Stop()
                    $elapsedMs = $stopwatch.ElapsedMilliseconds
                    Write-Host "  AI response received (${elapsedMs}ms)" -ForegroundColor Green
                    
                    # Unload model after use to free VRAM
                    Unload-OllamaModel -ModelName $model
                    
                    return $responseText
                }
            }
            catch {
                Write-Host "  AI request failed: $($_.Exception.Message)" -ForegroundColor Yellow
                # Try to unload model even on error
                Unload-OllamaModel -ModelName $model
                return $null
            }
        }
        else {
            # Use generate API
            $options = @{
                num_thread = $threads
                num_predict = $maxTokens
                num_ctx = $script:AIConfig.MaxContextLength
                temperature = 0.7
                top_p = 0.9
            }
            
            # Add GPU layers if available (enables simultaneous GPU/RAM operation)
            # Setting num_gpu to a specific number means:
            # - First N layers run on GPU (using VRAM)
            # - Remaining layers run on CPU (using RAM)
            # This allows hybrid operation where both VRAM and RAM are used simultaneously
            if ($gpuLayers -gt 0) {
                $options.num_gpu = $gpuLayers
            }
            
            $body = @{
                model = $model
                prompt = $Prompt
                stream = $false
                system = $SystemPrompt
                options = $options
            }
            
            $jsonBody = $body | ConvertTo-Json -Depth 10 -Compress
            
            try {
                $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/generate" `
                    -Method Post `
                    -Body $jsonBody `
                    -ContentType "application/json; charset=utf-8" `
                    -TimeoutSec $script:AIConfig.RequestTimeoutSec
                
                if ($response.response) {
                    $responseText = $response.response.Trim()
                    
                    # Check for refusal and escalate if needed
                    if ($AutoEscalate -and (Test-ModelRefusal -Response $responseText)) {
                        Write-Host "  Model refusal detected, escalating to Tier 3..." -ForegroundColor Yellow
                        # Unload original model before switching
                        Unload-OllamaModel -ModelName $model
                        # Retry with escalation model
                        $escalationModel = $script:AIConfig.SelectedModels["escalation"]
                        if ($escalationModel -and $escalationModel -ne $model) {
                            Write-Host "  Retrying with escalation model: $escalationModel" -ForegroundColor Gray
                            # Recursive call with escalation model (prevent infinite loop)
                            return Invoke-OllamaRequest -Prompt $Prompt -TaskType $TaskType -ResponseLength $ResponseLength -SystemPrompt $SystemPrompt -ModelName $escalationModel -UseChatAPI:$UseChatAPI -AutoEscalate:$false
                        }
                        else {
                            # No escalation model available, return refusal
                            Write-Host "  No escalation model available" -ForegroundColor Yellow
                            return $responseText
                        }
                    }
                    
                    $stopwatch.Stop()
                    $elapsedMs = $stopwatch.ElapsedMilliseconds
                    Write-Host "  AI response received (${elapsedMs}ms)" -ForegroundColor Green
                    
                    # Unload model after use to free VRAM
                    Unload-OllamaModel -ModelName $model
                    
                    return $responseText
                }
            }
            catch {
                Write-Host "  AI request failed: $($_.Exception.Message)" -ForegroundColor Yellow
                # Try to unload model even on error
                Unload-OllamaModel -ModelName $model
                return $null
            }
        }
    
    return $null
}

function Unload-OllamaModel {
    <#
    .SYNOPSIS
    Unloads an Ollama model from VRAM to free memory.
    #>
    param(
        [string]$ModelName
    )
    
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        return
    }
    
    try {
        # Use Ollama API to unload model (keep_alive: 0)
        $ollamaUrl = "$script:OllamaApiUrl/generate"
        $body = @{
            model = $ModelName
            prompt = ""
            keep_alive = 0
            stream = $false
        } | ConvertTo-Json -Compress
        
        $null = Invoke-RestMethod -Uri $ollamaUrl -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
    } catch {
        # Try CLI method as fallback
        try {
            $null = & ollama stop $ModelName 2>&1
        } catch {
            # Ignore errors - model may already be unloaded
        }
    }
}

# Export functions
Export-ModuleMember -Function Get-OptimalThreadCount, Start-OllamaIfNeeded, Test-OllamaConnection, Select-BestAvailableModel, Invoke-OllamaRequest, Get-CachedChildItem, Invoke-ThrottledFileProcessing, Invoke-CPUThrottle, Clear-FileCache, Test-ModelRefusal, Test-DarkTone, Get-GPUInfo, Get-OptimalGPULayers, Unload-OllamaModel

