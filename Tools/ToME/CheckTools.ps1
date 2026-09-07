# CheckTools.ps1
# AI-Assisted Modding Tools (AAMT) - ToME Toolset
# PowerShell helper script for Python scripts to check tool availability

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Ollama", "Python", "ImageMagick", "Blender", "StableDiffusion", "All")]
    [string]$Tool = "All",
    
    [Parameter(Mandatory=$false)]
    [switch]$Json
)

# Import unified tool detection
$sharedPath = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue

if ($Json) {
    # Output JSON for Python scripts to parse
    $status = Get-AllToolsStatus
    $status | ConvertTo-Json -Depth 3
} else {
    # Output human-readable status
    Show-ToolsStatus
}

# Exit with error code if specific tool is not available
if ($Tool -ne "All") {
    $available = Test-ToolAvailable -ToolName $Tool
    if (-not $available) {
        exit 1
    }
}
