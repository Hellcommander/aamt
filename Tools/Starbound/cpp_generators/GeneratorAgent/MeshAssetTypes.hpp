#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace MeshAssets {

using MeshHandle = uint32_t;
using MaterialHandle = uint32_t;
using UVHandle = uint32_t;
using MorphHandle = uint32_t;
using ComputeMeshHandle = uint32_t;
using NaniteMeshHandle = uint32_t;
using TessellationHandle = uint32_t;
using MLMeshHandle = uint32_t;
using CollisionHandle = uint32_t;


enum class MeshType { Primitive, Terrain, ImplicitSurface, Sculpt, Custom };

struct MeshParams {
    std::string id = "default_mesh";
    MeshType type = MeshType::Primitive;
    glm::vec3 dimensions = {1.0f, 1.0f, 1.0f};
    int subdivisions = 16;
    float noiseFrequency = 1.0f;
    float isoThreshold = 0.0f;
    std::string sculptHeightMap;
    bool generateNormals = true;
    bool generateTangents = false;
    bool generateUVs = true;
    bool weldVertices = true;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MeshParams) - (2*sizeof(std::string)));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, sculptHeightMap.c_str(), sculptHeightMap.length());
        return XXH64_digest(&hash_state);
    }
};

struct LODParams {
    std::string baseMeshId;
    std::vector<float> screenSizes;
    std::vector<float> targetRatios;
    bool preserveBorders = true;
    bool preserveUVSeams = true;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(LODParams) - sizeof(std::string) - 2*sizeof(std::vector<float>));
        XXH64_update(&hash_state, baseMeshId.c_str(), baseMeshId.length());
        XXH64_update(&hash_state, screenSizes.data(), screenSizes.size() * sizeof(float));
        XXH64_update(&hash_state, targetRatios.data(), targetRatios.size() * sizeof(float));
        return XXH64_digest(&hash_state);
    }
};

struct MaterialParams {
    std::string id = "default_material";
    std::string shaderType = "PBR";
    glm::vec4 albedo = {0.8f, 0.8f, 0.8f, 1.0f};
    glm::vec4 emissive = {0.0f, 0.0f, 0.0f, 1.0f};
    float metallic = 0.1f;
    float roughness = 0.5f;
    std::string normalMap;
    std::string aoMap;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MaterialParams) - (4*sizeof(std::string)));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, shaderType.c_str(), shaderType.length());
        XXH64_update(&hash_state, normalMap.c_str(), normalMap.length());
        XXH64_update(&hash_state, aoMap.c_str(), aoMap.length());
        return XXH64_digest(&hash_state);
    }
};

struct MorphParams {
    std::string baseMeshId;
    std::vector<std::string> targetMaps;
    bool enableCompression = true;
    float tolerance = 0.01f;

     uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(MorphParams) - sizeof(std::string) - sizeof(std::vector<std::string>));
        XXH64_update(&hash_state, baseMeshId.c_str(), baseMeshId.length());
        for(const auto& map : targetMaps) {
            XXH64_update(&hash_state, map.c_str(), map.length());
        }
        return XXH64_digest(&hash_state);
    }
};

// --- Advanced Generation Params ---
struct ComputeMeshParams {
    // Parameters for GPU-based generation (e.g., SDF evaluation)
};

struct NaniteParams {
    // Parameters for cluster-based streaming
    int trianglesPerCluster = 128;
};

struct TessellationParams {
    // Parameters for on-the-fly tessellation
    float maxTessellationFactor = 16.0f;
};

struct MLMeshParams {
    // Parameters for style-guided synthesis
    std::string styleImagePath;
};

struct CollisionParams {
    // Parameters for automatic physics hull generation
    bool generateConvexHull = true;
};


struct MeshAssetBundle {
    MeshHandle mesh;
    MeshHandle lodMesh;
    MaterialHandle material;
    UVHandle uvLayout;
    MorphHandle morphTargets;
    // --- Advanced Asset Handles ---
    ComputeMeshHandle computeMesh;
    NaniteMeshHandle naniteMesh;
    TessellationHandle tessellationData;
    MLMeshHandle mlMesh;
    CollisionHandle collisionMesh;
};

} // namespace MeshAssets
} // namespace MagiTech
