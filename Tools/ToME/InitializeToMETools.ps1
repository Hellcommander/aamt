# InitializeToMETools.ps1
# AI-Assisted Modding Tools (AAMT) - ToME Toolset
# Initializes and validates tools for ToME scripts

param(
    [Parameter(Mandatory=$false)]
    [string[]]$RequiredTools = @("Python"),
    
    [Parameter(Mandatory=$false)]
    [string[]]$OptionalTools = @("Ollama", "ImageMagick")
)

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for ToME
$tools = Initialize-ToolsetTools `
    -RequiredTools $RequiredTools `
    -OptionalTools $OptionalTools

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for ToME scripts" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Tales of Maj'Eyal" `
        -RequiredTools $RequiredTools `
        -OptionalTools $OptionalTools
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    Write-Host "[OK] Ollama integration enabled" -ForegroundColor Green
}

# Export tool status for Python scripts
$script:ToMETools = $tools
$script:PythonPath = Get-PythonPath
$script:OllamaAvailable = $tools.Tools["Ollama"].Available
$script:ImageMagickPath = Get-ImageMagickPath

# Return tool status as hashtable
return @{
    Tools = $tools
    PythonPath = $script:PythonPath
    OllamaAvailable = $script:OllamaAvailable
    ImageMagickPath = $script:ImageMagickPath
    AllRequiredAvailable = $tools.AllRequiredAvailable
}
