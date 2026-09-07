#pragma once
#include <string>
#include <vector>
#include <optional>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace CentipedeMechs {

using MeshHandle = uint32_t;
using LegHandle = uint32_t;
using CockpitHandle = uint32_t;
using WeaponHandle = uint32_t;
using SensorHandle = uint32_t;
using MaterialSet = uint32_t;
using VFXBundle = uint32_t;
using AudioBundle = uint32_t;
using ColliderHandle = uint32_t;

// High-Level Mech Parameters
struct MechParams {
    std::string id;
    int segmentCount = 8;
    float segmentLength = 1.2f;
    float segmentRadius = 0.3f;
    glm::vec4 baseColor = {0.5f, 0.5f, 0.5f, 1.0f};
    bool seamlessJoints = true;
    uint64_t hashKey() const;
};

// Leg Parameters (per segment)
struct LegParams {
    int legsPerSegment = 2;
    float upperLegLength = 0.8f;
    float lowerLegLength = 0.6f;
    float jointRadius = 0.1f;
    bool armorPlates = true;
    std::string footType;
    uint64_t hashKey() const;
};

// Cockpit Parameters
struct CockpitParams {
    bool hasCockpit = true;
    glm::vec3 cockpitPosition = {0, 0, 0};
    float width = 1.0f, height = 0.8f, depth = 1.2f;
    bool enableDisplays = true;
    int displayCount = 4;
    std::string seatMaterial;
    std::string controlStyle;
    uint64_t hashKey() const;
};

// Weapon & Sensor Parameters
struct HardpointParams {
    int missileTubes = 2;
    int autocannonSlots = 1;
    bool enableTurret = true;
    bool enableRadarArray = true;
    float radarRange = 300.0f;
    uint64_t hashKey() const;
};

// Asset Bundle
struct MechBundle {
    std::vector<MeshHandle> segments;
    std::vector<MeshHandle> joints;
    std::vector<LegHandle> legs;
    CockpitHandle cockpit = 0;
    WeaponHandle weapons = 0;
    SensorHandle sensorArray = 0;
    MaterialSet materials = 0;
    VFXBundle vfx = 0;
    AudioBundle audio = 0;
    ColliderHandle collider = 0;
};

} // namespace CentipedeMechs
} // namespace MagiTech
