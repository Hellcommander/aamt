#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Helper script to create new registry template files.
    
.DESCRIPTION
    Creates a new registry JSON file with a template entry for the specified asset type.
    
.PARAMETER Type
    Asset type: Projectile, Shield, Armor, FX, or Aura
    
.PARAMETER OutputPath
    Output path for the new registry file
    
.PARAMETER AssetId
    ID for the new asset (optional)
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Projectile", "Shield", "Armor", "FX", "Aura")]
    [string]$Type,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$AssetId = "new_asset"
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    Write-Host $Message -ForegroundColor $(switch ($Level) {
        "ERROR" { "Red" }
        "SUCCESS" { "Green" }
        default { "White" }
    })
}

# Template definitions
$templates = @{
    "Projectile" = @{
        version = "1.0.0"
        projectiles = @(
            @{
                id = $AssetId
                type = "Laser"
                quality = "High"
                visual = @{
                    spriteSize = @(32, 32)
                    rotations = 1
                    frames = 1
                    palette = @{
                        primary = "#ff6600"
                        secondary = "#ffaa00"
                        glow = "#ff8800"
                        trail = "#ffaa00"
                    }
                    material = @{
                        type = "Energy"
                        glowIntensity = 3.0
                        emissionStrength = 2.5
                        roughness = 0.2
                        metallic = 0.0
                    }
                    normalMap = $false
                    distortionMap = $false
                    animationHints = @{
                        pulse = $true
                        rotate = $false
                        trailLength = 0
                        particleCount = 0
                    }
                }
                physics = @{
                    speed = 120
                    acceleration = 0
                    lifetime = 5.0
                    drag = 0.0
                }
                damage = @{
                    baseDamage = 15
                    damageType = "laser"
                    areaRadius = 0
                    statusEffects = @()
                }
                fx = @{
                    trail = @{
                        enabled = $true
                        length = 15
                        fade = 0.7
                        color = "#ffaa00"
                    }
                    lightEmission = @{
                        enabled = $true
                        intensity = 1.5
                        radius = 8
                        color = "#ff6600"
                    }
                    sound = @{
                        fire = "sfxLaserFire"
                        impact = "sfxLaserImpact"
                    }
                }
                export = @{
                    xmlTemplate = "Projectile"
                    unid = "&pl$($AssetId.Replace('_', ''));"
                    resourcePaths = @{
                        image = "Resources/Projectiles/$AssetId.png"
                    }
                }
            }
        )
    }
    
    "Shield" = @{
        version = "1.0.0"
        shields = @(
            @{
                id = $AssetId
                type = "shield"
                maxStrength = 120
                rechargeRate = 6.0
                rechargeDelay = 2.5
                absorptionCurve = "linear"
                visual = @{
                    radius = 1.6
                    thickness = 0.08
                    color = "#66ccff"
                    glowColor = "#aaffff"
                    damagedColor = "#ff6666"
                    pulseFrequency = 0.9
                    pulseStrength = 0.5
                    distortionStrength = 0.3
                    waveFrequency = 4.0
                    waveSpeed = 2.0
                    particleProfile = "distortion_core"
                    spriteStrip = $false
                    normalMap = $true
                }
                fx = @{
                    hitFlashDuration = 0.12
                    hitPulseStrength = 1.6
                    impactParticleCount = 12
                    breakParticleCount = 30
                    sound = @{
                        hit = "sfxShieldHit"
                        break = "sfxShieldBreak"
                        recharge = "sfxShieldRecharge"
                    }
                }
                export = @{
                    unid = "&sh$($AssetId.Replace('_', ''));"
                    transcendenceXml = $true
                    resourcePaths = @{
                        sprite = "Resources/Shields/$AssetId.png"
                        normalMap = "Resources/Shields/$AssetId_normal.png"
                    }
                }
            }
        )
        armor = @()
    }
    
    "FX" = @{
        version = "1.0.0"
        effects = @(
            @{
                id = $AssetId
                type = "fx"
                style = "novaDrift"
                visual = @{
                    coreColor = "#ff66ff"
                    rimColor = "#ffffff"
                    shockwaveColor = "#ff99ff"
                    bloomColor = "#ffccff"
                    distortionStrength = 0.04
                    distortionType = "heatHaze"
                    noiseType = "perlin"
                    noiseSpeed = 1.2
                    noiseScale = 4.0
                    spriteSize = 64
                    frames = 12
                    layers = @("core", "shockwave", "bloom", "particles")
                    coreGlow = @{
                        enabled = $true
                        intensity = 3.0
                        pulse = $true
                        expand = $true
                    }
                    shockwave = @{
                        enabled = $true
                        ringCount = 1
                        thickness = 0.02
                        expandSpeed = 2.0
                    }
                    bloom = @{
                        enabled = $true
                        intensity = 1.5
                        radius = 1.2
                    }
                    chromaticAberration = $false
                }
                particles = @{
                    burstCount = 24
                    burstSpeedMin = 0.8
                    burstSpeedMax = 2.4
                    lifetimeMin = 0.2
                    lifetimeMax = 0.6
                    sizeMin = 0.02
                    sizeMax = 0.08
                    blend = "additive"
                    motionPattern = "radialBurst"
                    coreParticles = @{
                        enabled = $true
                        count = 8
                        speedMin = 0.1
                        speedMax = 0.3
                        lifeMin = 0.4
                        lifeMax = 0.8
                    }
                    shockwaveParticles = @{
                        enabled = $false
                    }
                }
                timing = @{
                    coreExpandTime = 0.12
                    shockwaveExpandTime = 0.18
                    fadeOutTime = 0.3
                    easeIn = "easeOut"
                    easeOut = "easeIn"
                }
                export = @{
                    unid = "&fx$($AssetId.Replace('_', ''));"
                    transcendence = @{
                        as = "explosion"
                        rotationFrames = 1
                        ticksPerFrame = 1
                    }
                    resourcePaths = @{
                        sprite = "Resources/FX/$AssetId.png"
                        particleProfile = "Resources/FX/$AssetId_particles.json"
                    }
                }
            }
        )
    }
    
    "Aura" = @{
        version = "1.0.0"
        auras = @(
            @{
                id = $AssetId
                type = "shieldAura"
                visual = @{
                    baseColor = "#66ccff"
                    windColor = "#aaffff"
                    distortionColor = "#88ddff"
                    radiusMin = 1.2
                    radiusMax = 2.4
                    alphaNoiseSpeed = 1.8
                    alphaNoiseScale = 3.2
                    alphaNoiseStrength = 0.6
                    distortionStrength = 0.05
                    distortionFrequency = 2.6
                    distortionType = "heatHaze"
                    windStreakCount = 12
                    windSpeed = 0.6
                    windNoise = 1.2
                    spriteSize = 64
                    frames = 12
                    noiseType = "perlin"
                    falloffCurve = "smooth"
                }
                particles = @{
                    orbitCount = 24
                    orbitSpeedMin = 0.4
                    orbitSpeedMax = 1.6
                    orbitRadiusMin = 0.8
                    orbitRadiusMax = 1.8
                    gravityStrength = 0.8
                    particleSize = 0.04
                    particleLifetime = 5.0
                    particleAlpha = 0.7
                    turbulence = 0.3
                    blend = "additive"
                }
                behavior = @{
                    projectileInfluence = $true
                    projectileOrbitTime = 0.3
                    projectileInfluenceRadius = 2.0
                    projectileGravityStrength = 0.6
                    projectileTangentialBlend = 0.4
                    projectileInwardPull = 0.2
                    shieldScaleWithHP = $true
                    radiusScaleCurve = "smooth"
                    alphaScaleWithHP = $true
                    speedScaleWithHP = $true
                }
                export = @{
                    unid = "&au$($AssetId.Replace('_', ''));"
                    transcendenceXml = $true
                    resourcePaths = @{
                        auraSprite = "Resources/Auras/$AssetId.png"
                        distortionMap = "Resources/Auras/$AssetId_distort.png"
                        particleProfile = "Resources/Auras/$AssetId_particles.json"
                    }
                }
            }
        )
    }
}

# Get template
if (-not $templates.ContainsKey($Type)) {
    Write-Log "Error: Unknown asset type: $Type" "ERROR"
    Write-Log "Valid types: Projectile, Shield, Armor, FX, Aura" "ERROR"
    exit 1
}

$template = $templates[$Type]

# Convert to JSON
$json = $template | ConvertTo-Json -Depth 10

# Write to file
try {
    $json | Out-File -FilePath $OutputPath -Encoding UTF8
    Write-Log "Created registry template: $OutputPath" "SUCCESS"
    Write-Log "Asset ID: $AssetId" "INFO"
    Write-Log "Type: $Type" "INFO"
    Write-Log ""
    Write-Log "Next steps:" "INFO"
    Write-Log "1. Edit the registry file to customize your asset" "INFO"
    Write-Log "2. Validate: python validate_registry.py --registry $OutputPath" "INFO"
    Write-Log "3. Generate: Use appropriate generator script" "INFO"
} catch {
    Write-Log "Error creating registry file: $_" "ERROR"
    exit 1
}

