# ============================================================================
# AIImplementChanges.ps1
# ============================================================================
# AI-Powered Code Change Implementation Tool
# Uses AI to analyze code and automatically implement suggested changes
# Based on AutoUpdate-CPP20-API.ps1
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Path = ".",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Backup = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowDetails = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:34b",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxCodeLength = 8000,  # Max characters per file for AI analysis
    
    [Parameter(Mandatory=$false)]
    [int]$MaxAITimePerFile = 300,  # 5 minutes max per file
    
    [Parameter(Mandatory=$false)]
    [switch]$Interactive = $false,  # Ask before applying each change
    
    [Parameter(Mandatory=$false)]
    [string]$Focus = "",  # Focus area: "C++20", "CodeChain", "SmartPointers", "All"
    
    [Parameter(Mandatory=$false)]
    [string]$LogFile = "",  # Path to log file with recommended changes
    
    [Parameter(Mandatory=$false)]
    [switch]$GuiMode = $false  # When true, skip main execution (for GUI wrapper)
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# ============================================================================
# CONFIGURATION
# ============================================================================

$Script:Config = @{
    Path = $Path
    DryRun = $DryRun
    Backup = $Backup
    Verbose = $ShowDetails
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    MaxCodeLength = $MaxCodeLength
    MaxAITimePerFile = $MaxAITimePerFile
    Interactive = $Interactive
    Focus = if ($Focus) { $Focus } else { "All" }
    FilesProcessed = 0
    FilesModified = 0
    TotalChanges = 0
    AIAnalyses = 0
    ChangesApplied = 0
    ChangesSkipped = 0
}

# File operation cache to avoid repeated expensive scans (prevents CPU burn)
$Script:FileCache = @{
    GetChildItem = @{}
    LastCacheTime = @{}
    CacheTimeoutMinutes = 5
}

# Performance throttling settings
$Script:PerformanceConfig = @{
    FileReadDelayMs = 10
    FileScanBatchSize = 50
    ProgressUpdateInterval = 10
    EnableThrottling = $true
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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
    if ($Script:FileCache.GetChildItem.ContainsKey($cacheKey)) {
        $cacheTime = $Script:FileCache.LastCacheTime[$cacheKey]
        $ageMinutes = ([datetime]::Now - $cacheTime).TotalMinutes
        
        if ($ageMinutes -lt $Script:FileCache.CacheTimeoutMinutes) {
            # Cache hit - return cached result
            return $Script:FileCache.GetChildItem[$cacheKey]
        }
        else {
            # Cache expired - remove
            $Script:FileCache.GetChildItem.Remove($cacheKey)
            $Script:FileCache.LastCacheTime.Remove($cacheKey)
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
    $Script:FileCache.GetChildItem[$cacheKey] = $result
    $Script:FileCache.LastCacheTime[$cacheKey] = [datetime]::Now
    
    return $result
}

function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $color = switch ($Type) {
        "Info"    { "Cyan" }
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error"   { "Red" }
        default   { "White" }
    }
    
    $prefix = switch ($Type) {
        "Info"    { "[*]" }
        "Success" { "[+]" }
        "Warning" { "[!]" }
        "Error"   { "[-]" }
        default   { "[.]" }
    }
    
    Write-Host "$prefix $Message" -ForegroundColor $color
}

# ============================================================================
# OLLAMA AI INTEGRATION
# ============================================================================

function Test-OllamaAvailable {
    try {
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        $models = $response.models | ForEach-Object { $_.name }
        
        if ($models -contains $Script:Config.OllamaModel -or $models -like "*codellama*") {
            if ($models -notcontains $Script:Config.OllamaModel) {
                $codellamaModel = $models | Where-Object { $_ -like "*codellama*34b*" -or $_ -like "*codellama:34b*" } | Select-Object -First 1
                if ($codellamaModel) {
                    $Script:Config.OllamaModel = $codellamaModel
                    Write-Status "Using available model: $codellamaModel" "Info"
                } else {
                    $codellamaModel = $models | Where-Object { $_ -like "*codellama*" } | Select-Object -First 1
                    if ($codellamaModel) {
                        $Script:Config.OllamaModel = $codellamaModel
                        Write-Status "Using available CodeLlama model: $codellamaModel" "Info"
                    }
                }
            }
            return $true
        }
        Write-Status "Model $($Script:Config.OllamaModel) not found. Available: $($models -join ', ')" "Warning"
        return $false
    } catch {
        Write-Status "Ollama not available: $_" "Warning"
        return $false
    }
}

function Invoke-AICodeAnalysis {
    <#
    .SYNOPSIS
      Uses AI to analyze code and generate specific change suggestions with code examples
    #>
    param(
        [string]$FilePath,
        [string]$FileContent,
        [string]$ApiVersion = "unknown"
    )
    
    if (-not (Test-OllamaAvailable)) {
        Write-Status "Skipping AI analysis (Ollama not available)" "Warning"
        return $null
    }
    
    try {
        # Limit code size for AI analysis
        $codeSnippet = if ($FileContent.Length -gt $Script:Config.MaxCodeLength) {
            $FileContent.Substring(0, $Script:Config.MaxCodeLength) + "`n// ... (truncated) ..."
        } else {
            $FileContent
        }
        
        $focusArea = switch ($Script:Config.Focus) {
            "C++20" { "C++20 standard library updates, modern C++ features, ranges, concepts" }
            "CodeChain" { "Transcendence CodeChain API changes (CC.Link -> CCodeChain::LinkCode, Print(), TopLevel(), etc.)" }
            "SmartPointers" { "Smart pointer conversions (raw pointers to ICCItemPtr, memory safety)" }
            default { "C++20 migration, CodeChain API updates, smart pointers, const correctness, modern C++ features" }
        }
        
        $systemPrompt = @"
You are an expert C++ code analyzer specializing in C++20 migration and the Transcendence CodeChain API.
Your task is to analyze code and provide SPECIFIC, ACTIONABLE changes that need to be made.

API Version: $ApiVersion
Focus Area: $focusArea

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Do NOT suggest using third-party libraries or dependencies
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
- Work within the constraints of existing includes and dependencies

IMPORTANT: You must respond with a JSON object containing:
1. An array of specific changes to make
2. Each change must include: the exact code pattern to find, the replacement code, and a description
3. Changes should be ordered from most critical to least critical
4. Provide complete, compilable code examples

Response Format (JSON):
{
  "changes": [
    {
      "priority": 1-10 (10 = critical),
      "description": "Brief description of the change",
      "find": "exact code pattern to find (can use regex-like patterns)",
      "replace": "exact replacement code",
      "category": "C++20|CodeChain|SmartPointers|ConstCorrectness|Other",
      "reason": "Why this change is needed"
    }
  ],
  "summary": "Brief summary of all changes needed",
  "estimated_impact": "Low|Medium|High"
}
"@
        
        $userPrompt = @"
Analyze this C++ code file and identify ALL specific changes needed for C++20 migration and CodeChain API updates.

FILE: $FilePath
API VERSION: $ApiVersion
FOCUS: $focusArea

CODE:
```cpp
$codeSnippet
```

Provide a JSON response with specific changes. Each change must include:
- Exact code pattern to find (use literal strings, not complex regex)
- Exact replacement code
- Priority (1-10)
- Category
- Description

CRITICAL: Do NOT suggest adding new #include statements or external libraries. Only work with existing includes and C++20 standard library.

Be specific and actionable. Focus on:
1. CodeChain API changes (CC.Link -> CCodeChain::LinkCode, Print() parameter removal, etc.)
2. Smart pointer conversions
3. C++20 standard library updates
4. Const correctness
5. Modern C++20 features

Respond ONLY with valid JSON, no markdown code blocks.
"@
        
        # Use /api/generate for better performance
        $generateUrl = "$($Script:Config.OllamaApiUrl)/generate"
        $generateBody = @{
            model = $Script:Config.OllamaModel
            prompt = ($systemPrompt + "`n`n" + $userPrompt)
            stream = $false
            options = @{
                num_ctx = 8192
                temperature = 0.1  # Lower temperature for more deterministic code changes
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "  Analyzing code with AI (this may take 30-60 seconds)..." "Info"
        
        $response = Invoke-RestMethod -Uri $generateUrl -Method Post -Body $generateBody -ContentType "application/json" -TimeoutSec $Script:Config.MaxAITimePerFile
        $aiResponse = if ($response.response) { $response.response.Trim() } else { "" }
        
        if ($aiResponse) {
            # Try to parse JSON response
            try {
                # Extract JSON from markdown code blocks if present
                if ($aiResponse -match '```json\s*(\{.*?\})\s*```' -or $aiResponse -match '```\s*(\{.*?\})\s*```') {
                    $aiResponse = $matches[1]
                }
                
                # Handle multi-line JSON
                $aiResponse = $aiResponse -replace "`n", " " -replace "`r", " "
                
                $result = $aiResponse | ConvertFrom-Json
                
                $Script:Config.AIAnalyses++
                
                return @{
                    Changes = if ($result.changes) { $result.changes } else { @() }
                    Summary = if ($result.summary) { $result.summary } else { "" }
                    EstimatedImpact = if ($result.estimated_impact) { $result.estimated_impact } else { "Medium" }
                    RawResponse = $aiResponse
                }
            } catch {
                Write-Status "  AI response received but JSON parsing failed: $_" "Warning"
                Write-Status "  Raw response: $($aiResponse.Substring(0, [Math]::Min(200, $aiResponse.Length)))..." "Info"
                return $null
            }
        }
    } catch {
        Write-Status "  AI analysis failed: $_" "Warning"
        return $null
    }
    
    return $null
}

function Parse-LogFile {
    <#
    .SYNOPSIS
      Parses a log file to extract recommended changes
    #>
    param(
        [string]$LogFilePath
    )
    
    if (-not (Test-Path $LogFilePath)) {
        Write-Status "Log file not found: $LogFilePath" "Error"
        return @()
    }
    
    $logContent = Get-Content -Path $LogFilePath -Raw -ErrorAction SilentlyContinue
    if (-not $logContent) {
        Write-Status "Log file is empty: $LogFilePath" "Warning"
        return @()
    }
    
    $changes = @()
    
    # Try to parse JSON format first (from AI responses)
    try {
        if ($logContent -match '\{.*"changes".*\}') {
            $jsonMatch = $logContent | Select-String -Pattern '\{.*"changes".*?\}' -AllMatches
            if ($jsonMatch) {
                foreach ($match in $jsonMatch.Matches) {
                    try {
                        $jsonObj = $match.Value | ConvertFrom-Json
                        if ($jsonObj.changes) {
                            foreach ($change in $jsonObj.changes) {
                                $changes += $change
                            }
                        }
                    } catch {
                        # Continue parsing other formats
                    }
                }
            }
        }
    } catch {
        # Not JSON, continue with text parsing
    }
    
    # Parse text format (from AI suggestions or manual logs)
    # Look for patterns like:
    # - "Find: ... Replace: ..."
    # - "Change: ..."
    # - "Description: ... Find: ... Replace: ..."
    # - Lines with "->" or "=>" indicating replacements
    
    $lines = $logContent -split "`n"
    $currentChange = $null
    
    foreach ($line in $lines) {
        $line = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        
        # Look for change patterns
        if ($line -match '(?i)(find|pattern|search):\s*(.+)') {
            if (-not $currentChange) {
                $currentChange = @{
                    find = ""
                    replace = ""
                    description = ""
                    priority = 5
                    category = "LogFile"
                }
            }
            $currentChange.find = $matches[2].Trim()
        }
        elseif ($line -match '(?i)(replace|with|to):\s*(.+)') {
            if ($currentChange) {
                $currentChange.replace = $matches[2].Trim()
            }
        }
        elseif ($line -match '(?i)(description|change|suggestion):\s*(.+)') {
            if (-not $currentChange) {
                $currentChange = @{
                    find = ""
                    replace = ""
                    description = ""
                    priority = 5
                    category = "LogFile"
                }
            }
            $currentChange.description = $matches[2].Trim()
        }
        elseif ($line -match '(.+?)\s*[-=]>\s*(.+)') {
            # Pattern: "old -> new"
            $changes += @{
                find = $matches[1].Trim()
                replace = $matches[2].Trim()
                description = "Replace: $($matches[1].Trim()) -> $($matches[2].Trim())"
                priority = 5
                category = "LogFile"
            }
        }
        elseif ($line -match 'CC\.Link' -or $line -match 'CCodeChain::LinkCode' -or $line -match '\.Print\s*\([^)]*CC' -or $line -match '\.TopLevel') {
            # Common CodeChain patterns
            if ($line -match 'CC\.Link\s*\(') {
                $changes += @{
                    find = "CC.Link("
                    replace = "CCodeChain::LinkCode("
                    description = "Replace CC.Link with CCodeChain::LinkCode"
                    priority = 10
                    category = "CodeChain"
                }
            }
        }
        
        # If we have a complete change, add it
        if ($currentChange -and $currentChange.find -and $currentChange.replace) {
            if (-not $currentChange.description) {
                $currentChange.description = "Change: $($currentChange.find) -> $($currentChange.replace)"
            }
            $changes += $currentChange
            $currentChange = $null
        }
    }
    
    # Add any remaining change
    if ($currentChange -and $currentChange.find -and $currentChange.replace) {
        if (-not $currentChange.description) {
            $currentChange.description = "Change: $($currentChange.find) -> $($currentChange.replace)"
        }
        $changes += $currentChange
    }
    
    Write-Status "Parsed $($changes.Count) changes from log file" "Info"
    return $changes
}

function Apply-AIChange {
    <#
    .SYNOPSIS
      Applies a single AI-suggested change to code
    #>
    param(
        [string]$Content,
        [object]$Change
    )
    
    $findPattern = $Change.find
    $replacePattern = $Change.replace
    $description = $Change.description
    
    # Try simple string replacement first
    if ($Content -match [regex]::Escape($findPattern)) {
        $newContent = $Content -replace [regex]::Escape($findPattern), $replacePattern
        return @{
            Success = $true
            Content = $newContent
            Message = "Applied: $description"
        }
    }
    
    # Try as regex pattern if simple replacement didn't work
    try {
        $newContent = $Content -replace $findPattern, $replacePattern
        if ($newContent -ne $Content) {
            return @{
                Success = $true
                Content = $newContent
                Message = "Applied (regex): $description"
            }
        }
    } catch {
        # Regex failed, try literal replacement with some flexibility
        $escapedPattern = [regex]::Escape($findPattern)
        $newContent = $Content -replace $escapedPattern, $replacePattern
        if ($newContent -ne $Content) {
            return @{
                Success = $true
                Content = $newContent
                Message = "Applied (literal): $description"
            }
        }
    }
    
    return @{
        Success = $false
        Content = $Content
        Message = "Could not find pattern: $description"
    }
}

function Process-FileWithLogChanges {
    <#
    .SYNOPSIS
      Processes a file using changes from a log file
    #>
    param(
        [string]$FilePath,
        [array]$LogChanges
    )
    
    $content = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return @{ Modified = $false; Changes = 0; ChangeLog = @() }
    }
    
    $originalContent = $content
    $changeLog = @()
    $changesApplied = 0
    
    # Apply each change from log, one by one
    foreach ($change in $LogChanges) {
        $priority = if ($change.priority) { $change.priority } else { 5 }
        $description = if ($change.description) { $change.description } else { "Unknown change" }
        $category = if ($change.category) { $change.category } else { "LogFile" }
        
        # Ask user if interactive mode
        if ($Script:Config.Interactive) {
            Write-Host ""
            Write-Host "Change: $description" -ForegroundColor Yellow
            Write-Host "Category: $category" -ForegroundColor Gray
            Write-Host "Priority: $priority/10" -ForegroundColor Gray
            Write-Host "Find: $($change.find)" -ForegroundColor Cyan
            Write-Host "Replace: $($change.replace)" -ForegroundColor Green
            
            $response = Read-Host "Apply this change? (Y/N/Skip remaining)"
            if ($response -eq "N" -or $response -eq "n") {
                $Script:Config.ChangesSkipped++
                $changeLog += "  [SKIPPED] $description"
                continue
            }
            if ($response -eq "Skip remaining" -or $response -eq "skip") {
                Write-Status "  Skipping remaining changes" "Warning"
                break
            }
        }
        
        # Apply the change
        $result = Apply-AIChange -Content $content -Change $change
        
        if ($result.Success) {
            $content = $result.Content
            $changesApplied++
            $Script:Config.ChangesApplied++
            $changeLog += "  [$category] $description (Priority: $priority)"
            
            if ($Script:Config.Verbose) {
                Write-Status "    $($result.Message)" "Success"
            }
        } else {
            if ($Script:Config.Verbose) {
                Write-Status "    $($result.Message)" "Warning"
            }
            $changeLog += "  [FAILED] $description"
        }
    }
    
    return @{
        Modified = ($content -ne $originalContent)
        Content = $content
        Changes = $changesApplied
        ChangeLog = $changeLog
    }
}

function Process-FileWithAI {
    <#
    .SYNOPSIS
      Processes a single file using AI to identify and apply changes
    #>
    param(
        [string]$FilePath,
        [string]$ApiVersion = "unknown"
    )
    
    $content = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return @{ Modified = $false; Changes = 0; ChangeLog = @() }
    }
    
    $originalContent = $content
    $changeLog = @()
    $changesApplied = 0
    
    # Get AI analysis
    $aiAnalysis = Invoke-AICodeAnalysis -FilePath $FilePath -FileContent $content -ApiVersion $ApiVersion
    
    if (-not $aiAnalysis -or $aiAnalysis.Changes.Count -eq 0) {
        Write-Status "  No AI-suggested changes found" "Info"
        return @{ Modified = $false; Changes = 0; ChangeLog = @() }
    }
    
    Write-Status "  AI found $($aiAnalysis.Changes.Count) suggested change(s)" "Info"
    if ($aiAnalysis.Summary) {
        Write-Status "  Summary: $($aiAnalysis.Summary)" "Info"
    }
    
    # Sort changes by priority (highest first)
    $sortedChanges = $aiAnalysis.Changes | Sort-Object -Property { if ($_.priority) { $_.priority } else { 5 } } -Descending
    
    # Apply each change
    foreach ($change in $sortedChanges) {
        $priority = if ($change.priority) { $change.priority } else { 5 }
        $description = if ($change.description) { $change.description } else { "Unknown change" }
        $category = if ($change.category) { $change.category } else { "Other" }
        $reason = if ($change.reason) { $change.reason } else { "" }
        
        # Ask user if interactive mode
        if ($Script:Config.Interactive) {
            Write-Host ""
            Write-Host "Change: $description" -ForegroundColor Yellow
            Write-Host "Category: $category" -ForegroundColor Gray
            Write-Host "Priority: $priority/10" -ForegroundColor Gray
            if ($reason) {
                Write-Host "Reason: $reason" -ForegroundColor Gray
            }
            Write-Host "Find: $($change.find)" -ForegroundColor Cyan
            Write-Host "Replace: $($change.replace)" -ForegroundColor Green
            
            $response = Read-Host "Apply this change? (Y/N/Skip remaining)"
            if ($response -eq "N" -or $response -eq "n") {
                $Script:Config.ChangesSkipped++
                $changeLog += "  [SKIPPED] $description"
                continue
            }
            if ($response -eq "Skip remaining" -or $response -eq "skip") {
                Write-Status "  Skipping remaining changes" "Warning"
                break
            }
        }
        
        # Apply the change
        $result = Apply-AIChange -Content $content -Change $change
        
        if ($result.Success) {
            $content = $result.Content
            $changesApplied++
            $Script:Config.ChangesApplied++
            $changeLog += "  [$category] $description (Priority: $priority)"
            
            if ($Script:Config.Verbose) {
                Write-Status "    $($result.Message)" "Success"
            }
        } else {
            if ($Script:Config.Verbose) {
                Write-Status "    $($result.Message)" "Warning"
            }
            $changeLog += "  [FAILED] $description"
        }
    }
    
    return @{
        Modified = ($content -ne $originalContent)
        Content = $content
        Changes = $changesApplied
        ChangeLog = $changeLog
        AIAnalysis = $aiAnalysis
    }
}

# ============================================================================
# API VERSION DETECTION (from AutoUpdate-CPP20-API.ps1)
# ============================================================================

function Get-ApiVersion {
    param([string]$SearchPath)
    
    Write-Status "Detecting API version..." "Info"
    
    $folderName = Split-Path -Leaf $SearchPath
    if ($folderName -match 'API(\d+)') {
        $version = $matches[1]
        Write-Status "Detected API version from folder: $version" "Success"
        return $version
    }
    
    $parentFolder = Split-Path -Parent $SearchPath
    if ($parentFolder -match 'API(\d+)') {
        $version = $matches[1]
        Write-Status "Detected API version from parent folder: $version" "Success"
        return $version
    }
    
    $projFiles = Get-CachedChildItem -Path $SearchPath -Recurse -Filter "*.vcxproj" -File | Select-Object -First 5
    foreach ($file in $projFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match 'API(\d+)') {
            $version = $matches[1]
            Write-Status "Detected API version from project file: $version" "Success"
            return $version
        }
    }
    
    Write-Status "Could not auto-detect API version, using 'unknown'" "Warning"
    return "unknown"
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

# Skip main execution if in GUI mode
if ($GuiMode) {
    return
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AI-Powered Code Change Implementation Tool" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Resolve path
$resolvedPath = Resolve-Path $Script:Config.Path -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
    Write-Status "Path not found: $($Script:Config.Path)" "Error"
    exit 1
}

$Script:Config.Path = $resolvedPath.Path
Write-Status "Processing: $($Script:Config.Path)" "Info"

# Detect API version
$apiVersion = Get-ApiVersion -SearchPath $Script:Config.Path
Write-Status "API Version: $apiVersion" "Info"

# Check AI availability
Write-Status "AI Model: $($Script:Config.OllamaModel)" "Info"
if (-not (Test-OllamaAvailable)) {
    Write-Status "Ollama not available - cannot proceed" "Error"
    exit 1
}
Write-Status "Ollama service is available" "Success"

if ($Script:Config.DryRun) {
    Write-Status "DRY RUN MODE - No files will be modified" "Warning"
}

if ($Script:Config.Interactive) {
    Write-Status "INTERACTIVE MODE - You will be asked to confirm each change" "Info"
}

Write-Status "Focus Area: $($Script:Config.Focus)" "Info"
Write-Host ""

# Check if log file is provided
$logChanges = @()
if ($Script:Config.LogFile -and (Test-Path $Script:Config.LogFile)) {
    Write-Status "Loading changes from log file: $($Script:Config.LogFile)" "Info"
    $logChanges = Parse-LogFile -LogFilePath $Script:Config.LogFile
    
    if ($logChanges.Count -eq 0) {
        Write-Status "No changes found in log file, falling back to AI analysis" "Warning"
    } else {
        Write-Status "Found $($logChanges.Count) changes to implement from log file" "Success"
        Write-Status "Will implement changes one by one" "Info"
    }
}

# Get all C++ files
# Use cached file operations to prevent CPU burn
$cppFiles = Get-CachedChildItem -Path $Script:Config.Path -Recurse -Include "*.cpp", "*.h", "*.hpp" -File | Where-Object { -not $_.PSIsContainer }

if ($cppFiles.Count -eq 0) {
    Write-Status "No C++ files found in: $($Script:Config.Path)" "Warning"
    exit 0
}

Write-Status "Found $($cppFiles.Count) C++ file(s) to process" "Info"
Write-Host ""

# Process each file with CPU throttling
$fileCount = $cppFiles.Count
foreach ($file in $cppFiles) {
    $Script:Config.FilesProcessed++
    
    # Throttle file operations to reduce CPU usage
    if ($Script:PerformanceConfig.EnableThrottling -and $Script:Config.FilesProcessed % $Script:PerformanceConfig.FileScanBatchSize -eq 0) {
        Start-Sleep -Milliseconds $Script:PerformanceConfig.FileReadDelayMs
    }
    
    Write-Status "Processing: $($file.Name) ($($Script:Config.FilesProcessed)/$fileCount)" "Info"
    
    # Use log file changes if available, otherwise use AI
    if ($logChanges.Count -gt 0) {
        $result = Process-FileWithLogChanges -FilePath $file.FullName -LogChanges $logChanges
    } else {
        $result = Process-FileWithAI -FilePath $file.FullName -ApiVersion $apiVersion
    }
    
    if ($result.Modified) {
        $Script:Config.FilesModified++
        $Script:Config.TotalChanges += $result.Changes
        
        Write-Status "Modified: $($file.Name) ($($result.Changes) change(s))" "Success"
        
        if ($Script:Config.Verbose) {
            foreach ($log in $result.ChangeLog) {
                Write-Host $log -ForegroundColor Gray
            }
        }
        
        if (-not $Script:Config.DryRun) {
            # Create backup
            if ($Script:Config.Backup) {
                $backupPath = "$($file.FullName).backup"
                Copy-Item -Path $file.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
            }
            
            # Write modified content
            [System.IO.File]::WriteAllText($file.FullName, $result.Content, [System.Text.Encoding]::UTF8)
            Write-Status "  Saved changes" "Success"
        }
    } else {
        if ($Script:Config.Verbose) {
            Write-Status "  No changes needed" "Info"
        }
    }
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Status "API Version: $apiVersion" "Info"
Write-Status "Files processed: $($Script:Config.FilesProcessed)" "Info"
Write-Status "Files modified: $($Script:Config.FilesModified)" $(if ($Script:Config.FilesModified -gt 0) { "Success" } else { "Info" })
Write-Status "Total changes applied: $($Script:Config.ChangesApplied)" $(if ($Script:Config.ChangesApplied -gt 0) { "Success" } else { "Info" })
Write-Status "Changes skipped: $($Script:Config.ChangesSkipped)" "Info"
Write-Status "AI analyses performed: $($Script:Config.AIAnalyses)" "Info"

if ($Script:Config.DryRun) {
    Write-Host ""
    Write-Status "This was a dry run. No files were modified." "Warning"
    Write-Status "Run without -DryRun to apply changes." "Warning"
}

Write-Host ""
Write-Status "AI implementation complete!" "Success"
Write-Host ""

