#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace GrappleHooks {

using MeshHandle = uint32_t;
using MaterialHandle = uint32_t;
using PhysicsAsset = uint32_t;
using ShaderHandle = uint32_t;

struct HookParams {
    std::string id;
    glm::vec3 tipPosition = {0,0,0};
    float hookRadius = 0.5f;
    float hookThickness = 0.1f;
    int segmentCount = 32;
    uint64_t hashKey() const;
};

struct ChainParams {
    int linkCount = 20;
    float linkLength = 0.3f;
    float linkThickness = 0.05f;
    glm::vec3 linkScale = {1,1,1};
    float twistAngle = 3.14159f / 18.0f; // 10 degrees
    uint64_t hashKey() const;
};

struct MaterialParams {
    std::string baseColorMap;
    std::string normalMap;
    std::string metallicRoughnessMap;
    glm::vec4 colorTint = {1,1,1,1};
    uint64_t hashKey() const;
};

struct PhysicsParams {
    bool enablePhysics = true;
    float linkMass = 0.2f;
    float jointStiffness = 150.0f;
    float jointDamping = 5.0f;
    glm::vec3 gravityOverride = {0, -9.8f, 0};
    uint64_t hashKey() const;
};

struct LODParams {
    std::vector<int> meshLODs;
    std::vector<float> displayRanges;
    uint64_t hashKey() const;
};

struct LODData {
    std::vector<float> thresholds;
    std::vector<MeshHandle> hookLODs;
    std::vector<std::vector<MeshHandle>> chainLODs;
};

struct GrappleBundle {
    MeshHandle hookMesh = 0;
    std::vector<MeshHandle> chainMeshes;
    MaterialHandle material = 0;
    PhysicsAsset physics = 0;
    LODData lodData;
    ShaderHandle shader = 0;
};

} // namespace GrappleHooks
} // namespace MagiTech
