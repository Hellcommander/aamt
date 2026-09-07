#include "ParticleAssetLuaBindings.hpp"
#include "ParticleAssetFactory.hpp"
#include "ParticleAssetTypes.hpp"
#include <sol/sol.hpp>
#include <memory>
#include <future>

namespace MagiTech {
namespace Particles {

void bindParticleAssetToLua(sol::state& lua) {
    // Bind parameter structures
    lua.new_usertype<EmitterParams>("EmitterParams",
        sol::constructors<EmitterParams()>(),
        "id", &EmitterParams::id,
        "position", &EmitterParams::position,
        "rotation", &EmitterParams::rotation,
        "scale", &EmitterParams::scale,
        "rate", &EmitterParams::rate,
        "duration", &EmitterParams::duration,
        "loop", &EmitterParams::loop,
        "burstMode", &EmitterParams::burstMode,
        "burstCount", &EmitterParams::burstCount,
        "burstInterval", &EmitterParams::burstInterval,
        "gpuDriven", &EmitterParams::gpuDriven,
        "customParameters", &EmitterParams::customParameters
    );

    lua.new_usertype<BehaviorParams>("BehaviorParams",
        sol::constructors<BehaviorParams()>(),
        "initialVelocity", &BehaviorParams::initialVelocity,
        "velocityVariance", &BehaviorParams::velocityVariance,
        "acceleration", &BehaviorParams::acceleration,
        "gravity", &BehaviorParams::gravity,
        "drag", &BehaviorParams::drag,
        "collision", &BehaviorParams::collision,
        "turbulence", &BehaviorParams::turbulence,
        "turbulenceStrength", &BehaviorParams::turbulenceStrength,
        "wind", &BehaviorParams::wind,
        "attractorMode", &BehaviorParams::attractorMode,
        "attractorPosition", &BehaviorParams::attractorPosition,
        "attractorStrength", &BehaviorParams::attractorStrength,
        "attractorRadius", &BehaviorParams::attractorRadius,
        "customParameters", &BehaviorParams::customParameters
    );

    lua.new_usertype<ShapeParams>("ShapeParams",
        sol::constructors<ShapeParams()>(),
        "type", &ShapeParams::type,
        "dimensions", &ShapeParams::dimensions,
        "angle", &ShapeParams::angle,
        "radius", &ShapeParams::radius,
        "innerRadius", &ShapeParams::innerRadius,
        "meshPath", &ShapeParams::meshPath,
        "randomRotation", &ShapeParams::randomRotation,
        "alignToVelocity", &ShapeParams::alignToVelocity,
        "customParameters", &ShapeParams::customParameters
    );

    lua.new_usertype<LifetimeParams>("LifetimeParams",
        sol::constructors<LifetimeParams()>(),
        "minLife", &LifetimeParams::minLife,
        "maxLife", &LifetimeParams::maxLife,
        "sizeRange", &LifetimeParams::sizeRange,
        "sizeOverLife", &LifetimeParams::sizeOverLife,
        "fadeIn", &LifetimeParams::fadeIn,
        "fadeOut", &LifetimeParams::fadeOut,
        "fadeInTime", &LifetimeParams::fadeInTime,
        "fadeOutTime", &LifetimeParams::fadeOutTime,
        "colorOverLife", &LifetimeParams::colorOverLife,
        "startColor", &LifetimeParams::startColor,
        "endColor", &LifetimeParams::endColor,
        "velocityOverLife", &LifetimeParams::velocityOverLife,
        "velocityStart", &LifetimeParams::velocityStart,
        "velocityEnd", &LifetimeParams::velocityEnd,
        "customParameters", &LifetimeParams::customParameters
    );

    lua.new_usertype<RenderParams>("RenderParams",
        sol::constructors<RenderParams()>(),
        "texturePath", &RenderParams::texturePath,
        "animated", &RenderParams::animated,
        "frameCount", &RenderParams::frameCount,
        "frameRate", &RenderParams::frameRate,
        "frameSize", &RenderParams::frameSize,
        "billboard", &RenderParams::billboard,
        "alignToCamera", &RenderParams::alignToCamera,
        "softParticles", &RenderParams::softParticles,
        "additive", &RenderParams::additive,
        "multiply", &RenderParams::multiply,
        "distortion", &RenderParams::distortion,
        "distortionStrength", &RenderParams::distortionStrength,
        "glow", &RenderParams::glow,
        "glowIntensity", &RenderParams::glowIntensity,
        "normalMapPath", &RenderParams::normalMapPath,
        "emissionMapPath", &RenderParams::emissionMapPath,
        "customParameters", &RenderParams::customParameters
    );

    lua.new_usertype<LODParams>("LODParams",
        sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes,
        "rateScales", &LODParams::rateScales,
        "qualityScales", &LODParams::qualityScales,
        "adaptiveLOD", &LODParams::adaptiveLOD,
        "adaptiveThreshold", &LODParams::adaptiveThreshold,
        "customParameters", &LODParams::customParameters
    );

    lua.new_usertype<ParticleEffectDefinition>("ParticleEffectDefinition",
        sol::constructors<ParticleEffectDefinition()>(),
        "name", &ParticleEffectDefinition::name,
        "description", &ParticleEffectDefinition::description,
        "category", &ParticleEffectDefinition::category,
        "emitter", &ParticleEffectDefinition::emitter,
        "behavior", &ParticleEffectDefinition::behavior,
        "shape", &ParticleEffectDefinition::shape,
        "lifetime", &ParticleEffectDefinition::lifetime,
        "render", &ParticleEffectDefinition::render,
        "lod", &ParticleEffectDefinition::lod,
        "tags", &ParticleEffectDefinition::tags,
        "metadata", &ParticleEffectDefinition::metadata,
        "enableHotReload", &ParticleEffectDefinition::enableHotReload,
        "enableCaching", &ParticleEffectDefinition::enableCaching
    );

    lua.new_usertype<ParticleEffectResult>("ParticleEffectResult",
        sol::constructors<ParticleEffectResult()>(),
        "bundle", &ParticleEffectResult::bundle,
        "definition", &ParticleEffectResult::definition,
        "processingTime", &ParticleEffectResult::processingTime,
        "success", &ParticleEffectResult::success,
        "errorMessage", &ParticleEffectResult::errorMessage,
        "warnings", &ParticleEffectResult::warnings,
        "metadata", &ParticleEffectResult::metadata
    );

    lua.new_usertype<ParticleBundle>("ParticleBundle",
        sol::constructors<ParticleBundle()>(),
        "system", &ParticleBundle::system,
        "lodData", &ParticleBundle::lodData,
        "texture", &ParticleBundle::texture,
        "shader", &ParticleBundle::shader,
        "computeShader", &ParticleBundle::computeShader,
        "metadata", &ParticleBundle::metadata,
        "creationTime", &ParticleBundle::creationTime,
        "memoryUsage", &ParticleBundle::memoryUsage,
        "gpuAccelerated", &ParticleBundle::gpuAccelerated
    );

    lua.new_usertype<Particle>("Particle",
        sol::constructors<Particle()>(),
        "position", &Particle::position,
        "velocity", &Particle::velocity,
        "acceleration", &Particle::acceleration,
        "color", &Particle::color,
        "size", &Particle::size,
        "age", &Particle::age,
        "lifetime", &Particle::lifetime,
        "rotation", &Particle::rotation,
        "rotationSpeed", &Particle::rotationSpeed,
        "uvOffset", &Particle::uvOffset,
        "active", &Particle::active
    );

    lua.new_usertype<ParticleForceField>("ParticleForceField",
        sol::constructors<ParticleForceField()>(),
        "type", &ParticleForceField::type,
        "position", &ParticleForceField::position,
        "direction", &ParticleForceField::direction,
        "strength", &ParticleForceField::strength,
        "radius", &ParticleForceField::radius,
        "falloff", &ParticleForceField::falloff,
        "active", &ParticleForceField::active
    );

    lua.new_usertype<ParticleCollision>("ParticleCollision",
        sol::constructors<ParticleCollision()>(),
        "type", &ParticleCollision::type,
        "position", &ParticleCollision::position,
        "dimensions", &ParticleCollision::dimensions,
        "normal", &ParticleCollision::normal,
        "restitution", &ParticleCollision::restitution,
        "friction", &ParticleCollision::friction,
        "active", &ParticleCollision::active
    );

    lua.new_usertype<ParticleTrail>("ParticleTrail",
        sol::constructors<ParticleTrail()>(),
        "enabled", &ParticleTrail::enabled,
        "maxPoints", &ParticleTrail::maxPoints,
        "fadeTime", &ParticleTrail::fadeTime,
        "width", &ParticleTrail::width,
        "color", &ParticleTrail::color,
        "useTexture", &ParticleTrail::useTexture,
        "texturePath", &ParticleTrail::texturePath
    );

    lua.new_usertype<ParticleSubEmitter>("ParticleSubEmitter",
        sol::constructors<ParticleSubEmitter()>(),
        "effectName", &ParticleSubEmitter::effectName,
        "probability", &ParticleSubEmitter::probability,
        "offset", &ParticleSubEmitter::offset,
        "inheritVelocity", &ParticleSubEmitter::inheritVelocity,
        "inheritRotation", &ParticleSubEmitter::inheritRotation,
        "inheritColor", &ParticleSubEmitter::inheritColor,
        "inheritSize", &ParticleSubEmitter::inheritSize
    );

    lua.new_usertype<AdvancedParticleParams>("AdvancedParticleParams",
        sol::constructors<AdvancedParticleParams()>(),
        "useGPU", &AdvancedParticleParams::useGPU,
        "useInstancing", &AdvancedParticleParams::useInstancing,
        "useGeometryShaders", &AdvancedParticleParams::useGeometryShaders,
        "maxParticles", &AdvancedParticleParams::maxParticles,
        "batchSize", &AdvancedParticleParams::batchSize,
        "enableSorting", &AdvancedParticleParams::enableSorting,
        "enableCulling", &AdvancedParticleParams::enableCulling,
        "cullDistance", &AdvancedParticleParams::cullDistance,
        "enableOcclusion", &AdvancedParticleParams::enableOcclusion,
        "enableDepthPrePass", &AdvancedParticleParams::enableDepthPrePass,
        "customParameters", &AdvancedParticleParams::customParameters
    );

    lua.new_usertype<ParticleEffectTemplate>("ParticleEffectTemplate",
        sol::constructors<ParticleEffectTemplate()>(),
        "name", &ParticleEffectTemplate::name,
        "description", &ParticleEffectTemplate::description,
        "tags", &ParticleEffectTemplate::tags,
        "baseDefinition", &ParticleEffectTemplate::baseDefinition,
        "subEmitters", &ParticleEffectTemplate::subEmitters,
        "forceFields", &ParticleEffectTemplate::forceFields,
        "collisions", &ParticleEffectTemplate::collisions,
        "trail", &ParticleEffectTemplate::trail,
        "advanced", &ParticleEffectTemplate::advanced,
        "metadata", &ParticleEffectTemplate::metadata
    );

    lua.new_usertype<ParticleEffectInstance>("ParticleEffectInstance",
        sol::constructors<ParticleEffectInstance()>(),
        "templateName", &ParticleEffectInstance::templateName,
        "definition", &ParticleEffectInstance::definition,
        "position", &ParticleEffectInstance::position,
        "rotation", &ParticleEffectInstance::rotation,
        "scale", &ParticleEffectInstance::scale,
        "active", &ParticleEffectInstance::active,
        "startTime", &ParticleEffectInstance::startTime,
        "duration", &ParticleEffectInstance::duration,
        "loopCount", &ParticleEffectInstance::loopCount,
        "parameters", &ParticleEffectInstance::parameters,
        "state", &ParticleEffectInstance::state
    );

    lua.new_usertype<ParticleSystemState>("ParticleSystemState",
        sol::constructors<ParticleSystemState()>(),
        "activeParticles", &ParticleSystemState::activeParticles,
        "totalParticles", &ParticleSystemState::totalParticles,
        "updateTime", &ParticleSystemState::updateTime,
        "renderTime", &ParticleSystemState::renderTime,
        "memoryUsage", &ParticleSystemState::memoryUsage,
        "isActive", &ParticleSystemState::isActive,
        "isPaused", &ParticleSystemState::isPaused,
        "currentTime", &ParticleSystemState::currentTime,
        "currentLOD", &ParticleSystemState::currentLOD
    );

    lua.new_usertype<ParticlePerformanceMetrics>("ParticlePerformanceMetrics",
        sol::constructors<ParticlePerformanceMetrics()>(),
        "frameTime", &ParticlePerformanceMetrics::frameTime,
        "updateTime", &ParticlePerformanceMetrics::updateTime,
        "renderTime", &ParticlePerformanceMetrics::renderTime,
        "drawCalls", &ParticlePerformanceMetrics::drawCalls,
        "activeParticles", &ParticlePerformanceMetrics::activeParticles,
        "totalParticles", &ParticlePerformanceMetrics::totalParticles,
        "memoryUsage", &ParticlePerformanceMetrics::memoryUsage,
        "gpuTime", &ParticlePerformanceMetrics::gpuTime,
        "cpuTime", &ParticlePerformanceMetrics::cpuTime,
        "lodLevel", &ParticlePerformanceMetrics::lodLevel,
        "gpuAccelerated", &ParticlePerformanceMetrics::gpuAccelerated
    );

    // Bind enums
    lua.new_enum("ShapeType",
        "Point", ShapeParams::Point,
        "Sphere", ShapeParams::Sphere,
        "Box", ShapeParams::Box,
        "Cone", ShapeParams::Cone,
        "Circle", ShapeParams::Circle,
        "Cylinder", ShapeParams::Cylinder,
        "Torus", ShapeParams::Torus,
        "CustomMesh", ShapeParams::CustomMesh
    );

    lua.new_enum("FieldType",
        "Gravity", ParticleForceField::Gravity,
        "Wind", ParticleForceField::Wind,
        "Turbulence", ParticleForceField::Turbulence,
        "Attractor", ParticleForceField::Attractor,
        "Repulsor", ParticleForceField::Repulsor,
        "Vortex", ParticleForceField::Vortex,
        "Custom", ParticleForceField::Custom
    );

    lua.new_enum("CollisionType",
        "None", ParticleCollision::None,
        "Sphere", ParticleCollision::Sphere,
        "Box", ParticleCollision::Box,
        "Plane", ParticleCollision::Plane,
        "Mesh", ParticleCollision::Mesh
    );

    lua.new_enum("ParticleQuality",
        "Low", ParticleQuality::Low,
        "Medium", ParticleQuality::Medium,
        "High", ParticleQuality::High,
        "Ultra", ParticleQuality::Ultra
    );

    // Bind factory functions
    lua.set_function("create_particle_effect", 
        [&](const ParticleEffectDefinition& definition) {
            return particleFactory.generateAsync(definition).get();
        });

    lua.set_function("create_particle_effect_sync", 
        [&](const ParticleEffectDefinition& definition) {
            return particleFactory.generate(definition);
        });

    lua.set_function("create_particle_instance", 
        [&](const std::string& templateName, 
            const glm::vec3& position,
            const glm::vec3& rotation,
            const glm::vec3& scale) {
            return particleFactory.createInstance(templateName, position, rotation, scale);
        });

    lua.set_function("destroy_particle_instance", 
        [&](const std::string& instanceId) {
            particleFactory.destroyInstance(instanceId);
        });

    lua.set_function("update_particle_instance", 
        [&](const std::string& instanceId, float deltaTime) {
            particleFactory.updateInstance(instanceId, deltaTime);
        });

    // Bind factory management functions
    lua.set_function("register_particle_template", 
        [&](const ParticleEffectTemplate& template) {
            particleFactory.registerTemplate(template);
        });

    lua.set_function("unregister_particle_template", 
        [&](const std::string& templateName) {
            particleFactory.unregisterTemplate(templateName);
        });

    lua.set_function("get_particle_template", 
        [&](const std::string& templateName) {
            return particleFactory.getTemplate(templateName);
        });

    // Bind force field management
    lua.set_function("add_global_force_field", 
        [&](const ParticleForceField& forceField) {
            particleFactory.addGlobalForceField(forceField);
        });

    lua.set_function("remove_global_force_field", 
        [&](const std::string& forceFieldId) {
            particleFactory.removeGlobalForceField(forceFieldId);
        });

    lua.set_function("update_global_force_fields", 
        [&](float deltaTime) {
            particleFactory.updateGlobalForceFields(deltaTime);
        });

    // Bind collision management
    lua.set_function("add_global_collision", 
        [&](const ParticleCollision& collision) {
            particleFactory.addGlobalCollision(collision);
        });

    lua.set_function("remove_global_collision", 
        [&](const std::string& collisionId) {
            particleFactory.removeGlobalCollision(collisionId);
        });

    lua.set_function("update_global_collisions", 
        [&](float deltaTime) {
            particleFactory.updateGlobalCollisions(deltaTime);
        });

    // Bind cache management
    lua.set_function("clear_particle_cache", 
        [&]() {
            particleFactory.clearCache();
        });

    lua.set_function("set_particle_cache_size", 
        [&](size_t maxEntries) {
            particleFactory.setCacheSize(maxEntries);
        });

    lua.set_function("get_particle_cache_size", 
        [&]() {
            return particleFactory.getCacheSize();
        });

    lua.set_function("get_particle_cache_hits", 
        [&]() {
            return particleFactory.getCacheHits();
        });

    lua.set_function("get_particle_cache_misses", 
        [&]() {
            return particleFactory.getCacheMisses();
        });

    // Bind thread pool management
    lua.set_function("set_particle_max_threads", 
        [&](int threads) {
            particleFactory.setMaxThreads(threads);
        });

    lua.set_function("get_particle_max_threads", 
        [&]() {
            return particleFactory.getMaxThreads();
        });

    // Bind GPU acceleration
    lua.set_function("enable_particle_gpu_acceleration", 
        [&](bool enable) {
            particleFactory.enableGPUAcceleration(enable);
        });

    lua.set_function("is_particle_gpu_acceleration_enabled", 
        [&]() {
            return particleFactory.isGPUAccelerationEnabled();
        });

    // Bind quality settings
    lua.set_function("set_particle_quality", 
        [&](ParticleQuality quality) {
            particleFactory.setParticleQuality(quality);
        });

    lua.set_function("get_particle_quality", 
        [&]() {
            return particleFactory.getParticleQuality();
        });

    // Bind performance monitoring
    lua.set_function("get_particle_performance_metrics", 
        [&]() {
            return particleFactory.getPerformanceMetrics();
        });

    lua.set_function("reset_particle_performance_metrics", 
        [&]() {
            particleFactory.resetPerformanceMetrics();
        });

    // Bind error handling
    lua.set_function("get_particle_last_error", 
        [&]() {
            return particleFactory.getLastError();
        });

    lua.set_function("clear_particle_last_error", 
        [&]() {
            particleFactory.clearLastError();
        });

    // Bind generation status
    lua.set_function("is_particle_generating", 
        [&]() {
            return particleFactory.isGenerating();
        });

    lua.set_function("get_particle_generation_progress", 
        [&]() {
            return particleFactory.getGenerationProgress();
        });

    // Bind memory management
    lua.set_function("get_particle_total_memory_usage", 
        [&]() {
            return particleFactory.getTotalMemoryUsage();
        });

    lua.set_function("set_particle_max_memory_usage", 
        [&](size_t maxBytes) {
            particleFactory.setMaxMemoryUsage(maxBytes);
        });

    lua.set_function("get_particle_max_memory_usage", 
        [&]() {
            return particleFactory.getMaxMemoryUsage();
        });

    // Bind utility functions
    lua.set_function("validate_particle_definition", 
        [&](const ParticleEffectDefinition& definition) {
            return particleFactory.validateDefinition(definition);
        });

    // Bind helper functions for creating common effects
    lua.set_function("create_explosion_effect", 
        [&](const glm::vec3& position, float intensity) {
            ParticleEffectDefinition def;
            def.name = "explosion";
            def.category = "combat";
            
            def.emitter.position = position;
            def.emitter.rate = 100.0f * intensity;
            def.emitter.duration = 2.0f;
            def.emitter.burstMode = true;
            def.emitter.burstCount = static_cast<int>(50 * intensity);
            def.emitter.gpuDriven = true;
            
            def.behavior.initialVelocity = {0, 5 * intensity, 0};
            def.behavior.velocityVariance = {2 * intensity, 1 * intensity, 2 * intensity};
            def.behavior.gravity = -9.81f;
            def.behavior.turbulence = true;
            def.behavior.turbulenceStrength = 0.5f * intensity;
            
            def.shape.type = ShapeParams::Sphere;
            def.shape.radius = 1.0f * intensity;
            def.shape.randomRotation = true;
            
            def.lifetime.minLife = 1.0f;
            def.lifetime.maxLife = 3.0f;
            def.lifetime.sizeRange = {0.1f * intensity, 0.5f * intensity};
            def.lifetime.fadeOut = true;
            def.lifetime.colorOverLife = true;
            
            def.render.texturePath = "textures/particles/explosion.png";
            def.render.billboard = true;
            def.render.additive = true;
            def.render.glow = true;
            def.render.glowIntensity = 0.8f * intensity;
            
            return particleFactory.generate(def);
        });

    lua.set_function("create_fire_effect", 
        [&](const glm::vec3& position, float intensity) {
            ParticleEffectDefinition def;
            def.name = "fire";
            def.category = "environment";
            
            def.emitter.position = position;
            def.emitter.rate = 50.0f * intensity;
            def.emitter.duration = -1.0f; // Infinite
            def.emitter.loop = true;
            def.emitter.gpuDriven = true;
            
            def.behavior.initialVelocity = {0, 2 * intensity, 0};
            def.behavior.velocityVariance = {0.5f * intensity, 0.2f * intensity, 0.5f * intensity};
            def.behavior.gravity = -2.0f;
            def.behavior.turbulence = true;
            def.behavior.turbulenceStrength = 0.3f * intensity;
            
            def.shape.type = ShapeParams::Cone;
            def.shape.radius = 0.5f * intensity;
            def.shape.angle = 30.0f;
            
            def.lifetime.minLife = 2.0f;
            def.lifetime.maxLife = 4.0f;
            def.lifetime.sizeRange = {0.2f * intensity, 0.8f * intensity};
            def.lifetime.fadeOut = true;
            def.lifetime.colorOverLife = true;
            def.lifetime.startColor = {1.0f, 0.5f, 0.0f, 1.0f};
            def.lifetime.endColor = {1.0f, 0.2f, 0.0f, 0.0f};
            
            def.render.texturePath = "textures/particles/fire.png";
            def.render.billboard = true;
            def.render.additive = true;
            def.render.glow = true;
            def.render.glowIntensity = 0.6f * intensity;
            
            return particleFactory.generate(def);
        });

    lua.set_function("create_magic_sparkle_effect", 
        [&](const glm::vec3& position, float intensity) {
            ParticleEffectDefinition def;
            def.name = "magic_sparkle";
            def.category = "magic";
            
            def.emitter.position = position;
            def.emitter.rate = 20.0f * intensity;
            def.emitter.duration = 5.0f;
            def.emitter.gpuDriven = true;
            
            def.behavior.initialVelocity = {0, 1 * intensity, 0};
            def.behavior.velocityVariance = {1 * intensity, 0.5f * intensity, 1 * intensity};
            def.behavior.gravity = -1.0f;
            
            def.shape.type = ShapeParams::Sphere;
            def.shape.radius = 0.3f * intensity;
            def.shape.randomRotation = true;
            
            def.lifetime.minLife = 3.0f;
            def.lifetime.maxLife = 6.0f;
            def.lifetime.sizeRange = {0.1f * intensity, 0.3f * intensity};
            def.lifetime.fadeOut = true;
            def.lifetime.colorOverLife = true;
            def.lifetime.startColor = {0.5f, 0.8f, 1.0f, 1.0f};
            def.lifetime.endColor = {1.0f, 1.0f, 1.0f, 0.0f};
            
            def.render.texturePath = "textures/particles/sparkle.png";
            def.render.billboard = true;
            def.render.additive = true;
            def.render.glow = true;
            def.render.glowIntensity = 0.9f * intensity;
            
            return particleFactory.generate(def);
        });
}

} // namespace Particles
} // namespace MagiTech
