#include "TileLibraryLuaBindings.hpp"
#include "TileLibraryBuilder.hpp"
#include "core/Log.hpp"
#include <memory>
#include <set>

namespace MagiTech {

static std::unique_ptr<TileLibraryBuilder> g_tileLibrary;

namespace {

// Lua passes license lists as arrays ({"CC0", "MIT"}).
std::set<std::string> toStringSet(const sol::table& t) {
    std::set<std::string> out;
    for (const auto& [key, value] : t) {
        if (value.is<std::string>()) out.insert(value.as<std::string>());
    }
    return out;
}

} // namespace

void TileLibraryLuaBindings::bind(sol::state& lua) {
    // Create global tile library instance
    g_tileLibrary = std::make_unique<TileLibraryBuilder>();
    
    // Bind TileLibraryBuilder class. Paths, sizes and license sets are taken
    // as Lua strings, numbers and arrays and converted here.
    lua.new_usertype<TileLibraryBuilder>("TileLibraryBuilder",
        sol::constructors<TileLibraryBuilder()>(),
        
        // Core pipeline methods
        "loadManifest", [](TileLibraryBuilder& b, const std::string& path) { b.loadManifest(path); },
        "validateLicenses", [](TileLibraryBuilder& b, sol::optional<sol::table> allow) {
            b.validateLicenses(allow ? toStringSet(*allow) : b.getAllowedLicenses());
        },
        "generateVariants", &TileLibraryBuilder::generateVariants,
        "packAtlases", [](TileLibraryBuilder& b, const std::string& outDir) { b.packAtlases(outDir); },
        "writeMetadata", [](TileLibraryBuilder& b, const std::string& outDir) { b.writeMetadata(outDir); },
        
        // Utility methods
        "scanDirectory", [](TileLibraryBuilder& b, const std::string& dir) { b.scanDirectory(dir); },
        "categorizeAssets", &TileLibraryBuilder::categorizeAssets,
        "generateAtlasVariants", &TileLibraryBuilder::generateAtlasVariants,
        
        // Configuration
        "setTileSize", [](TileLibraryBuilder& b, int w, int h) { b.setTileSize({w, h}); },
        "setAtlasSize", [](TileLibraryBuilder& b, int w, int h) { b.setAtlasSize({w, h}); },
        "setAllowedLicenses", [](TileLibraryBuilder& b, const sol::table& licenses) {
            b.setAllowedLicenses(toStringSet(licenses));
        },
        
        // Getters
        "getValidatedAssets", &TileLibraryBuilder::getValidatedAssets,
        "getAtlases", &TileLibraryBuilder::getAtlases
    );
    
    // Bind TileAsset struct
    lua.new_usertype<TileAsset>("TileAsset",
        sol::constructors<TileAsset()>(),
        "path", sol::property(
            [](const TileAsset& a) { return a.path.string(); },
            [](TileAsset& a, const std::string& p) { a.path = p; }),
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
        // id -> AtlasTile, copied into a Lua table (unordered_map members
        // cannot be bound as sol containers in this sol2 build)
        "tiles", sol::readonly_property([](const AtlasMetadata& a, sol::this_state ts) {
            sol::state_view view(ts);
            sol::table t = view.create_table();
            for (const auto& [id, tile] : a.tiles) t[id] = tile;
            return t;
        })
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
    
    lua["TileLibrary"]["buildAtlases"] = [](const std::string& outDir, sol::optional<int> variantCount) {
        g_tileLibrary->validateLicenses(g_tileLibrary->getAllowedLicenses()); // default: CC0, CC-BY, MIT
        g_tileLibrary->generateVariants(variantCount.value_or(3));
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
    
    lua["TileLibrary"]["getTilesByCategory"] = [](sol::this_state ts, const std::string& category) -> sol::table {
        sol::state_view lua(ts);
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
    
    lua["TileLibrary"]["getAtlasInfo"] = [](sol::this_state ts, const std::string& atlasName) -> sol::optional<sol::table> {
        sol::state_view lua(ts);
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
