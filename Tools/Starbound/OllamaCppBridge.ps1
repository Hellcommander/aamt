# OllamaCppBridge.ps1
# Bridge script for C++ backend to call Ollama
# This can be executed from C++ via system() or Lua os.execute()

param(
    [Parameter(Mandatory=$true)]
    [string]$Action,  # "enhance_description", "extract_parameters", "assess_quality"
    
    [Parameter(Mandatory=$false)]
    [string]$Description = "",
    
    [Parameter(Mandatory=$false)]
    [string]$InputFile = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "qwen2.5-coder:14b"  # Use structured planning model for analysis (deterministic JSON, atlas layouts)
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Check Ollama connection
function Test-OllamaConnection {
    param([string]$Url = "http://localhost:11434")
    try {
        $response = Invoke-RestMethod -Uri "$Url/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Enhance description with Ollama
function Enhance-Description {
    param([string]$Description, [string]$OllamaUrl, [string]$Model)
    
    if (-not (Test-OllamaConnection -Url $OllamaUrl)) {
        Write-Output $Description
        return
    }
    
    try {
        $prompt = @"
You are a game asset designer for Starbound. Enhance this asset description to provide detailed visual guidance for procedural generation:

Original: $Description

Provide an enhanced description with:
- Specific color palette suggestions (RGB values)
- Visual style details (pixel art, shading, outlines)
- Material/texture characteristics
- Size and proportion details
- Thematic elements

Return ONLY the enhanced description, no other text.
"@
        
        $body = @{
            model = $Model
            prompt = $prompt
            stream = $false
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $enhanced = $response.response.Trim()
        if ($enhanced -and $enhanced.Length -gt $Description.Length) {
            Write-Output $enhanced
        } else {
            Write-Output $Description
        }
    } catch {
        Write-Output $Description
    }
}

# Extract parameters from description
function Extract-Parameters {
    param([string]$Description, [string]$OllamaUrl, [string]$Model)
    
    if (-not (Test-OllamaConnection -Url $OllamaUrl)) {
        Write-Output "{}"
        return
    }
    
    try {
        $prompt = @"
Extract visual parameters from this description as JSON:
"$Description"

Return ONLY a JSON object with: colorPalette (array of RGB arrays), style (string), hasGradient (bool), hasPattern (bool), hasSparkles (bool)
"@
        
        $body = @{
            model = $Model
            prompt = $prompt
            stream = $false
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/generate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 30 `
            -ErrorAction Stop
        
        $result = $response.response.Trim()
        # Try to extract JSON
        $jsonStart = $result.IndexOf('{')
        $jsonEnd = $result.LastIndexOf('}') + 1
        if ($jsonStart -ge 0 -and $jsonEnd -gt $jsonStart) {
            Write-Output $result.Substring($jsonStart, $jsonEnd - $jsonStart)
        } else {
            Write-Output "{}"
        }
    } catch {
        Write-Output "{}"
    }
}

# Main execution
switch ($Action) {
    "enhance_description" {
        if ($Description) {
            $enhanced = Enhance-Description -Description $Description -OllamaUrl $OllamaUrl -Model $Model
            if ($OutputFile) {
                Set-Content -Path $OutputFile -Value $enhanced -Encoding UTF8
            } else {
                Write-Output $enhanced
            }
        } elseif ($InputFile -and (Test-Path $InputFile)) {
            $desc = Get-Content -Path $InputFile -Raw -Encoding UTF8
            $enhanced = Enhance-Description -Description $desc -OllamaUrl $OllamaUrl -Model $Model
            if ($OutputFile) {
                Set-Content -Path $OutputFile -Value $enhanced -Encoding UTF8
            } else {
                Write-Output $enhanced
            }
        }
    }
    
    "extract_parameters" {
        if ($Description) {
            $params = Extract-Parameters -Description $Description -OllamaUrl $OllamaUrl -Model $Model
            if ($OutputFile) {
                Set-Content -Path $OutputFile -Value $params -Encoding UTF8
            } else {
                Write-Output $params
            }
        } elseif ($InputFile -and (Test-Path $InputFile)) {
            $desc = Get-Content -Path $InputFile -Raw -Encoding UTF8
            $params = Extract-Parameters -Description $desc -OllamaUrl $OllamaUrl -Model $Model
            if ($OutputFile) {
                Set-Content -Path $OutputFile -Value $params -Encoding UTF8
            } else {
                Write-Output $params
            }
        }
    }
    
    "check_connection" {
        if (Test-OllamaConnection -Url $OllamaUrl) {
            Write-Output "OK"
            exit 0
        } else {
            Write-Output "FAIL"
            exit 1
        }
    }
    
    default {
        Write-Error "Unknown action: $Action"
        exit 1
    }
}
