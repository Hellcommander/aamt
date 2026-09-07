<#
.SYNOPSIS
    Applies manual review fixes using the smartest AI model

.DESCRIPTION
    This tool uses the best AI model (default: codellama:34b) to apply fixes
    that require manual review. It reads from manual_review.txt and applies
    complex fixes that need more intelligence.

.PARAMETER Path

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    Path to the API folder or file to process

.PARAMETER ManualReviewFile
    Path to manual review file (default: manual_review.txt)

.PARAMETER OllamaModel
    Ollama model to use (default: codellama:34b for best quality)

.PARAMETER OllamaUrl
    Ollama API URL (default: http://localhost:11434)

.PARAMETER DryRun
    Show what would be fixed without making changes

.PARAMETER ShowDetails
    Verbose output

.EXAMPLE
    .\Apply-ManualReviewFixes.ps1 "D:\path\to\API59"

.EXAMPLE
    .\Apply-ManualReviewFixes.ps1 "D:\path\to\API59" -ManualReviewFile "my_review.txt"
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Path = ".",
    
    [Parameter(Mandatory=$false)]
    [string]$ManualReviewFile = "manual_review.txt",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:34b",  # Best model for complex fixes
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowDetails = $false
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

# Configuration
$Script:Config = @{
    Path = $Path
    DryRun = $DryRun
    Verbose = $ShowDetails
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    ManualReviewFile = $ManualReviewFile
    FilesProcessed = 0
    FilesModified = 0
    FixesApplied = 0
    LastAICallTime = $null
    AIDelay = 3  # Longer delay for quality model
    NumThreads = $optimalThreads  # Optimal CPU thread count
    CpuCores = $cpuCores
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
        
        # Try to find a similar high-quality model
        $bestModel = $models | Where-Object { $_ -like "*codellama*34b*" -or $_ -like "*codellama:34b*" } | Select-Object -First 1
        if (-not $bestModel) {
            $bestModel = $models | Where-Object { $_ -like "*codellama*" } | Select-Object -First 1
        }
        if ($bestModel) {
            $Script:Config.OllamaModel = $bestModel
            Write-Status "Using available model: $bestModel" "Info"
            return $true
        }
        
        Write-Status "Model $($Script:Config.OllamaModel) not found. Available: $($models -join ', ')" "Warning"
        return $false
    } catch {
        Write-Status "Ollama not available: $_" "Warning"
        return $false
    }
}

function Load-ManualReviewItems {
    param(
        [string]$FilePath
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Status "Manual review file not found: $FilePath" "Error"
        return @()
    }
    
    $items = @()
    $content = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    
    if (-not $content) {
        Write-Status "Manual review file is empty" "Warning"
        return @()
    }
    
    Write-Status "Loading manual review items from file..." "Info"
    
    # Parse different formats
    $lines = $content -split "`n"
    $currentItem = $null
    
    foreach ($line in $lines) {
        $line = $line.Trim()
        
        # Skip comments and empty lines
        if ($line.Length -eq 0 -or $line.StartsWith("#")) {
            continue
        }
        
        # File specification
        if ($line -match '^file:\s*(.+)' -or $line -match '^FILE:\s*(.+)') {
            if ($currentItem) {
                $items += $currentItem
            }
            $currentItem = @{
                File = $matches[1].Trim()
                Issue = ""
                Context = @()
                Code = ""
            }
        }
        # Issue/description
        elseif ($line -match '^issue:\s*(.+)' -or $line -match '^ISSUE:\s*(.+)' -or $line -match '^problem:\s*(.+)') {
            if ($currentItem) {
                $currentItem.Issue = $matches[1].Trim()
            }
        }
        # Code block start
        elseif ($line -match '^```' -or $line -match '^CODE:' -or $line -match '^code:') {
            if ($currentItem) {
                $currentItem.InCodeBlock = $true
                $currentItem.Code = ""
            }
        }
        # Code block end
        elseif ($line -match '^```' -and $currentItem -and $currentItem.InCodeBlock) {
            $currentItem.InCodeBlock = $false
        }
        # Context line
        elseif ($line -match '^context:\s*(.+)' -or $line -match '^CONTEXT:\s*(.+)') {
            if ($currentItem) {
                $currentItem.Context += $matches[1].Trim()
            }
        }
        # Regular content
        else {
            if ($currentItem) {
                if ($currentItem.InCodeBlock) {
                    $currentItem.Code += $line + "`n"
                } elseif ($currentItem.Issue.Length -eq 0) {
                    $currentItem.Issue = $line
                } else {
                    $currentItem.Context += $line
                }
            } else {
                # No file specified, create general item
                $currentItem = @{
                    File = "general"
                    Issue = $line
                    Context = @()
                    Code = ""
                    InCodeBlock = $false
                }
            }
        }
    }
    
    # Add last item
    if ($currentItem) {
        $items += $currentItem
    }
    
    Write-Status "Loaded $($items.Count) manual review item(s)" "Success"
    return $items
}

function Invoke-AIApplyManualReview {
    param(
        [hashtable]$ReviewItem,
        [string]$FilePath,
        [string]$CurrentContent
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
        $maxCodeLength = 8000  # Larger context for complex fixes
        $codeSnippet = if ($CurrentContent.Length -gt $maxCodeLength) {
            # Try to include context around the issue if possible
            if ($ReviewItem.Code.Length -gt 0) {
                $codeIndex = $CurrentContent.IndexOf($ReviewItem.Code.Substring(0, [Math]::Min(100, $ReviewItem.Code.Length)))
                if ($codeIndex -ge 0) {
                    $start = [Math]::Max(0, $codeIndex - 2000)
                    $end = [Math]::Min($CurrentContent.Length, $codeIndex + $ReviewItem.Code.Length + 2000)
                    $CurrentContent.Substring($start, $end - $start) + "`n// ... (truncated) ..."
                } else {
                    $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
                }
            } else {
                $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
            }
        } else {
            $CurrentContent
        }
        
        $contextText = if ($ReviewItem.Context.Count -gt 0) {
            $ReviewItem.Context -join "`n"
        } else {
            "No additional context provided"
        }
        
        $systemPrompt = @"
You are an expert C++ code fixer specializing in complex C++20 migration issues.
You are applying fixes that require manual review - these are more complex than simple pattern replacements.

CRITICAL CONSTRAINTS:
- NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
- Preserve code functionality and behavior
- Maintain code style and formatting
- Ensure the fix is correct and complete

You must provide the COMPLETE, CORRECT fix that can be directly applied.
"@
        
        $userPrompt = @"
FILE: $fileName

ISSUE REQUIRING MANUAL REVIEW:
$($ReviewItem.Issue)

ADDITIONAL CONTEXT:
$contextText

CURRENT CODE:
```cpp
$codeSnippet
```

PROBLEMATIC CODE (if specified):
```cpp
$($ReviewItem.Code.Trim())
```

TASK:
Apply the fix for this issue. Provide the COMPLETE MODIFIED CODE that resolves the problem.
The fix must be:
1. Correct and complete
2. Compatible with C++20
3. Using only existing libraries
4. Preserving functionality

Return the fix in this format:
OLD CODE:
[exact code to replace]

NEW CODE:
[complete replacement code]

If the fix affects multiple sections, provide all of them.
"@
        
        $requestBody = @{
            model = $Script:Config.OllamaModel
            messages = @(
                @{ role = "system"; content = $systemPrompt }
                @{ role = "user"; content = $userPrompt }
            )
            stream = $false
            options = @{
                num_ctx = 16000  # Large context for complex fixes
                temperature = 0.1  # Low for deterministic fixes
                num_predict = 2000  # Allow longer responses for complex fixes
                num_thread = $Script:Config.NumThreads  # Maximum CPU thread usage
                numa = $false  # Disable NUMA for better CPU utilization
                use_mmap = $true  # Memory-mapped files for faster loading
                use_mlock = $false  # Don't lock memory (allows swapping if needed)
                numa_strategy = "disabled"  # Disable NUMA for better CPU usage
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "  Requesting fix from AI (model: $($Script:Config.OllamaModel), this may take 30-60 seconds)..." "Info"
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 180
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        Write-Status "  AI response received (took $([Math]::Round($elapsed, 1))s)" "Info"
        
        $aiResponse = $response.message.content.Trim()
        if ($Script:Config.Verbose -and $aiResponse.Length -gt 0) {
            $preview = if ($aiResponse.Length -gt 300) { $aiResponse.Substring(0, 300) + "..." } else { $aiResponse }
            Write-Status "  AI response preview: $preview" "Info"
        }
        
        return $aiResponse
    }
    catch {
        Write-Status "AI fix generation failed: $_" "Warning"
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
            # For manual review items, we want to be more careful
            # Try to find the location based on context
            Write-Status "  Extracted code block, attempting context-based replacement..." "Info"
            # Append with clear marker for review
            $modifiedContent = $CurrentContent + "`n`n// ===== AI APPLIED FIX (MANUAL REVIEW) =====`n" + $extractedCode + "`n// ===== END AI FIX =====`n"
            return @{ Success = $true; Content = $modifiedContent; Method = "append_review" }
        }
        
        Write-Status "  Could not automatically apply change - manual review needed" "Warning"
        if ($Script:Config.Verbose) {
            Write-Host "  AI Response (first 500 chars):" -ForegroundColor Yellow
            $preview = if ($AICodeChange.Length -gt 500) { $AICodeChange.Substring(0, 500) + "..." } else { $AICodeChange }
            Write-Host "  $preview" -ForegroundColor Gray
        }
        return @{ Success = $false; Content = $CurrentContent; Method = "manual" }
    }
    catch {
        Write-Status "  Error applying AI change: $_" "Warning"
        return @{ Success = $false; Content = $CurrentContent; Method = "error" }
    }
}

# Main Script
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Manual Review Fix Application Tool (Best AI)" -ForegroundColor Cyan
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

Write-Status "Using best AI model: $($Script:Config.OllamaModel)" "Info"
Write-Status "AI delay: $($Script:Config.AIDelay)s between calls" "Info"
Write-Status "CPU optimization: Using $($Script:Config.NumThreads) threads (of $($Script:Config.CpuCores) available cores)" "Info"

# Load manual review items
$reviewItems = Load-ManualReviewItems -FilePath $Script:Config.ManualReviewFile

if ($reviewItems.Count -eq 0) {
    Write-Status "No manual review items found" "Warning"
    exit 0
}

if ($Script:Config.DryRun) {
    Write-Status "DRY RUN MODE - No files will be modified" "Warning"
}

Write-Host ""

# Process each review item
foreach ($item in $reviewItems) {
    $Script:Config.FilesProcessed++
    
    # Resolve file path
    $filePath = $item.File
    if ($filePath -eq "general" -or -not (Test-Path $filePath)) {
        # Try to find the file
        if (-not [System.IO.Path]::IsPathRooted($filePath)) {
            $filePath = Join-Path $Script:Config.Path $filePath
        }
        
        # Try to find by filename
        if (-not (Test-Path $filePath)) {
            $fileName = Split-Path -Leaf $item.File
            $foundFile = Get-ChildItem -Path $Script:Config.Path -Recurse -Filter $fileName -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($foundFile) {
                $filePath = $foundFile.FullName
            }
        }
    }
    
    if (-not (Test-Path $filePath)) {
        Write-Status "File not found: $($item.File)" "Warning"
        continue
    }
    
    Write-Status "Processing: $filePath ($($Script:Config.FilesProcessed)/$($reviewItems.Count))" "Info"
    Write-Status "  Issue: $($item.Issue)" "Info"
    
    try {
        $content = Get-Content -Path $filePath -Raw -ErrorAction SilentlyContinue
        if (-not $content) {
            Write-Status "  Could not read file" "Warning"
            continue
        }
        
        # Get AI fix
        Write-Status "  Requesting fix from AI..." "Info"
        $aiFix = Invoke-AIApplyManualReview -ReviewItem $item -FilePath $filePath -CurrentContent $content
        
        if ($aiFix) {
            Write-Status "  Applying fix..." "Info"
            $applyResult = Apply-AICodeChange -FilePath $filePath -AICodeChange $aiFix -CurrentContent $content
            
            if ($applyResult.Success) {
                if (-not $Script:Config.DryRun) {
                    # Create backup
                    $backupPath = "$filePath.backup"
                    if (-not (Test-Path $backupPath)) {
                        Copy-Item -Path $filePath -Destination $backupPath -Force -ErrorAction SilentlyContinue
                    }
                    
                    # Write modified content
                    [System.IO.File]::WriteAllText($filePath, $applyResult.Content, [System.Text.Encoding]::UTF8)
                    
                    Write-Status "  Fix applied ($($applyResult.Method))" "Success"
                    $Script:Config.FilesModified++
                    $Script:Config.FixesApplied++
                } else {
                    Write-Status "  Fix ready (DryRun - not applied)" "Info"
                }
            } else {
                Write-Status "  Could not automatically apply fix" "Warning"
            }
        } else {
            Write-Status "  Could not generate fix" "Warning"
        }
    } catch {
        Write-Status "  Error processing: $_" "Warning"
    }
    
    Write-Host ""
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Status "Items processed: $($Script:Config.FilesProcessed)" "Info"
Write-Status "Files modified: $($Script:Config.FilesModified)" $(if ($Script:Config.FilesModified -gt 0) { "Success" } else { "Info" })
Write-Status "Fixes applied: $($Script:Config.FixesApplied)" $(if ($Script:Config.FixesApplied -gt 0) { "Success" } else { "Info" })

if ($Script:Config.DryRun) {
    Write-Host ""
    Write-Status "This was a dry run. No files were modified." "Warning"
}

Write-Host ""

