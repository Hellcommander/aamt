#include "AlchemicalLauncherLuaBindings.hpp"
#include "AlchemicalLauncherFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include "AlchemicalLauncherTypes.hpp"
#include "ColorPickerSystem.hpp"
#include <vector>
#include <chrono>

namespace MagiTech {
namespace AlchemicalLaunchers {

static std::vector<std::pair<std::future<LauncherAssetBundle>, std::string>> pendingLaunchers;
static std::chrono::high_resolution_clock::time_point generationStartTime;

void AlchemicalLauncherLuaBindings::bind(sol::state& lua) {
    // Bind enums
    lua.new_enum("LauncherType",
        "CATAPULT", LauncherType::CATAPULT,
        "CROSSBOW", LauncherType::CROSSBOW,
        "BALLISTA", LauncherType::BALLISTA,
        "CANNON", LauncherType::CANNON,
        "ROCKET", LauncherType::ROCKET,
        "RAILGUN", LauncherType::RAILGUN,
        "MAGIC_STAFF", LauncherType::MAGIC_STAFF,
        "WAND", LauncherType::WAND,
        "CUSTOM", LauncherType::CUSTOM
    );
    
    lua.new_enum("MaterialType",
        "STEEL", MaterialType::STEEL,
        "IRON", MaterialType::IRON,
        "BRONZE", MaterialType::BRONZE,
        "WOOD", MaterialType::WOOD,
        "STONE", MaterialType::STONE,
        "CRYSTAL", MaterialType::CRYSTAL,
        "MAGIC", MaterialType::MAGIC,
        "ORGANIC", MaterialType::ORGANIC,
        "CUSTOM", MaterialType::CUSTOM
    );
    
    lua.new_enum("SightType",
        "NONE", SightType::NONE,
        "IRON_SIGHT", SightType::IRON_SIGHT,
        "SCOPE", SightType::SCOPE,
        "MAGIC_SIGHT", SightType::MAGIC_SIGHT,
        "THERMAL", SightType::THERMAL,
        "CUSTOM", SightType::CUSTOM
    );
    
    lua.new_enum("EngravingPattern",
        "NONE", EngravingPattern::NONE,
        "ALCHEMY_RUNES", EngravingPattern::ALCHEMY_RUNES,
        "MAGIC_SIGILS", EngravingPattern::MAGIC_SIGILS,
        "GEOMETRIC", EngravingPattern::GEOMETRIC,
        "FLORAL", EngravingPattern::FLORAL,
        "DRAGON", EngravingPattern::DRAGON,
        "PHOENIX", EngravingPattern::PHOENIX,
        "CUSTOM", EngravingPattern::CUSTOM
    );
    
    lua.new_enum("BackgroundShape",
        "RECTANGLE", BackgroundShape::RECTANGLE,
        "CIRCLE", BackgroundShape::CIRCLE,
        "HEXAGON", BackgroundShape::HEXAGON,
        "DIAMOND", BackgroundShape::DIAMOND,
        "NONE", BackgroundShape::NONE,
        "CUSTOM", BackgroundShape::CUSTOM
    );

    // Bind Color struct
    lua.new_usertype<ColorPicker::Color>("Color",
        sol::constructors<
            ColorPicker::Color(),
            ColorPicker::Color(float, float, float, float),
            ColorPicker::Color(const glm::vec4&)
        >(),
        "rgba", &ColorPicker::Color::rgba,
        "hsv", &ColorPicker::Color::hsv,
        "toHex", &ColorPicker::Color::toHex,
        "fromHex", &ColorPicker::Color::fromHex,
        "fromHSV", &ColorPicker::Color::fromHSV,
        "complementary", &ColorPicker::Color::complementary,
        "analogous", &ColorPicker::Color::analogous,
        "triadic", &ColorPicker::Color::triadic,
        "splitComplementary", &ColorPicker::Color::splitComplementary,
        "tetradic", &ColorPicker::Color::tetradic,
        "monochromatic", &ColorPicker::Color::monochromatic
    );

    // Bind ColorPalette struct
    lua.new_usertype<ColorPicker::ColorPalette>("ColorPalette",
        sol::constructors<
            ColorPicker::ColorPalette(),
            ColorPicker::ColorPalette(const std::string&)
        >(),
        "name", &ColorPicker::ColorPalette::name,
        "colors", &ColorPicker::ColorPalette::colors,
        "description", &ColorPicker::ColorPalette::description,
        "tags", &ColorPicker::ColorPalette::tags,
        "addColor", &ColorPicker::ColorPalette::addColor,
        "removeColor", &ColorPicker::ColorPalette::removeColor,
        "clear", &ColorPicker::ColorPalette::clear,
        "size", &ColorPicker::ColorPalette::size,
        "empty", &ColorPicker::ColorPalette::empty,
        "toJson", &ColorPicker::ColorPalette::toJson,
        "fromJson", &ColorPicker::ColorPalette::fromJson
    );

    // Bind ColorTheme struct
    lua.new_usertype<ColorPicker::ColorTheme>("ColorTheme",
        sol::constructors<
            ColorPicker::ColorTheme(),
            ColorPicker::ColorTheme(const std::string&)
        >(),
        "name", &ColorPicker::ColorTheme::name,
        "description", &ColorPicker::ColorTheme::description,
        "setColor", &ColorPicker::ColorTheme::setColor,
        "getColor", &ColorPicker::ColorTheme::getColor,
        "hasColor", &ColorPicker::ColorTheme::hasColor,
        "toJson", &ColorPicker::ColorTheme::toJson,
        "fromJson", &ColorPicker::ColorTheme::fromJson
    );

    // Bind ColorPickerSystem
    lua.new_usertype<ColorPicker::ColorPickerSystem>("ColorPickerSystem",
        sol::no_constructor,
        "instance", &ColorPicker::ColorPickerSystem::instance,
        "drawColorPicker", &ColorPicker::ColorPickerSystem::drawColorPicker,
        "drawPaletteSelector", &ColorPicker::ColorPickerSystem::drawPaletteSelector,
        "drawPaletteEditor", &ColorPicker::ColorPickerSystem::drawPaletteEditor,
        "drawThemeSelector", &ColorPicker::ColorPickerSystem::drawThemeSelector,
        "addPalette", &ColorPicker::ColorPickerSystem::addPalette,
        "removePalette", &ColorPicker::ColorPickerSystem::removePalette,
        "getPalette", &ColorPicker::ColorPickerSystem::getPalette,
        "getPaletteNames", &ColorPicker::ColorPickerSystem::getPaletteNames,
        "addTheme", &ColorPicker::ColorPickerSystem::addTheme,
        "removeTheme", &ColorPicker::ColorPickerSystem::removeTheme,
        "getTheme", &ColorPicker::ColorPickerSystem::getTheme,
        "getThemeNames", &ColorPicker::ColorPickerSystem::getThemeNames,
        "savePalettes", &ColorPicker::ColorPickerSystem::savePalettes,
        "loadPalettes", &ColorPicker::ColorPickerSystem::loadPalettes,
        "saveThemes", &ColorPicker::ColorPickerSystem::saveThemes,
        "loadThemes", &ColorPicker::ColorPickerSystem::loadThemes,
        "randomColor", &ColorPicker::ColorPickerSystem::randomColor,
        "randomHarmony", &ColorPicker::ColorPickerSystem::randomHarmony,
        "randomizePalette", &ColorPicker::ColorPickerSystem::randomizePalette,
        "lerp", &ColorPicker::ColorPickerSystem::lerp,
        "getContrastRatio", &ColorPicker::ColorPickerSystem::getContrastRatio,
        "isAccessible", &ColorPicker::ColorPickerSystem::isAccessible
    );

    // Bind AlchemicalLauncherParams with all fields
    lua.new_usertype<AlchemicalLauncherParams>("AlchemicalLauncherParams",
        sol::constructors<AlchemicalLauncherParams()>(),
        // Basic properties
        "id", &AlchemicalLauncherParams::id,
        "launcherType", &AlchemicalLauncherParams::launcherType,
        "materialMain", &AlchemicalLauncherParams::materialMain,
        "materialSecondary", &AlchemicalLauncherParams::materialSecondary,
        "sightType", &AlchemicalLauncherParams::sightType,
        "engravingPattern", &AlchemicalLauncherParams::engravingPattern,
        
        // Physical properties
        "barrelLength", &AlchemicalLauncherParams::barrelLength,
        "barrelRadius", &AlchemicalLauncherParams::barrelRadius,
        "barrelThickness", &AlchemicalLauncherParams::barrelThickness,
        "frameLength", &AlchemicalLauncherParams::frameLength,
        "frameWidth", &AlchemicalLauncherParams::frameWidth,
        "frameHeight", &AlchemicalLauncherParams::frameHeight,
        "gripLength", &AlchemicalLauncherParams::gripLength,
        "gripWidth", &AlchemicalLauncherParams::gripWidth,
        "gripHeight", &AlchemicalLauncherParams::gripHeight,
        "magazineRadius", &AlchemicalLauncherParams::magazineRadius,
        "magazineHeight", &AlchemicalLauncherParams::magazineHeight,
        "magazineCapacity", &AlchemicalLauncherParams::magazineCapacity,
        "sightHeight", &AlchemicalLauncherParams::sightHeight,
        "sightWidth", &AlchemicalLauncherParams::sightWidth,
        
        // Performance properties
        "fireRate", &AlchemicalLauncherParams::fireRate,
        "reloadTime", &AlchemicalLauncherParams::reloadTime,
        "accuracy", &AlchemicalLauncherParams::accuracy,
        "range", &AlchemicalLauncherParams::range,
        "projectileSpeed", &AlchemicalLauncherParams::projectileSpeed,
        "recoilForce", &AlchemicalLauncherParams::recoilForce,
        "recoilRecovery", &AlchemicalLauncherParams::recoilRecovery,
        "muzzleVelocity", &AlchemicalLauncherParams::muzzleVelocity,
        
        // Visual properties
        "colorPrimary", &AlchemicalLauncherParams::colorPrimary,
        "colorSecondary", &AlchemicalLauncherParams::colorSecondary,
        "colorAccent", &AlchemicalLauncherParams::colorAccent,
        "glowColor", &AlchemicalLauncherParams::glowColor,
        "noiseScale", &AlchemicalLauncherParams::noiseScale,
        "noiseIntensity", &AlchemicalLauncherParams::noiseIntensity,
        "metallicness", &AlchemicalLauncherParams::metallicness,
        "roughness", &AlchemicalLauncherParams::roughness,
        "emissivePower", &AlchemicalLauncherParams::emissivePower,
        "transparency", &AlchemicalLauncherParams::transparency,
        "refractionIndex", &AlchemicalLauncherParams::refractionIndex,
        "reflectionStrength", &AlchemicalLauncherParams::reflectionStrength,
        
        // Muzzle effects
        "muzzleGlowIntensity", &AlchemicalLauncherParams::muzzleGlowIntensity,
        "muzzleFlashSize", &AlchemicalLauncherParams::muzzleFlashSize,
        "muzzleFlashDuration", &AlchemicalLauncherParams::muzzleFlashDuration,
        "muzzleSmokeCount", &AlchemicalLauncherParams::muzzleSmokeCount,
        "muzzleSmokeLifetime", &AlchemicalLauncherParams::muzzleSmokeLifetime,
        "muzzleSmokeSize", &AlchemicalLauncherParams::muzzleSmokeSize,
        "muzzleSmokeSpeed", &AlchemicalLauncherParams::muzzleSmokeSpeed,
        "muzzleFlashColor", &AlchemicalLauncherParams::muzzleFlashColor,
        "muzzleSmokeColor", &AlchemicalLauncherParams::muzzleSmokeColor,
        
        // Particle effects
        "enableShellEjection", &AlchemicalLauncherParams::enableShellEjection,
        "shellEjectionCount", &AlchemicalLauncherParams::shellEjectionCount,
        "shellEjectionSpeed", &AlchemicalLauncherParams::shellEjectionSpeed,
        "shellEjectionLifetime", &AlchemicalLauncherParams::shellEjectionLifetime,
        "enableHeatDistortion", &AlchemicalLauncherParams::enableHeatDistortion,
        "heatDistortionStrength", &AlchemicalLauncherParams::heatDistortionStrength,
        "heatDistortionRadius", &AlchemicalLauncherParams::heatDistortionRadius,
        
        // Audio properties
        "soundVolume", &AlchemicalLauncherParams::soundVolume,
        "soundPitch", &AlchemicalLauncherParams::soundPitch,
        "soundDuration", &AlchemicalLauncherParams::soundDuration,
        "enableSpatialAudio", &AlchemicalLauncherParams::enableSpatialAudio,
        "audioDistance", &AlchemicalLauncherParams::audioDistance,
        "enableEcho", &AlchemicalLauncherParams::enableEcho,
        "echoDelay", &AlchemicalLauncherParams::echoDelay,
        "echoDecay", &AlchemicalLauncherParams::echoDecay,
        "enableReverb", &AlchemicalLauncherParams::enableReverb,
        "reverbIntensity", &AlchemicalLauncherParams::reverbIntensity,
        
        // Shader properties
        "shaderType", &AlchemicalLauncherParams::shaderType,
        "shaderIntensity", &AlchemicalLauncherParams::shaderIntensity,
        "enableDistortion", &AlchemicalLauncherParams::enableDistortion,
        "distortionStrength", &AlchemicalLauncherParams::distortionStrength,
        "enableRefraction", &AlchemicalLauncherParams::enableRefraction,
        "refractionStrength", &AlchemicalLauncherParams::refractionStrength,
        "enableReflection", &AlchemicalLauncherParams::enableReflection,
        "reflectionStrength", &AlchemicalLauncherParams::reflectionStrength,
        "enableEmission", &AlchemicalLauncherParams::enableEmission,
        "emissionStrength", &AlchemicalLauncherParams::emissionStrength,
        
        // Physics properties
        "enablePhysics", &AlchemicalLauncherParams::enablePhysics,
        "enableCollision", &AlchemicalLauncherParams::enableCollision,
        "collisionRadius", &AlchemicalLauncherParams::collisionRadius,
        "enableGravity", &AlchemicalLauncherParams::enableGravity,
        "enableAirResistance", &AlchemicalLauncherParams::enableAirResistance,
        "airResistanceFactor", &AlchemicalLauncherParams::airResistanceFactor,
        "enableBounce", &AlchemicalLauncherParams::enableBounce,
        "bounceFactor", &AlchemicalLauncherParams::bounceFactor,
        "mass", &AlchemicalLauncherParams::mass,
        "density", &AlchemicalLauncherParams::density,
        "friction", &AlchemicalLauncherParams::friction,
        "bounciness", &AlchemicalLauncherParams::bounciness,
        
        // Ornamentation properties
        "ornamentation", &AlchemicalLauncherParams::ornamentation,
        "ornamentationScale", &AlchemicalLauncherParams::ornamentationScale,
        "ornamentationIntensity", &AlchemicalLauncherParams::ornamentationIntensity,
        "enableRunes", &AlchemicalLauncherParams::enableRunes,
        "runeGlowIntensity", &AlchemicalLauncherParams::runeGlowIntensity,
        "enableCrystals", &AlchemicalLauncherParams::enableCrystals,
        "crystalGlowIntensity", &AlchemicalLauncherParams::crystalGlowIntensity,
        "enableGems", &AlchemicalLauncherParams::enableGems,
        "gemGlowIntensity", &AlchemicalLauncherParams::gemGlowIntensity,
        
        // Performance properties
        "enableCaching", &AlchemicalLauncherParams::enableCaching,
        "enableHotReload", &AlchemicalLauncherParams::enableHotReload,
        "enableParallelProcessing", &AlchemicalLauncherParams::enableParallelProcessing,
        "lodLevel", &AlchemicalLauncherParams::lodLevel,
        
        // Metadata
        "description", &AlchemicalLauncherParams::description,
        "tags", &AlchemicalLauncherParams::tags,
        "metadata", &AlchemicalLauncherParams::metadata,
        
        // Utility methods
        "hashKey", &AlchemicalLauncherParams::hashKey
    );

    // Bind UIParams with all fields
    lua.new_usertype<UIParams>("LauncherUIParams",
        sol::constructors<UIParams()>(),
        // Icon properties
        "iconSize", &UIParams::iconSize,
        "borderColor", &UIParams::borderColor,
        "backgroundShape", &UIParams::backgroundShape,
        "flashOnSelect", &UIParams::flashOnSelect,
        
        // Visual properties
        "borderThickness", &UIParams::borderThickness,
        "cornerRadius", &UIParams::cornerRadius,
        "enableGlow", &UIParams::enableGlow,
        "glowColor", &UIParams::glowColor,
        "glowIntensity", &UIParams::glowIntensity,
        "enablePulse", &UIParams::enablePulse,
        "pulseFrequency", &UIParams::pulseFrequency,
        "pulseAmplitude", &UIParams::pulseAmplitude,
        
        // Animation properties
        "enableHoverEffect", &UIParams::enableHoverEffect,
        "hoverScale", &UIParams::hoverScale,
        "hoverDuration", &UIParams::hoverDuration,
        "enableClickEffect", &UIParams::enableClickEffect,
        "clickScale", &UIParams::clickScale,
        "clickDuration", &UIParams::clickDuration,
        
        // Text properties
        "label", &UIParams::label,
        "enableLabel", &UIParams::enableLabel,
        "labelColor", &UIParams::labelColor,
        "labelSize", &UIParams::labelSize,
        "labelFont", &UIParams::labelFont,
        
        // Performance properties
        "enableCaching", &UIParams::enableCaching,
        "enableHotReload", &UIParams::enableHotReload,
        "lodLevel", &UIParams::lodLevel,
        
        // Metadata
        "description", &UIParams::description,
        "tags", &UIParams::tags,
        "metadata", &UIParams::metadata,
        
        // Utility methods
        "hashKey", &UIParams::hashKey
    );

    // Bind LauncherAssetBundle with all fields
    lua.new_usertype<LauncherAssetBundle>("LauncherAssetBundle",
        sol::no_constructor,
        // Main launcher assets
        "meshBody", &LauncherAssetBundle::meshBody,
        "textureBody", &LauncherAssetBundle::textureBody,
        "shaderBody", &LauncherAssetBundle::shaderBody,
        
        // Effect assets
        "muzzleFlash", &LauncherAssetBundle::muzzleFlash,
        "muzzleSmoke", &LauncherAssetBundle::muzzleSmoke,
        "shellEjection", &LauncherAssetBundle::shellEjection,
        "heatDistortion", &LauncherAssetBundle::heatDistortion,
        
        // Physics assets
        "recoilPhysics", &LauncherAssetBundle::recoilPhysics,
        "magazinePhysics", &LauncherAssetBundle::magazinePhysics,
        
        // Audio assets
        "sfxFire", &LauncherAssetBundle::sfxFire,
        "sfxReload", &LauncherAssetBundle::sfxReload,
        "sfxShellEject", &LauncherAssetBundle::sfxShellEject,
        "sfxHeatDistortion", &LauncherAssetBundle::sfxHeatDistortion,
        
        // UI assets
        "icon", &LauncherAssetBundle::icon,
        
        // Performance metrics
        "generationTime", &LauncherAssetBundle::generationTime,
        "vertexCount", &LauncherAssetBundle::vertexCount,
        "triangleCount", &LauncherAssetBundle::triangleCount,
        "particleCount", &LauncherAssetBundle::particleCount,
        "gpuAccelerated", &LauncherAssetBundle::gpuAccelerated
    );

    // Bind parameter conversion utilities
    lua.set_function("parseLauncherType", ParamUtils::parseLauncherType);
    lua.set_function("parseMaterialType", ParamUtils::parseMaterialType);
    lua.set_function("parseSightType", ParamUtils::parseSightType);
    lua.set_function("parseEngravingPattern", ParamUtils::parseEngravingPattern);
    lua.set_function("parseBackgroundShape", ParamUtils::parseBackgroundShape);
    
    lua.set_function("launcherTypeToString", ParamUtils::launcherTypeToString);
    lua.set_function("materialTypeToString", ParamUtils::materialTypeToString);
    lua.set_function("sightTypeToString", ParamUtils::sightTypeToString);
    lua.set_function("engravingPatternToString", ParamUtils::engravingPatternToString);
    lua.set_function("backgroundShapeToString", ParamUtils::backgroundShapeToString);

    // Bind JSON serialization utilities
    lua.set_function("launcherParamsToJson", ParamUtils::toJson);
    lua.set_function("launcherParamsFromJson", ParamUtils::fromJson);
    lua.set_function("uiParamsToJson", [](const UIParams& p) { return ParamUtils::toJson(p); });
    lua.set_function("uiParamsFromJson", [](const nlohmann::json& j) { return ParamUtils::fromJson(j); });

    // Bind color picker utilities
    lua.set_function("openColorPicker", [](const std::string& name, ColorPicker::Color& color) {
        auto& picker = ColorPicker::ColorPickerSystem::instance();
        return picker.drawColorPicker(name.c_str(), color);
    });
    
    lua.set_function("createColorFromHex", [](const std::string& hex) {
        return ColorPicker::Color::fromHex(hex);
    });
    
    lua.set_function("createColorFromHSV", [](float h, float s, float v, float a) {
        return ColorPicker::Color::fromHSV(h, s, v, a);
    });
    
    lua.set_function("createRandomColor", [](float saturation, float value) {
        auto& picker = ColorPicker::ColorPickerSystem::instance();
        return picker.randomColor(saturation, value);
    });
    
    lua.set_function("createRandomHarmony", [](const ColorPicker::Color& base, const std::string& harmonyType) {
        auto& picker = ColorPicker::ColorPickerSystem::instance();
        return picker.randomHarmony(base, harmonyType);
    });

    // Bind color theme creation functions
    lua.set_function("createFireTheme", ColorPicker::ColorThemes::createFireTheme);
    lua.set_function("createInfernoTheme", ColorPicker::ColorThemes::createInfernoTheme);
    lua.set_function("createEmberTheme", ColorPicker::ColorThemes::createEmberTheme);
    lua.set_function("createIceTheme", ColorPicker::ColorThemes::createIceTheme);
    lua.set_function("createFrostTheme", ColorPicker::ColorThemes::createFrostTheme);
    lua.set_function("createCrystalTheme", ColorPicker::ColorThemes::createCrystalTheme);
    lua.set_function("createArcaneTheme", ColorPicker::ColorThemes::createArcaneTheme);
    lua.set_function("createMysticTheme", ColorPicker::ColorThemes::createMysticTheme);
    lua.set_function("createEtherealTheme", ColorPicker::ColorThemes::createEtherealTheme);
    lua.set_function("createNatureTheme", ColorPicker::ColorThemes::createNatureTheme);
    lua.set_function("createOrganicTheme", ColorPicker::ColorThemes::createOrganicTheme);
    lua.set_function("createVerdantTheme", ColorPicker::ColorThemes::createVerdantTheme);
    lua.set_function("createSteelTheme", ColorPicker::ColorThemes::createSteelTheme);
    lua.set_function("createBronzeTheme", ColorPicker::ColorThemes::createBronzeTheme);
    lua.set_function("createGoldTheme", ColorPicker::ColorThemes::createGoldTheme);
    lua.set_function("createVoidTheme", ColorPicker::ColorThemes::createVoidTheme);
    lua.set_function("createShadowTheme", ColorPicker::ColorThemes::createShadowTheme);
    lua.set_function("createAbyssTheme", ColorPicker::ColorThemes::createAbyssTheme);

    // Bind accessibility functions
    lua.set_function("createColorBlindFriendlyPalette", ColorPicker::Accessibility::createColorBlindFriendlyPalette);
    lua.set_function("createHighContrastPalette", ColorPicker::Accessibility::createHighContrastPalette);
    lua.set_function("isColorBlindFriendly", ColorPicker::Accessibility::isColorBlindFriendly);
    lua.set_function("hasSufficientContrast", ColorPicker::Accessibility::hasSufficientContrast);
    lua.set_function("adjustForColorBlindness", ColorPicker::Accessibility::adjustForColorBlindness);
    lua.set_function("ensureContrast", ColorPicker::Accessibility::ensureContrast);

    // Bind launcher generation functions
    lua.set_function("spawn_launcher",
        [&](const AlchemicalLauncherParams& p, const UIParams& u) {
            generationStartTime = std::chrono::high_resolution_clock::now();
            auto factory = MainPlugin::instance().getAlchemicalLauncherFactory();
            return factory->generateAsync(p, u).get();
        }
    );

    lua.set_function("spawn_launcher_async",
        [&](const AlchemicalLauncherParams& p, const UIParams& u) {
            auto factory = MainPlugin::instance().getAlchemicalLauncherFactory();
            pendingLaunchers.emplace_back(factory->generateAsync(p, u), p.id);
        }
    );
    
    // Bind utility functions for parameter creation
    lua.set_function("createDefaultLauncherParams", []() {
        AlchemicalLauncherParams p;
        p.id = "default_launcher";
        p.launcherType = LauncherType::CATAPULT;
        p.materialMain = MaterialType::STEEL;
        p.materialSecondary = MaterialType::WOOD;
        p.sightType = SightType::IRON_SIGHT;
        p.engravingPattern = EngravingPattern::NONE;
        
        // Physical properties
        p.barrelLength = 1.2f;
        p.barrelRadius = 0.1f;
        p.barrelThickness = 0.02f;
        p.frameLength = 1.0f;
        p.frameWidth = 0.2f;
        p.frameHeight = 0.1f;
        p.gripLength = 0.2f;
        p.gripWidth = 0.1f;
        p.gripHeight = 0.05f;
        p.magazineRadius = 0.15f;
        p.magazineHeight = 0.15f;
        p.magazineCapacity = 6;
        p.sightHeight = 0.05f;
        p.sightWidth = 0.02f;
        
        // Performance properties
        p.fireRate = 0.5f;
        p.reloadTime = 2.5f;
        p.accuracy = 0.8f;
        p.range = 50.0f;
        p.projectileSpeed = 30.0f;
        p.recoilForce = 30.0f;
        p.recoilRecovery = 5.0f;
        p.muzzleVelocity = 25.0f;
        
        // Visual properties
        p.colorPrimary = {0.6f, 0.6f, 0.6f};
        p.colorSecondary = {0.3f, 0.2f, 0.1f};
        p.colorAccent = {0.8f, 0.6f, 0.2f};
        p.glowColor = {1.0f, 0.8f, 0.4f};
        p.noiseScale = 2.0f;
        p.noiseIntensity = 0.5f;
        p.metallicness = 0.8f;
        p.roughness = 0.3f;
        p.emissivePower = 0.0f;
        p.transparency = 0.0f;
        p.refractionIndex = 1.0f;
        p.reflectionStrength = 0.5f;
        
        // Muzzle effects
        p.muzzleGlowIntensity = 1.5f;
        p.muzzleFlashSize = 0.8f;
        p.muzzleFlashDuration = 0.1f;
        p.muzzleSmokeCount = 20;
        p.muzzleSmokeLifetime = 0.6f;
        p.muzzleSmokeSize = 0.2f;
        p.muzzleSmokeSpeed = 1.0f;
        p.muzzleFlashColor = {1.0f, 0.8f, 0.4f};
        p.muzzleSmokeColor = {0.2f, 0.2f, 0.2f};
        
        // Particle effects
        p.enableShellEjection = true;
        p.shellEjectionCount = 1;
        p.shellEjectionSpeed = 5.0f;
        p.shellEjectionLifetime = 2.0f;
        p.enableHeatDistortion = true;
        p.heatDistortionStrength = 0.3f;
        p.heatDistortionRadius = 0.3f;
        
        // Audio properties
        p.soundVolume = 1.0f;
        p.soundPitch = 1.0f;
        p.soundDuration = 0.5f;
        p.enableSpatialAudio = true;
        p.audioDistance = 10.0f;
        p.enableEcho = true;
        p.echoDelay = 0.1f;
        p.echoDecay = 0.5f;
        p.enableReverb = true;
        p.reverbIntensity = 0.3f;
        
        // Shader properties
        p.shaderType = "PBR";
        p.shaderIntensity = 1.0f;
        p.enableDistortion = false;
        p.distortionStrength = 0.0f;
        p.enableRefraction = false;
        p.refractionStrength = 0.0f;
        p.enableReflection = true;
        p.reflectionStrength = 0.5f;
        p.enableEmission = false;
        p.emissionStrength = 0.0f;
        
        // Physics properties
        p.enablePhysics = true;
        p.enableCollision = true;
        p.collisionRadius = 0.2f;
        p.enableGravity = true;
        p.enableAirResistance = true;
        p.airResistanceFactor = 0.1f;
        p.enableBounce = false;
        p.bounceFactor = 0.0f;
        p.mass = 5.0f;
        p.density = 7.8f;
        p.friction = 0.3f;
        p.bounciness = 0.0f;
        
        // Ornamentation properties
        p.ornamentation = false;
        p.ornamentationScale = 1.0f;
        p.ornamentationIntensity = 0.5f;
        p.enableRunes = false;
        p.runeGlowIntensity = 0.0f;
        p.enableCrystals = false;
        p.crystalGlowIntensity = 0.0f;
        p.enableGems = false;
        p.gemGlowIntensity = 0.0f;
        
        // Performance properties
        p.enableCaching = true;
        p.enableHotReload = false;
        p.enableParallelProcessing = true;
        p.lodLevel = 0;
        
        return p;
    });
    
    lua.set_function("createDefaultUIParams", []() {
        UIParams u;
        u.iconSize = 64;
        u.borderColor = {1.0f, 1.0f, 1.0f, 0.8f};
        u.backgroundShape = BackgroundShape::RECTANGLE;
        u.flashOnSelect = true;
        u.borderThickness = 2.0f;
        u.cornerRadius = 4.0f;
        u.enableGlow = false;
        u.glowColor = {1.0f, 1.0f, 1.0f};
        u.glowIntensity = 1.0f;
        u.enablePulse = false;
        u.pulseFrequency = 1.0f;
        u.pulseAmplitude = 0.1f;
        u.enableHoverEffect = true;
        u.hoverScale = 1.1f;
        u.hoverDuration = 0.2f;
        u.enableClickEffect = true;
        u.clickScale = 0.95f;
        u.clickDuration = 0.1f;
        u.label = "";
        u.enableLabel = false;
        u.labelColor = {1.0f, 1.0f, 1.0f};
        u.labelSize = 12.0f;
        u.labelFont = "default";
        u.enableCaching = true;
        u.enableHotReload = false;
        u.lodLevel = 0;
        return u;
    });
}

void AlchemicalLauncherLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingLaunchers.begin(); it != pendingLaunchers.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                auto endTime = std::chrono::high_resolution_clock::now();
                auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - generationStartTime);
                lua["print"]("Launcher ready: " + it->second + " (generated in " + std::to_string(duration.count()) + "ms)");
                lua["print"]("  Vertices: " + std::to_string(b.vertexCount));
                lua["print"]("  Triangles: " + std::to_string(b.triangleCount));
                lua["print"]("  Particles: " + std::to_string(b.particleCount));
                lua["print"]("  GPU Accelerated: " + std::string(b.gpuAccelerated ? "Yes" : "No"));
            } catch (const std::exception& e) {
                lua["print"]("Error generating launcher: " + std::string(e.what()));
            }
            it = pendingLaunchers.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace AlchemicalLaunchers
} // namespace MagiTech
