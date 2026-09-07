<#
.SYNOPSIS
    Helper functions for path validation in asset generators.
    
.DESCRIPTION
    Provides validation functions to prevent null path errors when using
    Join-Path, New-Item, Test-Path, and other path operations.
#>

function Test-ValidPath {
    <#
    .SYNOPSIS
        Validates that a path variable is not null or empty.
    
    .PARAMETER Path
        The path variable to validate
    
    .PARAMETER VariableName
        The name of the variable (for error messages)
    
    .PARAMETER DefaultValue
        Optional default value to use if path is empty
    
    .EXAMPLE
        if (-not (Test-ValidPath -Path $ModPath -VariableName "ModPath")) {
            exit 1
        }
    #>
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [string]$Path,
        
        [Parameter(Mandatory=$true)]
        [string]$VariableName,
        
        [Parameter(Mandatory=$false)]
        [string]$DefaultValue = $null
    )
    
    if ([string]::IsNullOrWhiteSpace($Path)) {
        if ($DefaultValue) {
            Write-Host "Warning: $VariableName was empty, using default: $DefaultValue" -ForegroundColor Yellow
            Set-Variable -Name $VariableName -Value $DefaultValue -Scope 1
            return $true
        } else {
            Write-Host "Error: $VariableName cannot be null or empty" -ForegroundColor Red
            return $false
        }
    }
    
    return $true
}

function Join-PathSafe {
    <#
    .SYNOPSIS
        Safely joins paths with validation.
    
    .PARAMETER Path
        Base path
    
    .PARAMETER ChildPath
        Child path(s) to join
    
    .EXAMPLE
        $outputDir = Join-PathSafe -Path $ModPath -ChildPath "assets", "sprites"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [string]$Path,
        
        [Parameter(Mandatory=$true)]
        [string[]]$ChildPath
    )
    
    if ([string]::IsNullOrWhiteSpace($Path)) {
        Write-Host "Error: Cannot join paths - base path is null or empty" -ForegroundColor Red
        return $null
    }
    
    $result = $Path
    foreach ($child in $ChildPath) {
        if ([string]::IsNullOrWhiteSpace($child)) {
            Write-Host "Warning: Skipping empty child path component" -ForegroundColor Yellow
            continue
        }
        $result = Join-Path $result $child
    }
    
    return $result
}

function New-DirectorySafe {
    <#
    .SYNOPSIS
        Safely creates a directory with validation.
    
    .PARAMETER Path
        Directory path to create
    
    .PARAMETER Force
        Force creation even if parent doesn't exist
    
    .EXAMPLE
        if (-not (New-DirectorySafe -Path $outputDir)) {
            Write-Host "Failed to create directory" -ForegroundColor Red
        }
    #>
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [string]$Path,
        
        [Parameter(Mandatory=$false)]
        [switch]$Force
    )
    
    if ([string]::IsNullOrWhiteSpace($Path)) {
        Write-Host "Error: Cannot create directory - path is null or empty" -ForegroundColor Red
        return $false
    }
    
    if (Test-Path $Path) {
        return $true
    }
    
    try {
        New-Item -ItemType Directory -Path $Path -Force:$Force | Out-Null
        return $true
    } catch {
        Write-Host "Error: Cannot create directory '$Path': $_" -ForegroundColor Red
        return $false
    }
}

function Get-SafeOutputDir {
    <#
    .SYNOPSIS
        Safely creates an output directory path with validation.
    
    .PARAMETER BasePath
        Base path (e.g., $ModPath)
    
    .PARAMETER SubPath
        Sub-path components to join
    
    .EXAMPLE
        $outputDir = Get-SafeOutputDir -BasePath $ModPath -SubPath "assets", "sprites"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [string]$BasePath,
        
        [Parameter(Mandatory=$true)]
        [string[]]$SubPath
    )
    
    if ([string]::IsNullOrWhiteSpace($BasePath)) {
        Write-Host "Error: BasePath cannot be null or empty" -ForegroundColor Red
        return $null
    }
    
    $result = $BasePath
    foreach ($part in $SubPath) {
        if ([string]::IsNullOrWhiteSpace($part)) {
            Write-Host "Warning: Skipping empty path component" -ForegroundColor Yellow
            continue
        }
        $result = Join-Path $result $part
    }
    
    return $result
}

Export-ModuleMember -Function Test-ValidPath, Join-PathSafe, New-DirectorySafe, Get-SafeOutputDir
