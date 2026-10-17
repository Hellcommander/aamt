#include "TileLibraryBuilder.hpp"
#include "core/Log.hpp"
#include "vendor/xxhash/xxhash.h"
#include <stb_image.h>        // implementation compiled once in core/StbImageImpl.cpp
#include <stb_image_write.h>  // implementation compiled once in core/StbImageImpl.cpp
#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <map>
#include <memory>
#include <random>
#include <set>
#include <type_traits>

namespace MagiTech {

namespace {

constexpr const char* kLogCategory = "TileLibrary";

// Field-by-field XXH64 accumulator (strings are length-prefixed).
class TileHasher {
public:
    TileHasher() { XXH64_reset(&m_state, 0); }
    template<typename T>
    TileHasher& add(const T& v) {
        static_assert(std::is_trivially_copyable_v<T>);
        XXH64_update(&m_state, &v, sizeof(T));
        return *this;
    }
    TileHasher& add(const std::string& s) {
        const uint64_t len = s.size();
        XXH64_update(&m_state, &len, sizeof(len));
        XXH64_update(&m_state, s.data(), s.size());
        return *this;
    }
    TileHasher& add(bool b) {
        const uint8_t v = b ? 1 : 0;
        XXH64_update(&m_state, &v, 1);
        return *this;
    }
    uint64_t digest() const { return XXH64_digest(&m_state); }

private:
    XXH64_state_t m_state;
};

std::string toLower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

// HSV (all components in [0,1]) to RGB.
glm::vec3 hsvToRgb(float h, float s, float v) {
    h = h - std::floor(h);
    const float c = v * s;
    const float hp = h * 6.0f;
    const float x = c * (1.0f - std::fabs(std::fmod(hp, 2.0f) - 1.0f));
    glm::vec3 rgb(0.0f);
    if (hp < 1.0f)      rgb = {c, x, 0};
    else if (hp < 2.0f) rgb = {x, c, 0};
    else if (hp < 3.0f) rgb = {0, c, x};
    else if (hp < 4.0f) rgb = {0, x, c};
    else if (hp < 5.0f) rgb = {x, 0, c};
    else                rgb = {c, 0, x};
    return rgb + glm::vec3(v - c);
}

struct StbFree {
    void operator()(unsigned char* p) const { stbi_image_free(p); }
};

// RGBA8 image loaded through stb_image.
struct RgbaImage {
    int width = 0;
    int height = 0;
    std::unique_ptr<unsigned char, StbFree> pixels;
    bool valid() const { return pixels != nullptr && width > 0 && height > 0; }
};

RgbaImage loadRgba(const fs::path& path) {
    RgbaImage img;
    int channels = 0;
    img.pixels.reset(stbi_load(path.string().c_str(), &img.width, &img.height, &channels, 4));
    return img;
}

uint8_t toByte(float v) {
    return static_cast<uint8_t>(std::clamp(v, 0.0f, 1.0f) * 255.0f + 0.5f);
}

} // namespace

// Hash function implementations
uint64_t TileAsset::hashKey() const {
    TileHasher h;
    h.add(path.generic_string()).add(license).add(category);
    h.add(static_cast<uint64_t>(tags.size()));
    for (const auto& tag : tags) h.add(tag);
    h.add(size);
    return h.digest();
}

uint64_t TileVariant::hashKey() const {
    TileHasher h;
    h.add(baseId).add(category).add(tintColor).add(noiseIntensity).add(rotation).add(mirrored);
    return h.digest();
}

uint64_t AtlasMetadata::hashKey() const {
    TileHasher h;
    h.add(atlasName).add(texturePath).add(tileSize).add(atlasSize);
    return h.digest();
}

void TileLibraryBuilder::loadManifest(const fs::path& manifestPath) {
    Log::info(kLogCategory, "Loading asset manifest from: {}", manifestPath.string());
    std::ifstream f(manifestPath);
    if (!f.is_open()) {
        Log::error(kLogCategory, "Failed to open manifest file: {}", manifestPath.string());
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
                const auto& size = item.at("size");
                asset.size = {size.at(0).get<int>(), size.at(1).get<int>()};
            }

            m_assets.push_back(asset);
        }
        Log::info(kLogCategory, "Loaded {} assets from manifest.", m_assets.size());
    } catch (const std::exception& e) {
        Log::error(kLogCategory, "Failed to parse manifest JSON: {}", e.what());
    }
}

void TileLibraryBuilder::scanDirectory(const fs::path& dirPath) {
    Log::info(kLogCategory, "Scanning directory for assets: {}", dirPath.string());
    m_assets.clear();

    if (!fs::exists(dirPath)) {
        Log::error(kLogCategory, "Directory does not exist: {}", dirPath.string());
        return;
    }

    for (const auto& entry : fs::recursive_directory_iterator(dirPath)) {
        if (entry.is_regular_file() && isValidImageFile(entry.path())) {
            TileAsset asset;
            asset.path = entry.path();
            asset.license = extractLicenseFromFile(entry.path());
            asset.category = "unknown"; // Will be categorized later
            asset.size = m_tileSize;

            // Simple category extraction based on filename
            const std::string filename = toLower(entry.path().stem().string());
            if (filename.find("floor") != std::string::npos) asset.category = "floor";
            else if (filename.find("wall") != std::string::npos) asset.category = "wall";
            else if (filename.find("ceiling") != std::string::npos) asset.category = "ceiling";
            else if (filename.find("prop") != std::string::npos) asset.category = "prop";
            else if (filename.find("trap") != std::string::npos) asset.category = "trap";

            m_assets.push_back(asset);
        }
    }

    Log::info(kLogCategory, "Found {} image assets in directory.", m_assets.size());
}

void TileLibraryBuilder::validateLicenses(const std::set<std::string>& allowList) {
    Log::info("Validating licenses against allowlist...");
    m_validated_assets.clear();

    for (const auto& asset : m_assets) {
        if (allowList.count(asset.license)) {
            m_validated_assets.push_back(asset);
        } else {
            Log::warn(kLogCategory, "Asset '{}' has a non-compliant license: {}",
                     asset.path.string(), asset.license);
        }
    }

    Log::info(kLogCategory, "Validated {} assets out of {} total.", m_validated_assets.size(), m_assets.size());
}

void TileLibraryBuilder::appendVariants(const TileAsset& asset, int variantCount, std::mt19937& gen) {
    std::uniform_real_distribution<float> unit(0.0f, 1.0f);
    std::uniform_real_distribution<float> noiseDist(0.0f, 0.3f);
    std::uniform_real_distribution<float> rotationDist(0.0f, 360.0f);
    std::uniform_int_distribution<int> mirrorDist(0, 1);

    for (int i = 0; i < variantCount; ++i) {
        TileVariant variant;
        variant.baseId = asset.path.stem().string();
        variant.category = asset.category;

        // Random tint: pick in HSV for pleasant colours, store as RGB
        const float hue = unit(gen);
        const float saturation = 0.3f + unit(gen) * 0.4f;
        const float value = 0.7f + unit(gen) * 0.3f;
        variant.tintColor = glm::vec4(hsvToRgb(hue, saturation, value), 1.0f);
        variant.noiseIntensity = noiseDist(gen);
        variant.rotation = rotationDist(gen);
        variant.mirrored = mirrorDist(gen) == 1;

        m_variants.push_back(variant);
    }
}

void TileLibraryBuilder::generateVariants(int variantCount) {
    Log::info(kLogCategory, "Generating {} variants per asset...", variantCount);
    m_variants.clear();

    std::random_device rd;
    std::mt19937 gen(rd());
    for (const auto& asset : m_validated_assets) {
        appendVariants(asset, variantCount, gen);
    }

    Log::info(kLogCategory, "Generated {} variants.", m_variants.size());
}

void TileLibraryBuilder::packAtlases(const fs::path& outDir) {
    Log::info(kLogCategory, "Packing atlases to: {}", outDir.string());

    std::error_code ec;
    fs::create_directories(outDir, ec);
    if (ec) {
        Log::error(kLogCategory, "Cannot create output directory {}: {}", outDir.string(), ec.message());
        return;
    }
    m_atlases.clear();

    // Group assets by category (sorted so atlas order is deterministic)
    std::map<std::string, std::vector<TileAsset>> categorizedAssets;
    for (const auto& asset : m_validated_assets) {
        categorizedAssets[asset.category].push_back(asset);
    }

    // Pack each category into its own atlas, splitting into pages when one atlas is full
    const int perRow = m_tileSize.x > 0 ? m_atlasSize.x / m_tileSize.x : 0;
    const int perCol = m_tileSize.y > 0 ? m_atlasSize.y / m_tileSize.y : 0;
    const size_t capacity = static_cast<size_t>(std::max(0, perRow * perCol));
    if (capacity == 0) {
        Log::error(kLogCategory, "Atlas size {}x{} cannot hold a {}x{} tile",
                   m_atlasSize.x, m_atlasSize.y, m_tileSize.x, m_tileSize.y);
        return;
    }
    for (const auto& [category, assets] : categorizedAssets) {
        for (size_t start = 0, page = 0; start < assets.size(); start += capacity, ++page) {
            const size_t end = std::min(assets.size(), start + capacity);
            std::vector<TileAsset> pageTiles(assets.begin() + start, assets.begin() + end);
            std::string name = "atlas_" + category + (page == 0 ? "" : "_" + std::to_string(page));
            if (packAtlas(name, pageTiles)) {
                // Compose the atlas texture from the tile images
                const AtlasMetadata& atlas = m_atlases.back();
                std::vector<unsigned char> pixels(static_cast<size_t>(atlas.atlasSize.x) * atlas.atlasSize.y * 4, 0);
                std::set<std::string> drawn; // duplicate ids keep the first image, as in packAtlas
                for (const auto& tileAsset : pageTiles) {
                    const std::string id = tileAsset.path.stem().string();
                    if (!drawn.insert(id).second) continue;
                    const AtlasTile& tile = atlas.tiles.at(id);
                    RgbaImage img = loadRgba(tileAsset.path);
                    if (!img.valid()) {
                        Log::warn(kLogCategory, "Cannot read tile image {}: {}", tileAsset.path.string(),
                                  stbi_failure_reason() ? stbi_failure_reason() : "unknown error");
                        continue;
                    }
                    const int x0 = static_cast<int>(std::lround(tile.uv.x * atlas.atlasSize.x));
                    const int y0 = static_cast<int>(std::lround(tile.uv.y * atlas.atlasSize.y));
                    // Nearest-neighbour scale into the tile cell
                    for (int y = 0; y < atlas.tileSize.y; ++y) {
                        const int sy = y * img.height / atlas.tileSize.y;
                        for (int x = 0; x < atlas.tileSize.x; ++x) {
                            const int sx = x * img.width / atlas.tileSize.x;
                            const unsigned char* src = img.pixels.get() + (static_cast<size_t>(sy) * img.width + sx) * 4;
                            unsigned char* dst = pixels.data() +
                                (static_cast<size_t>(y0 + y) * atlas.atlasSize.x + (x0 + x)) * 4;
                            std::copy(src, src + 4, dst);
                        }
                    }
                }
                const fs::path texturePath = outDir / atlas.texturePath;
                if (!stbi_write_png(texturePath.string().c_str(), atlas.atlasSize.x, atlas.atlasSize.y, 4,
                                    pixels.data(), atlas.atlasSize.x * 4)) {
                    Log::error(kLogCategory, "Failed to write atlas texture: {}", texturePath.string());
                }
            }
        }
    }

    // Render the generated variants next to the atlases
    if (!m_variants.empty()) {
        const fs::path variantDir = outDir / "variants";
        fs::create_directories(variantDir, ec);
        std::unordered_map<std::string, int> variantIndex;
        for (const auto& variant : m_variants) {
            auto base = std::find_if(m_validated_assets.begin(), m_validated_assets.end(),
                                     [&](const TileAsset& a) { return a.path.stem().string() == variant.baseId; });
            if (base == m_validated_assets.end()) continue;
            const int index = variantIndex[variant.baseId]++;
            applyVariantEffects(*base, variant, variantDir / (variant.baseId + "_v" + std::to_string(index) + ".png"));
        }
    }

    Log::info(kLogCategory, "Packed {} atlases.", m_atlases.size());
}

void TileLibraryBuilder::writeMetadata(const fs::path& outDir) {
    Log::info(kLogCategory, "Writing metadata to: {}", outDir.string());
    std::error_code ec;
    fs::create_directories(outDir, ec);

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

    Log::info(kLogCategory, "Wrote metadata for {} atlases.", m_atlases.size());
}

void TileLibraryBuilder::categorizeAssets() {
    Log::info("Categorizing assets...");

    for (auto& asset : m_assets) {
        if (asset.category == "unknown") {
            // Try to determine category from path and tags
            const std::string pathStr = toLower(asset.path.string());
            auto hasTag = [&asset](const char* t) {
                return std::any_of(asset.tags.begin(), asset.tags.end(),
                                   [t](const std::string& tag) { return toLower(tag) == t; });
            };
            auto matches = [&](const char* key) { return pathStr.find(key) != std::string::npos || hasTag(key); };

            if (matches("floor")) asset.category = "floor";
            else if (matches("wall")) asset.category = "wall";
            else if (matches("ceiling")) asset.category = "ceiling";
            else if (matches("prop")) asset.category = "prop";
            else if (matches("trap")) asset.category = "trap";
            else asset.category = "misc";
        }
    }
}

void TileLibraryBuilder::generateAtlasVariants(const std::string& category, int variantCount) {
    Log::info(kLogCategory, "Generating {} variants for category: {}", variantCount, category);

    // Replace only this category's variants
    m_variants.erase(std::remove_if(m_variants.begin(), m_variants.end(),
                                    [&category](const TileVariant& v) { return v.category == category; }),
                     m_variants.end());

    std::random_device rd;
    std::mt19937 gen(rd());
    size_t generated = 0;
    for (const auto& asset : m_validated_assets) {
        if (asset.category != category) continue;
        appendVariants(asset, variantCount, gen);
        generated += static_cast<size_t>(std::max(0, variantCount));
    }

    if (generated == 0) {
        Log::warn(kLogCategory, "No validated assets in category: {}", category);
    }
}

bool TileLibraryBuilder::isValidImageFile(const fs::path& path) const {
    const std::string ext = toLower(path.extension().string());
    return ext == ".png" || ext == ".jpg" || ext == ".jpeg" || ext == ".tga";
}

std::string TileLibraryBuilder::extractLicenseFromFile(const fs::path& path) const {
    // Check for license.txt in same directory
    fs::path licenseFile = path.parent_path() / "license.txt";
    if (fs::exists(licenseFile)) {
        std::ifstream f(licenseFile);
        std::string license;
        std::getline(f, license);
        while (!license.empty() && std::isspace(static_cast<unsigned char>(license.back()))) license.pop_back();
        return license;
    }

    // Check filename for license info
    const std::string filename = toLower(path.stem().string());
    if (filename.find("cc0") != std::string::npos) return "CC0";
    if (filename.find("cc-by") != std::string::npos) return "CC-BY";
    if (filename.find("mit") != std::string::npos) return "MIT";

    return "UNKNOWN";
}

void TileLibraryBuilder::applyVariantEffects(const TileAsset& base, const TileVariant& variant,
                                           const fs::path& outputPath) {
    RgbaImage img = loadRgba(base.path);
    if (!img.valid()) {
        Log::warn(kLogCategory, "Cannot read tile image {} for variant", base.path.string());
        return;
    }

    const int w = img.width;
    const int h = img.height;
    std::vector<unsigned char> out(static_cast<size_t>(w) * h * 4, 0);
    const float angle = glm::radians(variant.rotation);
    const float cs = std::cos(angle);
    const float sn = std::sin(angle);
    const float cx = (w - 1) * 0.5f;
    const float cy = (h - 1) * 0.5f;
    // Deterministic per-variant noise
    std::mt19937 noiseGen(static_cast<uint32_t>(variant.hashKey()));
    std::uniform_real_distribution<float> noise(-1.0f, 1.0f);

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // Inverse-map the destination pixel: rotate about the centre, then mirror
            const float dx = x - cx;
            const float dy = y - cy;
            float sxf = cs * dx + sn * dy + cx;
            const float syf = -sn * dx + cs * dy + cy;
            if (variant.mirrored) sxf = (w - 1) - sxf;
            const int sx = static_cast<int>(std::lround(sxf));
            const int sy = static_cast<int>(std::lround(syf));
            unsigned char* dst = out.data() + (static_cast<size_t>(y) * w + x) * 4;
            if (sx < 0 || sy < 0 || sx >= w || sy >= h) continue; // transparent outside the source

            const unsigned char* src = img.pixels.get() + (static_cast<size_t>(sy) * w + sx) * 4;
            const float n = variant.noiseIntensity * noise(noiseGen);
            for (int c = 0; c < 3; ++c) {
                dst[c] = toByte(src[c] / 255.0f * variant.tintColor[c] + n);
            }
            dst[3] = toByte(src[3] / 255.0f * variant.tintColor.a);
        }
    }

    std::error_code ec;
    if (outputPath.has_parent_path()) fs::create_directories(outputPath.parent_path(), ec);
    if (!stbi_write_png(outputPath.string().c_str(), w, h, 4, out.data(), w * 4)) {
        Log::error(kLogCategory, "Failed to write variant image: {}", outputPath.string());
    }
}

bool TileLibraryBuilder::packAtlas(const std::string& atlasName, const std::vector<TileAsset>& tiles) {
    Log::info(kLogCategory, "Packing atlas {} with {} tiles", atlasName, tiles.size());

    AtlasMetadata atlas;
    atlas.atlasName = atlasName;
    atlas.texturePath = atlas.atlasName + ".png";
    atlas.tileSize = m_tileSize;
    atlas.atlasSize = m_atlasSize;

    // Simple grid packing: every tile occupies one tileSize cell
    if (atlas.tileSize.x <= 0 || atlas.tileSize.y <= 0) {
        Log::warn(kLogCategory, "Invalid tile size {}x{}", atlas.tileSize.x, atlas.tileSize.y);
        return false;
    }
    const int tilesPerRow = atlas.atlasSize.x / atlas.tileSize.x;
    const int tilesPerCol = atlas.atlasSize.y / atlas.tileSize.y;
    const size_t maxTiles = static_cast<size_t>(std::max(0, tilesPerRow * tilesPerCol));

    if (tiles.size() > maxTiles) {
        Log::warn(kLogCategory, "Too many tiles for atlas: {} > {}", tiles.size(), maxTiles);
        return false;
    }

    // Pack tiles into grid
    for (size_t i = 0; i < tiles.size(); ++i) {
        const int row = static_cast<int>(i) / tilesPerRow;
        const int col = static_cast<int>(i) % tilesPerRow;

        AtlasTile tile;
        tile.id = tiles[i].path.stem().string();
        tile.license = tiles[i].license;
        tile.category = tiles[i].category;
        tile.size = tiles[i].size;

        // UVs of the cell in pixel-exact atlas space
        const float u = static_cast<float>(col * atlas.tileSize.x) / atlas.atlasSize.x;
        const float v = static_cast<float>(row * atlas.tileSize.y) / atlas.atlasSize.y;
        const float uSize = static_cast<float>(atlas.tileSize.x) / atlas.atlasSize.x;
        const float vSize = static_cast<float>(atlas.tileSize.y) / atlas.atlasSize.y;

        tile.uv = glm::vec4(u, v, u + uSize, v + vSize);
        if (atlas.tiles.count(tile.id)) {
            Log::warn(kLogCategory, "Duplicate tile id '{}' in atlas {}; keeping the first", tile.id, atlasName);
            continue;
        }
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

    Log::info(kLogCategory, "Wrote atlas metadata: {}", jsonPath.string());
}

} // namespace MagiTech
