#include "RealTimeArtGenerator.hpp"
#include "CrossbowAssetGenerator.hpp"
#include "core/Log.hpp"
#include <sol/sol.hpp>

namespace MagiTech {
namespace RealTimeArt {

void bindRealTimeArtGenerator(sol::state& lua) {
    // Bind GenDef struct
    lua.new_usertype<RealTimeArtGenerator::GenDef>("GenDef",
        sol::constructors<RealTimeArtGenerator::GenDef()>(),
        "prompt", &RealTimeArtGenerator::GenDef::prompt,
        "outW", &RealTimeArtGenerator::GenDef::outW,
        "outH", &RealTimeArtGenerator::GenDef::outH,
        "directions", &RealTimeArtGenerator::GenDef::directions,
        "seed", &RealTimeArtGenerator::GenDef::seed,
        "style", &RealTimeArtGenerator::GenDef::style,
        "palette", &RealTimeArtGenerator::GenDef::palette,
        "effects", &RealTimeArtGenerator::GenDef::effects
    );

    // Bind DamageParams struct
    lua.new_usertype<RealTimeArtGenerator::DamageParams>("DamageParams",
        sol::constructors<RealTimeArtGenerator::DamageParams()>(),
        "baseTexId", &RealTimeArtGenerator::DamageParams::baseTexId,
        "impactX", &RealTimeArtGenerator::DamageParams::impactX,
        "impactY", &RealTimeArtGenerator::DamageParams::impactY,
        "intensity", &RealTimeArtGenerator::DamageParams::intensity,
        "seed", &RealTimeArtGenerator::DamageParams::seed,
        "useAI", &RealTimeArtGenerator::DamageParams::useAI,
        "prompt", &RealTimeArtGenerator::DamageParams::prompt,
        "damageType", &RealTimeArtGenerator::DamageParams::damageType
    );

    // Bind TextureHandle struct
    lua.new_usertype<RealTimeArtGenerator::TextureHandle>("TextureHandle",
        sol::constructors<RealTimeArtGenerator::TextureHandle()>(),
        "id", &RealTimeArtGenerator::TextureHandle::id,
        "width", &RealTimeArtGenerator::TextureHandle::width,
        "height", &RealTimeArtGenerator::TextureHandle::height,
        "isValid", &RealTimeArtGenerator::TextureHandle::isValid
    );

    // Bind Stats struct
    lua.new_usertype<RealTimeArtGenerator::Stats>("ArtGenStats",
        "totalRequests", &RealTimeArtGenerator::Stats::totalRequests,
        "cacheHits", &RealTimeArtGenerator::Stats::cacheHits,
        "aiGenerations", &RealTimeArtGenerator::Stats::aiGenerations,
        "shaderEdits", &RealTimeArtGenerator::Stats::shaderEdits,
        "averageGenerationTime", &RealTimeArtGenerator::Stats::averageGenerationTime,
        "averageDamageEditTime", &RealTimeArtGenerator::Stats::averageDamageEditTime
    );

    // Create ArtGen table
    lua["ArtGen"] = lua.create_table_with(
        // Main generation functions
        "generate", [&](const RealTimeArtGenerator::GenDef& def, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generate(def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "generateCrossbow", [&](const CrossbowParams& params, const RealTimeArtGenerator::GenDef& def, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generateCrossbow(params, def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "generateBolt", [&](const BoltParams& params, const RealTimeArtGenerator::GenDef& def, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generateBolt(params, def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "generateArrow", [&](const ArrowParams& params, const RealTimeArtGenerator::GenDef& def, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generateArrow(params, def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        // Damage editing functions
        "editDamage", [&](const RealTimeArtGenerator::DamageParams& params, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->editDamage(params, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "addBulletHole", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->addBulletHole(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "addCrack", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->addCrack(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        "addBurn", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->addBurn(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        },

        // Batch generation
        "generateBatch", [&](const std::vector<RealTimeArtGenerator::GenDef>& defs, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generateBatch(defs, [callback](const std::vector<RealTimeArtGenerator::TextureHandle>& textures) {
                callback(textures);
            });
        },

        "generateCrossbowBatch", [&](const std::vector<std::pair<CrossbowParams, RealTimeArtGenerator::GenDef>>& items, sol::function callback) {
            if (!g_realTimeArtGenerator) {
                Log::error("Real-time art generator not initialized");
                return;
            }
            g_realTimeArtGenerator->generateCrossbowBatch(items, [callback](const std::vector<RealTimeArtGenerator::TextureHandle>& textures) {
                callback(textures);
            });
        },

        // Utility functions
        "update", [&]() {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->update();
            }
        },

        "clearCache", [&]() {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->clearCache();
            }
        },

        "getCacheSize", [&]() -> size_t {
            return g_realTimeArtGenerator ? g_realTimeArtGenerator->getCacheSize() : 0;
        },

        "getStats", [&]() -> RealTimeArtGenerator::Stats {
            return g_realTimeArtGenerator ? g_realTimeArtGenerator->getStats() : RealTimeArtGenerator::Stats{};
        },

        "isInitialized", [&]() -> bool {
            return g_realTimeArtGenerator != nullptr;
        }
    );

    // Create convenience functions for common weapon types
    lua["createLaserRifle"] = [&](sol::function callback) {
        RealTimeArtGenerator::GenDef def;
        def.prompt = "pixel-art 64x64 laser rifle, side view, neon blue highlights";
        def.outW = 64;
        def.outH = 64;
        def.directions = 4;
        def.seed = std::random_device()();
        def.style = "pixel-art";
        def.palette = "neon";
        def.effects = {"metallic", "glowing"};

        if (g_realTimeArtGenerator) {
            g_realTimeArtGenerator->generate(def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        }
    };

    lua["createIceStaff"] = [&](sol::function callback) {
        RealTimeArtGenerator::GenDef def;
        def.prompt = "pixel-art 64x64 ice staff, top-down, frost theme";
        def.outW = 64;
        def.outH = 64;
        def.directions = 1;
        def.seed = std::random_device()();
        def.style = "pixel-art";
        def.palette = "starbound";
        def.effects = {"frost", "crystalline"};

        if (g_realTimeArtGenerator) {
            g_realTimeArtGenerator->generate(def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        }
    };

    lua["createPlasmaPistol"] = [&](sol::function callback) {
        RealTimeArtGenerator::GenDef def;
        def.prompt = "pixel-art 64x64 plasma pistol, 8 directions, clean linework, neon green";
        def.outW = 64;
        def.outH = 64;
        def.directions = 8;
        def.seed = std::random_device()();
        def.style = "pixel-art";
        def.palette = "neon";
        def.effects = {"plasma", "high-tech"};

        if (g_realTimeArtGenerator) {
            g_realTimeArtGenerator->generate(def, [callback](RealTimeArtGenerator::TextureHandle tex) {
                callback(tex);
            });
        }
    };

    // Create damage editing convenience functions
    lua["Damage"] = lua.create_table_with(
        "edit", [&](const RealTimeArtGenerator::DamageParams& params, sol::function callback) {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->editDamage(params, [callback](RealTimeArtGenerator::TextureHandle tex) {
                    callback(tex);
                });
            }
        },

        "addBulletHole", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->addBulletHole(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                    callback(tex);
                });
            }
        },

        "addCrack", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->addCrack(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                    callback(tex);
                });
            }
        },

        "addBurn", [&](uint32_t baseTexId, float x, float y, float intensity, sol::function callback) {
            if (g_realTimeArtGenerator) {
                g_realTimeArtGenerator->addBurn(baseTexId, x, y, intensity, [callback](RealTimeArtGenerator::TextureHandle tex) {
                    callback(tex);
                });
            }
        }
    );

    Log::info("Real-time art generation Lua bindings initialized");
}

} // namespace RealTimeArt
} // namespace MagiTech 
