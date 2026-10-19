#include "ParticleAssetLuaBindings.hpp"
#include "ParticleAssetFactory.hpp"
#include "ParticleAssetTypes.hpp"
#include "core/Log.hpp"
#include <sol/sol.hpp>
#include <chrono>
#include <memory>
#include <future>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace Particles {

static std::vector<std::pair<std::future<ParticleEffectResult>, std::string>> pendingEffects;
static std::mutex pendingEffectsMutex;

static std::mutex factoryMutex;
static std::shared_ptr<ParticleAssetFactory> sharedFactory;

void ParticleAssetLuaBindings::setFactory(std::shared_ptr<ParticleAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<ParticleAssetFactory> ParticleAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<ParticleAssetFactory>();
        sharedFactory->initialize(256, 4);
    }
    return sharedFactory;
}

static std::shared_ptr<ParticleAssetFactory> factory() {
    return ParticleAssetLuaBindings::factory();
}

void ParticleAssetLuaBindings::bind(sol::state& lua) {
    bindParticleAssetToLua(lua);
}

void ParticleAssetLuaBindings::poll_assets(sol::state& lua) {
    // Take finished futures out under the lock; run Lua callbacks without it.
    std::vector<std::pair<std::future<ParticleEffectResult>, std::string>> ready;
    {
        std::lock_guard<std::mutex> lock(pendingEffectsMutex);
        for (auto it = pendingEffects.begin(); it != pendingEffects.end();) {
            if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                ready.push_back(std::move(*it));
                it = pendingEffects.erase(it);
            } else {
                ++it;
            }
        }
    }

    for (auto& [future, effectName] : ready) {
        try {
            ParticleEffectResult result = future.get();
            if (!result.success) {
                Log::error("ParticleAsset", "Particle effect {} failed: {}", effectName, result.errorMessage);
            }
            sol::protected_function callback = lua["on_particle_effect_ready"];
            if (callback.valid()) {
                auto call = callback(effectName, result);
                if (!call.valid()) {
                    sol::error err = call;
                    Log::error("ParticleAsset", "on_particle_effect_ready failed for {}: {}", effectName, err.what());
                }
            } else {
                lua["print"]("Particle effect ready: " + effectName);
            }
        } catch (const std::exception& e) {
            Log::error("ParticleAsset", "Particle effect generation failed for {}: {}", effectName, e.what());
        }
    }
}

// std::map members are exposed as plain Lua tables (copied on read, replaced on
// write). Pushing the maps as sol container userdata is avoided on purpose: the
// vendored sol2 associative-container iterator does not compile with MSVC
// (usertype_container.hpp calls iter::end() instead of iter::sen()).
template <typename Owner, typename V>
static auto mapProperty(std::map<std::string, V> Owner::*member) {
    return sol::property(
        [member](const Owner& owner) { return sol::as_table(owner.*member); },
        [member](Owner& owner, sol::table table) {
            std::map<std::string, V> values;
            for (const auto& [key, value] : table) {
                if (key.template is<std::string>() && value.template is<V>()) {
                    values[key.template as<std::string>()] = value.template as<V>();
                }
            }
            owner.*member = std::move(values);
        });
}

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
        "customParameters", mapProperty(&EmitterParams::customParameters)
    );

    lua.new_usertype<BehaviorParams>("ParticleBehaviorParams",
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
        "customParameters", mapProperty(&BehaviorParams::customParameters)
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
        "customParameters", mapProperty(&ShapeParams::customParameters)
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
        "customParameters", mapProperty(&LifetimeParams::customParameters)
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
        "customParameters", mapProperty(&RenderParams::customParameters)
    );

    lua.new_usertype<LODParams>("ParticleLODParams",
        sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes,
        "rateScales", &LODParams::rateScales,
        "qualityScales", &LODParams::qualityScales,
        "adaptiveLOD", &LODParams::adaptiveLOD,
        "adaptiveThreshold", &LODParams::adaptiveThreshold,
        "customParameters", mapProperty(&LODParams::customParameters)
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
        "metadata", mapProperty(&ParticleEffectDefinition::metadata),
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
        "metadata", mapProperty(&ParticleEffectResult::metadata)
    );

    lua.new_usertype<ParticleBundle>("ParticleBundle",
        sol::constructors<ParticleBundle()>(),
        "system", &ParticleBundle::system,
        "lodData", &ParticleBundle::lodData,
        "texture", &ParticleBundle::texture,
        "shader", &ParticleBundle::shader,
        "computeShader", &ParticleBundle::computeShader,
        "metadata", mapProperty(&ParticleBundle::metadata),
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
        "id", &ParticleForceField::id,
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
        "id", &ParticleCollision::id,
        "position", &ParticleCollision::position,
        "dimensions", &ParticleCollision::dimensions,
        "normal", &ParticleCollision::normal,
        "restitution", &ParticleCollision::restitution,
        "friction", &ParticleCollision::friction,
        "active", &ParticleCollision::active,
        "meshPath", &ParticleCollision::meshPath
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
        "customParameters", mapProperty(&AdvancedParticleParams::customParameters)
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
        "metadata", mapProperty(&ParticleEffectTemplate::metadata)
    );

    lua.new_usertype<ParticleEffectInstance>("ParticleEffectInstance",
        sol::constructors<ParticleEffectInstance()>(),
        "id", &ParticleEffectInstance::id,
        "templateName", &ParticleEffectInstance::templateName,
        "definition", &ParticleEffectInstance::definition,
        "position", &ParticleEffectInstance::position,
        "rotation", &ParticleEffectInstance::rotation,
        "scale", &ParticleEffectInstance::scale,
        "active", &ParticleEffectInstance::active,
        "startTime", &ParticleEffectInstance::startTime,
        "duration", &ParticleEffectInstance::duration,
        "loopCount", &ParticleEffectInstance::loopCount,
        "parameters", mapProperty(&ParticleEffectInstance::parameters),
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
        [](const ParticleEffectDefinition& definition) {
            return factory()->generateAsync(definition).get();
        });

    lua.set_function("create_particle_effect_sync", 
        [](const ParticleEffectDefinition& definition) {
            return factory()->generate(definition);
        });

    // Queues generation; the result is delivered by poll_assets (on_particle_effect_ready)
    lua.set_function("create_particle_effect_async",
        [](const ParticleEffectDefinition& definition) {
            auto future = factory()->generateAsync(definition);
            std::lock_guard<std::mutex> lock(pendingEffectsMutex);
            pendingEffects.emplace_back(std::move(future), definition.name);
        });

    lua.set_function("create_particle_instance",
        [](const std::string& templateName, 
            const glm::vec3& position,
            const glm::vec3& rotation,
            const glm::vec3& scale) {
            return factory()->createInstance(templateName, position, rotation, scale);
        });

    lua.set_function("destroy_particle_instance", 
        [](const std::string& instanceId) {
            factory()->destroyInstance(instanceId);
        });

    lua.set_function("update_particle_instance", 
        [](const std::string& instanceId, float deltaTime) {
            factory()->updateInstance(instanceId, deltaTime);
        });

    // Bind factory management functions
    lua.set_function("register_particle_template", 
        [](const ParticleEffectTemplate& effectTemplate) {
            factory()->registerTemplate(effectTemplate);
        });

    lua.set_function("unregister_particle_template", 
        [](const std::string& templateName) {
            factory()->unregisterTemplate(templateName);
        });

    lua.set_function("get_particle_template", 
        [](const std::string& templateName) {
            return factory()->getTemplate(templateName);
        });

    // Bind force field management
    lua.set_function("add_global_force_field", 
        [](const ParticleForceField& forceField) {
            factory()->addGlobalForceField(forceField);
        });

    lua.set_function("remove_global_force_field", 
        [](const std::string& forceFieldId) {
            factory()->removeGlobalForceField(forceFieldId);
        });

    lua.set_function("update_global_force_fields", 
        [](float deltaTime) {
            factory()->updateGlobalForceFields(deltaTime);
        });

    // Bind collision management
    lua.set_function("add_global_collision", 
        [](const ParticleCollision& collision) {
            factory()->addGlobalCollision(collision);
        });

    lua.set_function("remove_global_collision", 
        [](const std::string& collisionId) {
            factory()->removeGlobalCollision(collisionId);
        });

    lua.set_function("update_global_collisions", 
        [](float deltaTime) {
            factory()->updateGlobalCollisions(deltaTime);
        });

    // Bind cache management
    lua.set_function("clear_particle_cache", 
        []() {
            factory()->clearCache();
        });

    lua.set_function("set_particle_cache_size", 
        [](size_t maxEntries) {
            factory()->setCacheSize(maxEntries);
        });

    lua.set_function("get_particle_cache_size", 
        []() {
            return factory()->getCacheSize();
        });

    lua.set_function("get_particle_cache_hits", 
        []() {
            return factory()->getCacheHits();
        });

    lua.set_function("get_particle_cache_misses", 
        []() {
            return factory()->getCacheMisses();
        });

    // Bind thread pool management
    lua.set_function("set_particle_max_threads", 
        [](int threads) {
            factory()->setMaxThreads(threads);
        });

    lua.set_function("get_particle_max_threads", 
        []() {
            return factory()->getMaxThreads();
        });

    // Bind GPU acceleration
    lua.set_function("enable_particle_gpu_acceleration", 
        [](bool enable) {
            factory()->enableGPUAcceleration(enable);
        });

    lua.set_function("is_particle_gpu_acceleration_enabled", 
        []() {
            return factory()->isGPUAccelerationEnabled();
        });

    // Bind quality settings
    lua.set_function("set_particle_quality", 
        [](ParticleQuality quality) {
            factory()->setParticleQuality(quality);
        });

    lua.set_function("get_particle_quality", 
        []() {
            return factory()->getParticleQuality();
        });

    // Bind performance monitoring
    lua.set_function("get_particle_performance_metrics", 
        []() {
            return factory()->getPerformanceMetrics();
        });

    lua.set_function("reset_particle_performance_metrics", 
        []() {
            factory()->resetPerformanceMetrics();
        });

    // Bind error handling
    lua.set_function("get_particle_last_error", 
        []() {
            return factory()->getLastError();
        });

    lua.set_function("clear_particle_last_error", 
        []() {
            factory()->clearLastError();
        });

    // Bind generation status
    lua.set_function("is_particle_generating", 
        []() {
            return factory()->isGenerating();
        });

    lua.set_function("get_particle_generation_progress", 
        []() {
            return factory()->getGenerationProgress();
        });

    // Bind memory management
    lua.set_function("get_particle_total_memory_usage", 
        []() {
            return factory()->getTotalMemoryUsage();
        });

    lua.set_function("set_particle_max_memory_usage", 
        [](size_t maxBytes) {
            factory()->setMaxMemoryUsage(maxBytes);
        });

    lua.set_function("get_particle_max_memory_usage", 
        []() {
            return factory()->getMaxMemoryUsage();
        });

    // Bind utility functions
    lua.set_function("validate_particle_definition", 
        [](const ParticleEffectDefinition& definition) {
            return factory()->validateDefinition(definition);
        });

    // Bind helper functions for creating common effects
    lua.set_function("create_explosion_effect", 
        [](const glm::vec3& position, float intensity) {
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
            
            return factory()->generate(def);
        });

    lua.set_function("create_fire_effect", 
        [](const glm::vec3& position, float intensity) {
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
            
            return factory()->generate(def);
        });

    lua.set_function("create_magic_sparkle_effect", 
        [](const glm::vec3& position, float intensity) {
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
            
            return factory()->generate(def);
        });
}

} // namespace Particles
} // namespace MagiTech
