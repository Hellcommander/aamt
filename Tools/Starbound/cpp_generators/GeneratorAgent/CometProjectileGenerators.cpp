#include "CometProjectileFactory.hpp"
#include "CometProjectileTypes.hpp"
#include "CometProjectileAssets.hpp"
#include "core/Log.hpp"
#include "core/utils/ShaderBuilder.hpp"
#include <chrono>
#include <cmath>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>
#include <random>

namespace MagiTech {
namespace CometProjectiles {

using ParamUtils::cometTypeToString;
using ParamUtils::cometShapeToString;
using ParamUtils::trailTypeToString;
using ParamUtils::fragmentationTypeToString;
using ParamUtils::noiseTypeToString;
using ParamUtils::blendModeToString;

// Global factory instance
CometProjectileFactory g_cometFactory;

namespace MeshGen {
    MeshHandle buildCometCore(const CometProjectileParams& p) {
        Log::info("CometProjectile", "Building comet core mesh for: {} (type: {}, shape: {})", 
                  p.id, cometTypeToString(p.cometType), cometShapeToString(p.cometShape));
        
        // Generate base icosphere with appropriate detail level
        int detailLevel = 3;
        if (p.cometShape == CometShape::CRYSTALLINE) detailLevel = 4;
        if (p.cometShape == CometShape::FRAGMENTED) detailLevel = 5;
        
        auto baseMesh = generateIcoSphere(p.coreRadius, detailLevel);
        
        // Apply irregularity based on shape
        switch (p.cometShape) {
            case CometShape::SPHERE:
                // Keep as sphere, minimal irregularity
                if (p.irregularity > 0.1f) {
                    baseMesh = applyVertexNoise(baseMesh, p.irregularity * 0.3f);
                }
                break;
            case CometShape::IRREGULAR:
                baseMesh = applyVertexNoise(baseMesh, p.irregularity);
                break;
            case CometShape::FRAGMENTED:
                // Apply more aggressive noise for fragmented look
                baseMesh = applyVertexNoise(baseMesh, p.irregularity * 1.5f);
                // Add additional fragmentation noise
                baseMesh = applyVertexNoise(baseMesh, p.irregularity * 0.8f);
                break;
            case CometShape::CRYSTALLINE:
                // Apply crystalline noise pattern with sharp edges
                baseMesh = applyVertexNoise(baseMesh, p.irregularity * 0.8f);
                // Add crystalline structure
                baseMesh = applyCrystallineNoise(baseMesh, p.irregularity);
                break;
            case CometShape::CUSTOM_SHAPE:
                // Apply custom shape modifications
                baseMesh = applyVertexNoise(baseMesh, p.irregularity);
                break;
        }
        
        // Apply physics-based deformations
        if (p.enablePhysics) {
            baseMesh = applyPhysicsDeformation(baseMesh, p.mass, p.speed);
        }
        
        Log::info("Comet core mesh parameters:");
        Log::info("CometProjectile", "  - Core radius: {}", p.coreRadius);
        Log::info("CometProjectile", "  - Irregularity: {}", p.irregularity);
        Log::info("CometProjectile", "  - Mass: {}", p.mass);
        Log::info("CometProjectile", "  - Collision radius: {}", p.collisionRadius);
        Log::info("CometProjectile", "  - Detail level: {}", detailLevel);
        
        return baseMesh;
    }
    
    MeshHandle buildCometTrail(const CometProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No trail
        }
        
        Log::info("CometProjectile", "Building comet trail mesh for: {} (type: {}, length: {}, width: {})", 
                  p.id, trailTypeToString(p.trailType), p.trailLength, p.trailWidth);
        
        // Create ribbon mesh for trail with appropriate segments
        int segmentCount = static_cast<int>(p.trailLength * p.speed / 2.0f);
        segmentCount = std::max(8, std::min(64, segmentCount)); // Clamp between 8 and 64
        
        auto trailMesh = createRibbonMesh(p.trailLength, p.trailWidth, segmentCount);
        
        // Apply trail-specific modifications
        if (p.enableTrailDistortion) {
            trailMesh = applyTrailDistortion(trailMesh, p.trailDistortionStrength, p.trailNoiseScale, p.trailNoiseSpeed);
        }
        
        Log::info("Comet trail mesh parameters:");
        Log::info("CometProjectile", "  - Trail type: {}", trailTypeToString(p.trailType));
        Log::info("CometProjectile", "  - Trail length: {}", p.trailLength);
        Log::info("CometProjectile", "  - Trail width: {}", p.trailWidth);
        Log::info("CometProjectile", "  - Trail opacity: {}", p.trailOpacity);
        Log::info("CometProjectile", "  - Enable trail fade: {}", p.enableTrailFade);
        Log::info("CometProjectile", "  - Trail fade speed: {}", p.trailFadeSpeed);
        Log::info("CometProjectile", "  - Enable trail distortion: {}", p.enableTrailDistortion);
        Log::info("CometProjectile", "  - Trail distortion strength: {}", p.trailDistortionStrength);
        Log::info("CometProjectile", "  - Segment count: {}", segmentCount);
        
        return trailMesh;
    }
    
    MeshHandle generateIcoSphere(float radius, int detail) {
        Log::info("CometProjectile", "Generating icosphere: radius={}, detail={}", radius, detail);
        
        // Create icosphere using subdivision
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        
        // Generate icosphere geometry
        generateIcosphereGeometry(radius, detail, vertices, normals, uvs, indices);
        
        // Create mesh handle and upload to GPU
        MeshHandle handle = createMeshHandle();
        uploadMeshData(handle, vertices, normals, uvs, indices);
        
        Log::info("CometProjectile", "Generated icosphere with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle applyVertexNoise(MeshHandle mesh, float irregularity) {
        Log::info("CometProjectile", "Applying vertex noise: irregularity={}", irregularity);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply Perlin noise to vertices
        CometNoise noise;
        for (auto& vertex : vertices) {
            glm::vec3 noiseOffset = noise.perlinVec3(vertex * 2.0f) * irregularity;
            vertex += noiseOffset;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        Log::info("CometProjectile", "Applied vertex noise to {} vertices", vertices.size());
        
        return mesh;
    }
    
    MeshHandle applyCrystallineNoise(MeshHandle mesh, float irregularity) {
        Log::info("CometProjectile", "Applying crystalline noise: irregularity={}", irregularity);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply crystalline noise pattern
        CometNoise noise;
        for (auto& vertex : vertices) {
            // Create sharp crystalline structure
            glm::vec3 crystalNoise = noise.fractalVec3(vertex * 4.0f, 3) * irregularity * 0.5f;
            vertex += crystalNoise;
            
            // Add sharp edges
            glm::vec3 sharpNoise = noise.perlinVec3(vertex * 8.0f) * irregularity * 0.3f;
            vertex += sharpNoise;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        return mesh;
    }
    
    MeshHandle applyPhysicsDeformation(MeshHandle mesh, float mass, float speed) {
        Log::info("CometProjectile", "Applying physics deformation: mass={}, speed={}", mass, speed);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply physics-based deformations
        float deformationFactor = (mass * speed) / 100.0f; // Normalize
        
        if (normals.size() != vertices.size()) {
            recalculateNormals(vertices, indices, normals);
        }
        for (size_t i = 0; i < vertices.size(); ++i) {
            // Apply aerodynamic deformation
            float distanceFromCenter = glm::length(vertices[i]);
            float deformation = deformationFactor * (1.0f - distanceFromCenter);
            vertices[i] += normals[i] * deformation * 0.1f;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        return mesh;
    }
    
    MeshHandle createRibbonMesh(float length, float width, int segmentCount) {
        Log::info("CometProjectile", "Creating ribbon mesh: length={}, width={}, segments={}", length, width, segmentCount);
        
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        
        // Create ribbon geometry along velocity vector (width = trail width)
        if (segmentCount < 1) segmentCount = 1;

        for (int i = 0; i <= segmentCount; ++i) {
            float t = static_cast<float>(i) / segmentCount;
            float z = t * length;
            
            // Create ribbon cross-section
            for (int j = 0; j <= 4; ++j) { // 4 segments for ribbon width
                float u = static_cast<float>(j) / 4.0f;
                float x = (u - 0.5f) * width;
                float y = 0.0f;
                
                vertices.emplace_back(x, y, z);
                normals.emplace_back(0.0f, 1.0f, 0.0f);
                uvs.emplace_back(u, t);
            }
        }
        
        // Generate indices for ribbon
        for (int i = 0; i < segmentCount; ++i) {
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
        
        Log::info("CometProjectile", "Created ribbon mesh with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle applyTrailDistortion(MeshHandle mesh, float strength, float scale, float speed) {
        Log::info("CometProjectile", "Applying trail distortion: strength={}, scale={}, speed={}", strength, scale, speed);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply curl noise for trail distortion
        CometNoise noise;
        for (auto& vertex : vertices) {
            glm::vec3 curl = noise.curl3D(vertex * scale) * strength;
            vertex += curl;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        return mesh;
    }
    
    MeshHandle buildFragments(const CometProjectileParams& p) {
        if (p.fragmentationCount <= 0) {
            return 0; // No fragments
        }
        
        Log::info("CometProjectile", "Building comet fragments for: {} (count: {}, size factor: {})", 
                  p.id, p.fragmentationCount, p.fragmentSizeFactor);
        
        // Create fragment meshes
        std::vector<glm::vec3> allVertices;
        std::vector<glm::vec3> allNormals;
        std::vector<glm::vec2> allUVs;
        std::vector<uint32_t> allIndices;
        
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> sizeDist(0.5f, 1.5f);
        std::uniform_real_distribution<float> posDist(-p.fragmentSpread, p.fragmentSpread);
        
        uint32_t vertexOffset = 0;
        
        for (int i = 0; i < p.fragmentationCount; ++i) {
            // Generate fragment geometry
            float fragmentSize = p.coreRadius * p.fragmentSizeFactor * sizeDist(gen);
            auto fragmentMesh = generateIcoSphere(fragmentSize, 2);
            
            // Get fragment data
            std::vector<glm::vec3> vertices, normals;
            std::vector<glm::vec2> uvs;
            std::vector<uint32_t> indices;
            downloadMeshData(fragmentMesh, vertices, normals, uvs, indices);
            
            // Apply fragment-specific noise
            for (auto& vertex : vertices) {
                vertex += glm::vec3(posDist(gen), posDist(gen), posDist(gen)) * 0.1f;
            }
            
            // Add to combined mesh
            for (const auto& vertex : vertices) {
                allVertices.push_back(vertex);
            }
            for (const auto& normal : normals) {
                allNormals.push_back(normal);
            }
            for (const auto& uv : uvs) {
                allUVs.push_back(uv);
            }
            for (const auto& index : indices) {
                allIndices.push_back(index + vertexOffset);
            }
            
            vertexOffset += vertices.size();
            
            // Clean up individual fragment mesh
            destroyMeshHandle(fragmentMesh);
        }
        
        // Create combined fragment mesh
        MeshHandle handle = createMeshHandle();
        uploadMeshData(handle, allVertices, allNormals, allUVs, allIndices);
        
        Log::info("Fragment parameters:");
        Log::info("CometProjectile", "  - Fragmentation type: {}", fragmentationTypeToString(p.fragmentationType));
        Log::info("CometProjectile", "  - Fragment count: {}", p.fragmentationCount);
        Log::info("CometProjectile", "  - Fragment size factor: {}", p.fragmentSizeFactor);
        Log::info("CometProjectile", "  - Fragment spread: {}", p.fragmentSpread);
        Log::info("CometProjectile", "  - Fragment velocity: {}", p.fragmentVelocity);
        Log::info("CometProjectile", "  - Enable fragment physics: {}", p.enableFragmentPhysics);
        Log::info("CometProjectile", "  - Fragment lifetime: {}", p.fragmentLifetime);
        Log::info("CometProjectile", "  - Total fragment vertices: {}", allVertices.size());
        
        return handle;
    }
}

namespace ShaderGen {
    ShaderHandle buildCometShader(const CometProjectileParams& p) {
        Log::info("CometProjectile", "Building comet shader for: {} (blend: {}, noise: {})", 
                  p.id, blendModeToString(p.blendMode), noiseTypeToString(p.noiseType));
        
        // Create shader based on parameters
        std::string shaderCode = generateCometShaderCode(p);
        
        // Compile shader with parameters
        ShaderBuilder builder;
        builder.setVertexShader(generateCometVertexShader(p));
        builder.setFragmentShader(shaderCode);
        builder.addUniform("uGlowIntensity", p.glowIntensity);
        builder.addUniform("uEmissivePower", p.emissivePower);
        builder.addUniform("uNoiseScale", p.trailNoiseScale);
        builder.addUniform("uNoiseSpeed", p.trailNoiseSpeed);
        builder.addUniform("uTrailOpacity", p.trailOpacity);
        builder.addUniform("uCoreOpacity", p.coreOpacity);
        builder.addUniform("uHeatColor", p.heatColor);
        builder.addUniform("uBurnColor", p.burnColor);
        builder.addUniform("uCoreColor", p.coreColor);
        builder.addUniform("uGlowColor", p.glowColor);
        
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
        
        ShaderHandle handle = builder.compile();
        
        Log::info("Compiling comet shader with parameters:");
        Log::info("CometProjectile", "  - Shader type: {}", p.shaderType);
        Log::info("CometProjectile", "  - Shader intensity: {}", p.shaderIntensity);
        Log::info("CometProjectile", "  - Glow intensity: {}", p.glowIntensity);
        Log::info("CometProjectile", "  - Emissive power: {}", p.emissivePower);
        Log::info("CometProjectile", "  - Core opacity: {}", p.coreOpacity);
        Log::info("CometProjectile", "  - Trail opacity: {}", p.trailOpacity);
        Log::info("CometProjectile", "  - Enable core glow: {}", p.enableCoreGlow);
        Log::info("CometProjectile", "  - Enable trail glow: {}", p.enableTrailGlow);
        Log::info("CometProjectile", "  - Enable distortion: {}", p.enableDistortion);
        Log::info("CometProjectile", "  - Distortion strength: {}", p.distortionStrength);
        Log::info("CometProjectile", "  - Enable blur: {}", p.enableBlur);
        Log::info("CometProjectile", "  - Blur strength: {}", p.blurStrength);
        
        return handle;
    }
    
    ShaderHandle buildHeatDistortion(const CometProjectileParams& p) {
        if (!p.enableHeatDistortion) {
            return 0; // No heat distortion
        }
        
        Log::info("CometProjectile", "Building heat distortion shader for: {} (strength: {})", 
                  p.id, p.heatDistortionStrength);
        
        ShaderBuilder builder;
        builder.setVertexShader(generateHeatDistortionVertexShader(p));
        builder.setFragmentShader(generateHeatDistortionFragmentShader(p));
        builder.addUniform("uHeatDistortionStrength", p.heatDistortionStrength);
        builder.addUniform("uNoiseScale", p.trailNoiseScale);
        builder.addUniform("uNoiseSpeed", p.trailNoiseSpeed);
        builder.enableFeature("HEAT_DISTORTION");
        
        ShaderHandle handle = builder.compile();
        
        return handle;
    }
    
    std::string generateCometShaderCode(const CometProjectileParams& p) {
        std::stringstream ss;
        ss << "// Comet shader for: " << p.id << "\n";
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
        ss << "uniform vec3 uHeatColor;\n";
        ss << "uniform vec3 uBurnColor;\n";
        ss << "uniform vec3 uCoreColor;\n";
        ss << "uniform vec3 uGlowColor;\n";
        ss << "uniform float uGlowIntensity;\n";
        ss << "uniform float uEmissivePower;\n";
        ss << "uniform float uNoiseScale;\n";
        ss << "uniform float uNoiseSpeed;\n";
        ss << "uniform float uTrailOpacity;\n";
        ss << "uniform float uCoreOpacity;\n";
        
        if (p.enableDistortion) {
            ss << "uniform float uDistortionStrength;\n";
        }
        if (p.enableBlur) {
            ss << "uniform float uBlurStrength;\n";
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
        ss << "    vec3 baseColor = mix(uCoreColor, uHeatColor, 0.5);\n";
        ss << "    vec3 glowColor = uGlowColor * uGlowIntensity;\n";
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
            ss << "    baseColor = mix(baseColor, uBurnColor, trailFactor * 0.3);\n";
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
    
    std::string generateCometVertexShader(const CometProjectileParams& p) {
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
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vPosition = (uModel * vec4(aPosition, 1.0)).xyz;\n";
        ss << "    vNormal = uNormalMatrix * aNormal;\n";
        ss << "    vTexCoord = aTexCoord;\n";
        ss << "    gl_Position = uModelViewProjection * vec4(aPosition, 1.0);\n";
        ss << "}\n";
        
        return ss.str();
    }
    
    std::string generateHeatDistortionVertexShader(const CometProjectileParams& p) {
        std::stringstream ss;
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec2 aPosition;\n";
        ss << "layout(location = 1) in vec2 aTexCoord;\n";
        ss << "\n";
        ss << "layout(location = 0) out vec2 vTexCoord;\n";
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vTexCoord = aTexCoord;\n";
        ss << "    gl_Position = vec4(aPosition, 0.0, 1.0);\n";
        ss << "}\n";
        
        return ss.str();
    }
    
    std::string generateHeatDistortionFragmentShader(const CometProjectileParams& p) {
        std::stringstream ss;
        ss << "#version 450\n";
        ss << "layout(location = 0) in vec2 vTexCoord;\n";
        ss << "layout(location = 0) out vec4 fragColor;\n";
        ss << "\n";
        ss << "uniform sampler2D uMainTexture;\n";
        ss << "uniform float uHeatDistortionStrength;\n";
        ss << "uniform float uNoiseScale;\n";
        ss << "uniform float uNoiseSpeed;\n";
        ss << "uniform float uTime;\n";
        ss << "\n";
        ss << "float noise(vec2 p) {\n";
        ss << "    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);\n";
        ss << "}\n";
        ss << "\n";
        ss << "void main() {\n";
        ss << "    vec2 distortedCoord = vTexCoord;\n";
        ss << "    \n";
        ss << "    // Apply heat distortion\n";
        ss << "    vec2 noiseCoord = vTexCoord * uNoiseScale + uTime * uNoiseSpeed;\n";
        ss << "    vec2 distortion = vec2(noise(noiseCoord), noise(noiseCoord + vec2(1.0, 1.0))) * 2.0 - 1.0;\n";
        ss << "    distortedCoord += distortion * uHeatDistortionStrength;\n";
        ss << "    \n";
        ss << "    fragColor = texture(uMainTexture, distortedCoord);\n";
        ss << "}\n";
        
        return ss.str();
    }
}

namespace TextureGen {
    TextureHandle buildCometTexture(const CometProjectileParams& p) {
        Log::info("CometProjectile", "Building comet texture for: {} (noise: {}, heat: ({},{},{}), burn: ({},{},{}))", 
                  p.id, noiseTypeToString(p.noiseType),
                  p.heatColor.x, p.heatColor.y, p.heatColor.z,
                  p.burnColor.x, p.burnColor.y, p.burnColor.z);
        
        // Generate rock texture
        TextureHandle rockTex = buildRockTexture(4.0f);
        
        // Generate color map
        TextureHandle colorTex = buildColorMap(p.heatColor, p.burnColor);
        
        // Merge textures
        TextureHandle finalTex = mergeTextures(rockTex, colorTex);
        
        // Apply additional effects based on comet type
        switch (p.cometType) {
            case CometType::METEOR:
                finalTex = applyMeteorEffects(finalTex, p);
                break;
            case CometType::COMET:
                finalTex = applyCometEffects(finalTex, p);
                break;
            case CometType::ASTEROID:
                finalTex = applyAsteroidEffects(finalTex, p);
                break;
            case CometType::FALLING_STAR:
                finalTex = applyFallingStarEffects(finalTex, p);
                break;
            case CometType::CELESTIAL_ROCK:
                finalTex = applyCelestialRockEffects(finalTex, p);
                break;
            default:
                break;
        }
        
        return finalTex;
    }
    
    TextureHandle buildRockTexture(float frequency) {
        Log::info("CometProjectile", "Building rock texture: frequency={}", frequency);
        
        const int width = 512;
        const int height = 512;
        std::vector<uint8_t> data(width * height * 4);
        
        CometNoise noise;

        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float nx = static_cast<float>(x) / width;
                float ny = static_cast<float>(y) / height;
                
                // Generate 3D noise for rock texture
                glm::vec3 pos(nx * frequency, ny * frequency, 0.0f);
                float noiseValue = noise.perlin3D(pos);
                
                // Create rock-like pattern
                float rockValue = (noiseValue + 1.0f) * 0.5f;
                uint8_t value = static_cast<uint8_t>(rockValue * 255.0f);
                
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
    
    TextureHandle buildColorMap(const glm::vec3& heatColor, const glm::vec3& burnColor) {
        Log::info("CometProjectile", "Building color map: heat=({},{},{}), burn=({},{},{})", 
                  heatColor.x, heatColor.y, heatColor.z,
                  burnColor.x, burnColor.y, burnColor.z);
        
        const int width = 256;
        const int height = 256;
        std::vector<uint8_t> data(width * height * 4);
        
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                float nx = static_cast<float>(x) / width;
                float ny = static_cast<float>(y) / height;
                
                // Create radial gradient from heat to burn color
                float distance = glm::length(glm::vec2(nx - 0.5f, ny - 0.5f));
                float t = glm::clamp(distance * 2.0f, 0.0f, 1.0f);
                
                glm::vec3 color = glm::mix(heatColor, burnColor, t);
                
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
    
    TextureHandle mergeTextures(const TextureHandle& rock, const TextureHandle& color) {
        Log::info("CometProjectile", "Merging rock texture {} with color map {}", rock, color);

        auto rockData = getTextureData(rock);
        auto colorData = getTextureData(color);
        if (!colorData || colorData->rgba.empty()) return rock;
        if (!rockData || rockData->rgba.empty()) return color;

        // Output at the larger resolution; both inputs are sampled with nearest filtering.
        const int width = std::max(rockData->width, colorData->width);
        const int height = std::max(rockData->height, colorData->height);
        std::vector<uint8_t> data(static_cast<size_t>(width) * height * 4);

        auto sample = [](const CometTextureData& tex, float u, float v, int channel) -> float {
            const int x = std::clamp(static_cast<int>(u * tex.width), 0, tex.width - 1);
            const int y = std::clamp(static_cast<int>(v * tex.height), 0, tex.height - 1);
            return tex.rgba[(static_cast<size_t>(y) * tex.width + x) * 4 + channel] / 255.0f;
        };

        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                const float u = (x + 0.5f) / width;
                const float v = (y + 0.5f) / height;
                // Rock luminance modulates the heat/burn colour (kept above 35% so colour survives)
                const float rockLum = sample(*rockData, u, v, 0);
                const float shade = 0.35f + 0.65f * rockLum;
                const size_t index = (static_cast<size_t>(y) * width + x) * 4;
                for (int c = 0; c < 3; ++c) {
                    data[index + c] = static_cast<uint8_t>(std::clamp(sample(*colorData, u, v, c) * shade, 0.0f, 1.0f) * 255.0f);
                }
                data[index + 3] = static_cast<uint8_t>(sample(*colorData, u, v, 3) * 255.0f);
            }
        }

        TextureHandle handle = createTextureHandle();
        uploadTextureData(handle, width, height, data.data(), colorData->generateMipmaps || rockData->generateMipmaps);
        return handle;
    }

    namespace {
        // Rewrites every texel through `fn(u, v, rgb, alpha)` into a new texture handle.
        template <typename Fn>
        TextureHandle transformTexture(TextureHandle texture, Fn&& fn) {
            auto tex = getTextureData(texture);
            if (!tex || tex->rgba.empty()) return texture;
            std::vector<uint8_t> data = tex->rgba;
            for (int y = 0; y < tex->height; ++y) {
                for (int x = 0; x < tex->width; ++x) {
                    const size_t index = (static_cast<size_t>(y) * tex->width + x) * 4;
                    glm::vec3 rgb(data[index] / 255.0f, data[index + 1] / 255.0f, data[index + 2] / 255.0f);
                    float alpha = data[index + 3] / 255.0f;
                    fn((x + 0.5f) / tex->width, (y + 0.5f) / tex->height, rgb, alpha);
                    rgb = glm::clamp(rgb, glm::vec3(0.0f), glm::vec3(1.0f));
                    data[index + 0] = static_cast<uint8_t>(rgb.r * 255.0f);
                    data[index + 1] = static_cast<uint8_t>(rgb.g * 255.0f);
                    data[index + 2] = static_cast<uint8_t>(rgb.b * 255.0f);
                    data[index + 3] = static_cast<uint8_t>(std::clamp(alpha, 0.0f, 1.0f) * 255.0f);
                }
            }
            TextureHandle handle = createTextureHandle();
            uploadTextureData(handle, tex->width, tex->height, data.data(), tex->generateMipmaps);
            return handle;
        }

        float radialDistance(float u, float v) {
            return glm::length(glm::vec2(u - 0.5f, v - 0.5f)) * 2.0f; // 0 centre, 1 edge
        }
    }

    TextureHandle applyMeteorEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying meteor effects to texture");
        // Molten centre glowing in the heat colour, charred rim.
        const glm::vec3 heat = p.heatColor * (0.5f + 0.5f * std::min(p.emissivePower, 2.0f));
        return transformTexture(texture, [&](float u, float v, glm::vec3& rgb, float&) {
            const float d = radialDistance(u, v);
            const float glow = std::pow(std::max(0.0f, 1.0f - d), 2.0f);
            rgb = glm::mix(rgb * (1.0f - 0.4f * d), heat, glow * 0.6f);
        });
    }

    TextureHandle applyCometEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying comet effects to texture");
        // Icy coma: brighten and cool the outer region, keep the nucleus in the core colour.
        const glm::vec3 ice(0.7f, 0.85f, 1.0f);
        return transformTexture(texture, [&](float u, float v, glm::vec3& rgb, float& alpha) {
            const float d = radialDistance(u, v);
            rgb = glm::mix(glm::mix(rgb, p.coreColor, 0.25f), ice, glm::smoothstep(0.4f, 1.0f, d) * 0.5f);
            alpha *= glm::mix(1.0f, p.coreOpacity, glm::smoothstep(0.6f, 1.0f, d));
        });
    }

    TextureHandle applyAsteroidEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying asteroid effects to texture");
        // Cold rock: mostly desaturated with craters darkened by noise.
        CometNoise noise(static_cast<int>(p.hashKey() & 0x7fffffff));
        return transformTexture(texture, [&](float u, float v, glm::vec3& rgb, float&) {
            const float grey = glm::dot(rgb, glm::vec3(0.299f, 0.587f, 0.114f));
            rgb = glm::mix(rgb, glm::vec3(grey), 0.75f);
            const float crater = noise.perlin3D(glm::vec3(u * 12.0f, v * 12.0f, 0.5f));
            if (crater > 0.35f) rgb *= 1.0f - (crater - 0.35f) * 1.2f;
        });
    }

    TextureHandle applyFallingStarEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying falling star effects to texture");
        // Bright, glowing body pushed towards the glow colour.
        const float boost = 1.0f + 0.25f * std::min(p.glowIntensity, 4.0f);
        return transformTexture(texture, [&](float u, float v, glm::vec3& rgb, float&) {
            const float d = radialDistance(u, v);
            rgb = glm::mix(rgb * boost, p.glowColor, std::max(0.0f, 1.0f - d) * 0.5f);
        });
    }

    TextureHandle applyCelestialRockEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying celestial rock effects to texture");
        // Dark stone with scattered glints in the glow colour.
        CometNoise noise(static_cast<int>((p.hashKey() >> 7) & 0x7fffffff));
        return transformTexture(texture, [&](float u, float v, glm::vec3& rgb, float&) {
            rgb *= 0.75f;
            const float glint = noise.perlin3D(glm::vec3(u * 48.0f, v * 48.0f, 1.5f));
            if (glint > 0.55f) rgb = glm::mix(rgb, p.glowColor, (glint - 0.55f) / 0.45f);
        });
    }
}

namespace ParticleGen {
    ParticleHandle buildDustTrail(const CometProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No dust trail
        }
        
        Log::info("CometProjectile", "Building dust trail particles for: {} (count: {}, lifetime: {}, size: {})", 
                  p.id, p.dustParticleCount, p.dustLifetime, p.dustSize);
        
        // Create particle emitter description
        ParticleEmitterDesc desc;
        desc.type = ParticleType::BILLBOARD;
        desc.rate = p.dustParticleCount;
        desc.lifetime = p.dustLifetime;
        desc.startColor = p.dustColor;
        desc.endColor = glm::vec4(p.dustColor.x, p.dustColor.y, p.dustColor.z, 0.0f);
        desc.startSize = p.dustSize;
        desc.endSize = p.dustSize * 2.0f;
        desc.velocity = glm::vec3(-p.speed * 0.2f, 0.0f, 0.0f);
        desc.velocityVariation = p.dustSpeed;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.gravityInfluence, 0.0f);
        desc.enableFade = p.enableDustFade;
        desc.fadeSpeed = p.dustFadeSpeed;
        
        // Create particle emitter
        ParticleHandle handle = createParticleEmitter(desc);
        
        Log::info("Dust trail particle parameters:");
        Log::info("CometProjectile", "  - Count: {}", p.dustParticleCount);
        Log::info("CometProjectile", "  - Lifetime: {}", p.dustLifetime);
        Log::info("CometProjectile", "  - Size: {}", p.dustSize);
        Log::info("CometProjectile", "  - Speed: {}", p.dustSpeed);
        Log::info("CometProjectile", "  - Color: ({},{},{},{})", 
                  p.dustColor.x, p.dustColor.y, p.dustColor.z, p.dustColor.w);
        Log::info("CometProjectile", "  - Enable fade: {}", p.enableDustFade);
        Log::info("CometProjectile", "  - Fade speed: {}", p.dustFadeSpeed);
        
        return handle;
    }
    
    ParticleHandle buildSparks(const CometProjectileParams& p) {
        Log::info("CometProjectile", "Building spark particles for: {} (count: {}, lifetime: {}, size: {})", 
                  p.id, p.sparkParticleCount, p.sparkLifetime, p.sparkSize);
        
        // Create particle emitter description
        ParticleEmitterDesc desc;
        desc.type = ParticleType::POINT;
        desc.rate = p.sparkParticleCount;
        desc.lifetime = p.sparkLifetime;
        desc.startColor = p.sparkColor;
        desc.endColor = glm::vec4(p.sparkColor.x, p.sparkColor.y, p.sparkColor.z, 0.0f);
        desc.startSize = p.sparkSize;
        desc.endSize = p.sparkSize * 0.5f;
        desc.velocity = glm::vec3(0.0f, 0.0f, 0.0f);
        desc.velocityVariation = p.sparkSpeed;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.gravityInfluence * 0.5f, 0.0f);
        desc.enableFade = p.enableSparkFade;
        desc.fadeSpeed = p.sparkFadeSpeed;
        
        // Create particle emitter
        ParticleHandle handle = createParticleEmitter(desc);
        
        Log::info("Spark particle parameters:");
        Log::info("CometProjectile", "  - Count: {}", p.sparkParticleCount);
        Log::info("CometProjectile", "  - Lifetime: {}", p.sparkLifetime);
        Log::info("CometProjectile", "  - Size: {}", p.sparkSize);
        Log::info("CometProjectile", "  - Speed: {}", p.sparkSpeed);
        Log::info("CometProjectile", "  - Color: ({},{},{},{})", 
                  p.sparkColor.x, p.sparkColor.y, p.sparkColor.z, p.sparkColor.w);
        Log::info("CometProjectile", "  - Enable fade: {}", p.enableSparkFade);
        Log::info("CometProjectile", "  - Fade speed: {}", p.sparkFadeSpeed);
        
        return handle;
    }
    
    ParticleHandle buildFragments(const CometProjectileParams& p) {
        if (p.fragmentationCount <= 0) {
            return 0; // No fragments
        }
        
        Log::info("CometProjectile", "Building fragment particles for: {} (count: {}, lifetime: {})", 
                  p.id, p.fragmentationCount, p.fragmentLifetime);
        
        // Create particle emitter description for fragments
        ParticleEmitterDesc desc;
        desc.type = ParticleType::MESH;
        desc.rate = p.fragmentationCount;
        desc.lifetime = p.fragmentLifetime;
        desc.startColor = glm::vec4(p.coreColor, p.coreOpacity);
        desc.endColor = glm::vec4(p.coreColor, 0.0f);
        desc.startSize = p.coreRadius * p.fragmentSizeFactor;
        desc.endSize = p.coreRadius * p.fragmentSizeFactor * 0.5f;
        desc.velocity = glm::vec3(0.0f, 0.0f, 0.0f);
        desc.velocityVariation = p.fragmentVelocity;
        desc.gravity = glm::vec3(0.0f, -9.81f * p.gravityInfluence, 0.0f);
        desc.enablePhysics = p.enableFragmentPhysics;
        desc.spread = p.fragmentSpread;
        
        // Create particle emitter
        ParticleHandle handle = createParticleEmitter(desc);
        
        Log::info("Fragment particle parameters:");
        Log::info("CometProjectile", "  - Count: {}", p.fragmentationCount);
        Log::info("CometProjectile", "  - Size factor: {}", p.fragmentSizeFactor);
        Log::info("CometProjectile", "  - Spread: {}", p.fragmentSpread);
        Log::info("CometProjectile", "  - Velocity: {}", p.fragmentVelocity);
        Log::info("CometProjectile", "  - Lifetime: {}", p.fragmentLifetime);
        Log::info("CometProjectile", "  - Enable physics: {}", p.enableFragmentPhysics);
        
        return handle;
    }
}

CometAssetBundle buildCometAssetBundle(const CometProjectileParams& p) {
    const auto start = std::chrono::steady_clock::now();

    CometAssetBundle b{};
    b.mesh = MeshGen::buildCometCore(p);
    b.texture = TextureGen::buildCometTexture(p);
    b.shader = ShaderGen::buildCometShader(p);
    b.dustTrail = ParticleGen::buildDustTrail(p);
    b.sparks = ParticleGen::buildSparks(p);
    b.fragments = ParticleGen::buildFragments(p);
    b.heatDistortion = ShaderGen::buildHeatDistortion(p);

    // Performance metrics
    if (auto mesh = getMeshData(b.mesh)) {
        b.vertexCount = mesh->vertices.size();
        b.triangleCount = mesh->indices.size() / 3;
    }
    b.particleCount = static_cast<size_t>(std::max(0, p.dustParticleCount) + std::max(0, p.sparkParticleCount) +
                                          std::max(0, p.fragmentationCount));
    b.gpuAccelerated = p.enableParallelProcessing;
    b.generationTime = std::chrono::duration<float>(std::chrono::steady_clock::now() - start).count();
    return b;
}

CometProjectileParams loadCometParamsFromJsonFile(const std::string& jsonPath) {
    std::ifstream file(jsonPath);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open comet parameter file: " + jsonPath);
    }
    nlohmann::json json = nlohmann::json::parse(file); // throws on malformed JSON
    return ParamUtils::fromJson(json);
}

} // namespace CometProjectiles
} // namespace MagiTech
