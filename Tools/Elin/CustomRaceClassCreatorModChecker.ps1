<#
.SYNOPSIS
    AI-Guided Mod Checker for CustomRaceClassCreator
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Comprehensive mod validation tool that checks code, assets, configuration, and dependencies.
    Uses AI to provide intelligent suggestions and fixes for common issues.

.PARAMETER ModPath
    Path to CustomRaceClassCreator mod directory

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER CheckTypes
    Comma-separated list of checks to perform (code, assets, config, dependencies, all)
    Default: all

.PARAMETER UseAI
    Use Ollama AI for intelligent suggestions and fixes

.PARAMETER OllamaModel
    Ollama model to use (default: auto-select based on check type)

.PARAMETER FixIssues
    Automatically fix issues where possible

.PARAMETER GenerateReport
    Generate detailed HTML report

.PARAMETER Verbose
    Show detailed output

.PARAMETER SourcePaths
    Comma-separated paths to decompiled source directories for context
    Default: G:\Elin_Decompiled_source\Elin,G:\Elin_Decompiled_source\Elin.Plugins-CWL-1.21.10,G:\Elin_Decompiled_source\Plugins.Dungen,G:\Elin_Decompiled_source\Plugins.Sound,G:\Elin_Decompiled_source\System.Xml,G:\Elin_Decompiled_source\Plugins

.PARAMETER Interactive
    Enable interactive mode to provide recommendations to AI for code improvements

.EXAMPLE
    .\CustomRaceClassCreatorModChecker.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator"

.EXAMPLE
    .\CustomRaceClassCreatorModChecker.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -CheckTypes "code,assets" -UseAI -FixIssues

.EXAMPLE
    .\CustomRaceClassCreatorModChecker.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -SourcePaths "G:\Elin_Decompiled_source\Elin" -UseAI
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [string]$CheckTypes = "all",
    
    [switch]$UseAI,
    
    [string]$OllamaModel = "",
    
    [switch]$FixIssues,
    
    [switch]$GenerateReport,
    
    [switch]$Interactive,
    
    [string]$SourcePaths = "G:\Elin_Decompiled_source\Elin,G:\Elin_Decompiled_source\Elin.Plugins-CWL-1.21.10,G:\Elin_Decompiled_source\Plugins.Dungen,G:\Elin_Decompiled_source\Plugins.Sound,G:\Elin_Decompiled_source\System.Xml,G:\Elin_Decompiled_source\Plugins"
)

$ErrorActionPreference = "Continue"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for mod checking
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python")

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin (Mod Checker)" `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python")
Write-Host ""

# Use Ollama if available and requested
if ($UseAI) {
    $ollamaAvailable = Use-OllamaIfAvailable
    if (-not $ollamaAvailable) {
        Write-Host "⚠ Warning: Ollama not available, but -UseAI was specified" -ForegroundColor Yellow
        Write-Host "  Continuing without AI features..." -ForegroundColor Gray
        $UseAI = $false
    } else {
        Write-Host "✓ Ollama integration enabled" -ForegroundColor Green
    }
}

# ============================================================
# CONFIGURATION
# ============================================================

$script:OllamaUrl = "http://localhost:11434"
$script:OllamaApiUrl = "$script:OllamaUrl/api"

# AI Configuration - High Performance Settings
# Note: Mod checker runs when game is NOT running, so we can use more resources
$script:AIConfig = @{
    # Model preferences - ordered by preference (will auto-select available)
    PreferredModels = @{
        "code" = @("codellama:7b", "codellama:13b", "qwen2.5-coder:7b", "deepseek-coder:6.7b", "llama3.2:3b")
        "analysis" = @("llama3.2:3b", "mistral:7b", "qwen2.5:7b", "gemma2:9b")
        "simple" = @("llama3.2:1b", "qwen2.5:1.5b", "phi3:mini", "gemma2:2b")
    }
    # Selected models (populated at runtime)
    SelectedModels = @{
        "code" = $null
        "analysis" = $null
        "simple" = $null
    }
    # Performance settings - HIGH PERFORMANCE (game not running)
    MaxConcurrentRequests = 1           # Ollama handles one at a time anyway
    RequestTimeoutSec = 300             # 5 minutes max per request (longer for complex fixes)
    MaxTokensSimple = 512               # Longer responses for better fixes
    MaxTokensStandard = 2048            # Detailed responses for code fixes
    MaxTokensDetailed = 4096            # Very detailed analysis for complex issues
    # Resource limits - HIGH PERFORMANCE
    UseHalfCores = $false               # Use most cores (game not running)
    MaxContextLength = 262144            # Maximum context window (256k) for comprehensive analysis
    # Caching
    EnableCache = $true
    CacheMaxEntries = 100               # Larger cache
    # Rate limiting - reduced delay for faster processing
    MinDelayBetweenRequests = 200       # ms between requests (faster when game not running)
}

# AI Request cache to avoid duplicate calls
$script:AICache = @{
    Responses = @{}
    Timestamps = @{}
    LastRequestTime = [datetime]::MinValue
}

# Check type to AI task mapping
$script:CheckAIModels = @{
    "code" = "code"                     # Use code-optimized model
    "assets" = "simple"                 # Simple analysis
    "config" = "simple"                 # Simple analysis
    "dependencies" = "analysis"         # General analysis
    "cwl" = "code"                      # Code analysis
    "harmony" = "code"                  # Code analysis
}

# Results storage
$script:Results = @{
    Code = @()
    Assets = @()
    Config = @()
    Dependencies = @()
    CWL = @()
    Harmony = @()
    TODOs = @()
    Warnings = @()
    Errors = @()
    Suggestions = @()
    AIStats = @{
        RequestCount = 0
        CacheHits = 0
        TotalTokensUsed = 0
        TotalTimeMs = 0
    }
}

# Source context storage
$script:SourceContext = @{
    AvailableTypes = @()
    AvailableMethods = @()
    CWLAPIs = @()
    HarmonyPatches = @()
    CWLAdapters = @()
    SaveSafetySystems = @()
}

# Mod-specific context (cached, loaded once)
$script:ModContext = $null

# File operation cache to avoid repeated expensive scans

function Test-IsInteractiveSession {
    <#
    .SYNOPSIS
    True only when -Interactive was passed AND stdin is a live console (never hang in CI/automation).
    #>
    if (-not $Interactive) {
        return $false
    }
    try {
        if ([Environment]::UserInteractive -eq $false) {
            return $false
        }
        if ($Host.Name -eq 'ServerRemoteHost') {
            return $false
        }
        if ([Console]::IsInputRedirected) {
            return $false
        }
    }
    catch {
        return $false
    }
    return $true
}
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
# UTILITY FUNCTIONS
# ============================================================

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

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [switch]$NoNewline
    )
    if ($NoNewline) {
        Write-Host $Message -ForegroundColor $Color -NoNewline
    }
    else {
        Write-Host $Message -ForegroundColor $Color
    }
}

function Write-ProgressDetail {
    param(
        [string]$Activity,
        [string]$Status,
        [int]$PercentComplete
    )
    Write-Progress -Activity $Activity -Status $Status -PercentComplete $PercentComplete
    if ($VerbosePreference -eq 'Continue') {
        Write-ColorOutput "[$PercentComplete%] $Activity - $Status" "Cyan"
    }
}

function Get-CachedChildItem {
    <#
    .SYNOPSIS
    Cached wrapper for Get-ChildItem to avoid repeated expensive recursive scans.
    #>
    param(
        [string]$Path,
        [string]$Filter = "*",
        [switch]$Recurse,
        [switch]$File
    )
    
    # Create cache key
    $cacheKey = "$Path|$Filter|$Recurse|$File"
    
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
    
    if ($Filter -ne "*") {
        $params.Filter = $Filter
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

# ============================================================
# OLLAMA AI INTEGRATION - Resource-Efficient Implementation
# Based on: https://github.com/ollama/ollama
# ============================================================

function Get-ModSystemContext {
    <#
    .SYNOPSIS
    Gets cached mod-specific context for AI prompts.
    Loaded once and reused to minimize overhead.
    #>
    if ($null -eq $script:ModContext) {
        $script:ModContext = @"
CustomRaceClassCreator mod for Elin game. Architecture:
- CWL (Custom World Loader): REQUIRED for data/config/Excel/save-load
- Harmony patches: REQUIRED for complex runtime modifications
- ModSaveSafetyIntegration: For complex saves CWL cannot handle
- Both CWL+SaveSafety can be used together (hybrid approach)
- NEVER suggest removing used Harmony patches
- Focus on: compilation errors, missing refs, structural issues
"@
    }
    return $script:ModContext
}

function Get-OptimalThreadCount {
    <#
    .SYNOPSIS
    Gets optimal thread count for Ollama.
    Leaves 6% CPU headroom to prevent burn test behavior.
    #>
    $totalCores = [Environment]::ProcessorCount
    if ($totalCores -le 0) { $totalCores = 4 }
    
    if ($script:AIConfig.UseHalfCores) {
        $threads = [math]::Max(2, [math]::Floor($totalCores / 2))
    }
    else {
        # Leave 6% CPU headroom (use 94% of cores) to prevent system overload
        # This prevents the tool from acting like a CPU burn test
        $threads = [math]::Max(2, [math]::Floor($totalCores * 0.94))
    }
    
    return $threads
}

function Get-CacheKey {
    <#
    .SYNOPSIS
    Generates a cache key for a prompt to enable response caching.
    #>
    param([string]$Prompt, [string]$TaskType)
    
    # Create a hash of the prompt for caching
    $bytes = [System.Text.Encoding]::UTF8.GetBytes("$TaskType|$Prompt")
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return [System.BitConverter]::ToString($hash).Replace("-", "").Substring(0, 16)
}

function Get-CachedResponse {
    <#
    .SYNOPSIS
    Retrieves a cached AI response if available and not expired.
    #>
    param([string]$CacheKey)
    
    if (-not $script:AIConfig.EnableCache) { return $null }
    
    if ($script:AICache.Responses.ContainsKey($CacheKey)) {
        $timestamp = $script:AICache.Timestamps[$CacheKey]
        # Cache valid for 1 hour
        if (([datetime]::Now - $timestamp).TotalMinutes -lt 60) {
            $script:Results.AIStats.CacheHits++
            return $script:AICache.Responses[$CacheKey]
        }
        else {
            # Expired, remove
            $script:AICache.Responses.Remove($CacheKey)
            $script:AICache.Timestamps.Remove($CacheKey)
        }
    }
    return $null
}

function Set-CachedResponse {
    <#
    .SYNOPSIS
    Caches an AI response for future reuse.
    #>
    param([string]$CacheKey, [string]$Response)
    
    if (-not $script:AIConfig.EnableCache) { return }
    
    # Limit cache size
    if ($script:AICache.Responses.Count -ge $script:AIConfig.CacheMaxEntries) {
        # Remove oldest entry
        $oldest = $script:AICache.Timestamps.GetEnumerator() | Sort-Object Value | Select-Object -First 1
        if ($oldest) {
            $script:AICache.Responses.Remove($oldest.Key)
            $script:AICache.Timestamps.Remove($oldest.Key)
        }
    }
    
    $script:AICache.Responses[$CacheKey] = $Response
    $script:AICache.Timestamps[$CacheKey] = [datetime]::Now
}

function Wait-ForRateLimit {
    <#
    .SYNOPSIS
    Enforces rate limiting between AI requests.
    #>
    $elapsed = ([datetime]::Now - $script:AICache.LastRequestTime).TotalMilliseconds
    $minDelay = $script:AIConfig.MinDelayBetweenRequests
    
    if ($elapsed -lt $minDelay) {
        $waitTime = $minDelay - $elapsed
        Start-Sleep -Milliseconds $waitTime
    }
    
    $script:AICache.LastRequestTime = [datetime]::Now
}

function Invoke-OllamaRequest {
    <#
    .SYNOPSIS
    Sends a resource-efficient request to Ollama API.
    Features: caching, rate limiting, optimal threading, smart model selection.
    Based on: https://github.com/ollama/ollama/blob/main/docs/api.md
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt,
        
        [ValidateSet("code", "analysis", "simple")]
        [string]$TaskType = "analysis",
        
        [ValidateSet("short", "standard", "detailed")]
        [string]$ResponseLength = "standard",
        
        [string]$AdditionalContext = "",
        
        [switch]$SkipCache
    )
    
    if (-not $UseAI) { return $null }
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    # CPU throttling to maintain ~94% usage (leave 6% free)
    Invoke-CPUThrottle
    
    # Check cache first
    $cacheKey = Get-CacheKey -Prompt $Prompt -TaskType $TaskType
    if (-not $SkipCache) {
        $cached = Get-CachedResponse -CacheKey $cacheKey
        if ($cached) {
            Write-ColorOutput "  [Cache hit]" "Gray"
            return $cached
        }
    }
    
    # Get the appropriate model
    $model = $script:AIConfig.SelectedModels[$TaskType]
    if (-not $model) {
        Write-ColorOutput "  No model available for task type: $TaskType" "Yellow"
        return $null
    }
    
    # Rate limiting
    Wait-ForRateLimit
    
    try {
        # Determine max tokens based on response length
        $maxTokens = switch ($ResponseLength) {
            "short" { $script:AIConfig.MaxTokensSimple }
            "standard" { $script:AIConfig.MaxTokensStandard }
            "detailed" { $script:AIConfig.MaxTokensDetailed }
        }
        
        # Get optimal thread count
        $threads = Get-OptimalThreadCount
        
        # Build efficient prompt
        $systemPrompt = Get-ModSystemContext
        $fullPrompt = if ($AdditionalContext) {
            "$AdditionalContext`n`n$Prompt"
        } else {
            $Prompt
        }
        
        # Truncate prompt if too long (save context window)
        $maxPromptLength = $script:AIConfig.MaxContextLength - $maxTokens - 500
        if ($fullPrompt.Length -gt $maxPromptLength) {
            $fullPrompt = $fullPrompt.Substring(0, $maxPromptLength) + "`n[truncated for efficiency]"
        }
        
        # Build request per Ollama API spec
        $body = @{
            model = $model
            prompt = $fullPrompt
            stream = $false
            system = $systemPrompt
            options = @{
                num_thread = $threads
                num_predict = $maxTokens
                num_ctx = $script:AIConfig.MaxContextLength
                temperature = 0.7
                top_p = 0.9
            }
        }
        
        Write-ColorOutput "  AI: $model (threads: $threads, max_tokens: $maxTokens)" "Gray"
        
        $jsonBody = $body | ConvertTo-Json -Depth 10 -Compress
        
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/generate" `
            -Method Post `
            -Body $jsonBody `
            -ContentType "application/json; charset=utf-8" `
            -TimeoutSec $script:AIConfig.RequestTimeoutSec
        
        $script:Results.AIStats.RequestCount++
        
        if ($response.response) {
            $result = $response.response.Trim()
            
            # Track token usage if available
            if ($response.eval_count) {
                $script:Results.AIStats.TotalTokensUsed += $response.eval_count
            }
            
            # Cache the response
            Set-CachedResponse -CacheKey $cacheKey -Response $result
            
            $stopwatch.Stop()
            $script:Results.AIStats.TotalTimeMs += $stopwatch.ElapsedMilliseconds
            
            $elapsedMs = $stopwatch.ElapsedMilliseconds
            Write-ColorOutput "  AI response received (${elapsedMs}ms)" "Green"
            return $result
        }
        else {
            Write-ColorOutput "  AI returned empty response" "Yellow"
            return $null
        }
    }
    catch {
        $stopwatch.Stop()
        Write-ColorOutput "  AI request failed: $($_.Exception.Message)" "Yellow"
        return $null
    }
}

function Invoke-OllamaCodeAnalysis {
    <#
    .SYNOPSIS
    Specialized function for code analysis - uses code-optimized model.
    #>
    param(
        [string]$Code,
        [string]$Question,
        [string]$FileName = ""
    )
    
    $context = if ($FileName) { "File: $FileName`n" } else { "" }
    $prompt = @"
$context
Code:
$Code

Question: $Question

Provide a concise fix. No explanations unless asked.
"@
    
    return Invoke-OllamaRequest -Prompt $prompt -TaskType "code" -ResponseLength "standard"
}

function Apply-AIFixes {
    <#
    .SYNOPSIS
    Parses AI suggestions and applies fixes to source files with Y/N confirmation.
    Shows alternatives and lets user choose.
    #>
    param(
        [string]$Suggestion,
        [array]$ErrorLines,
        [array]$ErrorFiles
    )
    
    if (-not $Suggestion -or -not $FixIssues) {
        return
    }
    
    $fixesApplied = 0
    $fixesFailed = 0
    $fixesSkipped = 0
    
    # Parse AI response for FILE/LINE/OLD/NEW format and alternatives
    $fixBlocks = @()
    $alternatives = @()
    $currentFix = @{
        File = $null
        Line = 0
        Old = ""
        New = ""
        Reason = ""
        Priority = "medium"
        Alternatives = @()
    }
    $currentSection = ""
    $inAlternative = $false
    $currentAlternative = $null
    
    $lines = $Suggestion -split "`n"
    foreach ($line in $lines) {
        $line = $line.Trim()
        
        if ($line -match '^FILE:\s*(.+)' -and -not $inAlternative) {
            # Save previous fix if complete
            if ($currentFix.File -and $currentFix.Line -gt 0 -and $currentFix.New) {
                $fixBlocks += $currentFix
            }
            # Start new fix
            $currentFix = @{
                File = $matches[1].Trim()
                Line = 0
                Old = ""
                New = ""
                Reason = ""
                Priority = "medium"
                Alternatives = @()
            }
            $currentSection = ""
            $inAlternative = $false
        }
        elseif ($line -match '^ALTERNATIVE\s+(\d+):') {
            # Save current fix if we're starting an alternative
            if ($currentFix.File -and $currentFix.Line -gt 0 -and $currentFix.New -and $currentFix.Alternatives.Count -eq 0) {
                # Don't add yet, wait for alternatives
            }
            $inAlternative = $true
            $currentAlternative = @{
                Number = [int]$matches[1]
                File = $currentFix.File
                Line = $currentFix.Line
                Approach = ""
                Old = ""
                New = ""
                Pros = ""
                Cons = ""
            }
            $currentSection = ""
        }
        elseif ($line -match '^LINE:\s*(\d+)') {
            if ($inAlternative) {
                $currentAlternative.Line = [int]$matches[1]
            }
            else {
                $currentFix.Line = [int]$matches[1]
            }
            $currentSection = ""
        }
        elseif ($line -match '^APPROACH:') {
            $currentSection = "APPROACH"
            $currentAlternative.Approach = ""
        }
        elseif ($line -match '^OLD:') {
            $currentSection = "OLD"
            if ($inAlternative) {
                $currentAlternative.Old = ""
            }
            else {
                $currentFix.Old = ""
            }
        }
        elseif ($line -match '^NEW:') {
            $currentSection = "NEW"
            if ($inAlternative) {
                $currentAlternative.New = ""
            }
            else {
                $currentFix.New = ""
            }
        }
        elseif ($line -match '^REASON:') {
            $currentSection = "REASON"
            $currentFix.Reason = ""
        }
        elseif ($line -match '^PRIORITY:') {
            $currentSection = "PRIORITY"
        }
        elseif ($line -match '^PROS:') {
            $currentSection = "PROS"
            $currentAlternative.Pros = ""
        }
        elseif ($line -match '^CONS:') {
            $currentSection = "CONS"
            $currentAlternative.Cons = ""
        }
        elseif ($currentSection -eq "APPROACH" -and $line) {
            $currentAlternative.Approach += $line + " "
        }
        elseif ($currentSection -eq "OLD" -and $line) {
            if ($inAlternative) {
                $currentAlternative.Old += $line + "`n"
            }
            else {
                $currentFix.Old += $line + "`n"
            }
        }
        elseif ($currentSection -eq "NEW" -and $line) {
            if ($inAlternative) {
                $currentAlternative.New += $line + "`n"
            }
            else {
                $currentFix.New += $line + "`n"
            }
        }
        elseif ($currentSection -eq "REASON" -and $line) {
            $currentFix.Reason += $line + " "
        }
        elseif ($currentSection -eq "PRIORITY" -and $line) {
            $currentFix.Priority = $line.ToLower()
        }
        elseif ($currentSection -eq "PROS" -and $line) {
            $currentAlternative.Pros += $line + " "
        }
        elseif ($currentSection -eq "CONS" -and $line) {
            $currentAlternative.Cons += $line + " "
        }
        # Check if we're done with current alternative
        elseif ($inAlternative -and ($line -match '^FILE:' -or $line -match '^ALTERNATIVE' -or ($line -eq "" -and $currentAlternative.New))) {
            if ($currentAlternative.New) {
                $currentFix.Alternatives += $currentAlternative
            }
            $inAlternative = $false
            $currentAlternative = $null
        }
    }
    
    # Save last fix
    if ($currentFix.File -and $currentFix.Line -gt 0 -and $currentFix.New) {
        if ($currentAlternative -and $currentAlternative.New) {
            $currentFix.Alternatives += $currentAlternative
        }
        $fixBlocks += $currentFix
    }
    
    # Apply each fix with Y/N confirmation
    $autoApply = $false
    $skipAll = $false
    
    foreach ($fix in $fixBlocks) {
        if ($skipAll) {
            $fixesSkipped++
            continue
        }
        
        $fix.Old = $fix.Old.Trim()
        $fix.New = $fix.New.Trim()
        $fix.Reason = $fix.Reason.Trim()
        
        Write-ColorOutput "`n--- Fix for $($fix.File) at line $($fix.Line) ---" "Cyan"
        Write-ColorOutput "Reason: $($fix.Reason)" "White"
        Write-ColorOutput "Priority: $($fix.Priority)" "Gray"
        Write-ColorOutput "`nOLD CODE:" "Yellow"
        Write-ColorOutput $fix.Old "Gray"
        Write-ColorOutput "`nNEW CODE:" "Green"
        Write-ColorOutput $fix.New "Gray"
        
        # Show alternatives if available
        if ($fix.Alternatives.Count -gt 0) {
            Write-ColorOutput "`n--- Alternative Options ---" "Cyan"
            for ($i = 0; $i -lt $fix.Alternatives.Count; $i++) {
                $alt = $fix.Alternatives[$i]
                Write-ColorOutput "`n[$($i + 1)] Alternative $($i + 1):" "Yellow"
                Write-ColorOutput "  Approach: $($alt.Approach.Trim())" "White"
                if ($alt.Pros) {
                    Write-ColorOutput "  Pros: $($alt.Pros.Trim())" "Green"
                }
                if ($alt.Cons) {
                    Write-ColorOutput "  Cons: $($alt.Cons.Trim())" "Red"
                }
                Write-ColorOutput "  OLD: $($alt.Old.Trim().Substring(0, [Math]::Min(80, $alt.Old.Trim().Length)))..." "Gray"
                Write-ColorOutput "  NEW: $($alt.New.Trim().Substring(0, [Math]::Min(80, $alt.New.Trim().Length)))..." "Gray"
            }
        }
        
        # Ask for recommendation (default behavior - no Y/N, just recommend what you want)
        if (-not $autoApply -and -not $skipAll) {
            if (-not (Test-IsInteractiveSession)) {
                Write-ColorOutput "  ⊘ Skipped (non-interactive; use -Interactive to review fixes)" "Gray"
                $fixesSkipped++
                continue
            }
            $promptText = "`nRecommend what you want implemented (or Enter=accept fix"
            if ($fix.Alternatives.Count -gt 0) {
                $promptText += "/1-$($fix.Alternatives.Count)=alternative"
            }
            $promptText += "/A=apply all/S=skip all): "
            Write-ColorOutput $promptText "Yellow" -NoNewline
            $response = Read-Host
            
            if ([string]::IsNullOrWhiteSpace($response) -or $response -match '^(accept|ok|yes|y)$') {
                # User pressed Enter or typed accept - accept the primary fix
                if (Apply-SingleFix -FileName $fix.File -LineNumber $fix.Line -OldCode $fix.Old -NewCode $fix.New) {
                    $fixesApplied++
                    Write-ColorOutput "  ✓ Fix applied" "Green"
                }
                else {
                    $fixesFailed++
                    Write-ColorOutput "  ✗ Fix failed" "Yellow"
                }
            }
            elseif ($response -match '^[Aa]') {
                # Apply all remaining fixes automatically
                $autoApply = $true
                if (Apply-SingleFix -FileName $fix.File -LineNumber $fix.Line -OldCode $fix.Old -NewCode $fix.New) {
                    $fixesApplied++
                    Write-ColorOutput "  ✓ Fix applied (auto-apply enabled)" "Green"
                }
                else {
                    $fixesFailed++
                    Write-ColorOutput "  ✗ Fix failed" "Yellow"
                }
            }
            elseif ($response -match '^[Ss]') {
                $fixesSkipped++
                Write-ColorOutput "  ⊘ Fix skipped (skipping all remaining)" "Gray"
                $skipAll = $true
            }
            elseif ($response -match '^[1-9]' -and $fix.Alternatives.Count -gt 0) {
                # User chose an alternative by number
                $altIndex = [int]$response - 1
                if ($altIndex -ge 0 -and $altIndex -lt $fix.Alternatives.Count) {
                    $alt = $fix.Alternatives[$altIndex]
                    Write-ColorOutput "  Applying Alternative $($altIndex + 1)..." "Cyan"
                    if (Apply-SingleFix -FileName $alt.File -LineNumber $alt.Line -OldCode $alt.Old.Trim() -NewCode $alt.New.Trim()) {
                        $fixesApplied++
                        Write-ColorOutput "  ✓ Alternative fix applied" "Green"
                    }
                    else {
                        $fixesFailed++
                        Write-ColorOutput "  ✗ Alternative fix failed" "Yellow"
                    }
                }
            }
            else {
                # User provided a recommendation - get AI implementation
                Write-ColorOutput "`nGetting AI implementation for your recommendation..." "Cyan"
                $targetFile = Get-CachedChildItem -Path $ModPath -Filter $fix.File -Recurse -File | Select-Object -First 1
                
                # Build recommendation with context about the current fix
                $recommendation = "Current AI fix suggestion: Replace '$($fix.Old.Substring(0, [Math]::Min(100, $fix.Old.Length)))...' with '$($fix.New.Substring(0, [Math]::Min(100, $fix.New.Length)))...'`n"
                $recommendation += "User recommendation: $response`n"
                $recommendation += "Please show how to implement this recommendation instead."
                
                $implementation = Get-AIImplementationSuggestion -Recommendation $recommendation -TargetFile $targetFile
                
                if ($implementation) {
                    $applied = Show-ImplementationOptions -Implementation $implementation -TargetFile $targetFile -OriginalFix $fix
                    if ($applied) {
                        $fixesApplied++
                    }
                    else {
                        # Fall back to original fix if user didn't apply recommendation
                        Write-ColorOutput "  Applying original AI fix as fallback..." "Cyan"
                        if (Apply-SingleFix -FileName $fix.File -LineNumber $fix.Line -OldCode $fix.Old -NewCode $fix.New) {
                            $fixesApplied++
                            Write-ColorOutput "  ✓ Original fix applied" "Green"
                        }
                        else {
                            $fixesFailed++
                            Write-ColorOutput "  ✗ Fix failed" "Yellow"
                        }
                    }
                }
                else {
                    Write-ColorOutput "  ⚠ Could not get AI implementation. Applying original fix..." "Yellow"
                    if (Apply-SingleFix -FileName $fix.File -LineNumber $fix.Line -OldCode $fix.Old -NewCode $fix.New) {
                        $fixesApplied++
                        Write-ColorOutput "  ✓ Original fix applied" "Green"
                    }
                    else {
                        $fixesFailed++
                        Write-ColorOutput "  ✗ Fix failed" "Yellow"
                    }
                }
            }
        }
        elseif ($autoApply) {
            # Auto-apply mode
            if (Apply-SingleFix -FileName $fix.File -LineNumber $fix.Line -OldCode $fix.Old -NewCode $fix.New) {
                $fixesApplied++
                Write-ColorOutput "  ✓ Fix applied (auto-apply)" "Green"
            }
            else {
                $fixesFailed++
                Write-ColorOutput "  ✗ Fix failed" "Yellow"
            }
        }
    }
    
    if ($fixesApplied -gt 0) {
        Write-ColorOutput "`n  ✓ Successfully applied $fixesApplied fix(es)" "Green"
        if ($fixesFailed -gt 0) {
            Write-ColorOutput "  ✗ Failed to apply $fixesFailed fix(es)" "Yellow"
        }
        if ($fixesSkipped -gt 0) {
            Write-ColorOutput "  ⊘ Skipped $fixesSkipped fix(es)" "Gray"
        }
        Write-ColorOutput "  Rebuilding project to verify fixes..." "Cyan"
    }
    elseif ($fixBlocks.Count -eq 0) {
        Write-ColorOutput "  ⚠ Could not parse structured fixes from AI response" "Yellow"
        Write-ColorOutput "     AI may need to provide fixes in FILE/LINE/OLD/NEW format" "Yellow"
    }
}

function Apply-SingleFix {
    <#
    .SYNOPSIS
    Applies a single fix to a source file by replacing OLD code with NEW code.
    #>
    param(
        [string]$FileName,
        [int]$LineNumber,
        [string]$OldCode,
        [string]$NewCode
    )
    
    try {
        # Find the file
        $file = Get-CachedChildItem -Path $ModPath -Filter $FileName -Recurse -File | Select-Object -First 1
        if (-not $file) {
            Write-ColorOutput "      File not found: $FileName" "Yellow"
            return $false
        }
        
        # Create backup
        $backupPath = "$($file.FullName).backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
        Copy-Item $file.FullName $backupPath -ErrorAction SilentlyContinue
        Write-ColorOutput "      Backup: $(Split-Path $backupPath -Leaf)" "Gray"
        
        # Read file content
        $content = Get-Content $file.FullName -Raw
        $lines = $content -split "`n"
        
        if ($LineNumber -gt $lines.Count -or $LineNumber -lt 1) {
            Write-ColorOutput "      Line $LineNumber out of range (file has $($lines.Count) lines)" "Yellow"
            return $false
        }
        
        # Find the OLD code in the file (search around the line number)
        $searchStart = [Math]::Max(0, $LineNumber - 10)
        $searchEnd = [Math]::Min($lines.Count, $LineNumber + 10)
        $searchRegion = $lines[$searchStart..($searchEnd - 1)] -join "`n"
        
        # Try to find exact match of OLD code
        $oldLines = $OldCode -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        $oldPattern = [regex]::Escape($OldCode.Trim())
        
        # Try direct replacement
        if ($content -match $oldPattern) {
            $newContent = $content -replace $oldPattern, $NewCode.Trim()
            Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8 -NoNewline
            Write-ColorOutput "      Applied fix (exact match)" "Green"
            return $true
        }
        
        # Try line-by-line replacement around the error line
        $oldLineCount = ($OldCode -split "`n").Count
        $newLineCount = ($NewCode -split "`n").Count
        
        # Replace lines starting at LineNumber
        $newLines = @()
        $replaced = $false
        $skipCount = 0
        
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if (-not $replaced -and $i -eq ($LineNumber - 1)) {
                # Check if the next few lines match OLD code
                $matchRegion = ($lines[$i..([Math]::Min($i + $oldLineCount - 1, $lines.Count - 1))] -join "`n").Trim()
                $oldTrimmed = $OldCode.Trim()
                
                if ($matchRegion -eq $oldTrimmed -or 
                    ($matchRegion -match [regex]::Escape($oldTrimmed)) -or
                    ($oldTrimmed -match [regex]::Escape($matchRegion))) {
                    # Replace with NEW code
                    $newLines += ($NewCode -split "`n")
                    $skipCount = $oldLineCount - 1
                    $replaced = $true
                    Write-ColorOutput "      Applied fix (line replacement)" "Green"
                    continue
                }
                else {
                    # Try to insert NEW code at this line
                    $newLines += ($NewCode -split "`n")
                    $replaced = $true
                    Write-ColorOutput "      Applied fix (inserted at line)" "Green"
                    continue
                }
            }
            
            if ($skipCount -gt 0) {
                $skipCount--
                continue
            }
            
            $newLines += $lines[$i]
        }
        
        if ($replaced) {
            $newContent = $newLines -join "`n"
            Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8 -NoNewline
            return $true
        }
        else {
            Write-ColorOutput "      Could not find OLD code to replace" "Yellow"
            Write-ColorOutput "      OLD: $($OldCode.Substring(0, [Math]::Min(50, $OldCode.Length)))..." "Gray"
            return $false
        }
    }
    catch {
        Write-ColorOutput "      Error: $_" "Red"
        return $false
    }
}

function Invoke-OllamaQuickCheck {
    <#
    .SYNOPSIS
    Quick yes/no or simple answer check - uses smallest model.
    #>
    param([string]$Question)
    
    return Invoke-OllamaRequest -Prompt $Question -TaskType "simple" -ResponseLength "short"
}

function Invoke-OllamaBatchAnalysis {
    <#
    .SYNOPSIS
    Analyzes multiple items efficiently by batching into single request.
    #>
    param(
        [array]$Items,
        [string]$AnalysisType,
        [int]$MaxItemsPerBatch = 5
    )
    
    $results = @()
    $batches = for ($i = 0; $i -lt $Items.Count; $i += $MaxItemsPerBatch) {
        $Items[$i..([math]::Min($i + $MaxItemsPerBatch - 1, $Items.Count - 1))]
    }
    
    foreach ($batch in $batches) {
        $batchText = ($batch | ForEach-Object { "- $_" }) -join "`n"
        $prompt = "Analyze these $AnalysisType issues briefly (one line each):`n$batchText"
        
        $response = Invoke-OllamaRequest -Prompt $prompt -TaskType "analysis" -ResponseLength "standard"
        if ($response) {
            $results += $response
        }
    }
    
    return $results -join "`n"
}

function Get-AvailableOllamaModels {
    <#
    .SYNOPSIS
    Gets list of available Ollama models with their sizes.
    #>
    try {
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 10
        if ($response.models) {
            return $response.models | ForEach-Object {
                @{
                    Name = $_.name
                    Size = if ($_.size) { [math]::Round($_.size / 1GB, 2) } else { 0 }
                    Modified = $_.modified_at
                }
            }
        }
        return @()
    }
    catch {
        return @()
    }
}

function Select-BestAvailableModel {
    <#
    .SYNOPSIS
    Selects the best available model from a preference list.
    #>
    param(
        [array]$PreferredModels,
        [array]$AvailableModels
    )
    
    foreach ($preferred in $PreferredModels) {
        # Check exact match
        if ($AvailableModels -contains $preferred) {
            return $preferred
        }
        # Check partial match (e.g., "codellama:7b" matches "codellama:7b-instruct")
        $baseName = $preferred.Split(':')[0]
        $matching = $AvailableModels | Where-Object { $_ -like "$baseName*" } | Select-Object -First 1
        if ($matching) {
            return $matching
        }
    }
    
    # Fallback: return first available model
    if ($AvailableModels.Count -gt 0) {
        return $AvailableModels[0]
    }
    
    return $null
}

function Start-OllamaIfNeeded {
    <#
    .SYNOPSIS
    Attempts to start Ollama if it's not running.
    #>
    # Check if ollama command is available
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaCmd) {
        Write-ColorOutput "  Ollama command not found in PATH" "Yellow"
        return $false
    }
    
    # Check if Ollama is already running
    try {
        $null = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 1 -ErrorAction Stop
        return $true
    }
    catch {
        # Ollama is not running, try to start it
        Write-ColorOutput "  Starting Ollama in background..." "Cyan"
        try {
            $process = Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru -ErrorAction Stop
            Write-ColorOutput "  Ollama process started (PID: $($process.Id))" "Gray"
            
            # Wait for Ollama to become available (max 30 seconds)
            $maxWait = 30
            $waited = 0
            while ($waited -lt $maxWait) {
                Start-Sleep -Seconds 2
                $waited += 2
                try {
                    $null = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 1 -ErrorAction Stop
                    Write-ColorOutput "  Ollama is now available" "Green"
                    return $true
                }
                catch {
                    Write-ColorOutput "  Waiting for Ollama... ($waited/$maxWait seconds)" "Gray"
                }
            }
            
            Write-ColorOutput "  Ollama did not become available within $maxWait seconds" "Yellow"
            return $false
        }
        catch {
            Write-ColorOutput "  Failed to start Ollama: $($_.Exception.Message)" "Yellow"
            return $false
        }
    }
}

function Test-OllamaConnection {
    <#
    .SYNOPSIS
    Tests Ollama connection and auto-selects best available models for each task type.
    Automatically starts Ollama if it's not running.
    #>
    try {
        # Quick connection test with short timeout
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        
        if (-not $response.models -or $response.models.Count -eq 0) {
            Write-ColorOutput "  No models found in Ollama" "Yellow"
            Write-ColorOutput "  Please install at least one model: ollama pull llama3.2:3b" "Gray"
            return $false
        }
        
        $availableModels = $response.models | ForEach-Object { $_.name }
        Write-ColorOutput "  Available models: $($availableModels.Count)" "Gray"
        
        # Select best model for each task type
        $modelSelections = @()
        foreach ($taskType in $script:AIConfig.PreferredModels.Keys) {
            $preferences = $script:AIConfig.PreferredModels[$taskType]
            $selected = Select-BestAvailableModel -PreferredModels $preferences -AvailableModels $availableModels
            
            if ($selected) {
                $script:AIConfig.SelectedModels[$taskType] = $selected
                $modelSelections += "  $taskType : $selected"
            }
            else {
                Write-ColorOutput "  Warning: No model available for $taskType tasks" "Yellow"
            }
        }
        
        Write-ColorOutput "  Model selection:" "Cyan"
        $modelSelections | ForEach-Object { Write-ColorOutput $_ "Gray" }
        
        # Show resource settings
        $threads = Get-OptimalThreadCount
        Write-ColorOutput "  Threads: $threads (of $([Environment]::ProcessorCount) cores)" "Gray"
        Write-ColorOutput "  Cache: $(if ($script:AIConfig.EnableCache) { 'enabled' } else { 'disabled' })" "Gray"
        
        return ($script:AIConfig.SelectedModels.Values | Where-Object { $_ }).Count -gt 0
    }
    catch {
        $errorMsg = $_.Exception.Message
        if ($errorMsg -match "timeout|connection|refused|unreachable") {
            Write-ColorOutput "  Ollama is not running" "Yellow"
            
            # Try to start Ollama automatically
            if (Start-OllamaIfNeeded) {
                # Retry connection after starting
                try {
                    $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
                    if ($response.models -and $response.models.Count -gt 0) {
                        # Process models (same logic as successful connection above)
                        $availableModels = $response.models | ForEach-Object { $_.name }
                        Write-ColorOutput "  Available models: $($availableModels.Count)" "Gray"
                        
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
                        
                        Write-ColorOutput "  Model selection:" "Cyan"
                        $modelSelections | ForEach-Object { Write-ColorOutput $_ "Gray" }
                        
                        $threads = Get-OptimalThreadCount
                        Write-ColorOutput "  Threads: $threads (of $([Environment]::ProcessorCount) cores)" "Gray"
                        
                        return ($script:AIConfig.SelectedModels.Values | Where-Object { $_ }).Count -gt 0
                    }
                }
                catch {
                    Write-ColorOutput "  Still cannot connect to Ollama after starting it" "Red"
                    return $false
                }
            }
            else {
                Write-ColorOutput "`n❌ ERROR: Ollama is required for this mod checker" "Red"
                Write-ColorOutput "  The mod checker requires AI to function properly." "Yellow"
                Write-ColorOutput "`n  To fix this:" "Cyan"
                Write-ColorOutput "  1. Install Ollama from https://ollama.com" "White"
                Write-ColorOutput "  2. Start Ollama manually: ollama serve" "White"
                Write-ColorOutput "  3. Install at least one model: ollama pull llama3.2:3b" "White"
                Write-ColorOutput "  4. Then run this script again" "White"
                Write-ColorOutput ""
                return $false
            }
        }
        else {
            Write-ColorOutput "  Connection error: $errorMsg" "Yellow"
            return $false
        }
    }
}

function Show-AIStats {
    <#
    .SYNOPSIS
    Displays AI usage statistics.
    #>
    $stats = $script:Results.AIStats
    if ($stats.RequestCount -gt 0) {
        Write-ColorOutput "`nAI Usage Statistics:" "Cyan"
        Write-ColorOutput "  Requests: $($stats.RequestCount)" "White"
        Write-ColorOutput "  Cache hits: $($stats.CacheHits)" "White"
        Write-ColorOutput "  Tokens used: $($stats.TotalTokensUsed)" "White"
        Write-ColorOutput "  Total time: $([math]::Round($stats.TotalTimeMs / 1000, 1))s" "White"
        if ($stats.RequestCount -gt 0) {
            $avgTime = [math]::Round($stats.TotalTimeMs / $stats.RequestCount)
            Write-ColorOutput "  Avg response time: ${avgTime}ms" "White"
        }
    }
}

function Show-FileScanSummary {
    <#
    .SYNOPSIS
    Displays a summary of files scanned.
    #>
    Write-ColorOutput "`n--- File Scan Summary ---" "Cyan"
    Write-ColorOutput "Total files found: $($script:FileScanStats.TotalFound)" "White"
    Write-ColorOutput "Build artifacts excluded: $($script:FileScanStats.UnityExcluded)" "Gray"
    Write-ColorOutput "Mod files to process: $($script:FileScanStats.ModFilesProcessed)" "Green"
    
    if ($VerbosePreference -eq 'Continue' -and $script:FileScanStats.ByDirectory.Count -gt 0) {
        Write-ColorOutput "Files by directory:" "Cyan"
        foreach ($dir in $script:FileScanStats.ByDirectory.Keys | Sort-Object) {
            $shortDir = $dir.Replace($ModPath, ".")
            Write-ColorOutput "  $shortDir : $($script:FileScanStats.ByDirectory[$dir])" "Gray"
        }
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Track file scanning statistics
$script:FileScanStats = @{
    TotalFound = 0
    UnityExcluded = 0
    ModFilesProcessed = 0
    ByDirectory = @{}
}

function Is-UnityFile {
    <#
    .SYNOPSIS
    Checks if a file is Unity-related and should be excluded from mod checks.
    Only excludes files that are clearly Unity engine files, not mod files that use Unity APIs.
    #>
    param(
        [System.IO.FileInfo]$File,
        [switch]$CheckContent
    )
    
    $fullPath = $File.FullName
    
    # ONLY exclude files in these specific Unity-related directories
    # Be very conservative - we don't want to exclude actual mod files
    $unityPathPatterns = @(
        '\\Library\\ScriptAssemblies\\',
        '\\Library\\PackageCache\\',
        '\\Temp\\UnityLockfile',
        '\\obj\\Debug\\',
        '\\obj\\Release\\',
        '\\bin\\Debug\\',
        '\\bin\\Release\\'
    )
    
    foreach ($pattern in $unityPathPatterns) {
        if ($fullPath -match [regex]::Escape($pattern) -or $fullPath -match $pattern) {
            return $true
        }
    }
    
    # Only exclude files named exactly like Unity engine files
    $unityExactNames = @(
        'AssemblyInfo.cs'
    )
    
    if ($unityExactNames -contains $File.Name) {
        return $true
    }
    
    # Do NOT exclude files just because they reference UnityEngine
    # Mods legitimately use UnityEngine APIs
    
    return $false
}

function Get-ModCsFiles {
    <#
    .SYNOPSIS
    Gets C# files from the mod directory, excluding only build artifacts.
    Includes detailed logging of what files are found.
    #>
    param(
        [string]$Path,
        [string]$Filter = "*.cs",
        [switch]$Recurse,
        [switch]$Verbose
    )
    
    # Get all matching files (use cached version to avoid repeated scans)
    $allFiles = if ($Recurse) {
        Get-CachedChildItem -Path $Path -Filter $Filter -Recurse -File
    }
    else {
        Get-CachedChildItem -Path $Path -Filter $Filter -File
    }
    
    $script:FileScanStats.TotalFound = $allFiles.Count
    
    # Filter out Unity build artifacts only
    $modFiles = @()
    $excludedFiles = @()
    
    foreach ($file in $allFiles) {
        if (Is-UnityFile -File $file) {
            $excludedFiles += $file
            $script:FileScanStats.UnityExcluded++
        }
        else {
            $modFiles += $file
            $script:FileScanStats.ModFilesProcessed++
            
            # Track by directory
            $dir = $file.DirectoryName
            if (-not $script:FileScanStats.ByDirectory.ContainsKey($dir)) {
                $script:FileScanStats.ByDirectory[$dir] = 0
            }
            $script:FileScanStats.ByDirectory[$dir]++
        }
    }
    
    if ($VerbosePreference -eq 'Continue' -or $Verbose) {
        Write-ColorOutput "  File scan: Found $($allFiles.Count) total, excluded $($excludedFiles.Count) build artifacts, processing $($modFiles.Count) mod files" "Cyan"
        if ($excludedFiles.Count -gt 0) {
            Write-ColorOutput "  Excluded files:" "Gray"
            foreach ($ex in $excludedFiles) {
                Write-ColorOutput "    - $($ex.FullName)" "Gray"
            }
        }
    }
    
    return $modFiles
}

function Get-AllModFiles {
    <#
    .SYNOPSIS
    Gets ALL files from the mod directory for comprehensive scanning.
    Returns a hashtable organized by file type.
    #>
    param(
        [string]$Path
    )
    
    $result = @{
        CSharp = @()
        Json = @()
        Xml = @()
        Excel = @()
        Markdown = @()
        Other = @()
    }
    
    $allFiles = Get-CachedChildItem -Path $Path -Recurse -File
    
    foreach ($file in $allFiles) {
        # Skip build artifacts
        if (Is-UnityFile -File $file) { continue }
        
        switch -Regex ($file.Extension.ToLower()) {
            '\.cs$' { $result.CSharp += $file }
            '\.json$' { $result.Json += $file }
            '\.xml$|\.csproj$|\.props$' { $result.Xml += $file }
            '\.xlsx?$' { $result.Excel += $file }
            '\.md$' { $result.Markdown += $file }
            default { $result.Other += $file }
        }
    }
    
    return $result
}

# ============================================================
# SOURCE CONTEXT BUILDING
# ============================================================

function Build-SourceContext {
    Write-ProgressDetail "Context Building" "Scanning decompiled source..." 5
    
    $sourceDirs = $SourcePaths -split ',' | ForEach-Object { $_.Trim() }
    $totalTypes = 0
    $totalMethods = 0
    
    foreach ($sourceDir in $sourceDirs) {
        if (-not (Test-Path $sourceDir)) {
            Write-ColorOutput "Warning: Source directory not found: $sourceDir" "Yellow"
            continue
        }
        
        Write-ColorOutput "Scanning: $sourceDir" "Cyan"
        # Use cached Get-ChildItem to avoid repeated expensive scans
        $csFiles = Get-CachedChildItem -Path $sourceDir -Filter "*.cs" -Recurse -File
        # Note: Source context can include Unity files for API discovery, but we filter them in mod checks
        
        $fileCount = $csFiles.Count
        $processedCount = 0
        $batchSize = $script:PerformanceConfig.FileScanBatchSize
        $updateInterval = $script:PerformanceConfig.ProgressUpdateInterval
        
        Write-ColorOutput "  Found $fileCount files, processing with CPU throttling..." "Cyan"
        
        foreach ($file in $csFiles) {
            $processedCount++
            
            # CPU throttling to maintain ~94% usage (leave 6% free)
            Invoke-CPUThrottle
            
            # Throttle file reads to reduce CPU usage
            if ($script:PerformanceConfig.EnableThrottling -and $processedCount % $batchSize -eq 0) {
                Start-Sleep -Milliseconds $script:PerformanceConfig.FileReadDelayMs
            }
            
            # Update progress periodically
            if ($processedCount % $updateInterval -eq 0) {
                $percent = [math]::Min(100, [int](($processedCount / $fileCount) * 100))
                Write-ProgressDetail "Context Building" "Processing $processedCount/$fileCount files from $sourceDir..." $percent
            }
            
            try {
                $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
                
                if ([string]::IsNullOrWhiteSpace($content)) {
                    continue
                }
                
                # Extract class/interface/struct names
                $typeMatches = [regex]::Matches($content, '(?:public|private|internal|protected)?\s*(?:static\s+)?(?:class|interface|struct|enum)\s+(\w+)')
                foreach ($match in $typeMatches) {
                    if (-not ($script:SourceContext.AvailableTypes -contains $match.Groups[1].Value)) {
                        $script:SourceContext.AvailableTypes += $match.Groups[1].Value
                        $totalTypes++
                    }
                }
                
                # Extract method signatures
                $methodMatches = [regex]::Matches($content, '(?:public|private|internal|protected)\s+(?:static\s+)?(?:[\w<>\[\]]+\s+)?(\w+)\s*\([^)]*\)')
                foreach ($match in $methodMatches) {
                    $methodName = $match.Groups[1].Value
                    if (-not ($script:SourceContext.AvailableMethods -contains $methodName)) {
                        $script:SourceContext.AvailableMethods += $methodName
                        $totalMethods++
                    }
                }
                
                # Look for CWL-specific APIs
                if ($content -match 'CWL|CustomWorldLoader') {
                    $cwlMatches = [regex]::Matches($content, '(?:class|interface|static\s+class)\s+(\w*CWL\w*|\w*Cwl\w*)')
                    foreach ($match in $cwlMatches) {
                        if (-not ($script:SourceContext.CWLAPIs -contains $match.Groups[1].Value)) {
                            $script:SourceContext.CWLAPIs += $match.Groups[1].Value
                        }
                    }
                }
            }
            catch {
                # Skip files that can't be read
                continue
            }
        }
        
        Write-ColorOutput "  Completed: $processedCount files processed" "Green"
    }
    
    Write-ProgressDetail "Context Building" "Complete" 100
    Write-ColorOutput "✓ Found $totalTypes types and $totalMethods methods in source" "Green"
    if ($VerbosePreference -eq 'Continue') {
        Write-ColorOutput "  CWL APIs found: $($script:SourceContext.CWLAPIs.Count)" "Cyan"
    }
}

function Get-SourceContextSummary {
    $summary = "Available Elin Game APIs:`n"
    $summary += "- Types: $($script:SourceContext.AvailableTypes.Count) found`n"
    $summary += "- Methods: $($script:SourceContext.AvailableMethods.Count) found`n"
    $summary += "- CWL APIs: $($script:SourceContext.CWLAPIs.Count) found`n"
    
    if ($script:SourceContext.CWLAPIs.Count -gt 0) {
        $summary += "CWL APIs: $($script:SourceContext.CWLAPIs -join ', ')"
    }
    
    return $summary
}

# ============================================================
# CODE CHECKS
# ============================================================

function Test-CodeCompilation {
    Write-ProgressDetail "Code Check" "Checking compilation..." 10
    
    $csprojFiles = Get-CachedChildItem -Path $ModPath -Filter "*.csproj" -Recurse -File
    if ($csprojFiles.Count -eq 0) {
        $script:Results.Errors += "No .csproj file found. Mod may not be properly configured."
        Write-ColorOutput "✗ No .csproj file found" "Red"
        return
    }
    
    $csprojFile = $csprojFiles[0]
    Write-ColorOutput "Found project file: $($csprojFile.Name)" "Green"
    
    # Try to build the project
    Write-ColorOutput "Attempting to build project..." "Cyan"
    try {
        $buildOutput = & dotnet build $csprojFile.FullName 2>&1
        $buildSuccess = $LASTEXITCODE -eq 0
    }
    catch {
        Write-ColorOutput "Build command failed: $_" "Red"
        $buildSuccess = $false
        $buildOutput = "Build command exception: $_"
    }
    
    if (-not $buildSuccess) {
        # Extract error messages from build output
        $errorLines = $buildOutput | Where-Object { $_ -match 'error\s+CS\d+' -or $_ -match 'error\s+:\s+' }
        $errorCount = ($errorLines | Measure-Object).Count
        
        Write-ColorOutput "✗ Code compilation failed with $errorCount error(s)" "Red"
        
        # Show first few errors
        if ($errorLines.Count -gt 0) {
            Write-ColorOutput "First errors:" "Yellow"
            $errorLines | Select-Object -First 10 | ForEach-Object {
                Write-ColorOutput "  $_" "Red"
            }
            if ($errorLines.Count -gt 10) {
                Write-ColorOutput "  ... and $($errorLines.Count - 10) more errors" "Yellow"
            }
        }
        
        # Check specifically for SpellgunSpellbowHelper.cs errors
        $spellgunErrors = $buildOutput | Where-Object { $_ -match 'SpellgunSpellbowHelper' -and $_ -match 'error' }
        if ($spellgunErrors.Count -gt 0) {
            Write-ColorOutput "`nSpellgunSpellbowHelper.cs errors found:" "Red"
            $spellgunErrors | ForEach-Object {
                Write-ColorOutput "  $_" "Red"
            }
            
            # Prioritize AI analysis for SpellgunSpellbowHelper.cs errors
            if ($UseAI) {
                Write-ColorOutput "Requesting AI analysis for SpellgunSpellbowHelper.cs errors..." "Cyan"
            }
        }
        
        $script:Results.Errors += "Code compilation failed with $errorCount error(s). Check build output for details."
        $script:Results.Code += @{
            Type = "Compilation"
            Status = "Failed"
            Details = $buildOutput
            ErrorCount = $errorCount
            ErrorLines = $errorLines
        }
        
        if ($UseAI) {
            # Get full error context for better fixes
            $errorSample = ($errorLines | Select-Object -First 20) -join "`n"
            
            # Get file paths from errors for context
            $errorFiles = $errorLines | Where-Object { $_ -match '\((\d+),(\d+)\)' } | ForEach-Object {
                if ($_ -match '([^\\]+\.cs)\((\d+),(\d+)\)') {
                    $matches[1]
                }
            } | Select-Object -Unique -First 5
            
            $fileContext = ""
            if ($errorFiles.Count -gt 0) {
                $fileContext = "`nRelevant files: $($errorFiles -join ', ')"
            }
            
            # Get actual file content for errors to provide context
            $fileContents = @{}
            foreach ($errorFile in $errorFiles) {
                $file = Get-CachedChildItem -Path $ModPath -Filter $errorFile -Recurse -File | Select-Object -First 1
                if ($file) {
                    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
                    # Extract relevant lines around errors
                    $errorLinesForFile = $errorLines | Where-Object { $_ -match $errorFile }
                    $lineNumbers = $errorLinesForFile | ForEach-Object {
                        if ($_ -match '\((\d+),') { [int]$matches[1] }
                    } | Select-Object -Unique
                    
                    $relevantCode = ""
                    foreach ($lineNum in $lineNumbers) {
                        $fileLines = $content -split "`n"
                        $start = [Math]::Max(1, $lineNum - 5)
                        $end = [Math]::Min($fileLines.Count, $lineNum + 5)
                        $relevantCode += "`n--- Lines $start-$end in $errorFile ---`n"
                        for ($i = $start - 1; $i -lt $end; $i++) {
                            $lineMarker = if ($i -eq $lineNum - 1) { ">>> " } else { "    " }
                            $relevantCode += "$lineMarker$($i + 1): $($fileLines[$i])`n"
                        }
                    }
                    $fileContents[$errorFile] = $relevantCode
                }
            }
            
            $fileContextCode = ""
            if ($fileContents.Count -gt 0) {
                $fileContextCode = "`n`nRelevant code sections:`n"
                foreach ($key in $fileContents.Keys) {
                    $fileContextCode += $fileContents[$key] + "`n"
                }
            }
            
            $prompt = @"
Analyze these C# compilation errors and provide solutions:

Errors:
$errorSample$fileContextCode

For EACH error, provide:
1. PRIMARY FIX (recommended solution)
2. ALTERNATIVE OPTIONS (if applicable)

Format for PRIMARY FIX:
FILE: [filename.cs]
LINE: [line number]
OLD: [the incorrect code line(s)]
NEW: [the corrected code line(s)]
REASON: [brief explanation]
PRIORITY: [high/medium/low]

Format for ALTERNATIVES (if multiple approaches exist):
ALTERNATIVE 1:
FILE: [filename.cs]
LINE: [line number]
APPROACH: [description of alternative approach]
OLD: [code]
NEW: [code]
PROS: [advantages]
CONS: [disadvantages]

ALTERNATIVE 2:
[repeat format]

IMPORTANT:
- Provide EXACT code that needs to be replaced
- Show complete corrected code
- Match exact indentation and formatting
- If multiple lines need changing, show all of them
- Suggest alternatives when there are multiple valid approaches
- Explain trade-offs between options

Example:
FILE: SpellgunSpellbowHelper.cs
LINE: 506
OLD:         }
NEW:         }
        }
REASON: Missing closing brace
PRIORITY: high

ALTERNATIVE 1:
FILE: SpellgunSpellbowHelper.cs
LINE: 505
APPROACH: Remove extra opening brace instead
OLD:         {
NEW:         
PROS: Simpler change
CONS: May affect other code structure

Be precise and provide actual code, not descriptions.
"@
            $aiSuggestion = Invoke-OllamaRequest -Prompt $prompt -TaskType "code" -ResponseLength "detailed"
            if ($aiSuggestion) {
                $script:Results.Suggestions += @{
                    Category = "Code"
                    Issue = "Compilation Errors ($errorCount)"
                    Suggestion = $aiSuggestion
                    ErrorLines = $errorLines
                    ErrorFiles = $errorFiles
                }
                
                # Apply fixes if requested
                if ($FixIssues) {
                    Write-ColorOutput "  Attempting to apply AI fixes..." "Cyan"
                    Apply-AIFixes -Suggestion $aiSuggestion -ErrorLines $errorLines -ErrorFiles $errorFiles
                }
            }
        }
    }
    else {
        Write-ColorOutput "✓ Code compiles successfully" "Green"
        $script:Results.Code += @{
            Type = "Compilation"
            Status = "Passed"
        }
    }
}

function Test-CodeStructure {
    Write-ProgressDetail "Code Check" "Analyzing code structure..." 30
    
    try {
        $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse -Verbose:($VerbosePreference -eq 'Continue')
        $totalFiles = $csFiles.Count
        
        Write-ColorOutput "Found $totalFiles C# files to analyze" "Cyan"
        
        # Show first few files being checked
        if ($totalFiles -gt 0) {
            Write-ColorOutput "Sample files:" "Gray"
            $csFiles | Select-Object -First 5 | ForEach-Object {
                Write-ColorOutput "  - $($_.Name)" "Gray"
            }
            if ($totalFiles -gt 5) {
                Write-ColorOutput "  ... and $($totalFiles - 5) more" "Gray"
            }
        }
    }
    catch {
        Write-ColorOutput "Error getting C# files: $_" "Red"
        Write-ColorOutput "Stack: $($_.ScriptStackTrace)" "Red"
        return
    }
    
    if ($totalFiles -eq 0) {
        Write-ColorOutput "WARNING: No C# files found to analyze!" "Yellow"
        Write-ColorOutput "Check if mod path is correct: $ModPath" "Yellow"
        return
    }
    
    # Check for common issues
    $issues = @()
    $fileCount = 0
    $priorityFiles = @("SpellgunSpellbowHelper.cs", "SpellEngine.cs", "ModSaveSafetyIntegration.cs")
    $priorityFileIssues = @{}
    
    Write-ColorOutput "Analyzing code structure (checking all $totalFiles files)..." "Cyan"
    
    foreach ($file in $csFiles) {
        $fileCount++
        $isPriorityFile = $priorityFiles -contains $file.Name
        
        if ($fileCount % 50 -eq 0 -or $isPriorityFile) {
            $pct = [math]::Round(($fileCount / $totalFiles) * 100)
            Write-Progress -Activity "Code Structure Analysis" -Status "File $fileCount of $totalFiles" -PercentComplete $pct
        }
        
        # Highlight priority files being processed
        if ($isPriorityFile) {
            Write-ColorOutput "  >> Analyzing priority file: $($file.Name)" "Cyan"
        }
        
        try {
            $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
            $fileIssues = @()
            
            if (-not $content) {
                $fileIssues += "Could not read file content"
                continue
            }
            
            $lineCount = ($content -split "`n").Count
            
            # For priority files, show line count
            if ($isPriorityFile) {
                Write-ColorOutput "     Lines: $lineCount" "Gray"
            }
            
            # Check for missing using statements
            if ($content -match '^\s*(public|private|internal|protected)\s+(class|interface|struct)' -and 
                $content -notmatch 'using\s+System;') {
                $fileIssues += "Missing System using"
            }
            
            # Check for TODO/FIXME comments
            $todoMatches = [regex]::Matches($content, '(?i)(TODO|FIXME|HACK|XXX)[:\s]+([^\r\n]+)')
            if ($todoMatches.Count -gt 0) {
                foreach ($match in $todoMatches) {
                    $fileIssues += "TODO: $($match.Groups[2].Value.Substring(0, [Math]::Min(50, $match.Groups[2].Value.Length)))..."
                }
            }
            
            # Check for empty catch blocks
            if ($content -match 'catch\s*\([^)]*\)\s*\{\s*\}') {
                $fileIssues += "Empty catch block"
            }
            
            # Check for syntax errors that might not compile
            # Missing method signatures (XML doc but no method)
            if ($content -match '///\s*<summary>.*</summary>\s*\n\s*\{') {
                $fileIssues += "Possible missing method signature after XML documentation"
            }
            
            # Check for try-finally-catch structure issues
            if ($content -match 'try\s*\{' -and $content -match 'finally\s*\{' -and $content -match 'catch\s*\(') {
                $tryCount = ([regex]::Matches($content, 'try\s*\{')).Count
                $finallyCount = ([regex]::Matches($content, 'finally\s*\{')).Count
                $catchCount = ([regex]::Matches($content, 'catch\s*\(')).Count
                if ($tryCount -ne $finallyCount -or $tryCount -ne $catchCount) {
                    $fileIssues += "Mismatched try-finally-catch blocks (try: $tryCount, finally: $finallyCount, catch: $catchCount)"
                }
            }
            
            # Check for brace balance
            $openBraces = ([regex]::Matches($content, '\{')).Count
            $closeBraces = ([regex]::Matches($content, '\}')).Count
            if ($openBraces -ne $closeBraces) {
                $fileIssues += "Unbalanced braces (open: $openBraces, close: $closeBraces)"
            }
            
            # Check for common C# syntax issues
            if ($content -match 'public\s+static\s+\w+\s*\([^)]*\)\s*\{[^}]*$') {
                # Method that might be missing closing brace
                $fileIssues += "Possible incomplete method definition"
            }
            
            # Add issues to list
            foreach ($issue in $fileIssues) {
                $issues += "$($file.Name): $issue"
            }
            
            # Track priority file issues separately
            if ($isPriorityFile -and $fileIssues.Count -gt 0) {
                $priorityFileIssues[$file.Name] = $fileIssues
                Write-ColorOutput "     Found $($fileIssues.Count) issue(s) in $($file.Name)" "Yellow"
            }
        }
        catch {
            Write-ColorOutput "  Error reading $($file.Name): $_" "Red"
            continue
        }
    }
    
    # Report priority file issues
    if ($priorityFileIssues.Count -gt 0) {
        Write-ColorOutput "`nPriority File Issues:" "Yellow"
        foreach ($fileName in $priorityFileIssues.Keys) {
            Write-ColorOutput "  $fileName :" "Yellow"
            foreach ($issue in $priorityFileIssues[$fileName]) {
                Write-ColorOutput "    - $issue" "Yellow"
            }
        }
    }
    
    if ($issues.Count -gt 0) {
        Write-ColorOutput "Found $($issues.Count) code structure issues" "Yellow"
        $script:Results.Warnings += "Found $($issues.Count) code structure issues"
        $script:Results.Code += @{
            Type = "Structure"
            Status = "Issues Found"
            Details = $issues
        }
        
        # Use AI to analyze structure issues (batch for efficiency)
        if ($UseAI -and $issues.Count -gt 0) {
            # Only analyze first 10 issues to save resources
            $issueSample = $issues | Select-Object -First 10
            $aiSuggestion = Invoke-OllamaBatchAnalysis -Items $issueSample -AnalysisType "code structure"
            if ($aiSuggestion) {
                $script:Results.Suggestions += @{
                    Category = "Code Structure"
                    Issue = "Structure Issues ($($issues.Count) found)"
                    Suggestion = $aiSuggestion
                }
                Write-ColorOutput "  AI suggestions generated" "Green"
            }
        }
    }
    else {
        Write-ColorOutput "✓ Code structure looks good" "Green"
    }
    
    Write-ProgressDetail "Code Check" "Code structure analysis complete" 100
}

function Test-CodeReferences {
    Write-ProgressDetail "Code Check" "Checking references..." 50
    
    try {
        $csprojFiles = Get-CachedChildItem -Path $ModPath -Filter "*.csproj" -Recurse -File
        if ($csprojFiles.Count -eq 0) {
            Write-ColorOutput "No .csproj file found for reference check" "Yellow"
            return
        }
        
        $csprojFile = $csprojFiles[0]
        Write-ColorOutput "Checking references in $($csprojFile.Name)..." "Cyan"
        
        [xml]$csproj = Get-Content $csprojFile.FullName -ErrorAction Stop
        
        $references = $csproj.Project.ItemGroup.Reference
        $missingRefs = @()
        
        if ($references) {
            foreach ($ref in $references) {
                $hintPath = $ref.HintPath
                if ($hintPath -and -not (Test-Path (Join-Path $ModPath $hintPath))) {
                    $missingRefs += $ref.Include
                }
            }
        }
        
        if ($missingRefs.Count -gt 0) {
            Write-ColorOutput "✗ Missing references: $($missingRefs -join ', ')" "Red"
            $script:Results.Errors += "Missing references: $($missingRefs -join ', ')"
            $script:Results.Code += @{
                Type = "References"
                Status = "Failed"
                Details = $missingRefs
            }
        }
        else {
            Write-ColorOutput "✓ All references found" "Green"
        }
    }
    catch {
        Write-ColorOutput "Error checking references: $_" "Red"
        $script:Results.Errors += "Reference check failed: $_"
    }
}

# ============================================================
# ASSET CHECKS
# ============================================================

function Test-AssetStructure {
    Write-ProgressDetail "Asset Check" "Checking asset structure..." 10
    
    $expectedDirs = @(
        "Assets",
        "Assets\Resources",
        "Assets\AssetBundles"
    )
    
    $missingDirs = @()
    foreach ($dir in $expectedDirs) {
        $fullPath = Join-Path $ModPath $dir
        if (-not (Test-Path $fullPath)) {
            $missingDirs += $dir
        }
    }
    
    if ($missingDirs.Count -gt 0) {
        $script:Results.Warnings += "Missing asset directories: $($missingDirs -join ', ')"
        $script:Results.Assets += @{
            Type = "Structure"
            Status = "Issues Found"
            Details = $missingDirs
        }
        
        if ($FixIssues) {
            foreach ($dir in $missingDirs) {
                $fullPath = Join-Path $ModPath $dir
                New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
                Write-ColorOutput "Created directory: $dir" "Yellow"
            }
        }
    }
    else {
        Write-ColorOutput "✓ Asset directories exist" "Green"
    }
}

function Test-AssetFiles {
    Write-ProgressDetail "Asset Check" "Checking asset files..." 30
    
    $resourceDir = Join-Path $ModPath "Assets\Resources"
    if (-not (Test-Path $resourceDir)) {
        return
    }
    
    $systems = Get-ChildItem -Path $resourceDir -Directory -ErrorAction SilentlyContinue
    $assetIssues = @()
    
    foreach ($system in $systems) {
        $textureDir = Join-Path $system.FullName "Textures"
        $iconDir = Join-Path $system.FullName "Icons"
        
        # Check for empty texture directories
        if ((Test-Path $textureDir) -and (Get-ChildItem $textureDir -ErrorAction SilentlyContinue).Count -eq 0) {
            $assetIssues += "Empty Textures directory in $($system.Name)"
        }
        
        # Check for missing icons
        if ((Test-Path $iconDir) -and (Get-ChildItem $iconDir -ErrorAction SilentlyContinue).Count -eq 0) {
            $assetIssues += "Empty Icons directory in $($system.Name)"
        }
    }
    
    if ($assetIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($assetIssues.Count) asset issues"
        $script:Results.Assets += @{
            Type = "Files"
            Status = "Issues Found"
            Details = $assetIssues
        }
        
        if ($UseAI) {
            $prompt = "Suggest brief solutions for missing/empty asset directories: $($assetIssues -join ', ')"
            $aiSuggestion = Invoke-OllamaRequest -Prompt $prompt -TaskType "simple" -ResponseLength "short"
            if ($aiSuggestion) {
                $script:Results.Suggestions += @{
                    Category = "Assets"
                    Issue = "Asset Issues ($($assetIssues.Count))"
                    Suggestion = $aiSuggestion
                }
            }
        }
    }
    else {
        Write-ColorOutput "✓ Asset files look good" "Green"
    }
}

function Test-AssetBundles {
    Write-ProgressDetail "Asset Check" "Checking asset bundles..." 50
    
    $bundleDirs = @(
        "Assets\AssetBundles\Windows",
        "Assets\AssetBundles\Linux",
        "Assets\AssetBundles\macOS"
    )
    
    $bundleIssues = @()
    foreach ($dir in $bundleDirs) {
        $fullPath = Join-Path $ModPath $dir
        if (Test-Path $fullPath) {
            $bundles = Get-ChildItem -Path $fullPath -Filter "*.assetbundle" -ErrorAction SilentlyContinue
            foreach ($bundle in $bundles) {
                if ($bundle.Length -eq 0) {
                    $bundleIssues += "Empty bundle: $($bundle.Name)"
                }
            }
        }
    }
    
    if ($bundleIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($bundleIssues.Count) bundle issues"
        $script:Results.Assets += @{
            Type = "Bundles"
            Status = "Issues Found"
            Details = $bundleIssues
        }
    }
}

# ============================================================
# CONFIGURATION CHECKS
# ============================================================

function Test-ConfigFiles {
    Write-ProgressDetail "Config Check" "Checking configuration files..." 10
    
    $configFiles = @(
        "manifest.json",
        "README.md",
        "CHANGELOG.md"
    )
    
    $missingConfigs = @()
    foreach ($file in $configFiles) {
        $fullPath = Join-Path $ModPath $file
        if (-not (Test-Path $fullPath)) {
            $missingConfigs += $file
        }
    }
    
    if ($missingConfigs.Count -gt 0) {
        $script:Results.Warnings += "Missing config files: $($missingConfigs -join ', ')"
        $script:Results.Config += @{
            Type = "Files"
            Status = "Issues Found"
            Details = $missingConfigs
        }
    }
    else {
        Write-ColorOutput "✓ Configuration files exist" "Green"
    }
}

function Test-Manifest {
    Write-ProgressDetail "Config Check" "Validating manifest..." 30
    
    $manifestPath = Join-Path $ModPath "manifest.json"
    if (-not (Test-Path $manifestPath)) {
        $script:Results.Errors += "manifest.json not found"
        return
    }
    
    try {
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        
        $requiredFields = @("name", "version_number", "website_url", "description")
        $missingFields = @()
        
        foreach ($field in $requiredFields) {
            if (-not $manifest.PSObject.Properties.Name -contains $field) {
                $missingFields += $field
            }
        }
        
        if ($missingFields.Count -gt 0) {
            $script:Results.Errors += "Manifest missing required fields: $($missingFields -join ', ')"
            $script:Results.Config += @{
                Type = "Manifest"
                Status = "Failed"
                Details = $missingFields
            }
        }
        else {
            Write-ColorOutput "✓ Manifest is valid" "Green"
        }
    }
    catch {
        $script:Results.Errors += "Manifest JSON is invalid: $_"
    }
}

# ============================================================
# SAVE SAFETY SYSTEM CHECKS
# ============================================================

function Test-SaveSafetySystems {
    Write-ProgressDetail "Save Safety Check" "Checking save safety systems..." 10
    
    $saveSafetyFiles = Get-ModCsFiles -Path $ModPath -Filter "*SaveSafety*.cs" -Recurse
    $saveSystemFiles = Get-ModCsFiles -Path $ModPath -Filter "*SaveSystem.cs" -Recurse
    $cwlSaveLoadFiles = Get-ModCsFiles -Path $ModPath -Filter "*CwlSaveLoad.cs" -Recurse
    
    $saveSafetyIssues = @()
    $saveSafetyInfo = @()
    
    # Check for ModSaveSafetyIntegration
    $modSaveSafety = Get-ModCsFiles -Path $ModPath -Filter "ModSaveSafetyIntegration.cs" -Recurse
    if ($modSaveSafety.Count -eq 0) {
        $saveSafetyIssues += "ModSaveSafetyIntegration.cs not found - required for complex functions CWL cannot handle"
    }
    else {
        $saveSafetyInfo += "ModSaveSafetyIntegration found (for complex functions CWL cannot handle)"
        $script:SourceContext.SaveSafetySystems += "ModSaveSafetyIntegration"
    }
    
    # Check CWL save/load files
    foreach ($file in $cwlSaveLoadFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match 'BaseCwlAdapter|CWL.*Save|CWL.*Load') {
            $saveSafetyInfo += "$($file.Name): Uses CWL for save/load"
        }
    }
    
    # Check save system files (for complex functions)
    foreach ($file in $saveSystemFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $usesSaveSafety = $content -match 'SaveSafetySystem|ModSaveSafetyIntegration'
        $usesCWL = $content -match 'CWL|BaseCwlAdapter|CwlSaveLoad'
        
        if ($usesSaveSafety -and $usesCWL) {
            $saveSafetyInfo += "$($file.Name): Uses BOTH CWL and save safety system (hybrid approach - correct)"
        }
        elseif ($usesSaveSafety) {
            $saveSafetyInfo += "$($file.Name): Uses save safety system (for complex functions)"
        }
        elseif ($usesCWL) {
            $saveSafetyInfo += "$($file.Name): Uses CWL for save/load"
        }
        elseif ($file.Name -notmatch 'CwlSaveLoad') {
            # Save system that doesn't use CWL or save safety - might be missing integration
            $saveSafetyIssues += "$($file.Name) is a save system but may not integrate with CWL or save safety system"
        }
    }
    
    Write-ColorOutput "Save Safety Systems:" "Cyan"
    Write-ColorOutput "  CWL Save/Load Files: $($cwlSaveLoadFiles.Count)" "White"
    Write-ColorOutput "  Save System Files: $($saveSystemFiles.Count)" "White"
    Write-ColorOutput "  Save Safety Integration: $(if ($modSaveSafety.Count -gt 0) { 'Found' } else { 'Missing' })" "White"
    
    if ($saveSafetyIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($saveSafetyIssues.Count) save safety issues"
        $script:Results.CWL += @{
            Type = "Save Safety"
            Status = "Issues Found"
            Details = $saveSafetyIssues
        }
    }
    else {
        Write-ColorOutput "✓ Save safety systems look good" "Green"
        if ($VerbosePreference -eq 'Continue') {
            foreach ($info in $saveSafetyInfo) {
                Write-ColorOutput "  - $info" "Cyan"
            }
        }
    }
    
    $script:Results.CWL += @{
        Type = "Save Safety Analysis"
        Status = "Analyzed"
        Details = @{
            CWLSaveLoadFiles = $cwlSaveLoadFiles.Count
            SaveSystemFiles = $saveSystemFiles.Count
            HasModSaveSafety = $modSaveSafety.Count -gt 0
        }
    }
}

function Test-SaveSafetyUsage {
    Write-ProgressDetail "Save Safety Check" "Analyzing save safety usage patterns..." 30
    
    $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse
    $saveSafetyUsage = @{
        UsesCWLForSave = 0
        UsesSaveSafetySystem = 0
        UsesBoth = 0
        MissingSaveSafety = 0
    }
    $issues = @()
    $hybridFiles = @()
    
    foreach ($file in $csFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        $usesCWL = $false
        $usesSaveSafety = $false
        
        # Check for CWL save/load
        if ($content -match 'CwlSaveLoad|CWL.*Save|CWL.*Load|BaseCwlAdapter.*Save') {
            $saveSafetyUsage.UsesCWLForSave++
            $usesCWL = $true
        }
        
        # Check for save safety system usage
        if ($content -match 'SaveSafetySystem|ModSaveSafetyIntegration|SaveAllModData|LoadAllModData') {
            $saveSafetyUsage.UsesSaveSafetySystem++
            $usesSaveSafety = $true
        }
        
        # Check if file uses BOTH (this is correct and intentional)
        if ($usesCWL -and $usesSaveSafety) {
            $saveSafetyUsage.UsesBoth++
            $hybridFiles += "$($file.Name): Uses both CWL and save safety system (hybrid approach)"
        }
        
        # Check for complex systems that might need save safety
        # Only flag if they use NEITHER system
        if ($file.Name -match 'System|Manager|Integration' -and 
            $file.Name -notmatch 'CwlAdapter|CwlSaveLoad|SaveSafety|SaveSystem|Config' -and
            $content -match 'Dictionary|List|Queue|Stack|HashSet' -and
            -not $usesCWL -and -not $usesSaveSafety) {
            
            # Check if it's a complex system
            $lineCount = ($content -split "`n").Count
            if ($lineCount -gt 300) {
                # Complex system that might need save safety
                $saveSafetyUsage.MissingSaveSafety++
                $issues += "$($file.Name) is complex but may not have save safety integration (neither CWL nor save safety system)"
            }
        }
    }
    
    Write-ColorOutput "Save Safety Usage Analysis:" "Cyan"
    Write-ColorOutput "  Uses CWL for Save/Load: $($saveSafetyUsage.UsesCWLForSave) files" "White"
    Write-ColorOutput "  Uses Save Safety System: $($saveSafetyUsage.UsesSaveSafetySystem) files" "White"
    Write-ColorOutput "  Uses BOTH (Hybrid): $($saveSafetyUsage.UsesBoth) files" "Green"
    
    if (($VerbosePreference -eq 'Continue') -and $hybridFiles.Count -gt 0) {
        Write-ColorOutput "  Hybrid Files (using both systems):" "Cyan"
        foreach ($hybrid in $hybridFiles) {
            Write-ColorOutput "    - $hybrid" "Cyan"
        }
    }
    
    if ($saveSafetyUsage.MissingSaveSafety -gt 0) {
        Write-ColorOutput "  Missing Save Safety: $($saveSafetyUsage.MissingSaveSafety) files (WARNING)" "Yellow"
    }
    
    if ($issues.Count -gt 0) {
        $script:Results.Warnings += "Found $($issues.Count) complex systems that may need save safety (neither CWL nor save safety system)"
        $script:Results.CWL += @{
            Type = "Save Safety Usage"
            Status = "Issues Found"
            Details = $issues
        }
    }
    else {
        Write-ColorOutput "✓ Save safety usage looks good" "Green"
    }
    
    $script:Results.CWL += @{
        Type = "Save Safety Usage Analysis"
        Status = "Analyzed"
        Details = $saveSafetyUsage
        HybridFiles = $hybridFiles
    }
}

# ============================================================
# CWL INTEGRATION CHECKS
# ============================================================

function Test-CWLAdapters {
    Write-ProgressDetail "CWL Check" "Checking CWL adapters..." 10
    
    $cwlAdapterFiles = Get-ModCsFiles -Path $ModPath -Filter "*CwlAdapter.cs" -Recurse
    $adapterIssues = @()
    $adapterInfo = @()
    
    foreach ($file in $cwlAdapterFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $adapterName = $file.BaseName
        
        # Check if extends BaseCwlAdapter
        # Note: Patterns based on CWL wiki, actual implementations may vary
        if ($content -notmatch ':\s*BaseCwlAdapter') {
            $adapterIssues += "$adapterName does not extend BaseCwlAdapter (pattern from CWL wiki - verify actual implementation)"
        }
        
        # Check for required methods
        # Note: These patterns are from CWL wiki documentation, actual implementations may use different patterns
        $requiredMethods = @("Initialize", "ProcessSheetForSystem", "IsSystemEnabled")
        foreach ($method in $requiredMethods) {
            if ($content -notmatch "(?:protected\s+override|public\s+static|private\s+static|public\s+override)\s+.*$method") {
                $adapterIssues += "$adapterName may be missing method: $method (pattern from CWL wiki - verify actual implementation)"
            }
        }
        
        # Check for singleton pattern
        if ($content -match 'private\s+static.*_instance' -and $content -match 'public\s+static\s+void\s+Initialize') {
            $adapterInfo += "$adapterName uses singleton pattern"
        }
        
        $script:SourceContext.CWLAdapters += @{
            Name = $adapterName
            File = $file.Name
            HasBaseClass = $content -match ':\s*BaseCwlAdapter'
            HasRequiredMethods = ($requiredMethods | ForEach-Object { $content -match $_ }) -notcontains $false
        }
    }
    
    if ($adapterIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($adapterIssues.Count) potential CWL adapter suggestions (based on CWL wiki patterns - verify manually)"
        $script:Results.CWL += @{
            Type = "Adapters"
            Status = "Suggestions Found"
            Details = $adapterIssues
            Note = "CWL adapter checks are based on CWL wiki patterns. Actual implementations may vary - these are suggestions, not errors. Review manually."
        }
    }
    else {
        Write-ColorOutput "✓ CWL adapters look good ($($cwlAdapterFiles.Count) found)" "Green"
        if ($VerbosePreference -eq 'Continue') {
            foreach ($info in $adapterInfo) {
                Write-ColorOutput "  - $info" "Cyan"
            }
        }
    }
}

function Test-CWLUsage {
    Write-ProgressDetail "CWL Check" "Analyzing CWL usage patterns..." 30
    
    $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse
    $cwlUsage = @{
        DirectCWL = 0
        CWLAdapters = 0
        ReflectionForCWL = 0
        MissingCWL = 0
    }
    $issues = @()
    
    foreach ($file in $csFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        # Check for direct CWL usage
        if ($content -match 'using\s+.*CWL|CustomWorldLoader|BaseCwlAdapter') {
            $cwlUsage.DirectCWL++
        }
        
        # Check for CWL adapters
        if ($content -match 'CwlAdapter|BaseCwlAdapter') {
            $cwlUsage.CWLAdapters++
        }
        
        # Check for reflection used for CWL integration
        if ($content -match 'GetType\(\)|GetMethod\(|Invoke\(|GetProperty\(|GetField\(') {
            # Check if it's for CWL integration
            if ($content -match '_cwlAvailable|CWL.*Available|if\s*\(.*CWL|CWL.*Type|CWL.*Method') {
                $cwlUsage.ReflectionForCWL++
            }
        }
        
        # Check for files that should use CWL but don't
        # Helper files that deal with data/config should use CWL
        if ($file.Name -match 'Helper|Manager|Config' -and 
            $file.Name -notmatch 'CwlAdapter|Patches' -and
            $content -notmatch 'CWL|BaseCwlAdapter|CustomWorldLoader') {
            $cwlUsage.MissingCWL++
            $issues += "$($file.Name) appears to handle data/config but doesn't use CWL"
        }
    }
    
    Write-ColorOutput "CWL Usage Analysis:" "Cyan"
    Write-ColorOutput "  Direct CWL Usage: $($cwlUsage.DirectCWL) files" "White"
    Write-ColorOutput "  CWL Adapters: $($cwlUsage.CWLAdapters) files" "White"
    Write-ColorOutput "  Reflection for CWL: $($cwlUsage.ReflectionForCWL) files" "White"
    
    if ($cwlUsage.MissingCWL -gt 0) {
        Write-ColorOutput "  Missing CWL: $($cwlUsage.MissingCWL) files (WARNING)" "Yellow"
    }
    
    if ($issues.Count -gt 0) {
        $script:Results.Warnings += "Found $($issues.Count) potential CWL integration suggestions (may not be accurate - review manually)"
        $script:Results.CWL += @{
            Type = "Usage"
            Status = "Suggestions Found"
            Details = $issues
            Note = "CWL usage analysis is based on CWL wiki patterns. Actual implementations may vary - these are suggestions based on wiki patterns, not errors. Complex systems may intentionally use different approaches."
        }
    }
    
    $script:Results.CWL += @{
        Type = "Usage Analysis"
        Status = "Analyzed"
        Details = $cwlUsage
    }
}

function Test-CWLRequired {
    Write-ProgressDetail "CWL Check" "Validating CWL is properly used (CWL is required)..." 50
    
    $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*Helper.cs" -Recurse
    $cwlIssues = @()
    $cwlNotes = @()
    
    foreach ($file in $csFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        # CWL is required - check that helpers properly use CWL
        # Check for reflection used for CWL integration
        if ($content -match 'GetType\(\)|GetMethod\(') {
            # Should be checking CWL availability for CWL integration
            if ($content -notmatch '_cwlAvailable|CWL.*Available|if\s*\(.*CWL.*\)') {
                # This might be okay if it's for Harmony patches or core functionality
                if ($file.Name -notmatch 'Patches' -and $content -notmatch 'HarmonyPatch') {
                    # Check if it's actually a CWL helper (might use reflection for CWL integration)
                    if ($file.Name -match 'CWL|Cwl' -or $content -match 'namespace.*CWL|using.*CWL') {
                        # CWL helpers might use reflection - this is acceptable
                        $cwlNotes += "$($file.Name) uses reflection for CWL integration (acceptable)"
                    }
                    elseif ($content -match 'BaseCwlAdapter|CustomWorldLoader') {
                        # Uses CWL types - reflection might be for CWL integration
                        $cwlNotes += "$($file.Name) uses reflection with CWL types (likely CWL integration)"
                    }
                    else {
                        # Might be an issue, but be conservative
                        $cwlIssues += "$($file.Name) uses reflection but doesn't appear to check CWL availability (may be acceptable for complex code)"
                    }
                }
            }
        }
        
        # Check for CWL adapter usage - adapters must be initialized
        if ($content -match 'CwlAdapter|CWL.*Adapter') {
            if ($content -notmatch '\.Initialize\(\)|Initialize\(\)') {
                # Check if it's defining the adapter (Initialize might be in base class)
                if ($content -match 'class.*CwlAdapter|:\s*BaseCwlAdapter') {
                    # Adapter definition - Initialize might be in base class or called elsewhere
                    $cwlNotes += "$($file.Name) defines CWL adapter (Initialize may be in base class or called elsewhere)"
                }
                else {
                    $cwlIssues += "$($file.Name) references CWL adapter but may not initialize it (verify initialization exists)"
                }
            }
        }
        
        # Files that handle SIMPLE data/config should use CWL
        # Complex implementations may intentionally use Harmony/custom code
        # Only flag simple data/config files that should clearly use CWL
        # Be very conservative - many false positives possible
        if ($file.Name -match '^[A-Z][a-z]+Config\.cs$|^[A-Z][a-z]+Data\.cs$' -and 
            $file.Name -notmatch 'CwlAdapter|Patches|System|Manager|Helper|Integration' -and
            $content -notmatch 'CWL|BaseCwlAdapter|CustomWorldLoader|SaveSafetySystem|ModSaveSafetyIntegration' -and
            $content -notmatch 'HarmonyPatch|complex|Complex|advanced|Advanced|Dictionary|List<|Queue|Stack') {
            # Very simple config/data files should use CWL
            $lineCount = ($content -split "`n").Count
            $hasComplexLogic = $content -match 'if\s*\(.*\)\s*\{.*if\s*\(|switch\s*\(|foreach\s*\(.*\)\s*\{.*foreach|try\s*\{.*try|class\s+\w+\s*\{[^}]{500,}'
            
            if ($lineCount -lt 100 -and -not $hasComplexLogic -and $content -match 'public\s+(static\s+)?(class|struct)') {
                # Very small, very simple files might benefit from CWL
                $cwlIssues += "$($file.Name) is a simple config/data file that might benefit from CWL (optional suggestion)"
            }
        }
    }
    
    if ($cwlIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($cwlIssues.Count) potential CWL usage suggestions (may not be accurate - review manually)"
        $script:Results.CWL += @{
            Type = "CWL Required"
            Status = "Suggestions Found"
            Details = $cwlIssues
            Notes = $cwlNotes
            Note = "CWL checks are based on CWL wiki patterns converted to validation rules. Actual implementations may vary - these are suggestions based on wiki patterns, not errors. Review suggestions manually."
        }
    }
    else {
        Write-ColorOutput "✓ CWL usage looks good (CWL used where appropriate, complex code uses Harmony/custom where needed)" "Green"
        if (($VerbosePreference -eq 'Continue') -and $cwlNotes.Count -gt 0) {
            Write-ColorOutput "  CWL Notes:" "Cyan"
            foreach ($note in $cwlNotes) {
                Write-ColorOutput "    - $note" "Cyan"
            }
        }
    }
}

# ============================================================
# HARMONY PATCH CHECKS
# ============================================================

function Test-HarmonyPatches {
    Write-ProgressDetail "Harmony Check" "Checking Harmony patches (only remove if unused)..." 10
    
    $patchFiles = Get-ModCsFiles -Path $ModPath -Filter "*Patches.cs" -Recurse
    $patchIssues = @()
    $patchInfo = @()
    $unusedPatches = @()
    
    # Get all C# files to check for references
    $allCsFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse
    
    foreach ($file in $patchFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $patchName = $file.BaseName
        $className = $patchName
        
        # Check for HarmonyPatch attributes
        $patchMatches = [regex]::Matches($content, '\[HarmonyPatch(?:\([^)]*\))?\]')
        $patchCount = $patchMatches.Count
        
        # Check if this patch file is referenced anywhere
        $isReferenced = $false
        $referenceCount = 0
        
        foreach ($otherFile in $allCsFiles) {
            if ($otherFile.FullName -eq $file.FullName) { continue }
            
            $otherContent = Get-Content $otherFile.FullName -Raw -ErrorAction SilentlyContinue
            
            # Check for references to this patch class
            if ($otherContent -match $className -or 
                $otherContent -match $file.Name -or
                $otherContent -match "new\s+$className|typeof\($className\)|$className\s*\(") {
                $isReferenced = $true
                $referenceCount++
            }
        }
        
        if ($patchCount -eq 0) {
            if (-not $isReferenced) {
                $unusedPatches += "$patchName has 'Patches' in name but no [HarmonyPatch] attributes and is not referenced (may be unused)"
            }
            else {
                $patchIssues += "$patchName has 'Patches' in name but no [HarmonyPatch] attributes (but is referenced - may be intentional)"
            }
        }
        else {
            $statusText = if ($isReferenced) { "USED (required)" } else { "check if unused" }
            $patchInfo += "${patchName}: ${patchCount} patch(es) - $statusText"
            
            # Check for proper patch methods
            $prefixMatches = [regex]::Matches($content, '\[HarmonyPrefix\]')
            $postfixMatches = [regex]::Matches($content, '\[HarmonyPostfix\]')
            $transpilerMatches = [regex]::Matches($content, '\[HarmonyTranspiler\]')
            
            $totalPatchMethods = $prefixMatches.Count + $postfixMatches.Count + $transpilerMatches.Count
            
            if ($totalPatchMethods -ne $patchCount) {
                $patchIssues += "$patchName has $patchCount patch attributes but $totalPatchMethods patch methods (may be intentional - verify structure)"
            }
            
            # Check for target method specification
            $targetMatches = [regex]::Matches($content, 'HarmonyPatch\([^)]*typeof\(([^)]+)\)')
            if ($targetMatches.Count -eq 0 -and $content -match 'HarmonyPatch\(') {
                # Might use method name instead, which is fine
            }
        }
        
        # Check for Harmony namespace
        if ($content -notmatch 'using\s+HarmonyLib|using\s+.*Harmony') {
            $patchIssues += "$patchName uses Harmony but missing using statement (may be in global usings)"
        }
        
        $script:SourceContext.HarmonyPatches += @{
            Name = $patchName
            File = $file.Name
            PatchCount = $patchCount
            HasPrefix = $prefixMatches.Count -gt 0
            HasPostfix = $postfixMatches.Count -gt 0
            HasTranspiler = $transpilerMatches.Count -gt 0
            Required = $isReferenced  # Only required if referenced/used
            IsReferenced = $isReferenced
            ReferenceCount = $referenceCount
        }
    }
    
    if ($unusedPatches.Count -gt 0) {
        Write-ColorOutput "  Potentially unused patches (only remove if verified unused):" "Yellow"
        foreach ($unused in $unusedPatches) {
            Write-ColorOutput "    - $unused" "Yellow"
        }
        $script:Results.Harmony += @{
            Type = "Unused Patches"
            Status = "Potential Unused"
            Details = $unusedPatches
            Note = "Only remove Harmony patches if they are TRULY UNUSED (nothing references them). Verify manually before removing."
        }
    }
    
    if ($patchIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($patchIssues.Count) Harmony patch structure suggestions"
        $script:Results.Harmony += @{
            Type = "Patches"
            Status = "Structure Suggestions"
            Details = $patchIssues
            Note = "Only suggest removing Harmony patches if they are TRULY UNUSED (nothing references them). Used patches are REQUIRED."
        }
    }
    else {
        Write-ColorOutput "✓ Harmony patches look good ($($patchFiles.Count) files, $($script:SourceContext.HarmonyPatches.Count) patches)" "Green"
        if ($VerbosePreference -eq 'Continue') {
            foreach ($info in $patchInfo) {
                Write-ColorOutput "  - $info" "Cyan"
            }
        }
    }
}

function Test-HarmonyTargets {
    Write-ProgressDetail "Harmony Check" "Validating patch targets (Harmony for core functionality CWL cannot handle)..." 30
    
    $patchFiles = Get-ModCsFiles -Path $ModPath -Filter "*Patches.cs" -Recurse
    $targetIssues = @()
    $harmonyUsage = @{
        CoreFunctionality = 0
        RuntimeModifications = 0
    }
    
    foreach ($file in $patchFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        
        # Harmony is used for complex core functionality that CWL cannot handle
        # Check if patches are for runtime modifications (appropriate use)
        if ($content -match 'HarmonyPrefix|HarmonyPostfix|HarmonyTranspiler') {
            $harmonyUsage.RuntimeModifications++
            
            # Check if it's for complex core functionality (not simple data loading)
            if ($content -notmatch 'CWL|BaseCwlAdapter|Excel|Sheet') {
                $harmonyUsage.CoreFunctionality++
            }
            
            # Check for complexity indicators
            $lineCount = ($content -split "`n").Count
            $hasComplexLogic = $content -match 'if\s*\(.*\)\s*\{.*if\s*\(|switch\s*\(|foreach\s*\(.*\)\s*\{.*foreach|try\s*\{.*try|reflection|GetType|GetMethod'
            
            if ($lineCount -gt 100 -or $hasComplexLogic) {
                Write-ColorOutput "  - $($file.Name): Complex Harmony patch (appropriate for complexity CWL cannot handle)" "Cyan"
            }
        }
        
        # Extract target types from HarmonyPatch attributes
        $targetMatches = [regex]::Matches($content, 'HarmonyPatch\([^)]*typeof\(([^)]+)\)')
        foreach ($match in $targetMatches) {
            $targetType = $match.Groups[1].Value.Trim()
            
            # Check if target type exists in source context
            if ($script:SourceContext.AvailableTypes.Count -gt 0) {
                if (-not ($script:SourceContext.AvailableTypes -contains $targetType)) {
                    $targetIssues += "$($file.Name) patches type '$targetType' which may not exist in Elin"
                }
            }
        }
        
        # Extract method names
        $methodMatches = [regex]::Matches($content, 'HarmonyPatch\([^)]*"([^"]+)"')
        foreach ($match in $methodMatches) {
            $methodName = $match.Groups[1].Value.Trim()
            
            # Check if method exists in source context
            if ($script:SourceContext.AvailableMethods.Count -gt 0) {
                if (-not ($script:SourceContext.AvailableMethods -contains $methodName)) {
                    $targetIssues += "$($file.Name) patches method '$methodName' which may not exist in Elin"
                }
            }
        }
    }
    
    Write-ColorOutput "Harmony Usage Analysis:" "Cyan"
    Write-ColorOutput "  Core Functionality Patches: $($harmonyUsage.CoreFunctionality)" "White"
    Write-ColorOutput "  Runtime Modifications: $($harmonyUsage.RuntimeModifications)" "White"
    Write-ColorOutput "  Note: Harmony is used for complex functionality CWL cannot handle without losing complexity" "Cyan"
    
    if ($targetIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($targetIssues.Count) potential target issues"
        $script:Results.Harmony += @{
            Type = "Targets"
            Status = "Issues Found"
            Details = $targetIssues
        }
    }
    else {
        Write-ColorOutput "✓ Patch targets validated" "Green"
    }
    
    $script:Results.Harmony += @{
        Type = "Usage Analysis"
        Status = "Analyzed"
        Details = $harmonyUsage
    }
}

# ============================================================
# TODO TRACKING
# ============================================================

function Test-TODOTracking {
    Write-ProgressDetail "TODO Check" "Analyzing TODO items..." 10
    
    $todoFile = Join-Path $ModPath "TODO.md"
    if (-not (Test-Path $todoFile)) {
        Write-ColorOutput "Warning: TODO.md not found" "Yellow"
        return
    }
    
    $todoContent = Get-Content $todoFile -Raw -ErrorAction SilentlyContinue
    $todoIssues = @()
    $todoStats = @{
        Total = 0
        Completed = 0
        Pending = 0
        InProgress = 0
    }
    
    # Count TODO items from TODO.md
    $pendingMatches = [regex]::Matches($todoContent, '-\s*\[ \]')
    $completedMatches = [regex]::Matches($todoContent, '-\s*\[x\]|-\s*\[X\]')
    $inProgressMatches = [regex]::Matches($todoContent, 'IN PROGRESS|in progress|In Progress')
    
    $todoStats.Pending = $pendingMatches.Count
    $todoStats.Completed = $completedMatches.Count
    $todoStats.InProgress = $inProgressMatches.Count
    $todoStats.Total = $todoStats.Pending + $todoStats.Completed
    
    Write-ColorOutput "TODO.md Statistics:" "Cyan"
    Write-ColorOutput "  Total Items: $($todoStats.Total)" "White"
    Write-ColorOutput "  Completed: $($todoStats.Completed)" "Green"
    Write-ColorOutput "  Pending: $($todoStats.Pending)" "Yellow"
    Write-ColorOutput "  In Progress: $($todoStats.InProgress)" "Cyan"
    
    # Check for TODO/FIXME comments in code
    $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse
    $codeTodos = @()
    
    foreach ($file in $csFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        $lineNumber = 1
        
        foreach ($line in ($content -split "`n")) {
            if ($line -match '(?i)(TODO|FIXME|HACK|XXX)[:\s]+(.+)') {
                $todoType = $matches[1]
                $todoText = $matches[2].Trim()
                $codeTodos += @{
                    File = $file.Name
                    Line = $lineNumber
                    Type = $todoType
                    Text = $todoText
                }
            }
            $lineNumber++
        }
    }
    
    if ($codeTodos.Count -gt 0) {
        Write-ColorOutput "  Code TODOs: $($codeTodos.Count) found in source files" "Yellow"
        if ($VerbosePreference -eq 'Continue') {
            foreach ($todo in $codeTodos) {
                Write-ColorOutput "    - $($todo.File):$($todo.Line) [$($todo.Type)] $($todo.Text)" "Cyan"
            }
        }
    }
    
    # Check for items marked as "IN PROGRESS" that might be stale
    if ($todoStats.InProgress -gt 0) {
        $inProgressItems = [regex]::Matches($todoContent, '-\s*\[x\].*IN PROGRESS[^\n]*\n(?:[^\n]*\n){0,5}[^\n]*-\s*\[x\]', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        if ($inProgressItems.Count -gt 0) {
            $todoIssues += "Found $($inProgressItems.Count) items marked as completed but still 'IN PROGRESS' - may need review"
        }
    }
    
    if ($todoIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($todoIssues.Count) TODO tracking issues"
        $script:Results.TODOs += @{
            Type = "Tracking"
            Status = "Issues Found"
            Details = $todoIssues
        }
    }
    
    $script:Results.TODOs += @{
        Type = "Statistics"
        Status = "Analyzed"
        Details = $todoStats
        CodeTodos = $codeTodos
    }
    
    Write-ColorOutput "✓ TODO tracking complete" "Green"
}

function Test-TODOCompletion {
    Write-ProgressDetail "TODO Check" "Checking TODO completion status..." 30
    
    $todoFile = Join-Path $ModPath "TODO.md"
    if (-not (Test-Path $todoFile)) {
        return
    }
    
    $todoContent = Get-Content $todoFile -Raw -ErrorAction SilentlyContinue
    
    # Check for completed items that reference code
    $completedItems = [regex]::Matches($todoContent, '-\s*\[x\][^\n]*(?:✅|COMPLETED|Completed)[^\n]*')
    $completionIssues = @()
    
    foreach ($match in $completedItems) {
        $item = $match.Value
        # Check if completed item references a file that doesn't exist or has issues
        if ($item -match '`([^`]+\.cs)`') {
            $referencedFile = $matches[1]
            $filePath = Get-CachedChildItem -Path $ModPath -Filter $referencedFile -Recurse -File
            if ($filePath.Count -eq 0) {
                $completionIssues += "Completed TODO references missing file: $referencedFile"
            }
        }
    }
    
    if ($completionIssues.Count -gt 0) {
        $script:Results.Warnings += "Found $($completionIssues.Count) TODO completion issues"
        $script:Results.TODOs += @{
            Type = "Completion"
            Status = "Issues Found"
            Details = $completionIssues
        }
    }
}

# ============================================================
# DEPENDENCY CHECKS
# ============================================================

function Test-Dependencies {
    Write-ProgressDetail "Dependency Check" "Checking dependencies..." 10
    
    $manifestPath = Join-Path $ModPath "manifest.json"
    if (-not (Test-Path $manifestPath)) {
        return
    }
    
    try {
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        
        if ($manifest.dependencies_json) {
            $deps = $manifest.dependencies_json | ConvertFrom-Json
            $missingDeps = @()
            
            foreach ($dep in $deps) {
                # Check if dependency mod exists (simplified check)
                $depPath = Join-Path (Split-Path $ModPath) $dep.name
                if (-not (Test-Path $depPath)) {
                    $missingDeps += $dep.name
                }
            }
            
            if ($missingDeps.Count -gt 0) {
                $script:Results.Warnings += "Missing dependencies: $($missingDeps -join ', ')"
                $script:Results.Dependencies += @{
                    Type = "Missing"
                    Status = "Issues Found"
                    Details = $missingDeps
                }
            }
            else {
                Write-ColorOutput "✓ All dependencies found" "Green"
            }
        }
    }
    catch {
        Write-ColorOutput "Could not check dependencies: $_" "Yellow"
    }
}

# ============================================================
# MAIN EXECUTION
# ============================================================

function Start-ModCheck {
    Write-ColorOutput "`n=== CustomRaceClassCreator Mod Checker ===" "Cyan"
    Write-ColorOutput "Mod Path: $ModPath" "White"
    Write-ColorOutput "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" "Gray"
    
    # Validate mod path
    if (-not (Test-Path $ModPath)) {
        Write-ColorOutput "ERROR: Mod path does not exist: $ModPath" "Red"
        return
    }
    
    # Scan all mod files first for summary
    Write-ColorOutput "--- Scanning Mod Files ---" "Cyan"
    $allModFiles = Get-AllModFiles -Path $ModPath
    Write-ColorOutput "C# files: $($allModFiles.CSharp.Count)" "White"
    Write-ColorOutput "JSON files: $($allModFiles.Json.Count)" "White"
    Write-ColorOutput "XML/Project files: $($allModFiles.Xml.Count)" "White"
    Write-ColorOutput "Excel files: $($allModFiles.Excel.Count)" "White"
    Write-ColorOutput "Markdown files: $($allModFiles.Markdown.Count)" "White"
    Write-ColorOutput "Other files: $($allModFiles.Other.Count)" "White"
    
    # List key files
    $keyFiles = @("SpellgunSpellbowHelper.cs", "SpellEngine.cs", "ModSaveSafetyIntegration.cs", "TODO.md")
    Write-ColorOutput "`nKey files status:" "Cyan"
    foreach ($keyFile in $keyFiles) {
        $found = $allModFiles.CSharp + $allModFiles.Markdown | Where-Object { $_.Name -eq $keyFile }
        if ($found) {
            Write-ColorOutput "  ✓ $keyFile found" "Green"
        }
        else {
            Write-ColorOutput "  ✗ $keyFile not found" "Yellow"
        }
    }
    
    # Check AI connection (required for this mod checker)
    if ($UseAI) {
        Write-ColorOutput "`n--- AI Connection (Required) ---" "Cyan"
        Write-ColorOutput "Checking Ollama at $script:OllamaUrl..." "Cyan"
        if (-not (Test-OllamaConnection)) {
            Write-ColorOutput "`n❌ FATAL: Ollama not available. This mod checker requires AI to function." "Red"
            Write-ColorOutput "  Exiting..." "Yellow"
            exit 1
        }
        else {
            Write-ColorOutput "✓ AI connection established" "Green"
        }
    }
    else {
        Write-ColorOutput "`n--- AI: Disabled ---" "Gray"
        Write-ColorOutput "  WARNING: Running without AI. Many features will be unavailable." "Yellow"
    }
    
    # Build source context first (for AI and validation)
    Write-ColorOutput "`n--- Building Source Context ---" "Cyan"
    Build-SourceContext
    
    # Determine which checks to run
    $checksToRun = @()
    $validCheckTypes = @("code", "assets", "config", "dependencies", "cwl", "harmony", "todos", "all")
    
    # Validate CheckTypes parameter
    if ($CheckTypes -match '^[A-Z]:\\' -or (Test-Path $CheckTypes -ErrorAction SilentlyContinue)) {
        # CheckTypes looks like a file path - this is wrong, reset to default
        Write-ColorOutput "WARNING: CheckTypes parameter appears to be a file path: '$CheckTypes'" "Yellow"
        Write-ColorOutput "Resetting to default 'all' checks" "Yellow"
        $CheckTypes = "all"
    }
    
    if ($CheckTypes -eq "all") {
        $checksToRun = @("code", "assets", "config", "dependencies", "cwl", "harmony", "todos")
    }
    else {
        $checksToRun = $CheckTypes -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $validCheckTypes -contains $_ }
        
        # If no valid check types found, default to "all"
        if ($checksToRun.Count -eq 0) {
            Write-ColorOutput "WARNING: No valid check types found in '$CheckTypes'. Using 'all'." "Yellow"
            $checksToRun = @("code", "assets", "config", "dependencies", "cwl", "harmony", "todos")
        }
    }
    
    Write-ColorOutput "`nCheckTypes parameter: '$CheckTypes'" "Cyan"
    Write-ColorOutput "Checks to run: $($checksToRun -join ', ')" "Cyan"
    Write-ColorOutput "Number of checks: $($checksToRun.Count)" "Cyan"
    
    if ($checksToRun.Count -eq 0) {
        Write-ColorOutput "ERROR: No checks to run! CheckTypes='$CheckTypes'" "Red"
        Write-ColorOutput "This should not happen - check parameter parsing" "Red"
        return
    }
    
    Write-ColorOutput "`nStarting check execution..." "Cyan"
    
    # Run checks
    if ($checksToRun -contains "code") {
        Write-ColorOutput "`n--- Code Checks ---" "Cyan"
        try {
            Test-CodeCompilation
            if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
                Write-ColorOutput "Code compilation check had issues (exit code: $LASTEXITCODE)" "Yellow"
            }
        }
        catch {
            Write-ColorOutput "Error in code compilation check: $_" "Red"
            Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" "Red"
            $script:Results.Errors += "Code compilation check failed: $_"
        }
        
        try {
            Test-CodeStructure
        }
        catch {
            Write-ColorOutput "Error in code structure check: $_" "Red"
            Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" "Red"
            $script:Results.Errors += "Code structure check failed: $_"
        }
        
        try {
            Test-CodeReferences
        }
        catch {
            Write-ColorOutput "Error in code references check: $_" "Red"
            Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" "Red"
            $script:Results.Errors += "Code references check failed: $_"
        }
    }
    
    if ($checksToRun -contains "cwl") {
        Write-ColorOutput "`n--- CWL Integration Checks (CWL is REQUIRED) ---" "Cyan"
        try {
            Test-CWLAdapters
            Test-CWLUsage
            Test-CWLRequired
            Test-SaveSafetySystems
            Test-SaveSafetyUsage
        }
        catch {
            Write-ColorOutput "Error in CWL checks: $_" "Red"
            $script:Results.Errors += "CWL check failed: $_"
        }
    }
    
    if ($checksToRun -contains "harmony") {
        Write-ColorOutput "`n--- Harmony Patch Checks ---" "Cyan"
        try {
            Test-HarmonyPatches
            Test-HarmonyTargets
        }
        catch {
            Write-ColorOutput "Error in Harmony checks: $_" "Red"
            $script:Results.Errors += "Harmony check failed: $_"
        }
    }
    
    if ($checksToRun -contains "assets") {
        Write-ColorOutput "`n--- Asset Checks ---" "Cyan"
        try {
            Test-AssetStructure
            Test-AssetFiles
            Test-AssetBundles
        }
        catch {
            Write-ColorOutput "Error in asset checks: $_" "Red"
            $script:Results.Errors += "Asset check failed: $_"
        }
    }
    
    if ($checksToRun -contains "config") {
        Write-ColorOutput "`n--- Configuration Checks ---" "Cyan"
        try {
            Test-ConfigFiles
            Test-Manifest
        }
        catch {
            Write-ColorOutput "Error in config checks: $_" "Red"
            $script:Results.Errors += "Config check failed: $_"
        }
    }
    
    if ($checksToRun -contains "dependencies") {
        Write-ColorOutput "`n--- Dependency Checks ---" "Cyan"
        try {
            Test-Dependencies
        }
        catch {
            Write-ColorOutput "Error in dependency checks: $_" "Red"
            $script:Results.Errors += "Dependency check failed: $_"
        }
    }
    
    if ($checksToRun -contains "todos") {
        Write-ColorOutput "`n--- TODO Tracking Checks ---" "Cyan"
        try {
            Test-TODOTracking
            Test-TODOCompletion
        }
        catch {
            Write-ColorOutput "Error in TODO checks: $_" "Red"
            $script:Results.Errors += "TODO check failed: $_"
        }
    }
    
    # Generate summary
    Write-ColorOutput "`n========================================" "Cyan"
    Write-ColorOutput "           SUMMARY" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    
    # File stats
    Write-ColorOutput "`nFiles Scanned:" "White"
    Write-ColorOutput "  Total C# files: $($script:FileScanStats.TotalFound)" "White"
    Write-ColorOutput "  Build artifacts excluded: $($script:FileScanStats.UnityExcluded)" "Gray"
    Write-ColorOutput "  Mod files analyzed: $($script:FileScanStats.ModFilesProcessed)" "Green"
    
    # Check results
    Write-ColorOutput "`nCheck Results:" "White"
    Write-ColorOutput "  Checks executed: $($checksToRun -join ', ')" "Cyan"
    
    if ($script:Results.Errors.Count -gt 0) {
        Write-ColorOutput "  Errors: $($script:Results.Errors.Count)" "Red"
    }
    else {
        Write-ColorOutput "  Errors: 0" "Green"
    }
    
    if ($script:Results.Warnings.Count -gt 0) {
        Write-ColorOutput "  Warnings: $($script:Results.Warnings.Count)" "Yellow"
    }
    else {
        Write-ColorOutput "  Warnings: 0" "Green"
    }
    
    Write-ColorOutput "  AI Suggestions: $($script:Results.Suggestions.Count)" "Cyan"
    
    # Mod components
    Write-ColorOutput "`nMod Components:" "White"
    Write-ColorOutput "  CWL Adapters: $($script:SourceContext.CWLAdapters.Count)" "Cyan"
    Write-ColorOutput "  Harmony Patches: $($script:SourceContext.HarmonyPatches.Count)" "Cyan"
    
    if ($script:Results.TODOs.Count -gt 0) {
        $todoStats = $script:Results.TODOs | Where-Object { $_.Type -eq "Statistics" } | Select-Object -First 1
        if ($todoStats -and $todoStats.Details) {
            Write-ColorOutput "  TODO Items: $($todoStats.Details.Pending) pending, $($todoStats.Details.Completed) completed" "Cyan"
        }
    }
    
    # Show errors if any
    if ($script:Results.Errors.Count -gt 0) {
        Write-ColorOutput "`nErrors Found:" "Red"
        foreach ($error in $script:Results.Errors) {
            Write-ColorOutput "  ✗ $error" "Red"
        }
    }
    
    Write-ColorOutput "`n========================================" "Cyan"
    
    # Show AI stats if AI was used
    if ($UseAI) {
        Show-AIStats
    }
    
    # Generate report if requested
    if ($GenerateReport) {
        Generate-Report
    }
    
    # Display suggestions
    if ($script:Results.Suggestions.Count -gt 0) {
        Write-ColorOutput "`n=== AI Suggestions ===" "Cyan"
        foreach ($suggestion in $script:Results.Suggestions) {
            Write-ColorOutput "`n[$($suggestion.Category)] $($suggestion.Issue)" "Yellow"
            Write-ColorOutput $suggestion.Suggestion "White"
        }
    }
    
    Write-ColorOutput "`nCompleted: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "Gray"
    
    # Interactive recommendation mode
    if ($Interactive -and $UseAI) {
        Write-ColorOutput "`n========================================" "Cyan"
        Write-ColorOutput "  INTERACTIVE RECOMMENDATION MODE" "Cyan"
        Write-ColorOutput "========================================" "Cyan"
        Start-InteractiveRecommendations
    }
}

function Start-InteractiveRecommendations {
    <#
    .SYNOPSIS
    Interactive mode where users can provide recommendations to AI for code improvements.
    #>
    
    Write-ColorOutput "`nYou can provide recommendations for code improvements." "Cyan"
    Write-ColorOutput "The AI will show implementation options for your suggestions." "Cyan"
    Write-ColorOutput "`nCommands:" "White"
    Write-ColorOutput "  - Type a recommendation and press Enter" "Gray"
    Write-ColorOutput "  - Type 'file: [filename]' to focus on a specific file" "Gray"
    Write-ColorOutput "  - Type 'list' to see available files" "Gray"
    Write-ColorOutput "  - Type 'quit' or 'exit' to finish" "Gray"
    Write-ColorOutput ""

    if (-not (Test-IsInteractiveSession)) {
        Write-ColorOutput "  ⊘ Interactive recommendations skipped (no live console or -Interactive not set)" "Gray"
        return
    }
    
    $currentFile = $null
    
    while ($true) {
        Write-ColorOutput "`nEnter recommendation (or 'quit' to exit): " "Yellow" -NoNewline
        $userInput = Read-Host
        
        if ([string]::IsNullOrWhiteSpace($userInput)) {
            continue
        }
        
        $userInput = $userInput.Trim()
        
        # Handle commands
        if ($userInput -match '^(quit|exit|q)$') {
            Write-ColorOutput "Exiting interactive mode..." "Gray"
            break
        }
        elseif ($userInput -match '^list$') {
            Show-AvailableFiles
            continue
        }
        elseif ($userInput -match '^file:\s*(.+)') {
            $fileName = $matches[1].Trim()
            $file = Get-CachedChildItem -Path $ModPath -Filter $fileName -Recurse -File | Select-Object -First 1
            if ($file) {
                $currentFile = $file
                Write-ColorOutput "  ✓ Focused on: $($file.Name)" "Green"
                Write-ColorOutput "    Path: $($file.FullName)" "Gray"
            }
            else {
                Write-ColorOutput "  ✗ File not found: $fileName" "Red"
            }
            continue
        }
        elseif ($userInput -match '^clear$') {
            $currentFile = $null
            Write-ColorOutput "  Cleared file focus" "Gray"
            continue
        }
        
        # Process recommendation
        Write-ColorOutput "`nAnalyzing recommendation..." "Cyan"
        $implementation = Get-AIImplementationSuggestion -Recommendation $userInput -TargetFile $currentFile
        
        if ($implementation) {
            Show-ImplementationOptions -Implementation $implementation -TargetFile $currentFile
        }
        else {
            Write-ColorOutput "  ⚠ Could not get AI implementation suggestion" "Yellow"
        }
    }
}

function Show-AvailableFiles {
    <#
    .SYNOPSIS
    Shows list of available C# files for user to focus on.
    #>
    $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse | Select-Object -First 50
    Write-ColorOutput "`nAvailable C# files (showing first 50):" "Cyan"
    $csFiles | ForEach-Object {
        $relativePath = $_.FullName.Replace($ModPath, ".")
        Write-ColorOutput "  - $($_.Name) ($relativePath)" "Gray"
    }
    if ($csFiles.Count -eq 50) {
        Write-ColorOutput "  ... and more (use 'file: [name]' to focus on a specific file)" "Gray"
    }
}

function Get-AIImplementationSuggestion {
    <#
    .SYNOPSIS
    Gets AI implementation suggestions for user recommendations.
    #>
    param(
        [string]$Recommendation,
        [System.IO.FileInfo]$TargetFile = $null
    )
    
    if (-not $UseAI) {
        return $null
    }
    
    # Build context
    $context = Get-ModSystemContext
    $fileContext = ""
    $fileContent = ""
    
    if ($TargetFile) {
        $fileContext = "Target File: $($TargetFile.Name)`nPath: $($TargetFile.FullName)`n"
        $fileContent = Get-Content $TargetFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($fileContent) {
            $lineCount = ($fileContent -split "`n").Count
            $fileContext += "Lines: $lineCount`n`n"
            
            # Include relevant sections (first 100 lines and last 50 lines for context)
            $lines = $fileContent -split "`n"
            $preview = ""
            if ($lines.Count -gt 150) {
                $preview = ($lines[0..99] -join "`n") + "`n... [middle section omitted] ...`n" + ($lines[-50..-1] -join "`n")
            }
            else {
                $preview = $fileContent
            }
            $fileContext += "File Content Preview:`n$preview`n"
        }
    }
    else {
        # Get summary of mod structure
        $csFiles = Get-ModCsFiles -Path $ModPath -Filter "*.cs" -Recurse
        $fileContext = "Mod has $($csFiles.Count) C# files. "
        $fileContext += "Key files: " + (($csFiles | Select-Object -First 10 | ForEach-Object { $_.Name }) -join ", ") + "`n"
    }
    
    $prompt = @"
User Recommendation: $Recommendation

$context
$fileContext

Provide implementation options for this recommendation. Show:

1. PRIMARY IMPLEMENTATION (recommended approach)
2. ALTERNATIVE OPTIONS (if applicable)

Format for PRIMARY:
FILE: [filename.cs] (or "new file" if creating new)
LOCATION: [where in file - method name, class, line number, etc.]
APPROACH: [description of approach]
IMPLEMENTATION:
```csharp
[complete code implementation]
```
EXPLANATION: [why this approach]
PROS: [advantages]
CONS: [disadvantages if any]

Format for ALTERNATIVES:
ALTERNATIVE 1:
FILE: [filename.cs]
APPROACH: [different approach]
IMPLEMENTATION:
```csharp
[code]
```
PROS: [advantages]
CONS: [disadvantages]

Be specific with actual code, not just descriptions.
"@
    
    $response = Invoke-OllamaRequest -Prompt $prompt -TaskType "code" -ResponseLength "detailed"
    return $response
}

function Show-ImplementationOptions {
    <#
    .SYNOPSIS
    Displays AI implementation options and allows user to apply them.
    #>
    param(
        [string]$Implementation,
        [System.IO.FileInfo]$TargetFile = $null,
        [hashtable]$OriginalFix = $null
    )
    
    if (-not $Implementation) {
        return
    }
    
    Write-ColorOutput "`n========================================" "Cyan"
    Write-ColorOutput "  AI IMPLEMENTATION SUGGESTIONS" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    
    # Parse implementation response
    $primary = @{
        File = $null
        Location = ""
        Approach = ""
        Code = ""
        Explanation = ""
        Pros = ""
        Cons = ""
    }
    $alternatives = @()
    
    $currentSection = ""
    $inCodeBlock = $false
    $currentCode = ""
    $currentAlt = $null
    
    $lines = $Implementation -split "`n"
    foreach ($line in $lines) {
        $line = $line.Trim()
        
        if ($line -match '^FILE:\s*(.+)') {
            if ($currentAlt) {
                $alternatives += $currentAlt
            }
            $currentAlt = $null
            $primary.File = $matches[1].Trim()
            $currentSection = ""
        }
        elseif ($line -match '^ALTERNATIVE\s+(\d+):') {
            if ($currentAlt) {
                $alternatives += $currentAlt
            }
            $currentAlt = @{
                Number = [int]$matches[1]
                File = $null
                Approach = ""
                Code = ""
                Pros = ""
                Cons = ""
            }
            $currentSection = ""
        }
        elseif ($line -match '^LOCATION:') {
            $currentSection = "LOCATION"
            $primary.Location = ""
        }
        elseif ($line -match '^APPROACH:') {
            $currentSection = "APPROACH"
            if ($currentAlt) {
                $currentAlt.Approach = ""
            }
            else {
                $primary.Approach = ""
            }
        }
        elseif ($line -match '^IMPLEMENTATION:') {
            $currentSection = "IMPLEMENTATION"
            $inCodeBlock = $false
            $currentCode = ""
        }
        elseif ($line -match '^EXPLANATION:') {
            $currentSection = "EXPLANATION"
            $primary.Explanation = ""
        }
        elseif ($line -match '^PROS:') {
            $currentSection = "PROS"
            if ($currentAlt) {
                $currentAlt.Pros = ""
            }
            else {
                $primary.Pros = ""
            }
        }
        elseif ($line -match '^CONS:') {
            $currentSection = "CONS"
            if ($currentAlt) {
                $currentAlt.Cons = ""
            }
            else {
                $primary.Cons = ""
            }
        }
        elseif ($line -match '^```(?:csharp|cs|C#)?') {
            $inCodeBlock = -not $inCodeBlock
            if (-not $inCodeBlock) {
                # End of code block
                if ($currentAlt) {
                    $currentAlt.Code = $currentCode.Trim()
                }
                else {
                    $primary.Code = $currentCode.Trim()
                }
                $currentCode = ""
            }
        }
        elseif ($inCodeBlock) {
            $currentCode += $line + "`n"
        }
        elseif ($currentSection -eq "LOCATION" -and $line) {
            $primary.Location += $line + " "
        }
        elseif ($currentSection -eq "APPROACH" -and $line) {
            if ($currentAlt) {
                $currentAlt.Approach += $line + " "
            }
            else {
                $primary.Approach += $line + " "
            }
        }
        elseif ($currentSection -eq "EXPLANATION" -and $line) {
            $primary.Explanation += $line + " "
        }
        elseif ($currentSection -eq "PROS" -and $line) {
            if ($currentAlt) {
                $currentAlt.Pros += $line + " "
            }
            else {
                $primary.Pros += $line + " "
            }
        }
        elseif ($currentSection -eq "CONS" -and $line) {
            if ($currentAlt) {
                $currentAlt.Cons += $line + " "
            }
            else {
                $primary.Cons += $line + " "
            }
        }
    }
    
    # Save last alternative
    if ($currentAlt) {
        $alternatives += $currentAlt
    }
    
    # Display primary implementation
    Write-ColorOutput "`n--- PRIMARY IMPLEMENTATION ---" "Cyan"
    if ($primary.File) {
        Write-ColorOutput "File: $($primary.File)" "White"
    }
    if ($primary.Location) {
        Write-ColorOutput "Location: $($primary.Location.Trim())" "White"
    }
    if ($primary.Approach) {
        Write-ColorOutput "Approach: $($primary.Approach.Trim())" "White"
    }
    if ($primary.Explanation) {
        Write-ColorOutput "Explanation: $($primary.Explanation.Trim())" "Gray"
    }
    if ($primary.Pros) {
        Write-ColorOutput "Pros: $($primary.Pros.Trim())" "Green"
    }
    if ($primary.Cons) {
        Write-ColorOutput "Cons: $($primary.Cons.Trim())" "Red"
    }
    if ($primary.Code) {
        Write-ColorOutput "`nImplementation Code:" "Yellow"
        Write-ColorOutput $primary.Code "Gray"
    }
    
    # Display alternatives
    if ($alternatives.Count -gt 0) {
        Write-ColorOutput "`n--- ALTERNATIVE OPTIONS ---" "Cyan"
        for ($i = 0; $i -lt $alternatives.Count; $i++) {
            $alt = $alternatives[$i]
            Write-ColorOutput "`n[$($i + 1)] Alternative $($i + 1):" "Yellow"
            if ($alt.File) {
                Write-ColorOutput "  File: $($alt.File)" "White"
            }
            if ($alt.Approach) {
                Write-ColorOutput "  Approach: $($alt.Approach.Trim())" "White"
            }
            if ($alt.Pros) {
                Write-ColorOutput "  Pros: $($alt.Pros.Trim())" "Green"
            }
            if ($alt.Cons) {
                Write-ColorOutput "  Cons: $($alt.Cons.Trim())" "Red"
            }
            if ($alt.Code) {
                Write-ColorOutput "  Code: $($alt.Code.Substring(0, [Math]::Min(100, $alt.Code.Length)))..." "Gray"
            }
        }
    }
    
    # Ask for user's recommendation or choice (recommendation-first approach)
    if (-not (Test-IsInteractiveSession)) {
        Write-ColorOutput "  ⊘ Skipped implementation (non-interactive safe default)" "Gray"
        return $false
    }
    Write-ColorOutput "`nRecommend another change, or " "Yellow" -NoNewline
    if ($alternatives.Count -gt 0) {
        Write-ColorOutput "(Enter=accept primary/1-$($alternatives.Count)=alternative/N=skip): " "Yellow" -NoNewline
    }
    else {
        Write-ColorOutput "(Enter=accept/N=skip): " "Yellow" -NoNewline
    }
    $response = Read-Host
    
    if ([string]::IsNullOrWhiteSpace($response)) {
        # User pressed Enter - accept primary implementation
        if (Apply-Implementation -Implementation $primary -TargetFile $TargetFile) {
            return $true
        }
    }
    elseif ($response -match '^[Nn]') {
        # Fall back to original fix if available
        if ($OriginalFix) {
            Write-ColorOutput "  Applying original AI fix..." "Cyan"
            if (Apply-SingleFix -FileName $OriginalFix.File -LineNumber $OriginalFix.Line -OldCode $OriginalFix.Old -NewCode $OriginalFix.New) {
                return $true
            }
        }
        Write-ColorOutput "  ⊘ Implementation not applied" "Gray"
    }
    elseif ($response -match '^[1-9]' -and $alternatives.Count -gt 0) {
        # User chose an alternative by number
        $altIndex = [int]$response - 1
        if ($altIndex -ge 0 -and $altIndex -lt $alternatives.Count) {
            $alt = $alternatives[$altIndex]
            if (Apply-Implementation -Implementation $alt -TargetFile $TargetFile) {
                return $true
            }
        }
    }
    else {
        # User provided a new recommendation
        Write-ColorOutput "  Getting AI implementation for your recommendation..." "Cyan"
        $newImplementation = Get-AIImplementationSuggestion -Recommendation $response -TargetFile $TargetFile
        if ($newImplementation) {
            return Show-ImplementationOptions -Implementation $newImplementation -TargetFile $TargetFile -OriginalFix $OriginalFix
        }
        else {
            Write-ColorOutput "  ⊘ Could not get AI implementation" "Yellow"
        }
    }
    
    return $false
}

function Apply-Implementation {
    <#
    .SYNOPSIS
    Applies an AI-generated implementation to a file.
    #>
    param(
        [hashtable]$Implementation,
        [System.IO.FileInfo]$TargetFile = $null
    )
    
    if (-not $Implementation.Code) {
        Write-ColorOutput "  ✗ No implementation code provided" "Red"
        return $false
    }
    
    $targetFileName = $Implementation.File
    if (-not $targetFileName -or $targetFileName -eq "new file") {
        if (-not (Test-IsInteractiveSession)) {
            Write-ColorOutput "  ⊘ Cannot determine target file (non-interactive; skipping)" "Gray"
            return $false
        }
        Write-ColorOutput "  ⚠ Cannot determine target file. Please specify file name:" "Yellow"
        Write-ColorOutput "  Enter file name (or 'cancel'): " "Yellow" -NoNewline
        $targetFileName = Read-Host
        if ($targetFileName -match '^(cancel|quit|exit)$') {
            return $false
        }
    }
    
    # Find or create file
    $file = $null
    if ($TargetFile -and $TargetFile.Name -eq $targetFileName) {
        $file = $TargetFile
    }
    else {
        $file = Get-CachedChildItem -Path $ModPath -Filter $targetFileName -Recurse -File | Select-Object -First 1
    }
    
    if (-not $file) {
        if (-not (Test-IsInteractiveSession)) {
            Write-ColorOutput "  ⊘ File not found: $targetFileName (non-interactive; will not create)" "Gray"
            return $false
        }
        Write-ColorOutput "  ⚠ File not found: $targetFileName" "Yellow"
        Write-ColorOutput "  Create new file? (Y/N): " "Yellow" -NoNewline
        $create = Read-Host
        if ($create -match '^[Yy]') {
            $filePath = Join-Path $ModPath $targetFileName
            # Create directory if needed
            $dir = Split-Path $filePath -Parent
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }
            New-Item -ItemType File -Path $filePath -Force | Out-Null
            $file = Get-Item $filePath
            Write-ColorOutput "  ✓ Created new file: $targetFileName" "Green"
        }
        else {
            return $false
        }
    }
    
    # Create backup
    $backupPath = "$($file.FullName).backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item $file.FullName $backupPath -ErrorAction SilentlyContinue
    Write-ColorOutput "  Backup: $(Split-Path $backupPath -Leaf)" "Gray"
    
    try {
        # Apply implementation
        if ($Implementation.Location -match 'line\s+(\d+)') {
            # Insert at specific line
            $lineNum = [int]$matches[1]
            $content = Get-Content $file.FullName -Raw
            $lines = $content -split "`n"
            $newLines = @()
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($i -eq $lineNum - 1) {
                    $newLines += ($Implementation.Code -split "`n")
                }
                $newLines += $lines[$i]
            }
            $newContent = $newLines -join "`n"
            Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8 -NoNewline
        }
        else {
            # Append to file
            $content = Get-Content $file.FullName -Raw
            $newContent = $content + "`n`n// AI Implementation: $($Implementation.Approach)`n" + $Implementation.Code
            Set-Content -Path $file.FullName -Value $newContent -Encoding UTF8 -NoNewline
        }
        
        Write-ColorOutput "  ✓ Implementation applied to $($file.Name)" "Green"
        return $true
    }
    catch {
        Write-ColorOutput "  ✗ Error applying implementation: $_" "Red"
        return $false
    }
}

function Generate-Report {
    $reportPath = Join-Path $ModPath "mod_check_report.html"
    
    $html = @"
<!DOCTYPE html>
<html>
<head>
    <title>CustomRaceClassCreator Mod Check Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .error { color: red; }
        .warning { color: orange; }
        .success { color: green; }
        .suggestion { background: #f0f0f0; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Mod Check Report</h1>
    <p>Generated: $(Get-Date)</p>
    <p>Mod Path: $ModPath</p>
    
    <h2>Summary</h2>
    <ul>
        <li class="error">Errors: $($script:Results.Errors.Count)</li>
        <li class="warning">Warnings: $($script:Results.Warnings.Count)</li>
        <li class="success">Suggestions: $($script:Results.Suggestions.Count)</li>
    </ul>
    
    <h2>Errors</h2>
    <ul>
$(($script:Results.Errors | ForEach-Object { "        <li class='error'>$_</li>" }) -join "`n")
    </ul>
    
    <h2>Warnings</h2>
    <ul>
$(($script:Results.Warnings | ForEach-Object { "        <li class='warning'>$_</li>" }) -join "`n")
    </ul>
    
    <h2>Suggestions</h2>
$(($script:Results.Suggestions | ForEach-Object { 
    "    <div class='suggestion'><h3>[$($_.Category)] $($_.Issue)</h3><p>$($_.Suggestion)</p></div>"
}) -join "`n")
</body>
</html>
"@
    
    $html | Out-File -FilePath $reportPath -Encoding UTF8
    Write-ColorOutput "`nReport generated: $reportPath" "Green"
}

# Run the checker
try {
    Start-ModCheck
}
catch {
    Write-ColorOutput "`nFATAL ERROR: $_" "Red"
    Write-ColorOutput "Stack trace: $($_.ScriptStackTrace)" "Red"
    exit 1
}

