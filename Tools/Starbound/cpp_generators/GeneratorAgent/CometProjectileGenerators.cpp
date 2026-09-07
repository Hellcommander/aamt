#include "CometProjectileFactory.hpp"
#include "CometProjectileTypes.hpp"
#include "CometProjectileParams.cpp"
#include "core/Log.hpp"
#include "core/utils/NoiseGenerator.hpp"
#include "core/utils/MeshBuilder.hpp"
#include "core/utils/ShaderBuilder.hpp"
#include "core/utils/TextureBuilder.hpp"
#include "core/utils/ParticleBuilder.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <stdexcept>
#include <random>

namespace MagiTech {
namespace CometProjectiles {

// Global factory instance
CometProjectileFactory g_cometFactory;

namespace MeshGen {
    MeshHandle buildCometCore(const CometProjectileParams& p) {
        Log::info("Building comet core mesh for: {} (type: {}, shape: {})", 
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
        Log::info("  - Core radius: {}", p.coreRadius);
        Log::info("  - Irregularity: {}", p.irregularity);
        Log::info("  - Mass: {}", p.mass);
        Log::info("  - Collision radius: {}", p.collisionRadius);
        Log::info("  - Detail level: {}", detailLevel);
        
        return baseMesh;
    }
    
    MeshHandle buildCometTrail(const CometProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No trail
        }
        
        Log::info("Building comet trail mesh for: {} (type: {}, length: {}, width: {})", 
                  p.id, trailTypeToString(p.trailType), p.trailLength, p.trailWidth);
        
        // Create ribbon mesh for trail with appropriate segments
        int segmentCount = static_cast<int>(p.trailLength * p.speed / 2.0f);
        segmentCount = std::max(8, std::min(64, segmentCount)); // Clamp between 8 and 64
        
        auto trailMesh = createRibbonMesh(p.trailLength, p.speed, segmentCount);
        
        // Apply trail-specific modifications
        if (p.enableTrailDistortion) {
            trailMesh = applyTrailDistortion(trailMesh, p.trailDistortionStrength, p.trailNoiseScale, p.trailNoiseSpeed);
        }
        
        Log::info("Comet trail mesh parameters:");
        Log::info("  - Trail type: {}", trailTypeToString(p.trailType));
        Log::info("  - Trail length: {}", p.trailLength);
        Log::info("  - Trail width: {}", p.trailWidth);
        Log::info("  - Trail opacity: {}", p.trailOpacity);
        Log::info("  - Enable trail fade: {}", p.enableTrailFade);
        Log::info("  - Trail fade speed: {}", p.trailFadeSpeed);
        Log::info("  - Enable trail distortion: {}", p.enableTrailDistortion);
        Log::info("  - Trail distortion strength: {}", p.trailDistortionStrength);
        Log::info("  - Segment count: {}", segmentCount);
        
        return trailMesh;
    }
    
    MeshHandle generateIcoSphere(float radius, int detail) {
        Log::info("Generating icosphere: radius={}, detail={}", radius, detail);
        
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
        
        Log::info("Generated icosphere with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle applyVertexNoise(MeshHandle mesh, float irregularity) {
        Log::info("Applying vertex noise: irregularity={}", irregularity);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply Perlin noise to vertices
        NoiseGenerator noise;
        for (auto& vertex : vertices) {
            glm::vec3 noiseOffset = noise.perlin3D(vertex * 2.0f) * irregularity;
            vertex += noiseOffset;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        Log::info("Applied vertex noise to {} vertices", vertices.size());
        
        return mesh;
    }
    
    MeshHandle applyCrystallineNoise(MeshHandle mesh, float irregularity) {
        Log::info("Applying crystalline noise: irregularity={}", irregularity);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply crystalline noise pattern
        NoiseGenerator noise;
        for (auto& vertex : vertices) {
            // Create sharp crystalline structure
            glm::vec3 crystalNoise = noise.fractal3D(vertex * 4.0f, 3) * irregularity * 0.5f;
            vertex += crystalNoise;
            
            // Add sharp edges
            glm::vec3 sharpNoise = noise.perlin3D(vertex * 8.0f) * irregularity * 0.3f;
            vertex += sharpNoise;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        return mesh;
    }
    
    MeshHandle applyPhysicsDeformation(MeshHandle mesh, float mass, float speed) {
        Log::info("Applying physics deformation: mass={}, speed={}", mass, speed);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply physics-based deformations
        float deformationFactor = (mass * speed) / 100.0f; // Normalize
        
        for (auto& vertex : vertices) {
            // Apply aerodynamic deformation
            float distanceFromCenter = glm::length(vertex);
            float deformation = deformationFactor * (1.0f - distanceFromCenter);
            vertex += normals[&vertex - &vertices[0]] * deformation * 0.1f;
        }
        
        // Recalculate normals
        recalculateNormals(vertices, indices, normals);
        
        // Upload modified mesh data
        uploadMeshData(mesh, vertices, normals, uvs, indices);
        
        return mesh;
    }
    
    MeshHandle createRibbonMesh(float length, float speed, int segmentCount) {
        Log::info("Creating ribbon mesh: length={}, speed={}, segments={}", length, speed, segmentCount);
        
        std::vector<glm::vec3> vertices;
        std::vector<glm::vec3> normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        
        // Create ribbon geometry along velocity vector
        float segmentLength = length / segmentCount;
        float width = 0.1f; // Default width
        
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
        
        Log::info("Created ribbon mesh with {} vertices, {} triangles", vertices.size(), indices.size() / 3);
        
        return handle;
    }
    
    MeshHandle applyTrailDistortion(MeshHandle mesh, float strength, float scale, float speed) {
        Log::info("Applying trail distortion: strength={}, scale={}, speed={}", strength, scale, speed);
        
        // Get mesh data
        std::vector<glm::vec3> vertices, normals;
        std::vector<glm::vec2> uvs;
        std::vector<uint32_t> indices;
        downloadMeshData(mesh, vertices, normals, uvs, indices);
        
        // Apply curl noise for trail distortion
        NoiseGenerator noise;
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
        
        Log::info("Building comet fragments for: {} (count: {}, size factor: {})", 
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
        Log::info("  - Fragmentation type: {}", fragmentationTypeToString(p.fragmentationType));
        Log::info("  - Fragment count: {}", p.fragmentationCount);
        Log::info("  - Fragment size factor: {}", p.fragmentSizeFactor);
        Log::info("  - Fragment spread: {}", p.fragmentSpread);
        Log::info("  - Fragment velocity: {}", p.fragmentVelocity);
        Log::info("  - Enable fragment physics: {}", p.enableFragmentPhysics);
        Log::info("  - Fragment lifetime: {}", p.fragmentLifetime);
        Log::info("  - Total fragment vertices: {}", allVertices.size());
        
        return handle;
    }
}

namespace ShaderGen {
    ShaderHandle buildCometShader(const CometProjectileParams& p) {
        Log::info("Building comet shader for: {} (blend: {}, noise: {})", 
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
        
        return handle;
    }
    
    ShaderHandle buildHeatDistortion(const CometProjectileParams& p) {
        if (!p.enableHeatDistortion) {
            return 0; // No heat distortion
        }
        
        Log::info("Building heat distortion shader for: {} (strength: {})", 
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
        Log::info("Building comet texture for: {} (noise: {}, heat: ({},{},{}), burn: ({},{},{}))", 
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
        Log::info("Building rock texture: frequency={}", frequency);
        
        const int width = 512;
        const int height = 512;
        std::vector<uint8_t> data(width * height * 4);
        
        NoiseGenerator noise;
        
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
        Log::info("Building color map: heat=({},{},{}), burn=({},{},{})", 
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
        Log::info("Merging rock and color textures");
        
        // In a real implementation, this would blend the textures
        // For now, return the color texture as the merged result
        return color;
    }
    
    TextureHandle applyMeteorEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying meteor effects to texture");
        // Apply meteor-specific texture effects
        return texture;
    }
    
    TextureHandle applyCometEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying comet effects to texture");
        // Apply comet-specific texture effects
        return texture;
    }
    
    TextureHandle applyAsteroidEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying asteroid effects to texture");
        // Apply asteroid-specific texture effects
        return texture;
    }
    
    TextureHandle applyFallingStarEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying falling star effects to texture");
        // Apply falling star-specific texture effects
        return texture;
    }
    
    TextureHandle applyCelestialRockEffects(TextureHandle texture, const CometProjectileParams& p) {
        Log::info("Applying celestial rock effects to texture");
        // Apply celestial rock-specific texture effects
        return texture;
    }
}

namespace ParticleGen {
    ParticleHandle buildDustTrail(const CometProjectileParams& p) {
        if (p.trailType == TrailType::NONE) {
            return 0; // No dust trail
        }
        
        Log::info("Building dust trail particles for: {} (count: {}, lifetime: {}, size: {})", 
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
        Log::info("  - Count: {}", p.dustParticleCount);
        Log::info("  - Lifetime: {}", p.dustLifetime);
        Log::info("  - Size: {}", p.dustSize);
        Log::info("  - Speed: {}", p.dustSpeed);
        Log::info("  - Color: ({},{},{},{})", 
                  p.dustColor.x, p.dustColor.y, p.dustColor.z, p.dustColor.w);
        Log::info("  - Enable fade: {}", p.enableDustFade);
        Log::info("  - Fade speed: {}", p.dustFadeSpeed);
        
        return handle;
    }
    
    ParticleHandle buildSparks(const CometProjectileParams& p) {
        Log::info("Building spark particles for: {} (count: {}, lifetime: {}, size: {})", 
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
        Log::info("  - Count: {}", p.sparkParticleCount);
        Log::info("  - Lifetime: {}", p.sparkLifetime);
        Log::info("  - Size: {}", p.sparkSize);
        Log::info("  - Speed: {}", p.sparkSpeed);
        Log::info("  - Color: ({},{},{},{})", 
                  p.sparkColor.x, p.sparkColor.y, p.sparkColor.z, p.sparkColor.w);
        Log::info("  - Enable fade: {}", p.enableSparkFade);
        Log::info("  - Fade speed: {}", p.sparkFadeSpeed);
        
        return handle;
    }
    
    ParticleHandle buildFragments(const CometProjectileParams& p) {
        if (p.fragmentationCount <= 0) {
            return 0; // No fragments
        }
        
        Log::info("Building fragment particles for: {} (count: {}, lifetime: {})", 
                  p.id, p.fragmentationCount, p.fragmentLifetime);
        
        // Create particle emitter description for fragments
        ParticleEmitterDesc desc;
        desc.type = ParticleType::MESH;
        desc.rate = p.fragmentationCount;
        desc.lifetime = p.fragmentLifetime;
        desc.startColor = p.coreColor;
        desc.endColor = glm::vec4(p.coreColor.x, p.coreColor.y, p.coreColor.z, 0.0f);
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
        Log::info("  - Count: {}", p.fragmentationCount);
        Log::info("  - Size factor: {}", p.fragmentSizeFactor);
        Log::info("  - Spread: {}", p.fragmentSpread);
        Log::info("  - Velocity: {}", p.fragmentVelocity);
        Log::info("  - Lifetime: {}", p.fragmentLifetime);
        Log::info("  - Enable physics: {}", p.enableFragmentPhysics);
        
        return handle;
    }
}

} // namespace CometProjectiles
} // namespace MagiTech
