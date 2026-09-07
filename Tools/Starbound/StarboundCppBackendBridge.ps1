#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bridge between PowerShell asset generators and C++ backend for Starbound mod.
    
.DESCRIPTION
    Integrates with the C++ backend asset generators in:
    D:\games\Steam\steamapps\common\Transcendence\Tools\Starbound\cpp_generators\GeneratorAgent
    (moved out of the Magi-Tech mod; runtime vendor still under the mod cpp_backend)
    
    Provides PowerShell interface to:

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - ImageGenerator (images, spritesheets, animations)
    - TextureAssetFactory (procedural textures)
    - ParticleAssetFactory (particle effects)
    - AnimationAssetFactory (animations)
    - IconAssetFactory (icons)
    - And other C++ generators
    
.PARAMETER BackendPath
    Path to the C++ backend directory
    
.PARAMETER GeneratorType
    Type of generator to use: Image, Texture, Particle, Animation, Icon, Atlas, Audio, Mesh
    
.PARAMETER Action
    Action to perform: Generate, Export, Validate
    
.PARAMETER AssetName
    Name of the asset to generate
    
.PARAMETER OutputDir
    Output directory for generated assets
    
.PARAMETER LuaScript
    Custom Lua script to execute
    
.PARAMETER Parameters
    Hashtable of parameters to pass to the generator
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$BackendPath = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Image", "Texture", "Particle", "Animation", "Icon", "Atlas", "Audio", "Mesh", "Spell", "Projectile")]
    [string]$GeneratorType = "Image",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Generate", "Export", "Validate", "Batch")]
    [string]$Action = "Generate",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "",
    
    [Parameter(Mandatory=$false)]
    [string]$LuaScript = "",
    
    [Parameter(Mandatory=$false)]
    [hashtable]$Parameters = @{}
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Prefer Tools/cpp_generators (moved GeneratorAgent). Fall back to the mod cpp_backend.
if ([string]::IsNullOrWhiteSpace($BackendPath)) {
    $toolsGen = Join-Path $PSScriptRoot "cpp_generators"
    $modBackend = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery\cpp_backend"
    if (Test-Path (Join-Path $toolsGen "GeneratorAgent")) {
        $BackendPath = $toolsGen
    } else {
        $BackendPath = $modBackend
    }
}

# Load Ollama integration helpers
$ollamaHelper = Join-Path $PSScriptRoot "OllamaImageGenerator.ps1"
$ollamaCppBridge = Join-Path $PSScriptRoot "OllamaCppBridge.ps1"  # Bridge for C++ backend to call Ollama

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Starbound C++ Backend Bridge" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate backend path
if (-not (Test-Path $BackendPath)) {
    Write-Host "Error: Backend path not found: $BackendPath" -ForegroundColor Red
    exit 1
}

# GeneratorAgent is either <Tools>/cpp_generators/GeneratorAgent or <mod>/cpp_backend/agents/GeneratorAgent
$generatorAgentPath = Join-Path $BackendPath "GeneratorAgent"
if (-not (Test-Path $generatorAgentPath)) {
    $generatorAgentPath = Join-Path $BackendPath "agents\GeneratorAgent"
}
if (-not (Test-Path $generatorAgentPath)) {
    Write-Host "Error: GeneratorAgent directory not found under $BackendPath" -ForegroundColor Red
    exit 1
}

Write-Host "Backend Path: $BackendPath" -ForegroundColor Green
Write-Host "Generator Type: $GeneratorType" -ForegroundColor Green
Write-Host "Action: $Action" -ForegroundColor Green
Write-Host ""

# Create output directory
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "StarboundAssets"
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Generate Lua script based on generator type
$luaScriptPath = Join-Path $env:TEMP "starbound_generator_$(Get-Random).lua"

if ([string]::IsNullOrWhiteSpace($LuaScript)) {
    # Set bridge script path for all generators
    $bridgeScriptPath = $ollamaCppBridge.Replace('\', '\\')
    
    # Generate script based on generator type
    $luaContent = switch ($GeneratorType) {
        "Image" {
            $outputPath = "$($OutputDir.Replace('\', '\\'))\\$(if ($AssetName) { $AssetName } else { 'generated_image' }).png"
            $width = if ($Parameters.Width) { $Parameters.Width } else { 256 }
            $height = if ($Parameters.Height) { $Parameters.Height } else { 256 }
            
            # Enhance description with Ollama if available
            $enhancedDescription = $Parameters.Description
            $enhancedParams = @{}
            
            if ($Parameters.Description -and $Parameters.Description.Trim().Length -gt 0) {
                Write-Host "Enhancing description with Ollama for improved generation quality..." -ForegroundColor Cyan
                Write-Host "  Original: $($Parameters.Description.Substring(0, [Math]::Min(80, $Parameters.Description.Length)))..." -ForegroundColor Gray
                
                try {
                    if (Test-Path $ollamaHelper) {
                        $enhancementResult = & $ollamaHelper -Description $Parameters.Description -Width $width -Height $height -ErrorAction Stop 2>&1 | ConvertFrom-Json
                        if ($enhancementResult -and $enhancementResult.EnhancedDescription) {
                            $enhancedDescription = $enhancementResult.EnhancedDescription
                            if ($enhancementResult.ExtractedParameters) {
                                $enhancedParams = $enhancementResult.ExtractedParameters
                            }
                            Write-Host "✓ Description enhanced with Ollama" -ForegroundColor Green
                            Write-Host "  Enhanced: $($enhancedDescription.Substring(0, [Math]::Min(80, $enhancedDescription.Length)))..." -ForegroundColor Gray
                        }
                    }
                } catch {
                    Write-Host "⚠ Ollama enhancement failed: $_" -ForegroundColor Yellow
                    Write-Host "  Using original description with C++ backend..." -ForegroundColor Gray
                }
            }
            
            # Generate Lua script with Ollama-enhanced description
            $descriptionParam = if ($enhancedDescription) { 
                $desc = $enhancedDescription -replace '"', '\"'
                "description = `"$desc`","
            } else { "" }
            
            # Build enhanced parameters from Ollama extraction
            $paramLines = @()
            if ($enhancedParams.ColorPalette) {
                $colors = $enhancedParams.ColorPalette | ForEach-Object { "{$_[0]}, $_[1], $_[2]" }
                $paramLines += "colorPalette = {$($colors -join ', ')},"
            }
            if ($enhancedParams.Style) {
                $paramLines += "style = `"$($enhancedParams.Style)`","
            }
            if ($enhancedParams.HasGradient) {
                $paramLines += "hasGradient = true,"
            }
            if ($enhancedParams.HasPattern) {
                $paramLines += "hasPattern = true,"
            }
            if ($enhancedParams.HasSparkles) {
                $paramLines += "hasSparkles = true,"
            }
            $enhancedParamString = if ($paramLines.Count -gt 0) { "`n    " + ($paramLines -join "`n    ") } else { "" }
            
            $bridgeScriptPath = $ollamaCppBridge.Replace('\', '\\')
            @"
-- Image Generation via C++ Backend with Ollama-Enhanced Description
require("agents.GeneratorAgent.ImageGenerator")
require("OllamaLuaHelper")  -- Load Ollama helper for description enhancement

-- Set bridge script path for Ollama helper
OllamaHelper.BRIDGE_SCRIPT = "$bridgeScriptPath"

local imageGen = ImageGenerator.new()
imageGen:initialize()

local params = {
    width = $width,
    height = $height,
    format = "$(if ($Parameters.Format) { $Parameters.Format } else { 'PNG' })",
    quality = $(if ($Parameters.Quality) { $Parameters.Quality } else { 3 }),
    $descriptionParam
    spriteType = "$(if ($Parameters.SpriteType) { $Parameters.SpriteType } else { 'Sprite' })",$enhancedParamString
    -- Enhanced generation flags
    useDescription = $(if ($enhancedDescription) { 'true' } else { 'false' }),
    enhanceWithDescription = $(if ($enhancedDescription) { 'true' } else { 'false' }),
    ollamaEnhanced = $(if ($enhancedDescription -and $enhancedDescription -ne $Parameters.Description) { 'true' } else { 'false' })
}

-- Set bridge script path for Ollama helper (for C++ backend to call Ollama)
OllamaHelper.BRIDGE_SCRIPT = "$($ollamaCppBridge.Replace('\', '\\'))"

-- Enhanced generation using Ollama-enhanced description
if params.description and params.description ~= "" then
    print("Using Ollama-enhanced description for high-quality generation...")
    print("Description: " .. (params.description:sub(1, 100) or ""))
    
    -- Use Ollama helper to further enhance description and parameters
    if OllamaHelper.isAvailable() then
        print("  ✓ Ollama available - enhancing description and parameters...")
        local enhancedDesc = OllamaHelper.enhanceDescription(params.description)
        if enhancedDesc and enhancedDesc ~= params.description then
            params.description = enhancedDesc
            params.ollamaEnhanced = true
            print("  ✓ Description enhanced by Ollama")
        end
        
        -- Extract and merge parameters
        params = OllamaHelper.enhanceProceduralParams(params, params.description)
        if params.ollamaEnhanced then
            print("  ✓ Parameters enhanced with Ollama-extracted values")
        end
    else
        print("  ⚠ Ollama not available - using description as-is")
    end
    
    print("  The C++ backend will use this enhanced description to guide")
    print("  procedural generation for better quality and thematic consistency")
end

local bundle = imageGen:generateImage(params)
if bundle then
    print("✓ Image generated successfully")
    print("  Size: " .. bundle.width .. "x" .. bundle.height)
    if bundle.metadata and bundle.metadata.description then
        print("  Metadata: " .. bundle.metadata.description)
    end
    imageGen:saveImage(bundle, "$outputPath")
else
    print("✗ Image generation failed")
end

imageGen:shutdown()
"@
        }
        
        "Texture" {
            @"
-- Texture Generation via C++ Backend
require("agents.GeneratorAgent.TextureAssetFactory")

initialize_texture_asset_factory(500, 4)

local textureParams = create_texture_params()
textureParams.id = "$(if ($AssetName) { $AssetName } else { 'generated_texture' })"
textureParams.width = $(if ($Parameters.Width) { $Parameters.Width } else { 256 })
textureParams.height = $(if ($Parameters.Height) { $Parameters.Height } else { 256 })
textureParams.format = "$(if ($Parameters.Format) { $Parameters.Format } else { 'PNG' })"

local noiseParams = create_noise_params()
noiseParams.scale = $(if ($Parameters.NoiseScale) { $Parameters.NoiseScale } else { 4.0 })
noiseParams.seed = $(if ($Parameters.Seed) { $Parameters.Seed } else { 0 })
noiseParams.seamless = $(if ($Parameters.Seamless -ne $null) { $Parameters.Seamless } else { $true })

local bundle = generate_texture_async(textureParams, noiseParams):get()
if bundle and bundle:isValid() then
    print("✓ Texture generated successfully")
    print("  Assets: " .. bundle:getAssetCount())
    export_texture_bundle(bundle, "$($OutputDir.Replace('\', '\\'))")
else
    print("✗ Texture generation failed")
end
"@
        }
        
        "Particle" {
            $descriptionParam = if ($Parameters.Description) { 
                $desc = $Parameters.Description -replace '"', '\"'
                "description = `"$desc`","
            } else { "" }
            @"
-- Particle Generation via C++ Backend with Ollama Description Enhancement
require("agents.GeneratorAgent.ParticleAssetFactory")
require("OllamaLuaHelper")  -- Load Ollama helper for description enhancement

-- Set bridge script path for Ollama helper
OllamaHelper.BRIDGE_SCRIPT = "$bridgeScriptPath"

initialize_particle_asset_factory(500, 4)

local particleParams = create_particle_params()
particleParams.id = "$(if ($AssetName) { $AssetName } else { 'generated_particles' })"
particleParams.particleCount = $(if ($Parameters.ParticleCount) { $Parameters.ParticleCount } else { 4 })
particleParams.frameCount = $(if ($Parameters.FrameCount) { $Parameters.FrameCount } else { 4 })
particleParams.particleSize = $(if ($Parameters.ParticleSize) { $Parameters.ParticleSize } else { 8 })
particleParams.effectType = "$(if ($Parameters.EffectType) { $Parameters.EffectType } else { 'Portal' })"
$descriptionParam

-- Enhance parameters with Ollama if available
if particleParams.description and particleParams.description ~= "" then
    print("Using Ollama-enhanced particle generation...")
    print("Description: " .. (particleParams.description:sub(1, 100) or ""))
    if OllamaHelper.isAvailable() then
        local enhancedDesc = OllamaHelper.enhanceDescription(particleParams.description)
        if enhancedDesc and enhancedDesc ~= particleParams.description then
            particleParams.description = enhancedDesc
            print("  ✓ Description enhanced by Ollama")
        end
    end
    particleParams = OllamaHelper.enhanceProceduralParams(particleParams, particleParams.description)
end

local bundle = generate_particle_async(particleParams):get()
if bundle and bundle:isValid() then
    print("✓ Particles generated successfully")
    print("  Assets: " .. bundle:getAssetCount())
    export_particle_bundle(bundle, "$($OutputDir.Replace('\', '\\'))")
else
    print("✗ Particle generation failed")
end
"@
        }
        
        "Animation" {
            $descriptionParam = if ($Parameters.Description) { 
                $desc = $Parameters.Description -replace '"', '\"'
                "description = `"$desc`","
            } else { "" }
            @"
-- Animation Generation via C++ Backend with Ollama Description Enhancement
require("agents.GeneratorAgent.AnimationAssetFactory")
require("OllamaLuaHelper")  -- Load Ollama helper for description enhancement

-- Set bridge script path for Ollama helper
OllamaHelper.BRIDGE_SCRIPT = "$bridgeScriptPath"

initialize_animation_asset_factory(500, 4)

local animParams = create_animation_params()
animParams.id = "$(if ($AssetName) { $AssetName } else { 'generated_animation' })"
animParams.frameCount = $(if ($Parameters.FrameCount) { $Parameters.FrameCount } else { 8 })
animParams.frameDuration = $(if ($Parameters.FrameDuration) { $Parameters.FrameDuration } else { 0.1 })
animParams.width = $(if ($Parameters.Width) { $Parameters.Width } else { 32 })
animParams.height = $(if ($Parameters.Height) { $Parameters.Height } else { 32 })
animParams.mode = "$(if ($Parameters.Mode) { $Parameters.Mode } else { 'Loop' })"
$descriptionParam

-- Enhance parameters with Ollama if available
if animParams.description and animParams.description ~= "" then
    print("Using Ollama-enhanced animation generation...")
    print("Description: " .. (animParams.description:sub(1, 100) or ""))
    if OllamaHelper.isAvailable() then
        local enhancedDesc = OllamaHelper.enhanceDescription(animParams.description)
        if enhancedDesc and enhancedDesc ~= animParams.description then
            animParams.description = enhancedDesc
            print("  ✓ Description enhanced by Ollama")
        end
    end
    animParams = OllamaHelper.enhanceProceduralParams(animParams, animParams.description)
end

local bundle = generate_animation_async(animParams):get()
if bundle and bundle:isValid() then
    print("✓ Animation generated successfully")
    print("  Frames: " .. bundle.frameCount)
    export_animation_bundle(bundle, "$($OutputDir.Replace('\', '\\'))")
else
    print("✗ Animation generation failed")
end
"@
        }
        
        "Icon" {
            $outputPath = "$($OutputDir.Replace('\', '\\'))\\$(if ($AssetName) { $AssetName } else { 'generated_icon' }).png"
            $size = if ($Parameters.Size) { $Parameters.Size } else { 32 }
            
            # Try Ollama first if description is available
            $ollamaSuccess = $false
            if ($Parameters.Description -and $Parameters.Description.Trim().Length -gt 0) {
                Write-Host "Attempting Ollama-based icon generation..." -ForegroundColor Cyan
                try {
                    if (Test-Path $ollamaHelper) {
                        $ollamaResult = & $ollamaHelper -Description $Parameters.Description -Width $size -Height $size -OutputPath $outputPath -ErrorAction Stop 2>&1
                        if ($LASTEXITCODE -eq 0 -and (Test-Path $outputPath)) {
                            Write-Host "✓ Icon generated with Ollama successfully" -ForegroundColor Green
                            $ollamaSuccess = $true
                        }
                    }
                } catch {
                    Write-Host "⚠ Ollama generation failed, using description-enhanced C++ backend..." -ForegroundColor Yellow
                }
            }
            
            $descriptionParam = if ($Parameters.Description) { 
                $desc = $Parameters.Description -replace '"', '\"'
                "description = `"$desc`","
            } else { "" }
            
            if ($ollamaSuccess) {
                @"
-- Icon was generated using Ollama
print("✓ Icon generated with Ollama")
print("  Output: $outputPath")
"@
            } else {
                @"
-- Icon Generation via C++ Backend with Ollama Description Enhancement
require("agents.GeneratorAgent.IconAssetFactory")
require("OllamaLuaHelper")  -- Load Ollama helper for description enhancement

-- Set bridge script path for Ollama helper
OllamaHelper.BRIDGE_SCRIPT = "$bridgeScriptPath"

initialize_icon_asset_factory(500, 4)

local iconParams = create_icon_params()
iconParams.id = "$(if ($AssetName) { $AssetName } else { 'generated_icon' })"
iconParams.size = $size
iconParams.style = "$(if ($Parameters.Style) { $Parameters.Style } else { 'Default' })"
iconParams.shape = "$(if ($Parameters.Shape) { $Parameters.Shape } else { 'Circle' })"
iconParams.color = {$(if ($Parameters.Color) { $Parameters.Color } else { '1.0, 0.5, 0.0' })}
$descriptionParam

-- Enhance parameters with Ollama if available
if iconParams.description and iconParams.description ~= "" then
    print("Using Ollama-enhanced icon generation...")
    if OllamaHelper.isAvailable() then
        local enhancedDesc = OllamaHelper.enhanceDescription(iconParams.description)
        if enhancedDesc and enhancedDesc ~= iconParams.description then
            iconParams.description = enhancedDesc
            print("  ✓ Description enhanced by Ollama")
        end
    end
    iconParams = OllamaHelper.enhanceProceduralParams(iconParams, iconParams.description)
end

local bundle = generate_icon_async(iconParams):get()
if bundle and bundle:isValid() then
    print("✓ Icon generated successfully")
    export_icon_bundle(bundle, "$($OutputDir.Replace('\', '\\'))")
else
    print("✗ Icon generation failed")
end
"@
            }
        }
        
        "Spell" {
            @"
-- Spell Generation via C++ Backend
require("agents.GeneratorAgent.GeneratorAgent")

local agent = GeneratorAgent.new()
agent:init()

local spellDef = {
    id = "$(if ($AssetName) { $AssetName } else { 'generated_spell' })",
    name = "$(if ($Parameters.Name) { $Parameters.Name } else { 'Generated Spell' })",
    description = "$(if ($Parameters.Description) { $Parameters.Description } else { 'A generated spell' })",
    type = "$(if ($Parameters.SpellType) { $Parameters.SpellType } else { 'projectile' })",
    power = $(if ($Parameters.Power) { $Parameters.Power } else { 1.0 }),
    cost = $(if ($Parameters.Cost) { $Parameters.Cost } else { 1.0 })
}

local result = agent:generateSpellFromDefinition(spellDef)
if result then
    print("✓ Spell generated successfully")
    print("  ID: " .. result.id)
    agent:exportToFile("$($OutputDir.Replace('\', '\\'))\\$(if ($AssetName) { $AssetName } else { 'spell' }).json")
else
    print("✗ Spell generation failed")
end

agent:shutdown()
"@
        }
        
        default {
            @"
-- Generic Asset Generation
print("Generator type: $GeneratorType")
print("Action: $Action")
print("Asset name: $AssetName")
print("Output directory: $OutputDir")
"@
        }
    }
} else {
    $luaContent = $LuaScript
}

# Write Lua script
[System.IO.File]::WriteAllText($luaScriptPath, $luaContent, [System.Text.UTF8Encoding]::new($false))

Write-Host "Generated Lua script: $luaScriptPath" -ForegroundColor Gray
Write-Host ""

# Find Starbound executable or Lua interpreter
$starboundExe = $null
$starboundPaths = @(
    "F:\Games\OpenStarbound\win64\starbound.exe",
    "F:\Games\OpenStarbound\starbound.exe",
    "${env:ProgramFiles}\Steam\steamapps\common\Starbound\win64\starbound.exe"
)

foreach ($path in $starboundPaths) {
    if (Test-Path $path) {
        $starboundExe = $path
        break
    }
}

# Alternative: Use Lua directly if available
$luaExe = Get-Command "lua" -ErrorAction SilentlyContinue

if ($starboundExe) {
    Write-Host "Found Starbound executable: $starboundExe" -ForegroundColor Green
    Write-Host "Note: Lua script execution requires Starbound to be running with mod loaded" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To execute the script:" -ForegroundColor Cyan
    Write-Host "  1. Start Starbound with the mod loaded" -ForegroundColor Gray
    Write-Host "  2. Use the in-game console or mod interface" -ForegroundColor Gray
    Write-Host "  3. Load the script: $luaScriptPath" -ForegroundColor Gray
    Write-Host ""
} elseif ($luaExe) {
    Write-Host "Found Lua interpreter: $($luaExe.Source)" -ForegroundColor Green
    Write-Host "Executing Lua script..." -ForegroundColor Cyan
    
    # Note: This may not work directly if the script requires Starbound-specific bindings
    # It's better to execute via Starbound's Lua environment
    Write-Host "  Warning: Direct Lua execution may not work without Starbound context" -ForegroundColor Yellow
} else {
    Write-Host "Starbound executable or Lua interpreter not found" -ForegroundColor Yellow
    Write-Host "Lua script saved to: $luaScriptPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To execute:" -ForegroundColor Cyan
    Write-Host "  1. Start Starbound with the mod loaded" -ForegroundColor Gray
    Write-Host "  2. Use the in-game console or mod interface" -ForegroundColor Gray
    Write-Host "  3. Load: $luaScriptPath" -ForegroundColor Gray
    Write-Host ""
}

# Create integration helper script (enhanced version)
$helperScript = @"
-- Integration Helper for PowerShell -> C++ Backend
-- This script can be loaded in Starbound to execute asset generation
-- Usage: local helper = require("/assets/integration_helper"); helper.execute("path/to/script.lua")

local IntegrationHelper = {}

-- Check if we're running in Starbound context
local function isStarboundContext()
    return type(sb) == "table" or type(world) == "table" or type(player) == "table"
end

-- Execute a Lua script with proper error handling
function IntegrationHelper.execute(script_path)
    if not script_path then
        print("[IntegrationHelper] Error: No script path provided")
        return false
    end
    
    -- Normalize path
    if not script_path:match("^/") then
        script_path = "/" .. script_path
    end
    
    local file = io.open(script_path, "r")
    if not file then
        print("[IntegrationHelper] Error: Could not open script: " .. script_path)
        print("[IntegrationHelper] Make sure the path is correct and the file exists")
        return false
    end
    
    local content = file:read("*all")
    file:close()
    
    if not content or content == "" then
        print("[IntegrationHelper] Error: Script file is empty: " .. script_path)
        return false
    end
    
    -- Create environment with Starbound bindings if available
    local env = {}
    if isStarboundContext() then
        if sb then env.sb = sb end
        if world then env.world = world end
        if player then env.player = player end
        if root then env.root = root end
        if vec2 then env.vec2 = vec2 end
        if math then env.math = math end
        if string then env.string = string end
        if table then env.table = table end
        if type then env.type = type end
        if print then env.print = print end
        if pcall then env.pcall = pcall end
        if error then env.error = error end
        if pairs then env.pairs = pairs end
        if ipairs then env.ipairs = ipairs end
        if tostring then env.tostring = tostring end
        if tonumber then env.tonumber = tonumber end
    else
        env = _ENV or _G
    end
    
    -- Load script
    local func, err = load(content, script_path, "t", env)
    if not func then
        print("[IntegrationHelper] Error loading script: " .. tostring(err))
        return false
    end
    
    -- Execute script
    print("[IntegrationHelper] Executing script: " .. script_path)
    local success, result = pcall(func)
    if not success then
        print("[IntegrationHelper] Error executing script: " .. tostring(result))
        return false
    end
    
    print("[IntegrationHelper] Script executed successfully")
    return true, result
end

-- Execute multiple scripts in sequence
function IntegrationHelper.executeBatch(script_paths)
    if not script_paths or type(script_paths) ~= "table" then
        print("[IntegrationHelper] Error: script_paths must be a table")
        return false
    end
    
    local success_count = 0
    for i, path in ipairs(script_paths) do
        print(string.format("[IntegrationHelper] Executing script %d/%d: %s", i, #script_paths, path))
        local success = IntegrationHelper.execute(path)
        if success then
            success_count = success_count + 1
        end
    end
    
    print(string.format("[IntegrationHelper] Batch complete: %d/%d scripts succeeded", success_count, #script_paths))
    return success_count == #script_paths
end

-- Check Starbound context and provide info
function IntegrationHelper.getContextInfo()
    local info = {
        isStarbound = isStarboundContext(),
        hasSb = type(sb) == "table",
        hasWorld = type(world) == "table",
        hasPlayer = type(player) == "table"
    }
    
    print("[IntegrationHelper] Context Info:")
    print("  - Starbound Context: " .. tostring(info.isStarbound))
    print("  - Has 'sb' global: " .. tostring(info.hasSb))
    print("  - Has 'world' global: " .. tostring(info.hasWorld))
    print("  - Has 'player' global: " .. tostring(info.hasPlayer))
    
    return info
end

-- Export module
return IntegrationHelper
"@

# Validate $OutputDir before Join-Path
$helperPath = Join-Path $OutputDir "integration_helper.lua"
if ([string]::IsNullOrWhiteSpace($helperPath)) {
    Write-Host "  [FAIL] helperPath is null (`${OutputDir}: '`${OutputDir}')" -ForegroundColor Red
    continue
}
[System.IO.File]::WriteAllText($helperPath, $helperScript, [System.Text.UTF8Encoding]::new($false))

Write-Host "Integration helper saved to: $helperPath" -ForegroundColor Green
Write-Host ""

# Create metadata
$metadata = @{
    GeneratorType = $GeneratorType
    Action = $Action
    AssetName = $AssetName
    OutputDirectory = $OutputDir
    LuaScriptPath = $luaScriptPath
    BackendPath = $BackendPath
    GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Parameters = $Parameters
}

# Validate $OutputDir before Join-Path
$metadataPath = Join-Path $OutputDir "generation_metadata.json"
if ([string]::IsNullOrWhiteSpace($metadataPath)) {
    Write-Host "  [FAIL] metadataPath is null (`${OutputDir}: '`${OutputDir}')" -ForegroundColor Red
    continue
}
$metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Bridge Setup Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Lua Script: $luaScriptPath" -ForegroundColor Green
Write-Host "Output Directory: $OutputDir" -ForegroundColor Green
Write-Host "Metadata: $metadataPath" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Start Starbound with the mod loaded" -ForegroundColor Gray
Write-Host "  2. Use the in-game console or mod interface" -ForegroundColor Gray
Write-Host "  3. Execute the Lua script to generate assets" -ForegroundColor Gray
Write-Host ""

