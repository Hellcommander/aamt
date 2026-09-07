<#
.SYNOPSIS
    Unified Tool Detection and Integration Module for AI-Assisted Modding Tools (AAMT)
    
.DESCRIPTION
    Provides unified detection and integration for all AAMT dependencies:
    - Ollama (AI assistance)
    - Stable Diffusion 3 (image generation)
    - ImageMagick (image post-processing)
    - Blender (3D asset generation)
    - Python (core runtime)
    
    All game-specific toolsets can use this module to detect and utilize available tools.
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:ToolCache = @{
    Ollama = $null
    StableDiffusion = $null
    ImageMagick = $null
    Blender = $null
    Python = $null
    LastCheck = $null
    CacheTimeoutMinutes = 5
}

# Common installation paths
$script:CommonPaths = @{
    ImageMagick = @(
        "E:\tools\ImageMagick\magick.exe",
        "D:\tools\ImageMagick\magick.exe",
        "C:\tools\ImageMagick\magick.exe",
        "${env:ProgramFiles}\ImageMagick-*\magick.exe"
    )
    Blender = @(
        "D:\tools\Blender Foundation\Blender*\blender.exe",
        "${env:ProgramFiles}\Blender Foundation\Blender*\blender.exe"
    )
    Python = @(
        "${env:ProgramFiles}\Python*\python.exe",
        "${env:LocalAppData}\Programs\Python\Python*\python.exe"
    )
}

# ============================================================
# CORE DETECTION FUNCTIONS
# ============================================================

function Test-ToolAvailable {
    <#
    .SYNOPSIS
    Tests if a tool is available and returns detection result.
    
    .PARAMETER ToolName
    Name of the tool: Ollama, StableDiffusion, ImageMagick, Blender, Python
    
    .EXAMPLE
    Test-ToolAvailable -ToolName "Ollama"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")]
        [string]$ToolName
    )
    
    $result = Get-ToolInfo -ToolName $ToolName
    return $result.Available
}

function Get-ToolInfo {
    <#
    .SYNOPSIS
    Gets detailed information about a tool's availability and configuration.
    
    .PARAMETER ToolName
    Name of the tool to check
    
    .OUTPUTS
    PSCustomObject with Available, Path, Version, and InstallationHint properties
    #>
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")]
        [string]$ToolName
    )
    
    # Check cache first
    $cacheKey = $ToolName
    if ($script:ToolCache[$cacheKey] -and 
        $script:ToolCache.LastCheck -and 
        ((Get-Date) - $script:ToolCache.LastCheck).TotalMinutes -lt $script:ToolCache.CacheTimeoutMinutes) {
        return $script:ToolCache[$cacheKey]
    }
    
    $result = switch ($ToolName) {
        "Ollama" { Get-OllamaInfo }
        "StableDiffusion" { Get-StableDiffusionInfo }
        "ImageMagick" { Get-ImageMagickInfo }
        "Blender" { Get-BlenderInfo }
        "Python" { Get-PythonInfo }
    }
    
    # Cache result
    $script:ToolCache[$cacheKey] = $result
    $script:ToolCache.LastCheck = Get-Date
    
    return $result
}

function Get-AllToolsStatus {
    <#
    .SYNOPSIS
    Gets status of all tools at once.
    
    .OUTPUTS
    Hashtable with tool names as keys and their status as values
    #>
    $tools = @("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")
    $status = @{}
    
    foreach ($tool in $tools) {
        $info = Get-ToolInfo -ToolName $tool
        $status[$tool] = @{
            Available = $info.Available
            Path = $info.Path
            Version = $info.Version
        }
    }
    
    return $status
}

# ============================================================
# TOOL-SPECIFIC DETECTION
# ============================================================

function Get-OllamaInfo {
    $info = @{
        Available = $false
        Path = $null
        Version = $null
        InstallationHint = "Download from https://ollama.com/download/OllamaSetup.exe"
    }
    
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        $info.Available = $true
        $info.Path = $ollamaCmd.Source
        try {
            $version = & ollama --version 2>&1
            if ($version) {
                $info.Version = $version.ToString().Trim()
            }
        } catch {
            $info.Version = "Unknown"
        }
    }
    
    return $info
}

function Get-StableDiffusionInfo {
    $info = @{
        Available = $false
        Path = $null
        Version = $null
        Url = "http://localhost:1338"
        ApiUrl = "http://localhost:1338/v1/images/generations"
        InstallationHint = "Use Install-CondaAndSetup.ps1 or see SETUP_REQUIRED_TOOLS.md"
    }
    
    # Check if server is running
    try {
        $response = Invoke-WebRequest -Uri "$($info.Url)/ping" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $info.Available = $true
            $info.Version = "Running"
        }
    } catch {
        # Server not running, but might be installable
        $info.InstallationHint = "Server not running. Start with: .\Start-StableDiffusionServer.ps1"
    }
    
    # Check if Python module is available
    if (-not $info.Available) {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            try {
                $testResult = & python -m stable_diffusion_api_server --help 2>&1
                if ($LASTEXITCODE -eq 0 -or ($testResult -notmatch "No module named")) {
                    $info.Available = $true
                    $info.Path = "Python module"
                    $info.Version = "Installed (not running)"
                }
            } catch {
                # Module not found
            }
        }
    }
    
    return $info
}

function Get-ImageMagickInfo {
    $info = @{
        Available = $false
        Path = $null
        Version = $null
        InstallationHint = "Download from https://imagemagick.org/script/download.php#windows"
    }
    
    # Check PATH first
    $magickCmd = Get-Command magick -ErrorAction SilentlyContinue
    if ($magickCmd) {
        $info.Available = $true
        $info.Path = $magickCmd.Source
        try {
            $version = & magick --version 2>&1 | Select-Object -First 1
            if ($version) {
                $info.Version = $version.ToString().Trim()
            }
        } catch {
            $info.Version = "Unknown"
        }
        return $info
    }
    
    # Check common paths
    foreach ($pathPattern in $script:CommonPaths.ImageMagick) {
        $resolvedPaths = Resolve-Path $pathPattern -ErrorAction SilentlyContinue
        foreach ($resolvedPath in $resolvedPaths) {
            if (Test-Path $resolvedPath) {
                $info.Available = $true
                $info.Path = $resolvedPath.Path
                try {
                    $version = & $resolvedPath.Path --version 2>&1 | Select-Object -First 1
                    if ($version) {
                        $info.Version = $version.ToString().Trim()
                    }
                } catch {
                    $info.Version = "Unknown"
                }
                return $info
            }
        }
    }
    
    return $info
}

function Get-BlenderInfo {
    $info = @{
        Available = $false
        Path = $null
        Version = $null
        InstallationHint = "Download from https://www.blender.org/download/"
    }
    
    # Check environment variables
    $envVars = @("BLENDER_PATH", "BLENDER_DIR", "BLENDER_HOME")
    foreach ($envVar in $envVars) {
        $envPath = [System.Environment]::GetEnvironmentVariable($envVar)
        if (-not [string]::IsNullOrWhiteSpace($envPath) -and (Test-Path $envPath)) {
            $blenderExe = if (Test-Path $envPath -PathType Container) {
                Join-Path $envPath "blender.exe"
            } else {
                $envPath
            }
            if (Test-Path $blenderExe) {
                $info.Available = $true
                $info.Path = $blenderExe
                try {
                    $version = & $blenderExe --version 2>&1 | Select-Object -First 1
                    if ($version) {
                        $info.Version = $version.ToString().Trim()
                    }
                } catch {
                    $info.Version = "Unknown"
                }
                return $info
            }
        }
    }
    
    # Check PATH
    $blenderCmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($blenderCmd) {
        $info.Available = $true
        $info.Path = $blenderCmd.Source
        try {
            $version = & blender --version 2>&1 | Select-Object -First 1
            if ($version) {
                $info.Version = $version.ToString().Trim()
            }
        } catch {
            $info.Version = "Unknown"
        }
        return $info
    }
    
    # Check common paths
    foreach ($pathPattern in $script:CommonPaths.Blender) {
        $resolvedPaths = Resolve-Path $pathPattern -ErrorAction SilentlyContinue
        foreach ($resolvedPath in $resolvedPaths) {
            if (Test-Path $resolvedPath) {
                $info.Available = $true
                $info.Path = $resolvedPath.Path
                try {
                    $version = & $resolvedPath.Path --version 2>&1 | Select-Object -First 1
                    if ($version) {
                        $info.Version = $version.ToString().Trim()
                    }
                } catch {
                    $info.Version = "Unknown"
                }
                return $info
            }
        }
    }
    
    return $info
}

function Get-PythonInfo {
    $info = @{
        Available = $false
        Path = $null
        Version = $null
        InstallationHint = "Download from https://www.python.org/downloads/ (check 'Add Python to PATH')"
    }
    
    # Check python first
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if ($pythonCmd) {
        $info.Available = $true
        $info.Path = $pythonCmd.Source
        try {
            $version = & python --version 2>&1
            if ($version) {
                $info.Version = $version.ToString().Trim()
            }
        } catch {
            try {
                $version = & python3 --version 2>&1
                if ($version) {
                    $info.Version = $version.ToString().Trim()
                }
            } catch {
                $info.Version = "Unknown"
            }
        }
        return $info
    }
    
    # Check common paths
    foreach ($pathPattern in $script:CommonPaths.Python) {
        $resolvedPaths = Resolve-Path $pathPattern -ErrorAction SilentlyContinue
        foreach ($resolvedPath in $resolvedPaths) {
            if (Test-Path $resolvedPath) {
                $info.Available = $true
                $info.Path = $resolvedPath.Path
                try {
                    $version = & $resolvedPath.Path --version 2>&1
                    if ($version) {
                        $info.Version = $version.ToString().Trim()
                    }
                } catch {
                    $info.Version = "Unknown"
                }
                return $info
            }
        }
    }
    
    return $info
}

# ============================================================
# CONVENIENCE FUNCTIONS FOR TOOLSETS
# ============================================================

function Get-ImageMagickPath {
    <#
    .SYNOPSIS
    Gets the path to ImageMagick executable, or $null if not available.
    #>
    $info = Get-ImageMagickInfo
    return $info.Path
}

function Get-BlenderPath {
    <#
    .SYNOPSIS
    Gets the path to Blender executable, or $null if not available.
    #>
    $info = Get-BlenderInfo
    return $info.Path
}

function Get-PythonPath {
    <#
    .SYNOPSIS
    Gets the path to Python executable, or $null if not available.
    #>
    $info = Get-PythonInfo
    return $info.Path
}

function Test-ImageMagickAvailable {
    <#
    .SYNOPSIS
    Quick test if ImageMagick is available.
    #>
    return (Test-ToolAvailable -ToolName "ImageMagick")
}

function Test-BlenderAvailable {
    <#
    .SYNOPSIS
    Quick test if Blender is available.
    #>
    return (Test-ToolAvailable -ToolName "Blender")
}

function Test-PythonAvailable {
    <#
    .SYNOPSIS
    Quick test if Python is available.
    #>
    return (Test-ToolAvailable -ToolName "Python")
}

function Test-OllamaAvailable {
    <#
    .SYNOPSIS
    Quick test if Ollama is available.
    #>
    return (Test-ToolAvailable -ToolName "Ollama")
}

function Test-StableDiffusionAvailable {
    <#
    .SYNOPSIS
    Quick test if Stable Diffusion server is available (running or installable).
    #>
    return (Test-ToolAvailable -ToolName "StableDiffusion")
}

# ============================================================
# REPORTING FUNCTIONS
# ============================================================

function Show-ToolsStatus {
    <#
    .SYNOPSIS
    Displays a formatted status report of all tools.
    #>
    Write-Host "`n=== AI-Assisted Modding Tools (AAMT) - Tool Status ===" -ForegroundColor Cyan
    Write-Host ""
    
    $tools = @("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")
    
    foreach ($tool in $tools) {
        $info = Get-ToolInfo -ToolName $tool
        $status = if ($info.Available) { "✅ Available" } else { "❌ Not Available" }
        $color = if ($info.Available) { "Green" } else { "Red" }
        
        Write-Host "${tool}: " -NoNewline
        Write-Host $status -ForegroundColor $color
        
        if ($info.Available) {
            if ($info.Path) {
                Write-Host "  Path: $($info.Path)" -ForegroundColor Gray
            }
            if ($info.Version) {
                Write-Host "  Version: $($info.Version)" -ForegroundColor Gray
            }
        } else {
            Write-Host "  Hint: $($info.InstallationHint)" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

function Get-MissingTools {
    <#
    .SYNOPSIS
    Returns a list of tools that are not available.
    
    .PARAMETER RequiredTools
    Array of tool names to check. If not specified, checks all tools.
    #>
    param(
        [Parameter(Mandatory=$false)]
        [ValidateSet("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")]
        [string[]]$RequiredTools = @("Ollama", "StableDiffusion", "ImageMagick", "Blender", "Python")
    )
    
    $missing = @()
    foreach ($tool in $RequiredTools) {
        if (-not (Test-ToolAvailable -ToolName $tool)) {
            $missing += $tool
        }
    }
    
    return $missing
}

# ============================================================
# EXPORT MODULE MEMBERS
# ============================================================

Export-ModuleMember -Function `
    Test-ToolAvailable,
    Get-ToolInfo,
    Get-AllToolsStatus,
    Get-ImageMagickPath,
    Get-BlenderPath,
    Get-PythonPath,
    Test-ImageMagickAvailable,
    Test-BlenderAvailable,
    Test-PythonAvailable,
    Test-OllamaAvailable,
    Test-StableDiffusionAvailable,
    Show-ToolsStatus,
    Get-MissingTools
