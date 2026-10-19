// Parameter hashing for the particle field generator family.
//
// The generator implementations (NoiseGen / ColorGen / LODGen / ShaderGen /
// FieldGen / SimGen) live in ParticleFieldAssetFactory.cpp; this file used to
// carry placeholder copies of them, which duplicated those definitions.
#include "ParticleFieldAssetFactory.hpp"

namespace MagiTech {
namespace ParticleFields {

namespace {

// Field-wise hashing (the structs contain strings and vectors, so they must not be
// hashed as raw memory).
template <typename T>
void hashPod(XXH64_state_t& s, const T& v) {
    XXH64_update(&s, &v, sizeof(T));
}

void hashString(XXH64_state_t& s, const std::string& v) {
    const uint64_t n = v.size();
    hashPod(s, n);
    XXH64_update(&s, v.data(), v.size());
}

template <typename T>
void hashVector(XXH64_state_t& s, const std::vector<T>& v) {
    const uint64_t n = v.size();
    hashPod(s, n);
    if (!v.empty()) XXH64_update(&s, v.data(), v.size() * sizeof(T));
}

} // namespace

uint64_t LODParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashVector(s, screenSizes);
    hashVector(s, densityScales);
    return XXH64_digest(&s);
}

uint64_t ParticleFieldParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashString(s, id);
    hashPod(s, boundsMin);
    hashPod(s, boundsMax);
    hashPod(s, density);
    hashPod(s, useVolume);
    hashPod(s, gpuDriven);
    hashPod(s, seed);
    hashPod(s, lod.hashKey());
    return XXH64_digest(&s);
}

uint64_t NoiseParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashString(s, noiseType);
    hashPod(s, octaves);
    hashPod(s, frequency);
    hashPod(s, lacunarity);
    hashPod(s, gain);
    hashPod(s, warp);
    return XXH64_digest(&s);
}

uint64_t ColorRampParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    const uint64_t n = stops.size();
    hashPod(s, n);
    for (const auto& [position, color] : stops) {
        hashPod(s, position);
        hashPod(s, color);
    }
    hashPod(s, cyclic);
    hashPod(s, resolution);
    return XXH64_digest(&s);
}

uint64_t ParticleParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashPod(s, sizeRange);
    hashPod(s, lifeTimeRange);
    hashPod(s, speedRange);
    hashPod(s, alignToCamera);
    return XXH64_digest(&s);
}

} // namespace ParticleFields
} // namespace MagiTech
