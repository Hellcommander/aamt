#pragma once

#include <nlohmann/json.hpp>
#include <filesystem>
#include <set>
#include <string>
#include <vector>
#include <unordered_map>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace fs = std::filesystem;

struct TileAsset {
    fs::path path;
    std::string license;
    std::string category;
    std::vector<std::string> tags;
    glm::ivec2 size = {64, 64};
    uint64_t hashKey() const;
};

struct TileVariant {
    std::string baseId;
    glm::vec4 tintColor = {1.0f, 1.0f, 1.0f, 1.0f};
    float noiseIntensity = 0.0f;
    float rotation = 0.0f;
    bool mirrored = false;
    uint64_t hashKey() const;
};

struct AtlasTile {
    std::string id;
    glm::vec4 uv = {0.0f, 0.0f, 1.0f, 1.0f};
    std::string license;
    std::string category;
    glm::ivec2 size = {64, 64};
};

struct AtlasMetadata {
    std::string atlasName;
    std::string texturePath;
    glm::ivec2 tileSize = {64, 64};
    glm::ivec2 atlasSize = {512, 256};
    std::unordered_map<std::string, AtlasTile> tiles;
    uint64_t hashKey() const;
};

class TileLibraryBuilder {
public:
    // Core pipeline methods
    void loadManifest(const fs::path& manifestPath);
    void validateLicenses(const std::set<std::string>& allowList);
    void generateVariants(int variantCount);
    void packAtlases(const fs::path& outDir);
    void writeMetadata(const fs::path& outDir);
    
    // Utility methods
    void scanDirectory(const fs::path& dirPath);
    void categorizeAssets();
    void generateAtlasVariants(const std::string& category, int variantCount);
    
    // Getters
    const std::vector<TileAsset>& getValidatedAssets() const { return m_validated_assets; }
    const std::vector<AtlasMetadata>& getAtlases() const { return m_atlases; }
    
    // Configuration
    void setTileSize(const glm::ivec2& size) { m_tileSize = size; }
    void setAtlasSize(const glm::ivec2& size) { m_atlasSize = size; }
    void setAllowedLicenses(const std::set<std::string>& licenses) { m_allowedLicenses = licenses; }

private:
    // Asset management
    std::vector<TileAsset> m_assets;
    std::vector<TileAsset> m_validated_assets;
    std::vector<TileVariant> m_variants;
    std::vector<AtlasMetadata> m_atlases;
    
    // Configuration
    glm::ivec2 m_tileSize = {64, 64};
    glm::ivec2 m_atlasSize = {512, 256};
    std::set<std::string> m_allowedLicenses = {"CC0", "CC-BY", "MIT"};
    
    // Internal methods
    bool isValidImageFile(const fs::path& path) const;
    std::string extractLicenseFromFile(const fs::path& path) const;
    void applyVariantEffects(const TileAsset& base, const TileVariant& variant, 
                           const fs::path& outputPath);
    bool packAtlas(const std::string& category, const std::vector<TileAsset>& tiles);
    void writeAtlasJson(const AtlasMetadata& atlas, const fs::path& outDir);
};
