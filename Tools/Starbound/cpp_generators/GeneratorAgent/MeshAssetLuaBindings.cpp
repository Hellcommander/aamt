#include "MeshAssetLuaBindings.hpp"
#include "MeshAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace MeshAssets {

static std::vector<std::pair<std::future<MeshAssetBundle>, std::string>> pendingAssets;

void MeshAssetLuaBindings::bind(sol::state& lua) {
    lua.new_enum("MeshType",
        "Primitive", MeshType::Primitive,
        "Terrain", MeshType::Terrain,
        "ImplicitSurface", MeshType::ImplicitSurface,
        "Sculpt", MeshType::Sculpt,
        "Custom", MeshType::Custom
    );

    lua.new_usertype<MeshParams>("MeshParams",
        sol::constructors<MeshParams()>(),
        "id", &MeshParams::id,
        "type", &MeshParams::type,
        "dimensions", &MeshParams::dimensions,
        "subdivisions", &MeshParams::subdivisions,
        "noiseFrequency", &MeshParams::noiseFrequency,
        "isoThreshold", &MeshParams::isoThreshold,
        "sculptHeightMap", &MeshParams::sculptHeightMap,
        "generateNormals", &MeshParams::generateNormals,
        "generateTangents", &MeshParams::generateTangents,
        "generateUVs", &MeshParams::generateUVs,
        "weldVertices", &MeshParams::weldVertices
    );

    lua.new_usertype<LODParams>("LODParams",
        sol::constructors<LODParams()>(),
        "baseMeshId", &LODParams::baseMeshId,
        "screenSizes", &LODParams::screenSizes,
        "targetRatios", &LODParams::targetRatios,
        "preserveBorders", &LODParams::preserveBorders,
        "preserveUVSeams", &LODParams::preserveUVSeams
    );

    lua.new_usertype<MaterialParams>("MaterialParams",
        sol::constructors<MaterialParams()>(),
        "id", &MaterialParams::id,
        "shaderType", &MaterialParams::shaderType,
        "albedo", &MaterialParams::albedo,
        "emissive", &MaterialParams::emissive,
        "metallic", &MaterialParams::metallic,
        "roughness", &MaterialParams::roughness,
        "normalMap", &MaterialParams::normalMap,
        "aoMap", &MaterialParams::aoMap
    );

    lua.new_usertype<MorphParams>("MorphParams",
        sol::constructors<MorphParams()>(),
        "baseMeshId", &MorphParams::baseMeshId,
        "targetMaps", &MorphParams::targetMaps,
        "enableCompression", &MorphParams::enableCompression,
        "tolerance", &MorphParams::tolerance
    );

    // Bind advanced params
    lua.new_usertype<ComputeMeshParams>("ComputeMeshParams", sol::constructors<ComputeMeshParams()>());
    lua.new_usertype<NaniteParams>("NaniteParams", sol::constructors<NaniteParams()>(), "trianglesPerCluster", &NaniteParams::trianglesPerCluster);
    lua.new_usertype<TessellationParams>("TessellationParams", sol::constructors<TessellationParams()>(), "maxTessellationFactor", &TessellationParams::maxTessellationFactor);
    lua.new_usertype<MLMeshParams>("MLMeshParams", sol::constructors<MLMeshParams()>(), "styleImagePath", &MLMeshParams::styleImagePath);
    lua.new_usertype<CollisionParams>("CollisionParams", sol::constructors<CollisionParams()>(), "generateConvexHull", &CollisionParams::generateConvexHull);
    
    lua.new_usertype<MeshAssetBundle>("MeshAssetBundle",
        sol::no_constructor,
        "mesh", &MeshAssetBundle::mesh,
        "lodMesh", &MeshAssetBundle::lodMesh,
        "material", &MeshAssetBundle::material,
        "uvLayout", &MeshAssetBundle::uvLayout,
        "morphTargets", &MeshAssetBundle::morphTargets,
        "computeMesh", &MeshAssetBundle::computeMesh,
        "naniteMesh", &MeshAssetBundle::naniteMesh,
        "tessellationData", &MeshAssetBundle::tessellationData,
        "mlMesh", &MeshAssetBundle::mlMesh,
        "collisionMesh", &MeshAssetBundle::collisionMesh
    );

    lua.set_function("spawn_mesh_asset",
        [&](const MeshParams& m, sol::optional<LODParams> l,
            sol::optional<MaterialParams> p, sol::optional<MorphParams> r,
            sol::optional<ComputeMeshParams> cmp, sol::optional<NaniteParams> np,
            sol::optional<TessellationParams> tp, sol::optional<MLMeshParams> mlp,
            sol::optional<CollisionParams> cp) {
            auto factory = MainPlugin::instance().getMeshAssetFactory();
            pendingAssets.emplace_back(factory->generateAsync(m, l, p, r, cmp, np, tp, mlp, cp), m.id);
        }
    );
}

void MeshAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Mesh asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace MeshAssets
} // namespace MagiTech
