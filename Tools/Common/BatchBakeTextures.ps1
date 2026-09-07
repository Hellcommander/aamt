<#
.SYNOPSIS
    Batch bakes multiple textures using Blender texture baker.

.DESCRIPTION
    Processes a list of material descriptions and bakes them to PNG textures.
    Can use predefined material types or JSON definitions from Ollama.

.PARAMETER MaterialList
    Array of material descriptions or file path containing descriptions

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER OutputDir
    Output directory for baked textures

.PARAMETER BlenderPath
    Path to Blender executable (auto-detected if not provided)

.PARAMETER TextureSize
    Size of output textures (default: 512)

.PARAMETER BakePass
    Type of bake pass: DIFFUSE, ROUGHNESS, NORMAL, EMIT, COMBINED

.PARAMETER UseJSON
    Generate JSON material definitions using Ollama instead of predefined types

.EXAMPLE
    .\BatchBakeTextures.ps1 -MaterialList @("wood", "stone", "metal") -OutputDir "Textures"

.EXAMPLE
    .\BatchBakeTextures.ps1 -MaterialList "materials.txt" -UseJSON -OutputDir "Textures"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string[]]$MaterialList,
    
    [string]$OutputDir = "BakedTextures",
    
    [string]$BlenderPath = "",
    
    [int]$TextureSize = 512,
    
    [ValidateSet("DIFFUSE", "ROUGHNESS", "NORMAL", "EMIT", "COMBINED")]
    [string]$BakePass = "DIFFUSE",
    
    [switch]$UseJSON,
    
    [string]$OllamaModel = ""
)

$ErrorActionPreference = "Stop"

# Find Blender
function Find-Blender {
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath) -and (Test-Path $BlenderPath)) {
        return $BlenderPath
    }
    
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        return $blender.Source
    }
    
    $commonPaths = @(
        "D:\tools\Blender Foundation\Blender 5.0\blender.exe",
        "${env:ProgramFiles}\Blender Foundation\Blender *\blender.exe"
    )
    
    foreach ($pathPattern in $commonPaths) {
        $parent = Split-Path $pathPattern -Parent
        if (Test-Path $parent) {
            $matches = Get-ChildItem -Path $parent -Filter (Split-Path $pathPattern -Leaf) -ErrorAction SilentlyContinue
            if ($matches) {
                return $matches[0].FullName
            }
        }
    }
    
    return $null
}

$blenderExe = Find-Blender
if (-not $blenderExe) {
    Write-Host "Error: Blender not found" -ForegroundColor Red
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Batch Texture Baking" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Blender: $blenderExe" -ForegroundColor Green
Write-Host "Output: $OutputDir" -ForegroundColor Gray
Write-Host "Size: ${TextureSize}x${TextureSize}" -ForegroundColor Gray
Write-Host "Pass: $BakePass" -ForegroundColor Gray
Write-Host ""

# Create output directory (ensure absolute path)
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Get material list
$materials = @()
if ($MaterialList.Count -eq 1 -and (Test-Path $MaterialList[0])) {
    # Load from file
    $materials = Get-Content $MaterialList[0] | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
} else {
    $materials = $MaterialList
}

Write-Host "Processing $($materials.Count) material(s)..." -ForegroundColor Cyan
Write-Host ""

$scriptPath = Join-Path $PSScriptRoot "bake_texture.py"
$successCount = 0

foreach ($material in $materials) {
    $material = $material.Trim()
    Write-Host "Baking: $material" -ForegroundColor Cyan
    
    $safeName = ($material -replace '[^\w\s]', '' -replace '\s+', '_').ToLower()
    $outputPath = [System.IO.Path]::GetFullPath((Join-Path $OutputDir "${safeName}.png"))
    
    if ($UseJSON) {
        # Generate JSON using Ollama (if available)
        Write-Host "  Generating JSON definition..." -ForegroundColor Gray
        
        # For now, use material name directly
        # In full implementation, call Ollama to generate JSON
        $jsonPath = Join-Path $env:TEMP "material_${safeName}.json"
        $jsonContent = @{
            name = $material
            noise = @{
                scale = 10.0
            }
            colors = @(
                @(0.3, 0.3, 0.3),
                @(0.7, 0.7, 0.7)
            )
            roughness = 0.5
        } | ConvertTo-Json -Depth 10
        
        [System.IO.File]::WriteAllText($jsonPath, $jsonContent, [System.Text.UTF8Encoding]::new($false))
        
        $blenderArgs = "--background --python `"$scriptPath`" -- --json `"$jsonPath`" --size $TextureSize --output `"$outputPath`" --pass $BakePass"
    } else {
        # Use predefined material type
        $blenderArgs = "--background --python `"$scriptPath`" -- --material `"$material`" --size $TextureSize --output `"$outputPath`" --pass $BakePass"
    }
    
    try {
        $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        
        if ($process.ExitCode -eq 0) {
            # Wait a moment for file system to sync
            Start-Sleep -Milliseconds 500
            
            if (Test-Path $outputPath) {
                $fileSize = (Get-Item $outputPath).Length / 1KB
                Write-Host "  ✓ Baked: $outputPath ($([math]::Round($fileSize, 2)) KB)" -ForegroundColor Green
                $successCount++
            } else {
                Write-Host "  ⚠ Blender completed but file not found: $outputPath" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ✗ Failed (exit code: $($process.ExitCode))" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Batch Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Successfully baked: $successCount/$($materials.Count) textures" -ForegroundColor $(if ($successCount -eq $materials.Count) { "Green" } else { "Yellow" })
Write-Host "Output directory: $OutputDir" -ForegroundColor Gray
Write-Host ""

