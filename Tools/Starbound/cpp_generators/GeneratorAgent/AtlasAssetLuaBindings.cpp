#include "AtlasAssetLuaBindings.hpp"
#include "AtlasAssetFactory.hpp"
#include "core/Log.hpp"
#include <chrono>
#include <mutex>
#include <vector>

namespace MagiTech {
namespace AtlasAssets {

static std::vector<std::pair<std::future<AtlasBundle>, std::string>> pendingAtlases;
static std::mutex pendingAtlasesMutex;

static std::mutex factoryMutex;
static std::shared_ptr<AtlasAssetFactory> sharedFactory;

void AtlasAssetLuaBindings::setFactory(std::shared_ptr<AtlasAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    sharedFactory = std::move(factory);
}

std::shared_ptr<AtlasAssetFactory> AtlasAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!sharedFactory) {
        sharedFactory = std::make_shared<AtlasAssetFactory>();
        sharedFactory->initialize(16, 4);
    }
    return sharedFactory;
}

void AtlasAssetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SpriteParams>("SpriteParams", sol::constructors<SpriteParams()>(),
        "id", &SpriteParams::id, "path", &SpriteParams::path, "trim", &SpriteParams::trim, "border", &SpriteParams::border);

    lua.new_usertype<AtlasParams>("AtlasParams", sol::constructors<AtlasParams()>(),
        "id", &AtlasParams::id, "maxWidth", &AtlasParams::maxWidth, "maxHeight", &AtlasParams::maxHeight, "padding", &AtlasParams::padding,
        "allowRotation", &AtlasParams::allowRotation, "generateMipmaps", &AtlasParams::generateMipmaps, "mipLevels", &AtlasParams::mipLevels);

    lua.new_usertype<MaterialParams>("AtlasMaterialParams", sol::constructors<MaterialParams()>(),
        "shader", &MaterialParams::shader, "alphaTest", &MaterialParams::alphaTest, "alphaThreshold", &MaterialParams::alphaThreshold);

    lua.new_usertype<LODParams>("AtlasLODParams", sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes, "atlasResolutions", &LODParams::atlasResolutions);

    lua.new_usertype<LODData>("AtlasLODData", sol::no_constructor,
        "screenSizes", &LODData::screenSizes, "lodAtlases", &LODData::lodAtlases);

    lua.new_usertype<AtlasBundle>("AtlasBundle", sol::no_constructor,
        "atlasTex", &AtlasBundle::atlasTex,
        "uvMap", sol::readonly_property([](const AtlasBundle& b, sol::this_state ts) {
            // Exposed as a plain Lua table: { [spriteId] = { x =, y =, w =, h = } }
            sol::state_view view(ts);
            sol::table out = view.create_table();
            for (const auto& [spriteId, rect] : b.uvMap) {
                out[spriteId] = view.create_table_with("x", rect.x, "y", rect.y, "w", rect.z, "h", rect.w);
            }
            return out;
        }),
        "material", &AtlasBundle::material, "lodData", &AtlasBundle::lodData);

    lua.set_function("spawn_atlas_asset",
        [](const std::vector<SpriteParams>& sprites, const AtlasParams& ap, const MaterialParams& mp, const LODParams& lp) {
            auto future = factory()->generateAsync(sprites, ap, mp, lp);
            std::lock_guard<std::mutex> lock(pendingAtlasesMutex);
            pendingAtlases.emplace_back(std::move(future), ap.id);
        }
    );
}

void AtlasAssetLuaBindings::poll_assets(sol::state& lua) {
    std::lock_guard<std::mutex> lock(pendingAtlasesMutex);
    for (auto it = pendingAtlases.begin(); it != pendingAtlases.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Atlas asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("AtlasAssets", "Asset generation failed for {}: {}", it->second, e.what());
            }
            it = pendingAtlases.erase(it);
        } else { ++it; }
    }
}

} // namespace AtlasAssets
} // namespace MagiTech
