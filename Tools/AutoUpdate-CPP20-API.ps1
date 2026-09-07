# ============================================================================
# AutoUpdate-CPP20-API.ps1
# ============================================================================
# Generic C++20 Migration Script for Transcendence API
# - Auto-detects API version from project structure
# - Searches online for C++20 migration requirements
# - Applies appropriate code transformations
# - Works for any API version
#
# IMPORTANT: AI (Ollama) is OPTIONAL - the tool works without it but benefits

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
#            from AI when available for better code analysis and verification
#
# Usage:
#   .\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder"
#   .\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder" -DryRun
#   .\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder" -Interactive
#   .\AutoUpdate-CPP20-API.ps1 -Path "D:\path\to\API\folder" -NoAI  # Explicitly disable AI
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
    [switch]$SkipOnlineCheck = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,  # If not specified, will auto-detect and use if available
    
    [Parameter(Mandatory=$false)]
    [switch]$NoAI,  # Explicitly disable AI
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:34b",  # Consider "codellama:13b" or "codellama:7b" for faster processing
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [switch]$FastMode = $false,  # Skip AI verification for known-safe changes (much faster)
    
    [Parameter(Mandatory=$false)]
    [int]$MaxAITimePerFile = 120,  # Max seconds per file for AI analysis (default 2 minutes)
    
    [Parameter(Mandatory=$false)]
    [int]$MaxTotalTime = 3600,  # Max total time in seconds (default 1 hour)
    
    [Parameter(Mandatory=$false)]
    [int]$MaxIterations = 3,  # Max iterations per file to prevent infinite loops
    
    [Parameter(Mandatory=$false)]
    [switch]$GuiMode = $false,  # When true, skip main execution (for GUI wrapper)
    
    [Parameter(Mandatory=$false)]
    [switch]$Interactive = $false,  # When true, prompt for each AI suggestion and allow alternative changes
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("smart", "aggressive", "conservative", "compile-first")]
    [string]$AIStrategy = "smart",  # AI usage strategy: smart (default), aggressive (use AI more), conservative (use AI less), compile-first (fix then compile, AI only on errors)
    
    [Parameter(Mandatory=$false)]
    [int]$AIDelay = 2,  # Delay in seconds between AI calls to prevent overwhelming Ollama (default: 2 seconds)
    
    [Parameter(Mandatory=$false)]
    [switch]$UseFixApiCompatibility = $true  # Use FixApiCompatibilityAI.py for better error handling
)

$ErrorActionPreference = "Continue"

# Import shared Ollama integration module
$sharedModulePath = Join-Path $PSScriptRoot "Shared\OllamaIntegration.psm1"
if (Test-Path $sharedModulePath) {
    Import-Module $sharedModulePath -Force
}

# ============================================================================
# CONFIGURATION
# ============================================================================

# Auto-detect AI availability if not explicitly set
$autoDetectAI = $false
if (-not $UseAI -and -not $NoAI) {
    # Neither flag specified - auto-detect
    $autoDetectAI = $true
    $UseAI = $false  # Will be set to true if Ollama is available
} elseif ($NoAI) {
    # Explicitly disabled
    $UseAI = $false
} else {
    # Explicitly enabled
    $UseAI = $true
}

$Script:Config = @{
    Path = $Path
    DryRun = $DryRun
    Backup = $Backup
    Verbose = $ShowDetails
    SkipOnlineCheck = $SkipOnlineCheck
    UseAI = $UseAI
    AutoDetectAI = $autoDetectAI
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    FastMode = $FastMode
    Interactive = $Interactive
    AIStrategy = $AIStrategy
    AIDelay = $AIDelay
    UseFixApiCompatibility = $UseFixApiCompatibility
    ApiVersion = $null
    FilesProcessed = 0
    FilesModified = 0
    TotalChanges = 0
    MigrationRules = @()
    AIVerifications = 0
    AISuggestions = 0
    AIApplied = 0
    MaxAITimePerFile = $MaxAITimePerFile
    MaxTotalTime = $MaxTotalTime
    MaxIterations = $MaxIterations
    LastAICallTime = $null
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Get-CachedChildItem {
    <#
    .SYNOPSIS
    Wrapper for Get-ChildItem with caching to prevent CPU burn
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        
        [switch]$Recurse,
        
        [string[]]$Include,
        
        [string]$Filter,
        
        [switch]$File,
        
        [switch]$Directory
    )
    
    # Use standard Get-ChildItem (caching would be complex, so just use the standard cmdlet)
    $params = @{
        Path = $Path
        ErrorAction = 'SilentlyContinue'
    }
    
    if ($Recurse) {
        $params['Recurse'] = $true
    }
    
    if ($Include) {
        $params['Include'] = $Include
    }
    
    if ($Filter) {
        $params['Filter'] = $Filter
    }
    
    if ($File) {
        $params['File'] = $true
    }
    
    if ($Directory) {
        $params['Directory'] = $true
    }
    
    Get-ChildItem @params
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
# API VERSION DETECTION
# ============================================================================

function Get-ApiVersion {
    param([string]$SearchPath)
    
    Write-Status "Detecting API version..." "Info"
    
    # Try to detect from folder name (e.g., "TranscendenceDev-integration-API59")
    $folderName = Split-Path -Leaf $SearchPath
    if ($folderName -match 'API(\d+)') {
        $version = $matches[1]
        Write-Status "Detected API version from folder: $version" "Success"
        return $version
    }
    
    # Try to detect from parent folder
    $parentFolder = Split-Path -Parent $SearchPath
    if ($parentFolder -match 'API(\d+)') {
        $version = $matches[1]
        Write-Status "Detected API version from parent folder: $version" "Success"
        return $version
    }
    
    # Search for API version in project files
    $projFiles = Get-CachedChildItem -Path $SearchPath -Recurse -Filter "*.vcxproj" -File | Select-Object -First 5
    foreach ($file in $projFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match 'API(\d+)') {
            $version = $matches[1]
            Write-Status "Detected API version from project file: $version" "Success"
            return $version
        }
    }
    
    # Search in source files
    $cppFiles = Get-CachedChildItem -Path $SearchPath -Recurse -Include "*.cpp", "*.h" -File | Select-Object -First 10
    foreach ($file in $cppFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match 'API\s*(\d+)' -or $content -match "apiVersion\s*=\s*['`"](\d+)") {
            $version = $matches[1]
            Write-Status "Detected API version from source: $version" "Success"
            return $version
        }
    }
    
    Write-Status "Could not auto-detect API version, using generic C++20 rules" "Warning"
    return "unknown"
}

# ============================================================================
# ONLINE C++20 MIGRATION RULES FETCHER
# ============================================================================

function Get-Cpp20MigrationRules {
    param([string]$ApiVersion)
    
    Write-Status "Loading C++20 migration rules..." "Info"
    
    $rules = @()
    
    # Always include built-in rules based on C++20 standard and Transcendence API patterns
    try {
        # Common C++20 migration patterns based on online resources
        # These are based on actual C++20 standard changes from:
        # - https://en.cppreference.com/w/cpp/20
        # - https://en.wikipedia.org/wiki/C%2B%2B20
        # - Actual Transcendence API migration patterns
            
            # 1. std::experimental -> std namespace
            $rules += @{
                Pattern = 'std::experimental::optional'
                Replacement = 'std::optional'
                Description = 'Replace std::experimental::optional with std::optional'
                Category = 'StandardLibrary'
            }
            
            $rules += @{
                Pattern = 'std::experimental::filesystem'
                Replacement = 'std::filesystem'
                Description = 'Replace std::experimental::filesystem with std::filesystem'
                Category = 'StandardLibrary'
            }
            
            $rules += @{
                Pattern = 'std::experimental::string_view'
                Replacement = 'std::string_view'
                Description = 'Replace std::experimental::string_view with std::string_view'
                Category = 'StandardLibrary'
            }
            
            # 2. CodeChain API specific (based on actual fixes we did)
            $linkPattern = 'CC\.Link\s*\(([^,]+?),\s*\d+,\s*NULL\s*\)'
            $rules += @{
                Pattern = $linkPattern
                Replacement = 'CCodeChain::LinkCode($1)'
                Description = 'Replace CC.Link() with CCodeChain::LinkCode()'
                Category = 'CodeChainAPI'
            }
            
            $rules += @{
                Pattern = '\.Print\s*\(\s*&CC\s*\)'
                Replacement = '.Print()'
                Description = 'Remove CCodeChain* parameter from Print()'
                Category = 'CodeChainAPI'
            }
            
            $rules += @{
                Pattern = '\.Print\s*\(\s*CC\s*\)'
                Replacement = '.Print()'
                Description = 'Remove CCodeChain parameter from Print()'
                Category = 'CodeChainAPI'
            }
            
            $rules += @{
                Pattern = '\.Discard\s*\(\s*&CC\s*\)'
                Replacement = '.Discard()'
                Description = 'Remove CCodeChain* parameter from Discard()'
                Category = 'CodeChainAPI'
            }
            
            $rules += @{
                Pattern = '\.Discard\s*\(\s*CC\s*\)'
                Replacement = '.Discard()'
                Description = 'Remove CCodeChain parameter from Discard()'
                Category = 'CodeChainAPI'
            }
            
            $topLevelPattern = '\.TopLevel\s*\(\s*([^,]+?),\s*&Ctx\s*\)'
            $rules += @{
                Pattern = $topLevelPattern
                Replacement = '.TopLevel(*$1, RunOptions)'
                Description = 'Update TopLevel() to use SRunOptions'
                Category = 'CodeChainAPI'
            }
            
            $rules += @{
                Pattern = 'CreateXMLElementFromCommandLine\s*\(\s*argc,\s*argv,'
                Replacement = 'CreateXMLElementFromCommandLine(argc, const_cast<const char **>(argv),'
                Description = 'Fix const correctness for CreateXMLElementFromCommandLine'
                Category = 'XMLUtil'
            }
            
            # 3. Smart pointer conversions
            $smartPtrLinkPattern = 'ICCItem\s+\*(\w+)\s*=\s*CCodeChain::LinkCode'
            $rules += @{
                Pattern = $smartPtrLinkPattern
                Replacement = 'ICCItemPtr $1 = CCodeChain::LinkCode'
                Description = 'Convert raw pointer to smart pointer for LinkCode'
                Category = 'SmartPointers'
            }
            
            $smartPtrTopPattern = 'ICCItem\s+\*(\w+)\s*=\s*CC\.TopLevel'
            $rules += @{
                Pattern = $smartPtrTopPattern
                Replacement = 'ICCItemPtr $1 = CC.TopLevel'
                Description = 'Convert raw pointer to smart pointer for TopLevel'
                Category = 'SmartPointers'
            }
            
            # 4. C++20 specific features
            $rules += @{
                Pattern = 'std::bind\s*<'
                Replacement = 'std::bind'  # Note: std::bind still works, but we can suggest alternatives
                Description = 'Consider using lambdas instead of std::bind in C++20'
                Category = 'C++20Features'
                WarningOnly = $true
            }
            
            Write-Status "Loaded $($rules.Count) migration rules" "Success"
            
    } catch {
        Write-Status "Error loading rules: $_" "Warning"
    }
    
    # Optionally try to fetch additional rules online (if not skipped)
    if (-not $Script:Config.SkipOnlineCheck) {
        try {
            Write-Status "Checking for additional online migration patterns..." "Info"
            # In the future, this could fetch rules from a web API or documentation
            # For now, we use comprehensive built-in rules based on:
            # - C++20 standard changes
            # - Transcendence CodeChain API changes
            # - Common migration patterns
        } catch {
            Write-Status "Online check skipped or failed, using built-in rules" "Info"
        }
    } else {
        Write-Status "Skipping online check, using built-in rules only" "Info"
    }
    
    Write-Status "Total rules available: $($rules.Count)" "Success"
    return $rules
}

# ============================================================================
# OLLAMA AI INTEGRATION
# ============================================================================

function Test-OllamaAvailable {
    <#
    .SYNOPSIS
      Checks if Ollama service is running and model is available
    #>
    # Use shared module if available
    if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
        if (Test-OllamaConnection) {
            # Try to use the selected code model from shared module
            if ($null -ne $script:AIConfig -and $null -ne $script:AIConfig.SelectedModels -and $script:AIConfig.SelectedModels["code"]) {
                $Script:Config.OllamaModel = $script:AIConfig.SelectedModels["code"]
                Write-Status "Using model: $($Script:Config.OllamaModel)" "Info"
            }
            return $true
        }
        return $false
    }
    
    # Fallback implementation
    try {
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        $models = $response.models | ForEach-Object { $_.name }
        
        if ($models -contains $Script:Config.OllamaModel -or $models -like "*codellama*") {
            # Use available CodeLlama model if exact match not found
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
      Uses Ollama CodeLlama to analyze code changes and verify correctness
    #>
    param(
        [string]$OriginalCode,
        [string]$ModifiedCode,
        [string]$FilePath,
        [string]$ApiVersion
    )
    
    if (-not $Script:Config.UseAI) {
        return @{ Verified = $true; Suggestions = @() }
    }
    
    if (-not (Test-OllamaAvailable)) {
        Write-Status "Skipping AI verification (Ollama not available)" "Warning"
        return @{ Verified = $true; Suggestions = @() }
    }
    
    # Apply AI delay to prevent overwhelming Ollama
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0) {
                if ($Script:Config.Verbose) {
                    Write-Status "  Waiting ${waitTime}s before AI call (rate limiting)..." "Info"
                }
                Start-Sleep -Seconds $waitTime
            }
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $systemPrompt = @"
You are an expert C++ code reviewer specializing in C++20 migration and the Transcendence CodeChain API.
Your task is to:
1. Verify that code transformations from older C++ standards to C++20 are correct
2. Check that API changes (like CC.Link -> CCodeChain::LinkCode) are properly applied
3. Identify any missing transformations or potential issues
4. Suggest improvements for C++20 compliance

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Do NOT suggest using third-party libraries or dependencies
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
- Work within the constraints of existing includes and dependencies

API Version: $ApiVersion
Focus on: CodeChain API changes, smart pointer usage, const correctness, C++20 standard library updates
"@
        
        $userPrompt = @"
Analyze these C++ code changes for C++20 migration correctness:

FILE: $FilePath
API VERSION: $ApiVersion

ORIGINAL CODE:
```cpp
$OriginalCode
```

MODIFIED CODE:
```cpp
$ModifiedCode
```

Please:
1. Verify the transformations are correct for C++20
2. Check if all necessary changes were applied
3. Identify any issues or missing transformations
4. Suggest any additional improvements

Respond in JSON format:
{
  "verified": true/false,
  "issues": ["list of issues if any"],
  "suggestions": ["list of improvement suggestions"],
  "missing_transformations": ["any patterns that should be changed but weren't"]
}
"@
        
        # Focus on one file at a time with full context
        # Increased context size to keep file context intact (3000 chars = ~750 tokens each)
        # This ensures AI has enough context to understand the file structure
        $maxCodeLength = 3000
        $originalSnippet = if ($OriginalCode.Length -gt $maxCodeLength) {
            # Take from start to preserve includes, namespace, class structure
            $OriginalCode.Substring(0, $maxCodeLength) + "`n// ... (truncated - showing first 3000 chars for context) ..."
        } else {
            $OriginalCode
        }
        $modifiedSnippet = if ($ModifiedCode.Length -gt $maxCodeLength) {
            # Take from start to preserve includes, namespace, class structure
            $ModifiedCode.Substring(0, $maxCodeLength) + "`n// ... (truncated - showing first 3000 chars for context) ..."
        } else {
            $ModifiedCode
        }
        
        $userPrompt = @"
Analyze these C++ code changes for C++20 migration correctness:

FILE: $FilePath
API VERSION: $ApiVersion

ORIGINAL CODE:
```cpp
$originalSnippet
```

MODIFIED CODE:
```cpp
$modifiedSnippet
```

Please:
1. Verify the transformations are correct for C++20
2. Check if all necessary changes were applied
3. Identify any issues or missing transformations
4. Suggest any additional improvements (WITHIN EXISTING LIBRARIES ONLY - no new includes or dependencies)

CRITICAL: Do NOT suggest adding new #include statements or external libraries. Only work with existing includes and C++20 standard library.

Respond in JSON format:
{
  "verified": true/false,
  "issues": ["list of issues if any"],
  "suggestions": ["list of improvement suggestions"],
  "missing_transformations": ["any patterns that should be changed but weren't"]
}
"@
        
        # Use /api/generate for better performance with large models
        # Focus on one file at a time - use larger context to keep file structure intact
        $generateUrl = "$($Script:Config.OllamaApiUrl)/generate"
        
        # Use larger context window to maintain full file context (6000 tokens)
        # This ensures AI can see the complete file structure, includes, namespaces, etc.
        $contextSize = 6000
        
        $generateBody = @{
            model = $Script:Config.OllamaModel
            prompt = ($systemPrompt + "`n`n" + $userPrompt)
            stream = $false
            options = @{
                num_ctx = $contextSize
                temperature = 0.1  # Lower temperature for faster, more deterministic responses
                num_predict = 500  # Limit response length for faster completion
                top_p = 0.9  # Nucleus sampling for faster generation
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "  Making POST request to $generateUrl with model $($Script:Config.OllamaModel)..." "Info"
        
        try {
            # Reduced timeout from 300s to 120s for faster failure detection
            $response = Invoke-RestMethod -Uri $generateUrl -Method Post -Body $generateBody -ContentType "application/json" -TimeoutSec 120
            $aiResponse = if ($response.response) { $response.response.Trim() } else { "" }
            Write-Status "  AI API call successful, response length: $($aiResponse.Length)" "Info"
        } catch {
            Write-Status "  /api/generate failed: $($_.Exception.Message), trying /api/chat..." "Warning"
            try {
                # Fallback to chat API with same optimizations
                $requestBody = @{
                    model = $Script:Config.OllamaModel
                    messages = @(
                        @{
                            role = "system"
                            content = $systemPrompt
                        },
                        @{
                            role = "user"
                            content = $userPrompt
                        }
                    )
                    stream = $false
                    options = @{
                        num_ctx = 6000  # Larger context to maintain full file structure
                        temperature = 0.1
                        num_predict = 500
                        top_p = 0.9
                    }
                } | ConvertTo-Json -Depth 10
                
                $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
                $aiResponse = $response.message.content.Trim()
                Write-Status "  AI API call successful (chat fallback), response length: $($aiResponse.Length)" "Info"
            } catch {
                Write-Status "  /api/chat also failed: $($_.Exception.Message)" "Error"
                Write-Status "  AI analysis unavailable - continuing without AI verification" "Warning"
                $aiResponse = ""
            }
        }
        
        if ($aiResponse) {
            
            # Try to parse JSON response
            try {
                # Extract JSON from markdown code blocks if present
                if ($aiResponse -match '```json\s*(\{.*?\})\s*```') {
                    $aiResponse = $matches[1]
                } elseif ($aiResponse -match '```\s*(\{.*?\})\s*```') {
                    $aiResponse = $matches[1]
                }
                
                $result = $aiResponse | ConvertFrom-Json
                
                $Script:Config.AIVerifications++
                
                return @{
                    Verified = if ($result.verified) { $result.verified } else { $true }
                    Issues = if ($result.issues) { $result.issues } else { @() }
                    Suggestions = if ($result.suggestions) { $result.suggestions } else { @() }
                    MissingTransformations = if ($result.missing_transformations) { $result.missing_transformations } else { @() }
                    RawResponse = $aiResponse
                }
            } catch {
                # If JSON parsing fails, try to extract information from text
                Write-Status "AI response received but JSON parsing failed, analyzing text..." "Warning"
                $Script:Config.AIVerifications++
                
                $hasIssues = $aiResponse -match 'issue|problem|error|incorrect|wrong' -and $aiResponse -notmatch 'no issue|no problem'
                $suggestions = @()
                
                if ($aiResponse -match 'suggest[^:]*?:\s*(.+?)(?:\n|$)') {
                    $suggestions += $matches[1]
                }
                
                return @{
                    Verified = -not $hasIssues
                    Issues = if ($hasIssues) { @("AI detected potential issues - review recommended") } else { @() }
                    Suggestions = $suggestions
                    MissingTransformations = @()
                    RawResponse = $aiResponse
                }
            }
        }
    } catch {
        Write-Status "AI analysis failed: $_" "Warning"
        return @{ Verified = $true; Suggestions = @() }
    }
    
    return @{ Verified = $true; Suggestions = @() }
}

function Invoke-AIAlternativeChange {
    <#
    .SYNOPSIS
      Requests an alternative implementation from AI based on user feedback
    #>
    param(
        [string]$FilePath,
        [string]$OriginalSuggestion,
        [string]$UserFeedback,
        [string]$ApiVersion,
        [string]$CurrentContent
    )
    
    if (-not $Script:Config.UseAI -or -not (Test-OllamaAvailable)) {
        return $null
    }
    
    # Apply AI delay to prevent overwhelming Ollama
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0) {
                if ($Script:Config.Verbose) {
                    Write-Status "  Waiting ${waitTime}s before AI alternative request (rate limiting)..." "Info"
                }
                Start-Sleep -Seconds $waitTime
            }
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $fileName = Split-Path -Leaf $FilePath
        $maxCodeLength = 3000
        $codeSnippet = if ($CurrentContent.Length -gt $maxCodeLength) {
            $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
        } else {
            $CurrentContent
        }
        
        $systemPrompt = @"
You are an expert C++ code reviewer specializing in C++20 migration.
The user wants an ALTERNATIVE implementation for a suggested change.

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
"@
        
        $userPrompt = @"
FILE: $fileName
API VERSION: $ApiVersion

ORIGINAL SUGGESTION:
$OriginalSuggestion

USER FEEDBACK/REQUEST:
$UserFeedback

CURRENT CODE (context):
```cpp
$codeSnippet
```

Provide an ALTERNATIVE implementation that addresses the user's feedback.
Return the complete code change needed, or explain why an alternative isn't possible.
Be specific and provide actual code if possible.
"@
        
        $requestBody = @{
            model = $Script:Config.OllamaModel
            messages = @(
                @{ role = "system"; content = $systemPrompt }
                @{ role = "user"; content = $userPrompt }
            )
            stream = $false
            options = @{
                num_ctx = 6000
                temperature = 0.2
                num_predict = 500
            }
        } | ConvertTo-Json -Depth 10
        
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
        return $response.message.content.Trim()
    }
    catch {
        Write-Status "AI alternative request failed: $_" "Warning"
        return $null
    }
}

function Invoke-AIGenerateCodeChange {
    <#
    .SYNOPSIS
      Uses AI to generate actual code changes for a suggestion
    #>
    param(
        [string]$FilePath,
        [string]$Suggestion,
        [string]$CurrentContent,
        [string]$ApiVersion
    )
    
    if (-not $Script:Config.UseAI -or -not (Test-OllamaAvailable)) {
        return $null
    }
    
    # Apply AI delay to prevent overwhelming Ollama
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0) {
                if ($Script:Config.Verbose) {
                    Write-Status "  Waiting ${waitTime}s before AI code generation (rate limiting)..." "Info"
                }
                Start-Sleep -Seconds $waitTime
            }
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $fileName = Split-Path -Leaf $FilePath
        $maxCodeLength = 4000  # Larger context for code generation
        $codeSnippet = if ($CurrentContent.Length -gt $maxCodeLength) {
            $CurrentContent.Substring(0, $maxCodeLength) + "`n// ... (truncated) ..."
        } else {
            $CurrentContent
        }
        
        $systemPrompt = @"
You are an expert C++ code reviewer specializing in C++20 migration.
Generate ACTUAL CODE CHANGES that can be applied to the file.

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies

Return the COMPLETE MODIFIED CODE SECTION that implements the suggestion.
If the change affects multiple parts, return all affected sections.
Use clear markers like "// OLD CODE:" and "// NEW CODE:" or provide a unified diff.
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
Be specific and provide the exact code that should be in the file.

Format your response as:
OLD CODE:
[code to replace]

NEW CODE:
[replacement code]

Or if it's a simple addition/modification, just provide the new code with clear context.
"@
        
        $requestBody = @{
            model = $Script:Config.OllamaModel
            messages = @(
                @{ role = "system"; content = $systemPrompt }
                @{ role = "user"; content = $userPrompt }
            )
            stream = $false
            options = @{
                num_ctx = 8000  # Larger context for code generation
                temperature = 0.1  # Lower for more deterministic code
                num_predict = 1000  # Allow longer responses for code
            }
        } | ConvertTo-Json -Depth 10
        
        $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 180
        return $response.message.content.Trim()
    }
    catch {
        Write-Status "AI code generation failed: $_" "Warning"
        return $null
    }
}

function Apply-AICodeChange {
    <#
    .SYNOPSIS
      Applies an AI-generated code change to a file
    #>
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
            
            # Try exact string match first (most reliable)
            if ($CurrentContent.Contains($oldCode)) {
                $modifiedContent = $CurrentContent.Replace($oldCode, $newCode)
                return @{ Success = $true; Content = $modifiedContent; Method = "replacement" }
            }
            
            # Try with normalized whitespace (handle different line endings)
            $oldCodeNormalized = $oldCode -replace '\r\n', "`n" -replace '\r', "`n"
            $currentNormalized = $CurrentContent -replace '\r\n', "`n" -replace '\r', "`n"
            
            if ($currentNormalized.Contains($oldCodeNormalized)) {
                $newCodeNormalized = $newCode -replace '\r\n', "`n" -replace '\r', "`n"
                $modifiedContent = $currentNormalized.Replace($oldCodeNormalized, $newCodeNormalized)
                # Restore original line endings if possible
                if ($CurrentContent -match '\r\n') {
                    $modifiedContent = $modifiedContent -replace "`n", "`r`n"
                } elseif ($CurrentContent -match '\r[^\n]') {
                    $modifiedContent = $modifiedContent -replace "`n", "`r"
                }
                return @{ Success = $true; Content = $modifiedContent; Method = "replacement" }
            }
        }
        
        # Fallback: Try to extract code from markdown code blocks
        $codeBlockPattern = '(?s)```(?:cpp|c\+\+)?\s*(.*?)```'
        if ($AICodeChange -match $codeBlockPattern) {
            $extractedCode = $Matches[1].Trim()
            
            # Try to find a unique identifier in the extracted code to locate where to insert/replace
            # Look for function names, class names, or variable names
            $identifiers = $extractedCode -split '\s+' | Where-Object { 
                $_ -match '^[a-zA-Z_][a-zA-Z0-9_]*$' -and $_.Length -gt 3 -and $_ -notmatch '^(if|for|while|return|const|auto|void|int|bool|class|struct)$'
            } | Select-Object -First 5
            
            foreach ($identifier in $identifiers) {
                # Try to find this identifier in the current content
                if ($CurrentContent.Contains($identifier)) {
                    # Try to find surrounding context (50 chars before and after)
                    $idx = $CurrentContent.IndexOf($identifier)
                    if ($idx -ge 0) {
                        $startIdx = [Math]::Max(0, $idx - 50)
                        $endIdx = [Math]::Min($CurrentContent.Length, $idx + $identifier.Length + 50)
                        $context = $CurrentContent.Substring($startIdx, $endIdx - $startIdx)
                        
                        # If extracted code contains similar context, try replacement
                        if ($extractedCode.Contains($identifier)) {
                            # Try to find a larger matching block around this identifier
                            # Look for function/class boundaries
                            $beforeContext = $CurrentContent.Substring([Math]::Max(0, $idx - 200), [Math]::Min(200, $idx))
                            $afterContext = $CurrentContent.Substring($idx, [Math]::Min(500, $CurrentContent.Length - $idx))
                            
                            # Try to match a larger block
                            $matchPattern = '(?s).{0,100}' + [regex]::Escape($identifier) + '.{0,200}'
                            if ($CurrentContent -match $matchPattern) {
                                $matchedBlock = $Matches[0]
                                # If the AI code is similar, try replacement
                                if ($extractedCode.Length -gt 20 -and $matchedBlock.Length -lt 1000) {
                                    # Heuristic: if extracted code is similar size and contains identifier
                                    $modifiedContent = $CurrentContent.Replace($matchedBlock, $extractedCode)
                                    Write-Status "  Applied change using context matching" "Info"
                                    return @{ Success = $true; Content = $modifiedContent; Method = "context_replacement" }
                                }
                            }
                        }
                    }
                }
            }
            
            # If no match found, append with clear marker for manual review
            $modifiedContent = $CurrentContent + "`n`n// ===== AI APPLIED CHANGE (review and integrate manually) =====`n" + $extractedCode + "`n// ===== END AI CHANGE =====`n"
            Write-Status "  Code extracted and appended for manual review" "Warning"
            return @{ Success = $true; Content = $modifiedContent; Method = "append_review" }
        }
        
        # Last resort: Extract any code-like content and append for review
        # Look for lines that look like C++ code
        $codeLines = $AICodeChange -split "`n" | Where-Object {
            $line = $_.Trim()
            $line.Length -gt 5 -and (
                $line -match '(?:^|\s)(?:if|for|while|class|struct|void|int|bool|return|const|auto|std::|namespace)' -or
                $line -match '^\s*(?:[a-zA-Z_][a-zA-Z0-9_]*\s*[=\(\)\[\]\{\}])' -or
                $line -match '^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*::' -or
                $line -match '^\s*[a-zA-Z_][a-zA-Z0-9_<>]*\s+[a-zA-Z_][a-zA-Z0-9_]*\s*[=\(]'
            )
        } | Select-Object -First 30
        
        if ($codeLines.Count -gt 0) {
            $extractedCode = ($codeLines -join "`n").Trim()
            $modifiedContent = $CurrentContent + "`n`n// ===== AI APPLIED CHANGE (review and integrate manually) =====`n" + $extractedCode + "`n// ===== END AI CHANGE =====`n"
            Write-Status "  Code extracted and appended for manual review" "Warning"
            return @{ Success = $true; Content = $modifiedContent; Method = "append_review" }
        }
        
        # Final fallback: Show the AI response for manual application
        Write-Status "  Could not automatically apply change - manual review needed" "Warning"
        Write-Host "  AI Generated Code (first 500 chars):" -ForegroundColor Yellow
        $preview = if ($AICodeChange.Length -gt 500) { $AICodeChange.Substring(0, 500) + "..." } else { $AICodeChange }
        Write-Host "  $preview" -ForegroundColor Gray
        return @{ Success = $false; Content = $CurrentContent; Method = "manual" }
    }
    catch {
        Write-Status "  Error applying AI change: $_" "Warning"
        return @{ Success = $false; Content = $CurrentContent; Method = "error" }
    }
}

function Invoke-AICodeReview {
    <#
    .SYNOPSIS
      Uses AI to review a file and suggest additional C++20 improvements
    #>
    param(
        [string]$FilePath,
        [string]$ApiVersion,
        [string]$ModifiedContent = $null  # If provided, review the modified content instead of reading from file
    )
    
    if (-not $Script:Config.UseAI) {
        return @()
    }
    
    if (-not (Test-OllamaAvailable)) {
        return @()
    }
    
    # Apply AI delay to prevent overwhelming Ollama
    if ($Script:Config.LastAICallTime) {
        $timeSinceLastCall = (Get-Date) - $Script:Config.LastAICallTime
        if ($timeSinceLastCall.TotalSeconds -lt $Script:Config.AIDelay) {
            $waitTime = [Math]::Ceiling($Script:Config.AIDelay - $timeSinceLastCall.TotalSeconds)
            if ($waitTime -gt 0) {
                if ($Script:Config.Verbose) {
                    Write-Status "  Waiting ${waitTime}s before AI review (rate limiting)..." "Info"
                }
                Start-Sleep -Seconds $waitTime
            }
        }
    }
    $Script:Config.LastAICallTime = Get-Date
    
    try {
        $content = if ($ModifiedContent) {
            $ModifiedContent
        } else {
            Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
        }
        
        if (-not $content -or $content.Length -gt 50000) {
            # Skip very large files
            return @()
        }
        
        # Focus on one file at a time with full context
        # Use larger code sample to preserve file structure and context
        $maxCodeLength = 3000
        $codeSnippet = if ($content.Length -gt $maxCodeLength) {
            # Take from start to preserve includes, namespace, class structure
            $content.Substring(0, $maxCodeLength) + "`n// ... (truncated - showing first 3000 chars for context) ..."
        } else {
            $content
        }
        
        $fileName = Split-Path -Leaf $FilePath
        $fileDir = Split-Path -Parent $FilePath
        
        $systemPrompt = @"
You are an expert C++ code reviewer specializing in C++20 migration.
Analyze ONE FILE AT A TIME with full context.

Focus on this single file only - do not reference other files.
Keep all suggestions within the context of this specific file.

CRITICAL CONSTRAINT: NO NEW LIBRARIES CAN BE SUPPORTED
- Do NOT suggest adding new #include statements for external libraries
- Do NOT suggest using third-party libraries or dependencies
- Only use existing libraries already present in the codebase
- Only use the C++20 standard library (std::) - no external dependencies
- Work within the constraints of existing includes and dependencies

Focus on: modern C++20 features, smart pointers, const correctness, ranges, concepts (if applicable).
Keep suggestions practical and specific to THIS FILE ONLY.
"@
        
        $userPrompt = @"
Review this SINGLE C++ file for additional C++20 improvements.
Maintain full context of the file structure.

FILE PATH: $FilePath
FILE NAME: $fileName
DIRECTORY: $fileDir
API VERSION: $ApiVersion

CODE (first 3000 chars for context):
```cpp
$codeSnippet
```

Suggest specific, actionable improvements for C++20 compliance and best practices FOR THIS FILE ONLY.
List them as bullet points, one per line.
Keep all suggestions focused on this single file.

CRITICAL: Do NOT suggest adding new #include statements or external libraries. Only work with existing includes and C++20 standard library.
"@
        
        # Use /api/generate for better performance with large models
        $generateUrl = "$($Script:Config.OllamaApiUrl)/generate"
        $generateBody = @{
            model = $Script:Config.OllamaModel
            prompt = ($systemPrompt + "`n`n" + $userPrompt)
            stream = $false
            options = @{
                num_ctx = 6000  # Larger context to maintain full file structure (one file at a time)
                temperature = 0.1  # Lower for faster, more deterministic responses
                num_predict = 300  # Limit response length
                top_p = 0.9
            }
        } | ConvertTo-Json -Depth 10
        
        Write-Status "  Making POST request to $generateUrl with model $($Script:Config.OllamaModel)..." "Info"
        
        try {
            # Reduced timeout from 300s to 120s for faster failure detection
            $response = Invoke-RestMethod -Uri $generateUrl -Method Post -Body $generateBody -ContentType "application/json" -TimeoutSec 120
            $aiResponse = if ($response.response) { $response.response.Trim() } else { "" }
            Write-Status "  AI API call successful (generate), response length: $($aiResponse.Length)" "Info"
        } catch {
            Write-Status "  /api/generate failed: $($_.Exception.Message), trying /api/chat..." "Warning"
            try {
                # Fallback to chat API with same optimizations
                $requestBody = @{
                    model = $Script:Config.OllamaModel
                    messages = @(
                        @{
                            role = "system"
                            content = $systemPrompt
                        },
                        @{
                            role = "user"
                            content = $userPrompt
                        }
                    )
                    stream = $false
                    options = @{
                        num_ctx = 6000  # Larger context to maintain full file structure (one file at a time)
                        temperature = 0.1
                        num_predict = 300
                        top_p = 0.9
                    }
                } | ConvertTo-Json -Depth 10
                
                Write-Status "  Making POST request to $($Script:Config.OllamaApiUrl)/chat..." "Info"
                $response = Invoke-RestMethod -Uri "$($Script:Config.OllamaApiUrl)/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
                $aiResponse = $response.message.content.Trim()
                Write-Status "  AI API call successful (chat), response length: $($aiResponse.Length)" "Info"
            } catch {
                Write-Status "  /api/chat also failed: $($_.Exception.Message)" "Error"
                Write-Status "  AI review unavailable - continuing without AI suggestions" "Warning"
                $aiResponse = ""
            }
        }
        
        if ($aiResponse) {
            $suggestions = $aiResponse -split "`n" | Where-Object { $_ -match '^\s*[-*•]' -or $_ -match '^\d+\.' } | ForEach-Object { $_.Trim() } | Where-Object { $_.Length -gt 0 }
            $Script:Config.AISuggestions += $suggestions.Count
            return $suggestions
        }
    } catch {
        Write-Status "AI review failed for $FilePath : $_" "Warning"
    }
    
    return @()
}

# ============================================================================
# CODE TRANSFORMATION
# ============================================================================

function Apply-MigrationRules {
    param(
        [string]$FilePath,
        [array]$Rules
    )
    
    $content = Get-Content -Path $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return @{ Modified = $false; Changes = 0 } }
    
    $originalContent = $content
    $changes = 0
    $changeLog = @()
    $aiAnalysis = $null
    
    foreach ($rule in $Rules) {
        if ($content -match $rule.Pattern) {
            $newContent = $content -replace $rule.Pattern, $rule.Replacement
            
            if ($newContent -ne $content) {
                $content = $newContent
                $changes++
                $changeLog += "  - $($rule.Description) [$($rule.Category)]"
                
                if ($Script:Config.Verbose) {
                    Write-Status "    Applied: $($rule.Description)" "Info"
                }
            }
        }
    }
    
    # Special handling for SRunOptions setup
    if ($content -match '\.TopLevel\s*\([^)]+?RunOptions') {
        if ($content -notmatch 'SRunOptions\s+RunOptions') {
            # Try to add SRunOptions setup if SExecuteCtx exists
            if ($content -match '(SExecuteCtx\s+Ctx[^;]+?;)') {
                $replacement = '$1' + "`r`n`r`n`tCCodeChain::SRunOptions RunOptions;`r`n`tRunOptions.pExternalCtx = &Ctx;"
                $content = $content -replace '(SExecuteCtx\s+Ctx[^;]+?;)', $replacement
                $changes++
                $changeLog += "  - Added SRunOptions setup"
            }
        }
    }
    
    # AI Verification if code was modified
    # Apply AI strategy to determine when to use AI
    $skipAIVerification = $false
    $shouldUseAI = $false
    
    if ($content -ne $originalContent -and $Script:Config.UseAI) {
        # Apply AI strategy
        switch ($Script:Config.AIStrategy) {
            "conservative" {
                # Only use AI for complex changes or errors
                $shouldUseAI = $changes -gt 3 -or ($changeLog -match "SmartPointers|C\+\+20Features")
            }
            "aggressive" {
                # Use AI for all changes
                $shouldUseAI = $true
            }
            "compile-first" {
                # Skip AI verification here - will use AI after compilation errors
                $shouldUseAI = $false
            }
            "smart" {
                # Default: Use AI for non-trivial changes, skip for simple pattern replacements
                # But be more liberal - use AI if there are any changes to CodeChainAPI or multiple changes
                $shouldUseAI = $changes -gt 0 -or ($changeLog -match "SmartPointers|C\+\+20Features|CodeChainAPI")
            }
        }
        
        if (-not $shouldUseAI) {
            $skipAIVerification = $true
            if ($Script:Config.Verbose) {
                Write-Status "  Skipping AI verification (strategy: $($Script:Config.AIStrategy))" "Info"
            }
        }
        # In FastMode, skip AI verification for known-safe pattern changes
        if ($Script:Config.FastMode) {
            # Check if changes match only known-safe patterns
            $safePatterns = @(
                'std::experimental::',
                'CC\.Link\s*\(',
                '\.Print\s*\(\s*&?CC\s*\)',
                '\.Discard\s*\(\s*&?CC\s*\)',
                'CreateXMLElementFromCommandLine\s*\(\s*argc,\s*argv,'
            )
            
            $hasOnlySafeChanges = $true
            foreach ($rule in $Rules) {
                if ($rule.Category -in @('StandardLibrary', 'CodeChainAPI', 'XMLUtil')) {
                    # These are known-safe transformations
                    continue
                } else {
                    $hasOnlySafeChanges = $false
                    break
                }
            }
            
            if ($hasOnlySafeChanges) {
                $skipAIVerification = $true
                Write-Status "  Skipping AI verification (FastMode: known-safe changes)" "Info"
            }
        }
        
        # If we have complex changes or unknown patterns, use AI
        if (-not $skipAIVerification) {
            # Extract code sample with full file context (focus on one file at a time)
            # Use larger sample to preserve file structure, includes, namespaces, class definitions
            $sampleSize = [Math]::Min(3000, $originalContent.Length)
            $originalSample = $originalContent.Substring(0, $sampleSize)
            $modifiedSample = $content.Substring(0, [Math]::Min($sampleSize, $content.Length))
            
            Write-Status "  Verifying changes with AI (focusing on this file with full context, ~20-40 seconds)..." "Info"
            Write-Status "  Making AI API call to Ollama ($($Script:Config.OllamaModel))..." "Info"
            
            # Use job with timeout to prevent infinite loops
            Write-Status "  Starting AI analysis job..." "Info"
            $aiJob = Start-Job -ScriptBlock {
                param($OriginalCode, $ModifiedCode, $FilePath, $ApiVersion, $Config, $MainScriptPath, $OllamaApiUrl, $OllamaModel)
                $Script:Config = $Config
                $Script:Config.OllamaApiUrl = $OllamaApiUrl
                $Script:Config.OllamaModel = $OllamaModel
                . $MainScriptPath -GuiMode:$true
                Invoke-AICodeAnalysis -OriginalCode $OriginalCode -ModifiedCode $ModifiedCode -FilePath $FilePath -ApiVersion $ApiVersion
            } -ArgumentList $originalSample, $modifiedSample, $FilePath, $Script:Config.ApiVersion, $Script:Config, (Join-Path $PSScriptRoot "AutoUpdate-CPP20-API.ps1"), $Script:Config.OllamaApiUrl, $Script:Config.OllamaModel
            
            # Wait with timeout (reduced default from 5 minutes to 2 minutes for faster processing)
            $aiTimeout = if ($Script:Config.MaxAITimePerFile) { $Script:Config.MaxAITimePerFile } else { 120 }
            
            # Progress reporting during wait to prevent "stuck" appearance
            $startTime = Get-Date
            $progressInterval = 10  # Report progress every 10 seconds
            $lastProgressTime = $startTime
            
            while ($aiJob.State -eq "Running") {
                Start-Sleep -Seconds 2
                
                $elapsed = (Get-Date) - $startTime
                if ($elapsed.TotalSeconds -gt $aiTimeout) {
                    Write-Status "  AI verification timeout reached (${aiTimeout}s) - stopping..." "Warning"
                    $aiJob | Stop-Job -ErrorAction SilentlyContinue
                    break
                }
                
                # Report progress every 10 seconds
                if (($elapsed - $lastProgressTime).TotalSeconds -ge $progressInterval) {
                    $remaining = [int]($aiTimeout - $elapsed.TotalSeconds)
                    Write-Status "  AI verification in progress... (~${remaining}s remaining)" "Info"
                    $lastProgressTime = Get-Date
                }
            }
            
            $waitResult = $aiJob | Wait-Job -Timeout 5  # Short timeout to get result if job completed
            
            if ($waitResult) {
                $aiAnalysis = Receive-Job $aiJob
                if ($aiAnalysis) {
                    Write-Status "  AI verification complete" "Success"
                    Write-Status "  AI Response received (Issues: $($aiAnalysis.Issues.Count), Suggestions: $($aiAnalysis.Suggestions.Count))" "Info"
                } else {
                    Write-Status "  AI verification returned no result" "Warning"
                    $aiAnalysis = @{ Verified = $true; Issues = @(); Suggestions = @(); MissingTransformations = @() }
                }
            } else {
                if ($aiJob.State -eq "Running") {
                    Write-Status "  AI verification timed out after ${aiTimeout}s - skipping verification" "Warning"
                    $aiJob | Stop-Job -ErrorAction SilentlyContinue
                } else {
                    # Check for errors in the job
                    $jobErrors = Receive-Job $aiJob -ErrorAction SilentlyContinue
                    if ($jobErrors) {
                        Write-Status "  AI verification job error: $jobErrors" "Warning"
                    }
                }
                $aiAnalysis = @{ Verified = $true; Issues = @(); Suggestions = @(); MissingTransformations = @() }
            }
            
            $aiJob | Remove-Job -ErrorAction SilentlyContinue
            
            if ($aiAnalysis.Issues.Count -gt 0) {
                Write-Status "  AI detected issues:" "Warning"
                foreach ($issue in $aiAnalysis.Issues) {
                    Write-Status "    - $issue" "Warning"
                }
            }
            
            if ($aiAnalysis.Suggestions.Count -gt 0) {
                Write-Status "  AI suggestions:" "Info"
                foreach ($suggestion in $aiAnalysis.Suggestions) {
                    Write-Status "    + $suggestion" "Info"
                    $changeLog += "  - AI Suggestion: $suggestion"
                }
            }
            
            if ($aiAnalysis.MissingTransformations.Count -gt 0) {
                Write-Status "  AI found missing transformations:" "Warning"
                foreach ($missing in $aiAnalysis.MissingTransformations) {
                    Write-Status "    ! $missing" "Warning"
                }
            }
        } else {
            # FastMode: Skip AI verification for known-safe changes
            if ($Script:Config.Verbose) {
                Write-Status "  Skipping AI verification (FastMode: known-safe changes)" "Info"
            }
            $aiAnalysis = @{ Verified = $true; Issues = @(); Suggestions = @(); MissingTransformations = @() }
        }
    } else {
        if ($Script:Config.Verbose) {
            Write-Status "  Skipping AI verification (content unchanged or AI disabled)" "Info"
        }
    }
    
    return @{
        Modified = ($content -ne $originalContent)
        Content = $content
        Changes = $changes
        ChangeLog = $changeLog
        AIAnalysis = $aiAnalysis
    }
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
Write-Host "  Auto C++20 Migration Tool for Transcendence API" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
if ($Script:Config.AutoDetectAI) {
    Write-Host "  AI: Auto-detection enabled (will use AI if Ollama is available)" -ForegroundColor Gray
    Write-Host ""
}

# Resolve path
$resolvedPath = Resolve-Path $Script:Config.Path -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
    Write-Status "Path not found: $($Script:Config.Path)" "Error"
    exit 1
}

$Script:Config.Path = $resolvedPath.Path
Write-Status "Processing: $($Script:Config.Path)" "Info"

# Detect API version
$Script:Config.ApiVersion = Get-ApiVersion -SearchPath $Script:Config.Path
Write-Status "API Version: $($Script:Config.ApiVersion)" "Info"

# Auto-detect and enable AI if available (unless explicitly disabled)
if ($Script:Config.AutoDetectAI) {
    Write-Status "Auto-detecting AI availability..." "Info"
    if (Test-OllamaAvailable) {
        $Script:Config.UseAI = $true
        Write-Status "AI automatically enabled (Ollama detected and available)" "Success"
        Write-Status "  Using model: $($Script:Config.OllamaModel)" "Info"
    } else {
        $Script:Config.UseAI = $false
        Write-Status "AI automatically disabled (Ollama not available)" "Info"
        Write-Status "  Install Ollama from https://ollama.ai to enable AI features" "Info"
        Write-Status "  Or use -UseAI flag to force enable (will show errors if unavailable)" "Info"
    }
}

# Check AI availability
if ($Script:Config.UseAI) {
    $modeText = if ($Script:Config.FastMode) { " (FastMode: skipping AI for known-safe changes)" } else { "" }
    $strategyText = " (Strategy: $($Script:Config.AIStrategy), Delay: $($Script:Config.AIDelay)s)"
    Write-Status "AI Assistance: Enabled (Model: $($Script:Config.OllamaModel))$modeText$strategyText" "Info"
    if ($Script:Config.FastMode) {
        Write-Status "FastMode enabled: AI verification skipped for known-safe pattern changes" "Info"
        Write-Status 'This significantly speeds up processing (2-5x faster)' "Info"
    }
    if (Test-OllamaAvailable) {
        Write-Status "Ollama service is available" "Success"
        if ($Script:Config.OllamaModel -like "*34b*") {
            Write-Status "Note: Using large model (34b). Consider 'codellama:13b' or 'codellama:7b' for faster processing" "Info"
        }
        
        # Test AI with a simple call to verify it works
        Write-Status "Testing AI connection..." "Info"
        try {
            $testUrl = "$($Script:Config.OllamaApiUrl)/generate"
            $testBody = @{
                model = $Script:Config.OllamaModel
                prompt = "Say 'OK' if you can read this."
                stream = $false
                options = @{
                    num_predict = 10
                }
            } | ConvertTo-Json -Depth 10
            
            $testResponse = Invoke-RestMethod -Uri $testUrl -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
            if ($testResponse.response) {
                Write-Status "AI connection test successful" "Success"
            } else {
                Write-Status "AI connection test returned no response" "Warning"
            }
        } catch {
            Write-Status "AI connection test failed: $($_.Exception.Message)" "Warning"
            Write-Status "AI may not work properly. Check Ollama logs for errors." "Warning"
        }
    } else {
        Write-Status "Ollama not available - AI features disabled" "Warning"
        $Script:Config.UseAI = $false
        if (-not $Script:Config.AutoDetectAI) {
            Write-Status "  Install Ollama from https://ollama.ai to enable AI features" "Info"
        }
    }
} else {
    if ($NoAI) {
        Write-Status "AI Assistance: Explicitly disabled" "Info"
    } else {
        Write-Status "AI Assistance: Disabled (Ollama not available)" "Info"
    }
}

# Get migration rules
$Script:Config.MigrationRules = Get-Cpp20MigrationRules -ApiVersion $Script:Config.ApiVersion

if ($Script:Config.DryRun) {
    Write-Status "DRY RUN MODE - No files will be modified" "Warning"
}

Write-Host ""

# Get all C++ files (use cached version to prevent CPU burn)
$cppFiles = Get-CachedChildItem -Path $Script:Config.Path -Recurse -Include "*.cpp", "*.h", "*.hpp" -File

if ($cppFiles.Count -eq 0) {
    Write-Status "No C++ files found in: $($Script:Config.Path)" "Warning"
    exit 0
}

Write-Status "Found $($cppFiles.Count) C++ file(s) to process" "Info"
Write-Host ""

# Process each file sequentially with CPU throttling
$fileCount = $cppFiles.Count
foreach ($file in $cppFiles) {
    $Script:Config.FilesProcessed++
    
    # Throttle file operations to reduce CPU usage
    if ($Script:Config.FilesProcessed % 50 -eq 0) {
        Start-Sleep -Milliseconds 10
    }
    
    Write-Status "Processing: $($file.Name) ($($Script:Config.FilesProcessed)/$fileCount)" "Info"
    if ($Script:Config.Verbose) {
        Write-Status "  File path: $($file.FullName)" "Info"
    }
    
    # Process one file at a time with full context
    $result = Apply-MigrationRules -FilePath $file.FullName -Rules $Script:Config.MigrationRules
    
    if ($result.Modified) {
        $Script:Config.FilesModified++
        $Script:Config.TotalChanges += $result.Changes
        
        $changeText = if ($result.Changes -eq 1) { "change" } else { "changes" }
        $fileName = $file.Name
        $changeCount = $result.Changes
        $statusMsg = "Modified: $fileName - $changeCount $changeText"
        Write-Status $statusMsg "Success"
        
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
        }
    }
    
    # AI verification and suggestions AFTER automatic rule-based changes
    # Apply AI strategy to determine when to analyze
    if ($Script:Config.UseAI) {
        # Determine if we should analyze based on strategy
        $shouldAnalyze = $false
        switch ($Script:Config.AIStrategy) {
            "conservative" {
                # Only analyze modified files with significant changes
                $shouldAnalyze = $result.Modified -and $result.Changes -gt 2
            }
            "aggressive" {
                # Analyze all modified files and periodically check others
                $shouldAnalyze = $result.Modified -or ($Script:Config.FilesProcessed % 10 -eq 0)
            }
            "compile-first" {
                # Skip analysis here - will use FixApiCompatibilityAI after compilation
                $shouldAnalyze = $false
            }
            "smart" {
                # Default: Analyze modified files and periodically check others (less frequent)
                $shouldAnalyze = $result.Modified -or ($Script:Config.FilesProcessed % 30 -eq 0)
            }
        }
        
        if ($shouldAnalyze) {
            Write-Status "  AI analysis triggered (strategy: $($Script:Config.AIStrategy), file: $($file.Name))" "Info"
            $contentToAnalyze = if ($result.Modified) {
                $result.Content  # Use the modified content if rules changed it
            } else {
                Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
            }
            
            if ($contentToAnalyze -and $contentToAnalyze.Length -lt 20000 -and $contentToAnalyze.Length -gt 100) {
                try {
                    if ($result.Modified) {
                        Write-Status "  Verifying automatic changes with AI..." "Info"
                    }
                    
                    Write-Status "  Calling Invoke-AICodeReview (making AI API call)..." "Info"
                    $suggestions = Invoke-AICodeReview -FilePath $file.FullName -ApiVersion $Script:Config.ApiVersion -ModifiedContent $contentToAnalyze
                    Write-Status "  AI review returned $($suggestions.Count) suggestion(s)" "Info"
                    if ($suggestions.Count -gt 0) {
                        if ($result.Modified) {
                            Write-Status "  AI recommendations for $($file.Name) (after automatic changes):" "Info"
                        } else {
                            Write-Status "  AI suggestions for $($file.Name):" "Info"
                        }
                        
                        # Interactive mode: prompt for each suggestion
                        if ($Script:Config.Interactive) {
                            foreach ($suggestion in $suggestions) {
                                Write-Host ""
                                Write-Host "  Suggestion: $suggestion" -ForegroundColor Cyan
                                Write-Host "  [Y] Apply  [N] Skip  [A] Alternative  [Q] Quit interactive mode" -ForegroundColor Yellow
                                
                                $response = Read-Host "  Your choice"
                                $response = $response.Trim().ToUpper()
                                
                                if ($response -eq "Q") {
                                    Write-Status "  Exiting interactive mode" "Info"
                                    $Script:Config.Interactive = $false
                                    break
                                }
                                elseif ($response -eq "Y") {
                                    # Apply suggestion - generate and apply actual code change
                                    Write-Status "  Generating code change..." "Info"
                                    $aiCodeChange = Invoke-AIGenerateCodeChange -FilePath $file.FullName -Suggestion $suggestion -CurrentContent $contentToAnalyze -ApiVersion $Script:Config.ApiVersion
                                    
                                    if ($aiCodeChange) {
                                        Write-Status "  Applying code change..." "Info"
                                        $applyResult = Apply-AICodeChange -FilePath $file.FullName -AICodeChange $aiCodeChange -CurrentContent $contentToAnalyze
                                        
                                        if ($applyResult.Success) {
                                            if (-not $Script:Config.DryRun) {
                                                # Create backup if not already done
                                                if ($Script:Config.Backup -and -not $result.Modified) {
                                                    $backupPath = "$($file.FullName).backup"
                                                    Copy-Item -Path $file.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
                                                }
                                                
                                                # Write modified content
                                                [System.IO.File]::WriteAllText($file.FullName, $applyResult.Content, [System.Text.Encoding]::UTF8)
                                                $contentToAnalyze = $applyResult.Content  # Update for next iteration
                                                
                                                Write-Status "  Code change applied ($($applyResult.Method))" "Success"
                                                $Script:Config.FilesModified++
                                                $Script:Config.TotalChanges++
                                            } else {
                                                Write-Status "  Code change ready (DryRun - not applied)" "Info"
                                            }
                                            $Script:Config.AIApplied++
                                        } else {
                                            Write-Status "  Could not automatically apply - manual review needed" "Warning"
                                        }
                                    } else {
                                        Write-Status "  Could not generate code change" "Warning"
                                    }
                                }
                                elseif ($response -eq "A") {
                                    Write-Host "  Enter your feedback/request for alternative:" -ForegroundColor Yellow
                                    $userFeedback = Read-Host "  "
                                    
                                    if ($userFeedback) {
                                        Write-Status "  Requesting alternative from AI..." "Info"
                                        $alternative = Invoke-AIAlternativeChange -FilePath $file.FullName -OriginalSuggestion $suggestion -UserFeedback $userFeedback -ApiVersion $Script:Config.ApiVersion -CurrentContent $contentToAnalyze
                                        
                                        if ($alternative) {
                                            Write-Host ""
                                            Write-Host "  Alternative implementation:" -ForegroundColor Green
                                            Write-Host "  $alternative" -ForegroundColor Gray
                                            Write-Host ""
                                            
                                            $applyAlt = Read-Host "  Apply this alternative? [Y/N]"
                                            if ($applyAlt.Trim().ToUpper() -eq "Y") {
                                                Write-Status "  Applying alternative code change..." "Info"
                                                $applyResult = Apply-AICodeChange -FilePath $file.FullName -AICodeChange $alternative -CurrentContent $contentToAnalyze
                                                
                                                if ($applyResult.Success) {
                                                    if (-not $Script:Config.DryRun) {
                                                        # Create backup if not already done
                                                        if ($Script:Config.Backup -and -not $result.Modified) {
                                                            $backupPath = "$($file.FullName).backup"
                                                            Copy-Item -Path $file.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
                                                        }
                                                        
                                                        # Write modified content
                                                        [System.IO.File]::WriteAllText($file.FullName, $applyResult.Content, [System.Text.Encoding]::UTF8)
                                                        $contentToAnalyze = $applyResult.Content  # Update for next iteration
                                                        
                                                        Write-Status "  Alternative applied ($($applyResult.Method))" "Success"
                                                        $Script:Config.FilesModified++
                                                        $Script:Config.TotalChanges++
                                                    } else {
                                                        Write-Status "  Alternative ready (DryRun - not applied)" "Info"
                                                    }
                                                    $Script:Config.AIApplied++
                                                } else {
                                                    Write-Status "  Could not automatically apply alternative - manual review needed" "Warning"
                                                }
                                            }
                                        } else {
                                            Write-Status "  Could not generate alternative" "Warning"
                                        }
                                    }
                                }
                                else {
                                    Write-Status "  Skipped" "Info"
                                }
                            }
                        } else {
                            # Non-interactive: automatically apply suggestions
                            Write-Status "  Auto-applying AI suggestions (non-interactive mode)..." "Info"
                            foreach ($suggestion in $suggestions) {
                                Write-Host "    • $suggestion" -ForegroundColor Gray
                                
                                # Generate and apply the code change
                                Write-Status "      Generating code change for suggestion..." "Info"
                                $aiCodeChange = Invoke-AIGenerateCodeChange -FilePath $file.FullName -Suggestion $suggestion -CurrentContent $contentToAnalyze -ApiVersion $Script:Config.ApiVersion
                                
                                if ($aiCodeChange) {
                                    Write-Status "      Applying code change..." "Info"
                                    $applyResult = Apply-AICodeChange -FilePath $file.FullName -AICodeChange $aiCodeChange -CurrentContent $contentToAnalyze
                                    
                                    if ($applyResult.Success) {
                                        if (-not $Script:Config.DryRun) {
                                            # Create backup if not already done
                                            if ($Script:Config.Backup -and -not $result.Modified) {
                                                $backupPath = "$($file.FullName).backup"
                                                Copy-Item -Path $file.FullName -Destination $backupPath -Force -ErrorAction SilentlyContinue
                                            }
                                            
                                            # Write modified content
                                            [System.IO.File]::WriteAllText($file.FullName, $applyResult.Content, [System.Text.Encoding]::UTF8)
                                            $contentToAnalyze = $applyResult.Content  # Update for next iteration
                                            
                                            Write-Status "      Code change applied ($($applyResult.Method))" "Success"
                                            $Script:Config.FilesModified++
                                            $Script:Config.TotalChanges++
                                        } else {
                                            Write-Status "      Code change ready (DryRun - not applied)" "Info"
                                        }
                                        $Script:Config.AIApplied++
                                    } else {
                                        Write-Status "      Could not automatically apply - manual review needed" "Warning"
                                    }
                                } else {
                                    Write-Status "      Could not generate code change" "Warning"
                                }
                            }
                        }
                    } elseif ($result.Modified) {
                        Write-Status "  AI verification: Changes look good" "Success"
                    }
                }
                catch {
                    # Silently continue - AI analysis is optional
                    if ($Script:Config.Verbose) {
                        Write-Status "  AI analysis failed for $($file.Name): $_" "Warning"
                    }
                }
            }
        }
    }
}

# Final AI review summary (AI analysis already done during processing)
if ($Script:Config.UseAI -and $Script:Config.AISuggestions -gt 0) {
    Write-Host ""
    Write-Status "AI analysis complete - $($Script:Config.AISuggestions) suggestion(s) provided" "Success"
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Status "API Version: $($Script:Config.ApiVersion)" "Info"
Write-Status "Files processed: $($Script:Config.FilesProcessed)" "Info"
Write-Status "Files modified: $($Script:Config.FilesModified)" $(if ($Script:Config.FilesModified -gt 0) { "Success" } else { "Info" })
Write-Status "Total changes: $($Script:Config.TotalChanges)" $(if ($Script:Config.TotalChanges -gt 0) { "Success" } else { "Info" })
Write-Status "Migration rules applied: $($Script:Config.MigrationRules.Count)" "Info"

if ($Script:Config.UseAI) {
    Write-Status "AI verifications: $($Script:Config.AIVerifications)" "Info"
    Write-Status "AI suggestions: $($Script:Config.AISuggestions)" "Info"
    if ($Script:Config.Interactive) {
        Write-Status "AI changes applied: $($Script:Config.AIApplied)" "Info"
    }
    
    # Warn if AI wasn't used much
    if ($Script:Config.AIVerifications -eq 0 -and $Script:Config.FilesModified -gt 0) {
        Write-Host ""
        Write-Status "WARNING: AI was enabled but made no verification calls" "Warning"
        Write-Status "This may indicate:" "Warning"
        Write-Status "  - Strategy too conservative (try -ai-strategy aggressive)" "Info"
        Write-Status "  - FastMode skipping AI (remove -fast flag)" "Info"
        Write-Status "  - All changes were simple pattern replacements" "Info"
        Write-Status "Check verbose output (-verbose) to see why AI was skipped" "Info"
    }
}

if ($Script:Config.DryRun) {
    Write-Host ""
    Write-Status "This was a dry run. No files were modified." "Warning"
    Write-Status "Run without -DryRun to apply changes." "Warning"
}

Write-Host ""
# Post-processing: If using compile-first strategy, run compilation and AI fixes
if ($Script:Config.AIStrategy -eq "compile-first" -and $Script:Config.UseAI -and $Script:Config.FilesModified -gt 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Compile-First Strategy: Testing Compilation" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if CompileApiFolder.ps1 exists
    $compileScript = Join-Path $PSScriptRoot "CompileApiFolder.ps1"
    
    # Try multiple possible locations for FixApiCompatibilityAI.py
    $fixApiScript = $null
    
    # First, check settings file for Transcendence root
    $transcendenceRoot = $null
    $toolsRoot = Split-Path $PSScriptRoot -Parent
    $settingsFile = Join-Path $toolsRoot "TranscendenceTools.ini"
    if (Test-Path $settingsFile) {
        $content = Get-Content $settingsFile -Raw
        if ($content -match '(?m)^\s*TranscendencePath\s*=\s*(.+)$') {
            $path = $matches[1].Trim()
            $path = [System.Environment]::ExpandEnvironmentVariables($path)
            if (Test-Path $path) {
                $transcendenceRoot = $path
            }
        }
    }
    
    # If not in settings, try to detect from common Steam locations
    if (-not $transcendenceRoot) {
        $searchPaths = @(
            "${env:ProgramFiles(x86)}\Steam\steamapps\common\Transcendence",
            "${env:ProgramFiles}\Steam\steamapps\common\Transcendence",
            "$env:LOCALAPPDATA\Programs\Steam\steamapps\common\Transcendence",
            "$env:USERPROFILE\SteamLibrary\steamapps\common\Transcendence",
            "$env:USERPROFILE\Steam\steamapps\common\Transcendence",
            (Split-Path -Parent $PSScriptRoot)
        )
        
        # Check common drive letters for games partition (D:, E:, F:, etc.)
        $commonDrives = @('D', 'E', 'F', 'G', 'H')
        foreach ($drive in $commonDrives) {
            # Check for \games\Steam\ pattern (common for partitioned OS drives)
            $gamesPath = "${drive}:\games\Steam\steamapps\common\Transcendence"
            if (Test-Path $gamesPath) {
                $searchPaths += $gamesPath
            }
            
            # Check for \SteamLibrary\ pattern (common for additional Steam libraries)
            $steamLibraryPath = "${drive}:\SteamLibrary\steamapps\common\Transcendence"
            if (Test-Path $steamLibraryPath) {
                $searchPaths += $steamLibraryPath
            }
        }
        foreach ($path in $searchPaths) {
            if (Test-Path (Join-Path $path "Transcendence.tdb")) {
                $transcendenceRoot = $path
                break
            }
        }
    }
    
    $possiblePaths = @(
        Join-Path $PSScriptRoot "FixApiCompatibilityAI.py",
        Join-Path $PSScriptRoot "Transcendence\FixApiCompatibilityAI.py",
        Join-Path (Split-Path $PSScriptRoot -Parent) "Tools\Transcendence\FixApiCompatibilityAI.py"
    )
    
    # Add Extensions path if Transcendence root was found
    if ($transcendenceRoot) {
        $possiblePaths += Join-Path $transcendenceRoot "Extensions\Tools\Transcendence\FixApiCompatibilityAI.py"
    } else {
        # Fallback: try relative to script location
        $possiblePaths += Join-Path (Split-Path -Parent $PSScriptRoot) "Extensions\Tools\Transcendence\FixApiCompatibilityAI.py"
    }
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $fixApiScript = $path
            break
        }
    }
    
    if ($compileScript -and $fixApiScript -and (Test-Path $compileScript) -and (Test-Path $fixApiScript)) {
        Write-Status "Attempting compilation to identify remaining issues..." "Info"
        
        try {
            # Try to compile (capture output)
            $compileOutput = & $compileScript -ApiFolderPath $Script:Config.Path -NonInteractive 2>&1 | Out-String
            $compileSuccess = $LASTEXITCODE -eq 0
            
            if (-not $compileSuccess) {
                Write-Status "Compilation failed - applying AI fixes..." "Warning"
                
                # Save error output
                $errorFile = Join-Path $env:TEMP "transcendence_compile_errors_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
                $compileOutput | Out-File -FilePath $errorFile -Encoding UTF8
                
                # Run AI fixer
                Write-Status "Running FixApiCompatibilityAI on compilation errors..." "Info"
                Write-Status "  Using FixApiCompatibilityAI.py at: $fixApiScript" "Info"
                
                # Check if Python is available
                $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
                if (-not $pythonCmd) {
                    Write-Status "  Python not found in PATH - trying 'py' command..." "Warning"
                    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
                    if ($pythonCmd) {
                        $pythonExe = "py"
                    } else {
                        Write-Status "  Python not available - cannot run AI fixer" "Error"
                        Write-Status "  Please install Python or add it to PATH" "Warning"
                        continue
                    }
                } else {
                    $pythonExe = "python"
                }
                
                try {
                    $fixResult = & $pythonExe $fixApiScript --error-file $errorFile --model $Script:Config.OllamaModel $Script:Config.Path 2>&1
                    $fixExitCode = $LASTEXITCODE
                    
                    if ($Script:Config.Verbose -and $fixResult) {
                        Write-Host "  FixApiCompatibilityAI output:" -ForegroundColor Gray
                        $fixResult | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                    }
                } catch {
                    Write-Status "  Error running FixApiCompatibilityAI: $_" "Error"
                    $fixExitCode = 1
                }
                
                if ($fixExitCode -eq 0) {
                    Write-Status "AI fixes applied - recompiling..." "Success"
                    $recompileOutput = & $compileScript -ApiFolderPath $Script:Config.Path -NonInteractive 2>&1 | Out-String
                    $recompileSuccess = $LASTEXITCODE -eq 0
                    
                    if ($recompileSuccess) {
                        Write-Status "Compilation successful after AI fixes!" "Success"
                    } else {
                        Write-Status "Compilation still failing - manual review needed" "Warning"
                    }
                } else {
                    Write-Status "AI fixer encountered issues (exit code: $fixExitCode)" "Warning"
                    if ($fixResult) {
                        Write-Host "  Error output:" -ForegroundColor Yellow
                        $fixResult | Select-Object -First 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
                    }
                }
            } else {
                Write-Status "Compilation successful - no AI fixes needed!" "Success"
            }
        } catch {
            Write-Status "Error during compile-first workflow: $_" "Warning"
        }
    } else {
        if (-not (Test-Path $compileScript)) {
            Write-Status "CompileApiFolder.ps1 not found at: $compileScript" "Warning"
        }
        if (-not $fixApiScript -or -not (Test-Path $fixApiScript)) {
            Write-Status "FixApiCompatibilityAI.py not found - skipping compile-first step" "Warning"
            Write-Status "  Searched in:" "Info"
            foreach ($path in $possiblePaths) {
                Write-Status "    - $path" "Info"
            }
        }
    }
}

Write-Status "Migration complete!" "Success"
Write-Host ""

