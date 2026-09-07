# Ollama CPU Offload Module
# Provides functions to get CPU offload settings for Ollama models

function Get-OllamaCpuOffloadOptions {
    <#
    .SYNOPSIS
    Gets Ollama API options with CPU offload configured for high VRAM models.
    
    .DESCRIPTION
    Uses the Ollama Model Router to determine if a model needs CPU offload
    (KV cache in RAM) and returns the appropriate num_gpu setting.
    
    .PARAMETER ModelName
    Name of the Ollama model (e.g., "codellama:13b", "llama3.1:8b")
    
    .PARAMETER NumThread
    Number of CPU threads (optional, will use router defaults if not specified)
    
    .PARAMETER NumPredict
    Maximum tokens to predict (optional)
    
    .PARAMETER Temperature
    Sampling temperature (default: 0.7)
    
    .PARAMETER TopP
    Top-p sampling parameter (default: 0.9)
    
    .PARAMETER NumCtx
    Context window size (optional)
    
    .EXAMPLE
    $options = Get-OllamaCpuOffloadOptions -ModelName "codellama:13b"
    # Returns: @{ num_gpu = 15; temperature = 0.7; top_p = 0.9 }
    
    .EXAMPLE
    $options = Get-OllamaCpuOffloadOptions -ModelName "codellama:7b" -NumThread 8 -NumPredict 2048
    # Returns: @{ num_thread = 8; num_predict = 2048; temperature = 0.7; top_p = 0.9 }
    # (No num_gpu for 7B models - they fit in VRAM)
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModelName,
        
        [int]$NumThread,
        [int]$NumPredict,
        [double]$Temperature = 0.7,
        [double]$TopP = 0.9,
        [int]$NumCtx
    )
    
    $scriptPath = Join-Path $PSScriptRoot "get_ollama_options.py"
    if (-not (Test-Path $scriptPath)) {
        Write-Warning "get_ollama_options.py not found. CPU offload not available."
        return @{
            temperature = $Temperature
            top_p = $TopP
        }
    }
    
    # Build arguments
    $args = @($ModelName)
    if ($NumThread) { $args += $NumThread } else { $args += "" }
    if ($NumPredict) { $args += $NumPredict } else { $args += "" }
    if ($Temperature) { $args += $Temperature } else { $args += "" }
    if ($TopP) { $args += $TopP } else { $args += "" }
    if ($NumCtx) { $args += $NumCtx } else { $args += "" }
    
    try {
        # Call Python helper script
        $jsonOutput = & python $scriptPath $args[0] $args[1] $args[2] $args[3] $args[4] $args[5] 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to get CPU offload options: $jsonOutput"
            return @{
                temperature = $Temperature
                top_p = $TopP
            }
        }
        
        # Parse JSON output
        $options = $jsonOutput | ConvertFrom-Json
        
        # Convert to hashtable
        $result = @{}
        $options.PSObject.Properties | ForEach-Object {
            $result[$_.Name] = $_.Value
        }
        
        return $result
    }
    catch {
        Write-Warning "Error getting CPU offload options: $_"
        return @{
            temperature = $Temperature
            top_p = $TopP
        }
    }
}

function Get-OllamaModelSize {
    <#
    .SYNOIS
    Gets the size of an Ollama model (7b, 8b, 13b, 14b, etc.)
    
    .PARAMETER ModelName
    Name of the Ollama model
    
    .EXAMPLE
    Get-OllamaModelSize -ModelName "codellama:13b"
    # Returns: "13b"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModelName
    )
    
    $nameLower = $ModelName.ToLower()
    
    if ($nameLower -match '14b|:14|-14') { return "14b" }
    if ($nameLower -match '13b|:13|-13') { return "13b" }
    if ($nameLower -match '8b|:8|-8') { return "8b" }
    if ($nameLower -match '7b|:7|-7') { return "7b" }
    
    return $null
}

Export-ModuleMember -Function Get-OllamaCpuOffloadOptions, Get-OllamaModelSize
