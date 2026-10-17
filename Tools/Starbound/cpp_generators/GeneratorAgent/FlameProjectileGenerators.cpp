#include "FlameProjectileFactory.hpp"
#include "FlameProjectileTypes.hpp"
#include "FlameProjectileAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/Primitives.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <FastNoiseLite.h>
#include <glm/gtc/constants.hpp>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace MagiTech {
namespace FlameProjectiles {

// Global factory instance
FlameProjectileFactory g_flameFactory;

using ParamUtils::flameTypeToString;
using ParamUtils::flameShapeToString;
using ParamUtils::blendModeToString;
using ParamUtils::noiseTypeToString;
using ParamUtils::trailTypeToString;

namespace {

constexpr int kTextureSize = 128;
constexpr int kRadialSegments = 24;

// Header-only FastNoiseLite configured for the flame's noise type.
void configureNoise(FastNoiseLite& noise, NoiseType type, float frequency) {
    noise.SetFrequency(frequency);
    switch (type) {
        case NoiseType::PERLIN:
            noise.SetNoiseType(FastNoiseLite::NoiseType_Perlin);
            break;
        case NoiseType::SIMPLEX:
            noise.SetNoiseType(FastNoiseLite::NoiseType_OpenSimplex2);
            break;
        case NoiseType::CURL:
            // Domain-warped simplex gives the swirling, curl-like look of flames
            noise.SetNoiseType(FastNoiseLite::NoiseType_OpenSimplex2);
            noise.SetDomainWarpType(FastNoiseLite::DomainWarpType_OpenSimplex2);
            noise.SetDomainWarpAmp(1.5f);
            break;
        case NoiseType::FRACTAL:
            noise.SetNoiseType(FastNoiseLite::NoiseType_Perlin);
            noise.SetFractalType(FastNoiseLite::FractalType_FBm);
            noise.SetFractalOctaves(4);
            break;
        case NoiseType::CUSTOM:
            noise.SetNoiseType(FastNoiseLite::NoiseType_ValueCubic);
            break;
    }
}

float sampleNoise2D(const FastNoiseLite& noise, NoiseType type, float x, float y) {
    if (type == NoiseType::CURL) {
        float wx = x;
        float wy = y;
        noise.DomainWarp(wx, wy);
        return noise.GetNoise(wx, wy);
    }
    return noise.GetNoise(x, y);
}

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
}

std::string blendModeName(BlendMode mode) {
    switch (mode) {
        case BlendMode::ADDITIVE: return "additive";
        case BlendMode::MULTIPLY: return "multiply";
        case BlendMode::SCREEN: return "screen";
        case BlendMode::OVERLAY: return "overlay";
        case BlendMode::NORMAL: return "normal";
    }
    return "normal";
}

void applyBlendMode(ShaderBuilder& builder, BlendMode mode) {
    switch (mode) {
        case BlendMode::ADDITIVE: builder.enableAdditiveBlend(); break;
        case BlendMode::MULTIPLY: builder.enableMultiplyBlend(); break;
        case BlendMode::SCREEN: builder.enableScreenBlend(); break;
        case BlendMode::OVERLAY: builder.enableOverlayBlend(); break;
        case BlendMode::NORMAL: builder.enableNormalBlend(); break;
    }
}

const char* kFlameVertexShader =
    "#version 450\n"
    "layout(location = 0) in vec3 aPosition;\n"
    "layout(location = 1) in vec3 aNormal;\n"
    "layout(location = 2) in vec2 aTexCoord;\n"
    "layout(location = 0) out vec3 vPosition;\n"
    "layout(location = 1) out vec2 vTexCoord;\n"
    "uniform mat4 uModelViewProjection;\n"
    "uniform float uTime;\n"
    "uniform float uOscillationFreq;\n"
    "uniform float uOscillationAmplitude;\n"
    "void main() {\n"
    "    vec3 pos = aPosition;\n"
    "    // Lateral sway that grows toward the flame tip\n"
    "    pos.x += sin(uTime * uOscillationFreq + pos.y * 4.0) * uOscillationAmplitude * aTexCoord.y;\n"
    "    vPosition = pos;\n"
    "    vTexCoord = aTexCoord;\n"
    "    gl_Position = uModelViewProjection * vec4(pos, 1.0);\n"
    "}\n";

/** Scales every vertex, then re-normalizes normals (inverse-transpose of a diagonal scale). */
void scaleMesh(MagiTech::Mesh& mesh, const glm::vec3& scale) {
    const glm::vec3 inv(1.0f / std::max(scale.x, 1e-4f), 1.0f / std::max(scale.y, 1e-4f), 1.0f / std::max(scale.z, 1e-4f));
    for (auto& v : mesh.vertices) {
        v.position *= scale;
        const glm::vec3 n = v.normal * inv;
        const float len = glm::length(n);
        if (len > 0.0f) v.normal = n / len;
    }
}

/** Cone whose radius is perturbed by turbulence noise: an organic, licking flame body. */
MagiTech::Mesh buildTurbulentFlameMesh(const FlameProjectileParams& p) {
    MagiTech::Mesh mesh;
    const int rings = 16;
    const int segments = kRadialSegments;
    const float halfLength = p.length * 0.5f;
    const float baseRadius = p.width * 0.5f;

    FastNoiseLite noise;
    configureNoise(noise, p.noiseType, 1.0f);

    for (int r = 0; r <= rings; ++r) {
        const float v = r / static_cast<float>(rings);           // 0 = base, 1 = tip
        const float y = -halfLength + v * p.length;
        const float profile = std::sin((1.0f - v) * glm::half_pi<float>() + 0.15f) * (1.0f - v * v);
        for (int s = 0; s <= segments; ++s) {
            const float u = s / static_cast<float>(segments);
            const float a = u * glm::two_pi<float>();
            const float n = noise.GetNoise(std::cos(a) * p.turbulenceScale, y * p.turbulenceScale, std::sin(a) * p.turbulenceScale);
            const float radius = std::max(0.0f, baseRadius * profile *
                (1.0f + n * p.flameWidthVariation * p.turbulenceStrength));
            MagiTech::Mesh::Vertex vert;
            vert.position = {std::cos(a) * radius, y, std::sin(a) * radius * p.flameHeight};
            vert.normal = glm::normalize(glm::vec3(std::cos(a), 0.3f, std::sin(a)));
            vert.uv = {u, v};
            mesh.vertices.push_back(vert);
        }
    }
    for (int r = 0; r < rings; ++r) {
        for (int s = 0; s < segments; ++s) {
            const uint32_t i0 = static_cast<uint32_t>(r * (segments + 1) + s);
            const uint32_t i1 = i0 + 1;
            const uint32_t i2 = i0 + static_cast<uint32_t>(segments + 1);
            const uint32_t i3 = i2 + 1;
            mesh.indices.insert(mesh.indices.end(), {i0, i2, i1, i1, i2, i3});
        }
    }
    return mesh;
}

} // namespace

namespace MeshGen {
    MeshHandle buildFlame(const FlameProjectileParams& p) {
        Log::info("FlameProjectile", "Building flame mesh for: {} (type: {}, shape: {})",
                  p.id, flameTypeToString(p.flameType), flameShapeToString(p.flameShape));

        // Create core flame mesh based on shape
        MeshHandle coreMesh = 0;
        switch (p.flameShape) {
            case FlameShape::CONE:
                coreMesh = buildCone(p.length, p.width, p.flameHeight);
                break;
            case FlameShape::RIBBON:
                coreMesh = buildTrailRibbon(p.length, p.trailLength, p.width);
                break;
            case FlameShape::SPHERE: {
                // Fireball: sphere of diameter `width`, stretched along the flight axis by `length`
                MagiTech::Mesh sphere = Primitives::createSphere(p.width * 0.5f, kRadialSegments);
                scaleMesh(sphere, glm::vec3(1.0f, std::max(p.length / std::max(p.width, 1e-4f), 1.0f), p.flameHeight));
                coreMesh = storeMesh(sphere);
                break;
            }
            case FlameShape::CYLINDER: {
                MagiTech::Mesh cylinder = Primitives::createCylinder(p.width * 0.5f, p.length, kRadialSegments);
                scaleMesh(cylinder, glm::vec3(1.0f, 1.0f, p.flameHeight));
                coreMesh = storeMesh(cylinder);
                break;
            }
            case FlameShape::CUSTOM_SHAPE:
                coreMesh = storeMesh(buildTurbulentFlameMesh(p));
                break;
        }

        // Create trail mesh if enabled
        MeshHandle trailMesh = 0;
        if (p.flameShape != FlameShape::RIBBON && p.trailType != TrailType::NONE && p.trailLength > 0.0f) {
            trailMesh = buildTrailRibbon(p.length, p.trailLength, p.trailWidth);
        }

        // Merge meshes if trail exists
        if (trailMesh != 0 && coreMesh != 0) {
            std::vector<MeshHandle> meshes = {coreMesh, trailMesh};
            return mergeMeshes(meshes);
        }

        return coreMesh != 0 ? coreMesh : trailMesh;
    }

    MeshHandle buildCone(float length, float width, float height) {
        Log::info("FlameProjectile", "Building cone mesh: length={}, width={}, height={}", length, width, height);
        // Cone along +Y (tip forward), base diameter `width`; `height` scales the vertical cross-section
        MagiTech::Mesh cone = Primitives::createCone(width * 0.5f, length, kRadialSegments);
        scaleMesh(cone, glm::vec3(1.0f, 1.0f, height > 0.0f ? height : 1.0f));
        return storeMesh(cone);
    }

    MeshHandle buildTrailRibbon(float length, float trailLength, float width) {
        Log::info("FlameProjectile", "Building trail ribbon: length={}, trailLength={}, width={}", length, trailLength, width);
        if (trailLength <= 0.0f || width <= 0.0f) {
            return 0;
        }

        // Flat ribbon behind the flame body (from its tail at -length/2 backwards), tapering to a point
        MagiTech::Mesh ribbon;
        const int segments = 12;
        const float start = -length * 0.5f;
        for (int i = 0; i <= segments; ++i) {
            const float t = i / static_cast<float>(segments);
            const float y = start - t * trailLength;
            const float halfWidth = width * 0.5f * (1.0f - t);
            for (int side = 0; side < 2; ++side) {
                MagiTech::Mesh::Vertex v;
                v.position = {side == 0 ? -halfWidth : halfWidth, y, 0.0f};
                v.normal = {0.0f, 0.0f, 1.0f};
                v.uv = {static_cast<float>(side), t};
                v.color = glm::vec4(1.0f, 1.0f, 1.0f, 1.0f - t);   // fades out along the trail
                ribbon.vertices.push_back(v);
            }
        }
        for (int i = 0; i < segments; ++i) {
            const uint32_t b = static_cast<uint32_t>(i * 2);
            ribbon.indices.insert(ribbon.indices.end(), {b, b + 2, b + 1, b + 1, b + 2, b + 3});
        }
        return storeMesh(ribbon);
    }

    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes) {
        Log::info("FlameProjectile", "Merging {} meshes", meshes.size());
        MagiTech::Mesh merged;
        size_t parts = 0;
        for (MeshHandle handle : meshes) {
            if (auto mesh = getMesh(handle)) {
                merged.append(*mesh);
                ++parts;
            }
        }
        if (parts == 0) {
            Log::warn("FlameProjectile", "No stored geometry for the {} meshes to merge", meshes.size());
            return meshes.empty() ? 0 : meshes[0];
        }
        return storeMesh(merged);
    }
}

namespace ShaderGen {
    ShaderHandle buildFlame(const FlameProjectileParams& p) {
        Log::info("FlameProjectile", "Building flame shader for: {} (blend: {}, noise: {})",
                  p.id, blendModeToString(p.blendMode), noiseTypeToString(p.noiseType));

        // Create shader based on parameters
        std::string shaderCode = generateFlameShaderCode(p);

        ShaderBuilder builder = ShaderBuilder::create("flame_" + p.id);
        builder.setVertexShader(kFlameVertexShader);
        builder.setFragmentShader(shaderCode);
        builder.addUniform("uCoreColor", p.coreColor);
        builder.addUniform("uOuterColor", p.outerColor);
        builder.addUniform("uGlowColor", p.glowColor);
        builder.addUniform("uNoiseScale", p.turbulenceScale);
        builder.addUniform("uNoiseSpeed", p.flickerSpeed);
        builder.addUniform("uFlickerIntensity", p.flickerIntensity);
        builder.addUniform("uTurbulenceStrength", p.turbulenceStrength);
        builder.addUniform("uOscillationFreq", p.oscillationFreq);
        builder.addUniform("uOscillationAmplitude", p.oscillationAmplitude);
        builder.addUniform("uShaderIntensity", p.shaderIntensity);
        applyBlendMode(builder, p.blendMode);
        if (p.enableDistortion) {
            builder.enableFeature("DISTORTION");
            builder.addUniform("uDistortionStrength", p.distortionStrength);
        }
        if (p.enableBlur) {
            builder.enableFeature("BLUR");
            builder.addUniform("uBlurStrength", p.blurStrength);
        }

        Log::info("Compiling flame shader with parameters:");
        Log::info("FlameProjectile", "  - Flicker intensity: {}", p.flickerIntensity);
        Log::info("FlameProjectile", "  - Flicker speed: {}", p.flickerSpeed);
        Log::info("FlameProjectile", "  - Turbulence strength: {}", p.turbulenceStrength);
        Log::info("FlameProjectile", "  - Turbulence scale: {}", p.turbulenceScale);
        Log::info("FlameProjectile", "  - Oscillation freq: {}", p.oscillationFreq);
        Log::info("FlameProjectile", "  - Oscillation amplitude: {}", p.oscillationAmplitude);
        Log::info("FlameProjectile", "  - Enable distortion: {}", p.enableDistortion);
        Log::info("FlameProjectile", "  - Distortion strength: {}", p.distortionStrength);
        Log::info("FlameProjectile", "  - Enable blur: {}", p.enableBlur);
        Log::info("FlameProjectile", "  - Blur strength: {}", p.blurStrength);

        ShaderHandle handle = builder.compile();
        storeShaderSource(handle, FlameShaderSource{kFlameVertexShader, shaderCode, blendModeName(p.blendMode)});
        return handle;
    }

    ShaderHandle buildHeatDistortion(const FlameProjectileParams& p) {
        if (!p.enableHeatDistortion) {
            return 0; // No heat distortion
        }

        Log::info("FlameProjectile", "Building heat distortion shader for: {} (strength: {})",
                  p.id, p.heatDistortionStrength);

        std::stringstream ss;
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec3 vPosition;\n";
        ss << "layout(location = 1) in vec2 vTexCoord;\n";
        ss << "layout(location = 0) out vec4 fragColor;\n";
        ss << "uniform sampler2D uSceneColor;\n";
        ss << "uniform vec2 uScreenSize;\n";
        ss << "uniform float uTime;\n";
        ss << "uniform float uHeatDistortionStrength;\n";
        ss << "uniform float uNoiseScale;\n";
        ss << "float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }\n";
        ss << "void main() {\n";
        ss << "    vec2 uv = gl_FragCoord.xy / uScreenSize;\n";
        ss << "    // Rising shimmer: offset decays toward the edges of the distortion volume\n";
        ss << "    float edge = 1.0 - abs(vTexCoord.x * 2.0 - 1.0);\n";
        ss << "    vec2 offset = vec2(sin(uTime * 6.0 + vPosition.y * uNoiseScale * 10.0),\n";
        ss << "                       hash(floor(vPosition.xy * uNoiseScale * 20.0) + uTime) - 0.5);\n";
        ss << "    uv += offset * uHeatDistortionStrength * 0.01 * edge;\n";
        ss << "    fragColor = texture(uSceneColor, uv);\n";
        ss << "}\n";

        ShaderBuilder builder = ShaderBuilder::create("flame_heat_" + p.id);
        builder.setVertexShader(kFlameVertexShader);
        builder.setFragmentShader(ss.str());
        builder.addUniform("uHeatDistortionStrength", p.heatDistortionStrength);
        builder.addUniform("uNoiseScale", p.turbulenceScale);
        builder.enableFeature("HEAT_DISTORTION");
        builder.enableNormalBlend();

        ShaderHandle handle = builder.compile();
        storeShaderSource(handle, FlameShaderSource{kFlameVertexShader, ss.str(), "normal"});
        return handle;
    }

    std::string generateFlameShaderCode(const FlameProjectileParams& p) {
        std::stringstream ss;
        ss << "// Flame shader for: " << p.id << "\n";
        ss << "// Generated with parameters:\n";
        ss << "// - Blend mode: " << blendModeToString(p.blendMode) << "\n";
        ss << "// - Noise type: " << noiseTypeToString(p.noiseType) << "\n";
        ss << "// - Flicker intensity: " << p.flickerIntensity << "\n";
        ss << "// - Turbulence strength: " << p.turbulenceStrength << "\n";
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec3 vPosition;\n";
        ss << "layout(location = 1) in vec2 vTexCoord;\n";
        ss << "layout(location = 0) out vec4 fragColor;\n";
        ss << "\n";
        ss << "uniform vec3 uCoreColor;\n";
        ss << "uniform vec3 uOuterColor;\n";
        ss << "uniform vec3 uGlowColor;\n";
        ss << "uniform float uNoiseScale;\n";
        ss << "uniform float uNoiseSpeed;\n";
        ss << "uniform float uFlickerIntensity;\n";
        ss << "uniform float uTurbulenceStrength;\n";
        ss << "uniform float uShaderIntensity;\n";
        ss << "uniform float uTime;\n";
        ss << "uniform sampler2D uFlameTexture;\n";
        if (p.enableDistortion) {
            ss << "uniform float uDistortionStrength;\n";
        }
        ss << "\n";
        ss << "float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }\n";
        ss << "float valueNoise(vec2 p) {\n";
        ss << "    vec2 i = floor(p); vec2 f = fract(p);\n";
        ss << "    vec2 u = f * f * (3.0 - 2.0 * f);\n";
        ss << "    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);\n";
        ss << "}\n";
        ss << "float turbulence(vec2 p) {\n";
        ss << "    float sum = 0.0; float amp = 0.5;\n";
        ss << "    for (int i = 0; i < 4; ++i) { sum += amp * valueNoise(p); p *= 2.0; amp *= 0.5; }\n";
        ss << "    return sum;\n";
        ss << "}\n";
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vec2 uv = vTexCoord;\n";
        if (p.enableDistortion) {
            ss << "    uv.x += (valueNoise(uv * uNoiseScale + vec2(0.0, uTime)) - 0.5) * uDistortionStrength;\n";
        }
        ss << "    // Noise scrolls toward the tail so the flame appears to stream backwards\n";
        ss << "    float n = turbulence(uv * uNoiseScale + vec2(0.0, -uTime * uNoiseSpeed)) * uTurbulenceStrength;\n";
        ss << "    float heat = clamp(uv.y + n - 0.5, 0.0, 1.0);\n";
        ss << "    vec3 color = mix(uOuterColor, uCoreColor, heat);\n";
        ss << "    color += uGlowColor * pow(heat, 3.0) * 0.5;\n";
        ss << "    float flicker = 1.0 - uFlickerIntensity * 0.5 * (1.0 + sin(uTime * uNoiseSpeed * 6.2831 + n * 4.0)) * 0.5;\n";
        ss << "    vec4 tex = texture(uFlameTexture, uv);\n";
        ss << "    float alpha = clamp(heat * 1.5, 0.0, 1.0) * tex.a;\n";
        ss << "    fragColor = vec4(color * tex.rgb * flicker * uShaderIntensity, alpha);\n";
        ss << "}\n";

        return ss.str();
    }
}

namespace TextureGen {
    TextureHandle buildFlame(const FlameProjectileParams& p) {
        Log::info("FlameProjectile", "Building flame texture for: {} (noise: {}, scale: {})",
                  p.id, noiseTypeToString(p.noiseType), p.turbulenceScale);

        // Generate noise texture
        TextureHandle noiseTex = buildNoiseTexture(p.turbulenceScale, p.noiseType);

        // Generate gradient texture
        TextureHandle gradientTex = buildGradientTexture(p.coreColor, p.outerColor);

        // Merge textures
        return mergeTextures(noiseTex, gradientTex);
    }

    TextureHandle buildNoiseTexture(float scale, NoiseType type) {
        Log::info("FlameProjectile", "Building noise texture: scale={}, type={}", scale, noiseTypeToString(type));

        FastNoiseLite noise;
        configureNoise(noise, type, 1.0f);

        std::vector<uint8_t> rgba(static_cast<size_t>(kTextureSize) * kTextureSize * 4);
        for (int y = 0; y < kTextureSize; ++y) {
            for (int x = 0; x < kTextureSize; ++x) {
                const float nx = x / static_cast<float>(kTextureSize) * scale;
                const float ny = y / static_cast<float>(kTextureSize) * scale;
                const float value = 0.5f + 0.5f * sampleNoise2D(noise, type, nx, ny);
                const uint8_t b = toByte(value);
                const size_t i = (static_cast<size_t>(y) * kTextureSize + x) * 4;
                rgba[i + 0] = b;
                rgba[i + 1] = b;
                rgba[i + 2] = b;
                rgba[i + 3] = 255;
            }
        }
        return storeTexture(kTextureSize, kTextureSize, std::move(rgba));
    }

    TextureHandle buildGradientTexture(const glm::vec3& startColor, const glm::vec3& endColor) {
        Log::info("FlameProjectile", "Building gradient texture: start=({},{},{}), end=({},{},{})",
                  startColor.x, startColor.y, startColor.z,
                  endColor.x, endColor.y, endColor.z);

        // Radial gradient: core colour at the centre, outer colour at the rim, alpha falling off to 0
        std::vector<uint8_t> rgba(static_cast<size_t>(kTextureSize) * kTextureSize * 4);
        for (int y = 0; y < kTextureSize; ++y) {
            for (int x = 0; x < kTextureSize; ++x) {
                const float dx = (x + 0.5f) / kTextureSize - 0.5f;
                const float dy = (y + 0.5f) / kTextureSize - 0.5f;
                const float t = std::clamp(std::sqrt(dx * dx + dy * dy) * 2.0f, 0.0f, 1.0f);
                const glm::vec3 c = glm::mix(startColor, endColor, t);
                const size_t i = (static_cast<size_t>(y) * kTextureSize + x) * 4;
                rgba[i + 0] = toByte(c.r);
                rgba[i + 1] = toByte(c.g);
                rgba[i + 2] = toByte(c.b);
                rgba[i + 3] = toByte(1.0f - t * t);
            }
        }
        return storeTexture(kTextureSize, kTextureSize, std::move(rgba));
    }

    TextureHandle mergeTextures(const TextureHandle& noise, const TextureHandle& gradient) {
        Log::info("FlameProjectile", "Merging noise texture {} and gradient texture {}", noise, gradient);

        auto noiseData = getTexture(noise);
        auto gradientData = getTexture(gradient);
        if (!gradientData) {
            Log::warn("FlameProjectile", "Gradient texture {} not found; using noise texture", gradient);
            return noise;
        }
        if (!noiseData || noiseData->width != gradientData->width || noiseData->height != gradientData->height) {
            Log::warn("FlameProjectile", "Noise texture {} missing or size mismatch; using gradient", noise);
            return gradient;
        }

        // Gradient colour modulated by noise; noise also breaks up the alpha into licking tongues
        std::vector<uint8_t> rgba(gradientData->rgba.size());
        for (size_t i = 0; i + 3 < rgba.size(); i += 4) {
            const float n = noiseData->rgba[i] / 255.0f;
            const float shade = 0.6f + 0.4f * n;
            for (size_t c = 0; c < 3; ++c) {
                rgba[i + c] = toByte(gradientData->rgba[i + c] / 255.0f * shade);
            }
            rgba[i + 3] = toByte(gradientData->rgba[i + 3] / 255.0f * (0.35f + 0.65f * n));
        }
        return storeTexture(gradientData->width, gradientData->height, std::move(rgba));
    }
}

namespace ParticleGen {
    ParticleHandle buildEmbers(const FlameProjectileParams& p) {
        Log::info("FlameProjectile", "Building ember particles for: {} (count: {}, lifetime: {}, size: {})",
                  p.id, p.emberCount, p.emberLifetime, p.emberSize);
        if (p.emberCount <= 0) {
            return 0;
        }

        // Create ember particle emitter
        Log::info("Ember particle parameters:");
        Log::info("FlameProjectile", "  - Count: {}", p.emberCount);
        Log::info("FlameProjectile", "  - Lifetime: {}", p.emberLifetime);
        Log::info("FlameProjectile", "  - Size: {}", p.emberSize);
        Log::info("FlameProjectile", "  - Speed: {}", p.emberSpeed);
        Log::info("FlameProjectile", "  - Color: ({},{},{},{})",
                  p.emberColor.x, p.emberColor.y, p.emberColor.z, p.emberColor.w);
        Log::info("FlameProjectile", "  - Enable fade: {}", p.enableEmberFade);
        Log::info("FlameProjectile", "  - Fade speed: {}", p.emberFadeSpeed);

        // Embers drift upward (lift) against their mass, slowed by drag
        const float verticalAccel = p.enablePhysics ? (p.physicsLift - p.physicsMass * 9.81f) : 0.0f;
        ParticleEmitter emitter = ParticleBuilder::createEmitter(ParticleType::EMBER);
        emitter.setCount(p.emberCount)
            .setRate(p.emberCount / std::max(p.emberLifetime, 0.01f))
            .setLifetime(p.emberLifetime)
            .setStartSize(p.emberSize)
            .setEndSize(p.enableEmberFade ? p.emberSize * 0.25f : p.emberSize)
            .setColor(p.emberColor)
            .setAlpha(p.emberColor.a, p.enableEmberFade ? 0.0f : p.emberColor.a)
            .setSpeed(p.emberSpeed)
            .setShape(ParticleShape::CONE)
            .setConeAngle(35.0f)
            .setDirection(glm::vec3(0.0f, -1.0f, 0.0f))
            .setGravity(glm::vec3(0.0f, verticalAccel, 0.0f))
            .setAirResistance(p.physicsDrag)
            .setGlowColor(p.glowColor)
            .setGlowIntensity(p.shaderIntensity)
            .setLayer(ParticleLayer::Front);

        const ParticleHandle handle = emitter.getHandle();
        storeParticleConfig(handle, emitter.toOpenStarboundParticleJson());
        return handle;
    }

    ParticleHandle buildTrail(const FlameProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No trail
        }

        Log::info("FlameProjectile", "Building trail particles for: {} (type: {}, length: {}, width: {})",
                  p.id, trailTypeToString(p.trailType), p.trailLength, p.trailWidth);

        Log::info("Trail particle parameters:");
        Log::info("FlameProjectile", "  - Type: {}", trailTypeToString(p.trailType));
        Log::info("FlameProjectile", "  - Length: {}", p.trailLength);
        Log::info("FlameProjectile", "  - Width: {}", p.trailWidth);
        Log::info("FlameProjectile", "  - Opacity: {}", p.trailOpacity);
        Log::info("FlameProjectile", "  - Enable fade: {}", p.enableTrailFade);
        Log::info("FlameProjectile", "  - Fade speed: {}", p.trailFadeSpeed);

        // A particle lives as long as the projectile needs to travel one trail length
        const float lifetime = std::max(p.trailLength / std::max(p.speed, 0.01f), 0.05f);
        const float fadeLifetime = p.enableTrailFade ? lifetime / std::max(p.trailFadeSpeed, 0.01f) : lifetime;

        ParticleType type = ParticleType::TRAIL;
        glm::vec3 color = p.glowColor;
        if (p.trailType == TrailType::SMOKE) {
            type = ParticleType::AREA_PUFF;
            color = glm::vec3(0.25f, 0.22f, 0.2f);
        } else if (p.trailType == TrailType::PARTICLES) {
            type = ParticleType::EMBER;
        } else if (p.trailType == TrailType::HEAT_DISTORTION) {
            type = ParticleType::BILLBOARD;
        }

        ParticleEmitter emitter = ParticleBuilder::createEmitter(type);
        emitter.setCount(std::max(1, static_cast<int>(p.trailLength * 30.0f)))
            .setRate(30.0f * std::max(p.speed, 1.0f) / 10.0f)
            .setLifetime(fadeLifetime)
            .setStartSize(p.trailWidth)
            .setEndSize(p.enableTrailFade ? 0.0f : p.trailWidth)
            .setColor(color)
            .setAlpha(p.trailOpacity, p.enableTrailFade ? 0.0f : p.trailOpacity)
            .setDirection(glm::vec3(0.0f, -1.0f, 0.0f))
            .setSpeed(0.0f)
            .setLayer(ParticleLayer::Middle);
        if (p.trailType == TrailType::HEAT_DISTORTION) {
            emitter.setDistortionStrength(p.heatDistortionStrength);
        }

        const ParticleHandle handle = emitter.getHandle();
        storeParticleConfig(handle, emitter.toOpenStarboundParticleJson());
        return handle;
    }

    ParticleHandle buildSmoke(const FlameProjectileParams& p) {
        Log::info("FlameProjectile", "Building smoke particles for: {}", p.id);

        // Smoke trails behind the flame: larger, darker, slower and longer lived than embers
        const int count = std::max(1, p.emberCount / 4);
        ParticleEmitter emitter = ParticleBuilder::createEmitter(ParticleType::AREA_PUFF);
        emitter.setCount(count)
            .setRate(count / std::max(p.emberLifetime * 3.0f, 0.01f))
            .setLifetime(std::max(p.emberLifetime * 3.0f, 0.1f))
            .setStartSize(p.width)
            .setEndSize(p.width * 2.5f)
            .setColor(glm::vec4(0.2f, 0.2f, 0.2f, 0.5f))
            .setAlpha(0.5f, 0.0f)
            .setSpeed(p.emberSpeed * 0.3f)
            .setDirection(glm::vec3(0.0f, 1.0f, 0.0f))
            .setGravity(glm::vec3(0.0f, 0.5f, 0.0f))
            .setAirResistance(std::max(p.physicsDrag, 0.2f))
            .setLayer(ParticleLayer::Back);

        const ParticleHandle handle = emitter.getHandle();
        storeParticleConfig(handle, emitter.toOpenStarboundParticleJson());
        return handle;
    }
}

} // namespace FlameProjectiles
} // namespace MagiTech
