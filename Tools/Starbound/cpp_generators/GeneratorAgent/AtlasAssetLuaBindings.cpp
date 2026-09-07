#include "AtlasAssetLuaBindings.hpp"
#include "AtlasAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace AtlasAssets {

static std::vector<std::pair<std::future<AtlasBundle>, std::string>> pendingAtlases;

void AtlasAssetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SpriteParams>("SpriteParams", sol::constructors<SpriteParams()>(),
        "id", &SpriteParams::id, "path", &SpriteParams::path, "trim", &SpriteParams::trim, "border", &SpriteParams::border);

    lua.new_usertype<AtlasParams>("AtlasParams", sol::constructors<AtlasParams()>(),
        "id", &AtlasParams::id, "maxWidth", &AtlasParams::maxWidth, "maxHeight", &AtlasParams::maxHeight, "padding", &AtlasParams::padding,
        "allowRotation", &AtlasParams::allowRotation, "generateMipmaps", &AtlasParams::generateMipmaps, "mipLevels", &AtlasParams::mipLevels);

    lua.new_usertype<MaterialParams>("MaterialParams", sol::constructors<MaterialParams()>(),
        "shader", &MaterialParams::shader, "alphaTest", &MaterialParams::alphaTest, "alphaThreshold", &MaterialParams::alphaThreshold);

    lua.new_usertype<LODParams>("LODParams", sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes, "atlasResolutions", &LODParams::atlasResolutions);

    lua.new_usertype<AtlasBundle>("AtlasBundle", sol::no_constructor,
        "atlasTex", &AtlasBundle::atlasTex, "uvMap", &AtlasBundle::uvMap, "material", &AtlasBundle::material, "lodData", &AtlasBundle::lodData);

    lua.set_function("spawn_atlas_asset",
        [&](const std::vector<SpriteParams>& sprites, const AtlasParams& ap, const MaterialParams& mp, const LODParams& lp) {
            auto factory = MainPlugin::instance().getAtlasAssetFactory();
            pendingAtlases.emplace_back(factory->generateAsync(sprites, ap, mp, lp), ap.id);
        }
    );
}

void AtlasAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAtlases.begin(); it != pendingAtlases.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Atlas asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingAtlases.erase(it);
        } else { ++it; }
    }
}

} // namespace AtlasAssets
} // namespace MagiTech
