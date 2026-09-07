# Space Whale Rigging Generator
# Creates bone-driven rigging system for space whale ships

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "space_whale_ship_example.json",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/Rigging",
    
    [Parameter(Mandatory=$false)]
    [int]$SegmentCount = 6,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBlender
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

Write-Host "Space Whale Rigging Generator" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# Check if registry exists
if (-not (Test-Path $RegistryPath)) {
    Write-Host "ERROR: Registry file not found: $RegistryPath" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Load registry
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$ships = $registry.ships

if ($null -eq $ships -or $ships.Count -eq 0) {
    Write-Host "ERROR: No ships found in registry" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($ships.Count) ship(s) in registry" -ForegroundColor Green
Write-Host ""

foreach ($ship in $ships) {
    $shipId = $ship.id
    Write-Host "Processing ship: $shipId" -ForegroundColor Yellow
    
    # Determine segment count from modules
    $modules = $ship.visual.modules
    $segmentCount = $modules.Count
    if ($segmentCount -eq 0) {
        $segmentCount = $SegmentCount
    }
    
    Write-Host "  Segment count: $segmentCount" -ForegroundColor Gray
    
    # Create rigging config
    $rigConfig = @{
        version = "1.0.0"
        shipId = $shipId
        rigging = @{
            spine = @{
                segmentCount = $segmentCount
                segmentLength = 1.0
            }
            fins = @{
                dorsal = @{
                    enabled = $true
                    attachmentBone = "Spine_$([math]::Floor($segmentCount / 2).ToString('00'))"
                }
                pectoral = @{
                    enabled = $true
                    attachmentBone = "Spine_$([math]::Floor($segmentCount / 3).ToString('00'))"
                }
                tail = @{
                    enabled = $true
                    attachmentBone = "Spine_$($segmentCount - 1).ToString('00')"
                }
            }
            gills = @{
                enabled = $true
                count = $ship.visual.animations.gillVentCount
                attachmentBone = "Spine_$([math]::Floor($segmentCount / 2).ToString('00'))"
            }
        }
    }
    
    $rigConfigPath = Join-Path $OutputDir "$shipId`_rig_config.json"
    $rigConfig | ConvertTo-Json -Depth 10 | Set-Content $rigConfigPath
    Write-Host "  Created rig config: $rigConfigPath" -ForegroundColor Gray
    
    if (-not $SkipBlender) {
        # Find Blender executable
        $blenderExe = $null
        
        # Check default location first
        $defaultBlender = "D:\tools\Blender Foundation\Blender 5.0\blender.exe"
        if (Test-Path $defaultBlender) {
            $blenderExe = $defaultBlender
            Write-Host "  Found Blender at default location: $defaultBlender" -ForegroundColor Gray
        } else {
            # Check PATH
            $blenderPath = Get-Command blender -ErrorAction SilentlyContinue
            if ($null -ne $blenderPath) {
                $blenderExe = $blenderPath.Source
                Write-Host "  Found Blender in PATH: $blenderExe" -ForegroundColor Gray
            } else {
                # Check other common locations
                $commonPaths = @(
                    "D:\tools\Blender Foundation\Blender 4.2\blender.exe",
                    "D:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                    "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                    "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
                )
                
                foreach ($path in $commonPaths) {
                    if (Test-Path $path) {
                        $blenderExe = $path
                        Write-Host "  Found Blender at: $path" -ForegroundColor Gray
                        break
                    }
                }
            }
        }
        
        if ($null -eq $blenderExe) {
            Write-Host "  WARNING: Blender not found. Skipping rig generation." -ForegroundColor Yellow
            Write-Host "  Default location checked: D:\tools\Blender Foundation\Blender 5.0\blender.exe" -ForegroundColor Yellow
            Write-Host "  Install Blender and add to PATH, or use --SkipBlender flag" -ForegroundColor Yellow
        } else {
            Write-Host "  Generating rig in Blender..." -ForegroundColor Gray
            
            $blenderScript = "blender_space_whale_rigging.py"
            $outputRigInfo = Join-Path $OutputDir "$shipId`_rig_info.json"
            
            $blenderArgs = @(
                "--background",
                "--python", $blenderScript,
                "--",
                "--config", $RegistryPath,
                "--output", $outputRigInfo,
                "--segment-count", $segmentCount
            )
            
            & $blenderExe $blenderArgs
            
            if (Test-Path $outputRigInfo) {
                Write-Host "  Rig info exported: $outputRigInfo" -ForegroundColor Green
            } else {
                Write-Host "  WARNING: Rig info not generated" -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host ""
}

Write-Host "Rigging generation complete!" -ForegroundColor Green
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan

