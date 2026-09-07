#include "DynamicAssetLuaBindings.hpp"
#include "DynamicAssetManager.hpp"
#include "DynamicAssetTypes.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace DynamicAssets {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingAssets;
static std::vector<sol::function> callbacks;

void DynamicAssetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<SpellstoneParams>("SpellstoneParams",
        "id",            &SpellstoneParams::id,
        "hueStart",      &SpellstoneParams::hueStart,
        "hueEnd",        &SpellstoneParams::hueEnd,
        "facets",        &SpellstoneParams::facets,
        "frames",        &SpellstoneParams::frames,
        "pulseSpeed",    &SpellstoneParams::pulseSpeed,
        "glowIntensity", &SpellstoneParams::glowIntensity,
        "size",          &SpellstoneParams::size
    );

    lua.set_function("new_spellstone",
        [&](const SpellstoneParams& p){
            auto manager = MainPlugin::instance().getDynamicAssetManager();
            auto fut = manager->generateAsync(p);
            pendingAssets.emplace_back(std::move(fut), p.id);
        }
    );

    lua.set_function("on_ready",
        [](sol::function cb) {
            callbacks.push_back(cb);
        }
    );
}

void DynamicAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end(); ) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            auto bundle = it->first.get();
            for (auto& cb : callbacks) {
                cb(it->second, bundle.mesh, bundle.tex);
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace DynamicAssets
} // namespace MagiTech
