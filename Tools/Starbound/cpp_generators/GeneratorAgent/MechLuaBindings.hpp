#pragma once

#include "MechTypes.hpp"
#include <sol/sol.hpp>
#include <memory>
#include <string>
#include <vector>

namespace MagiTech {
namespace Mechs {

class MechFactory;

// Lua integration for the hybrid C++/Lua mech pipeline.
//
// bind() registers the usertypes (MechParams, SegmentedMechParams, CockpitParams,
// UIParams, CentipedeMechParams, the bundles and instance states), the global
// `spawn_mech(params)` and the `mt_mech` table. Every mt_mech function that
// takes parameters accepts either the matching usertype or a plain Lua table
// with the same field names (vectors as {x, y, z}), e.g.
//
//   local future = mt_mech.generateSegmentedAsync({ id = "viper", segmentCount = 20 }, {}, {})
//   local bundle = future:get()
//
// Async generators return a future object with get() and ready().
class MechLuaBindings {
public:
    static void bind(sol::state_view lua);

    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates and initializes a default one.
    static void setFactory(std::shared_ptr<MechFactory> factory);
    static std::shared_ptr<MechFactory> factory();

    // Reports mechs queued with spawn_mech() whose generation has finished.
    static void poll_assets(sol::state_view lua);
};

// Entry point used by MainPlugin::bindAllToLua (equivalent to MechLuaBindings::bind).
void registerMechLuaBindings(lua_State* L);

// Conversions between Lua values (usertype or table) and the mech parameter types.
namespace LuaHelpers {
    MechParams toMechParams(const sol::object& value);
    SegmentedMechParams toSegmentedMechParams(const sol::object& value);
    CockpitParams toCockpitParams(const sol::object& value);
    UIParams toUIParams(const sol::object& value);
    CentipedeMechParams toCentipedeMechParams(const sol::object& value);
    ProceduralParams toProceduralParams(const sol::object& value);

    sol::table proceduralParamsToTable(sol::state_view lua, const ProceduralParams& params);
    sol::table performanceMetricsToTable(sol::state_view lua, const MechPerformanceMetrics& metrics);
    sol::table stringListToTable(sol::state_view lua, const std::vector<std::string>& values);

    // Named float properties of mech instances (used by get/setMechProperty)
    bool setMechProperty(MechInstanceState& instance, const std::string& property, float value);
    bool getMechProperty(const MechInstanceState& instance, const std::string& property, float& value);
    bool setSegmentedMechProperty(SegmentedMechInstanceState& instance, const std::string& property, float value);
    bool getSegmentedMechProperty(const SegmentedMechInstanceState& instance, const std::string& property, float& value);

    std::string describeMech(const MechInstanceState& instance);
    std::string describeSegmentedMech(const SegmentedMechInstanceState& instance);
}

} // namespace Mechs
} // namespace MagiTech
