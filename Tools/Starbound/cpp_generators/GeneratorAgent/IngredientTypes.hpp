#pragma once
#include <string>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace Ingredients {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using ParticleHandle = uint32_t;
using DecalHandle = uint32_t;
using PhysicsHandle = uint32_t;

enum class IngredientType { Herb, Crystal, Powder, Liquid, Bone, Runestone };

struct IngredientParams {
    std::string id = "moonpetal_herb_v1";

    // Common
    IngredientType type = IngredientType::Herb;
    float scaleMin = 0.8f;
    float scaleMax = 1.2f;
    float rotationVarianceDeg = 360.0f;

    // Herb
    int leafCount = 8;
    float leafLengthMin = 0.3f;
    float leafLengthMax = 0.5f;
    float stemThickness = 0.02f;

    // Crystal
    int facetCount = 12;
    float shardLengthMin = 0.2f;
    float shardLengthMax = 0.6f;
    glm::vec4 coreGlowColor = {0.3f, 0.8f, 1.0f, 1.0f};

    // Powder
    float moundRadius = 0.1f;
    float grainSize = 0.005f;
    glm::vec4 powderColor = {0.9f, 0.9f, 0.7f, 1.0f};

    // Liquid
    glm::vec4 liquidColor = {0.2f, 1.0f, 0.3f, 0.8f};
    float fillVolume = 0.75f;
    float viscosity = 0.5f;

    // Bone
    int boneCount = 5;
    float fragmentScaleMin = 0.1f;
    float fragmentScaleMax = 0.3f;

    // Runestone
    int runeCount = 3;
    float bevelDepth = 0.01f;
    glm::vec4 runeEmissiveColor = {1.0f, 0.5f, 0.0f, 1.0f};

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        // Hash all fields to ensure uniqueness
        XXH64_update(&hash_state, this, sizeof(IngredientParams));
        return XXH64_digest(&hash_state);
    }
};

struct IngredientAssetBundle {
    MeshHandle mesh;
    TextureHandle albedoMap;
    TextureHandle normalMap;
    TextureHandle detailMap;
    ShaderHandle materialShader;
    ParticleHandle ambientParticles;
    DecalHandle contextDecal;
    PhysicsHandle physicsBody;
};

} // namespace Ingredients
} // namespace MagiTech
