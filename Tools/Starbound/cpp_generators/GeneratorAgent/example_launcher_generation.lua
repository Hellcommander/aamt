-- Alchemical Grenade Launcher Asset Generation Pipeline Example
-- This script demonstrates the comprehensive asset generation capabilities
-- for creating bespoke alchemical grenade launchers with full customization.

-- Import the launcher generation system
local launcher = require("alchemical_launcher_generator")

-- Example 1: Phoenix Catapult - A fiery alchemical launcher
local phoenixParams = createDefaultLauncherParams()
phoenixParams.id = "phoenix_catapult"
phoenixParams.launcherType = LauncherType.CATAPULT
phoenixParams.materialMain = MaterialType.STEEL
phoenixParams.materialSecondary = MaterialType.WOOD
phoenixParams.sightType = SightType.IRON_SIGHT
phoenixParams.engravingPattern = EngravingPattern.PHOENIX

-- Physical properties
phoenixParams.barrelLength = 1.2
phoenixParams.barrelRadius = 0.1
phoenixParams.magazineCapacity = 6
phoenixParams.reloadTime = 2.5
phoenixParams.fireRate = 0.5

-- Visual properties - fiery theme
phoenixParams.colorPrimary = {0.7, 0.2, 0.1}      -- deep red
phoenixParams.colorSecondary = {0.3, 0.15, 0.05}   -- dark wood
phoenixParams.colorAccent = {1.0, 0.6, 0.2}        -- orange accent
phoenixParams.glowColor = {1.0, 0.8, 0.4}          -- golden glow
phoenixParams.noiseScale = 2.0
phoenixParams.metallicness = 0.8
phoenixParams.roughness = 0.3

-- Muzzle effects - intense fire
phoenixParams.muzzleGlowIntensity = 2.0
phoenixParams.muzzleFlashSize = 1.0
phoenixParams.muzzleFlashColor = {1.0, 0.8, 0.4}
phoenixParams.muzzleSmokeCount = 30
phoenixParams.muzzleSmokeColor = {0.3, 0.1, 0.05}

-- Particle effects
phoenixParams.enableShellEjection = true
phoenixParams.shellEjectionCount = 1
phoenixParams.shellEjectionSpeed = 5.0
phoenixParams.enableHeatDistortion = true
phoenixParams.heatDistortionStrength = 0.5
phoenixParams.heatDistortionRadius = 0.4

-- Audio properties
phoenixParams.soundVolume = 1.0
phoenixParams.soundPitch = 1.1
phoenixParams.enableEcho = true
phoenixParams.echoDelay = 0.15
phoenixParams.enableReverb = true
phoenixParams.reverbIntensity = 0.4

-- Physics properties
phoenixParams.recoilForce = 35.0
phoenixParams.recoilRecovery = 4.0
phoenixParams.mass = 6.0

-- Ornamentation
phoenixParams.ornamentation = true
phoenixParams.ornamentationIntensity = 0.7
phoenixParams.enableRunes = true
phoenixParams.runeGlowIntensity = 0.8

-- UI parameters for Phoenix launcher
local phoenixUI = createDefaultUIParams()
phoenixUI.iconSize = 64
phoenixUI.borderColor = {1.0, 0.6, 0.2, 0.9}
phoenixUI.backgroundShape = BackgroundShape.HEXAGON
phoenixUI.flashOnSelect = true
phoenixUI.enableGlow = true
phoenixUI.glowColor = {1.0, 0.8, 0.4}
phoenixUI.glowIntensity = 1.2
phoenixUI.label = "Phoenix"
phoenixUI.enableLabel = true
phoenixUI.labelColor = {1.0, 0.8, 0.4}

-- Example 2: Crystal Staff - A magical alchemical launcher
local crystalParams = createDefaultLauncherParams()
crystalParams.id = "crystal_staff"
crystalParams.launcherType = LauncherType.MAGIC_STAFF
crystalParams.materialMain = MaterialType.CRYSTAL
crystalParams.materialSecondary = MaterialType.MAGIC
crystalParams.sightType = SightType.MAGIC_SIGHT
crystalParams.engravingPattern = EngravingPattern.MAGIC_SIGILS

-- Physical properties
crystalParams.barrelLength = 1.5
crystalParams.barrelRadius = 0.08
crystalParams.magazineCapacity = 8
crystalParams.reloadTime = 1.8
crystalParams.fireRate = 0.8

-- Visual properties - crystalline theme
crystalParams.colorPrimary = {0.2, 0.6, 1.0}       -- blue crystal
crystalParams.colorSecondary = {0.8, 0.9, 1.0}      -- light blue
crystalParams.colorAccent = {0.4, 0.8, 1.0}         -- cyan accent
crystalParams.glowColor = {0.6, 0.8, 1.0}           -- blue glow
crystalParams.noiseScale = 1.5
crystalParams.metallicness = 0.2
crystalParams.roughness = 0.1
crystalParams.transparency = 0.3
crystalParams.refractionIndex = 1.5

-- Muzzle effects - magical
crystalParams.muzzleGlowIntensity = 1.8
crystalParams.muzzleFlashSize = 0.6
crystalParams.muzzleFlashColor = {0.6, 0.8, 1.0}
crystalParams.muzzleSmokeCount = 15
crystalParams.muzzleSmokeColor = {0.4, 0.6, 0.8}

-- Shader effects
crystalParams.enableRefraction = true
crystalParams.refractionStrength = 0.8
crystalParams.enableReflection = true
crystalParams.reflectionStrength = 0.9
crystalParams.enableEmission = true
crystalParams.emissionStrength = 0.6

-- Audio properties
crystalParams.soundVolume = 0.8
crystalParams.soundPitch = 1.3
crystalParams.enableEcho = true
crystalParams.echoDelay = 0.2
crystalParams.echoDecay = 0.7

-- Physics properties
crystalParams.recoilForce = 20.0
crystalParams.recoilRecovery = 6.0
crystalParams.mass = 3.0

-- Ornamentation
crystalParams.ornamentation = true
crystalParams.ornamentationIntensity = 0.9
crystalParams.enableCrystals = true
crystalParams.crystalGlowIntensity = 1.0

-- UI parameters for Crystal staff
local crystalUI = createDefaultUIParams()
crystalUI.iconSize = 64
crystalUI.borderColor = {0.6, 0.8, 1.0, 0.9}
crystalUI.backgroundShape = BackgroundShape.CIRCLE
crystalUI.flashOnSelect = true
crystalUI.enableGlow = true
crystalUI.glowColor = {0.6, 0.8, 1.0}
crystalUI.glowIntensity = 1.5
crystalUI.enablePulse = true
crystalUI.pulseFrequency = 2.0
crystalUI.pulseAmplitude = 0.2
crystalUI.label = "Crystal"
crystalUI.enableLabel = true
crystalUI.labelColor = {0.6, 0.8, 1.0}

-- Example 3: Dragon Cannon - A powerful alchemical launcher
local dragonParams = createDefaultLauncherParams()
dragonParams.id = "dragon_cannon"
dragonParams.launcherType = LauncherType.CANNON
dragonParams.materialMain = MaterialType.BRONZE
dragonParams.materialSecondary = MaterialType.STEEL
dragonParams.sightType = SightType.SCOPE
dragonParams.engravingPattern = EngravingPattern.DRAGON

-- Physical properties
dragonParams.barrelLength = 1.8
dragonParams.barrelRadius = 0.15
dragonParams.magazineCapacity = 4
dragonParams.reloadTime = 3.5
dragonParams.fireRate = 0.3

-- Visual properties - dragon theme
dragonParams.colorPrimary = {0.8, 0.4, 0.1}        -- bronze
dragonParams.colorSecondary = {0.6, 0.6, 0.6}       -- steel
dragonParams.colorAccent = {1.0, 0.3, 0.1}          -- red accent
dragonParams.glowColor = {1.0, 0.4, 0.2}            -- red glow
dragonParams.noiseScale = 3.0
dragonParams.metallicness = 0.9
dragonParams.roughness = 0.2

-- Muzzle effects - powerful
dragonParams.muzzleGlowIntensity = 2.5
dragonParams.muzzleFlashSize = 1.5
dragonParams.muzzleFlashColor = {1.0, 0.5, 0.2}
dragonParams.muzzleSmokeCount = 40
dragonParams.muzzleSmokeColor = {0.2, 0.1, 0.05}

-- Particle effects
dragonParams.enableShellEjection = true
dragonParams.shellEjectionCount = 2
dragonParams.shellEjectionSpeed = 8.0
dragonParams.enableHeatDistortion = true
dragonParams.heatDistortionStrength = 0.8
dragonParams.heatDistortionRadius = 0.6

-- Audio properties
dragonParams.soundVolume = 1.2
dragonParams.soundPitch = 0.8
dragonParams.enableEcho = true
dragonParams.echoDelay = 0.3
dragonParams.enableReverb = true
dragonParams.reverbIntensity = 0.6

-- Physics properties
dragonParams.recoilForce = 50.0
dragonParams.recoilRecovery = 3.0
dragonParams.mass = 12.0

-- Ornamentation
dragonParams.ornamentation = true
dragonParams.ornamentationIntensity = 0.8
dragonParams.enableGems = true
dragonParams.gemGlowIntensity = 0.9

-- UI parameters for Dragon cannon
local dragonUI = createDefaultUIParams()
dragonUI.iconSize = 64
dragonUI.borderColor = {1.0, 0.4, 0.2, 0.9}
dragonUI.backgroundShape = BackgroundShape.DIAMOND
dragonUI.flashOnSelect = true
dragonUI.enableGlow = true
dragonUI.glowColor = {1.0, 0.4, 0.2}
dragonUI.glowIntensity = 1.3
dragonUI.label = "Dragon"
dragonUI.enableLabel = true
dragonUI.labelColor = {1.0, 0.4, 0.2}

-- Function to generate launchers synchronously
local function generateLauncherSynchronous(params, uiParams)
    print("Generating launcher: " .. params.id)
    local bundle = spawn_launcher(params, uiParams)
    print("Launcher generated successfully!")
    print("  Mesh handle: " .. bundle.meshBody)
    print("  Texture handle: " .. bundle.textureBody)
    print("  Shader handle: " .. bundle.shaderBody)
    print("  Muzzle flash: " .. bundle.muzzleFlash)
    print("  Muzzle smoke: " .. bundle.muzzleSmoke)
    if bundle.shellEjection then
        print("  Shell ejection: " .. bundle.shellEjection)
    end
    if bundle.heatDistortion then
        print("  Heat distortion: " .. bundle.heatDistortion)
    end
    print("  Recoil physics: " .. bundle.recoilPhysics)
    print("  Magazine physics: " .. bundle.magazinePhysics)
    print("  Fire SFX: " .. bundle.sfxFire)
    print("  Reload SFX: " .. bundle.sfxReload)
    if bundle.sfxShellEject then
        print("  Shell eject SFX: " .. bundle.sfxShellEject)
    end
    if bundle.sfxHeatDistortion then
        print("  Heat distortion SFX: " .. bundle.sfxHeatDistortion)
    end
    print("  Icon: " .. bundle.icon)
    print("  Generation time: " .. bundle.generationTime .. "ms")
    print("  Vertices: " .. bundle.vertexCount)
    print("  Triangles: " .. bundle.triangleCount)
    print("  Particles: " .. bundle.particleCount)
    print("  GPU Accelerated: " .. (bundle.gpuAccelerated and "Yes" or "No"))
    return bundle
end

-- Function to generate launchers asynchronously
local function generateLauncherAsynchronous(params, uiParams)
    print("Starting async generation for: " .. params.id)
    spawn_launcher_async(params, uiParams)
end

-- Function to poll for completed async generations
local function pollAsyncGenerations()
    poll_assets()
end

-- Main execution
print("=== Alchemical Grenade Launcher Generation Pipeline ===")
print("Generating three different launcher types...")

-- Generate launchers synchronously
print("\n--- Generating Phoenix Catapult ---")
local phoenixBundle = generateLauncherSynchronous(phoenixParams, phoenixUI)

print("\n--- Generating Crystal Staff ---")
local crystalBundle = generateLauncherSynchronous(crystalParams, crystalUI)

print("\n--- Generating Dragon Cannon ---")
local dragonBundle = generateLauncherSynchronous(dragonParams, dragonUI)

-- Example of async generation
print("\n--- Starting Async Generation ---")
generateLauncherAsynchronous(phoenixParams, phoenixUI)
generateLauncherAsynchronous(crystalParams, crystalUI)
generateLauncherAsynchronous(dragonParams, dragonUI)

-- Poll for completion
print("\n--- Polling for Async Completion ---")
for i = 1, 10 do
    pollAsyncGenerations()
    if #pendingLaunchers == 0 then
        break
    end
    print("Waiting for async generations to complete...")
    -- In a real application, you'd wait here
end

print("\n=== Generation Complete ===")
print("All launchers have been generated successfully!")
print("Each launcher includes:")
print("  - Procedural mesh with barrel, frame, magazine, and grip")
print("  - PBR textures with metal and wood materials")
print("  - Custom shaders with dynamic properties")
print("  - Muzzle flash and smoke particle effects")
print("  - Shell ejection and heat distortion effects")
print("  - Physics simulation for recoil and magazine")
print("  - Procedural audio with spatial effects")
print("  - Custom UI icons with animations")
print("  - Performance metrics and GPU acceleration")

-- Example of parameter serialization
print("\n--- Parameter Serialization Example ---")
local phoenixJson = launcherParamsToJson(phoenixParams)
print("Phoenix params JSON: " .. phoenixJson:dump())

local uiJson = uiParamsToJson(phoenixUI)
print("UI params JSON: " .. uiJson:dump())

-- Example of parameter deserialization
local deserializedParams = launcherParamsFromJson(phoenixJson)
print("Deserialized launcher ID: " .. deserializedParams.id)

local deserializedUI = uiParamsFromJson(uiJson)
print("Deserialized UI icon size: " .. deserializedUI.iconSize)

print("\n=== Pipeline Complete ===") 