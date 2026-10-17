#include "DynamicAssetLuaBindings.hpp"
#include "DynamicAssetManager.hpp"
#include "DynamicAssetTypes.hpp"
#include <memory>
#include <mutex>
#include <map>
#include <future>
#include <vector>

namespace MagiTech {
namespace DynamicAssets {

static std::vector<std::pair<std::future<AssetBundle>, std::string>> pendingAssets;

namespace {
std::mutex& managerMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<DynamicAssetManager>& managerSlot() {
    static std::shared_ptr<DynamicAssetManager> f;
    return f;
}
} // namespace

void DynamicAssetLuaBindings::setManager(std::shared_ptr<DynamicAssetManager> manager) {
    std::lock_guard<std::mutex> lock(managerMutex());
    managerSlot() = std::move(manager);
}

std::shared_ptr<DynamicAssetManager> DynamicAssetLuaBindings::manager() {
    std::lock_guard<std::mutex> lock(managerMutex());
    auto& slot = managerSlot();
    if (!slot) {
        // No instance injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<DynamicAssetManager>();
        slot->initialize(64, 4);
    }
    return slot;
}
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
            auto manager = DynamicAssetLuaBindings::manager();
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
