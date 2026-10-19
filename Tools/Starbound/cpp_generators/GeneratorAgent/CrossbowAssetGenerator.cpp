#include "CrossbowAssetGenerator.hpp"
#include "CrossbowAssetFactory.hpp"
#include "core/Log.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <stb_image_write.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace MagiTech {
namespace Crossbows {

// Global asset generator instance
std::unique_ptr<CrossbowAssetGenerator> g_assetGenerator;

namespace {

// ---------------------------------------------------------------------------
// Minimal RGBA canvas for the procedural fallback sprites
struct Canvas {
    int width;
    int height;
    std::vector<uint8_t> pixels;

    Canvas(int w, int h) : width(w), height(h), pixels(static_cast<size_t>(w) * h * 4, 0) {}

    void set(int x, int y, uint32_t rgba) {
        if (x < 0 || y < 0 || x >= width || y >= height) return;
        uint8_t* p = &pixels[(static_cast<size_t>(y) * width + x) * 4];
        p[0] = static_cast<uint8_t>(rgba >> 24);
        p[1] = static_cast<uint8_t>(rgba >> 16);
        p[2] = static_cast<uint8_t>(rgba >> 8);
        p[3] = static_cast<uint8_t>(rgba);
    }

    void line(float x0, float y0, float x1, float y1, uint32_t rgba, int thickness = 1) {
        const int steps = static_cast<int>(std::max(std::abs(x1 - x0), std::abs(y1 - y0))) + 1;
        for (int i = 0; i <= steps; ++i) {
            const float t = steps == 0 ? 0.0f : static_cast<float>(i) / static_cast<float>(steps);
            const int x = static_cast<int>(std::lround(x0 + (x1 - x0) * t));
            const int y = static_cast<int>(std::lround(y0 + (y1 - y0) * t));
            for (int dy = 0; dy < thickness; ++dy)
                for (int dx = 0; dx < thickness; ++dx) set(x + dx, y + dy, rgba);
        }
    }

    void rect(int x0, int y0, int x1, int y1, uint32_t rgba) {
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) set(x, y, rgba);
    }

    bool savePng(const std::string& path) const {
        return stbi_write_png(path.c_str(), width, height, 4, pixels.data(), width * 4) != 0;
    }
};

// Colour picked from a material name (wood/metal/fiberglass/synthetic/feather...)
uint32_t materialColor(const std::string& material) {
    std::string m;
    for (unsigned char c : material) m.push_back(static_cast<char>(std::tolower(c)));
    if (m.find("wood") != std::string::npos || m.find("oak") != std::string::npos) return 0x8B5A2BFF;
    if (m.find("steel") != std::string::npos || m.find("metal") != std::string::npos) return 0x9AA4B0FF;
    if (m.find("carbon") != std::string::npos) return 0x2B2B30FF;
    if (m.find("fiberglass") != std::string::npos) return 0xD8D2B0FF;
    if (m.find("feather") != std::string::npos) return 0xF2F2F2FF;
    if (m.find("plastic") != std::string::npos) return 0xC83C3CFF;
    if (m.find("hemp") != std::string::npos) return 0xC8B48CFF;
    if (m.find("synthetic") != std::string::npos || m.find("kevlar") != std::string::npos) return 0xE6D25AFF;
    return 0xB4B4B4FF;
}

// Draws one crossbow frame (side view) into the canvas at horizontal offset `ox`; `draw` in [0,1]
void drawCrossbowFrame(Canvas& c, int ox, const CrossbowParams& p, float draw) {
    const uint32_t stock = materialColor(p.stockMaterial);
    const uint32_t limb = materialColor(p.limbMaterial);
    const uint32_t string = materialColor(p.stringMaterial);
    // Stock: horizontal bar
    c.rect(ox + 4, 15, ox + 26, 17, stock);
    c.rect(ox + 4, 18, ox + 9, 21, stock);          // grip
    // Limbs: arc at the front, bending more when drawn
    const float bend = 2.0f + 3.0f * draw;
    c.line(ox + 24.0f, 16.0f, ox + 26.0f - bend, 5.0f, limb, 2);
    c.line(ox + 24.0f, 16.0f, ox + 26.0f - bend, 27.0f, limb, 2);
    // String from limb tips to the nocking point
    const float nock = 24.0f - 12.0f * draw;
    c.line(ox + 26.0f - bend, 5.0f, ox + nock, 16.0f, string);
    c.line(ox + 26.0f - bend, 27.0f, ox + nock, 16.0f, string);
}

void drawProjectile(Canvas& c, float length01, uint32_t shaft, uint32_t fletch, bool fletched, bool barbed) {
    const int w = c.width, h = c.height;
    const int y = h / 2;
    const int x0 = static_cast<int>(w * (1.0f - length01) * 0.5f);
    const int x1 = w - 1 - x0;
    c.rect(x0, y, x1 - 4, y, shaft);
    // Tip
    c.line(static_cast<float>(x1 - 4), static_cast<float>(y - 2), static_cast<float>(x1), static_cast<float>(y), 0xD0D0D8FF);
    c.line(static_cast<float>(x1 - 4), static_cast<float>(y + 2), static_cast<float>(x1), static_cast<float>(y), 0xD0D0D8FF);
    if (barbed) {
        c.line(static_cast<float>(x1 - 5), static_cast<float>(y - 3), static_cast<float>(x1 - 3), static_cast<float>(y - 1), 0xA0A0A8FF);
        c.line(static_cast<float>(x1 - 5), static_cast<float>(y + 3), static_cast<float>(x1 - 3), static_cast<float>(y + 1), 0xA0A0A8FF);
    }
    if (fletched) {
        c.line(static_cast<float>(x0), static_cast<float>(y - 3), static_cast<float>(x0 + 4), static_cast<float>(y), fletch);
        c.line(static_cast<float>(x0), static_cast<float>(y + 3), static_cast<float>(x0 + 4), static_cast<float>(y), fletch);
    }
}

bool copyIfPresent(const std::string& from, const std::string& to) {
    std::error_code ec;
    if (from.empty() || !std::filesystem::exists(from, ec) || std::filesystem::file_size(from, ec) == 0) return false;
    std::filesystem::copy_file(from, to, std::filesystem::copy_options::overwrite_existing, ec);
    return !ec;
}

nlohmann::json levelValue(const std::string& level) {
    try {
        size_t used = 0;
        const double v = std::stod(level, &used);
        if (used == level.size()) return v;
    } catch (const std::exception&) {
    }
    return level;
}

} // namespace

CrossbowAssetGenerator::CrossbowAssetGenerator() {
    outputBasePath = "items/active/weapons/crossbow/";
}

void CrossbowAssetGenerator::initialize(std::shared_ptr<AIArt::AIArtGenerator> generator) {
    aiGenerator = std::move(generator);
}

CrossbowAssetGenerator::AssetOutput CrossbowAssetGenerator::generateCrossbowAssets(
    const CrossbowParams& params, const ItemConfig& config) {

    AssetOutput output;
    std::string baseName = sanitizeFilename(params.id);

    // Create output directory
    std::string outputDir = outputBasePath + baseName + "/";
    createDirectory(outputDir);

    // Generate all asset files
    output.itemFile = outputDir + baseName + ".activeitem";
    output.framesFile = outputDir + generateAssetName(baseName, "full.frames");
    output.spriteFile = outputDir + generateAssetName(baseName, "full.png");
    output.iconFile = outputDir + generateAssetName(baseName, "icon.png");
    output.behaviorFile = outputDir + baseName + ".lua";
    output.effectFile = outputDir + baseName + "_effects.json";

    writeFile(output.itemFile, generateActiveItemJSON(params, config));
    writeFile(output.framesFile, generateFramesJSON(baseName + "full", 8)); // 8 draw frames
    writeFile(output.behaviorFile, generateBehaviorScript(params, config));
    writeFile(output.effectFile, generateEffectConfig(params, config));

    // Sprites: AI art when enabled and available, procedural fallback otherwise
    bool haveArt = false;
    if (config.useAIArt && aiGenerator) {
        AIArt::ArtOutput art = generateCrossbowArt(params, config);
        if (art.success) {
            haveArt = copyIfPresent(art.spriteFile, output.spriteFile) && copyIfPresent(art.iconFile, output.iconFile);
            output.metadataFile = art.metadataFile;
        } else {
            Log::warn("CrossbowAsset", "AI art failed for {}: {}", params.id, art.errorMessage);
        }
    }
    if (!haveArt) {
        generateFallbackSprite(output.spriteFile, params);
        generateFallbackIcon(output.iconFile, config.itemName);
    }

    Log::info("CrossbowAsset", "Generated crossbow assets for: {}", params.id);
    return output;
}

CrossbowAssetGenerator::AssetOutput CrossbowAssetGenerator::generateBoltAssets(
    const BoltParams& params, const ItemConfig& config) {

    AssetOutput output;
    std::string baseName = sanitizeFilename(params.id);

    // Create output directory
    std::string outputDir = outputBasePath + "ammo/" + baseName + "/";
    createDirectory(outputDir);

    // Generate projectile file
    output.projectileFile = outputDir + baseName + ".projectile";
    output.effectFile = outputDir + baseName + "_effects.json";

    writeFile(output.projectileFile, generateProjectileJSON(params, config));
    writeFile(output.effectFile, generateEffectConfig(params, config));

    // Generate sprite files
    output.spriteFile = outputDir + baseName + ".png";
    output.iconFile = outputDir + generateAssetName(baseName, "icon.png");

    bool haveArt = false;
    if (config.useAIArt && aiGenerator) {
        AIArt::ArtOutput art = generateBoltArt(params, config);
        if (art.success) {
            haveArt = copyIfPresent(art.spriteFile, output.spriteFile) && copyIfPresent(art.iconFile, output.iconFile);
            output.metadataFile = art.metadataFile;
        } else {
            Log::warn("CrossbowAsset", "AI art failed for {}: {}", params.id, art.errorMessage);
        }
    }
    if (!haveArt) {
        generateFallbackSprite(output.spriteFile, params);
        generateFallbackIcon(output.iconFile, config.itemName);
    }

    Log::info("CrossbowAsset", "Generated bolt assets for: {}", params.id);
    return output;
}

CrossbowAssetGenerator::AssetOutput CrossbowAssetGenerator::generateArrowAssets(
    const ArrowParams& params, const ItemConfig& config) {

    AssetOutput output;
    std::string baseName = sanitizeFilename(params.id);

    // Create output directory
    std::string outputDir = outputBasePath + "ammo/" + baseName + "/";
    createDirectory(outputDir);

    // Generate projectile file
    output.projectileFile = outputDir + baseName + ".projectile";
    output.effectFile = outputDir + baseName + "_effects.json";

    writeFile(output.projectileFile, generateProjectileJSON(params, config));
    writeFile(output.effectFile, generateEffectConfig(params, config));

    // Generate sprite files
    output.spriteFile = outputDir + baseName + ".png";
    output.iconFile = outputDir + generateAssetName(baseName, "icon.png");

    bool haveArt = false;
    if (config.useAIArt && aiGenerator) {
        AIArt::ArtOutput art = generateArrowArt(params, config);
        if (art.success) {
            haveArt = copyIfPresent(art.spriteFile, output.spriteFile) && copyIfPresent(art.iconFile, output.iconFile);
            output.metadataFile = art.metadataFile;
        } else {
            Log::warn("CrossbowAsset", "AI art failed for {}: {}", params.id, art.errorMessage);
        }
    }
    if (!haveArt) {
        generateFallbackSprite(output.spriteFile, params);
        generateFallbackIcon(output.iconFile, config.itemName);
    }

    Log::info("CrossbowAsset", "Generated arrow assets for: {}", params.id);
    return output;
}

std::string CrossbowAssetGenerator::generateActiveItemJSON(const CrossbowParams& params, const ItemConfig& config) {
    const std::string base = sanitizeFilename(params.id);
    const std::string scriptPath = "/" + outputBasePath + base + "/" + base + ".lua";

    nlohmann::json item = nlohmann::json::parse(getCrossbowItemTemplate());
    item["itemName"] = config.itemName.empty() ? base : config.itemName;
    item["description"] = config.description.empty() ? generateDescription(params) : config.description;
    item["rarity"] = config.rarity.empty() ? "Common" : config.rarity;
    item["category"] = config.category.empty() ? "crossbow" : config.category;
    item["level"] = levelValue(config.level);
    item["inventoryIcon"] = generateAssetName(base, "icon.png");
    item["animation"] = base + ".animation";
    item["animationParts"]["bow"] = generateAssetName(base, "full.png");
    item["scripts"] = nlohmann::json::array({scriptPath});

    auto& ability = item["primaryAbility"];
    ability["abilityType"] = config.abilityType;
    ability["damageConfig"]["damageKind"] = config.damageType;
    ability["damageConfig"]["damage"] = config.damage;
    ability["fireTime"] = config.fireRate > 0.0f ? 1.0f / config.fireRate : 1.0f;
    ability["projectileParameters"]["power"] = params.drawWeight * 0.01f;
    ability["projectileType"] = config.projectileTypes.empty() ? std::string("crossbowbolt") : config.projectileTypes.front();

    item["crossbowData"] = {
        {"drawLength", params.drawLength},
        {"drawWeight", params.drawWeight},
        {"autoReload", params.autoReload},
        {"reloadTime", params.reloadTime},
        {"stockMaterial", params.stockMaterial},
        {"limbMaterial", params.limbMaterial},
        {"stringMaterial", params.stringMaterial}
    };
    item["magitechIntegration"] = {
        {"behaviorSystem", config.behaviorSystem},
        {"behaviorModule", integrateWithBehaviorSystem(config)},
        {"effectSystem", config.effectSystem},
        {"effectModule", integrateWithEffectSystem(config)},
        {"materialSystem", config.materialSystem},
        {"materialModule", integrateWithMaterialSystem(config)},
        {"specialEffects", config.specialEffects}
    };
    return item.dump(2);
}

std::string CrossbowAssetGenerator::generateProjectileJSON(const BoltParams& params, const ItemConfig& config) {
    nlohmann::json projectile = nlohmann::json::parse(getProjectileTemplate());
    projectile["projectileName"] = config.itemName.empty() ? sanitizeFilename(params.id) : config.itemName;
    projectile["projectileType"] = "bolt";
    projectile["damageKind"] = config.damageType;
    projectile["damage"] = config.damage;
    projectile["speed"] = params.length * 100.0f;
    projectile["knockback"] = 10;
    projectile["piercing"] = params.barbedTip;
    projectile["timeToLive"] = 2.0;
    projectile["image"] = sanitizeFilename(params.id) + ".png";
    projectile["actionOnReap"] = nlohmann::json::array({
        {{"action", "projectile"}, {"type", "damage"}, {"damage", config.damage * 0.5f}}
    });
    projectile["boltData"] = {
        {"length", params.length},
        {"shaftRadius", params.shaftRadius},
        {"useFletching", params.useFletching},
        {"fletchMaterial", params.fletchMaterial},
        {"fletchLength", params.fletchLength},
        {"tipMass", params.tipMass},
        {"barbedTip", params.barbedTip}
    };
    projectile["magitechIntegration"] = {
        {"effectSystem", config.effectSystem},
        {"specialEffects", config.specialEffects}
    };
    return projectile.dump(2);
}

std::string CrossbowAssetGenerator::generateProjectileJSON(const ArrowParams& params, const ItemConfig& config) {
    nlohmann::json projectile = nlohmann::json::parse(getProjectileTemplate());
    projectile["projectileName"] = config.itemName.empty() ? sanitizeFilename(params.id) : config.itemName;
    projectile["projectileType"] = "arrow";
    projectile["damageKind"] = config.damageType;
    projectile["damage"] = config.damage;
    projectile["speed"] = params.shaftLength * 80.0f;
    projectile["knockback"] = 8;
    projectile["piercing"] = false;
    projectile["timeToLive"] = 3.0;
    projectile["image"] = sanitizeFilename(params.id) + ".png";
    projectile["actionOnReap"] = nlohmann::json::array({
        {{"action", "projectile"}, {"type", "damage"}, {"damage", config.damage * 0.3f}}
    });
    projectile["arrowData"] = {
        {"shaftLength", params.shaftLength},
        {"shaftDiameter", params.shaftDiameter},
        {"spineRating", params.spineRating},
        {"useFletching", params.useFletching},
        {"fletchStyle", params.fletchStyle},
        {"nockSize", params.nockSize},
        {"tipMass", params.tipMass}
    };
    projectile["magitechIntegration"] = {
        {"effectSystem", config.effectSystem},
        {"specialEffects", config.specialEffects}
    };
    return projectile.dump(2);
}

std::string CrossbowAssetGenerator::generateBehaviorScript(const CrossbowParams& params, const ItemConfig& config) {
    std::string script = getBehaviorTemplate();

    // Effect set as a Lua table literal: { ["explosive"] = true, ... }
    std::ostringstream effects;
    effects << "{";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        effects << (i ? ", " : " ") << "[\"" << config.specialEffects[i] << "\"] = true";
    }
    effects << (config.specialEffects.empty() ? "}" : " }");

    auto replaceAll = [&script](const std::string& key, const std::string& value) {
        for (size_t pos = script.find(key); pos != std::string::npos; pos = script.find(key, pos + value.size())) {
            script.replace(pos, key.size(), value);
        }
    };
    replaceAll("%ID%", params.id);
    replaceAll("%BEHAVIOR_SYSTEM%", config.behaviorSystem);
    replaceAll("%EFFECT_SYSTEM%", config.effectSystem);
    replaceAll("%MATERIAL_SYSTEM%", config.materialSystem);
    replaceAll("%SPECIAL_EFFECTS%", effects.str());
    return script;
}

std::string CrossbowAssetGenerator::generateEffectConfig(const CrossbowParams& params, const ItemConfig& config) {
    nlohmann::json effect = nlohmann::json::parse(getEffectTemplate());
    effect["crossbowId"] = params.id;
    effect["effectSystem"] = config.effectSystem;
    effect["specialEffects"] = config.specialEffects;
    effect["materialEffects"] = {
        {"stock", params.stockMaterial},
        {"limb", params.limbMaterial},
        {"string", params.stringMaterial}
    };
    effect["crossbowData"] = {
        {"drawLength", params.drawLength},
        {"drawWeight", params.drawWeight},
        {"autoReload", params.autoReload},
        {"reloadTime", params.reloadTime}
    };
    return effect.dump(2);
}

std::string CrossbowAssetGenerator::generateEffectConfig(const BoltParams& params, const ItemConfig& config) {
    nlohmann::json effect = nlohmann::json::parse(getEffectTemplate());
    effect["projectileId"] = params.id;
    effect["projectileKind"] = "bolt";
    effect["effectSystem"] = config.effectSystem;
    effect["specialEffects"] = config.specialEffects;
    effect["materialEffects"] = {{"fletching", params.fletchMaterial}};
    effect["projectileData"] = {
        {"length", params.length},
        {"tipMass", params.tipMass},
        {"barbedTip", params.barbedTip}
    };
    return effect.dump(2);
}

std::string CrossbowAssetGenerator::generateEffectConfig(const ArrowParams& params, const ItemConfig& config) {
    nlohmann::json effect = nlohmann::json::parse(getEffectTemplate());
    effect["projectileId"] = params.id;
    effect["projectileKind"] = "arrow";
    effect["effectSystem"] = config.effectSystem;
    effect["specialEffects"] = config.specialEffects;
    effect["materialEffects"] = {{"fletching", params.fletchStyle}};
    effect["projectileData"] = {
        {"shaftLength", params.shaftLength},
        {"spineRating", params.spineRating},
        {"tipMass", params.tipMass}
    };
    return effect.dump(2);
}

std::string CrossbowAssetGenerator::generateFramesJSON(const std::string& spriteName, int frameCount) {
    // Starbound .frames format: a grid of 32x32 cells named <sprite>.<index>
    nlohmann::json frames = nlohmann::json::parse(getFramesTemplate());
    nlohmann::json names = nlohmann::json::array();
    for (int i = 0; i < frameCount; ++i) {
        names.push_back(spriteName + "." + std::to_string(i));
    }
    frames["frameGrid"]["dimensions"] = {frameCount, 1};
    frames["frameGrid"]["names"] = nlohmann::json::array({names});
    return frames.dump(2);
}

// ---------------------------------------------------------------------------
// AI art integration

AIArt::ArtOutput CrossbowAssetGenerator::generateCrossbowArt(const CrossbowParams& params, const ItemConfig& config) {
    if (!aiGenerator) {
        AIArt::ArtOutput out{};
        out.success = false;
        out.errorMessage = "No AI art generator attached";
        return out;
    }
    return aiGenerator->generateCrossbowSprite(params, createCrossbowArtPrompt(params, config));
}

AIArt::ArtOutput CrossbowAssetGenerator::generateBoltArt(const BoltParams& params, const ItemConfig& config) {
    if (!aiGenerator) {
        AIArt::ArtOutput out{};
        out.success = false;
        out.errorMessage = "No AI art generator attached";
        return out;
    }
    return aiGenerator->generateBoltSprite(params, createBoltArtPrompt(params, config));
}

AIArt::ArtOutput CrossbowAssetGenerator::generateArrowArt(const ArrowParams& params, const ItemConfig& config) {
    if (!aiGenerator) {
        AIArt::ArtOutput out{};
        out.success = false;
        out.errorMessage = "No AI art generator attached";
        return out;
    }
    return aiGenerator->generateArrowSprite(params, createArrowArtPrompt(params, config));
}

AIArt::ArtPrompt CrossbowAssetGenerator::createCrossbowArtPrompt(const CrossbowParams& params, const ItemConfig& config) {
    AIArt::ArtPrompt prompt{};
    prompt.description = config.itemName + ", " + generateDescription(params);
    prompt.style = config.artStyle;
    prompt.colorPalette = config.colorPalette;
    prompt.resolution = 32;
    prompt.frameCount = 8;
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.specialEffects = config.artEffects;
    prompt.specialEffects.insert(prompt.specialEffects.end(), config.specialEffects.begin(), config.specialEffects.end());
    return prompt;
}

AIArt::ArtPrompt CrossbowAssetGenerator::createBoltArtPrompt(const BoltParams& params, const ItemConfig& config) {
    AIArt::ArtPrompt prompt{};
    prompt.description = config.itemName + ", " + generateDescription(params);
    prompt.style = config.artStyle;
    prompt.colorPalette = config.colorPalette;
    prompt.resolution = 32;
    prompt.frameCount = 1;
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.specialEffects = config.artEffects;
    prompt.specialEffects.insert(prompt.specialEffects.end(), config.specialEffects.begin(), config.specialEffects.end());
    return prompt;
}

AIArt::ArtPrompt CrossbowAssetGenerator::createArrowArtPrompt(const ArrowParams& params, const ItemConfig& config) {
    AIArt::ArtPrompt prompt{};
    prompt.description = config.itemName + ", " + generateDescription(params);
    prompt.style = config.artStyle;
    prompt.colorPalette = config.colorPalette;
    prompt.resolution = 32;
    prompt.frameCount = 1;
    prompt.direction = "single";
    prompt.useAlpha = true;
    prompt.specialEffects = config.artEffects;
    prompt.specialEffects.insert(prompt.specialEffects.end(), config.specialEffects.begin(), config.specialEffects.end());
    return prompt;
}

// ---------------------------------------------------------------------------
// Procedural fallback sprites (PNG via stb_image_write)

bool CrossbowAssetGenerator::generateFallbackSprite(const std::string& outputPath, const CrossbowParams& params) {
    // 8 frames of 32x32: string drawn from rest to full and released at the end
    Canvas canvas(32 * 8, 32);
    for (int frame = 0; frame < 8; ++frame) {
        const float draw = frame < 7 ? static_cast<float>(frame) / 6.0f : 0.0f;
        drawCrossbowFrame(canvas, frame * 32, params, draw);
    }
    if (!canvas.savePng(outputPath)) {
        Log::error("CrossbowAsset", "Failed to write crossbow sprite: {}", outputPath);
        return false;
    }
    Log::info("CrossbowAsset", "Generated crossbow sprite: {}", outputPath);
    return true;
}

bool CrossbowAssetGenerator::generateFallbackSprite(const std::string& outputPath, const BoltParams& params) {
    Canvas canvas(32, 32);
    drawProjectile(canvas, std::clamp(params.length / 0.6f, 0.4f, 0.95f), 0x8B6B4AFF,
                   materialColor(params.fletchMaterial), params.useFletching, params.barbedTip);
    if (!canvas.savePng(outputPath)) {
        Log::error("CrossbowAsset", "Failed to write bolt sprite: {}", outputPath);
        return false;
    }
    Log::info("CrossbowAsset", "Generated bolt sprite: {}", outputPath);
    return true;
}

bool CrossbowAssetGenerator::generateFallbackSprite(const std::string& outputPath, const ArrowParams& params) {
    Canvas canvas(64, 32);
    drawProjectile(canvas, std::clamp(params.shaftLength / 1.0f, 0.5f, 0.95f), 0xA07850FF,
                   params.fletchStyle == "Flu-Flu" ? 0xF2F2F2FF : 0xC83C3CFF, params.useFletching, false);
    if (!canvas.savePng(outputPath)) {
        Log::error("CrossbowAsset", "Failed to write arrow sprite: {}", outputPath);
        return false;
    }
    Log::info("CrossbowAsset", "Generated arrow sprite: {}", outputPath);
    return true;
}

bool CrossbowAssetGenerator::generateFallbackIcon(const std::string& outputPath, const std::string& itemName) {
    // 16x16 icon: framed diagonal glyph tinted from the item name
    Canvas canvas(16, 16);
    uint32_t hash = 2166136261u;
    for (unsigned char c : itemName) hash = (hash ^ c) * 16777619u;
    const uint32_t tint = ((hash & 0xFFFFFF00u) | 0xFFu) | 0x40404000u;
    canvas.rect(0, 0, 15, 0, 0x3C3C46FF);
    canvas.rect(0, 15, 15, 15, 0x3C3C46FF);
    canvas.rect(0, 0, 0, 15, 0x3C3C46FF);
    canvas.rect(15, 0, 15, 15, 0x3C3C46FF);
    canvas.line(3.0f, 12.0f, 12.0f, 3.0f, tint, 2);
    canvas.line(3.0f, 3.0f, 5.0f, 5.0f, 0xE6E6E6FF);
    if (!canvas.savePng(outputPath)) {
        Log::error("CrossbowAsset", "Failed to write icon: {}", outputPath);
        return false;
    }
    Log::info("CrossbowAsset", "Generated icon: {}", outputPath);
    return true;
}

// ---------------------------------------------------------------------------
// File system helpers

bool CrossbowAssetGenerator::createDirectory(const std::string& path) {
    try {
        std::filesystem::create_directories(path);
        return true;
    } catch (const std::exception& e) {
        Log::error("CrossbowAsset", "Failed to create directory {}: {}", path, e.what());
        return false;
    }
}

bool CrossbowAssetGenerator::writeFile(const std::string& path, const std::string& content) {
    try {
        std::ofstream file(path);
        if (file.is_open()) {
            file << content;
            file.close();
            Log::info("CrossbowAsset", "Written file: {}", path);
            return true;
        }
        return false;
    } catch (const std::exception& e) {
        Log::error("CrossbowAsset", "Failed to write file {}: {}", path, e.what());
        return false;
    }
}

std::string CrossbowAssetGenerator::sanitizeFilename(const std::string& name) {
    std::string sanitized = name;
    // Replace spaces with underscores
    std::replace(sanitized.begin(), sanitized.end(), ' ', '_');
    // Remove special characters
    sanitized.erase(std::remove_if(sanitized.begin(), sanitized.end(),
        [](char c) { return !std::isalnum(static_cast<unsigned char>(c)) && c != '_' && c != '-'; }), sanitized.end());
    return sanitized;
}

// ---------------------------------------------------------------------------
// Templates

std::string CrossbowAssetGenerator::getCrossbowItemTemplate() {
    return R"({
  "itemName": "",
  "description": "",
  "rarity": "Common",
  "category": "crossbow",
  "level": 1,
  "price": 0,
  "twoHanded": true,
  "itemTags": ["weapon", "ranged", "crossbow"],
  "inventoryIcon": "",
  "animation": "",
  "animationParts": {},
  "scripts": [],
  "primaryAbility": {
    "abilityType": "crossbowshot",
    "damageConfig": {},
    "fireTime": 1.0,
    "projectileParameters": {},
    "projectileType": ""
  }
})";
}

std::string CrossbowAssetGenerator::getProjectileTemplate() {
    return R"({
  "projectileName": "",
  "image": "",
  "physics": "arrow",
  "flippable": true,
  "orientationLocked": false,
  "speed": 60,
  "timeToLive": 2.0,
  "damageKind": "physical",
  "damage": 0,
  "knockback": 0,
  "piercing": false,
  "actionOnReap": []
})";
}

std::string CrossbowAssetGenerator::getFramesTemplate() {
    return R"({
  "frameGrid": {
    "size": [32, 32],
    "dimensions": [1, 1],
    "names": [[]]
  }
})";
}

std::string CrossbowAssetGenerator::getBehaviorTemplate() {
    return R"(-- Crossbow behavior script for %ID%
-- Generated by Magi-Tech Crossbow Asset Generator

require "/scripts/util.lua"
require "/scripts/vec2.lua"
require "/items/active/weapons/weapon.lua"
require "/items/active/weapons/crossbow/crossbow.lua"

local function callEffectHook(prefix, effect, ...)
  local hook = _ENV[prefix .. effect .. "Effect"]
  if type(hook) == "function" then hook(...) end
end

function init()
  -- Initialize base crossbow behavior
  CrossbowInit()

  -- Magi-Tech integration
  self.magitechData = {
    behaviorSystem = "%BEHAVIOR_SYSTEM%",
    effectSystem = "%EFFECT_SYSTEM%",
    materialSystem = "%MATERIAL_SYSTEM%",
    specialEffects = %SPECIAL_EFFECTS%
  }

  -- Initialize special effects
  for effect in pairs(self.magitechData.specialEffects) do
    callEffectHook("init", effect)
  end
end

function update(dt, fireMode, shiftHeld)
  -- Update base crossbow behavior
  CrossbowUpdate(dt, fireMode, shiftHeld)

  -- Update special effects
  for effect in pairs(self.magitechData.specialEffects) do
    callEffectHook("update", effect, dt)
  end
end

function uninit()
  CrossbowUninit()
end
)";
}

std::string CrossbowAssetGenerator::getEffectTemplate() {
    return R"({
  "effectSystem": "projectile",
  "specialEffects": [],
  "materialEffects": {}
})";
}

// ---------------------------------------------------------------------------
// Naming and descriptions

std::string CrossbowAssetGenerator::generateAssetName(const std::string& baseName, const std::string& suffix) {
    return sanitizeFilename(baseName) + suffix;
}

std::string CrossbowAssetGenerator::generateDescription(const CrossbowParams& params) {
    std::ostringstream desc;
    desc << "A " << params.stockMaterial << " crossbow with " << params.limbMaterial << " limbs. ";
    desc << "Draw length: " << std::fixed << std::setprecision(1) << params.drawLength << "m, ";
    desc << "Draw weight: " << std::fixed << std::setprecision(0) << params.drawWeight << "N. ";
    if (params.autoReload) {
        desc << "Features automatic reload mechanism.";
    } else {
        desc << "Manual reload required.";
    }
    return desc.str();
}

std::string CrossbowAssetGenerator::generateDescription(const BoltParams& params) {
    std::ostringstream desc;
    desc << "A " << params.length << "m bolt with " << params.shaftRadius << "m radius. ";
    if (params.barbedTip) {
        desc << "Features barbed tip for increased damage. ";
    }
    if (params.useFletching) {
        desc << "Includes " << params.fletchMaterial << " fletching for stability.";
    } else {
        desc << "No fletching for maximum velocity.";
    }
    return desc.str();
}

std::string CrossbowAssetGenerator::generateDescription(const ArrowParams& params) {
    std::ostringstream desc;
    desc << "A " << params.shaftLength << "m arrow with " << params.spineRating << " spine rating. ";
    if (params.useFletching) {
        desc << "Features " << params.fletchStyle << " fletching for optimal flight.";
    }
    desc << " Designed for long-range accuracy.";
    return desc.str();
}

// ---------------------------------------------------------------------------
// Integration helpers: name the module that implements each configured system

std::string CrossbowAssetGenerator::integrateWithBehaviorSystem(const ItemConfig& config) {
    if (config.behaviorSystem == "cpp") return "magitech:crossbow_native";
    if (config.behaviorSystem == "hybrid") return "magitech:crossbow_native+/items/active/weapons/crossbow/crossbow.lua";
    return "/items/active/weapons/crossbow/crossbow.lua";
}

std::string CrossbowAssetGenerator::integrateWithEffectSystem(const ItemConfig& config) {
    if (config.effectSystem == "spell") return "magitech:spell_effects";
    if (config.effectSystem == "custom") return "magitech:custom_effects";
    return "magitech:projectile_effects";
}

std::string CrossbowAssetGenerator::integrateWithMaterialSystem(const ItemConfig& config) {
    if (config.materialSystem == "magitech") return "magitech:materials";
    if (config.materialSystem == "custom") return "magitech:custom_materials";
    return "vanilla";
}

} // namespace Crossbows
} // namespace MagiTech
