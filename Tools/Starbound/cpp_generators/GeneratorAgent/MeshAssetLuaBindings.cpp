#include "MeshAssetLuaBindings.hpp"
#include "MeshAssetFactory.hpp"
#include <memory>
#include <mutex>
#include <optional>
#include "core/Log.hpp"
#include <vector>

namespace MagiTech {
namespace MeshAssets {

static std::vector<std::pair<std::future<MeshAssetBundle>, std::string>> pendingAssets;

namespace {
std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}
std::shared_ptr<MeshAssetFactory>& factorySlot() {
    static std::shared_ptr<MeshAssetFactory> f;
    return f;
}
} // namespace

void MeshAssetLuaBindings::setFactory(std::shared_ptr<MeshAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<MeshAssetFactory> MeshAssetLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected (e.g. by MainPlugin): create a default one.
        slot = std::make_shared<MeshAssetFactory>();
        slot->initialize(128, 4);
    }
    return slot;
}

// sol::optional -> std::optional (the factory takes std::optional).
template <typename T>
static std::optional<T> toStd(const sol::optional<T>& v) {
    return v ? std::optional<T>(*v) : std::nullopt;
}

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
            auto factory = MeshAssetLuaBindings::factory();
            pendingAssets.emplace_back(factory->generateAsync(m, toStd(l), toStd(p), toStd(r), toStd(cmp),
                toStd(np), toStd(tp), toStd(mlp), toStd(cp)), m.id);
        }
    );
}

void MeshAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                it->first.get();
                lua["print"]("Mesh asset ready: " + it->second);
            } catch (const std::exception& e) {
                Log::error("MeshAssets", "Mesh asset {} failed: {}", it->second, e.what());
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace MeshAssets
} // namespace MagiTech
