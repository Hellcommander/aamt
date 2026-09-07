#include "GeometryAssetLuaBindings.hpp"
#include "GeometryAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace Geometry {

static std::vector<std::pair<std::future<GeometryBundle>, std::string>> pendingGeometry;

void GeometryAssetLuaBindings::bind(sol::state& lua) {
    lua.new_usertype<PrimitiveParams>("PrimitiveParams", sol::constructors<PrimitiveParams()>(),
        "type", &PrimitiveParams::type, "shape", &PrimitiveParams::shape,
        "dimensions", &PrimitiveParams::dimensions, "subdivisions", &PrimitiveParams::subdivisions);

    lua.new_usertype<ExtrusionParams>("ExtrusionParams", sol::constructors<ExtrusionParams()>(),
        "type", &ExtrusionParams::type, "profile", &ExtrusionParams::profile, "path", &ExtrusionParams::path,
        "segments", &ExtrusionParams::segments, "twist", &ExtrusionParams::twist, "capEnds", &ExtrusionParams::capEnds);

    lua.new_usertype<LSystemParams>("LSystemParams", sol::constructors<LSystemParams()>(),
        "type", &LSystemParams::type, "axiom", &LSystemParams::axiom, "rules", &LSystemParams::rules,
        "iterations", &LSystemParams::iterations, "angle", &LSystemParams::angle, "step", &LSystemParams::step);

    lua.new_usertype<SurfaceParams>("SurfaceParams", sol::constructors<SurfaceParams()>(),
        "type", &SurfaceParams::type, "func", &SurfaceParams::func, "uRange", &SurfaceParams::uRange,
        "vRange", &SurfaceParams::vRange, "resolution", &SurfaceParams::resolution);

    lua.new_usertype<BooleanParams>("BooleanParams", sol::constructors<BooleanParams()>(),
        "type", &BooleanParams::type, "op", &BooleanParams::op, "meshA", &BooleanParams::meshA, "meshB", &BooleanParams::meshB);

    lua.new_usertype<LODParams>("LODParams", sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes, "simplificationFactors", &LODParams::simplificationFactors);

    lua.new_usertype<GeometryBundle>("GeometryBundle", sol::no_constructor,
        "meshes", &GeometryBundle::meshes, "lod", &GeometryBundle::lod);

    lua.set_function("spawn_geometry_asset",
        [&](sol::table requests_table, const LODParams& lp) {
            std::vector<GeometryRequest> requests;
            for (const auto& kv : requests_table) {
                sol::table req = kv.second.as<sol::table>();
                GeometryType type = req["type"];
                if (type == GeometryType::Primitive) requests.push_back(req.as<PrimitiveParams>());
                else if (type == GeometryType::Extrusion) requests.push_back(req.as<ExtrusionParams>());
                else if (type == GeometryType::LSystem) requests.push_back(req.as<LSystemParams>());
                else if (type == GeometryType::Surface) requests.push_back(req.as<SurfaceParams>());
                else if (type == GeometryType::Boolean) requests.push_back(req.as<BooleanParams>());
            }
            auto factory = MainPlugin::instance().getGeometryAssetFactory();
            pendingGeometry.emplace_back(factory->generateAsync(requests, lp), "GeometryAsset");
        }
    );
}

void GeometryAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingGeometry.begin(); it != pendingGeometry.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Geometry asset ready: " + it->second);
            } catch (const std::exception& e) { /* log error */ }
            it = pendingGeometry.erase(it);
        } else { ++it; }
    }
}

} // namespace Geometry
} // namespace MagiTech
