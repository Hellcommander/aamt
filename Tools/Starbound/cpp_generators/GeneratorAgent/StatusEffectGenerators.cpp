#include "StatusEffectFactory.hpp"
#include "StatusEffectGenerators.hpp"
#include "StatusEffectTypes.hpp"
#include "StatusEffectGenAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <FastNoiseLite.h>
#include <glm/glm.hpp>
#include <algorithm>
#include <cmath>
#include <numbers>
#include <string>
#include <vector>

// The StatusEffectFactory member functions live in StatusEffectFactory.cpp; this file
// holds the generator namespaces and the global factory instance.

namespace MagiTech {
namespace StatusEffects {

// Global factory instance
StatusEffectFactory g_effectFactory;

// Utility functions for generation
namespace {
    constexpr float kTwoPi = 2.0f * std::numbers::pi_v<float>;

    uint8_t toByte(float v) {
        return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
    }

    int seedOf(const StatusEffectParams& s) {
        return static_cast<int>(s.hashKey() & 0x7fffffff);
    }

    // Fractal (4-octave) value noise texture; deterministic per effect so cache hits match
    std::vector<unsigned char> generateNoiseTexture(int width, int height, float scale, int seed) {
        std::vector<unsigned char> pixels(static_cast<size_t>(width) * height * 4);
        FastNoiseLite noise(seed);
        noise.SetNoiseType(FastNoiseLite::NoiseType_ValueCubic);
        noise.SetFractalType(FastNoiseLite::FractalType_FBm);
        noise.SetFractalOctaves(4);
        noise.SetFrequency(1.0f);

        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float u = static_cast<float>(x) / width * scale * 8.0f;
                float v = static_cast<float>(y) / height * scale * 8.0f;
                float value = 0.5f + 0.5f * noise.GetNoise(u, v);

                size_t index = (static_cast<size_t>(y) * width + x) * 4;
                unsigned char b = toByte(value);
                pixels[index + 0] = b; // R
                pixels[index + 1] = b; // G
                pixels[index + 2] = b; // B
                pixels[index + 3] = 255;   // A
            }
        }

        return pixels;
    }

    // Generate radial gradient texture
    std::vector<unsigned char> generateGradientTexture(int width, int height,
                                                      const glm::vec3& colorPrimary,
                                                      const glm::vec3& colorSecondary) {
        std::vector<unsigned char> pixels(static_cast<size_t>(width) * height * 4);

        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float dx = static_cast<float>(x - width/2) / (width/2);
                float dy = static_cast<float>(y - height/2) / (height/2);
                float dist = std::sqrt(dx*dx + dy*dy);
                dist = std::max(0.0f, std::min(1.0f, dist));

                // Interpolate between primary and secondary colors
                glm::vec3 color = glm::mix(colorPrimary, colorSecondary, dist);

                size_t index = (static_cast<size_t>(y) * width + x) * 4;
                pixels[index + 0] = toByte(color.r);
                pixels[index + 1] = toByte(color.g);
                pixels[index + 2] = toByte(color.b);
                pixels[index + 3] = toByte(1.0f - dist * dist);
            }
        }

        return pixels;
    }

    MagiTech::Mesh::Vertex makeVertex(const glm::vec3& position, const glm::vec3& normal, const glm::vec2& uv) {
        MagiTech::Mesh::Vertex v;
        v.position = position;
        v.normal = normal;
        v.uv = uv;
        return v;
    }

    /** Flat ring (annulus) in the XZ plane; `radiusAt(i)` lets the outer edge vary per segment. */
    template <typename OuterRadius>
    MagiTech::Mesh generateRing(int segments, float innerRadius, OuterRadius radiusAt) {
        MagiTech::Mesh mesh;
        for (int i = 0; i <= segments; ++i) {
            const float u = static_cast<float>(i) / segments;
            const float angle = u * kTwoPi;
            const float cosA = std::cos(angle);
            const float sinA = std::sin(angle);
            const float outer = radiusAt(i);
            mesh.vertices.push_back(makeVertex({cosA * innerRadius, 0, sinA * innerRadius}, {0, 1, 0}, {u, 0}));
            mesh.vertices.push_back(makeVertex({cosA * outer, 0, sinA * outer}, {0, 1, 0}, {u, 1}));
        }
        for (int i = 0; i < segments; ++i) {
            const uint32_t b = static_cast<uint32_t>(i * 2);
            mesh.indices.insert(mesh.indices.end(), {b, b + 1, b + 2, b + 1, b + 3, b + 2});
        }
        return mesh;
    }

    MagiTech::Mesh generateRing(int segments, float innerRadius, float outerRadius) {
        return generateRing(segments, innerRadius, [outerRadius](int) { return outerRadius; });
    }

    // Aura quad in the XZ plane
    MagiTech::Mesh generateAuraQuad(float size) {
        MagiTech::Mesh mesh;
        mesh.vertices = {
            makeVertex({-size, 0, -size}, {0, 1, 0}, {0, 0}),
            makeVertex({ size, 0, -size}, {0, 1, 0}, {1, 0}),
            makeVertex({ size, 0,  size}, {0, 1, 0}, {1, 1}),
            makeVertex({-size, 0,  size}, {0, 1, 0}, {0, 1})
        };
        mesh.indices = {0, 1, 2, 0, 2, 3};
        return mesh;
    }

    // Plus-shaped aura: two crossing bars in the XZ plane
    MagiTech::Mesh generateCross(float size, float barWidth) {
        MagiTech::Mesh mesh;
        auto addBar = [&mesh](float hx, float hz) {
            const uint32_t b = static_cast<uint32_t>(mesh.vertices.size());
            mesh.vertices.push_back(makeVertex({-hx, 0, -hz}, {0, 1, 0}, {0, 0}));
            mesh.vertices.push_back(makeVertex({ hx, 0, -hz}, {0, 1, 0}, {1, 0}));
            mesh.vertices.push_back(makeVertex({ hx, 0,  hz}, {0, 1, 0}, {1, 1}));
            mesh.vertices.push_back(makeVertex({-hx, 0,  hz}, {0, 1, 0}, {0, 1}));
            mesh.indices.insert(mesh.indices.end(), {b, b + 1, b + 2, b, b + 2, b + 3});
        };
        addBar(size, barWidth);
        addBar(barWidth, size);
        return mesh;
    }

    std::string shaderTypeName(const StatusEffectParams& s) {
        return s.shaderType.empty() ? std::string("standard") : s.shaderType;
    }
}

namespace ShaderGen {
    ShaderHandle build(const StatusEffectParams& s) {
        Log::info("StatusEffect", "Building shader for effect: {}", s.id);

        // Generate shader source with parameters
        std::string vertexShader = R"(
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform float uTime;
uniform float uIntensity;
uniform float uNoiseScale;
uniform float uNoiseSpeed;
uniform float uOscillationFreq;
uniform bool uDissolve;
uniform float uDissolveThreshold;

out vec2 TexCoord;
out vec3 WorldPos;
out vec3 Normal;

void main() {
    vec3 pos = aPos;

    // Apply oscillation if enabled
    if (uOscillationFreq > 0.0) {
        float oscillation = sin(uTime * uOscillationFreq) * 0.1;
        pos += aNormal * oscillation;
    }

    // Apply noise distortion
    vec2 noiseUV = aTexCoord * uNoiseScale + uTime * uNoiseSpeed;
    float noise = sin(noiseUV.x) * cos(noiseUV.y);
    pos += aNormal * noise * 0.05;

    WorldPos = vec3(uModel * vec4(pos, 1.0));
    Normal = mat3(transpose(inverse(uModel))) * aNormal;
    TexCoord = aTexCoord;

    gl_Position = uProjection * uView * uModel * vec4(pos, 1.0);
}
)";

        std::string fragmentShader = R"(
#version 330 core
in vec2 TexCoord;
in vec3 WorldPos;
in vec3 Normal;

uniform vec3 uColorPrimary;
uniform vec3 uColorSecondary;
uniform float uTime;
uniform float uIntensity;
uniform float uNoiseScale;
uniform float uNoiseSpeed;
uniform float uOscillationFreq;
uniform bool uDissolve;
uniform float uDissolveThreshold;
uniform sampler2D uNoiseTexture;
uniform sampler2D uGradientTexture;

out vec4 FragColor;

void main() {
    // Sample noise texture
    vec2 noiseUV = TexCoord * uNoiseScale + uTime * uNoiseSpeed;
    float noise = texture(uNoiseTexture, noiseUV).r;

    // Sample gradient texture
    vec4 gradient = texture(uGradientTexture, TexCoord);

    // Blend colors based on noise
    vec3 color = mix(uColorPrimary, uColorSecondary, noise);
    color *= gradient.rgb;

    // Apply intensity
    color *= uIntensity;

    // Apply dissolve effect
    float alpha = 1.0;
    if (uDissolve) {
        float dissolveNoise = texture(uNoiseTexture, TexCoord * 2.0).r;
        alpha = step(uDissolveThreshold, dissolveNoise);
    }

    // Add pulsing effect
    float pulse = sin(uTime * uOscillationFreq) * 0.5 + 0.5;
    color *= (1.0 + pulse * 0.2);

    FragColor = vec4(color, alpha * gradient.a);
}
)";

        ShaderBuilder builder = ShaderBuilder::create("status_" + s.id + "_" + shaderTypeName(s));
        builder.setVertexShader(vertexShader);
        builder.setFragmentShader(fragmentShader);
        builder.addUniform("uColorPrimary", s.colorPrimary);
        builder.addUniform("uColorSecondary", s.colorSecondary);
        builder.addUniform("uIntensity", s.intensity * s.shaderIntensity);
        builder.addUniform("uNoiseScale", s.noiseScale);
        builder.addUniform("uNoiseSpeed", s.noiseSpeed);
        builder.addUniform("uOscillationFreq", s.oscillationFreq);
        builder.addUniform("uDissolve", s.dissolve ? 1 : 0);
        builder.addUniform("uDissolveThreshold", 1.0f - std::clamp(s.opacity, 0.0f, 1.0f));
        if (s.enableDistortion) {
            builder.enableFeature("DISTORTION");
            builder.addUniform("uDistortionStrength", s.distortionStrength);
        }
        if (s.enableBlur) {
            builder.enableFeature("BLUR");
            builder.addUniform("uBlurStrength", s.blurStrength);
        }
        builder.enableAdditiveBlend();

        const ShaderHandle handle = builder.compile();
        storeStatusEffectShader(handle, StatusEffectShaderSource{vertexShader, fragmentShader});
        Log::info("StatusEffect", "Shader created with handle: {}", handle);
        return handle;
    }
}

namespace TextureGen {
    TextureHandle build(const StatusEffectParams& s) {
        Log::info("StatusEffect", "Building texture for effect: {}", s.id);

        const int width = 256;
        const int height = 256;

        // Generate noise texture
        auto noisePixels = generateNoiseTexture(width, height, s.noiseScale, seedOf(s));

        // Generate gradient texture
        auto gradientPixels = generateGradientTexture(width, height, s.colorPrimary, s.colorSecondary);

        // Combine: gradient colour modulated by noise, gradient alpha scaled by opacity
        std::vector<unsigned char> combinedPixels(static_cast<size_t>(width) * height * 4);
        for (size_t i = 0; i + 3 < combinedPixels.size(); i += 4) {
            float noise = noisePixels[i] / 255.0f;
            float shade = 0.7f + 0.3f * noise;
            for (size_t c = 0; c < 3; ++c) {
                combinedPixels[i + c] = toByte(gradientPixels[i + c] / 255.0f * shade);
            }
            combinedPixels[i + 3] = toByte(gradientPixels[i + 3] / 255.0f * std::clamp(s.opacity, 0.0f, 1.0f));
        }

        const TextureHandle handle = storeStatusEffectTexture(width, height, std::move(combinedPixels));
        Log::info("StatusEffect", "Texture created with handle: {}, size: {}x{}", handle, width, height);
        return handle;
    }
}

namespace MeshGen {
    MeshHandle build(const StatusEffectParams& s) {
        Log::info("StatusEffect", "Building mesh for effect: {}", s.id);

        MagiTech::Mesh mesh;

        switch (s.shapeType) {
            case ShapeType::CIRCLE:
                // Ring around the target
                mesh = generateRing(64, 0.8f, 1.2f);
                break;

            case ShapeType::SQUARE:
                // Aura quad
                mesh = generateAuraQuad(1.0f);
                break;

            case ShapeType::HEXAGON:
                // Hexagonal ring
                mesh = generateRing(6, 0.8f, 1.2f);
                break;

            case ShapeType::STAR:
                // Five-pointed star: outer edge alternates between point and notch radius
                mesh = generateRing(10, 0.3f, [](int i) { return (i % 2 == 0) ? 1.4f : 0.6f; });
                break;

            case ShapeType::CROSS:
                mesh = generateCross(1.0f, 0.3f);
                break;

            case ShapeType::DIAMOND:
                // Four-sided ring
                mesh = generateRing(4, 0.8f, 1.2f);
                break;

            default:
                // Default to aura quad
                mesh = generateAuraQuad(1.0f);
                break;
        }

        // Effect scale applies to the whole shape
        if (s.scale != 1.0f) {
            for (auto& v : mesh.vertices) {
                v.position *= s.scale;
            }
        }

        const MeshHandle handle = storeStatusEffectMesh(mesh);
        Log::info("StatusEffect", "Mesh created with handle: {}, vertices: {}, indices: {}",
                 handle, mesh.vertices.size(), mesh.indices.size());
        return handle;
    }
}

namespace ParticleGen {
    ParticleHandle build(const StatusEffectParams& s) {
        Log::info("StatusEffect", "Building particles for effect: {}", s.id);

        if (s.particleType == ParticleType::NONE) {
            Log::info("StatusEffect", "No particles requested for effect: {}", s.id);
            return 0;
        }

        int count = s.particleCount;
        glm::vec3 color = s.colorPrimary;
        float speed = s.noiseSpeed * 0.5f;
        float size = 0.1f;
        glm::vec3 gravity(0.0f);
        MagiTech::ParticleType emitterType = MagiTech::ParticleType::BILLBOARD;
        std::string typeName;

        switch (s.particleType) {
            case ParticleType::SPARKLE:
                typeName = "sparkle";
                count *= 2; // More sparkles
                emitterType = MagiTech::ParticleType::EMBER;
                break;
            case ParticleType::SMOKE:
                typeName = "smoke";
                size *= 2.0f; // Larger smoke particles
                emitterType = MagiTech::ParticleType::AREA_PUFF;
                gravity = {0.0f, 0.3f, 0.0f};
                break;
            case ParticleType::FIRE:
                typeName = "fire";
                color = {1.0f, 0.5f, 0.0f};
                emitterType = MagiTech::ParticleType::EMBER;
                gravity = {0.0f, 1.0f, 0.0f};
                break;
            case ParticleType::ICE:
                typeName = "ice";
                color = {0.5f, 0.8f, 1.0f};
                emitterType = MagiTech::ParticleType::SHARD_BURST;
                gravity = {0.0f, -2.0f, 0.0f};
                break;
            case ParticleType::LIGHTNING:
                typeName = "lightning";
                color = {1.0f, 1.0f, 0.0f};
                speed *= 2.0f;
                emitterType = MagiTech::ParticleType::STREAK;
                break;
            case ParticleType::POISON:
                typeName = "poison";
                color = {0.2f, 1.0f, 0.2f};
                emitterType = MagiTech::ParticleType::AREA_PUFF;
                gravity = {0.0f, 0.2f, 0.0f};
                break;
            case ParticleType::HEALING:
                typeName = "healing";
                color = {0.0f, 1.0f, 0.0f};
                gravity = {0.0f, 0.8f, 0.0f};
                break;
            case ParticleType::SHIELD:
                typeName = "shield";
                color = {0.5f, 0.5f, 1.0f};
                break;
            default:
                typeName = "custom";
                break;
        }

        ParticleEmitter emitter = ParticleBuilder::createEmitter(emitterType);
        emitter.setCount(count)
            .setRate(count / std::max(s.duration, 0.1f))
            .setLifetime(std::min(s.duration, 2.0f))
            .setStartSize(size * s.scale)
            .setEndSize(size * s.scale * 0.5f)
            .setColor(glm::vec4(color, std::clamp(s.opacity, 0.0f, 1.0f)))
            .setAlpha(std::clamp(s.opacity, 0.0f, 1.0f), 0.0f)
            .setShape(ParticleShape::CYLINDER)
            .setRadius(1.0f * s.scale)
            .setHeight(2.0f * s.scale)
            .setSpeed(speed)
            .setGravity(gravity)
            .setGlowColor(s.glowColor)
            .setGlowIntensity(s.intensity)
            .setLayer(ParticleLayer::Front);

        const ParticleHandle handle = storeStatusEffectParticles(emitter.toOpenStarboundParticleJson());
        Log::info("StatusEffect", "Particle system created with handle: {}, type: {}, count: {}",
                 handle, typeName, count);
        return handle;
    }
}

namespace IconGen {
    TextureHandle build(const StatusEffectParams& s, const UIParams& u) {
        Log::info("StatusEffect", "Building icon for effect: {}", s.id);

        const int width = std::clamp(u.iconSize, 1, 512);
        const int height = width;
        std::vector<unsigned char> pixels(static_cast<size_t>(width) * height * 4, 0);
        const float half = std::max(width / 2.0f, 1.0f);

        // Generate background
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float dx = (x + 0.5f - half) / half;
                float dy = (y + 0.5f - half) / half;
                float dist = std::sqrt(dx*dx + dy*dy);

                size_t index = (static_cast<size_t>(y) * width + x) * 4;
                const bool inside = (u.backgroundShape == "circle" && dist <= 1.0f) || u.backgroundShape == "square";
                if (inside) {
                    pixels[index + 0] = toByte(u.borderColor.r);
                    pixels[index + 1] = toByte(u.borderColor.g);
                    pixels[index + 2] = toByte(u.borderColor.b);
                    pixels[index + 3] = toByte(u.borderColor.a);
                }
            }
        }

        // Symbol: filled disc in the effect's icon colour with a soft glow ring
        int centerX = width / 2;
        int centerY = height / 2;
        int symbolSize = std::max(1, width / 4);

        for (int y = centerY - symbolSize; y <= centerY + symbolSize; ++y) {
            for (int x = centerX - symbolSize; x <= centerX + symbolSize; ++x) {
                if (x >= 0 && x < width && y >= 0 && y < height) {
                    size_t index = (static_cast<size_t>(y) * width + x) * 4;

                    float dx = static_cast<float>(x - centerX) / symbolSize;
                    float dy = static_cast<float>(y - centerY) / symbolSize;
                    float dist = std::sqrt(dx*dx + dy*dy);

                    if (dist <= 0.8f) {
                        pixels[index + 0] = toByte(s.iconColor.r);
                        pixels[index + 1] = toByte(s.iconColor.g);
                        pixels[index + 2] = toByte(s.iconColor.b);
                        pixels[index + 3] = 255;
                    } else if (dist <= 1.0f && glm::length(s.glowColor) > 0.0f) {
                        const float a = (1.0f - dist) / 0.2f;
                        pixels[index + 0] = toByte(glm::mix(pixels[index + 0] / 255.0f, s.glowColor.r, a));
                        pixels[index + 1] = toByte(glm::mix(pixels[index + 1] / 255.0f, s.glowColor.g, a));
                        pixels[index + 2] = toByte(glm::mix(pixels[index + 2] / 255.0f, s.glowColor.b, a));
                        pixels[index + 3] = std::max<unsigned char>(pixels[index + 3], toByte(a));
                    }
                }
            }
        }

        // Flash overlay: brighten the whole icon so it reads as "just applied"
        if (u.flashOnApply) {
            Log::info("StatusEffect", "  - Adding flash overlay to icon {}", s.id);
            for (size_t i = 0; i + 3 < pixels.size(); i += 4) {
                for (size_t c = 0; c < 3; ++c) {
                    pixels[i + c] = toByte(pixels[i + c] / 255.0f * 0.6f + 0.4f);
                }
            }
        }

        const TextureHandle handle = storeStatusEffectTexture(width, height, std::move(pixels));
        Log::info("StatusEffect", "Icon created with handle: {}, size: {}x{}", handle, width, height);
        return handle;
    }
}

} // namespace StatusEffects
} // namespace MagiTech
