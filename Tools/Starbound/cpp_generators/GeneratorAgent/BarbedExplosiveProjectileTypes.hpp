#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace BarbedExplosiveProjectiles {

using MeshHandle = uint32_t;
using MaterialHandle = uint32_t;
using ParticleHandle = uint32_t;
using ExplosionHandle = uint32_t;

struct GeometryParams {
    float length = 2.0f;
    float radius = 0.2f;
    int numBarbs = 6;
    float barbLength = 0.5f;
    float barbThickness = 0.1f;
    float barbCurvature = 15.0f; // degrees
    uint64_t hashKey() const;
};

struct ExplosionParams {
    float radius = 3.0f;
    float impulseStrength = 100.0f;
    int particleCount = 100;
    float particleLifespan = 2.0f;
    float shardSize = 0.2f;
    float shardVelocity = 20.0f;
    uint64_t hashKey() const;
};

struct VisualParams {
    glm::vec3 baseColor = {0.5f, 0.5f, 0.5f};
    float dirtVariation = 0.2f;
    float emissiveIntensity = 1.0f;
    float specularHighlight = 0.8f;
    uint64_t hashKey() const;
};

struct BarbedExplosiveProjectileBundle {
    std::vector<MeshHandle> lods;
    MaterialHandle material = 0;
    ExplosionHandle explosionEffect = 0;
};

} // namespace BarbedExplosiveProjectiles
} // namespace MagiTech
