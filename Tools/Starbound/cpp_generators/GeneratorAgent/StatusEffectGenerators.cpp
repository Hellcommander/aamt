#include "core/modules/status_effect_generator/StatusEffectFactory.hpp"
#include "core/modules/status_effect_generator/StatusEffectParams.hpp"
#include "core/Log.hpp"
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtx/transform.hpp>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>
#include <vector>
#include <cmath>
#include <random>

namespace MagiTech {
namespace StatusEffects {

// Global factory instance
StatusEffectFactory g_effectFactory;

// Utility functions for generation
namespace {
    static uint32_t nextShaderHandle = 1;
    static uint32_t nextTextureHandle = 1;
    static uint32_t nextMeshHandle = 1;
    static uint32_t nextParticleHandle = 1;
    static uint32_t nextIconHandle = 1;

    // Generate procedural noise for textures
    std::vector<unsigned char> generateNoiseTexture(int width, int height, float scale) {
        std::vector<unsigned char> pixels(width * height * 4);
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> noiseDist(0.0f, 1.0f);
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float u = static_cast<float>(x) / width * scale;
                float v = static_cast<float>(y) / height * scale;
                
                // Generate noise using multiple octaves
                float noise = 0.0f;
                float amplitude = 1.0f;
                float frequency = 1.0f;
                
                for (int octave = 0; octave < 4; ++octave) {
                    noise += noiseDist(gen) * amplitude;
                    amplitude *= 0.5f;
                    frequency *= 2.0f;
                }
                
                noise = std::max(0.0f, std::min(1.0f, noise));
                
                int index = (y * width + x) * 4;
                unsigned char value = static_cast<unsigned char>(noise * 255);
                pixels[index + 0] = value; // R
                pixels[index + 1] = value; // G
                pixels[index + 2] = value; // B
                pixels[index + 3] = 255;   // A
            }
        }
        
        return pixels;
    }

    // Generate radial gradient texture
    std::vector<unsigned char> generateGradientTexture(int width, int height, 
                                                      const glm::vec3& colorPrimary, 
                                                      const glm::vec3& colorSecondary) {
        std::vector<unsigned char> pixels(width * height * 4);
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float dx = static_cast<float>(x - width/2) / (width/2);
                float dy = static_cast<float>(y - height/2) / (height/2);
                float dist = sqrt(dx*dx + dy*dy);
                dist = std::max(0.0f, std::min(1.0f, dist));
                
                // Interpolate between primary and secondary colors
                glm::vec3 color = glm::mix(colorPrimary, colorSecondary, dist);
                
                int index = (y * width + x) * 4;
                pixels[index + 0] = static_cast<unsigned char>(color.r * 255);
                pixels[index + 1] = static_cast<unsigned char>(color.g * 255);
                pixels[index + 2] = static_cast<unsigned char>(color.b * 255);
                pixels[index + 3] = 255;
            }
        }
        
        return pixels;
    }

    // Generate vertex data for ring mesh
    struct Vertex {
        glm::vec3 position;
        glm::vec3 normal;
        glm::vec2 texCoord;
    };

    std::vector<Vertex> generateRingVertices(int segments, float innerRadius, float outerRadius) {
        std::vector<Vertex> vertices;
        
        for (int i = 0; i <= segments; ++i) {
            float angle = static_cast<float>(i) / segments * 2.0f * M_PI;
            float cosA = cos(angle);
            float sinA = sin(angle);
            
            // Inner vertex
            Vertex v1;
            v1.position = {cosA * innerRadius, 0, sinA * innerRadius};
            v1.normal = {0, 1, 0};
            v1.texCoord = {static_cast<float>(i) / segments, 0};
            vertices.push_back(v1);
            
            // Outer vertex
            Vertex v2;
            v2.position = {cosA * outerRadius, 0, sinA * outerRadius};
            v2.normal = {0, 1, 0};
            v2.texCoord = {static_cast<float>(i) / segments, 1};
            vertices.push_back(v2);
        }
        
        return vertices;
    }

    // Generate vertex data for aura quad
    std::vector<Vertex> generateAuraQuadVertices(float size) {
        std::vector<Vertex> vertices = {
            {{-size, 0, -size}, {0, 1, 0}, {0, 0}},
            {{ size, 0, -size}, {0, 1, 0}, {1, 0}},
            {{ size, 0,  size}, {0, 1, 0}, {1, 1}},
            {{-size, 0,  size}, {0, 1, 0}, {0, 1}}
        };
        return vertices;
    }

    // Generate vertex data for beam mesh
    std::vector<Vertex> generateBeamVertices(int segments, float length, float radius) {
        std::vector<Vertex> vertices;
        
        for (int i = 0; i <= segments; ++i) {
            float angle = static_cast<float>(i) / segments * 2.0f * M_PI;
            float cosA = cos(angle);
            float sinA = sin(angle);
            
            // Start vertex
            Vertex v1;
            v1.position = {cosA * radius, 0, sinA * radius};
            v1.normal = {cosA, 0, sinA};
            v1.texCoord = {static_cast<float>(i) / segments, 0};
            vertices.push_back(v1);
            
            // End vertex
            Vertex v2;
            v2.position = {cosA * radius, length, sinA * radius};
            v2.normal = {cosA, 0, sinA};
            v2.texCoord = {static_cast<float>(i) / segments, 1};
            vertices.push_back(v2);
        }
        
        return vertices;
    }

    // Generate vertex data for splash mesh
    std::vector<Vertex> generateSplashVertices(int fanCount, float radius) {
        std::vector<Vertex> vertices;
        
        for (int i = 0; i <= fanCount; ++i) {
            float angle = static_cast<float>(i) / fanCount * 2.0f * M_PI;
            float cosA = cos(angle);
            float sinA = sin(angle);
            
            // Center vertex
            Vertex v1;
            v1.position = {0, 0, 0};
            v1.normal = {0, 1, 0};
            v1.texCoord = {0.5f, 0.5f};
            vertices.push_back(v1);
            
            // Edge vertex
            Vertex v2;
            v2.position = {cosA * radius, 0, sinA * radius};
            v2.normal = {0, 1, 0};
            v2.texCoord = {cosA * 0.5f + 0.5f, sinA * 0.5f + 0.5f};
            vertices.push_back(v2);
        }
        
        return vertices;
    }
}

namespace ShaderGen {
    ShaderHandle build(const StatusEffectParams& s) {
        Log::info("Building shader for effect: {}", s.id);
        
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

        Log::info("Shader created with handle: {}", nextShaderHandle);
        return nextShaderHandle++;
    }
}

namespace TextureGen {
    TextureHandle build(const StatusEffectParams& s) {
        Log::info("Building texture for effect: {}", s.id);
        
        const int width = 256;
        const int height = 256;
        
        // Generate noise texture
        auto noisePixels = generateNoiseTexture(width, height, s.noiseScale);
        
        // Generate gradient texture
        auto gradientPixels = generateGradientTexture(width, height, s.colorPrimary, s.colorSecondary);
        
        // Combine textures (in a real implementation, this would be done in the shader)
        std::vector<unsigned char> combinedPixels(width * height * 4);
        for (int i = 0; i < width * height * 4; i += 4) {
            // Blend noise and gradient
            float noise = noisePixels[i] / 255.0f;
            float gradient = gradientPixels[i] / 255.0f;
            unsigned char blended = static_cast<unsigned char>((noise * 0.3f + gradient * 0.7f) * 255);
            
            combinedPixels[i + 0] = blended; // R
            combinedPixels[i + 1] = blended; // G
            combinedPixels[i + 2] = blended; // B
            combinedPixels[i + 3] = 255;     // A
        }
        
        Log::info("Texture created with handle: {}, size: {}x{}", 
                 nextTextureHandle, width, height);
        return nextTextureHandle++;
    }
}

namespace MeshGen {
    MeshHandle build(const StatusEffectParams& s) {
        Log::info("Building mesh for effect: {}", s.id);
        
        std::vector<Vertex> vertices;
        std::vector<uint32_t> indices;
        
        switch (s.shapeType) {
            case ShapeType::CIRCLE:
                // Create ring mesh
                vertices = generateRingVertices(64, 0.8f, 1.2f);
                // Generate indices for triangle strip
                for (int i = 0; i < 64; ++i) {
                    indices.push_back(i * 2);
                    indices.push_back(i * 2 + 1);
                }
                break;
                
            case ShapeType::SQUARE:
                // Create aura quad
                vertices = generateAuraQuadVertices(1.0f);
                indices = {0, 1, 2, 0, 2, 3};
                break;
                
            case ShapeType::HEXAGON:
                // Create hexagonal ring
                vertices = generateRingVertices(6, 0.8f, 1.2f);
                for (int i = 0; i < 6; ++i) {
                    indices.push_back(i * 2);
                    indices.push_back(i * 2 + 1);
                }
                break;
                
            case ShapeType::STAR:
                // Create star-shaped mesh
                vertices = generateRingVertices(10, 0.6f, 1.4f);
                for (int i = 0; i < 10; ++i) {
                    indices.push_back(i * 2);
                    indices.push_back(i * 2 + 1);
                }
                break;
                
            case ShapeType::CROSS:
                // Create cross-shaped mesh
                vertices = generateAuraQuadVertices(1.0f);
                indices = {0, 1, 2, 0, 2, 3};
                break;
                
            case ShapeType::DIAMOND:
                // Create diamond-shaped mesh
                vertices = generateRingVertices(4, 0.8f, 1.2f);
                for (int i = 0; i < 4; ++i) {
                    indices.push_back(i * 2);
                    indices.push_back(i * 2 + 1);
                }
                break;
                
            default:
                // Default to aura quad
                vertices = generateAuraQuadVertices(1.0f);
                indices = {0, 1, 2, 0, 2, 3};
                break;
        }
        
        Log::info("Mesh created with handle: {}, vertices: {}, indices: {}", 
                 nextMeshHandle, vertices.size(), indices.size());
        return nextMeshHandle++;
    }
}

namespace ParticleGen {
    ParticleHandle build(const StatusEffectParams& s) {
        Log::info("Building particles for effect: {}", s.id);
        
        if (s.particleType == ParticleType::NONE) {
            Log::info("No particles requested for effect: {}", s.id);
            return 0;
        }
        
        // Create particle system configuration
        struct ParticleSystem {
            std::string type;
            int count;
            glm::vec3 color;
            float lifetime;
            float speed;
            float size;
            bool enableRotation;
            float rotationSpeed;
        };
        
        ParticleSystem ps;
        ps.count = s.particleCount;
        ps.color = s.colorPrimary;
        ps.lifetime = s.duration;
        ps.speed = s.noiseSpeed * 0.5f;
        ps.size = 0.1f;
        ps.enableRotation = s.enableRotation;
        ps.rotationSpeed = s.rotationSpeed;
        
        switch (s.particleType) {
            case ParticleType::SPARKLE:
                ps.type = "sparkle";
                ps.count *= 2; // More sparkles
                break;
            case ParticleType::SMOKE:
                ps.type = "smoke";
                ps.size *= 2.0f; // Larger smoke particles
                break;
            case ParticleType::FIRE:
                ps.type = "fire";
                ps.color = {1.0f, 0.5f, 0.0f};
                break;
            case ParticleType::ICE:
                ps.type = "ice";
                ps.color = {0.5f, 0.8f, 1.0f};
                break;
            case ParticleType::LIGHTNING:
                ps.type = "lightning";
                ps.color = {1.0f, 1.0f, 0.0f};
                ps.speed *= 2.0f;
                break;
            case ParticleType::POISON:
                ps.type = "poison";
                ps.color = {0.2f, 1.0f, 0.2f};
                break;
            case ParticleType::HEALING:
                ps.type = "healing";
                ps.color = {0.0f, 1.0f, 0.0f};
                break;
            case ParticleType::SHIELD:
                ps.type = "shield";
                ps.color = {0.5f, 0.5f, 1.0f};
                break;
            default:
                ps.type = "custom";
                break;
        }
        
        Log::info("Particle system created with handle: {}, type: {}, count: {}", 
                 nextParticleHandle, ps.type, ps.count);
        return nextParticleHandle++;
    }
}

namespace IconGen {
    TextureHandle build(const StatusEffectParams& s, const UIParams& u) {
        Log::info("Building icon for effect: {}", s.id);
        
        const int width = u.iconSize;
        const int height = u.iconSize;
        std::vector<unsigned char> pixels(width * height * 4);
        
        // Generate background
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float dx = static_cast<float>(x - width/2) / (width/2);
                float dy = static_cast<float>(y - height/2) / (height/2);
                float dist = sqrt(dx*dx + dy*dy);
                
                int index = (y * width + x) * 4;
                
                if (u.backgroundShape == "circle") {
                    if (dist <= 1.0f) {
                        // Background circle
                        pixels[index + 0] = static_cast<unsigned char>(u.borderColor.r * 255);
                        pixels[index + 1] = static_cast<unsigned char>(u.borderColor.g * 255);
                        pixels[index + 2] = static_cast<unsigned char>(u.borderColor.b * 255);
                        pixels[index + 3] = static_cast<unsigned char>(u.borderColor.a * 255);
                    } else {
                        // Transparent outside
                        pixels[index + 0] = 0;
                        pixels[index + 1] = 0;
                        pixels[index + 2] = 0;
                        pixels[index + 3] = 0;
                    }
                } else if (u.backgroundShape == "square") {
                    // Square background
                    pixels[index + 0] = static_cast<unsigned char>(u.borderColor.r * 255);
                    pixels[index + 1] = static_cast<unsigned char>(u.borderColor.g * 255);
                    pixels[index + 2] = static_cast<unsigned char>(u.borderColor.b * 255);
                    pixels[index + 3] = static_cast<unsigned char>(u.borderColor.a * 255);
                } else {
                    // No background
                    pixels[index + 0] = 0;
                    pixels[index + 1] = 0;
                    pixels[index + 2] = 0;
                    pixels[index + 3] = 0;
                }
            }
        }
        
        // Add icon symbol based on effect type
        int centerX = width / 2;
        int centerY = height / 2;
        int symbolSize = width / 4;
        
        // Draw simple symbol based on effect type
        for (int y = centerY - symbolSize; y <= centerY + symbolSize; ++y) {
            for (int x = centerX - symbolSize; x <= centerX + symbolSize; ++x) {
                if (x >= 0 && x < width && y >= 0 && y < height) {
                    int index = (y * width + x) * 4;
                    
                    // Simple symbol drawing (in a real implementation, this would use proper glyphs)
                    float dx = static_cast<float>(x - centerX) / symbolSize;
                    float dy = static_cast<float>(y - centerY) / symbolSize;
                    float dist = sqrt(dx*dx + dy*dy);
                    
                    if (dist <= 0.8f) {
                        pixels[index + 0] = static_cast<unsigned char>(s.iconColor.r * 255);
                        pixels[index + 1] = static_cast<unsigned char>(s.iconColor.g * 255);
                        pixels[index + 2] = static_cast<unsigned char>(s.iconColor.b * 255);
                        pixels[index + 3] = 255;
                    }
                }
            }
        }
        
        // Add flash overlay if requested
        if (u.flashOnApply) {
            Log::info("  - Adding flash overlay to icon");
        }
        
        Log::info("Icon created with handle: {}, size: {}x{}", 
                 nextIconHandle, width, height);
        return nextIconHandle++;
    }
}

// Factory implementation
StatusEffectFactory::StatusEffectFactory() : m_initialized(false) {
}

StatusEffectFactory::~StatusEffectFactory() {
    shutdown();
}

void StatusEffectFactory::initialize(size_t cache_size, size_t num_threads) {
    if (m_initialized) return;
    
    m_cache.set_capacity(cache_size);
    m_pool.start(num_threads);
    m_initialized = true;
    
    Log::info("StatusEffectFactory initialized with cache_size={}, threads={}", 
             cache_size, num_threads);
}

void StatusEffectFactory::shutdown() {
    if (!m_initialized) return;
    
    m_pool.stop();
    m_initialized = false;
    
    Log::info("StatusEffectFactory shutdown");
}

std::future<EffectBundle> StatusEffectFactory::generateAsync(const StatusEffectParams& s, const UIParams& u) {
    uint64_t key = s.hashKey() ^ (u.hashKey() << 1);
    
    if (auto found = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *found; });
    }
    
    return m_pool.enqueue([=]() {
        EffectBundle bundle;
        bundle.shader = ShaderGen::build(s);
        bundle.texture = TextureGen::build(s);
        bundle.mesh = MeshGen::build(s);
        bundle.particles = ParticleGen::build(s);
        bundle.icon = IconGen::build(s, u);
        
        m_cache.insert(key, bundle);
        return bundle;
    });
}

EffectBundle StatusEffectFactory::generateSync(const StatusEffectParams& s, const UIParams& u) {
    return generateAsync(s, u).get();
}

std::future<EffectBundle> StatusEffectFactory::generateFromJson(const std::string& effectJsonPath, const std::string& uiJsonPath) {
    return m_pool.enqueue([=]() {
        // Load effect params from JSON
        StatusEffectParams effectParams;
        std::ifstream effectFile(effectJsonPath);
        if (effectFile.is_open()) {
            // Parse JSON and populate effectParams
            Log::info("Loading effect params from: {}", effectJsonPath);
        }
        
        // Load UI params from JSON
        UIParams uiParams;
        std::ifstream uiFile(uiJsonPath);
        if (uiFile.is_open()) {
            // Parse JSON and populate uiParams
            Log::info("Loading UI params from: {}", uiJsonPath);
        }
        
        return generateSync(effectParams, uiParams);
    });
}

std::future<EffectBundle> StatusEffectFactory::generateFromParams(const StatusEffectParams& effectParams, const UIParams& uiParams) {
    return generateAsync(effectParams, uiParams);
}

std::vector<std::future<EffectBundle>> StatusEffectFactory::generateBatch(const std::vector<std::pair<StatusEffectParams, UIParams>>& params) {
    std::vector<std::future<EffectBundle>> futures;
    futures.reserve(params.size());
    
    for (const auto& param : params) {
        futures.push_back(generateAsync(param.first, param.second));
    }
    
    return futures;
}

void StatusEffectFactory::clearCache() {
    m_cache.clear();
    Log::info("StatusEffectFactory cache cleared");
}

size_t StatusEffectFactory::getCacheSize() const {
    return m_cache.size();
}

size_t StatusEffectFactory::getCacheCapacity() const {
    return m_cache.capacity();
}

bool StatusEffectFactory::validateEffectParams(const StatusEffectParams& params) {
    return params.duration > 0 && params.intensity >= 0 && params.intensity <= 1;
}

std::string StatusEffectFactory::getEffectValidationErrors(const StatusEffectParams& params) {
    std::string errors;
    
    if (params.duration <= 0) {
        errors += "Duration must be positive\n";
    }
    if (params.intensity < 0 || params.intensity > 1) {
        errors += "Intensity must be between 0 and 1\n";
    }
    if (params.particleCount < 0) {
        errors += "Particle count must be non-negative\n";
    }
    
    return errors;
}

bool StatusEffectFactory::validateUIParams(const UIParams& params) {
    return params.iconSize > 0 && params.iconSize <= 512;
}

std::string StatusEffectFactory::getUIValidationErrors(const UIParams& params) {
    std::string errors;
    
    if (params.iconSize <= 0 || params.iconSize > 512) {
        errors += "Icon size must be between 1 and 512\n";
    }
    
    return errors;
}

} // namespace StatusEffects
} // namespace MagiTech
