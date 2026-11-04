#include "CosmicProjectileGenerators.hpp"
#include "CosmicAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <FastNoiseLite.h>
#include <glm/gtc/constants.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <algorithm>
#include <cmath>
#include <sstream>

namespace MagiTech {
namespace Cosmic {

namespace {

constexpr int kTextureSize = 128;

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
}

void configureNoise(FastNoiseLite& noise, const CosmicProjectileParams& p) {
    noise.SetSeed(static_cast<int>(p.hashKey() & 0x7fffffff));
    noise.SetNoiseType(FastNoiseLite::NoiseType_OpenSimplex2);
    noise.SetFractalType(FastNoiseLite::FractalType_FBm);
    noise.SetFractalOctaves(3);
    noise.SetFrequency(1.0f);
}

const char* kCosmicVertexShader =
    "#version 450\n"
    "layout(location = 0) in vec3 aPosition;\n"
    "layout(location = 1) in vec3 aNormal;\n"
    "layout(location = 2) in vec2 aTexCoord;\n"
    "layout(location = 0) out vec3 vNormal;\n"
    "layout(location = 1) out vec2 vTexCoord;\n"
    "layout(location = 2) out vec3 vPosition;\n"
    "uniform mat4 uModelViewProjection;\n"
    "void main() {\n"
    "    vNormal = aNormal;\n"
    "    vTexCoord = aTexCoord;\n"
    "    vPosition = aPosition;\n"
    "    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);\n"
    "}\n";

} // namespace

MeshHandle MeshGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("CosmicProjectile", "Building cosmic projectile mesh for: {} (type: {}, length: {}, radius: {})",
              p.id, p.type, p.length, p.radius);

    // Elongated, noise-roughened body: a sphere stretched along +Y (flight axis) to `length`
    MagiTech::Mesh body = Primitives::createSphere(std::max(p.radius, 0.001f), 24);
    const float stretch = std::max(p.length / std::max(2.0f * p.radius, 0.001f), 1.0f);
    FastNoiseLite noise;
    configureNoise(noise, p);
    for (auto& v : body.vertices) {
        const glm::vec3 dir = glm::length(v.position) > 0.0f ? glm::normalize(v.position) : glm::vec3(0, 1, 0);
        const float n = noise.GetNoise(dir.x * p.noiseScale, dir.y * p.noiseScale, dir.z * p.noiseScale);
        v.position += dir * (n * p.noiseIntensity * p.radius);
        v.position.y *= stretch;
        // Leading tip is the hot core, the tail fades toward the edge colour
        const float t = std::clamp(0.5f + 0.5f * dir.y, 0.0f, 1.0f);
        v.color = glm::vec4(glm::mix(p.colorEdge, p.colorCore, t), 1.0f);
        // Normal after anisotropic stretch: inverse-transpose of diag(1, stretch, 1)
        const glm::vec3 nrm(v.normal.x, v.normal.y / stretch, v.normal.z);
        if (glm::length(nrm) > 0.0f) v.normal = glm::normalize(nrm);
    }

    // Fragmenting projectiles carry their shards as small satellites around the body
    for (int i = 0; i < p.fragmentation; ++i) {
        const float a = glm::two_pi<float>() * static_cast<float>(i) / static_cast<float>(std::max(p.fragmentation, 1));
        MagiTech::Mesh shard = Primitives::createSphere(p.radius * 0.25f, 6);
        const glm::vec3 offset(std::cos(a) * p.radius * 1.2f, -p.length * 0.25f, std::sin(a) * p.radius * 1.2f);
        for (auto& v : shard.vertices) {
            v.color = glm::vec4(p.colorEdge, 1.0f);
        }
        body.append(shard, glm::translate(glm::mat4(1.0f), offset));
    }

    return storeCosmicMesh(body);
}

TextureHandle TextureGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("CosmicProjectile", "Building cosmic projectile texture for: {}", p.id);

    // Radial core->edge gradient broken up by noise; alpha falls off toward the rim
    FastNoiseLite noise;
    configureNoise(noise, p);
    std::vector<uint8_t> rgba(static_cast<size_t>(kTextureSize) * kTextureSize * 4);
    for (int y = 0; y < kTextureSize; ++y) {
        for (int x = 0; x < kTextureSize; ++x) {
            const float u = (x + 0.5f) / kTextureSize;
            const float v = (y + 0.5f) / kTextureSize;
            const float r = std::clamp(glm::length(glm::vec2(u - 0.5f, v - 0.5f)) * 2.0f, 0.0f, 1.0f);
            const float n = 0.5f + 0.5f * noise.GetNoise(u * p.noiseScale * 4.0f, v * p.noiseScale * 4.0f);
            const float t = std::clamp(r + (n - 0.5f) * p.noiseIntensity, 0.0f, 1.0f);
            const glm::vec3 c = glm::mix(p.colorCore, p.colorEdge, t);
            const size_t i = (static_cast<size_t>(y) * kTextureSize + x) * 4;
            rgba[i + 0] = toByte(c.r);
            rgba[i + 1] = toByte(c.g);
            rgba[i + 2] = toByte(c.b);
            rgba[i + 3] = toByte((1.0f - r * r) * (0.75f + 0.25f * n));
        }
    }
    return storeCosmicTexture(kTextureSize, kTextureSize, std::move(rgba));
}

ShaderHandle ShaderGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("CosmicProjectile", "Building cosmic projectile shader for: {}", p.id);

    std::ostringstream fs;
    fs << "#version 450\n"
       << "layout(location = 0) in vec3 vNormal;\n"
       << "layout(location = 1) in vec2 vTexCoord;\n"
       << "layout(location = 2) in vec3 vPosition;\n"
       << "layout(location = 0) out vec4 fragColor;\n"
       << "uniform vec3 uColorCore;\n"
       << "uniform vec3 uColorEdge;\n"
       << "uniform float uNoiseScale;\n"
       << "uniform float uNoiseIntensity;\n"
       << "uniform float uFlickerRate;\n"
       << "uniform float uTime;\n"
       << "uniform sampler2D uCosmicTexture;\n"
       << "float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453); }\n"
       << "void main() {\n"
       << "    vec3 n = normalize(vNormal);\n"
       << "    float rim = 1.0 - abs(n.z);\n"
       << "    float sparkle = hash(floor(vPosition * uNoiseScale * 8.0) + floor(uTime * uFlickerRate));\n"
       << "    float flicker = 0.85 + 0.15 * sin(uTime * uFlickerRate * 6.2831);\n"
       << "    vec3 color = mix(uColorCore, uColorEdge, rim) * flicker;\n"
       << "    color += uColorCore * step(1.0 - 0.05 * uNoiseIntensity, sparkle);\n"
       << "    vec4 tex = texture(uCosmicTexture, vTexCoord);\n"
       << "    fragColor = vec4(color * tex.rgb, tex.a);\n"
       << "}\n";

    ShaderBuilder builder = ShaderBuilder::create("cosmic_projectile_" + p.id);
    builder.setVertexShader(kCosmicVertexShader);
    builder.setFragmentShader(fs.str());
    builder.addUniform("uColorCore", p.colorCore);
    builder.addUniform("uColorEdge", p.colorEdge);
    builder.addUniform("uNoiseScale", p.noiseScale);
    builder.addUniform("uNoiseIntensity", p.noiseIntensity);
    builder.addUniform("uFlickerRate", p.flickerRate);
    builder.enableAdditiveBlend();
    if (p.homingStrength > 0.0f) {
        builder.enableFeature("HOMING_GLOW");
    }

    const ShaderHandle handle = builder.compile();
    storeCosmicShaderSource(handle, CosmicShaderSource{kCosmicVertexShader, fs.str()});
    return handle;
}

EffectHandle EffectsGen<CosmicProjectileParams>::build(const CosmicProjectileParams& p) {
    Log::info("CosmicProjectile", "Building cosmic projectile effect for: {} (trail: {}, impact: {})",
              p.id, p.trailType, p.impactEffect);

    std::vector<std::string> configs;

    // Trail emitter
    if (p.trailType != "none" && p.trailLength > 0.0f) {
        ParticleType trailType = ParticleType::STREAK;
        glm::vec4 color(p.colorEdge, 0.8f);
        if (p.trailType == "sparkle") {
            trailType = ParticleType::EMBER;
            color = glm::vec4(p.colorCore, 1.0f);
        } else if (p.trailType == "smoke") {
            trailType = ParticleType::AREA_PUFF;
            color = glm::vec4(glm::mix(p.colorEdge, glm::vec3(0.3f), 0.6f), 0.5f);
        }
        ParticleEmitter trail = ParticleBuilder::createEmitter(trailType);
        trail.setCount(std::max(4, static_cast<int>(p.trailLength * 20.0f)))
            .setRate(40.0f)
            .setLifetime(std::max(p.trailLength * 0.25f, 0.1f))
            .setStartSize(p.radius)
            .setEndSize(0.0f)
            .setColor(color)
            .setAlpha(color.a, 0.0f)
            .setDirection(glm::vec3(0.0f, -1.0f, 0.0f))
            .setSpeed(0.0f)
            .setGlowColor(p.colorCore)
            .setGlowIntensity(1.0f)
            .setLayer(ParticleLayer::Middle);
        configs.push_back(trail.toOpenStarboundParticleJson());
    }

    // Impact emitter: shatter scales with fragmentation
    if (p.impactEffect != "none") {
        const bool shatter = p.impactEffect == "shatter";
        ParticleEmitter impact = ParticleBuilder::createEmitter(shatter ? ParticleType::SHARD_BURST : ParticleType::BURST);
        impact.setCount(std::max(8, p.fragmentation * 4))
            .setLifetime(0.4f)
            .setStartSize(p.radius * (shatter ? 0.4f : 0.6f))
            .setEndSize(0.0f)
            .setColor(glm::vec4(p.colorCore, 1.0f))
            .setAlpha(1.0f, 0.0f)
            .setShape(ParticleShape::SPHERE)
            .setRadius(p.radius)
            .setSpeed(4.0f + 2.0f * static_cast<float>(p.fragmentation))
            .setGlowColor(p.colorEdge)
            .setGlowIntensity(1.5f)
            .setLayer(ParticleLayer::Front);
        configs.push_back(impact.toOpenStarboundParticleJson());
    }

    return storeCosmicEffect(std::move(configs));
}

} // namespace Cosmic
} // namespace MagiTech
