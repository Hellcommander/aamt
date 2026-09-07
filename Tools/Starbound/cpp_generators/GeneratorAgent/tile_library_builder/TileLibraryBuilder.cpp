#include "TileLibraryBuilder.hpp"
#include "core/Log.hpp"
#include "core/utils/HashCombine.hpp"
#include <fstream>
#include <algorithm>
#include <random>

namespace MagiTech {

// Hash function implementations
uint64_t TileAsset::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, path.string().c_str(), path.string().length());
    XXH64_update(&s, license.c_str(), license.length());
    XXH64_update(&s, category.c_str(), category.length());
    XXH64_update(&s, tags.data(), tags.size() * sizeof(std::string));
    XXH64_update(&s, &size, sizeof(glm::ivec2));
    return XXH64_digest(&s);
}

uint64_t TileVariant::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, baseId.c_str(), baseId.length());
    XXH64_update(&s, &tintColor, sizeof(glm::vec4));
    XXH64_update(&s, &noiseIntensity, sizeof(float));
    XXH64_update(&s, &rotation, sizeof(float));
    XXH64_update(&s, &mirrored, sizeof(bool));
    return XXH64_digest(&s);
}

uint64_t AtlasMetadata::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, atlasName.c_str(), atlasName.length());
    XXH64_update(&s, texturePath.c_str(), texturePath.length());
    XXH64_update(&s, &tileSize, sizeof(glm::ivec2));
    XXH64_update(&s, &atlasSize, sizeof(glm::ivec2));
    return XXH64_digest(&s);
}

void TileLibraryBuilder::loadManifest(const fs::path& manifestPath) {
    Log::info("Loading asset manifest from: {}", manifestPath.string());
    std::ifstream f(manifestPath);
    if (!f.is_open()) {
        Log::error("Failed to open manifest file: {}", manifestPath.string());
        return;
    }
    
    try {
        nlohmann::json data = nlohmann::json::parse(f);
        m_assets.clear();
        
        for (const auto& item : data) {
            TileAsset asset;
            asset.path = item.at("path").get<std::string>();
            asset.license = item.at("license").get<std::string>();
            asset.category = item.at("category").get<std::string>();
            asset.tags = item.at("tags").get<std::vector<std::string>>();
            
            // Optional size field
            if (item.contains("size")) {
                auto size = item["size"];
                asset.size = {size[0], size[1]};
            }
            
            m_assets.push_back(asset);
        }
        Log::info("Loaded {} assets from manifest.", m_assets.size());
    } catch (const std::exception& e) {
        Log::error("Failed to parse manifest JSON: {}", e.what());
    }
}

void TileLibraryBuilder::scanDirectory(const fs::path& dirPath) {
    Log::info("Scanning directory for assets: {}", dirPath.string());
    m_assets.clear();
    
    if (!fs::exists(dirPath)) {
        Log::error("Directory does not exist: {}", dirPath.string());
        return;
    }
    
    for (const auto& entry : fs::recursive_directory_iterator(dirPath)) {
        if (entry.is_regular_file() && isValidImageFile(entry.path())) {
            TileAsset asset;
            asset.path = entry.path();
            asset.license = extractLicenseFromFile(entry.path());
            asset.category = "unknown"; // Will be categorized later
            asset.size = m_tileSize;
            
            // Extract tags from filename
            std::string filename = entry.path().stem().string();
            std::transform(filename.begin(), filename.end(), filename.begin(), ::tolower);
            
            // Simple tag extraction based on filename
            if (filename.find("floor") != std::string::npos) asset.category = "floor";
            else if (filename.find("wall") != std::string::npos) asset.category = "wall";
            else if (filename.find("ceiling") != std::string::npos) asset.category = "ceiling";
            else if (filename.find("prop") != std::string::npos) asset.category = "prop";
            else if (filename.find("trap") != std::string::npos) asset.category = "trap";
            
            m_assets.push_back(asset);
        }
    }
    
    Log::info("Found {} image assets in directory.", m_assets.size());
}

void TileLibraryBuilder::validateLicenses(const std::set<std::string>& allowList) {
    Log::info("Validating licenses against allowlist...");
    m_validated_assets.clear();
    
    for (const auto& asset : m_assets) {
        if (allowList.count(asset.license)) {
            m_validated_assets.push_back(asset);
        } else {
            Log::warn("Asset '{}' has a non-compliant license: {}", 
                     asset.path.string(), asset.license);
        }
    }
    
    Log::info("Validated {} assets out of {} total.", m_validated_assets.size(), m_assets.size());
}

void TileLibraryBuilder::generateVariants(int variantCount) {
    Log::info("Generating {} variants per asset...", variantCount);
    m_variants.clear();
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> hueDist(0.0f, 1.0f);
    std::uniform_real_distribution<float> noiseDist(0.0f, 0.3f);
    std::uniform_real_distribution<float> rotationDist(0.0f, 360.0f);
    std::uniform_int_distribution<int> mirrorDist(0, 1);
    
    for (const auto& asset : m_validated_assets) {
        for (int i = 0; i < variantCount; ++i) {
            TileVariant variant;
            variant.baseId = asset.path.stem().string();
            
            // Generate random tint color
            float hue = hueDist(gen);
            float saturation = 0.3f + (hueDist(gen) * 0.4f);
            float value = 0.7f + (hueDist(gen) * 0.3f);
            
            // Convert HSV to RGB (simplified)
            variant.tintColor = glm::vec4(hue, saturation, value, 1.0f);
            variant.noiseIntensity = noiseDist(gen);
            variant.rotation = rotationDist(gen);
            variant.mirrored = mirrorDist(gen) == 1;
            
            m_variants.push_back(variant);
        }
    }
    
    Log::info("Generated {} variants.", m_variants.size());
}

void TileLibraryBuilder::packAtlases(const fs::path& outDir) {
    Log::info("Packing atlases to: {}", outDir.string());
    
    if (!fs::exists(outDir)) {
        fs::create_directories(outDir);
    }
    
    // Group assets by category
    std::unordered_map<std::string, std::vector<TileAsset>> categorizedAssets;
    for (const auto& asset : m_validated_assets) {
        categorizedAssets[asset.category].push_back(asset);
    }
    
    // Pack each category into its own atlas
    for (const auto& [category, assets] : categorizedAssets) {
        if (!assets.empty()) {
            packAtlas(category, assets);
        }
    }
    
    Log::info("Packed {} atlases.", m_atlases.size());
}

void TileLibraryBuilder::writeMetadata(const fs::path& outDir) {
    Log::info("Writing metadata to: {}", outDir.string());
    
    for (const auto& atlas : m_atlases) {
        writeAtlasJson(atlas, outDir);
    }
    
    // Write master index
    nlohmann::json masterIndex;
    masterIndex["atlases"] = nlohmann::json::array();
    
    for (const auto& atlas : m_atlases) {
        nlohmann::json atlasInfo;
        atlasInfo["name"] = atlas.atlasName;
        atlasInfo["texture"] = atlas.texturePath;
        atlasInfo["tileSize"] = {atlas.tileSize.x, atlas.tileSize.y};
        atlasInfo["atlasSize"] = {atlas.atlasSize.x, atlas.atlasSize.y};
        atlasInfo["tileCount"] = atlas.tiles.size();
        masterIndex["atlases"].push_back(atlasInfo);
    }
    
    std::ofstream indexFile(outDir / "atlas_index.json");
    indexFile << masterIndex.dump(2);
    
    Log::info("Wrote metadata for {} atlases.", m_atlases.size());
}

void TileLibraryBuilder::categorizeAssets() {
    Log::info("Categorizing assets...");
    
    for (auto& asset : m_assets) {
        if (asset.category == "unknown") {
            // Try to determine category from path and tags
            std::string pathStr = asset.path.string();
            std::transform(pathStr.begin(), pathStr.end(), pathStr.begin(), ::tolower);
            
            if (pathStr.find("floor") != std::string::npos) asset.category = "floor";
            else if (pathStr.find("wall") != std::string::npos) asset.category = "wall";
            else if (pathStr.find("ceiling") != std::string::npos) asset.category = "ceiling";
            else if (pathStr.find("prop") != std::string::npos) asset.category = "prop";
            else if (pathStr.find("trap") != std::string::npos) asset.category = "trap";
            else asset.category = "misc";
        }
    }
}

void TileLibraryBuilder::generateAtlasVariants(const std::string& category, int variantCount) {
    Log::info("Generating {} variants for category: {}", variantCount, category);
    
    auto it = std::find_if(m_validated_assets.begin(), m_validated_assets.end(),
                          [&category](const TileAsset& asset) { return asset.category == category; });
    
    if (it != m_validated_assets.end()) {
        generateVariants(variantCount);
    }
}

bool TileLibraryBuilder::isValidImageFile(const fs::path& path) const {
    std::string ext = path.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    return ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".tga";
}

std::string TileLibraryBuilder::extractLicenseFromFile(const fs::path& path) const {
    // Check for license.txt in same directory
    fs::path licenseFile = path.parent_path() / "license.txt";
    if (fs::exists(licenseFile)) {
        std::ifstream f(licenseFile);
        std::string license;
        std::getline(f, license);
        return license;
    }
    
    // Check filename for license info
    std::string filename = path.stem().string();
    if (filename.find("cc0") != std::string::npos) return "CC0";
    if (filename.find("cc-by") != std::string::npos) return "CC-BY";
    if (filename.find("mit") != std::string::npos) return "MIT";
    
    return "UNKNOWN";
}

void TileLibraryBuilder::applyVariantEffects(const TileAsset& base, const TileVariant& variant, 
                                           const fs::path& outputPath) {
    // This would implement actual image processing
    // For now, just log the operation
    Log::info("Applying variant effects to: {} -> {}", base.path.string(), outputPath.string());
}

bool TileLibraryBuilder::packAtlas(const std::string& category, const std::vector<TileAsset>& tiles) {
    Log::info("Packing atlas for category: {} with {} tiles", category, tiles.size());
    
    AtlasMetadata atlas;
    atlas.atlasName = "atlas_" + category;
    atlas.texturePath = atlas.atlasName + ".png";
    atlas.tileSize = m_tileSize;
    atlas.atlasSize = m_atlasSize;
    
    // Simple grid packing (in a real implementation, you'd use a proper bin packer)
    int tilesPerRow = atlas.atlasSize.x / atlas.tileSize.x;
    int tilesPerCol = atlas.atlasSize.y / atlas.tileSize.y;
    int maxTiles = tilesPerRow * tilesPerCol;
    
    if (tiles.size() > maxTiles) {
        Log::warn("Too many tiles for atlas: {} > {}", tiles.size(), maxTiles);
        return false;
    }
    
    // Pack tiles into grid
    for (size_t i = 0; i < tiles.size(); ++i) {
        int row = i / tilesPerRow;
        int col = i % tilesPerRow;
        
        AtlasTile tile;
        tile.id = tiles[i].path.stem().string();
        tile.license = tiles[i].license;
        tile.category = tiles[i].category;
        tile.size = tiles[i].size;
        
        // Calculate UV coordinates
        float u = static_cast<float>(col) / tilesPerRow;
        float v = static_cast<float>(row) / tilesPerCol;
        float uSize = 1.0f / tilesPerRow;
        float vSize = 1.0f / tilesPerCol;
        
        tile.uv = glm::vec4(u, v, u + uSize, v + vSize);
        atlas.tiles[tile.id] = tile;
    }
    
    m_atlases.push_back(atlas);
    return true;
}

void TileLibraryBuilder::writeAtlasJson(const AtlasMetadata& atlas, const fs::path& outDir) {
    nlohmann::json atlasJson;
    atlasJson["atlas"] = atlas.texturePath;
    atlasJson["tileSize"] = {atlas.tileSize.x, atlas.tileSize.y};
    atlasJson["atlasSize"] = {atlas.atlasSize.x, atlas.atlasSize.y};
    atlasJson["tiles"] = nlohmann::json::object();
    
    for (const auto& [id, tile] : atlas.tiles) {
        nlohmann::json tileJson;
        tileJson["uv"] = {tile.uv.x, tile.uv.y, tile.uv.z, tile.uv.w};
        tileJson["license"] = tile.license;
        tileJson["category"] = tile.category;
        tileJson["size"] = {tile.size.x, tile.size.y};
        atlasJson["tiles"][id] = tileJson;
    }
    
    fs::path jsonPath = outDir / (atlas.atlasName + ".json");
    std::ofstream f(jsonPath);
    f << atlasJson.dump(2);
    
    Log::info("Wrote atlas metadata: {}", jsonPath.string());
}

} // namespace MagiTech
