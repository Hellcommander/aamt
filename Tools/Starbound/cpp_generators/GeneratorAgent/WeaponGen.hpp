#pragma once

#include "AudioAssetTypes.hpp"
#include <vector>
#include <string>
#include <memory>
#include <map>
#include <unordered_map>
#include <chrono>

namespace MagiTech {
namespace Audio {

// Forward declarations
struct WeaponDefinition;
struct WeaponResult;
struct WeaponPack;
struct WeaponMesh;
struct ProcessedPart;
struct LODMesh;
struct ProcessedMaterial;
struct ProcessedTexture;
struct ProcessedAnimation;
struct PhysicsCollider;
struct BladePart;
struct GuardPart;
struct HiltPart;
struct PommelPart;
struct MaterialDefinition;
struct PhysicsSettings;
struct WeaponVariant;
struct Vertex;

// Weapon Types
enum class WeaponType {
    SWORD,
    AXE,
    MACE,
    DAGGER,
    SPEAR,
    BOW,
    CROSSBOW,
    STAFF,
    WAND,
    SHIELD
};

// Part Types
enum class PartType {
    BLADE,
    GUARD,
    HILT,
    POMMEL,
    GRIP,
    ORNAMENT
};

// Blade Shapes
enum class BladeShape {
    STRAIGHT,
    CURVED,
    WAVY,
    SERRATED,
    DOUBLE_EDGED,
    SINGLE_EDGED
};

// Guard Styles
enum class GuardStyle {
    CROSS,
    BASKET,
    RING,
    QUILLON,
    NONE
};

// Pommel Styles
enum class PommelStyle {
    BALL,
    WHEEL,
    TEARDROP,
    BRAZIL_NUT,
    NONE
};

// Shader Types
enum class ShaderType {
    PBR_METAL,
    PBR_LEATHER,
    PBR_WOOD,
    PBR_STONE,
    UNLIT,
    EMISSIVE
};

// Collision Types
enum class CollisionType {
    CONVEX_HULL,
    PRIMITIVE,
    MESH,
    NONE
};

// Quality Levels
enum class QualityLevel {
    LOW,
    MEDIUM,
    HIGH,
    ULTRA
};

// Texture Formats
enum class TextureFormat {
    RGBA8,
    RGBA16,
    RGB8,
    RGB16,
    R8,
    R16
};

// WeaponGen Class
class WeaponGen {
public:
    WeaponGen();
    ~WeaponGen();
    
    // Main processing function
    AudioBundle process(const WeaponParams& params);
    
    // Weapon definition management
    WeaponDefinition loadWeaponDefinition(const std::string& filePath);
    WeaponDefinition createDefaultWeaponDefinition(const WeaponParams& params);
    bool saveWeaponDefinition(const WeaponDefinition& def, const std::string& filePath);
    
    // Weapon pipeline processing
    WeaponResult processWeaponPipeline(const WeaponDefinition& weaponDef, const WeaponParams& params);
    
    // Weapon generator initialization
    void initializeWeaponGenerators();
    
    // Weapon part generation
    std::vector<ProcessedPart> generateWeaponParts(const WeaponDefinition& weaponDef);
    
    // Mesh assembly and processing
    WeaponMesh assembleWeaponMesh(const std::vector<ProcessedPart>& parts, const WeaponDefinition& weaponDef);
    std::vector<LODMesh> generateLODVariants(const WeaponMesh& baseMesh, const std::vector<WeaponVariant>& variants);
    WeaponMesh computeMeshAttributes(const WeaponMesh& mesh);
    WeaponMesh computeNormals(const WeaponMesh& mesh);
    WeaponMesh computeTangents(const WeaponMesh& mesh);
    WeaponMesh generateUVs(const WeaponMesh& mesh);
    WeaponMesh generateVertexColors(const WeaponMesh& mesh, const WeaponDefinition& weaponDef);
    
    // Material and texture processing
    std::vector<ProcessedMaterial> processMaterials(const std::map<std::string, MaterialDefinition>& materials);
    
    // Physics collider generation
    PhysicsCollider generatePhysicsCollider(const WeaponMesh& mesh, const PhysicsSettings& physics);
    
    // Animation processing
    std::vector<ProcessedAnimation> processAnimations(const std::map<std::string, std::string>& animations);
    
    // Weapon pack creation
    WeaponPack createWeaponPack(const WeaponDefinition& weaponDef,
                              const WeaponMesh& assembledMesh,
                              const std::vector<LODMesh>& lodMeshes,
                              const std::vector<ProcessedMaterial>& materials,
                              const PhysicsCollider& collider,
                              const std::vector<ProcessedAnimation>& animations);
    
    // Asset categorization
    void categorizeAssets(const std::vector<ProcessedPart>& parts,
                        const std::vector<LODMesh>& lodMeshes,
                        const std::vector<ProcessedMaterial>& materials,
                        const std::vector<ProcessedAnimation>& animations,
                        WeaponResult& result);
    
    // Part generators
    class BladeGenerator {
    public:
        void initialize() {}
        ProcessedPart generate(const BladePart& bladePart);
    };
    
    class GuardGenerator {
    public:
        void initialize() {}
        ProcessedPart generate(const GuardPart& guardPart);
    };
    
    class HiltGenerator {
    public:
        void initialize() {}
        ProcessedPart generate(const HiltPart& hiltPart);
    };
    
    class PommelGenerator {
    public:
        void initialize() {}
        ProcessedPart generate(const PommelPart& pommelPart);
    };
    
    // Mesh processors
    class MeshAssembler {
    public:
        void initialize() {}
        WeaponMesh assemble(const std::vector<ProcessedPart>& parts);
    };
    
    class LODGenerator {
    public:
        void initialize() {}
        LODMesh generate(const WeaponMesh& baseMesh, float reduction);
    };
    
    class ColliderGenerator {
    public:
        void initialize() {}
        PhysicsCollider generateConvexHull(const WeaponMesh& mesh);
        PhysicsCollider generatePrimitive(const WeaponMesh& mesh);
        PhysicsCollider generateMeshCollider(const WeaponMesh& mesh);
    };
    
    // Material processors
    class MaterialProcessor {
    public:
        void initialize() {}
        ProcessedMaterial process(const MaterialDefinition& materialDef);
    };
    
    class TextureProcessor {
    public:
        void initialize() {}
        ProcessedTexture process(const std::string& path, const std::string& type);
    };
    
    // Animation processors
    class AnimationProcessor {
    public:
        void initialize() {}
        ProcessedAnimation process(const std::string& path);
    };
    
    // Quality settings
    void setProcessingQuality(int quality);
    void setLODReduction(float reduction);
    void setPhysicsEnabled(bool enable);
    
    // Processing options
    void enableGPUAcceleration(bool enable);
    void setMaxProcessingThreads(int threads);
    
    // Error handling
    std::string getLastError() const;
    void clearLastError();
    
    // Utility functions
    float clamp(float value, float min, float max);
    int clamp(int value, int min, int max);
    size_t calculatePackSize(const WeaponPack& pack);
    std::string calculatePackChecksum(const WeaponPack& pack);
    
    // Quality calculation functions
    float calculatePeakAmplitude(const std::vector<float>& samples);
    float calculateRMSAmplitude(const std::vector<float>& samples);
    float calculateDynamicRange(const std::vector<float>& samples);
    float calculateSignalToNoiseRatio(const std::vector<float>& samples);

private:
    // Member variables
    bool m_gpuAccelerationEnabled;
    int m_processingQuality;
    float m_lodReduction;
    bool m_enablePhysics;
    int m_maxProcessingThreads;
    std::string m_lastError;
    
    // Processing settings
    bool m_enableHotReload;
    bool m_enableCaching;
    bool m_enableParallelProcessing;
    
    // Weapon part generators
    std::unique_ptr<BladeGenerator> m_bladeGenerator;
    std::unique_ptr<GuardGenerator> m_guardGenerator;
    std::unique_ptr<HiltGenerator> m_hiltGenerator;
    std::unique_ptr<PommelGenerator> m_pommelGenerator;
    
    // Mesh processors
    std::unique_ptr<MeshAssembler> m_meshAssembler;
    std::unique_ptr<LODGenerator> m_lodGenerator;
    std::unique_ptr<ColliderGenerator> m_colliderGenerator;
    
    // Material processors
    std::unique_ptr<MaterialProcessor> m_materialProcessor;
    std::unique_ptr<TextureProcessor> m_textureProcessor;
    
    // Animation processors
    std::unique_ptr<AnimationProcessor> m_animationProcessor;
    
    // Constants
    static constexpr size_t PACK_HEADER_SIZE = 64;
    static constexpr size_t MAX_LOD_LEVELS = 4;
    static constexpr float DEFAULT_LOD_REDUCTION = 0.5f;
};

// Weapon Definition Structures
struct BladePart {
    BladeShape shape = BladeShape::STRAIGHT;
    float length = 1.0f;
    float width = 0.08f;
    float thickness = 0.02f;
    float bevel = 0.005f;
    float curvature = 0.0f;
    std::map<std::string, float> parameters;
};

struct GuardPart {
    GuardStyle style = GuardStyle::CROSS;
    float width = 0.3f;
    float thickness = 0.04f;
    std::map<std::string, float> parameters;
};

struct HiltPart {
    float length = 0.2f;
    float radius = 0.03f;
    std::map<std::string, float> parameters;
};

struct PommelPart {
    PommelStyle style = PommelStyle::BALL;
    float radius = 0.035f;
    std::map<std::string, float> parameters;
};

struct WeaponParts {
    BladePart blade;
    GuardPart guard;
    HiltPart hilt;
    PommelPart pommel;
    std::map<std::string, std::string> additionalParts;
};

struct MaterialDefinition {
    ShaderType shader = ShaderType::PBR_METAL;
    std::map<std::string, std::string> textures;
    std::map<std::string, float> parameters;
};

struct PhysicsSettings {
    CollisionType collisionType = CollisionType::CONVEX_HULL;
    float mass = 1.0f;
    float friction = 0.5f;
    float restitution = 0.3f;
    std::map<std::string, float> parameters;
};

struct WeaponVariant {
    QualityLevel quality = QualityLevel::MEDIUM;
    float lodReduction = 0.5f;
    std::map<std::string, float> parameters;
};

struct WeaponDefinition {
    std::string name;
    WeaponType type;
    std::string description;
    WeaponParts parts;
    std::map<std::string, MaterialDefinition> materials;
    std::map<std::string, std::string> animations;
    PhysicsSettings physics;
    std::vector<WeaponVariant> variants;
    std::map<std::string, std::string> metadata;
    std::vector<std::string> tags;
    bool enableHotReload = true;
    bool enableCaching = true;
    bool enableParallelProcessing = true;
    int maxConcurrentParts = 8;
};

// Mesh and Geometry Structures
struct Vertex {
    glm::vec3 position;
    glm::vec3 normal;
    glm::vec3 tangent;
    glm::vec2 uv;
    glm::vec4 color;
};

struct WeaponMesh {
    uint32_t vertexCount = 0;
    uint32_t indexCount = 0;
    std::pair<glm::vec3, glm::vec3> boundingBox;
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;
    std::map<std::string, std::string> metadata;
};

struct ProcessedPart {
    std::string id;
    PartType type;
    WeaponMesh mesh;
    std::map<std::string, float> parameters;
    std::map<std::string, std::string> metadata;
};

struct LODMesh {
    QualityLevel quality = QualityLevel::MEDIUM;
    float lodReduction = 0.5f;
    WeaponMesh mesh;
    uint32_t vertexCount = 0;
    uint32_t indexCount = 0;
    std::map<std::string, float> parameters;
};

// Material and Texture Structures
struct ProcessedTexture {
    std::string path;
    std::string type;
    uint32_t width = 0;
    uint32_t height = 0;
    TextureFormat format = TextureFormat::RGBA8;
    uint32_t mipLevels = 1;
    std::vector<uint8_t> data;
    std::map<std::string, std::string> metadata;
};

struct ProcessedMaterial {
    std::string id;
    ShaderType shaderType = ShaderType::PBR_METAL;
    std::map<std::string, ProcessedTexture> textures;
    std::map<std::string, float> parameters;
    std::map<std::string, std::string> metadata;
};

// Physics Structures
struct PhysicsCollider {
    CollisionType type = CollisionType::CONVEX_HULL;
    std::pair<glm::vec3, glm::vec3> boundingBox;
    std::vector<glm::vec3> vertices;
    std::vector<uint32_t> indices;
    float mass = 1.0f;
    float friction = 0.5f;
    float restitution = 0.3f;
    std::map<std::string, float> parameters;
};

// Animation Structures
struct ProcessedAnimation {
    std::string id;
    std::string path;
    float duration = 0.0f;
    uint32_t frameCount = 0;
    float frameRate = 30.0f;
    std::vector<uint8_t> data;
    std::map<std::string, std::string> metadata;
};

// Weapon Pack Structure
struct WeaponPack {
    std::string name;
    WeaponType type;
    std::string version;
    WeaponMesh assembledMesh;
    std::vector<LODMesh> lodMeshes;
    std::vector<ProcessedMaterial> materials;
    PhysicsCollider collider;
    std::vector<ProcessedAnimation> animations;
    WeaponDefinition weaponDef;
    std::chrono::system_clock::time_point creationTime;
    std::string filePath;
    size_t totalSize = 0;
    std::string checksum;
};

// Weapon Result Structure
struct WeaponResult {
    std::vector<ProcessedPart> processedParts;
    std::vector<ProcessedPart> bladeParts;
    std::vector<ProcessedPart> guardParts;
    std::vector<ProcessedPart> hiltParts;
    std::vector<ProcessedPart> pommelParts;
    WeaponMesh assembledMesh;
    std::vector<LODMesh> lodMeshes;
    std::vector<LODMesh> highQualityMeshes;
    std::vector<LODMesh> mediumQualityMeshes;
    std::vector<LODMesh> lowQualityMeshes;
    std::vector<ProcessedMaterial> materials;
    std::vector<ProcessedMaterial> metalMaterials;
    std::vector<ProcessedMaterial> leatherMaterials;
    std::vector<ProcessedMaterial> woodMaterials;
    std::vector<ProcessedMaterial> otherMaterials;
    PhysicsCollider collider;
    std::vector<ProcessedAnimation> animations;
    std::vector<ProcessedAnimation> drawAnimations;
    std::vector<ProcessedAnimation> swingAnimations;
    std::vector<ProcessedAnimation> sheathAnimations;
    std::vector<ProcessedAnimation> otherAnimations;
    std::vector<ProcessedTexture> audioAssets;
    WeaponPack weaponPack;
    WeaponDefinition weaponDef;
    std::chrono::system_clock::time_point processingTime;
    bool success = true;
    std::string errorMessage;
    std::vector<std::string> warnings;
    std::map<std::string, std::string> metadata;
};

} // namespace Audio
} // namespace MagiTech 
