#include "LightningProjectileFactory.hpp"
#include "LightningProjectileTypes.hpp"
#include "LightningProjectileParams.cpp"
#include "core/Log.hpp"
#include "core/utils/NoiseGenerator.hpp"
#include "core/utils/MeshBuilder.hpp"
#include "core/utils/ShaderBuilder.hpp"
#include "core/utils/TextureBuilder.hpp"
#include "core/utils/ParticleBuilder.hpp"
#include "core/utils/AudioBuilder.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>
#include <random>
#include <cmath>

namespace MagiTech {
namespace LightningProjectiles {

// Global factory instance
LightningProjectileFactory g_lightningFactory;

namespace MeshGen {
    MeshHandle buildLightning(const LightningProjectileParams& p) {
        Log::info("Building lightning mesh for: {} (type: {}, length: {}, thickness: {})", 
                  p.id, lightningTypeToString(p.lightningType), p.length, p.thickness);
        
        // Generate main arc points
        int segments = static_cast<int>(p.arcSegments);
        auto arcPoints = generateArcPoints(p.length, segments, p.noiseScale, p.noiseIntensity);
        
        // Apply jitter if enabled
        if (p.enableJitter) {
            applyJitter(arcPoints, p.jitterAmplitude, p.jitterFrequency);
        }
        
        // Build main arc mesh
        auto mainArcMesh = buildPolylineRibbon(arcPoints, p.thickness, p.arcWidthVariation);
        
        // Build branches if enabled
        std::vector<MeshHandle> meshes = {mainArcMesh};
        if (p.enableBranching && p.branchCount > 0) {
            auto branchMesh = buildLightningBranches(p);
            if (branchMesh != 0) {
                meshes.push_back(branchMesh);
            }
        }
        
        // Build trail if enabled
        if (p.trailType != TrailType::NONE) {
            auto trailMesh = buildLightningTrail(p);
            if (trailMesh != 0) {
                meshes.push_back(trailMesh);
            }
        }
        
        // Merge all meshes
        MeshHandle finalMesh = mergeMeshes(meshes);
        
        Log::info("Lightning mesh parameters:");
        Log::info("  - Lightning type: {}", lightningTypeToString(p.lightningType));
        Log::info("  - Length: {}", p.length);
        Log::info("  - Thickness: {}", p.thickness);
        Log::info("  - Arc segments: {}", segments);
        Log::info("  - Noise intensity: {}", p.noiseIntensity);
        Log::info("  - Noise scale: {}", p.noiseScale);
        Log::info("  - Enable jitter: {}", p.enableJitter);
        Log::info("  - Jitter amplitude: {}", p.jitterAmplitude);
        Log::info("  - Jitter frequency: {}", p.jitterFrequency);
        Log::info("  - Arc width variation: {}", p.arcWidthVariation);
        Log::info("  - Enable branching: {}", p.enableBranching);
        Log::info("  - Branch count: {}", p.branchCount);
        Log::info("  - Trail type: {}", trailTypeToString(p.trailType));
        
        return finalMesh;
    }
    
    MeshHandle buildLightningArc(const LightningProjectileParams& p) {
        Log::info("Building lightning arc for: {}", p.id);
        
        // Generate arc points with appropriate segments
        int segments = static_cast<int>(p.arcSegments);
        auto arcPoints = generateArcPoints(p.length, segments, p.noiseScale, p.noiseIntensity);
        
        // Apply jitter if enabled
        if (p.enableJitter) {
            applyJitter(arcPoints, p.jitterAmplitude, p.jitterFrequency);
        }
        
        // Build polyline ribbon
        return buildPolylineRibbon(arcPoints, p.thickness, p.arcWidthVariation);
    }
    
    MeshHandle buildLightningBranches(const LightningProjectileParams& p) {
        if (p.branchCount <= 0) {
            return 0; // No branches
        }
        
        Log::info("Building lightning branches for: {} (count: {}, length factor: {})", 
                  p.id, p.branchCount, p.branchLengthFactor);
        
        // Generate main arc points for branch attachment
        int segments = static_cast<int>(p.arcSegments);
        auto mainArcPoints = generateArcPoints(p.length, segments, p.noiseScale, p.noiseIntensity);
        
        std::vector<MeshHandle> branchMeshes;
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> angleDist(-p.branchAngle, p.branchAngle);
        std::uniform_real_distribution<float> lengthDist(0.3f, 1.0f);
        
        for (int i = 0; i < p.branchCount; ++i) {
            // Select random point on main arc for branch attachment
            int attachmentPoint = std::uniform_int_distribution<int>(1, mainArcPoints.size() - 2)(gen);
            glm::vec3 attachmentPos = mainArcPoints[attachmentPoint];
            
            // Generate branch direction
            float branchAngle = angleDist(gen);
            float branchLength = p.length * p.branchLengthFactor * lengthDist(gen);
            
            // Generate branch points
            auto branchPoints = generateArcPoints(branchLength, segments / 2, p.noiseScale * 1.5f, p.noiseIntensity * 0.8f);
            
            // Transform branch points to attach to main arc
            glm::vec3 direction = glm::normalize(mainArcPoints[attachmentPoint + 1] - mainArcPoints[attachmentPoint - 1]);
            glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
            glm::vec3 right = glm::normalize(glm::cross(direction, up));
            
            for (auto& point : branchPoints) {
                // Rotate and translate branch point
                glm::mat4 transform = glm::translate(glm::mat4(1.0f), attachmentPos) *
                                    glm::rotate(glm::mat4(1.0f), branchAngle, up) *
                                    glm::translate(glm::mat4(1.0f), point);
                point = glm::vec3(transform * glm::vec4(point, 1.0f));
            }
            
            // Build branch mesh
            auto branchMesh = buildPolylineRibbon(branchPoints, p.thickness * 0.6f, p.arcWidthVariation * 0.8f);
            if (branchMesh != 0) {
                branchMeshes.push_back(branchMesh);
            }
        }
        
        // Merge all branch meshes
        if (branchMeshes.empty()) {
            return 0;
        }
        
        return mergeMeshes(branchMeshes);
    }
    
    MeshHandle buildLightningTrail(const LightningProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No trail
        }
        
        Log::info("Building lightning trail for: {} (type: {}, length: {})", 
                  p.id, trailTypeToString(p.trailType), p.trailLength);
        
        // Generate trail points based on main arc
        int segments = static_cast<int>(p.arcSegments);
        auto arcPoints = generateArcPoints(p.length, segments, p.noiseScale, p.noiseIntensity);
        
        // Apply jitter if enabled
        if (p.enableJitter) {
            applyJitter(arcPoints, p.jitterAmplitude, p.jitterFrequency);
        }
        
        // Build trail ribbon
        return buildTrailRibbon(arcPoints, p.trailLength, p.trailWidth);
    }
    
    std::vector<glm::vec3> generateArcPoints(float length, int segments, float noiseScale, float noiseIntensity) {
        std::vector<glm::vec3> points;
        points.reserve(segments + 1);
        
        NoiseGenerator noise;
        
        for (int i = 0; i <= segments; ++i) {
            float t = static_cast<float>(i) / segments;
            float z = t * length;
            
            // Generate noise-based displacement
            glm::vec3 noisePos = glm::vec3(t * noiseScale, 0.0f, z * noiseScale);
            float noiseX = noise.perlin3D(noisePos).x * noiseIntensity;
            float noiseY = noise.perlin3D(noisePos + glm::vec3(100.0f)).y * noiseIntensity;
            
            // Create arc point with noise displacement
            glm::vec3 point = glm::vec3(noiseX, noiseY, z);
            points.push_back(point);
        }
        
        return points;
    }
    
    void applyJitter(std::vector<glm::vec3>& points, float amplitude, float frequency) {
        NoiseGenerator noise;
        
        for (auto& point : points) {
            // Apply temporal jitter based on position
            glm::vec3 jitterPos = point * frequency;
            glm::vec3 jitter = noise.perlin3D(jitterPos) * amplitude;
            point += jitter;
        }
    }
    
    MeshHandle buildPolylineRibbon(const std::vector<glm::vec3>& points, float thickness, float widthVariation) {
        if (points.size() < 2) {
            return 0; // Need at least 2 points
        }
        
        Log::info("Building polyline ribbon: {} points, thickness: {}, width variation: {}", 
                  points.size(), thickness, widthVariation);
        
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        
        NoiseGenerator noise;
        
        for (size_t i = 0; i < points.size(); ++i) {
            glm::vec3 current = points[i];
            glm::vec3 next = (i + 1 < points.size()) ? points[i + 1] : current;
            glm::vec3 prev = (i > 0) ? points[i - 1] : current;
            
            // Calculate direction
            glm::vec3 direction = glm::normalize(next - prev);
            glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
            glm::vec3 right = glm::normalize(glm::cross(direction, up));
            
            // Calculate width variation
            float width = thickness;
            if (widthVariation > 0.0f) {
                float variation = noise.perlin1D(static_cast<float>(i) * 0.5f) * widthVariation;
                width += variation;
            }
            
            // Create ribbon cross-section
            for (int j = 0; j <= 4; ++j) { // 4 segments for ribbon width
                float u = static_cast<float>(j) / 4.0f;
                float v = static_cast<float>(i) / (points.size() - 1);
                
                glm::vec3 offset = right * (u - 0.5f) * width;
                glm::vec3 vertex = current + offset;
                
                vertices.push_back(vertex);
                normals.push_back(glm::normalize(offset));
                uvs.emplace_back(u, v);
            }
        }
        
        // Generate indices for ribbon
        for (size_t i = 0; i < points.size() - 1; ++i) {
            for (int j = 0; j < 4; ++j) {
                uint32_t base = i * 5 + j;
                
                // First triangle
                indices.push_back(base);
                indices.push_back(base + 1);
                indices.push_back(base + 5);
                
                // Second triangle
                indices.push_back(base + 1);
                indices.push_back(base + 6);
                indices.push_back(base + 5);
            }
        }
        
        // Create mesh handle and upload to GPU
        MeshHandle handle = createMeshHandle();
        uploadMeshData(handle, vertices, normals, uvs, indices);
        
        Log::info("Created polyline ribbon with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle buildTrailRibbon(const std::vector<glm::vec3>& points, float trailLength, float thickness) {
        if (points.size() < 2) {
            return 0; // Need at least 2 points
        }
        
        Log::info("Building trail ribbon: {} points, trail length: {}, thickness: {}", 
                  points.size(), trailLength, thickness);
        
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        
        // Create trail ribbon that follows the arc but with fade effect
        for (size_t i = 0; i < points.size(); ++i) {
            glm::vec3 current = points[i];
            glm::vec3 next = (i + 1 < points.size()) ? points[i + 1] : current;
            glm::vec3 prev = (i > 0) ? points[i - 1] : current;
            
            // Calculate direction
            glm::vec3 direction = glm::normalize(next - prev);
            glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f);
            glm::vec3 right = glm::normalize(glm::cross(direction, up));
            
            // Calculate fade factor based on position
            float fadeFactor = 1.0f - static_cast<float>(i) / points.size();
            float width = thickness * fadeFactor;
            
            // Create trail cross-section
            for (int j = 0; j <= 4; ++j) {
                float u = static_cast<float>(j) / 4.0f;
                float v = static_cast<float>(i) / (points.size() - 1);
                
                glm::vec3 offset = right * (u - 0.5f) * width;
                glm::vec3 vertex = current + offset;
                
                vertices.push_back(vertex);
                normals.push_back(glm::normalize(offset));
                uvs.emplace_back(u, v);
            }
        }
        
        // Generate indices for trail ribbon
        for (size_t i = 0; i < points.size() - 1; ++i) {
            for (int j = 0; j < 4; ++j) {
                uint32_t base = i * 5 + j;
                
                // First triangle
                indices.push_back(base);
                indices.push_back(base + 1);
                indices.push_back(base + 5);
                
                // Second triangle
                indices.push_back(base + 1);
                indices.push_back(base + 6);
                indices.push_back(base + 5);
            }
        }
        
        // Create mesh handle and upload to GPU
        MeshHandle handle = createMeshHandle();
        uploadMeshData(handle, vertices, normals, uvs, indices);
        
        Log::info("Created trail ribbon with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle mergeMeshes(const std::vector<MeshHandle>& meshes) {
        if (meshes.empty()) {
            return 0;
        }
        
        if (meshes.size() == 1) {
            return meshes[0];
        }
        
        Log::info("Merging {} lightning meshes", meshes.size());
        
        // In a real implementation, this would combine multiple meshes
        // For now, return the first mesh as a placeholder
        return meshes[0];
    }
}

namespace ShaderGen {
    ShaderHandle buildLightning(const LightningProjectileParams& p) {
        Log::info("Building lightning shader for: {} (blend: {}, noise: {})", 
                  p.id, blendModeToString(p.blendMode), noiseTypeToString(p.noiseType));
        
        // Create shader based on parameters
        std::string shaderCode = generateLightningShaderCode(p);
        
        // Compile shader with parameters
        ShaderBuilder builder;
        builder.setVertexShader(buildLightningVertexShader(p));
        builder.setFragmentShader(shaderCode);
        builder.addUniform("uMainColor", p.mainColor);
        builder.addUniform("uGlowColor", p.glowColor);
        builder.addUniform("uCoreColor", p.coreColor);
        builder.addUniform("uNoiseScale", p.noiseScale);
        builder.addUniform("uFlickerSpeed", p.flickerSpeed);
        builder.addUniform("uPulseFrequency", p.pulseFrequency);
        builder.addUniform("uGlowIntensity", p.glowIntensity);
        builder.addUniform("uEmissivePower", p.emissivePower);
        builder.addUniform("uCoreOpacity", p.coreOpacity);
        builder.addUniform("uTrailOpacity", p.trailOpacity);
        
        // Set blend mode
        switch (p.blendMode) {
            case BlendMode::ADDITIVE:
                builder.enableAdditiveBlend();
                break;
            case BlendMode::MULTIPLY:
                builder.enableMultiplyBlend();
                break;
            case BlendMode::SCREEN:
                builder.enableScreenBlend();
                break;
            case BlendMode::OVERLAY:
                builder.enableOverlayBlend();
                break;
            case BlendMode::NORMAL:
                builder.enableNormalBlend();
                break;
        }
        
        // Enable features based on parameters
        if (p.enableCoreGlow) {
            builder.enableFeature("CORE_GLOW");
        }
        if (p.enableTrailGlow) {
            builder.enableFeature("TRAIL_GLOW");
        }
        if (p.enableDistortion) {
            builder.enableFeature("DISTORTION");
            builder.addUniform("uDistortionStrength", p.distortionStrength);
        }
        if (p.enableBlur) {
            builder.enableFeature("BLUR");
            builder.addUniform("uBlurStrength", p.blurStrength);
        }
        if (p.enableHeatDistortion) {
            builder.enableFeature("HEAT_DISTORTION");
            builder.addUniform("uHeatDistortionStrength", p.heatDistortionStrength);
        }
        
        ShaderHandle handle = builder.compile();
        
        Log::info("Compiling lightning shader with parameters:");
        Log::info("  - Shader type: {}", p.shaderType);
        Log::info("  - Shader intensity: {}", p.shaderIntensity);
        Log::info("  - Glow intensity: {}", p.glowIntensity);
        Log::info("  - Emissive power: {}", p.emissivePower);
        Log::info("  - Core opacity: {}", p.coreOpacity);
        Log::info("  - Trail opacity: {}", p.trailOpacity);
        Log::info("  - Enable core glow: {}", p.enableCoreGlow);
        Log::info("  - Enable trail glow: {}", p.enableTrailGlow);
        Log::info("  - Enable distortion: {}", p.enableDistortion);
        Log::info("  - Distortion strength: {}", p.distortionStrength);
        Log::info("  - Enable blur: {}", p.enableBlur);
        Log::info("  - Blur strength: {}", p.blurStrength);
        Log::info("  - Enable heat distortion: {}", p.enableHeatDistortion);
        Log::info("  - Heat distortion strength: {}", p.heatDistortionStrength);
        
        return handle;
    }
    
    ShaderHandle buildLightningVertexShader(const LightningProjectileParams& p) {
        std::stringstream ss;
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec3 aPosition;\n";
        ss << "layout(location = 1) in vec3 aNormal;\n";
        ss << "layout(location = 2) in vec2 aTexCoord;\n";
        ss << "\n";
        ss << "layout(location = 0) out vec3 vPosition;\n";
        ss << "layout(location = 1) out vec3 vNormal;\n";
        ss << "layout(location = 2) out vec2 vTexCoord;\n";
        ss << "\n";
        ss << "uniform mat4 uModelViewProjection;\n";
        ss << "uniform mat4 uModel;\n";
        ss << "uniform mat3 uNormalMatrix;\n";
        ss << "uniform float uTime;\n";
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vPosition = (uModel * vec4(aPosition, 1.0)).xyz;\n";
        ss << "    vNormal = uNormalMatrix * aNormal;\n";
        ss << "    vTexCoord = aTexCoord;\n";
        ss << "    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);\n";
        ss << "}\n";
        
        return ShaderBuilder().setVertexShader(ss.str()).compile();
    }
    
    std::string generateLightningShaderCode(const LightningProjectileParams& p) {
        std::stringstream ss;
        ss << "// Lightning shader for: " << p.id << "\n";
        ss << "// Generated with parameters:\n";
        ss << "// - Blend mode: " << blendModeToString(p.blendMode) << "\n";
        ss << "// - Noise type: " << noiseTypeToString(p.noiseType) << "\n";
        ss << "// - Glow intensity: " << p.glowIntensity << "\n";
        ss << "// - Emissive power: " << p.emissivePower << "\n";
        ss << "\n";
        
        // Fragment shader code
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec3 vPosition;\n";
        ss << "layout(location = 1) in vec3 vNormal;\n";
        ss << "layout(location = 2) in vec2 vTexCoord;\n";
        ss << "\n";
        ss << "layout(location = 0) out vec4 fragColor;\n";
        ss << "\n";
        ss << "// Uniforms\n";
        ss << "uniform vec3 uMainColor;\n";
        ss << "uniform vec3 uGlowColor;\n";
        ss << "uniform vec3 uCoreColor;\n";
        ss << "uniform float uNoiseScale;\n";
        ss << "uniform float uFlickerSpeed;\n";
        ss << "uniform float uPulseFrequency;\n";
        ss << "uniform float uGlowIntensity;\n";
        ss << "uniform float uEmissivePower;\n";
        ss << "uniform float uCoreOpacity;\n";
        ss << "uniform float uTrailOpacity;\n";
        ss << "uniform float uTime;\n";
        
        if (p.enableDistortion) {
            ss << "uniform float uDistortionStrength;\n";
        }
        if (p.enableBlur) {
            ss << "uniform float uBlurStrength;\n";
        }
        if (p.enableHeatDistortion) {
            ss << "uniform float uHeatDistortionStrength;\n";
        }
        
        ss << "\n";
        ss << "// Noise functions\n";
        ss << "float noise(vec3 p) {\n";
        ss << "    return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);\n";
        ss << "}\n";
        ss << "\n";
        ss << "vec3 curlNoise(vec3 p) {\n";
        ss << "    float n = noise(p * uNoiseScale);\n";
        ss << "    return vec3(n, noise(p + vec3(1.0)), noise(p + vec3(2.0)));\n";
        ss << "}\n";
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vec3 position = vPosition;\n";
        ss << "    vec3 normal = normalize(vNormal);\n";
        ss << "    vec2 texCoord = vTexCoord;\n";
        ss << "\n";
        
        // Apply distortion if enabled
        if (p.enableDistortion) {
            ss << "    // Apply distortion\n";
            ss << "    vec3 distortion = curlNoise(position * uNoiseScale) * uDistortionStrength;\n";
            ss << "    position += distortion;\n";
            ss << "    normal = normalize(normal + distortion * 0.1);\n";
            ss << "\n";
        }
        
        // Calculate base color
        ss << "    // Calculate base color\n";
        ss << "    vec3 baseColor = mix(uCoreColor, uMainColor, 0.5);\n";
        ss << "    vec3 glowColor = uGlowColor * uGlowIntensity;\n";
        ss << "\n";
        
        // Apply flicker effect
        ss << "    // Apply flicker effect\n";
        ss << "    float flicker = noise(vec3(uTime * uFlickerSpeed, 0.0, 0.0));\n";
        ss << "    baseColor *= (0.8 + 0.4 * flicker);\n";
        ss << "\n";
        
        // Apply pulse effect
        ss << "    // Apply pulse effect\n";
        ss << "    float pulse = sin(uTime * uPulseFrequency) * 0.5 + 0.5;\n";
        ss << "    baseColor *= (0.7 + 0.6 * pulse);\n";
        ss << "\n";
        
        // Apply emissive glow
        if (p.enableCoreGlow) {
            ss << "    // Apply core glow\n";
            ss << "    float glowFactor = pow(max(0.0, dot(normal, vec3(0.0, 0.0, 1.0)), 2.0);\n";
            ss << "    baseColor += glowColor * glowFactor * uEmissivePower;\n";
            ss << "\n";
        }
        
        // Apply trail effects
        if (p.trailType != TrailType::NONE) {
            ss << "    // Apply trail effects\n";
            ss << "    float trailFactor = smoothstep(0.0, 1.0, texCoord.x);\n";
            ss << "    baseColor = mix(baseColor, uGlowColor, trailFactor * 0.3);\n";
            ss << "\n";
        }
        
        // Final color calculation
        ss << "    // Final color\n";
        ss << "    vec3 finalColor = baseColor;\n";
        ss << "    float alpha = uCoreOpacity;\n";
        ss << "\n";
        
        // Apply opacity based on trail
        if (p.trailType != TrailType::NONE) {
            ss << "    // Trail opacity\n";
            ss << "    alpha = mix(uCoreOpacity, uTrailOpacity, smoothstep(0.0, 1.0, texCoord.x));\n";
            ss << "\n";
        }
        
        ss << "    fragColor = vec4(finalColor, alpha);\n";
        ss << "}\n";
        
        return ss.str();
    }
}

namespace TextureGen {
    TextureHandle buildLightning(const LightningProjectileParams& p) {
        Log::info("Building lightning texture for: {} (noise: {}, main: ({},{},{}), glow: ({},{},{}))", 
                  p.id, noiseTypeToString(p.noiseType),
                  p.mainColor.x, p.mainColor.y, p.mainColor.z,
                  p.glowColor.x, p.glowColor.y, p.glowColor.z);
        
        // Generate lightning gradient
        TextureHandle gradientTex = buildLightningGradient(p.mainColor, p.glowColor);
        
        // Generate lightning noise
        TextureHandle noiseTex = buildLightningNoise(p.noiseScale, p.flickerSpeed);
        
        // Merge textures
        return mergeLightningTextures(gradientTex, noiseTex);
    }
    
    TextureHandle buildLightningGradient(const glm::vec3& mainColor, const glm::vec3& glowColor) {
        Log::info("Building lightning gradient: main=({},{},{}), glow=({},{},{})", 
                  mainColor.x, mainColor.y, mainColor.z,
                  glowColor.x, glowColor.y, glowColor.z);
        
        const int width = 256;
        const int height = 256;
        std::vector<uint8_t> data(width * height * 4);
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float nx = static_cast<float>(x) / width;
                float ny = static_cast<float>(y) / height;
                
                // Create radial gradient from main color to glow color
                float distance = glm::length(glm::vec2(nx - 0.5f, ny - 0.5f));
                float t = glm::clamp(distance * 2.0f, 0.0f, 1.0f);
                
                glm::vec3 color = glm::mix(mainColor, glowColor, t);
                
                int index = (y * width + x) * 4;
                data[index + 0] = static_cast<uint8_t>(color.x * 255.0f); // R
                data[index + 1] = static_cast<uint8_t>(color.y * 255.0f); // G
                data[index + 2] = static_cast<uint8_t>(color.z * 255.0f); // B
                data[index + 3] = 255; // A
            }
        }
        
        TextureHandle handle = createTextureHandle();
        uploadTextureData(handle, width, height, data.data(), true);
        
        return handle;
    }
    
    TextureHandle buildLightningNoise(float noiseScale, float flickerSpeed) {
        Log::info("Building lightning noise: scale={}, flicker={}", noiseScale, flickerSpeed);
        
        const int width = 256;
        const int height = 256;
        std::vector<uint8_t> data(width * height * 4);
        
        NoiseGenerator noise;
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float nx = static_cast<float>(x) / width;
                float ny = static_cast<float>(y) / height;
                
                // Generate 2D noise for lightning texture
                glm::vec2 pos(nx * noiseScale, ny * noiseScale);
                float noiseValue = noise.perlin2D(pos);
                
                // Create lightning-like pattern
                float lightningValue = (noiseValue + 1.0f) * 0.5f;
                uint8_t value = static_cast<uint8_t>(lightningValue * 255.0f);
                
                int index = (y * width + x) * 4;
                data[index + 0] = value; // R
                data[index + 1] = value; // G
                data[index + 2] = value; // B
                data[index + 3] = 255;   // A
            }
        }
        
        TextureHandle handle = createTextureHandle();
        uploadTextureData(handle, width, height, data.data(), true);
        
        return handle;
    }
    
    TextureHandle mergeLightningTextures(const TextureHandle& gradient, const TextureHandle& noise) {
        Log::info("Merging lightning gradient and noise textures");
        
        // In a real implementation, this would blend the textures
        // For now, return the gradient texture as the merged result
        return gradient;
    }
}

namespace ParticleGen {
    ParticleHandle buildSparks(const LightningProjectileParams& p) {
        Log::info("Building spark particles for: {} (count: {}, lifetime: {}, size: {})", 
                  p.id, p.sparkCount, p.sparkLifetime, p.sparkSize);
        
        // Create particle emitter description
        ParticleEmitterDesc desc;
        desc.type = ParticleType::POINT;
        desc.rate = p.sparkCount;
        desc.lifetime = p.sparkLifetime;
        desc.startColor = p.sparkColor;
        desc.endColor = glm::vec4(p.sparkColor.x, p.sparkColor.y, p.sparkColor.z, 0.0f);
        desc.startSize = p.sparkSize;
        desc.endSize = p.sparkSize * 0.5f;
        desc.velocity = glm::vec3(0.0f, 0.0f, 0.0f);
        desc.velocityVariation = p.sparkSpeed;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.sparkGravity, 0.0f);
        desc.enableFade = p.enableSparkFade;
        desc.fadeSpeed = p.sparkFadeSpeed;
        desc.enablePhysics = p.enableSparkPhysics;
        
        // Create particle emitter
        ParticleHandle handle = createParticleEmitter(desc);
        
        Log::info("Spark particle parameters:");
        Log::info("  - Count: {}", p.sparkCount);
        Log::info("  - Lifetime: {}", p.sparkLifetime);
        Log::info("  - Size: {}", p.sparkSize);
        Log::info("  - Speed: {}", p.sparkSpeed);
        Log::info("  - Color: ({},{},{},{})", 
                  p.sparkColor.x, p.sparkColor.y, p.sparkColor.z, p.sparkColor.w);
        Log::info("  - Enable fade: {}", p.enableSparkFade);
        Log::info("  - Fade speed: {}", p.sparkFadeSpeed);
        Log::info("  - Enable physics: {}", p.enableSparkPhysics);
        Log::info("  - Gravity: {}", p.sparkGravity);
        
        return handle;
    }
    
    ParticleHandle buildLightningParticles(const LightningProjectileParams& p) {
        Log::info("Building lightning particles for: {}", p.id);
        
        // Create specialized lightning particle emitter
        ParticleEmitterDesc desc;
        desc.type = ParticleType::BILLBOARD;
        desc.rate = p.sparkCount * 2; // More particles for lightning effect
        desc.lifetime = p.sparkLifetime * 0.5f; // Shorter lifetime for lightning
        desc.startColor = p.mainColor;
        desc.endColor = glm::vec4(p.glowColor.x, p.glowColor.y, p.glowColor.z, 0.0f);
        desc.startSize = p.sparkSize * 2.0f;
        desc.endSize = p.sparkSize * 0.1f;
        desc.velocity = glm::vec3(0.0f, 0.0f, 0.0f);
        desc.velocityVariation = p.sparkSpeed * 2.0f;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.sparkGravity * 0.5f, 0.0f);
        desc.enableFade = true;
        desc.fadeSpeed = p.sparkFadeSpeed * 2.0f;
        desc.enablePhysics = p.enableSparkPhysics;
        
        return createParticleEmitter(desc);
    }
    
    ParticleHandle buildElectricTrail(const LightningProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No electric trail
        }
        
        Log::info("Building electric trail particles for: {}", p.id);
        
        // Create electric trail particle emitter
        ParticleEmitterDesc desc;
        desc.type = ParticleType::BILLBOARD;
        desc.rate = p.sparkCount / 2; // Fewer particles for trail
        desc.lifetime = p.sparkLifetime * 1.5f; // Longer lifetime for trail
        desc.startColor = p.trailColor;
        desc.endColor = glm::vec4(p.trailColor.x, p.trailColor.y, p.trailColor.z, 0.0f);
        desc.startSize = p.sparkSize * 1.5f;
        desc.endSize = p.sparkSize * 0.2f;
        desc.velocity = glm::vec3(-p.speed * 0.1f, 0.0f, 0.0f);
        desc.velocityVariation = p.sparkSpeed * 0.5f;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.sparkGravity * 0.3f, 0.0f);
        desc.enableFade = true;
        desc.fadeSpeed = p.sparkFadeSpeed * 0.8f;
        desc.enablePhysics = p.enableSparkPhysics;
        
        return createParticleEmitter(desc);
    }
}

namespace AudioGen {
    AudioHandle buildCrackle(const LightningProjectileParams& p) {
        Log::info("Building crackle audio for: {} (pitch: {}, volume: {}, duration: {})", 
                  p.id, p.soundPitch, p.soundVolume, p.soundDuration);
        
        // Create procedural audio description
        ProceduralAudioDesc desc;
        desc.type = ProceduralAudioType::CRACKLE;
        desc.duration = p.soundDuration;
        desc.pitch = p.soundPitch;
        desc.volume = p.soundVolume;
        desc.intensity = p.branchCount; // Use branch count for intensity
        desc.enableSpatialAudio = p.enableSpatialAudio;
        desc.distance = p.audioDistance;
        
        // Create audio handle
        AudioHandle handle = createProceduralAudio(desc);
        
        Log::info("Crackle audio parameters:");
        Log::info("  - Audio type: {}", audioTypeToString(p.audioType));
        Log::info("  - Pitch: {}", p.soundPitch);
        Log::info("  - Volume: {}", p.soundVolume);
        Log::info("  - Duration: {}", p.soundDuration);
        Log::info("  - Enable audio: {}", p.enableAudio);
        Log::info("  - Enable spatial audio: {}", p.enableSpatialAudio);
        Log::info("  - Audio distance: {}", p.audioDistance);
        
        return handle;
    }
    
    AudioHandle buildLightningAudio(const LightningProjectileParams& p) {
        Log::info("Building lightning audio for: {}", p.id);
        
        // Create specialized lightning audio
        ProceduralAudioDesc desc;
        desc.type = ProceduralAudioType::ELECTRIC;
        desc.duration = p.soundDuration;
        desc.pitch = p.soundPitch;
        desc.volume = p.soundVolume;
        desc.intensity = p.charge; // Use charge for intensity
        desc.enableSpatialAudio = p.enableSpatialAudio;
        desc.distance = p.audioDistance;
        
        return createProceduralAudio(desc);
    }
    
    AudioHandle buildElectricSound(const LightningProjectileParams& p) {
        Log::info("Building electric sound for: {}", p.id);
        
        // Create electric sound effect
        ProceduralAudioDesc desc;
        desc.type = ProceduralAudioType::ZAP;
        desc.duration = p.soundDuration * 0.5f; // Shorter duration for electric sound
        desc.pitch = p.soundPitch * 1.2f; // Higher pitch for electric sound
        desc.volume = p.soundVolume * 0.8f; // Lower volume for electric sound
        desc.intensity = p.conductivity; // Use conductivity for intensity
        desc.enableSpatialAudio = p.enableSpatialAudio;
        desc.distance = p.audioDistance;
        
        return createProceduralAudio(desc);
    }
}

} // namespace LightningProjectiles
} // namespace MagiTech
