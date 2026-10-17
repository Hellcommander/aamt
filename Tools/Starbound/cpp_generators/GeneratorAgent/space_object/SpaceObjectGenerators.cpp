#include "SpaceObjectGenerators.hpp"
#include "CosmicAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <FastNoiseLite.h>
#include <glm/gtc/constants.hpp>
#include <algorithm>
#include <cmath>
#include <random>
#include <sstream>

namespace MagiTech {
namespace Cosmic {

namespace {

constexpr int kTextureSize = 256;

enum class SpaceObjectKind { Planet, Moon, Asteroid, Star, Nebula };

SpaceObjectKind kindOf(const SpaceObjectParams& p) {
    std::string t = p.objectType;
    std::transform(t.begin(), t.end(), t.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (t == "moon") return SpaceObjectKind::Moon;
    if (t == "asteroid") return SpaceObjectKind::Asteroid;
    if (t == "star" || t == "sun") return SpaceObjectKind::Star;
    if (t == "nebula") return SpaceObjectKind::Nebula;
    return SpaceObjectKind::Planet;
}

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
}

int seedOf(const SpaceObjectParams& p) {
    return static_cast<int>(p.hashKey() & 0x7fffffff);
}

/** Samples the palette as a piecewise-linear ramp over t in [0,1]. */
glm::vec3 samplePalette(const std::vector<glm::vec3>& palette, float t) {
    if (palette.empty()) {
        return glm::vec3(0.25f + 0.6f * std::clamp(t, 0.0f, 1.0f));
    }
    if (palette.size() == 1) {
        return palette.front();
    }
    const float x = std::clamp(t, 0.0f, 1.0f) * static_cast<float>(palette.size() - 1);
    const size_t i = std::min(static_cast<size_t>(x), palette.size() - 2);
    return glm::mix(palette[i], palette[i + 1], x - static_cast<float>(i));
}

struct Crater {
    glm::vec3 center;   // unit direction
    float radius;       // angular size (chord length on the unit sphere)
    float depth;
};

std::vector<Crater> makeCraters(const SpaceObjectParams& p) {
    std::vector<Crater> craters;
    const int count = static_cast<int>(std::clamp(p.craterDensity, 0.0f, 1.0f) * 60.0f);
    std::mt19937 rng(static_cast<uint32_t>(seedOf(p)));
    std::normal_distribution<float> gauss(0.0f, 1.0f);
    std::uniform_real_distribution<float> size(0.05f, 0.3f);
    for (int i = 0; i < count; ++i) {
        glm::vec3 d(gauss(rng), gauss(rng), gauss(rng));
        if (glm::length(d) < 1e-4f) continue;
        const float r = size(rng);
        craters.push_back({glm::normalize(d), r, r * 0.35f});
    }
    return craters;
}

/** Radial height (fraction of radius) of a rocky body at unit direction `dir`. */
float surfaceHeight(const SpaceObjectParams& p, const FastNoiseLite& noise, const std::vector<Crater>& craters, const glm::vec3& dir) {
    float h = noise.GetNoise(dir.x * 2.0f, dir.y * 2.0f, dir.z * 2.0f) * p.surfaceRoughness * 0.2f;
    for (const auto& c : craters) {
        const float d = glm::length(dir - c.center) / c.radius;
        if (d < 1.0f) {
            // Bowl with a slightly raised rim
            h -= c.depth * (1.0f - d * d) * 0.2f;
        } else if (d < 1.3f) {
            h += c.depth * 0.05f * (1.3f - d) / 0.3f;
        }
    }
    return h;
}

void configureSurfaceNoise(FastNoiseLite& noise, const SpaceObjectParams& p, SpaceObjectKind kind) {
    noise.SetSeed(seedOf(p));
    noise.SetNoiseType(FastNoiseLite::NoiseType_OpenSimplex2);
    noise.SetFractalType(kind == SpaceObjectKind::Asteroid ? FastNoiseLite::FractalType_Ridged : FastNoiseLite::FractalType_FBm);
    noise.SetFractalOctaves(2 + std::clamp(p.detailLevel, 0, 5));
    noise.SetFrequency(1.0f);
}

MagiTech::Mesh buildRing(const SpaceObjectParams& p) {
    MagiTech::Mesh ring;
    const int segments = std::max(8, p.ringDetail);
    const float inner = p.radius * 1.4f;
    const float outer = p.radius * 2.3f;
    for (int i = 0; i <= segments; ++i) {
        const float u = static_cast<float>(i) / static_cast<float>(segments);
        const float a = u * glm::two_pi<float>();
        const glm::vec3 dir(std::cos(a), 0.0f, std::sin(a));
        for (int side = 0; side < 2; ++side) {
            MagiTech::Mesh::Vertex v;
            v.position = dir * (side == 0 ? inner : outer);
            v.normal = {0.0f, 1.0f, 0.0f};
            v.uv = {static_cast<float>(side), u};
            v.color = glm::vec4(samplePalette(p.colorPalette, side == 0 ? 0.8f : 0.4f), side == 0 ? 0.9f : 0.3f);
            ring.vertices.push_back(v);
        }
    }
    for (int i = 0; i < segments; ++i) {
        const uint32_t b = static_cast<uint32_t>(i * 2);
        // Double-sided so the ring is visible from above and below
        ring.indices.insert(ring.indices.end(), {b, b + 2, b + 1, b + 1, b + 2, b + 3,
                                                 b, b + 1, b + 2, b + 1, b + 3, b + 2});
    }
    return ring;
}

/** Nebula volume: stacked, rotated quads (volumetric) or a single camera-facing quad. */
MagiTech::Mesh buildNebula(const SpaceObjectParams& p) {
    MagiTech::Mesh mesh;
    const int slices = p.nebulaVolumetrics ? 4 + 2 * std::clamp(p.detailLevel, 0, 5) : 1;
    for (int s = 0; s < slices; ++s) {
        const float a = glm::pi<float>() * static_cast<float>(s) / static_cast<float>(slices);
        const glm::vec3 axisU(std::cos(a), 0.0f, std::sin(a));
        const glm::vec3 axisV(0.0f, 1.0f, 0.0f);
        const glm::vec3 normal = glm::normalize(glm::cross(axisU, axisV));
        const uint32_t base = static_cast<uint32_t>(mesh.vertices.size());
        const float alpha = 1.0f / static_cast<float>(slices);
        for (int j = 0; j < 4; ++j) {
            const float su = (j == 1 || j == 2) ? 1.0f : -1.0f;
            const float sv = (j >= 2) ? 1.0f : -1.0f;
            MagiTech::Mesh::Vertex v;
            v.position = (axisU * su + axisV * sv) * p.radius;
            v.normal = normal;
            v.uv = {su * 0.5f + 0.5f, sv * 0.5f + 0.5f};
            v.color = glm::vec4(1.0f, 1.0f, 1.0f, alpha);
            mesh.vertices.push_back(v);
        }
        mesh.indices.insert(mesh.indices.end(), {base, base + 1, base + 2, base, base + 2, base + 3,
                                                 base, base + 2, base + 1, base, base + 3, base + 2});
    }
    return mesh;
}

const char* kSpaceVertexShader =
    "#version 450\n"
    "layout(location = 0) in vec3 aPosition;\n"
    "layout(location = 1) in vec3 aNormal;\n"
    "layout(location = 2) in vec2 aTexCoord;\n"
    "layout(location = 3) in vec4 aColor;\n"
    "layout(location = 0) out vec3 vNormal;\n"
    "layout(location = 1) out vec2 vTexCoord;\n"
    "layout(location = 2) out vec4 vColor;\n"
    "uniform mat4 uModelViewProjection;\n"
    "void main() {\n"
    "    vNormal = aNormal;\n"
    "    vTexCoord = aTexCoord;\n"
    "    vColor = aColor;\n"
    "    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);\n"
    "}\n";

} // namespace

MeshHandle MeshGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    const SpaceObjectKind kind = kindOf(p);
    Log::info("SpaceObject", "Building space object mesh for: {} (type: {}, radius: {}, detail: {})",
              p.id, p.objectType, p.radius, p.detailLevel);

    if (kind == SpaceObjectKind::Nebula) {
        return storeCosmicMesh(buildNebula(p));
    }

    const int segments = 8 << std::clamp(p.detailLevel, 0, 4);   // 8 .. 128
    MagiTech::Mesh body = Primitives::createSphere(std::max(p.radius, 0.001f), segments);

    if (kind != SpaceObjectKind::Star) {
        // Rocky bodies: noise relief plus craters, displaced along the radial direction
        FastNoiseLite noise;
        configureSurfaceNoise(noise, p, kind);
        const std::vector<Crater> craters = makeCraters(p);
        const float squash = kind == SpaceObjectKind::Asteroid ? 0.7f : 1.0f;   // asteroids are lumpy and flattened
        for (auto& v : body.vertices) {
            const glm::vec3 dir = glm::length(v.position) > 0.0f ? glm::normalize(v.position) : glm::vec3(0, 1, 0);
            const float h = surfaceHeight(p, noise, craters, dir) * (kind == SpaceObjectKind::Asteroid ? 2.5f : 1.0f);
            v.position = dir * p.radius * (1.0f + h);
            v.position.y *= squash;
            v.color = glm::vec4(samplePalette(p.colorPalette, 0.5f + h * 2.5f), 1.0f);
        }
        // Recompute smooth normals from the displaced faces
        for (auto& v : body.vertices) v.normal = glm::vec3(0.0f);
        for (size_t i = 0; i + 2 < body.indices.size(); i += 3) {
            auto& a = body.vertices[body.indices[i]];
            auto& b = body.vertices[body.indices[i + 1]];
            auto& c = body.vertices[body.indices[i + 2]];
            const glm::vec3 fn = glm::cross(b.position - a.position, c.position - a.position);
            a.normal += fn;
            b.normal += fn;
            c.normal += fn;
        }
        for (auto& v : body.vertices) {
            v.normal = glm::length(v.normal) > 0.0f ? glm::normalize(v.normal)
                                                     : (glm::length(v.position) > 0.0f ? glm::normalize(v.position) : glm::vec3(0, 1, 0));
        }
    } else {
        for (auto& v : body.vertices) {
            v.color = glm::vec4(samplePalette(p.colorPalette, 1.0f) * std::max(p.starBrightness, 0.0f), 1.0f);
        }
    }

    if (p.ringSystem && kind != SpaceObjectKind::Star) {
        body.append(buildRing(p));
    }

    return storeCosmicMesh(body);
}

TextureHandle TextureGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    const SpaceObjectKind kind = kindOf(p);
    Log::info("SpaceObject", "Building space object texture for: {} (type: {})", p.id, p.objectType);

    // Equirectangular surface map (u = longitude, v = latitude) coloured through the palette
    FastNoiseLite noise;
    configureSurfaceNoise(noise, p, kind);
    const std::vector<Crater> craters = makeCraters(p);

    std::vector<uint8_t> rgba(static_cast<size_t>(kTextureSize) * kTextureSize * 4);
    for (int y = 0; y < kTextureSize; ++y) {
        const float lat = ((y + 0.5f) / kTextureSize) * glm::pi<float>();
        for (int x = 0; x < kTextureSize; ++x) {
            const float lon = ((x + 0.5f) / kTextureSize) * glm::two_pi<float>();
            const glm::vec3 dir(std::sin(lat) * std::cos(lon), std::cos(lat), std::sin(lat) * std::sin(lon));
            glm::vec3 color;
            float alpha = 1.0f;
            switch (kind) {
                case SpaceObjectKind::Star: {
                    // Granulated photosphere: bright cells, darker lanes
                    const float g = 0.5f + 0.5f * noise.GetNoise(dir.x * 8.0f, dir.y * 8.0f, dir.z * 8.0f);
                    color = samplePalette(p.colorPalette, 0.6f + 0.4f * g) * std::max(p.starBrightness, 0.0f);
                    break;
                }
                case SpaceObjectKind::Nebula: {
                    // Wispy gas: domain-warped noise drives both colour and opacity
                    float wx = dir.x * 3.0f, wy = dir.y * 3.0f, wz = dir.z * 3.0f;
                    noise.DomainWarp(wx, wy, wz);
                    const float d = 0.5f + 0.5f * noise.GetNoise(wx, wy, wz);
                    color = samplePalette(p.colorPalette, d);
                    alpha = std::clamp((d - 0.35f) * 2.0f, 0.0f, 1.0f);
                    break;
                }
                default: {
                    const float h = surfaceHeight(p, noise, craters, dir);
                    color = samplePalette(p.colorPalette, 0.5f + h * 2.5f);
                    break;
                }
            }
            const size_t i = (static_cast<size_t>(y) * kTextureSize + x) * 4;
            rgba[i + 0] = toByte(color.r);
            rgba[i + 1] = toByte(color.g);
            rgba[i + 2] = toByte(color.b);
            rgba[i + 3] = toByte(alpha);
        }
    }
    return storeCosmicTexture(kTextureSize, kTextureSize, std::move(rgba));
}

ShaderHandle ShaderGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    const SpaceObjectKind kind = kindOf(p);
    Log::info("SpaceObject", "Building space object shader for: {} (type: {})", p.id, p.objectType);

    std::ostringstream fs;
    fs << "#version 450\n"
       << "layout(location = 0) in vec3 vNormal;\n"
       << "layout(location = 1) in vec2 vTexCoord;\n"
       << "layout(location = 2) in vec4 vColor;\n"
       << "layout(location = 0) out vec4 fragColor;\n"
       << "uniform sampler2D uSurface;\n"
       << "uniform vec3 uLightDir;\n"
       << "uniform float uStarBrightness;\n"
       << "uniform float uTime;\n"
       << "void main() {\n"
       << "    vec4 surface = texture(uSurface, vTexCoord) * vColor;\n";
    switch (kind) {
        case SpaceObjectKind::Star:
            fs << "    // Emissive with limb darkening\n"
               << "    float limb = pow(max(dot(normalize(vNormal), vec3(0.0, 0.0, 1.0)), 0.0), 0.4);\n"
               << "    fragColor = vec4(surface.rgb * uStarBrightness * (0.6 + 0.4 * limb), 1.0);\n";
            break;
        case SpaceObjectKind::Nebula:
            fs << "    // Additive gas, gently pulsing\n"
               << "    float pulse = 0.9 + 0.1 * sin(uTime * 0.5 + vTexCoord.x * 6.2831);\n"
               << "    fragColor = vec4(surface.rgb * pulse, surface.a);\n";
            break;
        default:
            fs << "    // Lambert lighting with a soft terminator and ambient floor\n"
               << "    float ndl = dot(normalize(vNormal), normalize(uLightDir));\n"
               << "    float light = 0.08 + 0.92 * smoothstep(-0.1, 0.3, ndl);\n"
               << "    fragColor = vec4(surface.rgb * light, surface.a);\n";
            break;
    }
    fs << "}\n";

    ShaderBuilder builder = ShaderBuilder::create("space_object_" + p.id);
    builder.setVertexShader(kSpaceVertexShader);
    builder.setFragmentShader(fs.str());
    builder.addUniform("uLightDir", glm::vec3(0.5f, 0.6f, 0.6f));
    builder.addUniform("uStarBrightness", p.starBrightness);
    if (kind == SpaceObjectKind::Star || kind == SpaceObjectKind::Nebula) {
        builder.enableAdditiveBlend();
    } else {
        builder.enableNormalBlend();
    }
    if (p.ringSystem) {
        builder.enableFeature("RING_SYSTEM");
    }
    if (p.nebulaVolumetrics) {
        builder.enableFeature("VOLUMETRIC");
    }

    const ShaderHandle handle = builder.compile();
    storeCosmicShaderSource(handle, CosmicShaderSource{kSpaceVertexShader, fs.str()});
    return handle;
}

EffectHandle EffectsGen<SpaceObjectParams>::build(const SpaceObjectParams& p) {
    const SpaceObjectKind kind = kindOf(p);
    Log::info("SpaceObject", "Building space object effect for: {} (stars: {}, brightness: {})",
              p.id, p.starCount, p.starBrightness);

    std::vector<std::string> configs;
    const glm::vec3 accent = samplePalette(p.colorPalette, 1.0f);

    if (p.starCount > 0) {
        // Background star field around the object
        ParticleEmitter stars = ParticleBuilder::createEmitter(ParticleType::EMBER);
        stars.setCount(p.starCount)
            .setRate(0.0f)
            .setLifetime(3600.0f)
            .setStartSize(0.02f * std::max(p.starBrightness, 0.1f))
            .setEndSize(0.02f * std::max(p.starBrightness, 0.1f))
            .setColor(glm::vec4(1.0f, 1.0f, 1.0f, std::clamp(p.starBrightness, 0.0f, 1.0f)))
            .setAlpha(std::clamp(p.starBrightness, 0.0f, 1.0f), std::clamp(p.starBrightness, 0.0f, 1.0f))
            .setShape(ParticleShape::SPHERE)
            .setRadius(p.radius * 8.0f)
            .setSpeed(0.0f)
            .setGlowIntensity(p.starBrightness)
            .setLayer(ParticleLayer::Back);
        configs.push_back(stars.toOpenStarboundParticleJson());
    }

    if (kind == SpaceObjectKind::Star) {
        // Corona flares
        ParticleEmitter corona = ParticleBuilder::createEmitter(ParticleType::CONTINUOUS);
        corona.setCount(32)
            .setRate(16.0f)
            .setLifetime(2.0f)
            .setStartSize(p.radius * 0.4f)
            .setEndSize(p.radius * 0.1f)
            .setColor(glm::vec4(accent * std::max(p.starBrightness, 0.0f), 0.8f))
            .setAlpha(0.8f, 0.0f)
            .setShape(ParticleShape::SPHERE)
            .setRadius(p.radius)
            .setSpeed(p.radius * 0.3f)
            .setGlowColor(accent)
            .setGlowIntensity(2.0f * p.starBrightness)
            .setLayer(ParticleLayer::Front);
        configs.push_back(corona.toOpenStarboundParticleJson());
    } else if (kind == SpaceObjectKind::Nebula) {
        // Drifting dust motes
        ParticleEmitter dust = ParticleBuilder::createEmitter(ParticleType::AREA_PUFF);
        dust.setCount(p.nebulaVolumetrics ? 64 : 24)
            .setRate(4.0f)
            .setLifetime(12.0f)
            .setStartSize(p.radius * 0.3f)
            .setEndSize(p.radius * 0.6f)
            .setColor(glm::vec4(accent, 0.25f))
            .setAlpha(0.25f, 0.0f)
            .setShape(ParticleShape::SPHERE)
            .setRadius(p.radius)
            .setSpeed(0.05f)
            .setLayer(ParticleLayer::Back);
        configs.push_back(dust.toOpenStarboundParticleJson());
    } else if (p.ringSystem) {
        // Glinting ring debris
        ParticleEmitter debris = ParticleBuilder::createEmitter(ParticleType::EMBER);
        debris.setCount(std::max(16, p.ringDetail / 2))
            .setRate(0.0f)
            .setLifetime(3600.0f)
            .setStartSize(0.01f * p.radius)
            .setEndSize(0.01f * p.radius)
            .setColor(glm::vec4(samplePalette(p.colorPalette, 0.8f), 0.8f))
            .setAlpha(0.8f, 0.8f)
            .setShape(ParticleShape::CYLINDER)
            .setRadius(p.radius * 1.85f)
            .setHeight(0.01f * p.radius)
            .setSpeed(0.0f)
            .setLayer(ParticleLayer::Middle);
        configs.push_back(debris.toOpenStarboundParticleJson());
    }

    return storeCosmicEffect(std::move(configs));
}

} // namespace Cosmic
} // namespace MagiTech
