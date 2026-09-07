#pragma once
#include <string>
#include <vector>
#include <utility>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace ParticleFields {

using ParticleSystemHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;

struct LODParams {
    std::vector<float> screenSizes;
    std::vector<float> densityScales;
    uint64_t hashKey() const;
};

struct ParticleFieldParams {
    std::string id;
    glm::vec3 boundsMin = {-50, -50, -50};
    glm::vec3 boundsMax = {50, 50, 50};
    float density = 0.1f;
    bool useVolume = true;
    bool gpuDriven = true;
    float seed = 1234.0f;
    LODParams lod;
    uint64_t hashKey() const;
};

struct NoiseParams {
    std::string noiseType = "FBM";
    int octaves = 5;
    float frequency = 0.02f;
    float lacunarity = 2.0f;
    float gain = 0.5f;
    glm::vec3 warp = {0.1f, 0.2f, 0.3f};
    uint64_t hashKey() const;
};

struct ColorRampParams {
    std::vector<std::pair<float, glm::vec4>> stops;
    bool cyclic = false;
    int resolution = 256;
    uint64_t hashKey() const;
};

struct ParticleParams {
    glm::vec2 sizeRange = {2, 5};
    glm::vec2 lifeTimeRange = {3, 8};
    glm::vec2 speedRange = {1, 3};
    bool alignToCamera = true;
    uint64_t hashKey() const;
};

struct LODData {
    std::vector<float> thresholds;
    std::vector<float> scales;
};

struct ParticleFieldBundle {
    ParticleSystemHandle particles = 0;
    TextureHandle noiseVolume = 0;
    TextureHandle colorRampTex = 0;
    ShaderHandle fieldShader = 0;
    LODData lodData;
};

} // namespace ParticleFields
} // namespace MagiTech
