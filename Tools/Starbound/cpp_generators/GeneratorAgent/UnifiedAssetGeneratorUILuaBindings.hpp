#pragma once

#include "UnifiedAssetGeneratorUI.hpp"
#include <sol/sol.hpp>

namespace MagiTech {
namespace AssetGen {

// Lua bindings for UnifiedAssetGeneratorUI
class UnifiedAssetGeneratorUILuaBindings {
public:
    static void registerBindings(sol::state& lua);
    
private:
    // Helper functions for Lua integration
    static void registerAssetCategoryEnum(sol::state& lua);
    static void registerAssetTypeEnum(sol::state& lua);
    static void registerAssetMetadata(sol::state& lua);
    static void registerIAssetGenerator(sol::state& lua);
    static void registerUnifiedAssetGeneratorUI(sol::state& lua);
    static void registerAssetGeneratorFactory(sol::state& lua);
    static void registerUIUtils(sol::state& lua);
    
    // Lua helper functions
    static sol::table createAssetMetadataTable(sol::state& lua, const AssetMetadata& metadata);
    static AssetMetadata createAssetMetadataFromTable(sol::state& lua, const sol::table& table);
    static sol::table createParameterTable(sol::state& lua, const std::unordered_map<std::string, std::any>& params);
    static std::unordered_map<std::string, std::any> createParameterMapFromTable(sol::state& lua, const sol::table& table);
};

// Lua wrapper for UnifiedAssetGeneratorUI
class UnifiedAssetGeneratorUILuaWrapper {
public:
    UnifiedAssetGeneratorUILuaWrapper();
    ~UnifiedAssetGeneratorUILuaWrapper();
    
    // Main UI functions
    void showMainWindow();
    void showAssetBrowser();
    void showGeneratorPanel();
    void showPreviewPanel();
    void showExportPanel();
    void showSettingsPanel();
    
    // Asset management
    bool registerGenerator(const std::string& name, sol::function creator);
    bool unregisterGenerator(const std::string& name);
    sol::table getGenerator(const std::string& name);
    
    // Asset generation
    bool generateAsset(const std::string& generatorName, const sol::table& metadata);
    bool batchGenerateAssets(const sol::table& assets);
    
    // UI state management
    void setActiveCategory(int category);
    void setActiveGenerator(const std::string& generatorName);
    void setActiveAssetType(int assetType);
    
    // Configuration
    bool saveConfiguration(const std::string& filePath);
    bool loadConfiguration(const std::string& filePath);
    
    // Export management
    bool exportAsset(const sol::table& metadata, const std::string& outputPath);
    bool exportBatch(const sol::table& assets, const std::string& outputDir);
    
    // Asset library management
    void addAssetToLibrary(const sol::table& asset);
    void removeAssetFromLibrary(const std::string& assetName);
    void updateAssetInLibrary(const sol::table& asset);
    sol::table findAssetInLibrary(const std::string& assetName);
    sol::table getAllAssets();
    
    // Utility functions
    sol::table getGeneratorsForCategory(int category);
    sol::table getAssetTypesForGenerator(const std::string& generatorName);
    std::string getCategoryName(int category);
    std::string getAssetTypeName(int assetType);
    sol::table getCategoryColor(int category);
    
    // Quick actions
    void duplicateAsset(const std::string& assetName);
    void exportAssetByName(const std::string& assetName);
    void deleteAsset(const std::string& assetName);
    void generateAllAssets();
    void exportAllAssets();
    void validateAllAssets();
    void cleanLibrary();
    
    // Batch operations
    void batchGenerateFromTable(const sol::table& assetTable);
    void batchExportFromTable(const sol::table& assetTable);
    
    // Search and filter
    sol::table searchAssets(const std::string& searchText);
    sol::table filterAssetsByCategory(int category);
    sol::table filterAssetsByType(int assetType);
    sol::table filterAssetsByTag(const std::string& tag);
    
    // Settings
    void setUISetting(const std::string& setting, const sol::object& value);
    sol::object getUISetting(const std::string& setting);
    void resetUISettings();
    
    // Statistics
    sol::table getStatistics();
    int getAssetCount();
    int getGeneratorCount();
    int getCategoryCount();
    
private:
    std::unique_ptr<UnifiedAssetGeneratorUI> m_ui;
    
    // Helper functions
    AssetMetadata tableToAssetMetadata(const sol::table& table);
    sol::table assetMetadataToTable(const AssetMetadata& metadata);
    std::vector<AssetMetadata> tableToAssetMetadataVector(const sol::table& table);
    sol::table assetMetadataVectorToTable(const std::vector<AssetMetadata>& assets);
};

// Lua wrapper for IAssetGenerator
class IAssetGeneratorLuaWrapper {
public:
    IAssetGeneratorLuaWrapper(std::unique_ptr<IAssetGenerator> generator);
    ~IAssetGeneratorLuaWrapper();
    
    // Core interface
    bool initialize();
    void shutdown();
    bool isInitialized() const;
    
    // Asset generation
    bool generateAsset(const sol::table& metadata);
    bool validateParameters(const sol::table& params);
    sol::table getSupportedParameters();
    sol::table getSupportedAssetTypes();
    
    // Metadata
    std::string getName() const;
    std::string getVersion() const;
    int getCategory() const;
    sol::table getSupportedAssetTypesEnum();
    
    // UI support
    void renderUI();
    void renderParameters();
    void renderPreview();
    void renderExport();
    
private:
    std::unique_ptr<IAssetGenerator> m_generator;
};

// Lua wrapper for AssetGeneratorFactory
class AssetGeneratorFactoryLuaWrapper {
public:
    AssetGeneratorFactoryLuaWrapper();
    ~AssetGeneratorFactoryLuaWrapper();
    
    // Register generators
    void registerGenerator(const std::string& name, sol::function creator);
    void unregisterGenerator(const std::string& name);
    
    // Create generators
    sol::table createGenerator(const std::string& name);
    sol::table getAvailableGenerators();
    
    // Category management
    void registerCategoryGenerator(int category, const std::string& generatorName);
    sol::table getGeneratorsForCategory(int category);
    
private:
    AssetGeneratorFactory& m_factory;
};

// Lua utility functions
namespace LuaUtils {
    // Asset metadata conversion
    sol::table createAssetMetadataTable(sol::state& lua, const AssetMetadata& metadata);
    AssetMetadata createAssetMetadataFromTable(sol::state& lua, const sol::table& table);
    
    // Parameter conversion
    sol::table createParameterTable(sol::state& lua, const std::unordered_map<std::string, std::any>& params);
    std::unordered_map<std::string, std::any> createParameterMapFromTable(sol::state& lua, const sol::table& table);
    
    // Enum conversion
    sol::table createAssetCategoryTable(sol::state& lua);
    sol::table createAssetTypeTable(sol::state& lua);
    
    // Color conversion
    sol::table createColorTable(sol::state& lua, const ImVec4& color);
    ImVec4 createColorFromTable(sol::state& lua, const sol::table& table);
    
    // Validation
    bool validateAssetMetadata(const sol::table& metadata);
    bool validateParameters(const sol::table& params);
    std::string getValidationError();
    
    // Utility
    std::string sanitizeAssetName(const std::string& name);
    std::string generateUniqueAssetName(int assetType, const std::string& baseName = "");
    sol::table getAssetTypeInfo(int assetType);
    sol::table getCategoryInfo(int category);
}

// Lua constants
namespace LuaConstants {
    // Asset categories
    constexpr int ASSET_CATEGORY_MECHS = 0;
    constexpr int ASSET_CATEGORY_PROJECTILES = 1;
    constexpr int ASSET_CATEGORY_WEAPONS = 2;
    constexpr int ASSET_CATEGORY_CREATURES = 3;
    constexpr int ASSET_CATEGORY_EFFECTS = 4;
    constexpr int ASSET_CATEGORY_AUDIO = 5;
    constexpr int ASSET_CATEGORY_VISUAL = 6;
    constexpr int ASSET_CATEGORY_UTILITY = 7;
    constexpr int ASSET_CATEGORY_COSMETIC = 8;
    constexpr int ASSET_CATEGORY_SYSTEM = 9;
    
    // Asset types
    constexpr int ASSET_TYPE_MECH_BASIC = 0;
    constexpr int ASSET_TYPE_MECH_MINI_JET = 1;
    constexpr int ASSET_TYPE_MECH_QUAD = 2;
    constexpr int ASSET_TYPE_MECH_CENTIPEDE = 3;
    constexpr int ASSET_TYPE_MECH_WORM = 4;
    constexpr int ASSET_TYPE_MECH_SNAKE = 5;
    
    constexpr int ASSET_TYPE_PROJECTILE_BASIC = 6;
    constexpr int ASSET_TYPE_PROJECTILE_BLACKHOLE = 7;
    constexpr int ASSET_TYPE_PROJECTILE_LIGHTNING = 8;
    constexpr int ASSET_TYPE_PROJECTILE_COMET = 9;
    constexpr int ASSET_TYPE_PROJECTILE_FLAME = 10;
    constexpr int ASSET_TYPE_PROJECTILE_GYRO = 11;
    constexpr int ASSET_TYPE_PROJECTILE_ICE_SHARD = 12;
    constexpr int ASSET_TYPE_PROJECTILE_EXPLOSIVE = 13;
    constexpr int ASSET_TYPE_PROJECTILE_HOMING = 14;
    constexpr int ASSET_TYPE_PROJECTILE_ACID = 15;
    constexpr int ASSET_TYPE_PROJECTILE_CLUSTER = 16;
    constexpr int ASSET_TYPE_PROJECTILE_SHOTGUN = 17;
    constexpr int ASSET_TYPE_PROJECTILE_BOOMERANG = 18;
    
    constexpr int ASSET_TYPE_WEAPON_SEGMENTED = 19;
    constexpr int ASSET_TYPE_WEAPON_CROSSBOW = 20;
    constexpr int ASSET_TYPE_WEAPON_BEAM_NET = 21;
    constexpr int ASSET_TYPE_WEAPON_GRAPPLE_HOOK = 22;
    
    constexpr int ASSET_TYPE_EFFECT_STATUS = 23;
    constexpr int ASSET_TYPE_EFFECT_VORTEX = 24;
    constexpr int ASSET_TYPE_EFFECT_FROST_NOVA = 25;
    constexpr int ASSET_TYPE_EFFECT_PARTICLE_FIELD = 26;
    constexpr int ASSET_TYPE_EFFECT_PORTAL = 27;
    
    constexpr int ASSET_TYPE_LAUNCHER_ALCHEMICAL = 28;
    constexpr int ASSET_TYPE_GRENADE_ALCHEMICAL = 29;
    constexpr int ASSET_TYPE_GRENADE_GAS = 30;
    
    constexpr int ASSET_TYPE_CREATURE_SEGMENTED = 31;
    constexpr int ASSET_TYPE_CREATURE_MONSTER = 32;
    
    constexpr int ASSET_TYPE_AUDIO_ASSET = 33;
    
    constexpr int ASSET_TYPE_LIGHT = 34;
    constexpr int ASSET_TYPE_TRAIL = 35;
    constexpr int ASSET_TYPE_PARTICLE = 36;
    constexpr int ASSET_TYPE_GEOMETRY = 37;
    constexpr int ASSET_TYPE_ATLAS = 38;
    constexpr int ASSET_TYPE_TEXTURE = 39;
    constexpr int ASSET_TYPE_MESH = 40;
    constexpr int ASSET_TYPE_ANIMATION = 41;
    constexpr int ASSET_TYPE_SHADER = 42;
    
    constexpr int ASSET_TYPE_UI_ASSET = 43;
    constexpr int ASSET_TYPE_ICON_ASSET = 44;
    constexpr int ASSET_TYPE_COCKPIT = 45;
    
    constexpr int ASSET_TYPE_DAMAGE_SYSTEM = 46;
    constexpr int ASSET_TYPE_INGREDIENT = 47;
    constexpr int ASSET_TYPE_SPELLSTONE = 48;
    constexpr int ASSET_TYPE_ROOM = 49;
    constexpr int ASSET_TYPE_MAGICAL_ITEM = 50;
    constexpr int ASSET_TYPE_ORB = 51;
    constexpr int ASSET_TYPE_TRAP = 52;
    
    constexpr int ASSET_TYPE_COSMIC = 53;
    constexpr int ASSET_TYPE_BEAM = 54;
    constexpr int ASSET_TYPE_SPELL = 55;
    constexpr int ASSET_TYPE_SNAKE_SPELL = 56;
    
    constexpr int ASSET_TYPE_DYNAMIC_ASSET = 57;
    constexpr int ASSET_TYPE_PROCEDURAL = 58;
    constexpr int ASSET_TYPE_FIREBALL = 59;
    constexpr int ASSET_TYPE_PLASMA_DISC = 60;
    constexpr int ASSET_TYPE_DRONE_MINION = 61;
}

} // namespace AssetGen
} // namespace MagiTech 
