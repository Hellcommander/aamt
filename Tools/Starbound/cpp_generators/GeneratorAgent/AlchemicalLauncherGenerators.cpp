#include "AlchemicalLauncherFactory.hpp"
#include "core/Log.hpp"
#include "core/rendering/MeshBuilder.hpp"
#include "core/rendering/TextureBuilder.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include "core/physics/PhysicsBuilder.hpp"
#include "core/audio/AudioBuilder.hpp"
#include "core/ui/IconBuilder.hpp"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <cmath>
#include <random>

namespace MagiTech {
namespace AlchemicalLaunchers {

namespace MeshGen {
    MeshHandle buildLauncherBody(const AlchemicalLauncherParams& p) {
        Log::info("Building launcher mesh for: {}", p.id);
        
        // Create barrel as extruded cylinder
        auto barrel = MeshBuilder::cylinder(p.barrelRadius, p.barrelLength, 24);
        barrel.translate({0, 0, p.barrelLength * 0.5f});
        
        // Create frame as box-prism with bevels
        auto frame = MeshBuilder::box(
            {p.frameWidth, p.frameHeight, p.frameLength}, 
            0.02f  // bevel radius
        );
        frame.translate({0, 0, p.frameLength * 0.5f});
        
        // Create magazine cylinder (revolving drum)
        auto drum = MeshBuilder::cylinder(
            p.magazineRadius, 
            p.magazineHeight, 
            16
        );
        drum.translate({0, 0, p.magazineHeight * 0.5f + p.frameLength});
        
        // Create grip
        auto grip = MeshBuilder::box(
            {p.gripWidth, p.gripHeight, p.gripLength}, 
            0.01f  // bevel radius
        );
        grip.translate({0, -p.gripHeight * 0.5f - p.frameHeight * 0.5f, p.gripLength * 0.5f});
        
        // Create sight if specified
        if (p.sightType != SightType::NONE) {
            auto sight = MeshBuilder::box(
                {p.sightWidth, p.sightHeight, 0.05f}, 
                0.005f
            );
            sight.translate({0, p.frameHeight * 0.5f + p.sightHeight * 0.5f, p.frameLength * 0.8f});
            frame = MeshBuilder::merge({frame, sight});
        }
        
        // Apply engravings if specified
        if (p.ornamentation && p.engravingPattern != EngravingPattern::NONE) {
            barrel = MeshBuilder::applyEngravings(barrel, p.engravingPattern, p.ornamentationIntensity);
        }
        
        // Merge all components
        auto finalMesh = MeshBuilder::merge({barrel, frame, drum, grip});
        
        // Apply material properties
        finalMesh.setMetallicness(p.metallicness);
        finalMesh.setRoughness(p.roughness);
        finalMesh.setEmissivePower(p.emissivePower);
        
        return finalMesh.getHandle();
    }
}

namespace TextureGen {
    TextureHandle buildLauncherTexture(const AlchemicalLauncherParams& p) {
        Log::info("Building launcher texture for: {}", p.id);
        
        // Generate procedural noise for metal surface
        auto metalNoise = TextureBuilder::generateNoise(512, p.noiseScale);
        auto woodNoise = TextureBuilder::generateNoise(256, p.noiseScale * 0.5f);
        
        // Create material-specific textures
        auto metalTexture = TextureBuilder::createPBRMaterial(
            p.colorPrimary, 
            metalNoise, 
            p.metallicness, 
            p.roughness
        );
        
        auto woodTexture = TextureBuilder::createPBRMaterial(
            p.colorSecondary, 
            woodNoise, 
            0.0f,  // non-metallic
            0.6f   // rough
        );
        
        // Create normal map from noise
        auto normalMap = TextureBuilder::generateNormalMap(metalNoise, p.noiseIntensity);
        
        // Create roughness map
        auto roughnessMap = TextureBuilder::createRoughnessMap(
            {metalTexture.roughness, woodTexture.roughness}, 
            {0.2f, 0.6f}
        );
        
        // Create metallic map
        auto metallicMap = TextureBuilder::createMetallicMap(
            {metalTexture.metallic, woodTexture.metallic}, 
            {1.0f, 0.0f}
        );
        
        // Combine textures into final PBR material
        auto finalTexture = TextureBuilder::combinePBRTextures({
            metalTexture.albedo,
            woodTexture.albedo,
            normalMap,
            roughnessMap,
            metallicMap
        });
        
        return finalTexture.getHandle();
    }
}

namespace ShaderGen {
    ShaderHandle buildLauncherShader(const AlchemicalLauncherParams& p) {
        Log::info("Building launcher shader for: {}", p.id);
        
        auto shader = ShaderBuilder::create("LauncherPBR");
        
        // Add uniforms for dynamic properties
        shader.addUniform("uMuzzleGlow", p.muzzleGlowIntensity);
        shader.addUniform("uColorPrimary", p.colorPrimary);
        shader.addUniform("uColorSecondary", p.colorSecondary);
        shader.addUniform("uGlowColor", p.glowColor);
        shader.addUniform("uEmissivePower", p.emissivePower);
        shader.addUniform("uMetallicness", p.metallicness);
        shader.addUniform("uRoughness", p.roughness);
        
        // Add special effects
        if (p.enableDistortion) {
            shader.addUniform("uDistortionStrength", p.distortionStrength);
        }
        
        if (p.enableRefraction) {
            shader.addUniform("uRefractionIndex", p.refractionIndex);
            shader.addUniform("uRefractionStrength", p.refractionStrength);
        }
        
        if (p.enableReflection) {
            shader.addUniform("uReflectionStrength", p.reflectionStrength);
        }
        
        if (p.enableEmission) {
            shader.addUniform("uEmissionStrength", p.emissionStrength);
        }
        
        // Compile shader
        return shader.compile();
    }
}

namespace ParticleGen {
    ParticleHandle buildMuzzleFlash(const AlchemicalLauncherParams& p) {
        Log::info("Building muzzle flash for: {}", p.id);
        
        auto emitter = ParticleBuilder::createEmitter(ParticleType::BURST);
        
        // Configure burst properties
        emitter.setCount(8);
        emitter.setLifetime(p.muzzleFlashDuration);
        emitter.setStartSize(p.muzzleFlashSize);
        emitter.setEndSize(p.muzzleFlashSize * 0.3f);
        emitter.setColor(p.muzzleFlashColor);
        emitter.setAlpha(1.0f, 0.0f);  // fade to transparent
        
        // Configure shape as cone
        emitter.setShape(ParticleShape::CONE);
        emitter.setConeAngle(30.0f);
        emitter.setDirection({0, 0, 1});  // forward
        
        // Add glow effect
        if (p.muzzleGlowIntensity > 0) {
            emitter.setGlowIntensity(p.muzzleGlowIntensity);
            emitter.setGlowColor(p.muzzleFlashColor);
        }
        
        return emitter.getHandle();
    }
    
    ParticleHandle buildMuzzleSmoke(const AlchemicalLauncherParams& p) {
        Log::info("Building muzzle smoke for: {}", p.id);
        
        auto emitter = ParticleBuilder::createEmitter(ParticleType::BILLBOARD);
        
        // Configure smoke properties
        emitter.setRate(p.muzzleSmokeCount);
        emitter.setLifetime(p.muzzleSmokeLifetime);
        emitter.setStartSize(0.2f);
        emitter.setEndSize(0.5f);
        emitter.setColor(p.muzzleSmokeColor);
        emitter.setAlpha(0.6f, 0.0f);  // fade to transparent
        
        // Configure physics
        emitter.setGravity({0, -0.5f, 0});
        emitter.setAirResistance(0.1f);
        emitter.setSpeed(p.muzzleSmokeSpeed);
        
        // Configure shape
        emitter.setShape(ParticleShape::SPHERE);
        emitter.setRadius(0.1f);
        
        return emitter.getHandle();
    }
    
    ParticleHandle buildShellEjection(const AlchemicalLauncherParams& p) {
        Log::info("Building shell ejection for: {}", p.id);
        
        auto emitter = ParticleBuilder::createEmitter(ParticleType::BURST);
        
        // Configure shell ejection properties
        emitter.setCount(p.shellEjectionCount);
        emitter.setLifetime(p.shellEjectionLifetime);
        emitter.setStartSize(0.05f);
        emitter.setEndSize(0.05f);  // shells don't change size
        emitter.setColor({0.8f, 0.7f, 0.5f});  // brass color
        emitter.setAlpha(1.0f, 1.0f);  // solid shells
        
        // Configure physics for realistic shell ejection
        emitter.setGravity({0, -9.8f, 0});
        emitter.setAirResistance(0.05f);
        emitter.setSpeed(p.shellEjectionSpeed);
        
        // Configure shape as small cylinders
        emitter.setShape(ParticleShape::CYLINDER);
        emitter.setRadius(0.02f);
        emitter.setHeight(0.03f);
        
        // Eject shells to the right side
        emitter.setDirection({1, 0.5f, 0});
        emitter.setConeAngle(15.0f);
        
        return emitter.getHandle();
    }
    
    ParticleHandle buildHeatDistortion(const AlchemicalLauncherParams& p) {
        Log::info("Building heat distortion for: {}", p.id);
        
        auto emitter = ParticleBuilder::createEmitter(ParticleType::CONTINUOUS);
        
        // Configure heat distortion properties
        emitter.setRate(50);  // continuous distortion
        emitter.setLifetime(2.0f);
        emitter.setStartSize(p.heatDistortionRadius);
        emitter.setEndSize(p.heatDistortionRadius * 1.5f);
        emitter.setColor({0.1f, 0.1f, 0.1f});  // dark distortion
        emitter.setAlpha(0.3f, 0.0f);  // subtle effect
        
        // Configure physics for heat rising
        emitter.setGravity({0, 2.0f, 0});  // heat rises
        emitter.setAirResistance(0.2f);
        emitter.setSpeed(0.5f);
        
        // Configure shape as sphere around muzzle
        emitter.setShape(ParticleShape::SPHERE);
        emitter.setRadius(p.heatDistortionRadius);
        
        // Position around muzzle
        emitter.setPosition({0, 0, p.barrelLength});
        
        // Add distortion effect
        emitter.setDistortionStrength(p.heatDistortionStrength);
        
        return emitter.getHandle();
    }
}

namespace PhysGen {
    PhysicsHandle buildRecoil(const AlchemicalLauncherParams& p) {
        Log::info("Building recoil physics for: {}", p.id);
        
        auto physics = PhysicsBuilder::create();
        
        // Configure recoil system
        physics.enableRecoil(p.recoilForce, p.recoilRecovery);
        
        // Configure magazine system
        physics.setupMagazine(p.magazineCapacity, p.reloadTime);
        
        // Configure physics properties
        physics.setMass(p.mass);
        physics.setDensity(p.density);
        physics.setFriction(p.friction);
        physics.setBounciness(p.bounciness);
        
        // Enable collision if specified
        if (p.enableCollision) {
            physics.enableCollision(p.collisionRadius);
        }
        
        // Enable gravity if specified
        if (p.enableGravity) {
            physics.enableGravity();
        }
        
        // Enable air resistance if specified
        if (p.enableAirResistance) {
            physics.enableAirResistance(p.airResistanceFactor);
        }
        
        // Enable bounce if specified
        if (p.enableBounce) {
            physics.enableBounce(p.bounceFactor);
        }
        
        return physics.getHandle();
    }
    
    PhysicsHandle buildMagazinePhysics(const AlchemicalLauncherParams& p) {
        Log::info("Building magazine physics for: {}", p.id);
        
        auto physics = PhysicsBuilder::create();
        
        // Configure revolving drum physics
        physics.setupRevolvingDrum(p.magazineCapacity, p.magazineRadius);
        
        // Configure rotation mechanics
        physics.setRotationSpeed(360.0f / p.magazineCapacity);  // degrees per chamber
        physics.setRotationDelay(p.reloadTime / p.magazineCapacity);
        
        // Configure chamber physics
        physics.setChamberSize(p.barrelRadius * 0.8f);
        physics.setChamberDepth(p.barrelLength * 0.3f);
        
        // Configure loading mechanism
        physics.setLoadingForce(50.0f);
        physics.setEjectionForce(p.shellEjectionSpeed);
        
        return physics.getHandle();
    }
}

namespace AudioGen {
    AudioHandle buildFireSFX(const AlchemicalLauncherParams& p) {
        Log::info("Building fire SFX for: {}", p.id);
        
        auto audio = AudioBuilder::createProcedural();
        
        // Configure metallic blast sound
        audio.setType(AudioType::METALLIC_BLAST);
        audio.setVolume(p.soundVolume);
        audio.setPitch(p.soundPitch);
        audio.setDuration(p.soundDuration);
        
        // Configure spatial audio
        if (p.enableSpatialAudio) {
            audio.enableSpatial(p.audioDistance);
        }
        
        // Configure echo effect
        if (p.enableEcho) {
            audio.enableEcho(p.echoDelay, p.echoDecay);
        }
        
        // Configure reverb effect
        if (p.enableReverb) {
            audio.enableReverb(p.reverbIntensity);
        }
        
        // Modulate by fire rate
        audio.modulateByParameter("fireRate", p.fireRate);
        
        return audio.getHandle();
    }
    
    AudioHandle buildReloadSFX(const AlchemicalLauncherParams& p) {
        Log::info("Building reload SFX for: {}", p.id);
        
        auto audio = AudioBuilder::createProcedural();
        
        // Configure clink sound
        audio.setType(AudioType::CLINK);
        audio.setVolume(p.soundVolume * 0.8f);
        audio.setPitch(p.soundPitch * 0.9f);
        audio.setDuration(p.soundDuration * 0.5f);
        
        // Configure spatial audio
        if (p.enableSpatialAudio) {
            audio.enableSpatial(p.audioDistance);
        }
        
        // Modulate by reload time
        audio.modulateByParameter("reloadTime", p.reloadTime);
        
        return audio.getHandle();
    }
    
    AudioHandle buildShellEjectSFX(const AlchemicalLauncherParams& p) {
        Log::info("Building shell eject SFX for: {}", p.id);
        
        auto audio = AudioBuilder::createProcedural();
        
        // Configure shell ejection sound
        audio.setType(AudioType::SHELL_EJECT);
        audio.setVolume(p.soundVolume * 0.6f);
        audio.setPitch(p.soundPitch * 1.1f);
        audio.setDuration(0.2f);
        
        // Configure spatial audio
        if (p.enableSpatialAudio) {
            audio.enableSpatial(p.audioDistance);
        }
        
        // Modulate by shell ejection speed
        audio.modulateByParameter("shellEjectionSpeed", p.shellEjectionSpeed);
        
        return audio.getHandle();
    }
    
    AudioHandle buildHeatDistortionSFX(const AlchemicalLauncherParams& p) {
        Log::info("Building heat distortion SFX for: {}", p.id);
        
        auto audio = AudioBuilder::createProcedural();
        
        // Configure heat distortion sound
        audio.setType(AudioType::HEAT_DISTORTION);
        audio.setVolume(p.soundVolume * 0.3f);
        audio.setPitch(p.soundPitch * 0.8f);
        audio.setDuration(1.0f);
        
        // Configure spatial audio
        if (p.enableSpatialAudio) {
            audio.enableSpatial(p.audioDistance);
        }
        
        // Modulate by heat distortion strength
        audio.modulateByParameter("heatDistortionStrength", p.heatDistortionStrength);
        
        return audio.getHandle();
    }
}

namespace IconGen {
    TextureHandle buildLauncherIcon(const AlchemicalLauncherParams& p, const UIParams& u) {
        Log::info("Building launcher icon for: {}", p.id);
        
        auto canvas = IconBuilder::createCanvas(u.iconSize, u.iconSize);
        
        // Draw background shape
        switch (u.backgroundShape) {
            case BackgroundShape::RECTANGLE:
                canvas.drawRectangle(u.borderColor, u.cornerRadius);
                break;
            case BackgroundShape::CIRCLE:
                canvas.drawCircle(u.borderColor);
                break;
            case BackgroundShape::HEXAGON:
                canvas.drawHexagon(u.borderColor);
                break;
            case BackgroundShape::DIAMOND:
                canvas.drawDiamond(u.borderColor);
                break;
            default:
                break;
        }
        
        // Draw launcher silhouette
        auto silhouette = IconBuilder::createLauncherSilhouette(p);
        canvas.drawShape(silhouette, p.colorPrimary, u.borderThickness);
        
        // Add glow effect
        if (u.enableGlow) {
            canvas.addGlow(u.glowColor, u.glowIntensity);
        }
        
        // Add pulse effect
        if (u.enablePulse) {
            canvas.addPulse(u.pulseFrequency, u.pulseAmplitude);
        }
        
        // Add label if specified
        if (u.enableLabel && !u.label.empty()) {
            canvas.drawText(u.label, u.labelColor, u.labelSize, u.labelFont);
        }
        
        // Add flash effect for selection
        if (u.flashOnSelect) {
            canvas.addSelectionFlash();
        }
        
        return canvas.toTexture();
    }
}

} // namespace AlchemicalLaunchers
} // namespace MagiTech
