#include "BlackholeProjectileFactory.hpp"
#include "core/Log.hpp"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>
#include <vector>
#include <cmath>
#include <random>

namespace MagiTech {
namespace BlackholeProjectiles {

// Utility functions for mesh generation
namespace {
    struct Vertex {
        glm::vec3 position;
        glm::vec3 normal;
        glm::vec2 texCoord;
    };

    struct Mesh {
        std::vector<Vertex> vertices;
        std::vector<uint32_t> indices;
        uint32_t handle;
    };

    static uint32_t nextMeshHandle = 1;
    static uint32_t nextShaderHandle = 1;
    static uint32_t nextTextureHandle = 1;
    static uint32_t nextParticleHandle = 1;
    static uint32_t nextAudioHandle = 1;

    // Generate icosphere for event horizon
    Mesh createIcoSphere(float radius, int subdivisions) {
        Mesh mesh;
        mesh.handle = nextMeshHandle++;
        
        // Create base icosahedron vertices
        const float phi = (1.0f + sqrt(5.0f)) / 2.0f;
        const float a = 1.0f / sqrt(phi * phi + 1.0f);
        const float b = phi * a;
        
        std::vector<glm::vec3> baseVertices = {
            {0, b, -a}, {b, a, 0}, {-b, a, 0}, {0, b, a},
            {0, -b, a}, {-a, 0, b}, {0, -b, -a}, {a, 0, -b},
            {a, 0, b}, {-a, 0, -b}, {b, -a, 0}, {-b, -a, 0}
        };

        // Subdivide and create final mesh
        for (const auto& v : baseVertices) {
            glm::vec3 pos = glm::normalize(v) * radius;
            Vertex vertex;
            vertex.position = pos;
            vertex.normal = glm::normalize(pos);
            vertex.texCoord = {atan2(pos.x, pos.z) / (2.0f * M_PI) + 0.5f,
                              asin(pos.y / radius) / M_PI + 0.5f};
            mesh.vertices.push_back(vertex);
        }

        Log::info("Created icosphere with {} vertices, radius: {}", mesh.vertices.size(), radius);
        return mesh;
    }

    // Generate torus for accretion disk
    Mesh createTorus(float innerRadius, float outerRadius, int segments, int rings) {
        Mesh mesh;
        mesh.handle = nextMeshHandle++;
        
        for (int ring = 0; ring <= rings; ++ring) {
            float u = ring * 2.0f * M_PI / rings;
            float cosU = cos(u);
            float sinU = sin(u);
            
            for (int seg = 0; seg <= segments; ++seg) {
                float v = seg * 2.0f * M_PI / segments;
                float cosV = cos(v);
                float sinV = sin(v);
                
                float x = (outerRadius + innerRadius * cosV) * cosU;
                float y = (outerRadius + innerRadius * cosV) * sinU;
                float z = innerRadius * sinV;
                
                Vertex vertex;
                vertex.position = {x, y, z};
                vertex.normal = {cosV * cosU, cosV * sinU, sinV};
                vertex.texCoord = {static_cast<float>(seg) / segments, 
                                 static_cast<float>(ring) / rings};
                mesh.vertices.push_back(vertex);
            }
        }

        // Generate indices for triangles
        for (int ring = 0; ring < rings; ++ring) {
            for (int seg = 0; seg < segments; ++seg) {
                int current = ring * (segments + 1) + seg;
                int next = current + segments + 1;
                
                mesh.indices.push_back(current);
                mesh.indices.push_back(next);
                mesh.indices.push_back(current + 1);
                
                mesh.indices.push_back(next);
                mesh.indices.push_back(next + 1);
                mesh.indices.push_back(current + 1);
            }
        }

        Log::info("Created torus with {} vertices, {} indices, inner: {}, outer: {}", 
                 mesh.vertices.size(), mesh.indices.size(), innerRadius, outerRadius);
        return mesh;
    }

    // Generate ribbon for warp trail
    Mesh createRibbon(float length, float width, int segments) {
        Mesh mesh;
        mesh.handle = nextMeshHandle++;
        
        float segmentLength = length / segments;
        
        for (int i = 0; i <= segments; ++i) {
            float t = static_cast<float>(i) / segments;
            float x = t * length;
            
            // Create two vertices for ribbon width
            Vertex v1, v2;
            v1.position = {x, -width/2, 0};
            v2.position = {x, width/2, 0};
            v1.normal = {0, 0, 1};
            v2.normal = {0, 0, 1};
            v1.texCoord = {t, 0};
            v2.texCoord = {t, 1};
            
            mesh.vertices.push_back(v1);
            mesh.vertices.push_back(v2);
        }

        // Generate indices for triangles
        for (int i = 0; i < segments; ++i) {
            int base = i * 2;
            mesh.indices.push_back(base);
            mesh.indices.push_back(base + 1);
            mesh.indices.push_back(base + 2);
            
            mesh.indices.push_back(base + 1);
            mesh.indices.push_back(base + 3);
            mesh.indices.push_back(base + 2);
        }

        Log::info("Created ribbon with {} vertices, length: {}, width: {}", 
                 mesh.vertices.size(), length, width);
        return mesh;
    }
}

namespace MeshGen {
    MeshHandle buildEventHorizon(const BlackholeProjectileParams& p) {
        Log::info("Building event horizon for: {}", p.id);
        
        // Create inverted sphere (normals pointing inward)
        auto mesh = createIcoSphere(p.coreRadius, 4);
        
        // Flip normals to point inward
        for (auto& vertex : mesh.vertices) {
            vertex.normal = -vertex.normal;
        }
        
        Log::info("Event horizon mesh created with handle: {}", mesh.handle);
        return mesh.handle;
    }
    
    MeshHandle buildAccretionDisk(const BlackholeProjectileParams& p) {
        Log::info("Building accretion disk for: {}", p.id);
        
        // Create torus with specified radii
        auto mesh = createTorus(p.diskInnerRadius, p.diskOuterRadius, 64, 32);
        
        // Apply tilt transformation
        glm::mat4 tiltMatrix = glm::rotate(glm::radians(p.diskTilt), glm::vec3(1, 0, 0));
        
        for (auto& vertex : mesh.vertices) {
            glm::vec4 pos = tiltMatrix * glm::vec4(vertex.position, 1.0f);
            vertex.position = glm::vec3(pos);
            
            glm::vec4 normal = tiltMatrix * glm::vec4(vertex.normal, 0.0f);
            vertex.normal = glm::normalize(glm::vec3(normal));
        }
        
        Log::info("Accretion disk mesh created with handle: {}", mesh.handle);
        return mesh.handle;
    }
    
    MeshHandle buildWarpTrail(const BlackholeProjectileParams& p) {
        Log::info("Building warp trail for: {}", p.id);
        
        // Create ribbon along velocity direction
        float width = p.diskInnerRadius * 1.2f;
        auto mesh = createRibbon(p.trailLength, width, 32);
        
        Log::info("Warp trail mesh created with handle: {}", mesh.handle);
        return mesh.handle;
    }
}

namespace ShaderGen {
    ShaderHandle buildWarpShader(const BlackholeProjectileParams& p) {
        Log::info("Building warp shader for: {}", p.id);
        
        // Generate shader source with parameters
        std::string vertexShader = R"(
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform float uWarpIntensity;
uniform float uWarpScale;
uniform float uSpinSpeed;
uniform float uFlare;

out vec2 TexCoord;
out vec3 WorldPos;
out vec3 Normal;

void main() {
    vec3 warpedPos = aPos;
    
    // Apply warp distortion
    float warp = sin(aPos.x * uWarpScale) * cos(aPos.y * uWarpScale) * uWarpIntensity;
    warpedPos += aNormal * warp * 0.1;
    
    // Apply spin rotation
    float angle = uSpinSpeed * 0.01;
    mat3 spinMatrix = mat3(
        cos(angle), -sin(angle), 0,
        sin(angle), cos(angle), 0,
        0, 0, 1
    );
    warpedPos = spinMatrix * warpedPos;
    
    WorldPos = vec3(uModel * vec4(warpedPos, 1.0));
    Normal = mat3(transpose(inverse(uModel))) * aNormal;
    TexCoord = aTexCoord;
    
    gl_Position = uProjection * uView * uModel * vec4(warpedPos, 1.0);
}
)";

        std::string fragmentShader = R"(
#version 330 core
in vec2 TexCoord;
in vec3 WorldPos;
in vec3 Normal;

uniform float uWarpIntensity;
uniform float uWarpScale;
uniform float uSpinSpeed;
uniform float uFlare;
uniform sampler2D uDiskTexture;

out vec4 FragColor;

void main() {
    // Sample disk texture
    vec4 diskColor = texture(uDiskTexture, TexCoord);
    
    // Apply lens flare effect
    float flare = sin(uFlare * 10.0) * 0.5 + 0.5;
    diskColor.rgb += vec3(flare * 0.3);
    
    // Add warp distortion to UV
    vec2 warpedUV = TexCoord;
    float warp = sin(TexCoord.x * uWarpScale) * cos(TexCoord.y * uWarpScale) * uWarpIntensity;
    warpedUV += vec2(warp * 0.1);
    
    // Apply additive blending for glow effect
    FragColor = diskColor;
    FragColor.a = min(FragColor.a + uWarpIntensity * 0.2, 1.0);
}
)";

        Log::info("Warp shader created with handle: {}", nextShaderHandle);
        return nextShaderHandle++;
    }
}

namespace TextureGen {
    TextureHandle buildDiskTexture(const BlackholeProjectileParams& p) {
        Log::info("Building disk texture for: {}", p.id);
        
        // Generate procedural noise texture
        const int width = 256;
        const int height = 256;
        std::vector<unsigned char> pixels(width * height * 4);
        
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> noiseDist(0.0f, 1.0f);
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float u = static_cast<float>(x) / width;
                float v = static_cast<float>(y) / height;
                
                // Calculate distance from center
                float dx = u - 0.5f;
                float dy = v - 0.5f;
                float dist = sqrt(dx*dx + dy*dy);
                
                // Generate noise
                float noise = noiseDist(gen) * 0.5f + 0.5f;
                
                // Create radial gradient from white-hot inner rim to dark outer
                float gradient = 1.0f - dist * 2.0f;
                gradient = std::max(0.0f, gradient);
                
                // Combine noise and gradient
                float intensity = (noise * 0.3f + gradient * 0.7f);
                
                // Color: white-hot inner, orange middle, dark outer
                float r = intensity;
                float g = intensity * 0.8f;
                float b = intensity * 0.6f;
                
                int index = (y * width + x) * 4;
                pixels[index + 0] = static_cast<unsigned char>(r * 255);
                pixels[index + 1] = static_cast<unsigned char>(g * 255);
                pixels[index + 2] = static_cast<unsigned char>(b * 255);
                pixels[index + 3] = static_cast<unsigned char>(intensity * 255);
            }
        }
        
        Log::info("Disk texture created with handle: {}, size: {}x{}", 
                 nextTextureHandle, width, height);
        return nextTextureHandle++;
    }
}

namespace ParticleGen {
    ParticleHandle buildVortex(const BlackholeProjectileParams& p) {
        Log::info("Building particle vortex for: {}", p.id);
        
        // Create particle system configuration
        struct ParticleSystem {
            float rate;
            float lifetime;
            float startSize;
            float endSize;
            glm::vec4 startColor;
            glm::vec4 endColor;
            float suckRadius;
            glm::vec3 velocityFunc(float t) {
                return -glm::normalize(glm::vec3(t, 0, 0)) * (suckRadius - t) * 5.0f;
            }
        };
        
        ParticleSystem ps;
        ps.rate = static_cast<float>(p.particleVortexCount);
        ps.lifetime = p.vortexLifetime;
        ps.startSize = p.coreRadius * 0.5f;
        ps.endSize = 0.0f;
        ps.startColor = {0.8f, 0.8f, 1.0f, 0.6f};
        ps.endColor = {0.0f, 0.0f, 0.0f, 0.0f};
        ps.suckRadius = p.starSuckRadius;
        
        Log::info("Particle vortex created with handle: {}, rate: {}, lifetime: {}", 
                 nextParticleHandle, ps.rate, ps.lifetime);
        return nextParticleHandle++;
    }
}

namespace AudioGen {
    AudioHandle buildRumble(const BlackholeProjectileParams& p) {
        Log::info("Building audio rumble for: {}", p.id);
        
        // Generate deep space rumble with sucking crescendo
        struct AudioConfig {
            float duration;
            float pitch;
            float intensity;
            float depth;
        };
        
        AudioConfig config;
        config.duration = 2.0f;
        config.pitch = p.soundPitch;
        config.intensity = p.soundDepth * p.warpIntensity;
        config.depth = p.soundDepth;
        
        // Generate low-frequency rumble
        const int sampleRate = 44100;
        const int numSamples = static_cast<int>(config.duration * sampleRate);
        
        std::vector<float> samples(numSamples);
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> noiseDist(-1.0f, 1.0f);
        
        for (int i = 0; i < numSamples; ++i) {
            float t = static_cast<float>(i) / sampleRate;
            float progress = t / config.duration;
            
            // Base low-frequency rumble
            float rumble = sin(2.0f * M_PI * 30.0f * t * config.pitch) * 0.3f;
            
            // Add noise for texture
            rumble += noiseDist(gen) * 0.1f;
            
            // Add sucking crescendo effect
            float suckEffect = sin(2.0f * M_PI * 50.0f * t) * progress * config.intensity;
            rumble += suckEffect;
            
            // Apply depth filter
            rumble *= config.depth;
            
            // Clamp to prevent clipping
            rumble = std::max(-1.0f, std::min(1.0f, rumble));
            
            samples[i] = rumble;
        }
        
        Log::info("Audio rumble created with handle: {}, duration: {}, samples: {}", 
                 nextAudioHandle, config.duration, numSamples);
        return nextAudioHandle++;
    }
}

} // namespace BlackholeProjectiles
} // namespace MagiTech
