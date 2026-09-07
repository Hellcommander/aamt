#include "WormMechLuaBindings.hpp"
#include "WormMechFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "core/utils/Observable.hpp"
#include <vector>

namespace MagiTech {
namespace WormMechs {

// Note: The async polling mechanism is now managed within the dynamic instance updates.
// This static vector is kept for any legacy async calls but should be phased out.
static std::vector<std::pair<std::future<MechAssetBundle>, std::string>> pendingMechs;

void WormMechLuaBindings::bind(sol::state& lua) {
    // Parameter Structs
    lua.new_usertype<WormMechParams>("WormMechParams",
        sol::constructors<WormMechParams()>(),
        "id", &WormMechParams::id,
        "segmentCount", &WormMechParams::segmentCount,
        "segmentLength", &WormMechParams::segmentLength,
        "segmentRadius", &WormMechParams::segmentRadius,
        "taperProfile", &WormMechParams::taperProfile,
        "segmentShape", &WormMechParams::segmentShape,
        "jointFlexibility", &WormMechParams::jointFlexibility,
        "armorPlating", &WormMechParams::armorPlating,
        "platingDetailLevel", &WormMechParams::platingDetailLevel,
        "colorPrimary", &WormMechParams::colorPrimary,
        "colorSecondary", &WormMechParams::colorSecondary,
        "noiseDetail", &WormMechParams::noiseDetail,
        "textureScale", &WormMechParams::textureScale,
        "cockpitType", &WormMechParams::cockpitType,
        "cockpitSegmentIndex", &WormMechParams::cockpitSegmentIndex,
        "cockpitRadius", &WormMechParams::cockpitRadius,
        "cockpitOrientation", &WormMechParams::cockpitOrientation,
        "animationProfile", &WormMechParams::animationProfile,
        "aiProfile", &WormMechParams::aiProfile
    );

    lua.new_usertype<UIParams>("UIParams",
        sol::constructors<UIParams()>(),
        "iconSize", &UIParams::iconSize,
        "borderColor", &UIParams::borderColor,
        "backgroundShape", &UIParams::backgroundShape,
        "flashOnSelect", &UIParams::flashOnSelect
    );

    // Observable Wrapper for Live Params
    lua.new_usertype<MagiTech::Utils::Observable<WormMechParams>>("LiveMechParams",
        "value", sol::property(&MagiTech::Utils::Observable<WormMechParams>::get, &MagiTech::Utils::Observable<WormMechParams>::set),
        "onChanged", &MagiTech::Utils::Observable<WormMechParams>::onChanged
    );

    // Dynamic Mech Instance
    lua.new_usertype<DynamicWormMech>("DynamicWormMech",
        "params", &DynamicWormMech::params,
        "setSegmentCount", &DynamicWormMech::setSegmentCount
        // Other methods like updateLOD can be added here
    );

    // Asset Bundle (for return types)
    lua.new_usertype<MechAssetBundle>("MechAssetBundle",
        sol::no_constructor,
        "mesh", &MechAssetBundle::mesh,
        "texture", &MechAssetBundle::texture,
        "shader", &MechAssetBundle::shader,
        "skeleton", &MechAssetBundle::skeleton,
        "animation", &MechAssetBundle::animation,
        "cockpitMesh", &MechAssetBundle::cockpitMesh,
        "cockpitTexture", &MechAssetBundle::cockpitTexture,
        "exhaustFX", &MechAssetBundle::exhaustFX,
        "icon", &MechAssetBundle::icon
    );
    
    // --- API Functions ---
    auto factory = MainPlugin::instance().getWormMechFactory();

    // Legacy static generator
    lua.set_function("spawn_worm_mech",
        [&](const WormMechParams& m, const UIParams& u) {
            return factory->generateAsync(m, u).get();
        }
    );

    // Creates a new, managed, dynamic mech instance
    lua.set_function("create_dynamic_mech",
        [&](const WormMechParams& initialParams) {
            return factory->createDynamicMech(initialParams);
        }
    );

    // Retrieves an existing dynamic mech instance by its ID
    lua.set_function("get_dynamic_mech",
        [&](const std::string& id) {
            return factory->getDynamicMech(id);
        }
    );
}

void WormMechLuaBindings::poll_assets(sol::state& lua) {
    // This polling is now less critical as updates are handled via callbacks,
    // but can be kept for non-dynamic async operations or for debugging.
    for (auto it = pendingMechs.begin(); it != pendingMechs.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Legacy Worm Mech ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingMechs.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace WormMechs
} // namespace MagiTech
