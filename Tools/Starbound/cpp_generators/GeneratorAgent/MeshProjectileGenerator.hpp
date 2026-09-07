#pragma once

#include "core/Log.hpp"
#include "core/threading/ThreadPool.hpp"
#include "core/graphics/Mesh.hpp"
#include "core/graphics/Material.hpp"
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <unordered_map>

namespace MagiTech {
namespace MeshProjectiles {

// Universal Mesh Projectile Generator for Magi-Tech Items
class MeshProjectileGenerator {
public:
    struct ProjectileParams {
        std::string id;
        std::string type;           // "bolt", "arrow", "energy", "crystal", "plasma", "magic"
        std::string material;       // "steel", "wood", "crystal", "energy", "plasma", "magic"
        float length;               // projectile length
        float diameter;             // projectile diameter
        float mass;                 // projectile mass
        float velocity;             // initial velocity
        float damage;               // base damage
        std::string damageType;     // "physical", "fire", "ice", "lightning", "magic", "plasma"
        std::vector<std::string> effects; // ["piercing", "explosive", "homing", "chain", "elemental"]
        
        // Mesh generation parameters
        bool useFletching;          // add fletching/vanes
        std::string fletchStyle;    // "standard", "parabolic", "spiral", "energy"
        bool useTip;                // add specialized tip
        std::string tipStyle;       // "sharp", "barbed", "explosive", "crystal", "energy"
        bool useTrail;              // add visual trail
        std::string trailStyle;     // "spark", "smoke", "energy", "magic", "plasma"
        
        // Physics parameters
        float dragCoefficient;      // aerodynamic drag
        float liftCoefficient;      // aerodynamic lift
        float spinRate;             // rotation rate
        bool useGravity;            // affected by gravity
        float bounceElasticity;     // bounce factor
        float penetrationDepth;     // how far it penetrates
    };

    struct MeshOutput {
        std::string meshFile;       // .obj mesh file
        std::string materialFile;   // .mtl material file
        std::string textureFile;    // .png texture file
        std::string physicsFile;    // .json physics data
        std::string trailFile;      // .json trail effect data
        std::string metadataFile;   // .json generation metadata
        bool success;
        std::string errorMessage;
    };

    struct MeshData {
        std::vector<float> vertices;    // x,y,z positions
        std::vector<float> normals;     // nx,ny,nz normals
        std::vector<float> texcoords;   // u,v texture coordinates
        std::vector<uint32_t> indices;  // triangle indices
        std::vector<float> colors;      // r,g,b,a colors
        std::vector<float> tangents;    // tx,ty,tz tangents
    };

    struct PhysicsData {
        float mass;
        float inertia[3][3];        // moment of inertia tensor
        float dragCoefficient;
        float liftCoefficient;
        float spinRate;
        bool useGravity;
        float bounceElasticity;
        float penetrationDepth;
        std::vector<float> collisionShape; // collision mesh vertices
    };

    struct TrailEffect {
        std::string type;           // "spark", "smoke", "energy", "magic", "plasma"
        float duration;             // trail duration
        float width;                // trail width
        std::vector<float> color;   // r,g,b,a color
        float fadeRate;             // fade rate
        bool useParticles;          // use particle system
        int particleCount;          // number of particles
    };

    MeshProjectileGenerator();
    ~MeshProjectileGenerator() = default;

    // Initialize the mesh generator
    bool initialize();
    void shutdown();

    // Generate mesh projectiles for different item types
    std::future<MeshOutput> generateProjectileAsync(const ProjectileParams& params);
    MeshOutput generateProjectile(const ProjectileParams& params);

    // Specialized generators for different Magi-Tech items
    MeshOutput generateCrossbowBolt(const ProjectileParams& params);
    MeshOutput generateEnergyProjectile(const ProjectileParams& params);
    MeshOutput generateCrystalProjectile(const ProjectileParams& params);
    MeshOutput generatePlasmaProjectile(const ProjectileParams& params);
    MeshOutput generateMagicProjectile(const ProjectileParams& params);
    MeshOutput generateArrow(const ProjectileParams& params);

    // Batch generation
    std::vector<MeshOutput> generateBatch(const std::vector<ProjectileParams>& params);
    std::vector<MeshOutput> generateItemSet(const std::string& itemType, 
                                           const std::vector<ProjectileParams>& params);

    // Mesh generation helpers
    MeshData generateShaftMesh(const ProjectileParams& params);
    MeshData generateTipMesh(const ProjectileParams& params);
    MeshData generateFletchingMesh(const ProjectileParams& params);
    MeshData generateTrailMesh(const ProjectileParams& params);
    MeshData generateEnergyCoreMesh(const ProjectileParams& params);
    MeshData generateCrystalMesh(const ProjectileParams& params);

    // Physics generation
    PhysicsData generatePhysicsData(const ProjectileParams& params);
    std::vector<float> generateCollisionShape(const ProjectileParams& params);

    // Material generation
    std::string generateMaterialFile(const ProjectileParams& params);
    std::string generateTextureFile(const ProjectileParams& params);
    std::string generateTrailEffectFile(const ProjectileParams& params);

    // File system helpers
    bool writeMeshFile(const std::string& path, const MeshData& mesh);
    bool writeMaterialFile(const std::string& path, const std::string& content);
    bool writePhysicsFile(const std::string& path, const PhysicsData& physics);
    bool writeTrailFile(const std::string& path, const TrailEffect& trail);
    bool createDirectory(const std::string& path);

    // Cache management
    void clearCache();
    size_t getCacheSize() const;
    bool isCached(const std::string& key) const;

private:
    std::unique_ptr<ThreadPool> pool;
    std::unordered_map<std::string, MeshOutput> meshCache;
    
    // Utility functions
    std::string hashProjectileParams(const ProjectileParams& params);
    std::string sanitizeFilename(const std::string& name);
    std::string generateAssetName(const std::string& baseName, const std::string& suffix);
    
    // Mesh generation algorithms
    MeshData generateCylinderMesh(float radius, float length, int segments);
    MeshData generateConeMesh(float baseRadius, float tipRadius, float length, int segments);
    MeshData generateSphereMesh(float radius, int segments);
    MeshData generateBoxMesh(float width, float height, float depth);
    MeshData generateCapsuleMesh(float radius, float height, int segments);
    
    // Specialized mesh generators
    MeshData generateBarbedTip(float length, float diameter);
    MeshData generateCrystalTip(float length, float diameter);
    MeshData generateEnergyTip(float length, float diameter);
    MeshData generateExplosiveTip(float length, float diameter);
    
    MeshData generateStandardFletching(float length, float width);
    MeshData generateParabolicFletching(float length, float width);
    MeshData generateSpiralFletching(float length, float width);
    MeshData generateEnergyFletching(float length, float width);
    
    // Material and texture generation
    std::string generateSteelMaterial();
    std::string generateWoodMaterial();
    std::string generateCrystalMaterial();
    std::string generateEnergyMaterial();
    std::string generatePlasmaMaterial();
    std::string generateMagicMaterial();
    
    // Physics calculations
    void calculateInertiaTensor(const MeshData& mesh, float mass, float inertia[3][3]);
    float calculateDragCoefficient(const ProjectileParams& params);
    float calculateLiftCoefficient(const ProjectileParams& params);
    
    // Trail effect generation
    TrailEffect generateSparkTrail(const ProjectileParams& params);
    TrailEffect generateSmokeTrail(const ProjectileParams& params);
    TrailEffect generateEnergyTrail(const ProjectileParams& params);
    TrailEffect generateMagicTrail(const ProjectileParams& params);
    TrailEffect generatePlasmaTrail(const ProjectileParams& params);
};

// Global mesh projectile generator instance
extern std::unique_ptr<MeshProjectileGenerator> g_meshProjectileGenerator;

} // namespace MeshProjectiles
} // namespace MagiTech 
