#pragma once

#include "ImageGenerator.hpp"
#include <imgui.h>
#include <memory>
#include <unordered_map>
#include <vector>
#include <string>
#include <functional>

namespace MagiTech {
namespace AssetGen {

// Forward declarations for all asset generators
class MechGenerator;
class MiniJetGenerator;
class QuadMechGenerator;
class CentipedeMechGenerator;
class MechAssetGenerator;
class StatusEffectGenerator;
class BlackholeProjectileGenerator;
class AlchemicalLauncherGenerator;
class AlchemicalGrenadeGenerator;
class ProjectileGenerator;
class LightningProjectileGenerator;
class CometProjectileGenerator;
class FlameProjectileGenerator;
class SegmentedWeaponGenerator;
class SegmentedCreatureGenerator;
class AudioAssetGenerator;
class MonsterGenerator;
class LightGenerator;
class TrailAssetGenerator;
class ParticleAssetGenerator;
class GeometryAssetGenerator;
class AtlasAssetGenerator;
class GrappleHookGenerator;
class ParticleFieldGenerator;
class BarbedExplosiveProjectileGenerator;
class PortalGenerator;
class SnakeSpellGenerator;
class DamageSystem;
class CrossbowGenerator;
class GyroProjectileGenerator;
class IceShardGenerator;
class DriftingOrbitalsGenerator;
class SpellProjectileGenerator;
class IconAssetGenerator;
class ShaderAssetGenerator;
class TextureAssetGenerator;
class MeshAssetGenerator;
class AnimationAssetGenerator;
class UIAssetGenerator;
class DroneMinionGenerator;
class GasGrenadeGenerator;
class FireballGenerator;
class CockpitGenerator;
class SnakeMechGenerator;
class PlasmaDiscGenerator;
class IngredientGenerator;
class ExplosiveProjectileGenerator;
class BeamNetGenerator;
class VortexSpellGenerator;
class FrostNovaGenerator;
class ShotgunPelletGenerator;
class BoomerangDiscGenerator;
class AcidLiquidProjectileGenerator;
class ClusterBombGenerator;
class HomingMissileGenerator;
class WormMechGenerator;
class TrapGenerator;
class CosmicGenerator;
class BeamGenerator;
class SpellstoneGenerator;
class RoomGenerator;
class MagicalItemGenerator;
class OrbGenerator;
class DynamicAssetPipeline;
class ProceduralAssetModule;

// Asset category enumeration
enum class AssetCategory {
    MECHS,
    PROJECTILES,
    WEAPONS,
    CREATURES,
    EFFECTS,
    AUDIO,
    VISUAL,
    UTILITY,
    COSMETIC,
    SYSTEM
};

// Asset type enumeration
enum class AssetType {
    // Mech types
    MECH_BASIC,
    MECH_MINI_JET,
    MECH_QUAD,
    MECH_CENTIPEDE,
    MECH_WORM,
    MECH_SNAKE,
    
    // Projectile types
    PROJECTILE_BASIC,
    PROJECTILE_BLACKHOLE,
    PROJECTILE_LIGHTNING,
    PROJECTILE_COMET,
    PROJECTILE_FLAME,
    PROJECTILE_GYRO,
    PROJECTILE_ICE_SHARD,
    PROJECTILE_EXPLOSIVE,
    PROJECTILE_HOMING,
    PROJECTILE_ACID,
    PROJECTILE_CLUSTER,
    PROJECTILE_SHOTGUN,
    PROJECTILE_BOOMERANG,
    
    // Weapon types
    WEAPON_SEGMENTED,
    WEAPON_CROSSBOW,
    WEAPON_BEAM_NET,
    WEAPON_GRAPPLE_HOOK,
    
    // Effect types
    EFFECT_STATUS,
    EFFECT_VORTEX,
    EFFECT_FROST_NOVA,
    EFFECT_PARTICLE_FIELD,
    EFFECT_PORTAL,
    
    // Launcher types
    LAUNCHER_ALCHEMICAL,
    GRENADE_ALCHEMICAL,
    GRENADE_GAS,
    
    // Creature types
    CREATURE_SEGMENTED,
    CREATURE_MONSTER,
    
    // Audio types
    AUDIO_ASSET,
    
    // Visual types
    LIGHT,
    TRAIL,
    PARTICLE,
    GEOMETRY,
    ATLAS,
    TEXTURE,
    MESH,
    ANIMATION,
    SHADER,
    
    // UI types
    UI_ASSET,
    ICON_ASSET,
    COCKPIT,
    
    // Utility types
    DAMAGE_SYSTEM,
    INGREDIENT,
    SPELLSTONE,
    ROOM,
    MAGICAL_ITEM,
    ORB,
    TRAP,
    
    // Cosmic types
    COSMIC,
    BEAM,
    SPELL,
    SNAKE_SPELL,
    
    // System types
    DYNAMIC_ASSET,
    PROCEDURAL,
    FIREBALL,
    PLASMA_DISC,
    DRONE_MINION
};

// Asset metadata structure
struct AssetMetadata {
    std::string name;
    std::string description;
    AssetCategory category;
    AssetType type;
    std::string version;
    std::string author;
    std::vector<std::string> tags;
    std::unordered_map<std::string, std::any> parameters;
    bool isGenerated = false;
    std::string outputPath;
    std::chrono::system_clock::time_point creationTime;
};

// Asset generator interface
class IAssetGenerator {
public:
    virtual ~IAssetGenerator() = default;
    
    // Core interface
    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
    virtual bool isInitialized() const = 0;
    
    // Asset generation
    virtual bool generateAsset(const AssetMetadata& metadata) = 0;
    virtual bool validateParameters(const std::unordered_map<std::string, std::any>& params) = 0;
    virtual std::vector<std::string> getSupportedParameters() const = 0;
    virtual std::vector<std::string> getSupportedAssetTypes() const = 0;
    
    // Metadata
    virtual std::string getName() const = 0;
    virtual std::string getVersion() const = 0;
    virtual AssetCategory getCategory() const = 0;
    virtual std::vector<AssetType> getSupportedAssetTypes() const = 0;
    
    // UI support
    virtual void renderUI() = 0;
    virtual void renderParameters() = 0;
    virtual void renderPreview() = 0;
    virtual void renderExport() = 0;
};

// Unified Asset Generator UI Class
class UnifiedAssetGeneratorUI {
public:
    UnifiedAssetGeneratorUI();
    ~UnifiedAssetGeneratorUI();
    
    // Main UI functions
    void showMainWindow();
    void showAssetBrowser();
    void showGeneratorPanel();
    void showPreviewPanel();
    void showExportPanel();
    void showSettingsPanel();
    
    // Asset management
    bool registerGenerator(const std::string& name, std::unique_ptr<IAssetGenerator> generator);
    bool unregisterGenerator(const std::string& name);
    IAssetGenerator* getGenerator(const std::string& name);
    
    // Asset generation
    bool generateAsset(const std::string& generatorName, const AssetMetadata& metadata);
    bool batchGenerateAssets(const std::vector<AssetMetadata>& assets);
    
    // UI state management
    void setActiveCategory(AssetCategory category);
    void setActiveGenerator(const std::string& generatorName);
    void setActiveAssetType(AssetType assetType);
    
    // Configuration
    bool saveConfiguration(const std::string& filePath);
    bool loadConfiguration(const std::string& filePath);
    
    // Export management
    bool exportAsset(const AssetMetadata& metadata, const std::string& outputPath);
    bool exportBatch(const std::vector<AssetMetadata>& assets, const std::string& outputDir);
    
private:
    // Internal state
    AssetCategory m_activeCategory = AssetCategory::MECHS;
    std::string m_activeGenerator;
    AssetType m_activeAssetType = AssetType::MECH_BASIC;
    bool m_showAssetBrowser = true;
    bool m_showGeneratorPanel = true;
    bool m_showPreviewPanel = true;
    bool m_showExportPanel = true;
    bool m_showSettingsPanel = false;
    
    // Asset generators
    std::unordered_map<std::string, std::unique_ptr<IAssetGenerator>> m_generators;
    std::unordered_map<AssetCategory, std::vector<std::string>> m_categoryGenerators;
    std::unordered_map<AssetType, std::string> m_typeToGenerator;
    
    // Asset metadata
    std::vector<AssetMetadata> m_assetLibrary;
    AssetMetadata m_currentAsset;
    
    // UI rendering helpers
    void renderCategoryTabs();
    void renderGeneratorList();
    void renderAssetTypeList();
    void renderParameterPanel();
    void renderPreviewPanel();
    void renderExportPanel();
    void renderSettingsPanel();
    void renderAssetBrowser();
    void renderQuickActions();
    void renderStatusBar();
    
    // Helper functions
    std::string getCategoryName(AssetCategory category);
    std::string getAssetTypeName(AssetType type);
    ImVec4 getCategoryColor(AssetCategory category);
    std::vector<std::string> getGeneratorsForCategory(AssetCategory category);
    std::vector<AssetType> getAssetTypesForGenerator(const std::string& generatorName);
    
    // Configuration
    void saveUISettings();
    void loadUISettings();
    void resetToDefaults();
    
    // Asset management
    void addAssetToLibrary(const AssetMetadata& asset);
    void removeAssetFromLibrary(const std::string& assetName);
    void updateAssetInLibrary(const AssetMetadata& asset);
    AssetMetadata* findAssetInLibrary(const std::string& assetName);
    
    // Generation helpers
    bool validateAssetMetadata(const AssetMetadata& metadata);
    std::string generateAssetName(AssetType type);
    std::string generateOutputPath(const AssetMetadata& metadata);
    
    // UI constants
    static constexpr float PANEL_WIDTH = 300.0f;
    static constexpr float PREVIEW_HEIGHT = 400.0f;
    static constexpr int MAX_RECENT_ASSETS = 10;
    static constexpr int MAX_QUICK_ACTIONS = 8;
};

// Asset Generator Factory
class AssetGeneratorFactory {
public:
    using GeneratorCreator = std::function<std::unique_ptr<IAssetGenerator>()>;
    
    static AssetGeneratorFactory& getInstance();
    
    // Register generators
    void registerGenerator(const std::string& name, GeneratorCreator creator);
    void unregisterGenerator(const std::string& name);
    
    // Create generators
    std::unique_ptr<IAssetGenerator> createGenerator(const std::string& name);
    std::vector<std::string> getAvailableGenerators() const;
    
    // Category management
    void registerCategoryGenerator(AssetCategory category, const std::string& generatorName);
    std::vector<std::string> getGeneratorsForCategory(AssetCategory category) const;
    
private:
    std::unordered_map<std::string, GeneratorCreator> m_creators;
    std::unordered_map<AssetCategory, std::vector<std::string>> m_categoryGenerators;
    std::mutex m_mutex;
};

// Utility functions
namespace UIUtils {
    std::string getCategoryDisplayName(AssetCategory category);
    std::string getAssetTypeDisplayName(AssetType type);
    ImVec4 getCategoryColor(AssetCategory category);
    ImVec4 getAssetTypeColor(AssetType type);
    std::string getAssetTypeIcon(AssetType type);
    bool isValidAssetName(const std::string& name);
    std::string sanitizeAssetName(const std::string& name);
    std::string generateUniqueAssetName(AssetType type, const std::string& baseName = "");
}

} // namespace AssetGen
} // namespace MagiTech 
