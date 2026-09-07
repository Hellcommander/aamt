#include "TileLibraryLuaBindings.hpp"
#include "TileLibraryBuilder.hpp"
#include "core/Log.hpp"
#include <memory>

namespace MagiTech {

static std::unique_ptr<TileLibraryBuilder> g_tileLibrary;

void TileLibraryLuaBindings::bind(sol::state& lua) {
    // Create global tile library instance
    g_tileLibrary = std::make_unique<TileLibraryBuilder>();
    
    // Bind TileLibraryBuilder class
    lua.new_usertype<TileLibraryBuilder>("TileLibraryBuilder",
        sol::constructors<TileLibraryBuilder()>(),
        
        // Core pipeline methods
        "loadManifest", &TileLibraryBuilder::loadManifest,
        "validateLicenses", &TileLibraryBuilder::validateLicenses,
        "generateVariants", &TileLibraryBuilder::generateVariants,
        "packAtlases", &TileLibraryBuilder::packAtlases,
        "writeMetadata", &TileLibraryBuilder::writeMetadata,
        
        // Utility methods
        "scanDirectory", &TileLibraryBuilder::scanDirectory,
        "categorizeAssets", &TileLibraryBuilder::categorizeAssets,
        "generateAtlasVariants", &TileLibraryBuilder::generateAtlasVariants,
        
        // Configuration
        "setTileSize", &TileLibraryBuilder::setTileSize,
        "setAtlasSize", &TileLibraryBuilder::setAtlasSize,
        "setAllowedLicenses", &TileLibraryBuilder::setAllowedLicenses,
        
        // Getters
        "getValidatedAssets", &TileLibraryBuilder::getValidatedAssets,
        "getAtlases", &TileLibraryBuilder::getAtlases
    );
    
    // Bind TileAsset struct
    lua.new_usertype<TileAsset>("TileAsset",
        sol::constructors<TileAsset()>(),
        "path", &TileAsset::path,
        "license", &TileAsset::license,
        "category", &TileAsset::category,
        "tags", &TileAsset::tags,
        "size", &TileAsset::size
    );
    
    // Bind AtlasMetadata struct
    lua.new_usertype<AtlasMetadata>("AtlasMetadata",
        sol::no_constructor,
        "atlasName", &AtlasMetadata::atlasName,
        "texturePath", &AtlasMetadata::texturePath,
        "tileSize", &AtlasMetadata::tileSize,
        "atlasSize", &AtlasMetadata::atlasSize,
        "tiles", &AtlasMetadata::tiles
    );
    
    // Bind AtlasTile struct
    lua.new_usertype<AtlasTile>("AtlasTile",
        sol::constructors<AtlasTile()>(),
        "id", &AtlasTile::id,
        "uv", &AtlasTile::uv,
        "license", &AtlasTile::license,
        "category", &AtlasTile::category,
        "size", &AtlasTile::size
    );
    
    // Create global TileLibrary namespace
    lua["TileLibrary"] = lua.create_table();
    
    // Add convenience functions
    lua["TileLibrary"]["getInstance"] = []() -> TileLibraryBuilder& {
        return *g_tileLibrary;
    };
    
    lua["TileLibrary"]["loadFromManifest"] = [](const std::string& manifestPath) {
        g_tileLibrary->loadManifest(manifestPath);
    };
    
    lua["TileLibrary"]["scanFromDirectory"] = [](const std::string& dirPath) {
        g_tileLibrary->scanDirectory(dirPath);
    };
    
    lua["TileLibrary"]["buildAtlases"] = [](const std::string& outDir, int variantCount = 3) {
        g_tileLibrary->validateLicenses({"CC0", "CC-BY", "MIT"});
        g_tileLibrary->generateVariants(variantCount);
        g_tileLibrary->packAtlases(outDir);
        g_tileLibrary->writeMetadata(outDir);
    };
    
    lua["TileLibrary"]["getTileUV"] = [](const std::string& tileId) -> sol::optional<glm::vec4> {
        for (const auto& atlas : g_tileLibrary->getAtlases()) {
            auto it = atlas.tiles.find(tileId);
            if (it != atlas.tiles.end()) {
                return it->second.uv;
            }
        }
        return sol::nullopt;
    };
    
    lua["TileLibrary"]["getTilesByCategory"] = [](const std::string& category) -> sol::table {
        sol::table result = lua.create_table();
        int index = 1;
        
        for (const auto& atlas : g_tileLibrary->getAtlases()) {
            for (const auto& [id, tile] : atlas.tiles) {
                if (tile.category == category) {
                    result[index] = id;
                    index++;
                }
            }
        }
        
        return result;
    };
    
    lua["TileLibrary"]["getAtlasInfo"] = [](const std::string& atlasName) -> sol::optional<sol::table> {
        for (const auto& atlas : g_tileLibrary->getAtlases()) {
            if (atlas.atlasName == atlasName) {
                sol::table info = lua.create_table();
                info["name"] = atlas.atlasName;
                info["texture"] = atlas.texturePath;
                info["tileSize"] = atlas.tileSize;
                info["atlasSize"] = atlas.atlasSize;
                info["tileCount"] = atlas.tiles.size();
                return info;
            }
        }
        return sol::nullopt;
    };
    
    Log::info("Tile Library Lua bindings initialized");
}

void TileLibraryLuaBindings::update(sol::state& lua) {
    // Update function for any per-frame operations
    // Currently empty, but could be used for async operations
}

} // namespace MagiTech 
