#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Crossbows {

using MeshHandle = uint32_t;
using AnimationHandle = uint32_t;
using MaterialHandle = uint32_t;
using SimulationHandle = uint32_t;
using ColliderHandle = uint32_t;

struct MaterialSet {
    std::vector<std::pair<std::string, MaterialHandle>> materials;
};

// Crossbow (Weapon) Parameters
struct CrossbowParams {
    std::string id;
    float drawLength = 0.5f;
    float drawWeight = 300.0f;
    bool autoReload = true;
    float reloadTime = 1.2f;
    std::string stockMaterial;
    std::string limbMaterial;
    std::string stringMaterial;
    uint64_t hashKey() const;
};

// Bolt (Short Projectile) Parameters
struct BoltParams {
    std::string id;
    float length = 0.4f;
    float shaftRadius = 0.005f;
    bool useFletching = false;
    std::string fletchMaterial;
    float fletchLength = 0.05f;
    float tipMass = 0.02f;
    bool barbedTip = true;
    uint64_t hashKey() const;
};

// Arrow (Long Projectile) Parameters
struct ArrowParams {
    std::string id;
    float shaftLength = 1.1f;
    float shaftDiameter = 0.008f;
    int spineRating = 600;
    bool useFletching = true;
    std::string fletchStyle;
    float nockSize = 0.02f;
    float tipMass = 0.015f;
    uint64_t hashKey() const;
};

// Asset Bundles
struct CrossbowBundle {
    MeshHandle mesh = 0;
    MeshHandle string = 0;
    AnimationHandle reloadAnim = 0;
    MaterialSet materials;
};

struct ProjectileBundle {
    MeshHandle mesh = 0;
    MaterialHandle material = 0;
    MeshHandle vfxTrail = 0;
    SimulationHandle flightSim = 0;
    ColliderHandle collider = 0;
};

} // namespace Crossbows
} // namespace MagiTech
