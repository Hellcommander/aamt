<#
.SYNOPSIS
    Toolset Integration Helper Module for AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Provides helper functions for game-specific toolsets to easily integrate
    with AAMT tools (Ollama, Stable Diffusion, ImageMagick, Blender, etc.).
    
    This module makes it easy for any toolset to:
    - Check for available tools
    - Use tools when available
    - Provide helpful messages when tools are missing
    - Gracefully degrade functionality
#>

# Import dependencies
$toolDetectionPath = Join-Path $PSScriptRoot "ToolDetection.psm1"
if (Test-Path $toolDetectionPath) {
    Import-Module $toolDetectionPath -ErrorAction SilentlyContinue
}

# ============================================================
# TOOLSET INTEGRATION HELPERS
# ============================================================

function Initialize-ToolsetTools {
    <#
    .SYNOPSIS
    Initializes and checks available tools for a toolset.
    
    .DESCRIPTION
    Checks for available tools and returns a status object that toolsets can use
    to determine what functionality is available.
    
    .PARAMETER RequiredTools
    Array of tool names that are required for this toolset.
    
    .PARAMETER OptionalTools
    Array of tool names that are optional but enhance functionality.
    
    .EXAMPLE
    $tools = Initialize-ToolsetTools -RequiredTools @("ImageMagick") -OptionalTools @("Ollama", "Blender")
    if ($tools.ImageMagick.Available) {
        # Use ImageMagick
    }
    #>
    param(
        [Parameter(Mandatory=$false)]
        [string[]]$RequiredTools = @(),
        
        [Parameter(Mandatory=$false)]
        [string[]]$OptionalTools = @()
    )
    
    $status = @{
        Tools = @{}
        MissingRequired = @()
        MissingOptional = @()
        AllRequiredAvailable = $true
    }
    
    # Check required tools
    foreach ($tool in $RequiredTools) {
        $info = Get-ToolInfo -ToolName $tool
        $status.Tools[$tool] = $info
        
        if (-not $info.Available) {
            $status.MissingRequired += $tool
            $status.AllRequiredAvailable = $false
        }
    }
    
    # Check optional tools
    foreach ($tool in $OptionalTools) {
        $info = Get-ToolInfo -ToolName $tool
        $status.Tools[$tool] = $info
        
        if (-not $info.Available) {
            $status.MissingOptional += $tool
        }
    }
    
    return $status
}

function Show-ToolsetStatus {
    <#
    .SYNOPSIS
    Shows a formatted status of tools for the current toolset.
    
    .PARAMETER ToolsetName
    Name of the toolset (e.g., "Starbound", "Elin", "Qud")
    
    .PARAMETER RequiredTools
    Array of required tool names
    
    .PARAMETER OptionalTools
    Array of optional tool names
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ToolsetName,
        
        [Parameter(Mandatory=$false)]
        [string[]]$RequiredTools = @(),
        
        [Parameter(Mandatory=$false)]
        [string[]]$OptionalTools = @()
    )
    
    Write-Host "`n=== $ToolsetName Toolset - Tool Status ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Check required tools
    if ($RequiredTools.Count -gt 0) {
        Write-Host "Required Tools:" -ForegroundColor Yellow
        foreach ($tool in $RequiredTools) {
            $info = Get-ToolInfo -ToolName $tool
            $status = if ($info.Available) { "✅ Available" } else { "❌ Missing (Required)" }
            $color = if ($info.Available) { "Green" } else { "Red" }
            
            Write-Host "  ${tool}: " -NoNewline
            Write-Host $status -ForegroundColor $color
            
            if (-not $info.Available) {
                Write-Host "    → $($info.InstallationHint)" -ForegroundColor Yellow
            }
        }
        Write-Host ""
    }
    
    # Check optional tools
    if ($OptionalTools.Count -gt 0) {
        Write-Host "Optional Tools (Enhance Functionality):" -ForegroundColor Gray
        foreach ($tool in $OptionalTools) {
            $info = Get-ToolInfo -ToolName $tool
            $status = if ($info.Available) { "✅ Available" } else { "⚠️  Not Available" }
            $color = if ($info.Available) { "Green" } else { "Yellow" }
            
            Write-Host "  ${tool}: " -NoNewline
            Write-Host $status -ForegroundColor $color
        }
        Write-Host ""
    }
}

function Use-ImageMagickIfAvailable {
    <#
    .SYNOPSIS
    Executes ImageMagick command if available, otherwise returns $false.
    
    .PARAMETER Arguments
    Array of arguments to pass to ImageMagick
    
    .PARAMETER InputPath
    Input file path
    
    .PARAMETER OutputPath
    Output file path
    
    .OUTPUTS
    Boolean indicating if ImageMagick was used successfully
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments,
        
        [Parameter(Mandatory=$false)]
        [string]$InputPath,
        
        [Parameter(Mandatory=$false)]
        [string]$OutputPath
    )
    
    if (-not (Test-ImageMagickAvailable)) {
        Write-Warning "ImageMagick not available. Skipping image processing."
        return $false
    }
    
    $magickPath = Get-ImageMagickPath
    if (-not $magickPath) {
        return $false
    }
    
    try {
        & $magickPath $Arguments
        return $LASTEXITCODE -eq 0
    } catch {
        Write-Error "ImageMagick execution failed: $_"
        return $false
    }
}

function Use-BlenderIfAvailable {
    <#
    .SYNOPSIS
    Executes Blender command if available, otherwise returns $false.
    
    .PARAMETER Arguments
    Array of arguments to pass to Blender
    
    .OUTPUTS
    Boolean indicating if Blender was used successfully
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments
    )
    
    if (-not (Test-BlenderAvailable)) {
        Write-Warning "Blender not available. Cannot perform 3D operations."
        return $false
    }
    
    $blenderPath = Get-BlenderPath
    if (-not $blenderPath) {
        return $false
    }
    
    try {
        & $blenderPath $Arguments
        return $LASTEXITCODE -eq 0
    } catch {
        Write-Error "Blender execution failed: $_"
        return $false
    }
}

function Use-PythonIfAvailable {
    <#
    .SYNOPSIS
    Executes Python script if available, otherwise returns $false.
    
    .PARAMETER ScriptPath
    Path to Python script
    
    .PARAMETER Arguments
    Array of arguments to pass to Python script
    
    .OUTPUTS
    Boolean indicating if Python was used successfully
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ScriptPath,
        
        [Parameter(Mandatory=$false)]
        [string[]]$Arguments = @()
    )
    
    if (-not (Test-PythonAvailable)) {
        Write-Warning "Python not available. Cannot execute Python scripts."
        return $false
    }
    
    $pythonPath = Get-PythonPath
    if (-not $pythonPath) {
        return $false
    }
    
    if (-not (Test-Path $ScriptPath)) {
        Write-Error "Python script not found: $ScriptPath"
        return $false
    }
    
    try {
        & $pythonPath $ScriptPath $Arguments
        return $LASTEXITCODE -eq 0
    } catch {
        Write-Error "Python execution failed: $_"
        return $false
    }
}

function Use-OllamaIfAvailable {
    <#
    .SYNOPSIS
    Uses Ollama if available by importing the integration module.
    
    .OUTPUTS
    Boolean indicating if Ollama integration is available
    #>
    if (-not (Test-OllamaAvailable)) {
        Write-Warning "Ollama not available. AI assistance features will be disabled."
        return $false
    }
    
    # Try to import Ollama integration module
    $ollamaModulePath = Join-Path $PSScriptRoot "OllamaIntegration.psm1"
    if (Test-Path $ollamaModulePath) {
        try {
            Import-Module $ollamaModulePath -ErrorAction SilentlyContinue
            return $true
        } catch {
            Write-Warning "Ollama module found but could not be imported: $_"
            return $false
        }
    }
    
    return $false
}

function Use-StableDiffusionIfAvailable {
    <#
    .SYNOPSIS
    Uses Stable Diffusion if available by importing the integration module.
    
    .OUTPUTS
    Boolean indicating if Stable Diffusion integration is available
    #>
    if (-not (Test-StableDiffusionAvailable)) {
        Write-Warning "Stable Diffusion not available. Image generation features will be disabled."
        return $false
    }
    
    # Try to import Stable Diffusion integration module
    $sdModulePath = Join-Path $PSScriptRoot "StableDiffusionIntegration.psm1"
    if (Test-Path $sdModulePath) {
        try {
            # Suppress warning about unapproved verb "Generate" - this is expected and harmless
            Import-Module $sdModulePath -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            return $true
        } catch {
            Write-Warning "Stable Diffusion module found but could not be imported: $_"
            return $false
        }
    }
    
    return $false
}

# ============================================================
# EXPORT MODULE MEMBERS
# ============================================================

Export-ModuleMember -Function `
    Initialize-ToolsetTools,
    Show-ToolsetStatus,
    Use-ImageMagickIfAvailable,
    Use-BlenderIfAvailable,
    Use-PythonIfAvailable,
    Use-OllamaIfAvailable,
    Use-StableDiffusionIfAvailable
