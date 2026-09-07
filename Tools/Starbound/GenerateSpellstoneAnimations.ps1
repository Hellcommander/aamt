#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generates OpenStarbound animation JSON files for spellstone assets.
    
.DESCRIPTION
    Creates animation definitions for spellstones with pulsing, swirling, and glow effects.
    Supports different animation types based on spellform and spellshape combinations.
    
.PARAMETER AssetName
    Base name of the spellstone asset
    
.PARAMETER AnimationType
    Type of animation: pulse, swirl, glow, or "all"
    
.PARAMETER FrameCount
    Number of animation frames (default: 8)
    
.PARAMETER CycleDuration
    Animation cycle duration in seconds (default: 2.0)
    
.PARAMETER OutputDir
    Output directory for animation files
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$AssetName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("pulse", "swirl", "glow", "all")]
    [string]$AnimationType = "all",
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 8,
    
    [Parameter(Mandatory=$false)]
    [double]$CycleDuration = 2.0,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\animations\spellstones"
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$animations = @{}

# Pulse animation (glow intensity pulsing)
if ($AnimationType -eq "all" -or $AnimationType -eq "pulse") {
    $pulseAnimation = @{
        animatedParts = @{
            stateTypes = @{
                idle = @{
                    default = "pulsing"
                    states = @{
                        pulsing = @{
                            frames = $FrameCount
                            cycle = $CycleDuration
                            mode = "loop"
                        }
                    }
                }
            }
            parts = @{
                core = @{
                    properties = @{
                        zLevel = 0
                        centered = $true
                        image = "/items/spellstones/$AssetName.png"
                        offset = @(0, 0)
                    }
                    partStates = @{
                        idle = @{
                            pulsing = @{
                                properties = @{}
                            }
                        }
                    }
                }
            }
        }
        sounds = @{}
    }
    
    # Add frame-specific properties for pulsing effect
    for ($i = 0; $i -lt $FrameCount; $i++) {
        $progress = $i / $FrameCount
        $scale = 0.95 + (0.1 * [Math]::Sin($progress * 2 * [Math]::PI))
        $opacity = 0.8 + (0.2 * [Math]::Sin($progress * 2 * [Math]::PI))
        
        $frameName = "frame$($i.ToString('00'))"
        $pulseAnimation.animatedParts.parts.core.partStates.idle.pulsing[$frameName] = @{
            properties = @{
                scale = @($scale, $scale)
                opacity = $opacity
            }
        }
    }
    
    $animations["pulse"] = $pulseAnimation
}

# Swirl animation (energy patterns swirling)
if ($AnimationType -eq "all" -or $AnimationType -eq "swirl") {
    $swirlAnimation = @{
        animatedParts = @{
            stateTypes = @{
                idle = @{
                    default = "swirling"
                    states = @{
                        swirling = @{
                            frames = $FrameCount
                            cycle = $CycleDuration
                            mode = "loop"
                        }
                    }
                }
            }
            parts = @{
                core = @{
                    properties = @{
                        zLevel = 0
                        centered = $true
                        image = "/items/spellstones/$AssetName.png"
                        offset = @(0, 0)
                    }
                    partStates = @{
                        idle = @{
                            swirling = @{
                                properties = @{}
                            }
                        }
                    }
                }
                energyPattern = @{
                    properties = @{
                        zLevel = 1
                        centered = $true
                        image = "/items/spellstones/${AssetName}_energy.png"
                        offset = @(0, 0)
                        fullbright = $true
                    }
                    partStates = @{
                        idle = @{
                            swirling = @{
                                properties = @{}
                            }
                        }
                    }
                }
            }
        }
        sounds = @{}
    }
    
    # Add rotation for swirling effect
    for ($i = 0; $i -lt $FrameCount; $i++) {
        $progress = $i / $FrameCount
        $rotation = $progress * 360
        
        $frameName = "frame$($i.ToString('00'))"
        $swirlAnimation.animatedParts.parts.energyPattern.partStates.idle.swirling[$frameName] = @{
            properties = @{
                rotation = $rotation
            }
        }
    }
    
    $animations["swirl"] = $swirlAnimation
}

# Glow animation (intensity pulsing with color shifts)
if ($AnimationType -eq "all" -or $AnimationType -eq "glow") {
    $glowAnimation = @{
        animatedParts = @{
            stateTypes = @{
                idle = @{
                    default = "glowing"
                    states = @{
                        glowing = @{
                            frames = $FrameCount
                            cycle = $CycleDuration
                            mode = "loop"
                        }
                    }
                }
            }
            parts = @{
                core = @{
                    properties = @{
                        zLevel = 0
                        centered = $true
                        image = "/items/spellstones/$AssetName.png"
                        offset = @(0, 0)
                    }
                    partStates = @{
                        idle = @{
                            glowing = @{
                                properties = @{}
                            }
                        }
                    }
                }
                glow = @{
                    properties = @{
                        zLevel = 1
                        centered = $true
                        image = "/items/spellstones/${AssetName}_glow.png"
                        offset = @(0, 0)
                        fullbright = $true
                    }
                    partStates = @{
                        idle = @{
                            glowing = @{
                                properties = @{}
                            }
                        }
                    }
                }
            }
        }
        sounds = @{}
    }
    
    # Add glow intensity variation
    for ($i = 0; $i -lt $FrameCount; $i++) {
        $progress = $i / $FrameCount
        $opacity = 0.5 + (0.5 * [Math]::Sin($progress * 2 * [Math]::PI))
        $scale = 1.0 + (0.15 * [Math]::Sin($progress * 2 * [Math]::PI))
        
        $frameName = "frame$($i.ToString('00'))"
        $glowAnimation.animatedParts.parts.glow.partStates.idle.glowing[$frameName] = @{
            properties = @{
                opacity = $opacity
                scale = @($scale, $scale)
            }
        }
    }
    
    $animations["glow"] = $glowAnimation
}

# Write animation files
foreach ($animType in $animations.Keys) {
    # Validate $OutputDir before Join-Path
    $outputPath = Join-Path $OutputDir "${AssetName}_${animType}.animation"
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
        Write-Host "  [FAIL] outputPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($outputPath)) {
        Write-Host "  [FAIL] outputPath is null (${OutputDir}: '${OutputDir}')" -ForegroundColor Red
        continue
    }
    
    $json = $animations[$animType] | ConvertTo-Json -Depth 10
    
    # Fix JSON formatting for OpenStarbound (remove quotes from numeric values in arrays)
    $json = $json -replace '"(\d+)"', '$1'
    
    [System.IO.File]::WriteAllText($outputPath, $json, [System.Text.UTF8Encoding]::new($false))
    
    Write-Host "✓ Generated animation: $outputPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Animation generation complete!" -ForegroundColor Cyan
