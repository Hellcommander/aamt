#pragma once

/**
 * Asset store for the spell projectile generators.
 *
 * Geometry, shader sources, particle configs, light / audio / collider descriptions
 * stay addressable by the handle the generators return. Handles come from
 * MagiTech::nextAssetHandle, so they are unique across threads and asset families.
 */

#include "SpellProjectileTypes.hpp"
#include "core/rendering/GeneratedMesh.hpp"
#include <optional>
#include <string>

namespace MagiTech {
namespace SpellProjectiles {

struct SpellLightDesc {
    glm::vec4 color{1.0f};
    float intensity = 1.0f;
    LightFlicker flickerMode = LightFlicker::None;
    float flickerSpeed = 1.0f;
    float flickerAmplitude = 0.0f;   // fraction of intensity the flicker removes at its minimum
};

struct SpellAudioDesc {
    std::string sfxFile;
    float volume = 1.0f;
    bool loop = false;
};

enum class SpellColliderShape { Sphere, Capsule, Mesh };

struct SpellColliderDesc {
    SpellColliderShape shape = SpellColliderShape::Sphere;
    float radius = 0.5f;
    float length = 0.0f;           // capsule length along +Z
    MeshHandle mesh = 0;           // geometry used by mesh colliders
    bool triggerOnly = true;
};

MeshHandle storeSpellMesh(const MagiTech::Mesh& mesh);
std::optional<MagiTech::Mesh> getSpellMesh(MeshHandle handle);

void storeSpellShaderSource(ShaderHandle handle, std::string source);
std::optional<std::string> getSpellShaderSource(ShaderHandle handle);

ParticleHandle storeSpellParticleConfig(std::string configJson);
std::optional<std::string> getSpellParticleConfig(ParticleHandle handle);

LightHandle storeSpellLight(const SpellLightDesc& light);
std::optional<SpellLightDesc> getSpellLight(LightHandle handle);

AudioHandle storeSpellAudio(const SpellAudioDesc& audio);
std::optional<SpellAudioDesc> getSpellAudio(AudioHandle handle);

ColliderHandle storeSpellCollider(const SpellColliderDesc& collider);
std::optional<SpellColliderDesc> getSpellCollider(ColliderHandle handle);

/** Drops every stored spell asset (handles stay unique). */
void clearSpellAssets();

} // namespace SpellProjectiles
} // namespace MagiTech
