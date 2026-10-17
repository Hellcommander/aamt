#include "SpellAssetFactory.hpp"
#include "SpellProjectileAssets.hpp"
#include "core/Log.hpp"
#include "core/rendering/ShaderBuilder.hpp"
#include "core/particles/ParticleBuilder.hpp"
#include <algorithm>
#include <cmath>
#include <numbers>
#include <random>

namespace MagiTech {
namespace SpellProjectiles {

#define LOG_SPELL_GEN(Action, Id) Log::info("SpellProjectile", "SpellGen - {}: {}", #Action, Id)

namespace {

constexpr float kPi = std::numbers::pi_v<float>;

// Field-wise hashing: never hash raw object bytes (std::string internals and padding are not stable)
template <typename T>
void hashValue(XXH64_state_t& s, const T& value) {
    XXH64_update(&s, &value, sizeof(T));
}

void hashString(XXH64_state_t& s, const std::string& str) {
    const uint64_t len = str.size();
    hashValue(s, len);
    XXH64_update(&s, str.data(), str.size());
}

} // namespace

// Hash function implementations
uint64_t SpellParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashString(s, id);
    hashValue(s, shape);
    hashValue(s, baseRadius);
    hashValue(s, length);
    hashValue(s, dynamicTess);
    return XXH64_digest(&s);
}
uint64_t TrailParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashValue(s, enableTrail);
    hashValue(s, mode);
    hashValue(s, trailLength);
    hashValue(s, width);
    hashValue(s, uptime);
    hashValue(s, headColor);
    hashValue(s, tailColor);
    return XXH64_digest(&s);
}
uint64_t VFXParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashString(s, shaderTemplate);
    for (const auto& d : defines) { hashString(s, d); }
    hashValue(s, noiseIntensity);
    hashValue(s, pulseFreq);
    return XXH64_digest(&s);
}
uint64_t ParticleParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashValue(s, enableParticles);
    hashValue(s, style);
    hashValue(s, maxCount);
    hashValue(s, spawnRate);
    hashValue(s, lifeTime);
    hashValue(s, initialVelocity);
    hashValue(s, spreadAngle);
    return XXH64_digest(&s);
}
uint64_t LightParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashValue(s, enableLight);
    hashValue(s, color);
    hashValue(s, intensity);
    hashValue(s, flickerMode);
    hashValue(s, flickerSpeed);
    return XXH64_digest(&s);
}
uint64_t AudioParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashValue(s, playOnCast);
    hashString(s, sfxFile);
    hashValue(s, volume);
    hashValue(s, loop);
    return XXH64_digest(&s);
}
uint64_t CollisionParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    hashValue(s, enableCollider);
    hashValue(s, radius);
    hashValue(s, meshCollider);
    hashValue(s, triggerOnly);
    return XXH64_digest(&s);
}

// Helper functions for geometry generation
namespace GeometryHelpers {
    // Generate sphere vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateSphere(float radius, int segments, int rings) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;

        for (int ring = 0; ring <= rings; ++ring) {
            float phi = ring * kPi / rings;
            float y = radius * std::cos(phi);
            float ringRadius = radius * std::sin(phi);

            for (int segment = 0; segment <= segments; ++segment) {
                float theta = segment * 2 * kPi / segments;
                float x = ringRadius * std::cos(theta);
                float z = ringRadius * std::sin(theta);
                vertices.emplace_back(x, y, z);
            }
        }

        // Generate indices for triangles
        for (int ring = 0; ring < rings; ++ring) {
            for (int segment = 0; segment < segments; ++segment) {
                uint32_t current = ring * (segments + 1) + segment;
                uint32_t next = current + segments + 1;

                indices.push_back(current);
                indices.push_back(next);
                indices.push_back(current + 1);

                indices.push_back(next);
                indices.push_back(next + 1);
                indices.push_back(current + 1);
            }
        }

        return {vertices, indices};
    }

    // Generate cone vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateCone(float baseRadius, float height, int segments) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;

        // Base center
        vertices.emplace_back(0, 0, 0);

        // Base ring
        for (int i = 0; i <= segments; ++i) {
            float angle = i * 2 * kPi / segments;
            float x = baseRadius * std::cos(angle);
            float z = baseRadius * std::sin(angle);
            vertices.emplace_back(x, 0, z);
        }

        // Apex
        vertices.emplace_back(0, height, 0);
        const uint32_t apex = static_cast<uint32_t>(vertices.size() - 1);

        // Base triangles
        for (int i = 1; i <= segments; ++i) {
            indices.push_back(0);
            indices.push_back(i);
            indices.push_back(i + 1);
        }

        // Side triangles
        for (int i = 1; i <= segments; ++i) {
            indices.push_back(i);
            indices.push_back(apex);
            indices.push_back(i + 1);
        }

        return {vertices, indices};
    }

    // Generate torus vertices and indices
    std::pair<std::vector<glm::vec3>, std::vector<uint32_t>> generateTorus(float majorRadius, float minorRadius, int majorSegments, int minorSegments) {
        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;

        for (int i = 0; i <= majorSegments; ++i) {
            float majorAngle = i * 2 * kPi / majorSegments;
            float cosMajor = std::cos(majorAngle);
            float sinMajor = std::sin(majorAngle);

            for (int j = 0; j <= minorSegments; ++j) {
                float minorAngle = j * 2 * kPi / minorSegments;
                float cosMinor = std::cos(minorAngle);
                float sinMinor = std::sin(minorAngle);

                float x = (majorRadius + minorRadius * cosMinor) * cosMajor;
                float y = (majorRadius + minorRadius * cosMinor) * sinMajor;
                float z = minorRadius * sinMinor;

                vertices.emplace_back(x, y, z);
            }
        }

        // Generate indices
        for (int i = 0; i < majorSegments; ++i) {
            for (int j = 0; j < minorSegments; ++j) {
                uint32_t current = i * (minorSegments + 1) + j;
                uint32_t next = current + minorSegments + 1;

                indices.push_back(current);
                indices.push_back(next);
                indices.push_back(current + 1);

                indices.push_back(next);
                indices.push_back(next + 1);
                indices.push_back(current + 1);
            }
        }

        return {vertices, indices};
    }

    /** Builds a mesh with area-weighted smooth normals and planar UVs from raw positions. */
    MagiTech::Mesh toMesh(const std::vector<glm::vec3>& positions, const std::vector<uint32_t>& indices,
                          const std::vector<glm::vec4>& colors = {}) {
        MagiTech::Mesh mesh;
        mesh.vertices.resize(positions.size());
        glm::vec3 minP(0.0f), maxP(0.0f);
        if (!positions.empty()) {
            minP = maxP = positions.front();
            for (const auto& p : positions) {
                minP = glm::min(minP, p);
                maxP = glm::max(maxP, p);
            }
        }
        const glm::vec3 extent = glm::max(maxP - minP, glm::vec3(1e-6f));
        for (size_t i = 0; i < positions.size(); ++i) {
            auto& v = mesh.vertices[i];
            v.position = positions[i];
            v.normal = glm::vec3(0.0f);
            v.uv = glm::vec2((positions[i].x - minP.x) / extent.x, (positions[i].z - minP.z) / extent.z);
            if (i < colors.size()) v.color = colors[i];
        }
        mesh.indices = indices;
        for (size_t i = 0; i + 2 < indices.size(); i += 3) {
            auto& a = mesh.vertices[indices[i]];
            auto& b = mesh.vertices[indices[i + 1]];
            auto& c = mesh.vertices[indices[i + 2]];
            const glm::vec3 fn = glm::cross(b.position - a.position, c.position - a.position);
            a.normal += fn;
            b.normal += fn;
            c.normal += fn;
        }
        for (auto& v : mesh.vertices) {
            v.normal = glm::length(v.normal) > 0.0f ? glm::normalize(v.normal) : glm::vec3(0.0f, 1.0f, 0.0f);
        }
        return mesh;
    }
}

namespace GeometryGen {
    MeshHandle build(const SpellParams& s) {
        LOG_SPELL_GEN(BuildingGeometry, s.id);

        std::vector<glm::vec3> vertices;
        std::vector<uint32_t> indices;
        // Dynamic tessellation doubles the base resolution
        const int detail = s.dynamicTess ? 32 : 16;

        switch (s.shape) {
            case SpellShape::Sphere: {
                auto [verts, inds] = GeometryHelpers::generateSphere(s.baseRadius, detail, detail);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Cone: {
                auto [verts, inds] = GeometryHelpers::generateCone(s.baseRadius, s.length, detail);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Torus: {
                auto [verts, inds] = GeometryHelpers::generateTorus(s.baseRadius, s.baseRadius * 0.3f, detail, detail / 2);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
            case SpellShape::Ribbon: {
                // Flat ribbon strip along +Z, subdivided so it can bend in the shader
                float width = s.baseRadius * 0.1f;
                const int segments = detail;
                for (int i = 0; i <= segments; ++i) {
                    const float z = s.length * static_cast<float>(i) / static_cast<float>(segments);
                    vertices.emplace_back(-width, 0.0f, z);
                    vertices.emplace_back(width, 0.0f, z);
                }
                for (int i = 0; i < segments; ++i) {
                    const uint32_t b = static_cast<uint32_t>(i * 2);
                    indices.insert(indices.end(), {b, b + 1, b + 2, b + 1, b + 3, b + 2});
                }
                break;
            }
            case SpellShape::CustomMesh:
            default: {
                // No custom mesh source in SpellParams: fall back to a sphere of the requested radius
                auto [verts, inds] = GeometryHelpers::generateSphere(s.baseRadius, detail, detail);
                vertices = std::move(verts);
                indices = std::move(inds);
                break;
            }
        }

        return storeSpellMesh(GeometryHelpers::toMesh(vertices, indices));
    }
}

namespace TrailGen {
    MeshHandle build(const TrailParams& t, const SpellParams& s) {
        if (!t.enableTrail) return 0;

        LOG_SPELL_GEN(BuildingTrail, s.id);

        std::vector<glm::vec3> vertices;
        std::vector<glm::vec4> colors;
        std::vector<uint32_t> indices;

        switch (t.mode) {
            case TrailMode::Ribbon: {
                // Generate ribbon trail
                int segments = std::max(1, static_cast<int>(t.trailLength * 10));
                float segmentLength = t.trailLength / segments;

                for (int i = 0; i <= segments; ++i) {
                    float u = static_cast<float>(i) / segments;
                    float alpha = 1.0f - u; // Fade from head to tail

                    // Interpolate color
                    glm::vec4 color = glm::mix(t.headColor, t.tailColor, u);

                    // Create ribbon strip
                    float width = t.width * alpha;
                    vertices.emplace_back(-width, 0, i * segmentLength);
                    vertices.emplace_back(width, 0, i * segmentLength);
                    colors.push_back(color);
                    colors.push_back(color);
                }

                // Generate indices for ribbon
                for (int i = 0; i < segments; ++i) {
                    uint32_t base = i * 2;
                    indices.push_back(base);
                    indices.push_back(base + 1);
                    indices.push_back(base + 2);
                    indices.push_back(base + 1);
                    indices.push_back(base + 3);
                    indices.push_back(base + 2);
                }
                break;
            }
            case TrailMode::SDFRibbon: {
                // Tube with a square cross-section; the SDF shader rounds it off
                int segments = std::max(1, static_cast<int>(t.trailLength * 8));
                float segmentLength = t.trailLength / segments;

                for (int i = 0; i <= segments; ++i) {
                    float u = static_cast<float>(i) / segments;
                    float alpha = 1.0f - u;
                    glm::vec4 color = glm::mix(t.headColor, t.tailColor, u);

                    float width = t.width * alpha;
                    for (int j = 0; j < 4; ++j) {
                        float angle = j * kPi / 2;
                        float x = width * std::cos(angle);
                        float y = width * std::sin(angle);
                        vertices.emplace_back(x, y, i * segmentLength);
                        colors.push_back(color);
                    }
                }

                // Generate indices for SDF ribbon
                for (int i = 0; i < segments; ++i) {
                    uint32_t base = i * 4;
                    for (int j = 0; j < 4; ++j) {
                        uint32_t current = base + j;
                        uint32_t next = base + ((j + 1) % 4);
                        uint32_t nextRow = base + 4 + j;
                        uint32_t nextRowNext = base + 4 + ((j + 1) % 4);

                        indices.push_back(current);
                        indices.push_back(next);
                        indices.push_back(nextRow);

                        indices.push_back(next);
                        indices.push_back(nextRowNext);
                        indices.push_back(nextRow);
                    }
                }
                break;
            }
            case TrailMode::Particles:
            default: {
                // Point cloud along the trail; each point becomes a camera-facing quad
                int particleCount = std::max(1, static_cast<int>(t.trailLength * 20));
                std::mt19937 rng(static_cast<uint32_t>(t.hashKey() ^ s.hashKey()));
                std::uniform_real_distribution<float> jitter(-0.5f, 0.5f);
                for (int i = 0; i < particleCount; ++i) {
                    float u = static_cast<float>(i) / particleCount;
                    float alpha = 1.0f - u;

                    // Random particle positions along trail
                    glm::vec3 center(jitter(rng) * t.width * alpha, jitter(rng) * t.width * alpha, u * t.trailLength);
                    float half = t.width * 0.25f * alpha;
                    glm::vec4 color = glm::mix(t.headColor, t.tailColor, u);
                    const uint32_t base = static_cast<uint32_t>(vertices.size());
                    vertices.push_back(center + glm::vec3(-half, -half, 0.0f));
                    vertices.push_back(center + glm::vec3(half, -half, 0.0f));
                    vertices.push_back(center + glm::vec3(half, half, 0.0f));
                    vertices.push_back(center + glm::vec3(-half, half, 0.0f));
                    colors.insert(colors.end(), 4, color);
                    indices.insert(indices.end(), {base, base + 1, base + 2, base, base + 2, base + 3});
                }
                break;
            }
        }

        return storeSpellMesh(GeometryHelpers::toMesh(vertices, indices, colors));
    }
}

namespace ShaderGen {
    ShaderHandle build(const VFXParams& v) {
        LOG_SPELL_GEN(BuildingShader, v.shaderTemplate);

        // Template-based shader generation
        std::string shaderSource = "// Generated VFX Shader\n";
        shaderSource += "// Template: " + v.shaderTemplate + "\n";
        shaderSource += "// Defines: ";
        for (const auto& define : v.defines) {
            shaderSource += define + " ";
        }
        shaderSource += "\n\n";

        // Add shader content based on defines
        for (const auto& define : v.defines) {
            if (define == "USE_NOISE") {
                shaderSource += "#define USE_NOISE\n";
                shaderSource += "uniform float uNoiseIntensity = " + std::to_string(v.noiseIntensity) + ";\n";
            }
            if (define == "ALPHA_PULSE") {
                shaderSource += "#define ALPHA_PULSE\n";
                shaderSource += "uniform float uPulseFreq = " + std::to_string(v.pulseFreq) + ";\n";
            }
        }

        // Add basic shader structure
        shaderSource += R"(
uniform float uTime;
uniform vec4 uColor = vec4(1.0, 1.0, 1.0, 1.0);

void main() {
    vec4 color = uColor;

    #ifdef USE_NOISE
    float noise = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
    color.rgb += noise * uNoiseIntensity;
    #endif

    #ifdef ALPHA_PULSE
    float pulse = 0.5 + 0.5 * sin(uTime * uPulseFreq);
    color.a *= pulse;
    #endif

    gl_FragColor = color;
}
)";

        ShaderBuilder builder = ShaderBuilder::create(v.shaderTemplate.empty() ? "spell_vfx" : v.shaderTemplate);
        builder.setFragmentShader(shaderSource);
        builder.addUniform("uNoiseIntensity", v.noiseIntensity);
        builder.addUniform("uPulseFreq", v.pulseFreq);
        for (const auto& define : v.defines) {
            builder.enableFeature(define);
        }
        builder.enableAdditiveBlend();

        const ShaderHandle handle = builder.compile();
        storeSpellShaderSource(handle, std::move(shaderSource));
        return handle;
    }
}

namespace ParticleGen {
    ParticleHandle build(const ParticleParams& p) {
        LOG_SPELL_GEN(BuildingParticles, (int)p.style);

        const float speed = glm::length(p.initialVelocity);
        const glm::vec3 direction = speed > 0.0f ? p.initialVelocity / speed : glm::vec3(0.0f, 0.0f, 1.0f);

        // Particle system configuration per style
        ParticleType type = ParticleType::BURST;
        glm::vec4 color(1.0f);
        float startSize = 0.1f;
        float endSize = 0.0f;
        glm::vec3 gravity(0.0f);
        ParticleLayer layer = ParticleLayer::Middle;
        switch (p.style) {
            case ParticleStyle::Sparks: {
                // High velocity, short lifetime, bright colors
                type = ParticleType::STREAK;
                color = glm::vec4(1.0f, 0.95f, 0.7f, 1.0f);
                startSize = 0.05f;
                gravity = glm::vec3(0.0f, -9.81f, 0.0f);
                layer = ParticleLayer::Front;
                break;
            }
            case ParticleStyle::Smoke: {
                // Low velocity, long lifetime, dark colors
                type = ParticleType::AREA_PUFF;
                color = glm::vec4(0.25f, 0.25f, 0.27f, 0.6f);
                startSize = 0.2f;
                endSize = 0.6f;
                gravity = glm::vec3(0.0f, 0.4f, 0.0f);
                layer = ParticleLayer::Back;
                break;
            }
            case ParticleStyle::Ember: {
                // Medium velocity, medium lifetime, orange/red colors
                type = ParticleType::EMBER;
                color = glm::vec4(1.0f, 0.45f, 0.1f, 1.0f);
                startSize = 0.06f;
                endSize = 0.02f;
                gravity = glm::vec3(0.0f, 0.8f, 0.0f);
                break;
            }
            case ParticleStyle::Cosmic: {
                // Variable velocity, long lifetime, purple/blue colors
                type = ParticleType::BILLBOARD;
                color = glm::vec4(0.55f, 0.35f, 1.0f, 0.9f);
                startSize = 0.08f;
                endSize = 0.0f;
                layer = ParticleLayer::Front;
                break;
            }
        }

        ParticleEmitter emitter = ParticleBuilder::createEmitter(type);
        emitter.setCount(p.maxCount)
            .setRate(p.spawnRate)
            .setLifetime(p.lifeTime)
            .setStartSize(startSize)
            .setEndSize(endSize)
            .setColor(color)
            .setAlpha(color.a, 0.0f)
            .setShape(ParticleShape::CONE)
            .setConeAngle(p.spreadAngle)
            .setDirection(direction)
            .setSpeed(speed)
            .setGravity(gravity)
            .setLayer(layer);
        return storeSpellParticleConfig(emitter.toOpenStarboundParticleJson());
    }
}

namespace LightGen {
    LightHandle build(const LightParams& l) {
        LOG_SPELL_GEN(BuildingLight, l.intensity);

        SpellLightDesc light;
        light.color = l.color;
        light.intensity = l.intensity;
        light.flickerMode = l.flickerMode;
        light.flickerSpeed = l.flickerSpeed;

        // How deep the flicker dips below the base intensity
        switch (l.flickerMode) {
            case LightFlicker::None:
                light.flickerAmplitude = 0.0f;
                break;
            case LightFlicker::Sinusoidal:
                light.flickerAmplitude = 0.3f;
                break;
            case LightFlicker::NoiseDriven:
                light.flickerAmplitude = 0.5f;
                break;
            case LightFlicker::Pulse:
                light.flickerAmplitude = 0.8f;
                break;
        }

        return storeSpellLight(light);
    }
}

namespace AudioGen {
    AudioHandle build(const AudioParams& a) {
        LOG_SPELL_GEN(BuildingAudio, a.sfxFile);

        if (a.sfxFile.empty()) {
            Log::warn("SpellProjectile", "Audio cue requested without an sfx file; no audio generated");
            return 0;
        }
        return storeSpellAudio(SpellAudioDesc{a.sfxFile, std::clamp(a.volume, 0.0f, 1.0f), a.loop});
    }
}

namespace CollisionGen {
    ColliderHandle build(const CollisionParams& c, const SpellParams& s) {
        LOG_SPELL_GEN(BuildingCollider, s.id);

        SpellColliderDesc collider;
        collider.triggerOnly = c.triggerOnly;
        collider.radius = c.radius;
        if (c.meshCollider) {
            // Use the spell's own geometry as the collision mesh
            collider.shape = SpellColliderShape::Mesh;
            collider.mesh = GeometryGen::build(s);
        } else if (s.shape == SpellShape::Cone || s.shape == SpellShape::Ribbon) {
            // Elongated shapes: capsule along the flight axis
            collider.shape = SpellColliderShape::Capsule;
            collider.length = s.length;
        } else {
            collider.shape = SpellColliderShape::Sphere;
        }
        return storeSpellCollider(collider);
    }
}

} // namespace SpellProjectiles
} // namespace MagiTech
