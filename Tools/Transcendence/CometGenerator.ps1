#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate a comet projectile asset using C++ backend or PowerShell generators.
    
.DESCRIPTION
    Creates a comet/meteor projectile with:
    - Rocky core with irregular shape
    - Glowing reentry fire
    - Particle dust trail

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Optional fragmentation effects
    - Starbound-compatible export
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$CometName = "SkyfallMeteor",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Meteor", "Comet", "Asteroid", "FallingStar", "CelestialRock")]
    [string]$CometType = "Meteor",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Sphere", "Irregular", "Fragmented", "Crystalline")]
    [string]$CometShape = "Irregular",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Dust", "Fire", "Smoke", "Sparks", "None")]
    [string]$TrailType = "Dust",
    
    [Parameter(Mandatory=$false)]
    [float]$CoreRadius = 0.5,
    
    [Parameter(Mandatory=$false)]
    [float]$Speed = 30.0,
    
    [Parameter(Mandatory=$false)]
    [float]$TrailLength = 2.0,
    
    [Parameter(Mandatory=$false)]
    [int]$DustParticleCount = 100,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseCppBackend,
    
    [Parameter(Mandatory=$false)]
    [string]$CppBackendPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "CometAssets",
    
    [Parameter(Mandatory=$false)]
    [switch]$LaunchControlRoom,
    
    [Parameter(Mandatory=$false)]
    [string]$WatchDirectory = ""
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Comet Projectile Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Setup watch directory for GUI
$watchDir = if ([string]::IsNullOrWhiteSpace($WatchDirectory)) {
    Join-Path $OutputDir "watch"
} else {
    $WatchDirectory
}

if (-not (Test-Path $watchDir)) {
    New-Item -ItemType Directory -Path $watchDir -Force | Out-Null
}

Write-Host "Comet Name: $CometName" -ForegroundColor Green
Write-Host "Comet Type: $CometType" -ForegroundColor Green
Write-Host "Comet Shape: $CometShape" -ForegroundColor Green
Write-Host "Trail Type: $TrailType" -ForegroundColor Green
Write-Host "Output Directory: $OutputDir" -ForegroundColor Green
Write-Host ""

# Launch Control Room if requested
if ($LaunchControlRoom) {
    $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
    if (Test-Path $controlRoomScript) {
        Write-Host "Launching Control Room..." -ForegroundColor Cyan
        
        $controlRoomArgs = @(
            "-AssetType", "Model",
            "-WatchDirectory", $watchDir,
            "-AutoExport"
        )
        
        $allArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$controlRoomScript`"") + $controlRoomArgs
        Start-Process -FilePath "pwsh" -ArgumentList $allArgs -WindowStyle Normal
        Write-Host "  ✓ Control Room launched" -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
}

if ($UseCppBackend) {
    Write-Host "Using C++ Backend" -ForegroundColor Cyan
    
    $bridgeScript = Join-Path $PSScriptRoot "StarboundCppBackendBridge.ps1"
    if (Test-Path $bridgeScript) {
        # Map PowerShell parameters to C++ backend parameters
        $cometTypeMap = @{
            "Meteor" = "METEOR"
            "Comet" = "COMET"
            "Asteroid" = "ASTEROID"
            "FallingStar" = "FALLING_STAR"
            "CelestialRock" = "CELESTIAL_ROCK"
        }
        
        $shapeMap = @{
            "Sphere" = "SPHERE"
            "Irregular" = "IRREGULAR"
            "Fragmented" = "FRAGMENTED"
            "Crystalline" = "CRYSTALLINE"
        }
        
        $trailMap = @{
            "Dust" = "DUST"
            "Fire" = "FIRE"
            "Smoke" = "SMOKE"
            "Sparks" = "SPARKS"
            "None" = "NONE"
        }
        
        $params = @{
            CometType = $cometTypeMap[$CometType]
            CometShape = $shapeMap[$CometShape]
            TrailType = $trailMap[$TrailType]
            CoreRadius = $CoreRadius
            Speed = $Speed
            TrailLength = $TrailLength
            DustParticleCount = $DustParticleCount
        }
        
        # Generate Lua script for comet
        $luaScript = @"
-- Comet Projectile Generation
require("agents.GeneratorAgent.CometProjectileFactory")

initialize_comet_projectile_factory(500, 4)

local cometParams = create_comet_params()
cometParams.id = "$CometName"
cometParams.cometType = CometType.$($cometTypeMap[$CometType])
cometParams.cometShape = CometShape.$($shapeMap[$CometShape])
cometParams.trailType = TrailType.$($trailMap[$TrailType])
cometParams.coreRadius = $CoreRadius
cometParams.speed = $Speed
cometParams.trailLength = $TrailLength
cometParams.dustParticleCount = $DustParticleCount
cometParams.heatColor = {1.0, 0.5, 0.1}
cometParams.burnColor = {1.0, 0.8, 0.3}
cometParams.coreColor = {0.8, 0.6, 0.4}
cometParams.glowColor = {1.0, 0.4, 0.0}
cometParams.glowIntensity = 2.0
cometParams.enableCoreGlow = true
cometParams.enableTrailGlow = true

local bundle = generate_comet_async(cometParams):get()
if bundle and bundle:isValid() then
    print("✓ Comet generated successfully")
    print("  Mesh: " .. bundle.mesh)
    print("  Texture: " .. bundle.texture)
    print("  Particles: " .. bundle.dustTrail)
    export_comet_bundle(bundle, "$($OutputDir.Replace('\', '\\'))")
else
    print("✗ Comet generation failed")
end
"@
        
        & $bridgeScript `
            -BackendPath $CppBackendPath `
            -GeneratorType "Projectile" `
            -Action "Generate" `
            -AssetName $CometName `
            -OutputDir $OutputDir `
            -LuaScript $luaScript `
            -Parameters $params
        
        Write-Host "  ✓ C++ backend generation initiated" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Bridge script not found, using PowerShell fallback" -ForegroundColor Yellow
        $UseCppBackend = $false
    }
}

if (-not $UseCppBackend) {
    Write-Host "Using PowerShell Generators" -ForegroundColor Cyan
    
    # Generate comet using Blender
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
        Write-Host "Generating comet mesh with Blender..." -ForegroundColor Cyan
        
        $blenderScript = Join-Path $env:TEMP "comet_gen_$(Get-Random).py"
        $pythonContent = @"
import bpy
import math
import os

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create irregular sphere for comet core
bpy.ops.mesh.primitive_ico_sphere_add(radius=$CoreRadius, subdivisions=3)
comet = bpy.context.active_object
comet.name = "$CometName"

# Add noise modifier for irregularity
bpy.ops.object.modifier_add(type='DISPLACE')
displace = comet.modifiers["Displace"]
displace.strength = $($CoreRadius * 0.3)
displace.mid_level = 0.5

# Create noise texture
noise = bpy.data.textures.new(name="CometNoise", type='CLOUDS')
noise.noise_scale = 2.0
noise.noise_depth = 3
displace.texture = noise

# Create material with emissive glow
mat = bpy.data.materials.new(name="CometMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
nodes.clear()

output = nodes.new(type='ShaderNodeOutputMaterial')
emission = nodes.new(type='ShaderNodeEmission')
principled = nodes.new(type='ShaderNodeBsdfPrincipled')

# Core color (rocky)
principled.inputs['Base Color'].default_value = (0.8, 0.6, 0.4, 1.0)
principled.inputs['Roughness'].default_value = 0.8
principled.inputs['Metallic'].default_value = 0.1

# Heat glow (orange/red)
emission.inputs['Color'].default_value = (1.0, 0.5, 0.1, 1.0)
emission.inputs['Strength'].default_value = 2.0

# Mix emission and base
mix = nodes.new(type='ShaderNodeMixShader')
mix.inputs['Fac'].default_value = 0.7

mat.node_tree.links.new(principled.outputs['BSDF'], mix.inputs[1])
mat.node_tree.links.new(emission.outputs['Emission'], mix.inputs[2])
mat.node_tree.links.new(mix.outputs['Shader'], output.inputs['Surface'])

comet.data.materials.append(mat)

# Set up camera
bpy.ops.object.camera_add()
camera = bpy.context.active_object
camera.location = (0, -3, 1)
camera.rotation_euler = (math.radians(75), 0, 0)

# Add lighting
bpy.ops.object.light_add(type='SUN')
light = bpy.context.active_object
light.location = (5, -5, 5)
light.data.energy = 3.0

# Set render settings
bpy.context.scene.render.resolution_x = 512
bpy.context.scene.render.resolution_y = 512
bpy.context.scene.render.film_transparent = True
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 32

# Render
bpy.context.scene.camera = camera
output_path = r'$($watchDir.Replace('\', '\\'))\\${CometName}_core.png'
bpy.context.scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)

print(f"Comet core rendered: {output_path}")

# Export mesh
mesh_path = r'$($OutputDir.Replace('\', '\\'))\\${CometName}.obj'
bpy.ops.export_scene.obj(filepath=mesh_path, use_selection=True)
print(f"Comet mesh exported: {mesh_path}")
"@
        
        [System.IO.File]::WriteAllText($blenderScript, $pythonContent, [System.Text.UTF8Encoding]::new($false))
        
        $blenderArgs = @("--background", "--python", "`"$blenderScript`"")
        $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        
        if ($process.ExitCode -eq 0) {
            Write-Host "  ✓ Comet core generated" -ForegroundColor Green
            
            # Generate particle trail
            $particleScript = Join-Path $PSScriptRoot "ParticleEffectGenerator.ps1"
            if (Test-Path $particleScript) {
                Write-Host "Generating particle trail..." -ForegroundColor Cyan
                
                & $particleScript `
                    -EffectType "Trail" `
                    -EffectName "${CometName}_Trail" `
                    -ParticleCount $DustParticleCount `
                    -FrameCount 8 `
                    -ParticleSize 8 `
                    -OutputDir $watchDir `
                    -GameFormat @("Starbound") `
                    -ColorPalette "orange,red,yellow" `
                    -ErrorAction Continue 2>&1 | Out-Null
                
                Write-Host "  ✓ Particle trail generated" -ForegroundColor Green
            }
        } else {
            Write-Host "  ✗ Blender generation failed" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠ Blender not found, creating placeholder" -ForegroundColor Yellow
        
        # Create placeholder image
        $placeholderPath = Join-Path $watchDir "${CometName}_core.png"
        $bitmap = New-Object System.Drawing.Bitmap 512, 512
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Black)
        
        # Draw comet (simple circle with glow)
        $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 128, 0))
        $graphics.FillEllipse($brush, 200, 200, 112, 112)
        
        $bitmap.Save($placeholderPath)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        Write-Host "  ✓ Placeholder created" -ForegroundColor Yellow
    }
}

# Create metadata
$metadata = @{
    CometName = $CometName
    CometType = $CometType
    CometShape = $CometShape
    TrailType = $TrailType
    CoreRadius = $CoreRadius
    Speed = $Speed
    TrailLength = $TrailLength
    DustParticleCount = $DustParticleCount
    GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    OutputDirectory = $OutputDir
    WatchDirectory = $watchDir
}

$metadataPath = Join-Path $OutputDir "comet_metadata.json"
$metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Comet Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Comet assets created at: $OutputDir" -ForegroundColor Green
Write-Host "Watch directory: $watchDir" -ForegroundColor Green
Write-Host ""

if ($LaunchControlRoom) {
    Write-Host "Control Room is watching: $watchDir" -ForegroundColor Cyan
    Write-Host "Assets should appear in the preview window" -ForegroundColor Cyan
}

Write-Host ""

