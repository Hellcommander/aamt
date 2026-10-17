#pragma once
#include <string>
#include <type_traits>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace DroneMinions {

namespace detail {
    // Field-wise hashing: hashing raw struct bytes would include padding and
    // std::string heap pointers, which makes cache keys non-deterministic.
    inline void hashField(XXH64_state_t& s, const std::string& v) noexcept {
        const uint64_t len = v.size();
        XXH64_update(&s, &len, sizeof(len));
        XXH64_update(&s, v.data(), v.size());
    }
    template <typename T>
    inline void hashField(XXH64_state_t& s, const T& v) noexcept {
        static_assert(std::is_trivially_copyable_v<T>, "hash members field by field");
        XXH64_update(&s, &v, sizeof(T));
    }
    template <typename... Ts>
    inline uint64_t hashFields(const Ts&... fields) noexcept {
        XXH64_state_t s;
        XXH64_reset(&s, 0);
        (hashField(s, fields), ...);
        return XXH64_digest(&s);
    }
} // namespace detail


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
        return detail::hashFields(id, bodyRadius, bodyHeight, bodyDetail, rotorCount, rotorRadius, rotorThickness, hoverHeight, bodyColorPrimary, bodyColorSecondary, ledColor, enableSensorArray, sensorCount, enableWeaponMount, weaponCount, weaponLength, enableThrusterFX, thrusterColor, thrusterLifetime, sparkCount, sparkColor, maxSpeed, acceleration, turnRateDeg, mass, detectionRange, attackRange, retreatThreshold, idlePatrolRadius, dynamicLOD, maxLODLevel);
    }
};

struct DroneMinionBundle {
    MeshHandle bodyMesh = 0;
    MeshHandle rotorMesh = 0;
    TextureHandle bodyTexture = 0;
    ShaderHandle bodyShader = 0;
    ParticleHandle thrusterFX = 0;
    ParticleHandle jointSparks = 0;
    PhysicsHandle flightPhysics = 0;
    AIHandle aiController = 0;
    TextureHandle icon = 0;
};

} // namespace DroneMinions
} // namespace MagiTech
