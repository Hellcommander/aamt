#include "CometProjectileLuaBindings.hpp"
#include "CometProjectileFactory.hpp"
#include "CometProjectileTypes.hpp"
#include "CometProjectileGenerators.cpp"
#include <fstream>
#include <sstream>

namespace MagiTech {
namespace CometProjectiles {

static std::vector<std::pair<std::future<CometAssetBundle>, std::string>> pendingComets;

void CometProjectileLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum("CometType",
        "METEOR", CometType::METEOR,
        "COMET", CometType::COMET,
        "ASTEROID", CometType::ASTEROID,
        "FALLING_STAR", CometType::FALLING_STAR,
        "CELESTIAL_ROCK", CometType::CELESTIAL_ROCK,
        "CUSTOM", CometType::CUSTOM
    );
    
    lua.new_enum("CometShape",
        "SPHERE", CometShape::SPHERE,
        "IRREGULAR", CometShape::IRREGULAR,
        "FRAGMENTED", CometShape::FRAGMENTED,
        "CRYSTALLINE", CometShape::CRYSTALLINE,
        "CUSTOM_SHAPE", CometShape::CUSTOM_SHAPE
    );
    
    lua.new_enum("TrailType",
        "NONE", TrailType::NONE,
        "DUST", TrailType::DUST,
        "FIRE", TrailType::FIRE,
        "SMOKE", TrailType::SMOKE,
        "SPARKS", TrailType::SPARKS,
        "CUSTOM", TrailType::CUSTOM
    );
    
    lua.new_enum("FragmentationType",
        "NONE", FragmentationType::NONE,
        "EXPLOSIVE", FragmentationType::EXPLOSIVE,
        "SHATTER", FragmentationType::SHATTER,
        "DISINTEGRATE", FragmentationType::DISINTEGRATE,
        "CUSTOM", FragmentationType::CUSTOM
    );
    
    lua.new_enum("NoiseType",
        "PERLIN", NoiseType::PERLIN,
        "SIMPLEX", NoiseType::SIMPLEX,
        "CURL", NoiseType::CURL,
        "FRACTAL", NoiseType::FRACTAL,
        "CUSTOM", NoiseType::CUSTOM
    );
    
    lua.new_enum("BlendMode",
        "ADDITIVE", BlendMode::ADDITIVE,
        "MULTIPLY", BlendMode::MULTIPLY,
        "SCREEN", BlendMode::SCREEN,
        "OVERLAY", BlendMode::OVERLAY,
        "NORMAL", BlendMode::NORMAL
    );

    // Bind parameter struct
    lua.new_usertype<CometProjectileParams>("CometProjectileParams",
        sol::constructors<CometProjectileParams()>(),
        
        // Basic properties
        "id", &CometProjectileParams::id,
        "cometType", &CometProjectileParams::cometType,
        "cometShape", &CometProjectileParams::cometShape,
        "trailType", &CometProjectileParams::trailType,
        "fragmentationType", &CometProjectileParams::fragmentationType,
        "noiseType", &CometProjectileParams::noiseType,
        "blendMode", &CometProjectileParams::blendMode,
        
        // Physical properties
        "coreRadius", &CometProjectileParams::coreRadius,
        "irregularity", &CometProjectileParams::irregularity,
        "speed", &CometProjectileParams::speed,
        "gravityInfluence", &CometProjectileParams::gravityInfluence,
        "mass", &CometProjectileParams::mass,
        "drag", &CometProjectileParams::drag,
        "lift", &CometProjectileParams::lift,
        
        // Color properties
        "heatColor", &CometProjectileParams::heatColor,
        "burnColor", &CometProjectileParams::burnColor,
        "coreColor", &CometProjectileParams::coreColor,
        "glowColor", &CometProjectileParams::glowColor,
        "dustColor", &CometProjectileParams::dustColor,
        "sparkColor", &CometProjectileParams::sparkColor,
        
        // Visual properties
        "glowIntensity", &CometProjectileParams::glowIntensity,
        "emissivePower", &CometProjectileParams::emissivePower,
        "coreOpacity", &CometProjectileParams::coreOpacity,
        "trailOpacity", &CometProjectileParams::trailOpacity,
        "enableCoreGlow", &CometProjectileParams::enableCoreGlow,
        "enableTrailGlow", &CometProjectileParams::enableTrailGlow,
        
        // Trail properties
        "trailLength", &CometProjectileParams::trailLength,
        "trailWidth", &CometProjectileParams::trailWidth,
        "trailNoiseScale", &CometProjectileParams::trailNoiseScale,
        "trailNoiseSpeed", &CometProjectileParams::trailNoiseSpeed,
        "trailFadeSpeed", &CometProjectileParams::trailFadeSpeed,
        "enableTrailFade", &CometProjectileParams::enableTrailFade,
        "enableTrailDistortion", &CometProjectileParams::enableTrailDistortion,
        "trailDistortionStrength", &CometProjectileParams::trailDistortionStrength,
        
        // Particle properties
        "dustParticleCount", &CometProjectileParams::dustParticleCount,
        "dustLifetime", &CometProjectileParams::dustLifetime,
        "dustSize", &CometProjectileParams::dustSize,
        "dustSpeed", &CometProjectileParams::dustSpeed,
        "enableDustFade", &CometProjectileParams::enableDustFade,
        "dustFadeSpeed", &CometProjectileParams::dustFadeSpeed,
        
        "sparkParticleCount", &CometProjectileParams::sparkParticleCount,
        "sparkLifetime", &CometProjectileParams::sparkLifetime,
        "sparkSize", &CometProjectileParams::sparkSize,
        "sparkSpeed", &CometProjectileParams::sparkSpeed,
        "enableSparkFade", &CometProjectileParams::enableSparkFade,
        "sparkFadeSpeed", &CometProjectileParams::sparkFadeSpeed,
        
        // Fragmentation properties
        "fragmentationCount", &CometProjectileParams::fragmentationCount,
        "fragmentSizeFactor", &CometProjectileParams::fragmentSizeFactor,
        "fragmentSpread", &CometProjectileParams::fragmentSpread,
        "fragmentVelocity", &CometProjectileParams::fragmentVelocity,
        "enableFragmentPhysics", &CometProjectileParams::enableFragmentPhysics,
        "fragmentLifetime", &CometProjectileParams::fragmentLifetime,
        
        // Shader properties
        "shaderType", &CometProjectileParams::shaderType,
        "shaderIntensity", &CometProjectileParams::shaderIntensity,
        "enableDistortion", &CometProjectileParams::enableDistortion,
        "distortionStrength", &CometProjectileParams::distortionStrength,
        "enableBlur", &CometProjectileParams::enableBlur,
        "blurStrength", &CometProjectileParams::blurStrength,
        "enableHeatDistortion", &CometProjectileParams::enableHeatDistortion,
        "heatDistortionStrength", &CometProjectileParams::heatDistortionStrength,
        
        // Physics properties
        "enablePhysics", &CometProjectileParams::enablePhysics,
        "enableCollision", &CometProjectileParams::enableCollision,
        "collisionRadius", &CometProjectileParams::collisionRadius,
        "enableGravity", &CometProjectileParams::enableGravity,
        "enableAirResistance", &CometProjectileParams::enableAirResistance,
        "airResistanceFactor", &CometProjectileParams::airResistanceFactor,
        
        // Performance properties
        "enableCaching", &CometProjectileParams::enableCaching,
        "enableHotReload", &CometProjectileParams::enableHotReload,
        "enableParallelProcessing", &CometProjectileParams::enableParallelProcessing,
        "lodLevel", &CometProjectileParams::lodLevel,
        
        // Metadata
        "description", &CometProjectileParams::description,
        "tags", &CometProjectileParams::tags,
        "metadata", &CometProjectileParams::metadata,
        
        // Methods
        "hashKey", &CometProjectileParams::hashKey
    );

    // Bind asset bundle
    lua.new_usertype<CometAssetBundle>("CometAssetBundle",
        "mesh", &CometAssetBundle::mesh,
        "shader", &CometAssetBundle::shader,
        "texture", &CometAssetBundle::texture,
        "dustTrail", &CometAssetBundle::dustTrail,
        "sparks", &CometAssetBundle::sparks,
        "fragments", &CometAssetBundle::fragments,
        "heatDistortion", &CometAssetBundle::heatDistortion,
        "generationTime", &CometAssetBundle::generationTime,
        "vertexCount", &CometAssetBundle::vertexCount,
        "triangleCount", &CometAssetBundle::triangleCount,
        "particleCount", &CometAssetBundle::particleCount,
        "gpuAccelerated", &CometAssetBundle::gpuAccelerated
    );

    // Bind factory functions
    lua.set_function("spawn_comet_projectile",
        [&](const CometProjectileParams& p) {
            auto bundle = g_cometFactory.generateSync(p);
            return bundle;
        }
    );

    lua.set_function("spawn_comet_projectile_async",
        [&](const CometProjectileParams& p) {
            auto fut = g_cometFactory.generateAsync(p);
            pendingComets.emplace_back(std::move(fut), p.id);
            return fut;
        }
    );

    // Bind validation functions
    lua.set_function("validate_comet_params", [](const CometProjectileParams& params) {
        return g_cometFactory.validateParams(params);
    });

    lua.set_function("get_comet_validation_errors", [](const CometProjectileParams& params) {
        return g_cometFactory.getValidationErrors(params);
    });

    // Bind JSON loading functions
    lua.set_function("load_comet_from_json", [](const std::string& jsonPath) {
        auto fut = g_cometFactory.generateFromJson(jsonPath);
        pendingComets.emplace_back(std::move(fut), "json_comet");
        return fut;
    });

    // Bind batch generation
    lua.set_function("generate_comet_batch", [](const std::vector<CometProjectileParams>& params) {
        return g_cometFactory.generateBatchAsync(params);
    });

    // Bind cache management
    lua.set_function("clear_comet_cache", []() {
        g_cometFactory.clearCache();
    });

    lua.set_function("get_comet_cache_size", []() {
        return g_cometFactory.getCacheSize();
    });

    lua.set_function("get_comet_cache_capacity", []() {
        return g_cometFactory.getCacheCapacity();
    });

    lua.set_function("get_comet_cache_hit_rate", []() {
        return g_cometFactory.getCacheHitRate();
    });

    lua.set_function("set_comet_cache_capacity", [](size_t capacity) {
        g_cometFactory.setCacheCapacity(capacity);
    });

    // Bind performance monitoring
    lua.set_function("get_comet_performance_metrics", []() {
        return g_cometFactory.getPerformanceMetrics();
    });

    lua.set_function("reset_comet_performance_metrics", []() {
        g_cometFactory.resetPerformanceMetrics();
    });

    // Bind utility functions
    lua.set_function("comet_type_to_string", [](CometType type) {
        return ParamUtils::cometTypeToString(type);
    });

    lua.set_function("comet_shape_to_string", [](CometShape shape) {
        return ParamUtils::cometShapeToString(shape);
    });

    lua.set_function("trail_type_to_string", [](TrailType type) {
        return ParamUtils::trailTypeToString(type);
    });

    lua.set_function("fragmentation_type_to_string", [](FragmentationType type) {
        return ParamUtils::fragmentationTypeToString(type);
    });

    lua.set_function("noise_type_to_string", [](NoiseType type) {
        return ParamUtils::noiseTypeToString(type);
    });

    lua.set_function("blend_mode_to_string", [](BlendMode mode) {
        return ParamUtils::blendModeToString(mode);
    });

    lua.set_function("parse_comet_type", [](const std::string& str) {
        return ParamUtils::parseCometType(str);
    });

    lua.set_function("parse_comet_shape", [](const std::string& str) {
        return ParamUtils::parseCometShape(str);
    });

    lua.set_function("parse_trail_type", [](const std::string& str) {
        return ParamUtils::parseTrailType(str);
    });

    lua.set_function("parse_fragmentation_type", [](const std::string& str) {
        return ParamUtils::parseFragmentationType(str);
    });

    lua.set_function("parse_noise_type", [](const std::string& str) {
        return ParamUtils::parseNoiseType(str);
    });

    lua.set_function("parse_blend_mode", [](const std::string& str) {
        return ParamUtils::parseBlendMode(str);
    });

    // Bind JSON serialization/deserialization
    lua.set_function("comet_params_to_json", [](const CometProjectileParams& params) {
        auto json = ParamUtils::toJson(params);
        return json.dump(2); // Pretty print with 2 spaces
    });

    lua.set_function("comet_params_from_json", [](const std::string& jsonStr) {
        try {
            auto json = nlohmann::json::parse(jsonStr);
            return ParamUtils::fromJson(json);
        } catch (const std::exception& e) {
            // Return default params on error
            CometProjectileParams params;
            params.id = "error_loading";
            return params;
        }
    });

    // Bind file operations
    lua.set_function("save_comet_params_to_file", [](const CometProjectileParams& params, const std::string& filePath) {
        try {
            auto json = ParamUtils::toJson(params);
            std::ofstream file(filePath);
            if (file.is_open()) {
                file << json.dump(2);
                file.close();
                return true;
            }
            return false;
        } catch (const std::exception& e) {
            return false;
        }
    });

    lua.set_function("load_comet_params_from_file", [](const std::string& filePath) {
        try {
            std::ifstream file(filePath);
            if (file.is_open()) {
                std::stringstream buffer;
                buffer << file.rdbuf();
                file.close();
                
                auto json = nlohmann::json::parse(buffer.str());
                return ParamUtils::fromJson(json);
            }
            // Return default params if file not found
            CometProjectileParams params;
            params.id = "file_not_found";
            return params;
        } catch (const std::exception& e) {
            // Return default params on error
            CometProjectileParams params;
            params.id = "error_loading";
            return params;
        }
    });

    // Create global comet factory table
    lua["CometFactory"] = lua.create_table_with(
        "getInstance", []() -> CometProjectileFactory* {
            return &g_cometFactory;
        },
        "initialize", [](size_t cacheSize, size_t numThreads) {
            g_cometFactory.initialize(cacheSize, numThreads);
        },
        "shutdown", []() {
            g_cometFactory.shutdown();
        },
        "generateSync", [](const CometProjectileParams& params) {
            return g_cometFactory.generateSync(params);
        },
        "generateAsync", [](const CometProjectileParams& params) {
            return g_cometFactory.generateAsync(params);
        },
        "generateFromJson", [](const std::string& jsonPath) {
            return g_cometFactory.generateFromJson(jsonPath);
        },
        "generateBatch", [](const std::vector<CometProjectileParams>& params) {
            return g_cometFactory.generateBatchAsync(params);
        },
        "validateParams", [](const CometProjectileParams& params) {
            return g_cometFactory.validateParams(params);
        },
        "getValidationErrors", [](const CometProjectileParams& params) {
            return g_cometFactory.getValidationErrors(params);
        },
        "clearCache", []() {
            g_cometFactory.clearCache();
        },
        "getCacheSize", []() {
            return g_cometFactory.getCacheSize();
        },
        "getCacheHitRate", []() {
            return g_cometFactory.getCacheHitRate();
        },
        "getPerformanceMetrics", []() {
            return g_cometFactory.getPerformanceMetrics();
        },
        "resetPerformanceMetrics", []() {
            g_cometFactory.resetPerformanceMetrics();
        }
    );
}

void CometProjectileLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingComets.begin(); it != pendingComets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto bundle = it->first.get();
                lua["print"]("Comet projectile ready: " + it->second);
                lua["print"]("Mesh ID: " + std::to_string(bundle.mesh));
                lua["print"]("Shader ID: " + std::to_string(bundle.shader));
                lua["print"]("Texture ID: " + std::to_string(bundle.texture));
                lua["print"]("Dust Trail ID: " + std::to_string(bundle.dustTrail));
                lua["print"]("Sparks ID: " + std::to_string(bundle.sparks));
                lua["print"]("Fragments ID: " + std::to_string(bundle.fragments));
                lua["print"]("Heat Distortion ID: " + std::to_string(bundle.heatDistortion));
                lua["print"]("Generation time: " + std::to_string(bundle.generationTime) + "s");
                lua["print"]("Vertex count: " + std::to_string(bundle.vertexCount));
                lua["print"]("Triangle count: " + std::to_string(bundle.triangleCount));
                lua["print"]("Particle count: " + std::to_string(bundle.particleCount));
                lua["print"]("GPU accelerated: " + std::string(bundle.gpuAccelerated ? "true" : "false"));
            } catch (const std::exception& e) {
                lua["print"]("Comet projectile error: " + std::string(e.what()));
            }
            it = pendingComets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace CometProjectiles
} // namespace MagiTech
