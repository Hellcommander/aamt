#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix Caves of Qud mods to work with newer API versions and correct Harmony patch asset references.
    
.DESCRIPTION
    Automatically analyzes and fixes Caves of Qud mods using AI code models to:
    - Update mods to newer API versions
    - Fix Harmony patch asset references
    - Correct broken API calls

# AI-Assisted Modding Tools (AAMT) - Caves of Qud Toolset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for Qud mod fixing
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Ollama", "Python") `
    -OptionalTools @()

if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Qud mod fixing" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Caves of Qud - Mod Fixer" `
        -RequiredTools @("Ollama", "Python")
    exit 1
}

# Use Ollama integration
Use-OllamaIfAvailable | Out-Null
    - Switch between different AI models for optimal performance
    
.PARAMETER ModName
    Name of mod to fix (or 'all' for all mods). If not specified, shows interactive menu.
    
.PARAMETER SourcePath
    Path to decompiled Caves of Qud source code (default: G:\CavesofQud-decompiledsource)
    
.PARAMETER AssetsPath
    Path to StreamingAssets directory (default: E:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets)
    
.PARAMETER ModsPath
    Path to mods directory (default: C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods)
    
.PARAMETER Model
    AI model to use (e.g., "codellama:7b", "starcoder:7b", "codellama:34b"). If not specified, shows model selection menu.
    
.PARAMETER NoBackup
    Note: Backups are always created before fixing (this parameter is kept for compatibility but ignored).
    
.PARAMETER AnalyzeOnly
    Only analyze mods, don't apply fixes.
    
.PARAMETER ListModels
    List available Ollama models and exit.
    
.PARAMETER Interactive
    Show interactive menu for model selection and mod selection.
    
.EXAMPLE
    .\QudModFixer.ps1 -ModName "Broodmother Mutation"
    
.EXAMPLE
    .\QudModFixer.ps1 -ModName "all" -Model "codellama:7b"
    
.EXAMPLE
    .\QudModFixer.ps1 -AnalyzeOnly -Interactive
    
.EXAMPLE
    .\QudModFixer.ps1 -ListModels
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false, Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$ModName = @(),
    
    [Parameter(Mandatory=$false)]
    [string]$SourcePath = "G:\CavesofQud-decompiledsource",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetsPath = "E:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets",
    
    [Parameter(Mandatory=$false)]
    [string]$ModsPath = "C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods",
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$NoBackup,
    
    [Parameter(Mandatory=$false)]
    [switch]$AnalyzeOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$ListModels,
    
    [Parameter(Mandatory=$false)]
    [switch]$Interactive
)

# Join mod name parts if it was split by spaces
if ($ModName.Count -gt 0) {
    $ModName = $ModName -join " "
} else {
    $ModName = ""
}

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-InteractiveConsole {
    if ($env:CI -eq "true" -or $env:CI -eq "1") { return $false }
    if ($env:TF_BUILD -eq "True") { return $false }
    try {
        return [Environment]::UserInteractive -and $Host.Name -ne "Default Host"
    } catch {
        return $false
    }
}

function Wait-OptionalKeyPress {
    if ($Interactive -and (Test-InteractiveConsole)) {
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}

# Global state for status UI
$script:StatusSpinner = $null
$script:StatusSpinnerActive = $false
$script:StatusMessage = ""
$script:ProgressValue = 0
$script:ProgressMax = 100

# ------------------------------------------------------------
# UI Helper Functions
# ------------------------------------------------------------

function Write-StatusHeader {
    param([string]$Title, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor $Color
    Write-Host ""
}

function Write-SectionHeader {
    param([string]$Title, [string]$Color = "Yellow")
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Color
    Write-Host "  $Title" -ForegroundColor $Color
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Color
    Write-Host ""
}

function Write-Status {
    param(
        [string]$Message,
        [string]$Status = "INFO",
        [string]$Color = "White"
    )
    
    $statusSymbol = switch ($Status) {
        "SUCCESS" { "✓" }
        "ERROR" { "✗" }
        "WARNING" { "⚠" }
        "INFO" { "ℹ" }
        "PROCESSING" { "⟳" }
        default { "•" }
    }
    
    $statusColor = switch ($Status) {
        "SUCCESS" { "Green" }
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "INFO" { "Cyan" }
        "PROCESSING" { "Magenta" }
        default { "Gray" }
    }
    
    Write-Host "  [$statusSymbol] " -NoNewline -ForegroundColor $statusColor
    Write-Host $Message -ForegroundColor $Color
}

function Show-ProgressBar {
    param(
        [int]$Value,
        [int]$Max = 100,
        [string]$Label = "Progress",
        [int]$Width = 40
    )
    
    $percent = [math]::Min(100, [math]::Max(0, [int](($Value / $Max) * 100)))
    $filled = [math]::Floor(($percent / 100) * $Width)
    $empty = $Width - $filled
    
    $bar = "█" * $filled + "░" * $empty
    Write-Host "`r  [$bar] $percent% - $Label" -NoNewline -ForegroundColor Cyan
}

function Start-Spinner {
    param([string]$Message = "Processing...")
    
    if ($script:StatusSpinnerActive) {
        Stop-Spinner
    }
    
    $script:StatusMessage = $Message
    $script:StatusSpinnerActive = $true
    
    $spinnerChars = @('|', '/', '-', '\')
    $spinnerIndex = 0
    
    $script:StatusSpinner = [System.Management.Automation.PowerShell]::Create().AddScript({
        while ($script:StatusSpinnerActive) {
            $char = $spinnerChars[$spinnerIndex % $spinnerChars.Length]
            Write-Host "`r  [$char] $($script:StatusMessage)" -NoNewline -ForegroundColor Magenta
            $script:spinnerIndex++
            Start-Sleep -Milliseconds 100
        }
    })
    
    $script:StatusSpinner.BeginInvoke() | Out-Null
}

function Stop-Spinner {
    if ($script:StatusSpinnerActive) {
        $script:StatusSpinnerActive = $false
        Start-Sleep -Milliseconds 150
        Write-Host "`r" + (" " * 80) -NoNewline
        Write-Host "`r" -NoNewline
    }
}

# ------------------------------------------------------------
# Model Management Functions
# ------------------------------------------------------------

function Get-OllamaModels {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $models = ($response.Content | ConvertFrom-Json).models
            return $models
        }
    } catch {
        return $null
    }
    return $null
}

function Show-ModelMenu {
    param([string]$CurrentModel = "")
    
    Write-StatusHeader "AI Model Selection" "Cyan"
    
    $models = Get-OllamaModels
    if (-not $models -or $models.Count -eq 0) {
        Write-Status "Ollama is not running or no models are available" "ERROR"
        Write-Host ""
        Write-Host "  To install models, run:" -ForegroundColor Gray
        Write-Host "    ollama pull codellama:7b" -ForegroundColor Yellow
        Write-Host "    ollama pull starcoder:7b" -ForegroundColor Yellow
        Write-Host "    ollama pull codellama:34b" -ForegroundColor Yellow
        Write-Host ""
        return $null
    }
    
    # Categorize models
    $codeModels = @()
    $otherModels = @()
    
    foreach ($model in $models) {
        $name = $model.name
        if ($name -match "codellama|starcoder|deepseek|qwen.*code|wizardcoder") {
            $codeModels += $model
        } else {
            $otherModels += $model
        }
    }
    
    Write-Host "  Available Code Models:" -ForegroundColor Cyan
    Write-Host ""
    
    $index = 1
    $menuItems = @()
    
    # Show code models first
    foreach ($model in $codeModels) {
        $name = $model.name
        $size = if ($model.size) { " ($([math]::Round($model.size / 1GB, 2)) GB)" } else { "" }
        $selected = if ($name -eq $CurrentModel) { " ← CURRENT" } else { "" }
        Write-Host "    [$index] $name$size$selected" -ForegroundColor $(if ($name -eq $CurrentModel) { "Green" } else { "White" })
        $menuItems += @{Name = $name; Model = $model}
        $index++
    }
    
    # Show other models
    if ($otherModels.Count -gt 0) {
        Write-Host ""
        Write-Host "  Other Models:" -ForegroundColor Gray
        Write-Host ""
        foreach ($model in $otherModels) {
            $name = $model.name
            $size = if ($model.size) { " ($([math]::Round($model.size / 1GB, 2)) GB)" } else { "" }
            $selected = if ($name -eq $CurrentModel) { " ← CURRENT" } else { "" }
            Write-Host "    [$index] $name$size$selected" -ForegroundColor $(if ($name -eq $CurrentModel) { "Green" } else { "Gray" })
            $menuItems += @{Name = $name; Model = $model}
            $index++
        }
    }
    
    Write-Host ""
    Write-Host "    [0] Use default (auto-select)" -ForegroundColor Yellow
    Write-Host ""

    if (-not (Test-InteractiveConsole)) {
        Write-Status "Non-interactive console: using default (auto-select)" "INFO"
        return ""
    }

    Write-Host "  Select model (0-$($menuItems.Count)): " -NoNewline -ForegroundColor Cyan
    
    $selection = Read-Host
    $selectionNum = [int]::TryParse($selection, [ref]$null) ? [int]$selection : -1
    
    if ($selectionNum -eq 0) {
        return ""
    } elseif ($selectionNum -ge 1 -and $selectionNum -le $menuItems.Count) {
        return $menuItems[$selectionNum - 1].Name
    } else {
        Write-Status "Invalid selection, using default" "WARNING"
        return ""
    }
}

function Show-ModelList {
    Write-StatusHeader "Available Ollama Models" "Cyan"
    
    $models = Get-OllamaModels
    if (-not $models -or $models.Count -eq 0) {
        Write-Status "Ollama is not running or no models are available" "ERROR"
        Write-Host ""
        Write-Host "  Install Ollama from: https://ollama.com" -ForegroundColor Gray
        Write-Host ""
        return
    }
    
    # Categorize models
    $codeModels = @()
    $otherModels = @()
    
    foreach ($model in $models) {
        $name = $model.name
        if ($name -match "codellama|starcoder|deepseek|qwen.*code|wizardcoder") {
            $codeModels += $model
        } else {
            $otherModels += $model
        }
    }
    
    if ($codeModels.Count -gt 0) {
        Write-Host "  Code Models (Recommended):" -ForegroundColor Green
        Write-Host ""
        foreach ($model in $codeModels) {
            $name = $model.name
            $size = if ($model.size) { " - $([math]::Round($model.size / 1GB, 2)) GB" } else { "" }
            $modified = if ($model.modified_at) { 
                $date = [DateTimeOffset]::FromUnixTimeSeconds($model.modified_at).LocalDateTime
                " - Modified: $($date.ToString('yyyy-MM-dd HH:mm'))"
            } else { "" }
            Write-Host "    • $name$size$modified" -ForegroundColor White
        }
        Write-Host ""
    }
    
    if ($otherModels.Count -gt 0) {
        Write-Host "  Other Models:" -ForegroundColor Gray
        Write-Host ""
        foreach ($model in $otherModels) {
            $name = $model.name
            $size = if ($model.size) { " - $([math]::Round($model.size / 1GB, 2)) GB" } else { "" }
            $modified = if ($model.modified_at) { 
                $date = [DateTimeOffset]::FromUnixTimeSeconds($model.modified_at).LocalDateTime
                " - Modified: $($date.ToString('yyyy-MM-dd HH:mm'))"
            } else { "" }
            Write-Host "    • $name$size$modified" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    Write-Status "Total models: $($models.Count)" "INFO"
}

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

function Find-Python {
    # Try python3 first
    $python = Get-Command "python3" -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    
    # Try python
    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    
    # Try common paths
    $commonPaths = @(
        "${env:ProgramFiles}\Python*",
        "${env:LocalAppData}\Programs\Python\Python*"
    )
    
    foreach ($pathPattern in $commonPaths) {
        $pythonDirs = Get-ChildItem -Path $pathPattern -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        
        foreach ($dir in $pythonDirs) {
            $pythonExe = Join-Path $dir.FullName "python.exe"
            if (Test-Path $pythonExe) {
                return $pythonExe
            }
        }
    }
    
    return $null
}

# ------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------

Clear-Host
Write-StatusHeader "Caves of Qud Mod Fixer" "Cyan"

# Handle ListModels parameter
if ($ListModels) {
    Show-ModelList
    exit 0
}

# Find Python
Write-Status "Detecting Python..." "PROCESSING"
$pythonExe = Find-Python
if (-not $pythonExe) {
    Write-Status "Python not found. Please install Python 3.7+ and ensure it's in PATH." "ERROR"
    exit 1
}

Write-Status "Found: $pythonExe" "SUCCESS"

# Check Python version
$pythonVersion = & $pythonExe --version 2>&1
Write-Status "Version: $pythonVersion" "INFO"
Write-Host ""

# Check if required packages are installed
Write-Status "Checking dependencies..." "PROCESSING"
$requiredPackages = @("psutil", "requests")
$missingPackages = @()

foreach ($package in $requiredPackages) {
    $checkCmd = "import $package; print('OK')"
    $result = & $pythonExe -c $checkCmd 2>&1
    if ($LASTEXITCODE -ne 0 -or $result -notmatch "OK") {
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Status "Missing packages: $($missingPackages -join ', ')" "WARNING"
    Write-Status "Installing missing packages..." "PROCESSING"
    foreach ($package in $missingPackages) {
        & $pythonExe -m pip install $package --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Installed $package" "SUCCESS"
        } else {
            Write-Status "Failed to install $package" "ERROR"
            exit 1
        }
    }
} else {
    Write-Status "All dependencies available" "SUCCESS"
}
Write-Host ""

# Check Ollama connection and models
Write-Status "Checking Ollama connection..." "PROCESSING"
$ollamaAvailable = $false
$availableModels = @()
$currentModel = ""

try {
    $ollamaResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    if ($ollamaResponse.StatusCode -eq 200) {
        $ollamaAvailable = $true
        Write-Status "Ollama is running" "SUCCESS"
        
        $models = ($ollamaResponse.Content | ConvertFrom-Json).models
        $availableModels = $models
        
        # Check for recommended code models
        $codeModels = $models | Where-Object { $_.name -match "codellama|starcoder" }
        if ($codeModels) {
            $modelNames = ($codeModels | ForEach-Object { $_.name }) -join ", "
            Write-Status "Code models found: $modelNames" "SUCCESS"
        } else {
            Write-Status "No recommended code models found. Install with: ollama pull codellama:7b" "WARNING"
        }
    }
} catch {
    Write-Status "Ollama not running or not accessible" "WARNING"
    Write-Host "    Install from: https://ollama.com" -ForegroundColor Gray
    Write-Host "    Then run: ollama pull codellama" -ForegroundColor Gray
}
Write-Host ""

# Model selection
if ($Interactive -and (Test-InteractiveConsole)) {
    if ($ollamaAvailable) {
        $selectedModel = Show-ModelMenu -CurrentModel $Model
        if ($null -ne $selectedModel) {
            $Model = $selectedModel
        }
    }
} elseif ([string]::IsNullOrWhiteSpace($Model)) {
    Write-Status "Using default model (auto-select)" "INFO"
}

if (-not [string]::IsNullOrWhiteSpace($Model)) {
    Write-Status "Selected model: $Model" "INFO"
}

# Validate paths
Write-Status "Validating paths..." "PROCESSING"
$pathErrors = @()
if (-not (Test-Path $SourcePath)) {
    Write-Status "Source path does not exist: $SourcePath" "WARNING"
}
if (-not (Test-Path $AssetsPath)) {
    Write-Status "Assets path does not exist: $AssetsPath" "WARNING"
}
if (-not (Test-Path $ModsPath)) {
    Write-Status "Mods path does not exist: $ModsPath" "ERROR"
    exit 1
}
Write-Status "Source: $SourcePath" "INFO"
Write-Status "Assets: $AssetsPath" "INFO"
Write-Status "Mods: $ModsPath" "INFO"
Write-Host ""

# Prepare script path
$fixerScript = Join-Path $PSScriptRoot "qud_mod_fixer.py"
if (-not (Test-Path $fixerScript)) {
    Write-Status "qud_mod_fixer.py not found at: $fixerScript" "ERROR"
    exit 1
}

# Build Python command arguments
$pythonArgs = @(
    $fixerScript,
    "--source", $SourcePath,
    "--assets", $AssetsPath,
    "--mods", $ModsPath
)

# Add model parameter if specified
if (-not [string]::IsNullOrWhiteSpace($Model)) {
    $pythonArgs += "--model", $Model
}

# Note: --no-backup is accepted but ignored - backups are always created for safety
if ($NoBackup) {
    Write-Status "Note: Backups are always created for safety (--no-backup ignored)" "WARNING"
}

if ($AnalyzeOnly) {
    $pythonArgs += "--analyze-only"
}

if (-not [string]::IsNullOrWhiteSpace($ModName)) {
    # Add mod name as a single argument (Python script handles spaces)
    $pythonArgs += $ModName
}

Write-SectionHeader "Starting Mod Fixer" "Cyan"
Write-Host ""

# Function to parse and enhance Python output
function Format-PythonOutput {
    param([string]$line)
    
    # Patterns to detect and enhance
    if ($line -match "SELECTED MODS TO PROCESS: (\d+) mod\(s\)") {
        $count = $matches[1]
        Write-SectionHeader "SELECTED MODS TO PROCESS: $count mod(s)" "Cyan"
        return
    }
    
    if ($line -match "\[(\d+)/(\d+)\]\s+Processing:\s+(.+)") {
        $current = $matches[1]
        $total = $matches[2]
        $modName = $matches[3]
        Write-SectionHeader "MOD $current of $total : $modName" "Yellow"
        return
    }
    
    if ($line -match "Analyzing mod:\s+(.+)") {
        Write-SectionHeader "ANALYZING MOD: $($matches[1])" "Cyan"
        return
    }
    
    if ($line -match "Fixing mod:\s+(.+)") {
        Write-SectionHeader "FIXING MOD: $($matches[1])" "Yellow"
        return
    }
    
    if ($line -match "Found (\d+) API issues") {
        $count = $matches[1]
        Write-Status "Found $count API compatibility issue(s)" "WARNING"
        Write-Host "         These need to be updated to match the current game API" -ForegroundColor Gray
        return
    }
    
    if ($line -match "Found (\d+) asset issues") {
        $count = $matches[1]
        Write-Status "Found $count asset reference issue(s)" "WARNING"
        Write-Host "         These assets may be missing or have incorrect paths" -ForegroundColor Gray
        return
    }
    
    if ($line -match "Fixing (\d+) asset reference issues") {
        $count = $matches[1]
        Write-Host ""
        Write-Status "FIXING ASSET REFERENCES" "PROCESSING"
        Write-Host "  Why: Asset paths may be broken or point to non-existent files" -ForegroundColor Gray
        Write-Host "  How: Using AI to locate correct asset paths in StreamingAssets" -ForegroundColor Gray
        Write-Host ""
        return
    }
    
    if ($line -match "Fixing (\d+) API issues") {
        $count = $matches[1]
        Write-Host ""
        Write-Status "FIXING API ISSUES" "PROCESSING"
        Write-Host "  Why: API calls may be outdated or incompatible with current game version" -ForegroundColor Gray
        Write-Host "  How: Using AI to update API calls to match decompiled source code" -ForegroundColor Gray
        Write-Host ""
        return
    }
    
    if ($line -match "Processing (\d+) files with (\d+) workers") {
        $fileCount = $matches[1]
        $workerCount = $matches[2]
        Write-Status "Processing $fileCount file(s) in parallel with $workerCount worker(s)..." "PROCESSING"
        return
    }
    
    if ($line -match "\[MODEL (ROUTING|SWAP)\]\s+(.+)") {
        $action = $matches[1]
        $message = $matches[2]
        $status = if ($action -eq "SWAP") { "PROCESSING" } else { "INFO" }
        Write-Status "[MODEL $action] $message" $status
        return
    }
    
    if ($line -match "Fixing asset references in (.+\.cs)") {
        $fileName = $matches[1]
        Write-Host ""
        Write-Status "FILE: $fileName" "INFO"
        Write-Status "TASK: Fixing asset references" "PROCESSING"
        Write-Host "  [WHY]  File contains references to assets that may not exist" -ForegroundColor Gray
        Write-Host "  [HOW]  Analyzing asset paths and correcting them using AI..." -ForegroundColor Gray
        return
    }
    
    if ($line -match "Fixing API issues in (.+\.cs)") {
        $fileName = $matches[1]
        Write-Host ""
        Write-Status "FILE: $fileName" "INFO"
        Write-Status "TASK: Fixing API compatibility issues" "PROCESSING"
        Write-Host "  [WHY]  File uses API calls that may be outdated or incompatible" -ForegroundColor Gray
        Write-Host "  [HOW]  Updating API calls to match current game version using AI..." -ForegroundColor Gray
        return
    }
    
    if ($line -match "Applied (\d+) changes to (.+\.cs)") {
        $changeCount = $matches[1]
        $fileName = $matches[2]
        Write-Status "Applied $changeCount change(s) to $fileName" "SUCCESS"
        return
    }
    
    if ($line -match "No changes suggested by AI for (.+\.cs)") {
        $fileName = $matches[1]
        Write-Status "No changes needed for $fileName (file is already correct)" "INFO"
        return
    }
    
    if ($line -match "Error getting AI fix for (.+\.cs):\s+(.+)") {
        $fileName = $matches[1]
        $errorMsg = $matches[2]
        Write-Status "Failed to fix $fileName : $errorMsg" "ERROR"
        return
    }
    
    if ($line -match "Exception processing (.+\.cs):\s+(.+)") {
        $fileName = $matches[1]
        $errorMsg = $matches[2]
        Write-Status "Exception while processing $fileName : $errorMsg" "ERROR"
        return
    }
    
    if ($line -match "Creating backup before making changes") {
        Write-Status "Creating backup of mod before making changes..." "PROCESSING"
        Write-Host "  [WHY]    Backups are kept in case AI makes mistakes" -ForegroundColor Gray
        return
    }
    
    if ($line -match "Backup created:\s+(.+)") {
        $backupName = $matches[1]
        Write-Status "Backup created: $backupName" "SUCCESS"
        return
    }
    
    if ($line -match "Backup available at:\s+(.+)") {
        $backupName = $matches[1]
        Write-Status "Backup available at: $backupName" "SUCCESS"
        return
    }
    
    if ($line -match "Skipping (.+)") {
        $modName = $matches[1]
        Write-Status "Skipping $modName" "WARNING"
        return
    }
    
    if ($line -match "No issues found in (.+)\. Skipping") {
        $modName = $matches[1]
        Write-Status "No issues found in $modName" "INFO"
        return
    }
    
    # Default: pass through the line as-is
    if ($line.Trim() -ne "") {
        Write-Host $line
    }
}

try {
    # Use a simpler approach: capture output and process it line by line
    $output = & $pythonExe $pythonArgs 2>&1
    
    # Process each line of output
    foreach ($line in $output) {
        if ($line -is [System.Management.Automation.ErrorRecord]) {
            Write-Status $line.ToString() "ERROR"
        } else {
            Format-PythonOutput -line $line.ToString()
        }
    }
    
    # Check exit code
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-StatusHeader "Mod Fixing Complete!" "Green"
        Write-Host ""
        Wait-OptionalKeyPress
    } else {
        Write-Host ""
        Write-StatusHeader "Mod Fixing Failed" "Red"
        Write-Status "Exit code: $LASTEXITCODE" "ERROR"
        Write-Host ""
        Wait-OptionalKeyPress
        exit 1
    }
}
catch {
    Write-Host ""
    Write-StatusHeader "Error Running Mod Fixer" "Red"
    Write-Status $_ "ERROR"
    exit 1
}
