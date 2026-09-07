#pragma once
#include <string>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Cockpits {

using MeshHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using AnimationHandle = uint32_t;
using DecalHandle = uint32_t;
using PhysicsHandle = uint32_t;

struct CockpitParams {
    std::string id = "fighter_cockpit_v1";

    // Seat & Interior
    float seatWidth = 0.8f;
    float seatDepth = 0.6f;
    float seatHeight = 0.5f;
    glm::vec4 seatFabricColor = {0.2f, 0.2f, 0.25f, 1.0f};
    bool headrestEnabled = true;

    // Canopy & Glass
    float canopyRadius = 1.0f;
    float canopyHeight = 0.7f;
    float glassThickness = 0.05f;
    glm::vec4 glassTint = {0.5f, 0.8f, 1.0f, 0.2f};
    float reflectivity = 0.4f;

    // Console & Controls
    int displayCount = 3;
    glm::vec2 displayResolution = {256, 128};
    float stickOffsetX = 0.3f;
    float stickOffsetY = -0.2f;
    bool throttleLever = true;
    bool pedalControls = true;

    // Instrumentation
    int gaugeCount = 5;
    float gaugeRadius = 0.05f;
    glm::vec4 gaugeNeedleColor = {1.0f, 0.3f, 0.1f, 1.0f};
    bool holographicHUD = true;

    // Ambient FX
    bool cockpitLight = true;
    glm::vec4 lightColor = {0.8f, 0.9f, 1.0f, 1.0f};
    float lightIntensity = 0.8f;

    // Interaction
    bool canopyAnimEnabled = true;
    float canopyOpenAngleDeg = 80.0f;
    float canopyOpenDuration = 1.5f;

    // Integration
    glm::vec3 mountOffset = {0.0f, 0.2f, 0.5f};
    glm::quat mountRotation = glm::quat(1.0f, 0.0f, 0.0f, 0.0f);

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(CockpitParams));
        return XXH64_digest(&hash_state);
    }
};

struct CockpitAssetBundle {
    MeshHandle seatMesh;
    MeshHandle canopyMesh;
    MeshHandle consoleMesh;
    MeshHandle gaugeMesh;
    MeshHandle hudMesh;
    ShaderHandle glassShader;
    ShaderHandle screenShader;
    AnimationHandle canopyAnimation;
    PhysicsHandle collisionVolume;
    DecalHandle uiDecals;
};

} // namespace Cockpits
} // namespace MagiTech
