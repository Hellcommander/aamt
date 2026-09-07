#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace DroneMinions {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using PhysicsHandle = uint32_t;
using AIHandle = uint32_t;

struct DroneMinionParams {
    // Identification
    std::string id = "default_drone";

    // Body Geometry
    float bodyRadius = 0.5f;
    float bodyHeight = 0.2f;
    int bodyDetail = 24;

    // Propulsion
    int rotorCount = 4;
    float rotorRadius = 0.4f;
    float rotorThickness = 0.05f;
    float hoverHeight = 1.5f;

    // Materials & Colors
    glm::vec4 bodyColorPrimary = {0.4f, 0.4f, 0.45f, 1.0f};
    glm::vec4 bodyColorSecondary = {0.2f, 0.2f, 0.2f, 1.0f};
    glm::vec4 ledColor = {1.0f, 0.5f, 0.0f, 1.0f};

    // Sensors & Weapons
    bool enableSensorArray = true;
    int sensorCount = 5;
    bool enableWeaponMount = true;
    int weaponCount = 2;
    float weaponLength = 0.3f;

    // VFX & Particles
    bool enableThrusterFX = true;
    glm::vec4 thrusterColor = {0.2f, 0.8f, 1.0f, 1.0f};
    float thrusterLifetime = 0.5f;
    int sparkCount = 10;
    glm::vec4 sparkColor = {1.0f, 1.0f, 0.8f, 1.0f};

    // Physics & Flight
    float maxSpeed = 10.0f;
    float acceleration = 8.0f;
    float turnRateDeg = 180.0f;
    float mass = 5.0f;

    // AI Behavior
    float detectionRange = 20.0f;
    float attackRange = 15.0f;
    float retreatThreshold = 0.25f;
    float idlePatrolRadius = 10.0f;

    // LOD & Performance
    bool dynamicLOD = true;
    int maxLODLevel = 3;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(DroneMinionParams));
        return XXH64_digest(&hash_state);
    }
};

struct DroneMinionBundle {
    MeshHandle bodyMesh;
    MeshHandle rotorMesh;
    TextureHandle bodyTexture;
    ShaderHandle bodyShader;
    ParticleHandle thrusterFX;
    ParticleHandle jointSparks;
    PhysicsHandle flightPhysics;
    AIHandle aiController;
    TextureHandle icon;
};

} // namespace DroneMinions
} // namespace MagiTech
