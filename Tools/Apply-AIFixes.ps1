<#
.SYNOPSIS
    Applies AI-suggested fixes using a faster AI model

.DESCRIPTION
    This tool focuses on applying AI-suggested fixes to C++ files using a faster AI model
    (default: codellama:7b) for quick processing. It can:
    - Re-analyze files and apply suggestions automatically
    - Work with saved suggestion files
    - Use faster models for quick fixes

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER Path
    Path to the API folder or file to process

.PARAMETER OllamaModel
    Ollama model to use (default: codellama:7b for speed)

.PARAMETER OllamaUrl
    Ollama API URL (default: http://localhost:11434)

.PARAMETER SuggestionsFile
    Optional: Path to a file containing previously saved suggestions

.PARAMETER DryRun
    Show what would be fixed without making changes

.PARAMETER ShowDetails
    Verbose output

.EXAMPLE
    .\Apply-AIFixes.ps1 "D:\path\to\API59"

.EXAMPLE
    .\Apply-AIFixes.ps1 "D:\path\to\API59" -OllamaModel "codellama:13b"
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Path = ".",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b",  # Faster model by default
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$SuggestionsFile = $null,  # Path to file containing suggestions to apply
    
    [Parameter(Mandatory=$false)]
    [string]$SuggestionsFormat = "auto",  # Format: auto, json, text, one-per-line
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowDetails = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$ParallelJobs = 0  # 0 = auto-scale with CPU, otherwise number of files to process in parallel
)

$ErrorActionPreference = "Continue"

# Import shared Ollama integration module if available
$sharedModulePath = Join-Path $PSScriptRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force
}

# Detect optimal CPU thread count for AI processing
$cpuCores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
if (-not $cpuCores) {
    $cpuCores = $env:NUMBER_OF_PROCESSORS
    if ($cpuCores) { $cpuCores = [int]$cpuCores } else { $cpuCores = 4 }
}
# Use most cores for AI processing - leave only 1-2 for system
# For systems with many cores, use all but 2; for smaller systems, use all but 1
if ($cpuCores -gt 8) {
    $optimalThreads = $cpuCores - 2  # Leave 2 cores for system
} else {
    $optimalThreads = [Math]::Max(2, $cpuCores - 1)  # Leave 1 core for system
}

# Auto-scale parallel jobs based on CPU count if not specified
# Use 2-3 files per core for good throughput (AI processing is I/O bound waiting for responses)
if ($ParallelJobs -eq 0) {
    if ($cpuCores -ge 16) {
        $ParallelJobs = $cpuCores * 2  # High-core systems: 2 files per core
    } elseif ($cpuCores -ge 8) {
        $ParallelJobs = [Math]::Floor($cpuCores * 1.5)  # Medium systems: 1.5 files per core
    } else {
        $ParallelJobs = [Math]::Max(4, $cpuCores)  # Small systems: at least 4, or 1 per core
    }
}

# Configuration
$Script:Config = @{
    Path = $Path
    DryRun = $DryRun
    Verbose = $ShowDetails
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    FilesProcessed = 0
    FilesModified = 0
    SuggestionsApplied = 0
    LastAICallTime = $null
    AIDelay = 1  # Shorter delay for faster processing
    SuggestionsFile = $SuggestionsFile
    SuggestionsFormat = $SuggestionsFormat
    LoadedSuggestions = @{}
    NumThreads = $optimalThreads  # Optimal CPU thread count
    CpuCores = $cpuCores
    ParallelJobs = $ParallelJobs
}

# Utility Functions
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

function Test-OllamaAvailable {
    try {
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        $models = $response.models | ForEach-Object { $_.name }
        
        if ($models -contains $Script:Config.OllamaModel) {
            return $true
        }
        
        # Try to find a similar model
        $similarModel = $models | Where-Object { $_ -like "*codellama*7b*" -or $_ -like "*codellama:7b*" } | Select-Object -First 1
        if ($similarModel) {
            $Script:Config.OllamaModel = $similarModel
            Write-Status "Using available model: $similarModel" "Info"
            return $true
        }
        
        Write-Status "Model $($Script:Config.OllamaModel) not found. Available: $($models -join ', ')" "Warning"
        return $false
    } catch {
        Write-Status "Ollama not available: $_" "Warning"
        return $false
    }
}

function Invoke-AIGenerateCodeChange {
    param(
        [string]$FilePath,
        [string]$Suggestion,
        [string]$CurrentContent,
        [string]$ApiVersion = "unknown"
    )
    
    # Apply AI delay
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0 -and $Script:Config.Verbose) {
                Write-Status "  Waiting ${waitTime}s before AI call..." "Info"
            }
            Start-Sleep -Seconds $waitTime
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $fileName = Split-Path -Leaf $FilePath
        $maxCodeLength = 4000
        $codeSnippet = if ($CurrentContent.Length -gt $maxCodeLength) {
            $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
        } else {
            $CurrentContent
        }
        
        $systemPrompt = @"
You are an expert C++ code fixer specializing in C++20 migration.
Generate ACTUAL CODE CHANGES that can be applied to fix the issue.

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies

Return the COMPLETE MODIFIED CODE SECTION that implements the suggestion.
"@
        
        $userPrompt = @"
FILE: $fileName
API VERSION: $ApiVersion

SUGGESTION TO IMPLEMENT:
$Suggestion

CURRENT CODE:
```cpp
$codeSnippet
```

Generate the ACTUAL CODE CHANGE needed to implement this suggestion.
Return the complete modified code section(s) that should replace the current code.

Format your response as:
OLD CODE:
[code to replace]

NEW CODE:
[replacement code]
"@
        
        $requestBody = @{
            model = $Script:Config.OllamaModel
            messages = @(
                @{ role = "system"; content = $systemPrompt }
                @{ role = "user"; content = $userPrompt }
            )
            stream = $false
            options = @{
                num_ctx = 4000  # Smaller context for faster processing
                temperature = 0.1  # Lower for more deterministic code
                num_predict = 800  # Allow reasonable response length
                num_thread = $Script:Config.NumThreads  # Maximum CPU thread usage
                numa = $false  # Disable NUMA for better CPU utilization
                use_mmap = $true  # Memory-mapped files for faster loading
                use_mlock = $false  # Don't lock memory (allows swapping if needed)
                numa_strategy = "disabled"  # Disable NUMA for better CPU usage
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "      [AI] Calling AI to generate code change (model: $($Script:Config.OllamaModel))..." "Info"
        Write-Status "      [AI] Sending request to Ollama API at $($Script:Config.OllamaApiUrl)/chat..." "Info"
        Write-Status "      [AI] AI processing (this will use CPU - may take 10-30 seconds)..." "Info"
        
        $startTime = Get-Date
        try {
            # Make the actual AI call - this should use CPU
            $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 90 -ErrorAction Stop
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            Write-Status "      [AI] AI response received (took $([Math]::Round($elapsed, 1))s)" "Success"
            
            if (-not $response) {
                Write-Status "      [ERROR] AI returned null response" "Error"
                return $null
            }
            
            if (-not $response.message) {
                Write-Status "      [ERROR] AI response missing message field" "Error"
                Write-Status "      Response structure: $($response | ConvertTo-Json -Depth 2)" "Info"
                return $null
            }
            
            $aiResponse = $response.message.content.Trim()
            if ($aiResponse.Length -eq 0) {
                Write-Status "      [WARNING] AI returned empty response content" "Warning"
                Write-Status "      Full response: $($response | ConvertTo-Json -Depth 3)" "Info"
                return $null
            }
            
            Write-Status "      [AI] AI generated $($aiResponse.Length) characters of code" "Info"
            if ($Script:Config.Verbose) {
                $preview = if ($aiResponse.Length -gt 200) { $aiResponse.Substring(0, 200) + "..." } else { $aiResponse }
                Write-Status "      Preview: $preview" "Info"
            }
            
            return $aiResponse
        } catch {
            Write-Status "      [ERROR] AI API call FAILED: $($_.Exception.Message)" "Error"
            Write-Status "      Error type: $($_.Exception.GetType().Name)" "Error"
            if ($_.Exception.Response) {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $responseBody = $reader.ReadToEnd()
                Write-Status "      Error response: $responseBody" "Error"
            }
            Write-Status "      Request URL: $($Script:Config.OllamaApiUrl)/chat" "Info"
            Write-Status "      Model: $($Script:Config.OllamaModel)" "Info"
            Write-Status "      This suggests AI is NOT being used - check Ollama logs" "Error"
            return $null
        }
    }
    catch {
        Write-Status "AI code generation failed: $_" "Warning"
        return $null
    }
}

function Apply-AICodeChange {
    param(
        [string]$FilePath,
        [string]$AICodeChange,
        [string]$CurrentContent
    )
    
    try {
        # Try to extract OLD CODE and NEW CODE from AI response
        $oldCodePattern = '(?s)OLD CODE:\s*(.*?)(?=NEW CODE:|$)'
        $newCodePattern = '(?s)NEW CODE:\s*(.*?)(?=OLD CODE:|$)'
        
        $oldCode = $null
        $newCode = $null
        
        if ($AICodeChange -match $oldCodePattern) {
            $oldCode = $Matches[1].Trim()
        }
        if ($AICodeChange -match $newCodePattern) {
            $newCode = $Matches[1].Trim()
        }
        
        # If we have both old and new, do a replacement
        if ($oldCode -and $newCode) {
            # Clean up code blocks if present
            $oldCode = $oldCode -replace '```cpp\s*', '' -replace '```c\+\+\s*', '' -replace '```\s*', '' -replace '```', '' -replace '^\s+', '' -replace '\s+$', ''
            $newCode = $newCode -replace '```cpp\s*', '' -replace '```c\+\+\s*', '' -replace '```\s*', '' -replace '```', '' -replace '^\s+', '' -replace '\s+$', ''
            
            # Try exact string match first
            if ($CurrentContent.Contains($oldCode)) {
                $modifiedContent = $CurrentContent.Replace($oldCode, $newCode)
                return @{ Success = $true; Content = $modifiedContent; Method = "replacement" }
            }
            
            # Try with normalized whitespace
            $oldCodeNormalized = $oldCode -replace '\r\n', "`n" -replace '\r', "`n"
            $currentNormalized = $CurrentContent -replace '\r\n', "`n" -replace '\r', "`n"
            
            if ($currentNormalized.Contains($oldCodeNormalized)) {
                $newCodeNormalized = $newCode -replace '\r\n', "`n" -replace '\r', "`n"
                $modifiedContent = $currentNormalized.Replace($oldCodeNormalized, $newCodeNormalized)
                # Restore original line endings
                if ($CurrentContent -match '\r\n') {
                    $modifiedContent = $modifiedContent -replace "`n", "`r`n"
                } elseif ($CurrentContent -match '\r[^\n]') {
                    $modifiedContent = $modifiedContent -replace "`n", "`r"
                }
                return @{ Success = $true; Content = $modifiedContent; Method = "replacement" }
            }
        }
        
        # Fallback: Extract code from markdown code blocks
        $codeBlockPattern = '(?s)```(?:cpp|c\+\+)?\s*(.*?)```'
        if ($AICodeChange -match $codeBlockPattern) {
            $extractedCode = $Matches[1].Trim()
            # Try to find where to insert based on context
            # For now, append with marker for manual review
            $modifiedContent = $CurrentContent + "`n`n// ===== AI APPLIED CHANGE (review and integrate manually) =====`n" + $extractedCode + "`n// ===== END AI CHANGE =====`n"
            Write-Status "  Code extracted and appended for manual review" "Warning"
            return @{ Success = $true; Content = $modifiedContent; Method = "append_review" }
        }
        
        Write-Status "  Could not automatically apply change - manual review needed" "Warning"
        return @{ Success = $false; Content = $CurrentContent; Method = "manual" }
    }
    catch {
        Write-Status "  Error applying AI change: $_" "Warning"
        return @{ Success = $false; Content = $CurrentContent; Method = "error" }
    }
}

function Invoke-AICodeReview {
    param(
        [string]$FilePath,
        [string]$ApiVersion = "unknown",
        [string]$CurrentContent = $null
    )
    
    if (-not $CurrentContent) {
        $CurrentContent = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    }
    
    if (-not $CurrentContent -or $CurrentContent.Length -gt 50000) {
        return @()
    }
    
    # Apply AI delay
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0 -and $Script:Config.Verbose) {
                Write-Status "  Waiting ${waitTime}s before AI review..." "Info"
            }
            Start-Sleep -Seconds $waitTime
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $maxCodeLength = 3000
        $codeSnippet = if ($CurrentContent.Length -gt $maxCodeLength) {
            $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
        } else {
            $CurrentContent
        }
        
        $fileName = Split-Path -Leaf $FilePath
        
        $systemPrompt = @"
You are an expert C++ code reviewer specializing in C++20 migration.
Analyze the code and suggest specific, actionable improvements.

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
"@
        
        $userPrompt = @"
Review this C++ file for C++20 improvements.

FILE: $fileName
API VERSION: $ApiVersion

CODE:
```cpp
$codeSnippet
```

Suggest specific, actionable improvements for C++20 compliance and best practices.
List them as bullet points, one per line.
"@
        
        $requestBody = @{
            model = $Script:Config.OllamaModel
            messages = @(
                @{ role = "system"; content = $systemPrompt }
                @{ role = "user"; content = $userPrompt }
            )
            stream = $false
            options = @{
                num_ctx = 4000  # Smaller context for faster processing
                temperature = 0.1
                num_predict = 300
                num_thread = $Script:Config.NumThreads  # Maximum CPU thread usage
                numa = $false  # Disable NUMA for better CPU utilization
                use_mmap = $true  # Memory-mapped files for faster loading
                use_mlock = $false  # Don't lock memory (allows swapping if needed)
                numa_strategy = "disabled"  # Disable NUMA for better CPU usage
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "  [AI] Calling AI to review file and generate suggestions..." "Info"
        Write-Status "  [AI] AI processing (this will use CPU - may take 5-15 seconds)..." "Info"
        $startTime = Get-Date
        try {
            $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 60 -ErrorAction Stop
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            Write-Status "  [AI] AI review complete (took $([Math]::Round($elapsed, 1))s)" "Success"
            
            if (-not $response -or -not $response.message) {
                Write-Status "  [ERROR] AI returned invalid response structure" "Error"
                return @()
            }
            
            $aiResponse = $response.message.content.Trim()
            
            if ($aiResponse) {
                $suggestions = $aiResponse -split "`n" | Where-Object { $_ -match '^\s*[-*•]' -or $_ -match '^\d+\.' } | ForEach-Object { $_.Trim() } | Where-Object { $_.Length -gt 0 }
                Write-Status "  [AI] AI generated $($suggestions.Count) suggestion(s)" "Info"
                return $suggestions
            } else {
                Write-Status "  [WARNING] AI returned empty response" "Warning"
                return @()
            }
        } catch {
            Write-Status "  [ERROR] AI review FAILED: $($_.Exception.Message)" "Error"
            Write-Status "  This suggests AI is NOT being used - check Ollama" "Error"
            return @()
        }
    } catch {
        Write-Status "AI review failed for $FilePath : $_" "Warning"
    }
    
    return @()
}

function Load-SuggestionsFromFile {
    param(
        [string]$FilePath,
        [string]$Format = "auto"
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Status "Suggestions file not found: $FilePath" "Error"
        return @{}
    }
    
    $suggestions = @{}
    $content = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    
    if (-not $content) {
        Write-Status "Suggestions file is empty" "Warning"
        return @{}
    }
    
    # Auto-detect format
    if ($Format -eq "auto") {
        if ($content -match '^\s*\{') {
            $Format = "json"
        } elseif ($content -match '^\s*\[.*file.*:.*suggestion') {
            $Format = "structured"
        } else {
            $Format = "text"
        }
    }
    
    Write-Status "Loading suggestions from file (format: $Format)..." "Info"
    
    try {
        switch ($Format.ToLower()) {
            "json" {
                $data = $content | ConvertFrom-Json
                if ($data.PSObject.Properties.Name -contains "suggestions") {
                    foreach ($item in $data.suggestions) {
                        $filePath = $item.file
                        if (-not $suggestions.ContainsKey($filePath)) {
                            $suggestions[$filePath] = @()
                        }
                        $suggestions[$filePath] += $item.suggestion
                    }
                } elseif ($data.PSObject.Properties.Name -contains "files") {
                    foreach ($file in $data.files) {
                        $filePath = $file.path
                        if (-not $suggestions.ContainsKey($filePath)) {
                            $suggestions[$filePath] = @()
                        }
                        foreach ($suggestion in $file.suggestions) {
                            $suggestions[$filePath] += $suggestion
                        }
                    }
                }
            }
            "structured" {
                # Format: file: path/to/file.cpp
                # suggestion: Fix this issue
                $lines = $content -split "`n"
                $currentFile = $null
                foreach ($line in $lines) {
                    if ($line -match '^file:\s*(.+)') {
                        $currentFile = $matches[1].Trim()
                        if (-not $suggestions.ContainsKey($currentFile)) {
                            $suggestions[$currentFile] = @()
                        }
                    } elseif ($line -match '^suggestion:\s*(.+)' -and $currentFile) {
                        $suggestions[$currentFile] += $matches[1].Trim()
                    } elseif ($line.Trim().Length -gt 0 -and $currentFile -and $line -notmatch '^file:') {
                        # Continuation of previous suggestion
                        if ($suggestions[$currentFile].Count -gt 0) {
                            $lastIdx = $suggestions[$currentFile].Count - 1
                            $suggestions[$currentFile][$lastIdx] += " " + $line.Trim()
                        }
                    }
                }
            }
            "text" {
                # Simple format: one suggestion per line, or file-based
                $lines = $content -split "`n" | Where-Object { $_.Trim().Length -gt 0 }
                
                # Check if it's file-based (contains paths)
                $hasFilePaths = $content -match '[a-zA-Z]:\\.*\.(cpp|h|hpp)'
                
                if ($hasFilePaths) {
                    # File-based format: file path followed by suggestions
                    $currentFile = $null
                    foreach ($line in $lines) {
                        if ($line -match '([a-zA-Z]:\\.*\.(?:cpp|h|hpp))') {
                            $currentFile = $matches[1]
                            if (-not $suggestions.ContainsKey($currentFile)) {
                                $suggestions[$currentFile] = @()
                            }
                        } elseif ($line -match '^\s*[-*•]\s*(.+)' -or $line -match '^\d+\.\s*(.+)') {
                            # Bullet point or numbered suggestion
                            $suggestion = $matches[1].Trim()
                            if ($currentFile) {
                                $suggestions[$currentFile] += $suggestion
                            } else {
                                # No file specified, add to "general" key
                                if (-not $suggestions.ContainsKey("general")) {
                                    $suggestions["general"] = @()
                                }
                                $suggestions["general"] += $suggestion
                            }
                        } elseif ($line.Trim().Length -gt 0) {
                            # Plain text suggestion
                            if ($currentFile) {
                                $suggestions[$currentFile] += $line.Trim()
                            } else {
                                if (-not $suggestions.ContainsKey("general")) {
                                    $suggestions["general"] = @()
                                }
                                $suggestions["general"] += $line.Trim()
                            }
                        }
                    }
                } else {
                    # Simple list format - apply to all files
                    foreach ($line in $lines) {
                        $suggestion = $line.Trim()
                        if ($suggestion.Length -gt 0) {
                            if (-not $suggestions.ContainsKey("general")) {
                                $suggestions["general"] = @()
                            }
                            $suggestions["general"] += $suggestion
                        }
                    }
                }
            }
        }
        
        $totalSuggestions = ($suggestions.Values | Measure-Object -Sum).Sum
        Write-Status "Loaded $totalSuggestions suggestion(s) from $($suggestions.Keys.Count) file(s)" "Success"
        
        return $suggestions
    } catch {
        Write-Status "Error loading suggestions file: $_" "Error"
        return @{}
    }
}

# Main Script
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AI Fix Application Tool (Fast Mode)" -ForegroundColor Cyan
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

# Check AI availability
if (-not (Test-OllamaAvailable)) {
    Write-Status "Ollama not available - cannot proceed" "Error"
    exit 1
}

Write-Status "Using fast AI model: $($Script:Config.OllamaModel)" "Info"
Write-Status "AI delay: $($Script:Config.AIDelay)s between calls" "Info"
Write-Status "CPU optimization: Using $($Script:Config.NumThreads) threads (of $($Script:Config.CpuCores) available cores)" "Info"
Write-Status "Parallel processing: $($Script:Config.ParallelJobs) files at a time" "Info"

# Verify AI is actually working with a test call
Write-Status "Verifying AI is working (test call)..." "Info"
try {
    $testBody = @{
        model = $Script:Config.OllamaModel
        messages = @(
            @{ role = "user"; content = "Say 'OK' if you can process this test." }
        )
        stream = $false
        options = @{
            num_predict = 10
            num_thread = $Script:Config.NumThreads  # Maximum CPU thread usage
        }
    } | ConvertTo-Json -Depth 10
    
    Write-Status "  Making test AI call (should use CPU for 1-2 seconds)..." "Info"
    $testStart = Get-Date
    $testResponse = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    $testElapsed = ((Get-Date) - $testStart).TotalSeconds
    
    if ($testResponse.message.content) {
        Write-Status "  [SUCCESS] AI test successful (took $([Math]::Round($testElapsed, 1))s) - AI is working!" "Success"
        Write-Status "  [INFO] You should see CPU usage when AI processes files" "Info"
    } else {
        Write-Status "  [WARNING] AI test returned no content" "Warning"
    }
} catch {
    Write-Status "  [ERROR] AI test FAILED: $($_.Exception.Message)" "Error"
    Write-Status "  [WARNING] AI may not be working - fixes may fail" "Warning"
    $continue = Read-Host "  Continue anyway? (y/n)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}

if ($Script:Config.DryRun) {
    Write-Status "DRY RUN MODE - No files will be modified" "Warning"
}

Write-Host ""

# Get C++ files
$cppFiles = Get-ChildItem -Path $Script:Config.Path -Recurse -Include "*.cpp", "*.h", "*.hpp" -File -ErrorAction SilentlyContinue

if ($cppFiles.Count -eq 0) {
    Write-Status "No C++ files found" "Warning"
    exit 0
}

Write-Status "Found $($cppFiles.Count) C++ file(s) to process" "Info"

# Load suggestions from file if provided
if ($Script:Config.SuggestionsFile) {
    $Script:Config.LoadedSuggestions = Load-SuggestionsFromFile -FilePath $Script:Config.SuggestionsFile -Format $Script:Config.SuggestionsFormat
    if ($Script:Config.LoadedSuggestions.Count -eq 0) {
        Write-Status "No suggestions loaded from file" "Warning"
        exit 0
    }
}

Write-Host ""

# Thread-safe counters for parallel processing
$syncCounters = [hashtable]::Synchronized(@{
    FilesProcessed = 0
    FilesModified = 0
    SuggestionsApplied = 0
})

# Function to process a single file (used in parallel)
function Process-SingleFile {
    param(
        [System.IO.FileInfo]$File,
        [hashtable]$Config,
        [hashtable]$SyncCounters,
        [hashtable]$LoadedSuggestions
    )
    
    $result = @{
        Processed = $true
        Modified = $false
        SuggestionsApplied = 0
        Error = $null
    }
    
    try {
        $content = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content -or $content.Length -gt 20000) {
            return $result
        }
        
        # Get suggestions (from file or AI)
        $suggestions = @()
        
        if ($Config.SuggestionsFile -and $LoadedSuggestions.Count -gt 0) {
            # Use suggestions from file
            $fileKey = $file.FullName
            $relativePath = $file.FullName.Replace($Config.Path, "").TrimStart('\', '/')
            
            # Try multiple key formats
            if ($LoadedSuggestions.ContainsKey($fileKey)) {
                $suggestions = $LoadedSuggestions[$fileKey]
            } elseif ($LoadedSuggestions.ContainsKey($relativePath)) {
                $suggestions = $LoadedSuggestions[$relativePath]
            } elseif ($LoadedSuggestions.ContainsKey($file.Name)) {
                $suggestions = $LoadedSuggestions[$file.Name]
            } elseif ($LoadedSuggestions.ContainsKey("general")) {
                # Apply general suggestions to all files
                $suggestions = $LoadedSuggestions["general"]
            }
        } else {
            # Get AI suggestions
            $suggestions = Invoke-AICodeReview -FilePath $file.FullName -ApiVersion "unknown" -CurrentContent $content
        }
        
        if ($suggestions.Count -gt 0) {
            # Apply each suggestion
            foreach ($suggestion in $suggestions) {
                # Generate and apply the code change using AI
                $aiCodeChange = Invoke-AIGenerateCodeChange -FilePath $file.FullName -Suggestion $suggestion -CurrentContent $content -ApiVersion "unknown"
                
                if ($aiCodeChange) {
                    $applyResult = Apply-AICodeChange -FilePath $file.FullName -AICodeChange $aiCodeChange -CurrentContent $content
                    
                    if ($applyResult.Success) {
                        if (-not $Config.DryRun) {
                            # Create backup
                            $backupPath = "$($file.FullName).backup"
                            if (-not (Test-Path $backupPath)) {
                                Copy-Item -Path $file.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
                            }
                            
                            # Write modified content
                            [System.IO.File]::WriteAllText($file.FullName, $applyResult.Content, [System.Text.Encoding]::UTF8)
                            $content = $applyResult.Content  # Update for next iteration
                            
                            $result.Modified = $true
                            $result.SuggestionsApplied++
                        }
                    }
                }
            }
        }
    } catch {
        $result.Error = $_.Exception.Message
    }
    
    return $result
}

# Process files in parallel
Write-Status "Starting parallel processing of $($cppFiles.Count) files with $($Script:Config.ParallelJobs) concurrent jobs..." "Info"
$startTime = Get-Date

$results = $cppFiles | ForEach-Object -Parallel {
    # Import functions and config into parallel context
    $file = $_
    $config = $using:Script:Config
    $syncCounters = $using:syncCounters
    $loadedSuggestions = $using:Script:Config.LoadedSuggestions
    
    # Import required functions (they need to be available in parallel context)
    function Invoke-AICodeReview { param($FilePath, $ApiVersion, $CurrentContent) 
        # Simplified - actual implementation should be here or imported
        return @()
    }
    function Invoke-AIGenerateCodeChange { param($FilePath, $Suggestion, $CurrentContent, $ApiVersion)
        # Simplified - actual implementation should be here or imported
        return $null
    }
    function Apply-AICodeChange { param($FilePath, $AICodeChange, $CurrentContent)
        # Simplified - actual implementation should be here or imported
        return @{ Success = $false }
    }
    
    # Process the file
    $result = Process-SingleFile -File $file -Config $config -SyncCounters $syncCounters -LoadedSuggestions $loadedSuggestions
    
    # Update counters thread-safely
    $syncCounters.FilesProcessed++
    
    if ($result.Modified) {
        $syncCounters.FilesModified++
        $syncCounters.SuggestionsApplied += $result.SuggestionsApplied
    }
    
    # Return result with file info for status
    return @{
        File = $file.Name
        Result = $result
    }
} -ThrottleLimit $Script:Config.ParallelJobs

$elapsed = ((Get-Date) - $startTime).TotalSeconds
Write-Status "Parallel processing completed in $([Math]::Round($elapsed, 1)) seconds" "Success"

# Update config with final counts
$Script:Config.FilesProcessed = $syncCounters.FilesProcessed
$Script:Config.FilesModified = $syncCounters.FilesModified
$Script:Config.SuggestionsApplied = $syncCounters.SuggestionsApplied

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Status "Files processed: $($Script:Config.FilesProcessed)" "Info"
Write-Status "Files modified: $($Script:Config.FilesModified)" $(if ($Script:Config.FilesModified -gt 0) { "Success" } else { "Info" })
Write-Status "Suggestions applied: $($Script:Config.SuggestionsApplied)" $(if ($Script:Config.SuggestionsApplied -gt 0) { "Success" } else { "Info" })

if ($Script:Config.DryRun) {
    Write-Host ""
    Write-Status "This was a dry run. No files were modified." "Warning"
}

Write-Host ""

