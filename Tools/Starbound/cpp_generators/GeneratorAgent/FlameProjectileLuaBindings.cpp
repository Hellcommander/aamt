#include "FlameProjectileLuaBindings.hpp"
#include "FlameProjectileFactory.hpp"
#include "FlameProjectileTypes.hpp"
#include <chrono>
#include <fstream>
#include <memory>
#include <mutex>
#include <sstream>
#include <vector>

namespace MagiTech {
namespace FlameProjectiles {

static std::vector<std::pair<std::future<FlameAssetBundle>, std::string>> pendingFlames;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<FlameProjectileFactory>& factorySlot() {
    static std::shared_ptr<FlameProjectileFactory> f;
    return f;
}

/** Params from a JSON document, falling back to the built-in preset tagged with `failureId`. */
FlameProjectileParams paramsFromJsonText(const std::string& text, const std::string& failureId) {
    try {
        return ParamUtils::fromJson(nlohmann::json::parse(text));
    } catch (const std::exception&) {
        FlameProjectileParams params = FlameProjectileFactory::defaultParams();
        params.id = failureId;
        return params;
    }
}
} // namespace

void FlameProjectileLuaBindings::setFactory(std::shared_ptr<FlameProjectileFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<FlameProjectileFactory> FlameProjectileLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): use the global instance (not owned, never deleted).
        g_flameFactory.initialize(64, 4);
        slot = std::shared_ptr<FlameProjectileFactory>(&g_flameFactory, [](FlameProjectileFactory*) {});
    }
    return slot;
}

void FlameProjectileLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum("FlameType",
        "FIREBALL", FlameType::FIREBALL,
        "INFERNO_BOLT", FlameType::INFERNO_BOLT,
        "HELLFIRE", FlameType::HELLFIRE,
        "PLASMA_FLAME", FlameType::PLASMA_FLAME,
        "MAGIC_FIRE", FlameType::MAGIC_FIRE,
        "CUSTOM", FlameType::CUSTOM
    );
    
    lua.new_enum("FlameShape",
        "CONE", FlameShape::CONE,
        "RIBBON", FlameShape::RIBBON,
        "SPHERE", FlameShape::SPHERE,
        "CYLINDER", FlameShape::CYLINDER,
        "CUSTOM_SHAPE", FlameShape::CUSTOM_SHAPE
    );
    
    lua.new_enum("BlendMode",
        "ADDITIVE", BlendMode::ADDITIVE,
        "MULTIPLY", BlendMode::MULTIPLY,
        "SCREEN", BlendMode::SCREEN,
        "OVERLAY", BlendMode::OVERLAY,
        "NORMAL", BlendMode::NORMAL
    );
    
    lua.new_enum("NoiseType",
        "PERLIN", NoiseType::PERLIN,
        "SIMPLEX", NoiseType::SIMPLEX,
        "CURL", NoiseType::CURL,
        "FRACTAL", NoiseType::FRACTAL,
        "CUSTOM", NoiseType::CUSTOM
    );
    
    lua.new_enum("TrailType",
        "NONE", TrailType::NONE,
        "RIBBON", TrailType::RIBBON,
        "PARTICLES", TrailType::PARTICLES,
        "SMOKE", TrailType::SMOKE,
        "HEAT_DISTORTION", TrailType::HEAT_DISTORTION,
        "CUSTOM", TrailType::CUSTOM
    );

    // Bind parameter struct
    lua.new_usertype<FlameProjectileParams>("FlameProjectileParams",
        sol::constructors<FlameProjectileParams()>(),
        
        // Basic properties
        "id", &FlameProjectileParams::id,
        "flameType", &FlameProjectileParams::flameType,
        "flameShape", &FlameProjectileParams::flameShape,
        "blendMode", &FlameProjectileParams::blendMode,
        "noiseType", &FlameProjectileParams::noiseType,
        "trailType", &FlameProjectileParams::trailType,
        
        // Physical properties
        "speed", &FlameProjectileParams::speed,
        "length", &FlameProjectileParams::length,
        "width", &FlameProjectileParams::width,
        "flameHeight", &FlameProjectileParams::flameHeight,
        "flameWidthVariation", &FlameProjectileParams::flameWidthVariation,
        
        // Color properties
        "coreColor", &FlameProjectileParams::coreColor,
        "outerColor", &FlameProjectileParams::outerColor,
        "glowColor", &FlameProjectileParams::glowColor,
        "emberColor", &FlameProjectileParams::emberColor,
        
        // Animation properties
        "flickerIntensity", &FlameProjectileParams::flickerIntensity,
        "flickerSpeed", &FlameProjectileParams::flickerSpeed,
        "turbulenceStrength", &FlameProjectileParams::turbulenceStrength,
        "turbulenceScale", &FlameProjectileParams::turbulenceScale,
        "oscillationFreq", &FlameProjectileParams::oscillationFreq,
        "oscillationAmplitude", &FlameProjectileParams::oscillationAmplitude,
        
        // Trail properties
        "trailLength", &FlameProjectileParams::trailLength,
        "trailWidth", &FlameProjectileParams::trailWidth,
        "trailOpacity", &FlameProjectileParams::trailOpacity,
        "enableTrailFade", &FlameProjectileParams::enableTrailFade,
        "trailFadeSpeed", &FlameProjectileParams::trailFadeSpeed,
        
        // Particle properties
        "emberCount", &FlameProjectileParams::emberCount,
        "emberLifetime", &FlameProjectileParams::emberLifetime,
        "emberSize", &FlameProjectileParams::emberSize,
        "emberSpeed", &FlameProjectileParams::emberSpeed,
        "enableEmberFade", &FlameProjectileParams::enableEmberFade,
        "emberFadeSpeed", &FlameProjectileParams::emberFadeSpeed,
        
        // Shader properties
        "shaderType", &FlameProjectileParams::shaderType,
        "shaderIntensity", &FlameProjectileParams::shaderIntensity,
        "enableDistortion", &FlameProjectileParams::enableDistortion,
        "distortionStrength", &FlameProjectileParams::distortionStrength,
        "enableBlur", &FlameProjectileParams::enableBlur,
        "blurStrength", &FlameProjectileParams::blurStrength,
        "enableHeatDistortion", &FlameProjectileParams::enableHeatDistortion,
        "heatDistortionStrength", &FlameProjectileParams::heatDistortionStrength,
        
        // Physics properties
        "enablePhysics", &FlameProjectileParams::enablePhysics,
        "physicsMass", &FlameProjectileParams::physicsMass,
        "physicsDrag", &FlameProjectileParams::physicsDrag,
        "physicsLift", &FlameProjectileParams::physicsLift,
        "enableCollision", &FlameProjectileParams::enableCollision,
        "collisionRadius", &FlameProjectileParams::collisionRadius,
        
        // Performance properties
        "enableCaching", &FlameProjectileParams::enableCaching,
        "enableHotReload", &FlameProjectileParams::enableHotReload,
        "enableParallelProcessing", &FlameProjectileParams::enableParallelProcessing,
        "lodLevel", &FlameProjectileParams::lodLevel,
        
        // Metadata
        "description", &FlameProjectileParams::description,
        "tags", &FlameProjectileParams::tags,
        // Exposed as a plain Lua table (copy in/out): the vendored sol2 container usertype cannot iterate std::map
        "metadata", sol::property(
            [](const FlameProjectileParams& params) { return sol::as_table(params.metadata); },
            [](FlameProjectileParams& params, sol::table table) {
                params.metadata.clear();
                for (const auto& [key, value] : table) {
                    params.metadata[key.as<std::string>()] = value.as<std::string>();
                }
            }),
        
        // Methods
        "hashKey", &FlameProjectileParams::hashKey
    );

    // Bind asset bundle
    lua.new_usertype<FlameAssetBundle>("FlameAssetBundle",
        "mesh", &FlameAssetBundle::mesh,
        "shader", &FlameAssetBundle::shader,
        "texture", &FlameAssetBundle::texture,
        "embers", &FlameAssetBundle::embers,
        "trail", &FlameAssetBundle::trail,
        "smoke", &FlameAssetBundle::smoke,
        "heatDistortion", &FlameAssetBundle::heatDistortion,
        "generationTime", &FlameAssetBundle::generationTime,
        "vertexCount", &FlameAssetBundle::vertexCount,
        "triangleCount", &FlameAssetBundle::triangleCount,
        "particleCount", &FlameAssetBundle::particleCount,
        "gpuAccelerated", &FlameAssetBundle::gpuAccelerated
    );

    lua.new_usertype<FlameProjectileFactory::PerformanceMetrics>("FlamePerformanceMetrics",
        "totalGenerations", &FlameProjectileFactory::PerformanceMetrics::totalGenerations,
        "cacheHits", &FlameProjectileFactory::PerformanceMetrics::cacheHits,
        "cacheMisses", &FlameProjectileFactory::PerformanceMetrics::cacheMisses,
        "totalGenerationTime", &FlameProjectileFactory::PerformanceMetrics::totalGenerationTime,
        "averageGenerationTime", &FlameProjectileFactory::PerformanceMetrics::averageGenerationTime,
        "getHitRate", &FlameProjectileFactory::PerformanceMetrics::getHitRate
    );

    // Fully initialized preset to start from (a bare FlameProjectileParams() leaves fields unset)
    lua.set_function("flame_default_params", []() {
        return FlameProjectileFactory::defaultParams();
    });

    // Bind factory functions
    lua.set_function("spawn_flame_projectile",
        [](const FlameProjectileParams& fp) {
            auto bundle = FlameProjectileLuaBindings::factory()->generateSync(fp);
            return bundle;
        }
    );

    // Queues generation; the bundle is reported by poll_assets. Returns the tracking id.
    lua.set_function("spawn_flame_projectile_async",
        [](const FlameProjectileParams& fp) {
            auto fut = FlameProjectileLuaBindings::factory()->generateAsync(fp);
            pendingFlames.emplace_back(std::move(fut), fp.id);
            return fp.id;
        }
    );

    // Bind validation functions
    lua.set_function("validate_flame_params", [](const FlameProjectileParams& params) {
        return FlameProjectileLuaBindings::factory()->validateParams(params);
    });

    lua.set_function("get_flame_validation_errors", [](const FlameProjectileParams& params) {
        return FlameProjectileLuaBindings::factory()->getValidationErrors(params);
    });

    // Bind JSON loading functions
    // Queues generation from a params file; reported by poll_assets under the file path.
    lua.set_function("load_flame_from_json", [](const std::string& jsonPath) {
        auto fut = FlameProjectileLuaBindings::factory()->generateFromJson(jsonPath);
        pendingFlames.emplace_back(std::move(fut), jsonPath);
        return jsonPath;
    });

    // Bind batch generation: queues every entry (reported by poll_assets), returns how many were queued
    lua.set_function("generate_flame_batch", [](const std::vector<FlameProjectileParams>& params) {
        auto futures = FlameProjectileLuaBindings::factory()->generateBatchAsync(params);
        for (size_t i = 0; i < futures.size(); ++i) {
            pendingFlames.emplace_back(std::move(futures[i]), params[i].id);
        }
        return futures.size();
    });

    // Bind cache management
    lua.set_function("clear_flame_cache", []() {
        FlameProjectileLuaBindings::factory()->clearCache();
    });

    lua.set_function("get_flame_cache_size", []() {
        return FlameProjectileLuaBindings::factory()->getCacheSize();
    });

    lua.set_function("get_flame_cache_capacity", []() {
        return FlameProjectileLuaBindings::factory()->getCacheCapacity();
    });

    lua.set_function("get_flame_cache_hit_rate", []() {
        return FlameProjectileLuaBindings::factory()->getCacheHitRate();
    });

    lua.set_function("set_flame_cache_capacity", [](size_t capacity) {
        FlameProjectileLuaBindings::factory()->setCacheCapacity(capacity);
    });

    // Bind performance monitoring
    lua.set_function("get_flame_performance_metrics", []() {
        return FlameProjectileLuaBindings::factory()->getPerformanceMetrics();
    });

    lua.set_function("reset_flame_performance_metrics", []() {
        FlameProjectileLuaBindings::factory()->resetPerformanceMetrics();
    });

    // Bind utility functions
    lua.set_function("flame_type_to_string", [](FlameType type) {
        return ParamUtils::flameTypeToString(type);
    });

    lua.set_function("flame_shape_to_string", [](FlameShape shape) {
        return ParamUtils::flameShapeToString(shape);
    });

    lua.set_function("blend_mode_to_string", [](BlendMode mode) {
        return ParamUtils::blendModeToString(mode);
    });

    lua.set_function("noise_type_to_string", [](NoiseType type) {
        return ParamUtils::noiseTypeToString(type);
    });

    lua.set_function("trail_type_to_string", [](TrailType type) {
        return ParamUtils::trailTypeToString(type);
    });

    lua.set_function("parse_flame_type", [](const std::string& str) {
        return ParamUtils::parseFlameType(str);
    });

    lua.set_function("parse_flame_shape", [](const std::string& str) {
        return ParamUtils::parseFlameShape(str);
    });

    lua.set_function("parse_blend_mode", [](const std::string& str) {
        return ParamUtils::parseBlendMode(str);
    });

    lua.set_function("parse_noise_type", [](const std::string& str) {
        return ParamUtils::parseNoiseType(str);
    });

    lua.set_function("parse_trail_type", [](const std::string& str) {
        return ParamUtils::parseTrailType(str);
    });

    // Bind JSON serialization/deserialization
    lua.set_function("flame_params_to_json", [](const FlameProjectileParams& params) {
        auto json = ParamUtils::toJson(params);
        return json.dump(2); // Pretty print with 2 spaces
    });

    lua.set_function("flame_params_from_json", [](const std::string& jsonStr) {
        return paramsFromJsonText(jsonStr, "error_loading");
    });

    // Bind file operations
    lua.set_function("save_flame_params_to_file", [](const FlameProjectileParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                file.close();
                return true;
            }
            return false;
        } catch (const std::exception&) {
            return false;
        }
    });

    lua.set_function("load_flame_params_from_file", [](const std::string& filePath) {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            // Default preset tagged so the caller can tell the file was missing
            FlameProjectileParams params = FlameProjectileFactory::defaultParams();
            params.id = "file_not_found";
            return params;
        }
        std::stringstream buffer;
        buffer << file.rdbuf();
        return paramsFromJsonText(buffer.str(), "error_loading");
    });

    // Create global flame factory table
    lua["FlameFactory"] = lua.create_table_with(
        "getInstance", []() -> FlameProjectileFactory* {
            return FlameProjectileLuaBindings::factory().get();
        },
        "initialize", [](size_t cacheSize, size_t numThreads) {
            FlameProjectileLuaBindings::factory()->initialize(cacheSize, numThreads);
        },
        "shutdown", []() {
            FlameProjectileLuaBindings::factory()->shutdown();
        },
        "generateSync", [](const FlameProjectileParams& params) {
            return FlameProjectileLuaBindings::factory()->generateSync(params);
        },
        // Async variants queue into poll_assets and return the tracking id
        "generateAsync", [](const FlameProjectileParams& params) {
            pendingFlames.emplace_back(FlameProjectileLuaBindings::factory()->generateAsync(params), params.id);
            return params.id;
        },
        "generateFromJson", [](const std::string& jsonPath) {
            pendingFlames.emplace_back(FlameProjectileLuaBindings::factory()->generateFromJson(jsonPath), jsonPath);
            return jsonPath;
        },
        // Generates the whole batch in parallel and returns the finished bundles
        "generateBatch", [](const std::vector<FlameProjectileParams>& params) {
            auto futures = FlameProjectileLuaBindings::factory()->generateBatchAsync(params);
            std::vector<FlameAssetBundle> bundles;
            bundles.reserve(futures.size());
            for (auto& fut : futures) {
                bundles.push_back(fut.get());
            }
            return bundles;
        },
        "validateParams", [](const FlameProjectileParams& params) {
            return FlameProjectileLuaBindings::factory()->validateParams(params);
        },
        "getValidationErrors", [](const FlameProjectileParams& params) {
            return FlameProjectileLuaBindings::factory()->getValidationErrors(params);
        },
        "clearCache", []() {
            FlameProjectileLuaBindings::factory()->clearCache();
        },
        "getCacheSize", []() {
            return FlameProjectileLuaBindings::factory()->getCacheSize();
        },
        "getCacheHitRate", []() {
            return FlameProjectileLuaBindings::factory()->getCacheHitRate();
        },
        "getPerformanceMetrics", []() {
            return FlameProjectileLuaBindings::factory()->getPerformanceMetrics();
        },
        "resetPerformanceMetrics", []() {
            FlameProjectileLuaBindings::factory()->resetPerformanceMetrics();
        }
    );
}

void FlameProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingFlames.begin(); it != pendingFlames.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                lua["print"]("Flame projectile ready: " + it->second);
                lua["print"]("Mesh ID: " + std::to_string(bundle.mesh));
                lua["print"]("Shader ID: " + std::to_string(bundle.shader));
                lua["print"]("Texture ID: " + std::to_string(bundle.texture));
                lua["print"]("Embers ID: " + std::to_string(bundle.embers));
                lua["print"]("Trail ID: " + std::to_string(bundle.trail));
                lua["print"]("Smoke ID: " + std::to_string(bundle.smoke));
                lua["print"]("Heat Distortion ID: " + std::to_string(bundle.heatDistortion));
                lua["print"]("Generation time: " + std::to_string(bundle.generationTime) + "s");
                lua["print"]("Vertex count: " + std::to_string(bundle.vertexCount));
                lua["print"]("Triangle count: " + std::to_string(bundle.triangleCount));
                lua["print"]("Particle count: " + std::to_string(bundle.particleCount));
                lua["print"]("GPU accelerated: " + std::string(bundle.gpuAccelerated ? "true" : "false"));
            } catch (const std::exception& e) {
                lua["print"]("Flame projectile error: " + std::string(e.what()));
            }
            it = pendingFlames.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace FlameProjectiles
} // namespace MagiTech
