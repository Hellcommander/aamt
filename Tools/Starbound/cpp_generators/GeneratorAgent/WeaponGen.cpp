#include "WeaponGen.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <random>
#include <chrono>
#include <filesystem>
#include <fstream>

namespace MagiTech {
namespace Audio {

// Constants
constexpr float PI = 3.14159265359f;
constexpr float TWO_PI = 2.0f * PI;
constexpr size_t DEFAULT_BUFFER_SIZE = 1024;
constexpr float DEFAULT_LOD_REDUCTION = 0.5f;
constexpr size_t MAX_LOD_LEVELS = 4;

// WeaponGen Implementation
WeaponGen::WeaponGen() 
    : m_gpuAccelerationEnabled(false)
    , m_processingQuality(1)
    , m_lodReduction(DEFAULT_LOD_REDUCTION)
    , m_enablePhysics(true)
    , m_maxProcessingThreads(4)
    , m_lastError("") {
    
    // Initialize with default settings
    m_enableHotReload = true;
    m_enableCaching = true;
    m_enableParallelProcessing = true;
    
    // Initialize weapon part generators
    initializeWeaponGenerators();
}

WeaponGen::~WeaponGen() = default;

AudioBundle WeaponGen::process(const WeaponParams& params) {
    try {
        AudioBundle bundle;
        bundle.meta.id = "weapon_" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        bundle.meta.duration = 0.0f;
        bundle.meta.loop = false;
        
        // Load weapon definition if provided
        WeaponDefinition weaponDef;
        if (!params.weaponDefinitionPath.empty()) {
            weaponDef = loadWeaponDefinition(params.weaponDefinitionPath);
        } else {
            weaponDef = createDefaultWeaponDefinition(params);
        }
        
        // Process weapon pipeline
        WeaponResult result = processWeaponPipeline(weaponDef, params);
        
        // Set the processed data (use first audio asset for compatibility)
        if (!result.audioAssets.empty()) {
            bundle.buffer = result.audioAssets[0].audioData;
            bundle.meta.duration = static_cast<float>(result.audioAssets[0].audioData.size()) / (result.audioAssets[0].sampleRate * result.audioAssets[0].numChannels);
        }
        
        // Calculate quality metrics
        if (!bundle.buffer.empty()) {
            bundle.quality.peakAmplitude = calculatePeakAmplitude(bundle.buffer);
            bundle.quality.rmsAmplitude = calculateRMSAmplitude(bundle.buffer);
            bundle.quality.dynamicRange = calculateDynamicRange(bundle.buffer);
            bundle.quality.signalToNoiseRatio = calculateSignalToNoiseRatio(bundle.buffer);
        }
        
        return bundle;
        
    } catch (const std::exception& e) {
        m_lastError = e.what();
        throw;
    }
}

// Weapon Definition Loading
WeaponDefinition WeaponGen::loadWeaponDefinition(const std::string& filePath) {
    WeaponDefinition def;
    
    // TODO: Implement YAML/JSON parsing for weapon definitions
    // For now, create a basic definition
    def.name = "longsword";
    def.type = WeaponType::SWORD;
    def.description = "A classic longsword";
    
    // Add blade part
    BladePart bladePart;
    bladePart.shape = BladeShape::STRAIGHT;
    bladePart.length = 1.2f;
    bladePart.width = 0.1f;
    bladePart.thickness = 0.02f;
    bladePart.bevel = 0.005f;
    bladePart.curvature = 0.0f;
    def.parts.blade = bladePart;
    
    // Add guard part
    GuardPart guardPart;
    guardPart.style = GuardStyle::CROSS;
    guardPart.width = 0.3f;
    guardPart.thickness = 0.04f;
    def.parts.guard = guardPart;
    
    // Add hilt part
    HiltPart hiltPart;
    hiltPart.length = 0.2f;
    hiltPart.radius = 0.03f;
    def.parts.hilt = hiltPart;
    
    // Add pommel part
    PommelPart pommelPart;
    pommelPart.style = PommelStyle::BALL;
    pommelPart.radius = 0.035f;
    def.parts.pommel = pommelPart;
    
    // Add materials
    MaterialDefinition bladeMaterial;
    bladeMaterial.shader = ShaderType::PBR_METAL;
    bladeMaterial.textures["albedo"] = "textures/metal_alb.png";
    bladeMaterial.textures["normal"] = "textures/metal_nrm.png";
    def.materials["blade"] = bladeMaterial;
    
    MaterialDefinition guardMaterial;
    guardMaterial.shader = ShaderType::PBR_LEATHER;
    guardMaterial.textures["albedo"] = "textures/leather_alb.png";
    def.materials["guard"] = guardMaterial;
    
    // Add animations
    def.animations["draw"] = "animations/longsword_draw.anim";
    def.animations["swing"] = "animations/longsword_swing.anim";
    
    // Add physics
    def.physics.collisionType = CollisionType::CONVEX_HULL;
    
    // Add variants
    WeaponVariant highVariant;
    highVariant.quality = QualityLevel::HIGH;
    highVariant.lodReduction = 0.0f;
    def.variants.push_back(highVariant);
    
    WeaponVariant mediumVariant;
    mediumVariant.quality = QualityLevel::MEDIUM;
    mediumVariant.lodReduction = 0.5f;
    def.variants.push_back(mediumVariant);
    
    WeaponVariant lowVariant;
    lowVariant.quality = QualityLevel::LOW;
    lowVariant.lodReduction = 0.8f;
    def.variants.push_back(lowVariant);
    
    return def;
}

WeaponDefinition WeaponGen::createDefaultWeaponDefinition(const WeaponParams& params) {
    WeaponDefinition def;
    def.name = "default_weapon";
    def.type = WeaponType::SWORD;
    def.description = "Default weapon";
    
    // Create basic parts
    BladePart bladePart;
    bladePart.shape = BladeShape::STRAIGHT;
    bladePart.length = 1.0f;
    bladePart.width = 0.08f;
    bladePart.thickness = 0.02f;
    bladePart.bevel = 0.005f;
    bladePart.curvature = 0.0f;
    def.parts.blade = bladePart;
    
    // Add default material
    MaterialDefinition defaultMaterial;
    defaultMaterial.shader = ShaderType::PBR_METAL;
    def.materials["default"] = defaultMaterial;
    
    return def;
}

// Weapon Pipeline Processing
WeaponResult WeaponGen::processWeaponPipeline(const WeaponDefinition& weaponDef, const WeaponParams& params) {
    WeaponResult result;
    
    // Step 1: Generate weapon parts
    std::vector<ProcessedPart> processedParts = generateWeaponParts(weaponDef);
    
    // Step 2: Assemble weapon mesh
    WeaponMesh assembledMesh = assembleWeaponMesh(processedParts, weaponDef);
    
    // Step 3: Generate LOD variants
    std::vector<LODMesh> lodMeshes = generateLODVariants(assembledMesh, weaponDef.variants);
    
    // Step 4: Process materials and textures
    std::vector<ProcessedMaterial> processedMaterials = processMaterials(weaponDef.materials);
    
    // Step 5: Generate physics colliders
    PhysicsCollider collider = generatePhysicsCollider(assembledMesh, weaponDef.physics);
    
    // Step 6: Process animations
    std::vector<ProcessedAnimation> animations = processAnimations(weaponDef.animations);
    
    // Step 7: Create weapon pack
    result.weaponPack = createWeaponPack(weaponDef, assembledMesh, lodMeshes, processedMaterials, collider, animations);
    
    // Step 8: Categorize assets by type
    categorizeAssets(processedParts, lodMeshes, processedMaterials, animations, result);
    
    result.processedParts = processedParts;
    result.assembledMesh = assembledMesh;
    result.lodMeshes = lodMeshes;
    result.materials = processedMaterials;
    result.collider = collider;
    result.animations = animations;
    result.weaponDef = weaponDef;
    
    return result;
}

// Weapon Generator Initialization
void WeaponGen::initializeWeaponGenerators() {
    // Initialize part generators
    m_bladeGenerator = std::make_unique<BladeGenerator>();
    m_guardGenerator = std::make_unique<GuardGenerator>();
    m_hiltGenerator = std::make_unique<HiltGenerator>();
    m_pommelGenerator = std::make_unique<PommelGenerator>();
    
    // Initialize mesh processors
    m_meshAssembler = std::make_unique<MeshAssembler>();
    m_lodGenerator = std::make_unique<LODGenerator>();
    m_colliderGenerator = std::make_unique<ColliderGenerator>();
    
    // Initialize material processors
    m_materialProcessor = std::make_unique<MaterialProcessor>();
    m_textureProcessor = std::make_unique<TextureProcessor>();
    
    // Initialize animation processors
    m_animationProcessor = std::make_unique<AnimationProcessor>();
}

// Weapon Part Generation
std::vector<ProcessedPart> WeaponGen::generateWeaponParts(const WeaponDefinition& weaponDef) {
    std::vector<ProcessedPart> parts;
    
    // Generate blade
    if (weaponDef.parts.blade.length > 0.0f) {
        ProcessedPart bladePart = m_bladeGenerator->generate(weaponDef.parts.blade);
        bladePart.id = "blade";
        bladePart.type = PartType::BLADE;
        parts.push_back(bladePart);
    }
    
    // Generate guard
    if (weaponDef.parts.guard.width > 0.0f) {
        ProcessedPart guardPart = m_guardGenerator->generate(weaponDef.parts.guard);
        guardPart.id = "guard";
        guardPart.type = PartType::GUARD;
        parts.push_back(guardPart);
    }
    
    // Generate hilt
    if (weaponDef.parts.hilt.length > 0.0f) {
        ProcessedPart hiltPart = m_hiltGenerator->generate(weaponDef.parts.hilt);
        hiltPart.id = "hilt";
        hiltPart.type = PartType::HILT;
        parts.push_back(hiltPart);
    }
    
    // Generate pommel
    if (weaponDef.parts.pommel.radius > 0.0f) {
        ProcessedPart pommelPart = m_pommelGenerator->generate(weaponDef.parts.pommel);
        pommelPart.id = "pommel";
        pommelPart.type = PartType::POMMEL;
        parts.push_back(pommelPart);
    }
    
    return parts;
}

// Mesh Assembly
WeaponMesh WeaponGen::assembleWeaponMesh(const std::vector<ProcessedPart>& parts, const WeaponDefinition& weaponDef) {
    WeaponMesh assembledMesh;
    
    // Assemble parts into unified mesh
    assembledMesh = m_meshAssembler->assemble(parts);
    
    // Compute UVs, normals, tangents
    assembledMesh = computeMeshAttributes(assembledMesh);
    
    // Generate vertex colors for ornament maps
    assembledMesh = generateVertexColors(assembledMesh, weaponDef);
    
    return assembledMesh;
}

// LOD Generation
std::vector<LODMesh> WeaponGen::generateLODVariants(const WeaponMesh& baseMesh, const std::vector<WeaponVariant>& variants) {
    std::vector<LODMesh> lodMeshes;
    
    for (const auto& variant : variants) {
        LODMesh lodMesh;
        lodMesh.quality = variant.quality;
        lodMesh.lodReduction = variant.lodReduction;
        
        // Generate LOD mesh
        lodMesh.mesh = m_lodGenerator->generate(baseMesh, variant.lodReduction);
        
        lodMeshes.push_back(lodMesh);
    }
    
    return lodMeshes;
}

// Material Processing
std::vector<ProcessedMaterial> WeaponGen::processMaterials(const std::map<std::string, MaterialDefinition>& materials) {
    std::vector<ProcessedMaterial> processedMaterials;
    
    for (const auto& [name, materialDef] : materials) {
        ProcessedMaterial processedMaterial;
        processedMaterial.id = name;
        processedMaterial.shaderType = materialDef.shader;
        
        // Process textures
        for (const auto& [type, path] : materialDef.textures) {
            ProcessedTexture texture = m_textureProcessor->process(path, type);
            processedMaterial.textures[type] = texture;
        }
        
        // Process material parameters
        processedMaterial.parameters = materialDef.parameters;
        
        processedMaterials.push_back(processedMaterial);
    }
    
    return processedMaterials;
}

// Physics Collider Generation
PhysicsCollider WeaponGen::generatePhysicsCollider(const WeaponMesh& mesh, const PhysicsSettings& physics) {
    PhysicsCollider collider;
    
    switch (physics.collisionType) {
        case CollisionType::CONVEX_HULL:
            collider = m_colliderGenerator->generateConvexHull(mesh);
            break;
        case CollisionType::PRIMITIVE:
            collider = m_colliderGenerator->generatePrimitive(mesh);
            break;
        case CollisionType::MESH:
            collider = m_colliderGenerator->generateMeshCollider(mesh);
            break;
    }
    
    return collider;
}

// Animation Processing
std::vector<ProcessedAnimation> WeaponGen::processAnimations(const std::map<std::string, std::string>& animations) {
    std::vector<ProcessedAnimation> processedAnimations;
    
    for (const auto& [name, path] : animations) {
        ProcessedAnimation animation = m_animationProcessor->process(path);
        animation.id = name;
        processedAnimations.push_back(animation);
    }
    
    return processedAnimations;
}

// Weapon Pack Creation
WeaponPack WeaponGen::createWeaponPack(const WeaponDefinition& weaponDef,
                                      const WeaponMesh& assembledMesh,
                                      const std::vector<LODMesh>& lodMeshes,
                                      const std::vector<ProcessedMaterial>& materials,
                                      const PhysicsCollider& collider,
                                      const std::vector<ProcessedAnimation>& animations) {
    WeaponPack pack;
    
    pack.name = weaponDef.name;
    pack.type = weaponDef.type;
    pack.version = "1.0.0";
    pack.assembledMesh = assembledMesh;
    pack.lodMeshes = lodMeshes;
    pack.materials = materials;
    pack.collider = collider;
    pack.animations = animations;
    pack.weaponDef = weaponDef;
    
    // Calculate total size
    pack.totalSize = calculatePackSize(pack);
    pack.creationTime = std::chrono::system_clock::now();
    
    // Generate pack checksum
    pack.checksum = calculatePackChecksum(pack);
    
    // TODO: Implement actual pack serialization
    // This would create the .weaponpack archive with header, meshes, textures, and metadata
    
    return pack;
}

// Asset Categorization
void WeaponGen::categorizeAssets(const std::vector<ProcessedPart>& parts,
                                const std::vector<LODMesh>& lodMeshes,
                                const std::vector<ProcessedMaterial>& materials,
                                const std::vector<ProcessedAnimation>& animations,
                                WeaponResult& result) {
    // Categorize parts
    for (const auto& part : parts) {
        switch (part.type) {
            case PartType::BLADE:
                result.bladeParts.push_back(part);
                break;
            case PartType::GUARD:
                result.guardParts.push_back(part);
                break;
            case PartType::HILT:
                result.hiltParts.push_back(part);
                break;
            case PartType::POMMEL:
                result.pommelParts.push_back(part);
                break;
        }
    }
    
    // Categorize LOD meshes
    for (const auto& lodMesh : lodMeshes) {
        switch (lodMesh.quality) {
            case QualityLevel::HIGH:
                result.highQualityMeshes.push_back(lodMesh);
                break;
            case QualityLevel::MEDIUM:
                result.mediumQualityMeshes.push_back(lodMesh);
                break;
            case QualityLevel::LOW:
                result.lowQualityMeshes.push_back(lodMesh);
                break;
        }
    }
    
    // Categorize materials
    for (const auto& material : materials) {
        switch (material.shaderType) {
            case ShaderType::PBR_METAL:
                result.metalMaterials.push_back(material);
                break;
            case ShaderType::PBR_LEATHER:
                result.leatherMaterials.push_back(material);
                break;
            case ShaderType::PBR_WOOD:
                result.woodMaterials.push_back(material);
                break;
            default:
                result.otherMaterials.push_back(material);
                break;
        }
    }
    
    // Categorize animations
    for (const auto& animation : animations) {
        if (animation.id.find("draw") != std::string::npos) {
            result.drawAnimations.push_back(animation);
        } else if (animation.id.find("swing") != std::string::npos) {
            result.swingAnimations.push_back(animation);
        } else if (animation.id.find("sheath") != std::string::npos) {
            result.sheathAnimations.push_back(animation);
        } else {
            result.otherAnimations.push_back(animation);
        }
    }
}

// Mesh Attribute Computation
WeaponMesh WeaponGen::computeMeshAttributes(const WeaponMesh& mesh) {
    WeaponMesh processedMesh = mesh;
    
    // Compute normals
    processedMesh = computeNormals(processedMesh);
    
    // Compute tangents
    processedMesh = computeTangents(processedMesh);
    
    // Generate UVs
    processedMesh = generateUVs(processedMesh);
    
    return processedMesh;
}

WeaponMesh WeaponGen::computeNormals(const WeaponMesh& mesh) {
    // TODO: Implement normal computation
    return mesh;
}

WeaponMesh WeaponGen::computeTangents(const WeaponMesh& mesh) {
    // TODO: Implement tangent computation
    return mesh;
}

WeaponMesh WeaponGen::generateUVs(const WeaponMesh& mesh) {
    // TODO: Implement UV generation
    return mesh;
}

WeaponMesh WeaponGen::generateVertexColors(const WeaponMesh& mesh, const WeaponDefinition& weaponDef) {
    // TODO: Implement vertex color generation for ornament maps
    return mesh;
}

// Size and Checksum Calculation
size_t WeaponGen::calculatePackSize(const WeaponPack& pack) {
    size_t totalSize = 64; // Header size
    
    // Add mesh sizes
    for (const auto& lodMesh : pack.lodMeshes) {
        totalSize += lodMesh.mesh.vertexCount * sizeof(Vertex);
        totalSize += lodMesh.mesh.indexCount * sizeof(uint32_t);
    }
    
    // Add material sizes
    for (const auto& material : pack.materials) {
        for (const auto& [type, texture] : material.textures) {
            totalSize += texture.data.size();
        }
    }
    
    // Add animation sizes
    for (const auto& animation : pack.animations) {
        totalSize += animation.data.size();
    }
    
    return totalSize;
}

std::string WeaponGen::calculatePackChecksum(const WeaponPack& pack) {
    // TODO: Implement proper SHA-256 checksum
    // For now, use pack name and version as checksum
    return pack.name + "_" + pack.version;
}

// Part Generator Implementations
ProcessedPart WeaponGen::BladeGenerator::generate(const BladePart& bladePart) {
    ProcessedPart part;
    part.id = "blade";
    part.type = PartType::BLADE;
    
    // TODO: Implement actual blade mesh generation
    // For now, create placeholder mesh data
    part.mesh.vertexCount = 1000;
    part.mesh.indexCount = 2000;
    part.mesh.boundingBox = {glm::vec3(-0.5f, -0.5f, -0.5f), glm::vec3(0.5f, 0.5f, 0.5f)};
    
    return part;
}

ProcessedPart WeaponGen::GuardGenerator::generate(const GuardPart& guardPart) {
    ProcessedPart part;
    part.id = "guard";
    part.type = PartType::GUARD;
    
    // TODO: Implement actual guard mesh generation
    part.mesh.vertexCount = 500;
    part.mesh.indexCount = 1000;
    part.mesh.boundingBox = {glm::vec3(-0.2f, -0.2f, -0.2f), glm::vec3(0.2f, 0.2f, 0.2f)};
    
    return part;
}

ProcessedPart WeaponGen::HiltGenerator::generate(const HiltPart& hiltPart) {
    ProcessedPart part;
    part.id = "hilt";
    part.type = PartType::HILT;
    
    // TODO: Implement actual hilt mesh generation
    part.mesh.vertexCount = 300;
    part.mesh.indexCount = 600;
    part.mesh.boundingBox = {glm::vec3(-0.1f, -0.1f, -0.1f), glm::vec3(0.1f, 0.1f, 0.1f)};
    
    return part;
}

ProcessedPart WeaponGen::PommelGenerator::generate(const PommelPart& pommelPart) {
    ProcessedPart part;
    part.id = "pommel";
    part.type = PartType::POMMEL;
    
    // TODO: Implement actual pommel mesh generation
    part.mesh.vertexCount = 200;
    part.mesh.indexCount = 400;
    part.mesh.boundingBox = {glm::vec3(-0.05f, -0.05f, -0.05f), glm::vec3(0.05f, 0.05f, 0.05f)};
    
    return part;
}

// Mesh Processor Implementations
WeaponMesh WeaponGen::MeshAssembler::assemble(const std::vector<ProcessedPart>& parts) {
    WeaponMesh assembledMesh;
    
    // TODO: Implement actual mesh assembly
    // Combine all part meshes into unified mesh
    for (const auto& part : parts) {
        assembledMesh.vertexCount += part.mesh.vertexCount;
        assembledMesh.indexCount += part.mesh.indexCount;
    }
    
    return assembledMesh;
}

LODMesh WeaponGen::LODGenerator::generate(const WeaponMesh& baseMesh, float reduction) {
    LODMesh lodMesh;
    
    // TODO: Implement actual LOD generation
    // Simplify mesh based on reduction factor
    lodMesh.mesh = baseMesh;
    lodMesh.vertexCount = static_cast<uint32_t>(baseMesh.vertexCount * (1.0f - reduction));
    lodMesh.indexCount = static_cast<uint32_t>(baseMesh.indexCount * (1.0f - reduction));
    
    return lodMesh;
}

PhysicsCollider WeaponGen::ColliderGenerator::generateConvexHull(const WeaponMesh& mesh) {
    PhysicsCollider collider;
    collider.type = CollisionType::CONVEX_HULL;
    
    // TODO: Implement convex hull generation
    collider.boundingBox = mesh.boundingBox;
    
    return collider;
}

PhysicsCollider WeaponGen::ColliderGenerator::generatePrimitive(const WeaponMesh& mesh) {
    PhysicsCollider collider;
    collider.type = CollisionType::PRIMITIVE;
    
    // TODO: Implement primitive collider generation
    collider.boundingBox = mesh.boundingBox;
    
    return collider;
}

PhysicsCollider WeaponGen::ColliderGenerator::generateMeshCollider(const WeaponMesh& mesh) {
    PhysicsCollider collider;
    collider.type = CollisionType::MESH;
    
    // TODO: Implement mesh collider generation
    collider.boundingBox = mesh.boundingBox;
    
    return collider;
}

// Material Processor Implementations
ProcessedTexture WeaponGen::TextureProcessor::process(const std::string& path, const std::string& type) {
    ProcessedTexture texture;
    texture.path = path;
    texture.type = type;
    
    // TODO: Implement actual texture processing
    // Load, compress, and generate mipmaps
    texture.width = 512;
    texture.height = 512;
    texture.format = TextureFormat::RGBA8;
    texture.mipLevels = 9;
    
    return texture;
}

// Animation Processor Implementations
ProcessedAnimation WeaponGen::AnimationProcessor::process(const std::string& path) {
    ProcessedAnimation animation;
    animation.path = path;
    
    // TODO: Implement actual animation processing
    // Load and compile animation data
    animation.duration = 2.0f;
    animation.frameCount = 60;
    animation.frameRate = 30.0f;
    
    return animation;
}

// Quality calculation functions
float WeaponGen::calculatePeakAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    return *std::max_element(samples.begin(), samples.end(), 
                            [](float a, float b) { return std::abs(a) < std::abs(b); });
}

float WeaponGen::calculateRMSAmplitude(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float sum = 0.0f;
    for (float sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

float WeaponGen::calculateDynamicRange(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float peak = calculatePeakAmplitude(samples);
    float rms = calculateRMSAmplitude(samples);
    return peak > 0.0f ? 20.0f * std::log10(peak / rms) : 0.0f;
}

float WeaponGen::calculateSignalToNoiseRatio(const std::vector<float>& samples) {
    if (samples.empty()) return 0.0f;
    float signal = calculateRMSAmplitude(samples);
    float noise = 0.001f; // Assumed noise floor
    return signal > 0.0f ? 20.0f * std::log10(signal / noise) : 0.0f;
}

// Quality Settings
void WeaponGen::setProcessingQuality(int quality) {
    m_processingQuality = clamp(quality, 1, 10);
}

void WeaponGen::setLODReduction(float reduction) {
    m_lodReduction = clamp(reduction, 0.0f, 1.0f);
}

void WeaponGen::setPhysicsEnabled(bool enable) {
    m_enablePhysics = enable;
}

// Processing Options
void WeaponGen::enableGPUAcceleration(bool enable) {
    m_gpuAccelerationEnabled = enable;
}

void WeaponGen::setMaxProcessingThreads(int threads) {
    m_maxProcessingThreads = clamp(threads, 1, 16);
}

// Error Handling
std::string WeaponGen::getLastError() const {
    return m_lastError;
}

void WeaponGen::clearLastError() {
    m_lastError.clear();
}

// Utility Functions
float WeaponGen::clamp(float value, float min, float max) {
    return std::max(min, std::min(max, value));
}

int WeaponGen::clamp(int value, int min, int max) {
    return std::max(min, std::min(max, value));
}

} // namespace Audio
} // namespace MagiTech 
