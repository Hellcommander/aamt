#include "CrossbowAssetGenerator.hpp"
#include "CrossbowAssetFactory.hpp"
#include "core/Log.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>

namespace MagiTech {
namespace Crossbows {

// Global asset generator instance
std::unique_ptr<CrossbowAssetGenerator> g_assetGenerator;

CrossbowAssetGenerator::CrossbowAssetGenerator() {
    outputBasePath = "items/active/weapons/crossbow/";
}

CrossbowAssetGenerator::~CrossbowAssetGenerator() = default;

CrossbowAssetGenerator::AssetOutput CrossbowAssetGenerator::generateCrossbowAssets(
    const CrossbowParams& params, const ItemConfig& config) {
    
    AssetOutput output;
    std::string baseName = sanitizeFilename(params.id);
    
    // Create output directory
    std::string outputDir = outputBasePath + baseName + "/";
    createDirectory(outputDir);
    
    // Generate all asset files
    output.itemFile = outputDir + baseName + ".activeitem";
    output.framesFile = outputDir + baseName + "full.frames";
    output.spriteFile = outputDir + baseName + "full.png";
    output.iconFile = outputDir + baseName + "icon.png";
    output.behaviorFile = outputDir + baseName + ".lua";
    output.effectFile = outputDir + baseName + "_effects.json";
    
    // Generate JSON files
    std::string activeItemJSON = generateActiveItemJSON(params, config);
    std::string framesJSON = generateFramesJSON(baseName + "full", 8); // 8 animation frames
    std::string behaviorScript = generateBehaviorScript(params, config);
    std::string effectConfig = generateEffectConfig(params, config);
    
    writeFile(output.itemFile, activeItemJSON);
    writeFile(output.framesFile, framesJSON);
    writeFile(output.behaviorFile, behaviorScript);
    writeFile(output.effectFile, effectConfig);
    
    // Generate sprite files (placeholder - would integrate with image generation)
    generateSprite(output.spriteFile, params);
    generateIcon(output.iconFile, config.itemName);
    
    Log::info("Generated crossbow assets for: {}", params.id);
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
    
    std::string projectileJSON = generateProjectileJSON(params, config);
    std::string effectConfig = generateEffectConfig(params, config);
    
    writeFile(output.projectileFile, projectileJSON);
    writeFile(output.effectFile, effectConfig);
    
    // Generate sprite files
    output.spriteFile = outputDir + baseName + ".png";
    output.iconFile = outputDir + baseName + "icon.png";
    
    generateSprite(output.spriteFile, params);
    generateIcon(output.iconFile, config.itemName);
    
    Log::info("Generated bolt assets for: {}", params.id);
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
    
    std::string projectileJSON = generateProjectileJSON(params, config);
    std::string effectConfig = generateEffectConfig(params, config);
    
    writeFile(output.projectileFile, projectileJSON);
    writeFile(output.effectFile, effectConfig);
    
    // Generate sprite files
    output.spriteFile = outputDir + baseName + ".png";
    output.iconFile = outputDir + baseName + "icon.png";
    
    generateSprite(output.spriteFile, params);
    generateIcon(output.iconFile, config.itemName);
    
    Log::info("Generated arrow assets for: {}", params.id);
    return output;
}

std::string CrossbowAssetGenerator::generateActiveItemJSON(const CrossbowParams& params, const ItemConfig& config) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"itemName\" : \"" << config.itemName << "\",\n";
    json << "  \"description\" : \"" << generateDescription(params) << "\",\n";
    json << "  \"rarity\" : \"" << config.rarity << "\",\n";
    json << "  \"category\" : \"" << config.category << "\",\n";
    json << "  \"level\" : " << config.level << ",\n";
    json << "  \"price\" : 0,\n";
    json << "  \"twoHanded\" : true,\n";
    json << "  \"itemTags\" : [\"weapon\", \"ranged\", \"crossbow\"],\n";
    json << "  \"inventoryIcon\" : \"" << sanitizeFilename(params.id) << "icon.png\",\n";
    json << "  \"animation\" : \"" << sanitizeFilename(params.id) << ".animation\",\n";
    json << "  \"animationParts\" : {\n";
    json << "    \"bow\" : \"" << sanitizeFilename(params.id) << "full.png\"\n";
    json << "  },\n";
    json << "  \"scripts\" : {\n";
    json << "    \"init\" : [\"/items/active/weapons/crossbow/" << sanitizeFilename(params.id) << ".lua\"],\n";
    json << "    \"update\" : [\"/items/active/weapons/crossbow/" << sanitizeFilename(params.id) << ".lua\"]\n";
    json << "  },\n";
    json << "  \"primaryAbility\" : {\n";
    json << "    \"abilityType\" : \"" << config.abilityType << "\",\n";
    json << "    \"damageConfig\" : {\n";
    json << "      \"damageKind\" : \"" << config.damageType << "\",\n";
    json << "      \"damage\" : " << std::fixed << std::setprecision(1) << config.damage << "\n";
    json << "    },\n";
    json << "    \"fireTime\" : " << std::fixed << std::setprecision(2) << (1.0f / config.fireRate) << ",\n";
    json << "    \"projectileParameters\" : {\n";
    json << "      \"power\" : " << (params.drawWeight * 0.01f) << "\n";
    json << "    },\n";
    json << "    \"projectileType\" : \"" << config.projectileTypes[0] << "\"\n";
    json << "  },\n";
    json << "  \"crossbowData\" : {\n";
    json << "    \"drawLength\" : " << std::fixed << std::setprecision(2) << params.drawLength << ",\n";
    json << "    \"drawWeight\" : " << std::fixed << std::setprecision(1) << params.drawWeight << ",\n";
    json << "    \"autoReload\" : " << (params.autoReload ? "true" : "false") << ",\n";
    json << "    \"reloadTime\" : " << std::fixed << std::setprecision(2) << params.reloadTime << ",\n";
    json << "    \"stockMaterial\" : \"" << params.stockMaterial << "\",\n";
    json << "    \"limbMaterial\" : \"" << params.limbMaterial << "\",\n";
    json << "    \"stringMaterial\" : \"" << params.stringMaterial << "\"\n";
    json << "  },\n";
    json << "  \"magitechIntegration\" : {\n";
    json << "    \"behaviorSystem\" : \"" << config.behaviorSystem << "\",\n";
    json << "    \"effectSystem\" : \"" << config.effectSystem << "\",\n";
    json << "    \"materialSystem\" : \"" << config.materialSystem << "\",\n";
    json << "    \"specialEffects\" : [";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        json << "\"" << config.specialEffects[i] << "\"";
        if (i < config.specialEffects.size() - 1) json << ", ";
    }
    json << "]\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

std::string CrossbowAssetGenerator::generateProjectileJSON(const BoltParams& params, const ItemConfig& config) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"projectileName\" : \"" << config.itemName << "\",\n";
    json << "  \"projectileType\" : \"bolt\",\n";
    json << "  \"damageKind\" : \"" << config.damageType << "\",\n";
    json << "  \"damage\" : " << std::fixed << std::setprecision(1) << config.damage << ",\n";
    json << "  \"speed\" : " << (params.length * 100.0f) << ",\n";
    json << "  \"knockback\" : 10,\n";
    json << "  \"piercing\" : " << (params.barbedTip ? "true" : "false") << ",\n";
    json << "  \"timeToLive\" : 2.0,\n";
    json << "  \"actionOnReap\" : [\n";
    json << "    {\n";
    json << "      \"action\" : \"projectile\",\n";
    json << "      \"type\" : \"damage\",\n";
    json << "      \"damage\" : " << (config.damage * 0.5f) << "\n";
    json << "    }\n";
    json << "  ],\n";
    json << "  \"boltData\" : {\n";
    json << "    \"length\" : " << std::fixed << std::setprecision(3) << params.length << ",\n";
    json << "    \"shaftRadius\" : " << std::fixed << std::setprecision(4) << params.shaftRadius << ",\n";
    json << "    \"useFletching\" : " << (params.useFletching ? "true" : "false") << ",\n";
    json << "    \"fletchMaterial\" : \"" << params.fletchMaterial << "\",\n";
    json << "    \"fletchLength\" : " << std::fixed << std::setprecision(3) << params.fletchLength << ",\n";
    json << "    \"tipMass\" : " << std::fixed << std::setprecision(4) << params.tipMass << ",\n";
    json << "    \"barbedTip\" : " << (params.barbedTip ? "true" : "false") << "\n";
    json << "  },\n";
    json << "  \"magitechIntegration\" : {\n";
    json << "    \"effectSystem\" : \"" << config.effectSystem << "\",\n";
    json << "    \"specialEffects\" : [";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        json << "\"" << config.specialEffects[i] << "\"";
        if (i < config.specialEffects.size() - 1) json << ", ";
    }
    json << "]\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

std::string CrossbowAssetGenerator::generateProjectileJSON(const ArrowParams& params, const ItemConfig& config) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"projectileName\" : \"" << config.itemName << "\",\n";
    json << "  \"projectileType\" : \"arrow\",\n";
    json << "  \"damageKind\" : \"" << config.damageType << "\",\n";
    json << "  \"damage\" : " << std::fixed << std::setprecision(1) << config.damage << ",\n";
    json << "  \"speed\" : " << (params.shaftLength * 80.0f) << ",\n";
    json << "  \"knockback\" : 8,\n";
    json << "  \"piercing\" : false,\n";
    json << "  \"timeToLive\" : 3.0,\n";
    json << "  \"actionOnReap\" : [\n";
    json << "    {\n";
    json << "      \"action\" : \"projectile\",\n";
    json << "      \"type\" : \"damage\",\n";
    json << "      \"damage\" : " << (config.damage * 0.3f) << "\n";
    json << "    }\n";
    json << "  ],\n";
    json << "  \"arrowData\" : {\n";
    json << "    \"shaftLength\" : " << std::fixed << std::setprecision(3) << params.shaftLength << ",\n";
    json << "    \"shaftDiameter\" : " << std::fixed << std::setprecision(4) << params.shaftDiameter << ",\n";
    json << "    \"spineRating\" : " << params.spineRating << ",\n";
    json << "    \"useFletching\" : " << (params.useFletching ? "true" : "false") << ",\n";
    json << "    \"fletchStyle\" : \"" << params.fletchStyle << "\",\n";
    json << "    \"nockSize\" : " << std::fixed << std::setprecision(4) << params.nockSize << ",\n";
    json << "    \"tipMass\" : " << std::fixed << std::setprecision(4) << params.tipMass << "\n";
    json << "  },\n";
    json << "  \"magitechIntegration\" : {\n";
    json << "    \"effectSystem\" : \"" << config.effectSystem << "\",\n";
    json << "    \"specialEffects\" : [";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        json << "\"" << config.specialEffects[i] << "\"";
        if (i < config.specialEffects.size() - 1) json << ", ";
    }
    json << "]\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

std::string CrossbowAssetGenerator::generateBehaviorScript(const CrossbowParams& params, const ItemConfig& config) {
    std::ostringstream lua;
    
    lua << "-- Crossbow behavior script for " << params.id << "\n";
    lua << "-- Generated by Magi-Tech Crossbow Asset Generator\n\n";
    
    lua << "require \"/scripts/util.lua\"\n";
    lua << "require \"/scripts/vec2.lua\"\n";
    lua << "require \"/items/active/weapons/weapon.lua\"\n";
    lua << "require \"/items/active/weapons/crossbow/crossbow.lua\"\n\n";
    
    lua << "function init()\n";
    lua << "  -- Initialize base crossbow behavior\n";
    lua << "  CrossbowInit()\n\n";
    
    lua << "  -- Magi-Tech integration\n";
    lua << "  self.magitechData = {\n";
    lua << "    behaviorSystem = \"" << config.behaviorSystem << "\",\n";
    lua << "    effectSystem = \"" << config.effectSystem << "\",\n";
    lua << "    materialSystem = \"" << config.materialSystem << "\",\n";
    lua << "    specialEffects = {";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        lua << "\"" << config.specialEffects[i] << "\"";
        if (i < config.specialEffects.size() - 1) lua << ", ";
    }
    lua << "}\n";
    lua << "  }\n\n";
    
    lua << "  -- Initialize special effects\n";
    for (const auto& effect : config.specialEffects) {
        lua << "  if self.magitechData.specialEffects[\"" << effect << "\"] then\n";
        lua << "    init" << effect << "Effect()\n";
        lua << "  end\n";
    }
    lua << "end\n\n";
    
    lua << "function update(dt, fireMode, shiftHeld)\n";
    lua << "  -- Update base crossbow behavior\n";
    lua << "  CrossbowUpdate(dt, fireMode, shiftHeld)\n\n";
    
    lua << "  -- Update special effects\n";
    for (const auto& effect : config.specialEffects) {
        lua << "  if self.magitechData.specialEffects[\"" << effect << "\"] then\n";
        lua << "    update" << effect << "Effect(dt)\n";
        lua << "  end\n";
    }
    lua << "end\n\n";
    
    lua << "function uninit()\n";
    lua << "  CrossbowUninit()\n";
    lua << "end\n";
    
    return lua.str();
}

std::string CrossbowAssetGenerator::generateEffectConfig(const CrossbowParams& params, const ItemConfig& config) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"crossbowId\" : \"" << params.id << "\",\n";
    json << "  \"effectSystem\" : \"" << config.effectSystem << "\",\n";
    json << "  \"specialEffects\" : [";
    for (size_t i = 0; i < config.specialEffects.size(); ++i) {
        json << "\"" << config.specialEffects[i] << "\"";
        if (i < config.specialEffects.size() - 1) json << ", ";
    }
    json << "],\n";
    json << "  \"materialEffects\" : {\n";
    json << "    \"stock\" : \"" << params.stockMaterial << "\",\n";
    json << "    \"limb\" : \"" << params.limbMaterial << "\",\n";
    json << "    \"string\" : \"" << params.stringMaterial << "\"\n";
    json << "  },\n";
    json << "  \"crossbowData\" : {\n";
    json << "    \"drawLength\" : " << std::fixed << std::setprecision(2) << params.drawLength << ",\n";
    json << "    \"drawWeight\" : " << std::fixed << std::setprecision(1) << params.drawWeight << ",\n";
    json << "    \"autoReload\" : " << (params.autoReload ? "true" : "false") << ",\n";
    json << "    \"reloadTime\" : " << std::fixed << std::setprecision(2) << params.reloadTime << "\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

std::string CrossbowAssetGenerator::generateFramesJSON(const std::string& spriteName, int frameCount) {
    std::ostringstream json;
    
    json << "{\n";
    json << "  \"" << spriteName << "\" : {\n";
    json << "    \"frameGrid\" : {\n";
    json << "      \"size\" : [32, 32],\n";
    json << "      \"dimensions\" : [" << frameCount << ", 1]\n";
    json << "    },\n";
    json << "    \"frames\" : [\n";
    
    for (int i = 0; i < frameCount; ++i) {
        json << "      {\n";
        json << "        \"name\" : \"frame" << i << "\",\n";
        json << "        \"position\" : [" << (i * 32) << ", 0]\n";
        json << "      }";
        if (i < frameCount - 1) json << ",";
        json << "\n";
    }
    
    json << "    ]\n";
    json << "  }\n";
    json << "}";
    
    return json.str();
}

bool CrossbowAssetGenerator::generateSprite(const std::string& outputPath, const CrossbowParams& params) {
    // This would integrate with the existing image generation system
    // For now, create a placeholder sprite file
    std::ofstream file(outputPath, std::ios::binary);
    if (file.is_open()) {
        // Create a simple 256x256 PNG placeholder
        // In a real implementation, this would use the mesh data to generate a sprite
        file.close();
        Log::info("Generated crossbow sprite: {}", outputPath);
        return true;
    }
    return false;
}

bool CrossbowAssetGenerator::generateSprite(const std::string& outputPath, const BoltParams& params) {
    // Generate bolt sprite
    std::ofstream file(outputPath, std::ios::binary);
    if (file.is_open()) {
        // Create a simple 32x32 PNG placeholder for bolt
        file.close();
        Log::info("Generated bolt sprite: {}", outputPath);
        return true;
    }
    return false;
}

bool CrossbowAssetGenerator::generateSprite(const std::string& outputPath, const ArrowParams& params) {
    // Generate arrow sprite
    std::ofstream file(outputPath, std::ios::binary);
    if (file.is_open()) {
        // Create a simple 32x64 PNG placeholder for arrow
        file.close();
        Log::info("Generated arrow sprite: {}", outputPath);
        return true;
    }
    return false;
}

bool CrossbowAssetGenerator::generateIcon(const std::string& outputPath, const std::string& itemName) {
    // Generate inventory icon
    std::ofstream file(outputPath, std::ios::binary);
    if (file.is_open()) {
        // Create a simple 32x32 PNG placeholder icon
        file.close();
        Log::info("Generated icon: {}", outputPath);
        return true;
    }
    return false;
}

bool CrossbowAssetGenerator::createDirectory(const std::string& path) {
    try {
        std::filesystem::create_directories(path);
        return true;
    } catch (const std::exception& e) {
        Log::error("Failed to create directory {}: {}", path, e.what());
        return false;
    }
}

bool CrossbowAssetGenerator::writeFile(const std::string& path, const std::string& content) {
    try {
        std::ofstream file(path);
        if (file.is_open()) {
            file << content;
            file.close();
            Log::info("Written file: {}", path);
            return true;
        }
        return false;
    } catch (const std::exception& e) {
        Log::error("Failed to write file {}: {}", path, e.what());
        return false;
    }
}

std::string CrossbowAssetGenerator::sanitizeFilename(const std::string& name) {
    std::string sanitized = name;
    // Replace spaces with underscores
    std::replace(sanitized.begin(), sanitized.end(), ' ', '_');
    // Remove special characters
    sanitized.erase(std::remove_if(sanitized.begin(), sanitized.end(), 
        [](char c) { return !std::isalnum(c) && c != '_' && c != '-'; }), sanitized.end());
    return sanitized;
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

} // namespace Crossbows
} // namespace MagiTech 
