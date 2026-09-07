#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate particle effects for game assets (portals, spells, projectiles, etc.)
    
.DESCRIPTION
    Creates particle effect assets including:
    - Particle spritesheets (multiple particle types in one sheet)
    - Animated particle sequences
    - Particle textures for different game engines

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Portal-specific particle effects
    - Spell/projectile particle trails
    
.PARAMETER EffectType
    Type of particle effect: Portal, Spell, Projectile, Explosion, Trail, Custom
    
.PARAMETER EffectName
    Name of the particle effect
    
.PARAMETER ParticleCount
    Number of different particle types to generate
    
.PARAMETER FrameCount
    Number of animation frames per particle
    
.PARAMETER ParticleSize
    Size of individual particles in pixels
    
.PARAMETER OutputDir
    Output directory for particle assets
    
.PARAMETER GameFormat
    Target game format: Terraria, Elin, Starbound, Transcendence, All
    
.PARAMETER UseAI
    Use AI to generate particle designs
    
.PARAMETER OllamaModel
    Ollama model for AI generation
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Portal", "Spell", "Projectile", "Explosion", "Trail", "Custom")]
    [string]$EffectType = "Portal",
    
    [Parameter(Mandatory=$true)]
    [string]$EffectName,
    
    [Parameter(Mandatory=$false)]
    [int]$ParticleCount = 4,
    
    [Parameter(Mandatory=$false)]
    [int]$FrameCount = 4,
    
    [Parameter(Mandatory=$false)]
    [int]$ParticleSize = 8,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "ParticleEffects",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Terraria", "Elin", "Starbound", "Transcendence", "All")]
    [string[]]$GameFormat = @("All"),
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [string]$ColorPalette = "",
    
    [Parameter(Mandatory=$false)]
    [string]$EffectDescription = ""
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Particle Effect Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$effectDir = Join-Path $OutputDir $EffectName
if (-not (Test-Path $effectDir)) {
    New-Item -ItemType Directory -Path $effectDir -Force | Out-Null
}

Write-Host "Effect Type: $EffectType" -ForegroundColor Green
Write-Host "Effect Name: $EffectName" -ForegroundColor Green
Write-Host "Particle Count: $ParticleCount" -ForegroundColor Green
Write-Host "Frame Count: $FrameCount" -ForegroundColor Green
Write-Host "Particle Size: ${ParticleSize}x${ParticleSize}" -ForegroundColor Green
Write-Host ""

# Determine color palette based on effect type
if ([string]::IsNullOrWhiteSpace($ColorPalette)) {
    switch ($EffectType) {
        "Portal" { $ColorPalette = "purple,blue,cyan" }
        "Spell" { $ColorPalette = "blue,white,lightblue" }
        "Projectile" { $ColorPalette = "yellow,orange,red" }
        "Explosion" { $ColorPalette = "orange,red,yellow" }
        "Trail" { $ColorPalette = "blue,cyan,white" }
        default { $ColorPalette = "white,lightgray,gray" }
    }
}

# Generate particle descriptions
$particleDescriptions = @()
if ($UseAI -and -not [string]::IsNullOrWhiteSpace($EffectDescription)) {
    Write-Host "Generating particle descriptions with AI..." -ForegroundColor Cyan
    
    $assetMakerScript = Join-Path $PSScriptRoot "..\Transcendence\AssetMakerAI.ps1"
    if (Test-Path $assetMakerScript) {
        $aiPrompt = "Generate $ParticleCount different particle effect descriptions for a $EffectType effect. Each should be unique: $EffectDescription. Colors: $ColorPalette. Output as a comma-separated list."
        
        # This would call AI, but for now we'll generate procedurally
        Write-Host "  AI generation not fully implemented, using procedural generation" -ForegroundColor Yellow
    }
}

# Generate procedural particle descriptions
if ($particleDescriptions.Count -eq 0) {
    $baseDescriptions = @{
        "Portal" = @("swirling energy particle", "spark", "energy orb", "glowing fragment", "magical dust")
        "Spell" = @("magic sparkle", "mana particle", "arcane fragment", "spell dust", "magical energy")
        "Projectile" = @("trail particle", "spark", "ember", "glow", "energy trail")
        "Explosion" = @("explosion spark", "debris", "smoke particle", "fire ember", "shockwave")
        "Trail" = @("trail particle", "energy trail", "spark trail", "glow trail", "dust trail")
    }
    
    $descriptions = if ($baseDescriptions.ContainsKey($EffectType)) {
        $baseDescriptions[$EffectType]
    } else {
        @("particle", "spark", "glow", "energy", "fragment")
    }
    
    for ($i = 0; $i -lt $ParticleCount; $i++) {
        $desc = $descriptions[$i % $descriptions.Count]
        $particleDescriptions += "$desc, $ColorPalette, size $ParticleSize pixels"
    }
}

Write-Host "Generating $ParticleCount particle types..." -ForegroundColor Cyan
Write-Host ""

# Generate particles
$tempParticlesDir = Join-Path $env:TEMP "Particles_$(Get-Random)"
if (-not (Test-Path $tempParticlesDir)) {
    New-Item -ItemType Directory -Path $tempParticlesDir -Force | Out-Null
}

$particleFiles = @()

for ($p = 0; $p -lt $ParticleCount; $p++) {
    Write-Host "  Particle $($p + 1)/$ParticleCount : $($particleDescriptions[$p])" -ForegroundColor Gray
    
    $particleFrames = @()
    
    # Generate frames for this particle
    for ($f = 0; $f -lt $FrameCount; $f++) {
        $framePath = Join-Path $tempParticlesDir "particle_${p}_frame_$($f.ToString('00')).png"
        
        # Create particle frame using Blender or fallback
        $blenderExe = $null
        $commonPaths = @("D:\tools\Blender Foundation", "${env:ProgramFiles}\Blender Foundation")
        foreach ($basePath in $commonPaths) {
            if (Test-Path $basePath) {
                $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -match '^Blender' } | Sort-Object Name -Descending
                foreach ($dir in $blenderDirs) {
                    $blenderExe = Join-Path $dir.FullName "blender.exe"
                    if (Test-Path $blenderExe) { break }
                }
            }
            if ($blenderExe) { break }
        }
        
        if ($blenderExe) {
            # Generate particle with Blender
            $blenderScript = Join-Path $tempParticlesDir "gen_particle_${p}_${f}.py"
            
            $progress = $f / $FrameCount
            $size = $ParticleSize * (1.0 - $progress * 0.5)  # Fade out
            $alpha = 1.0 - ($progress * 0.7)  # Fade alpha
            
            $scriptContent = @"
import bpy
import math
import os

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create particle (sphere or custom shape)
particle_type = $p % 3
if particle_type == 0:
    # Energy orb
    bpy.ops.mesh.primitive_ico_sphere_add(radius=$($size / 100.0), subdivisions=1)
elif particle_type == 1:
    # Spark (elongated)
    bpy.ops.mesh.primitive_cube_add(size=$($size / 100.0))
    bpy.context.active_object.scale[2] = 2.0
else:
    # Fragment (irregular)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=$($size / 100.0), subdivisions=0)

particle = bpy.context.active_object

# Create material
mat = bpy.data.materials.new(name="ParticleMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()

output = nodes.new(type='ShaderNodeOutputMaterial')
emission = nodes.new(type='ShaderNodeEmission')

# Color based on effect type and particle index
colors = {
    'Portal': [(0.5, 0.2, 1.0), (0.3, 0.5, 1.0), (0.2, 0.8, 1.0), (0.4, 0.3, 1.0)],
    'Spell': [(0.2, 0.5, 1.0), (0.4, 0.6, 1.0), (0.6, 0.8, 1.0), (0.8, 0.9, 1.0)],
    'Projectile': [(1.0, 0.8, 0.2), (1.0, 0.6, 0.1), (1.0, 0.4, 0.0), (1.0, 0.2, 0.0)],
    'Explosion': [(1.0, 0.5, 0.0), (1.0, 0.3, 0.0), (1.0, 0.1, 0.0), (0.8, 0.1, 0.0)],
    'Trail': [(0.2, 0.6, 1.0), (0.4, 0.7, 1.0), (0.6, 0.8, 1.0), (0.8, 0.9, 1.0)]
}

effect_type = '$EffectType'
color_index = $p % 4
color = colors.get(effect_type, [(1.0, 1.0, 1.0)])[color_index]

emission.inputs['Color'].default_value = (*color, $alpha)
emission.inputs['Strength'].default_value = 3.0 * $alpha
mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])

particle.data.materials.append(mat)

# Set up camera
bpy.ops.object.camera_add()
camera = bpy.context.active_object
camera.location = (0, -0.5, 0)
camera.rotation_euler = (math.radians(90), 0, 0)

# Set render settings
bpy.context.scene.render.resolution_x = $ParticleSize
bpy.context.scene.render.resolution_y = $ParticleSize
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 16

# Render
bpy.context.scene.camera = camera
output_path = r'$($framePath.Replace('\', '\\'))'
bpy.context.scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)

print(f"Particle frame rendered: {output_path}")
"@
            
            [System.IO.File]::WriteAllText($blenderScript, $scriptContent, [System.Text.UTF8Encoding]::new($false))
            
            $blenderArgs = @("--background", "--python", "`"$blenderScript`"")
            $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
            
            if ($process.ExitCode -eq 0 -and (Test-Path $framePath)) {
                $particleFrames += $framePath
            }
        } else {
            # Fallback: Create simple particle frame
            $bitmap = New-Object System.Drawing.Bitmap $ParticleSize, $ParticleSize
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.Clear([System.Drawing.Color]::Transparent)
            
            $progress = $f / $FrameCount
            $size = [Math]::Max(2, [int]($ParticleSize * (1.0 - $progress * 0.5)))
            $alpha = [int](255 * (1.0 - $progress * 0.7))
            
            $colors = @{
                "Portal" = [System.Drawing.Color]::FromArgb($alpha, 128, 0, 255)
                "Spell" = [System.Drawing.Color]::FromArgb($alpha, 100, 150, 255)
                "Projectile" = [System.Drawing.Color]::FromArgb($alpha, 255, 200, 0)
                "Explosion" = [System.Drawing.Color]::FromArgb($alpha, 255, 100, 0)
                "Trail" = [System.Drawing.Color]::FromArgb($alpha, 50, 150, 255)
            }
            
            $color = if ($colors.ContainsKey($EffectType)) { $colors[$EffectType] } else { [System.Drawing.Color]::FromArgb($alpha, 255, 255, 255) }
            $brush = New-Object System.Drawing.SolidBrush($color)
            
            $x = ($ParticleSize - $size) / 2
            $y = ($ParticleSize - $size) / 2
            $graphics.FillEllipse($brush, $x, $y, $size, $size)
            
            $bitmap.Save($framePath)
            $graphics.Dispose()
            $bitmap.Dispose()
            
            $particleFrames += $framePath
        }
    }
    
    if ($particleFrames.Count -gt 0) {
        $particleFiles += $particleFrames
        Write-Host "    ✓ Generated $($particleFrames.Count) frames" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Assembling particle spritesheet..." -ForegroundColor Cyan

# Assemble spritesheet
$spritesheetWidth = $ParticleSize * $FrameCount
$spritesheetHeight = $ParticleSize * $ParticleCount
$spritesheetPath = Join-Path $effectDir "${EffectName}_Particles.png"

$spritesheet = New-Object System.Drawing.Bitmap $spritesheetWidth, $spritesheetHeight
$graphics = [System.Drawing.Graphics]::FromImage($spritesheet)
$graphics.Clear([System.Drawing.Color]::Transparent)

$particleIndex = 0
for ($p = 0; $p -lt $ParticleCount; $p++) {
    for ($f = 0; $f -lt $FrameCount; $f++) {
        $frameIndex = $p * $FrameCount + $f
        if ($frameIndex -lt $particleFiles.Count -and (Test-Path $particleFiles[$frameIndex])) {
            $frame = [System.Drawing.Image]::FromFile($particleFiles[$frameIndex])
            $x = $f * $ParticleSize
            $y = $p * $ParticleSize
            $graphics.DrawImage($frame, $x, $y, $ParticleSize, $ParticleSize)
            $frame.Dispose()
        }
    }
}

$spritesheet.Save($spritesheetPath)
$graphics.Dispose()
$spritesheet.Dispose()

Write-Host "  ✓ Spritesheet created: $spritesheetPath" -ForegroundColor Green
Write-Host "    Dimensions: ${spritesheetWidth}x${spritesheetHeight}" -ForegroundColor Gray
Write-Host ""

# Export to game formats
Write-Host "Exporting to game formats..." -ForegroundColor Cyan

foreach ($format in $GameFormat) {
    $formatDir = Join-Path $effectDir "${format}Export"
    if (-not (Test-Path $formatDir)) {
        New-Item -ItemType Directory -Path $formatDir -Force | Out-Null
    }
    
    Copy-Item -Path $spritesheetPath -Destination (Join-Path $formatDir "${EffectName}_Particles.png") -Force
    
    # Create format-specific metadata
    switch ($format) {
        "Terraria" {
            $terrariaMeta = @{
                particleCount = $ParticleCount
                framesPerParticle = $FrameCount
                particleSize = $ParticleSize
                sheetWidth = $spritesheetWidth
                sheetHeight = $spritesheetHeight
                effectType = $EffectType
            }
            $terrariaMeta | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $formatDir "${EffectName}_particles.json") -Encoding UTF8
        }
        "Elin" {
            $elinMeta = @{
                name = $EffectName
                type = "particles"
                particleCount = $ParticleCount
                framesPerParticle = $FrameCount
                size = $ParticleSize
            }
            $elinMeta | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $formatDir "${EffectName}_particles.json") -Encoding UTF8
        }
    }
    
    Write-Host "  ✓ Exported to $format" -ForegroundColor Green
}

# Create metadata
$metadata = @{
    EffectName = $EffectName
    EffectType = $EffectType
    ParticleCount = $ParticleCount
    FrameCount = $FrameCount
    ParticleSize = $ParticleSize
    SpritesheetDimensions = @{
        Width = $spritesheetWidth
        Height = $spritesheetHeight
    }
    GameFormats = $GameFormat
    GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    ColorPalette = $ColorPalette
}

$metadataPath = Join-Path $effectDir "metadata.json"
$metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8

# Cleanup
Remove-Item -LiteralPath $tempParticlesDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Particle Effect Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Particle effect created at: $effectDir" -ForegroundColor Green
Write-Host "Spritesheet: $spritesheetPath" -ForegroundColor Green
Write-Host ""

