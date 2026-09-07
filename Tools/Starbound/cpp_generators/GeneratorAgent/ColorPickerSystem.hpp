#pragma once
#include <string>
#include <vector>
#include <map>
#include <functional>
#include <memory>
#include <atomic>
#include <thread>
#include <future>
#include <filesystem>
#ifndef _WIN32
#include <dlfcn.h>
#endif
#include <glm/glm.hpp>
#include "vendor/json/include/nlohmann/json.hpp"
#include "vendor/imgui/imgui.h"

namespace MagiTech {
namespace ColorPicker {

// Plugin interface for color palette providers
class IColorPalettePlugin {
public:
    virtual ~IColorPalettePlugin() = default;
    
    // Plugin metadata
    virtual std::string getName() const = 0;
    virtual std::string getVersion() const = 0;
    virtual std::string getAuthor() const = 0;
    virtual std::string getDescription() const = 0;
    
    // Plugin lifecycle
    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
    virtual bool isEnabled() const = 0;
    
    // Palette management
    virtual std::vector<std::string> getAvailablePalettes() const = 0;
    virtual ColorPalette loadPalette(const std::string& name) = 0;
    virtual bool savePalette(const ColorPalette& palette) = 0;
    virtual bool deletePalette(const std::string& name) = 0;
    
    // Dynamic palette generation
    virtual std::vector<ColorPalette> generatePalettes(const std::string& context) = 0;
    virtual ColorPalette generatePaletteFromMood(const std::string& mood) = 0;
    virtual ColorPalette generatePaletteFromTheme(const std::string& theme) = 0;
    
    // Plugin capabilities
    virtual bool supportsDynamicGeneration() const = 0;
    virtual bool supportsMoodBasedGeneration() const = 0;
    virtual bool supportsThemeBasedGeneration() const = 0;
    virtual bool supportsRealTimeGeneration() const = 0;
};

// Plugin manager for handling multiple palette plugins
class ColorPalettePluginManager {
public:
    static ColorPalettePluginManager& instance();
    
    // Plugin loading and management
    bool loadPlugin(const std::string& pluginPath);
    bool loadLuaPlugin(const std::string& scriptPath);
    bool unloadPlugin(const std::string& pluginName);
    void unloadAllPlugins();
    
    // Plugin discovery
    void scanForPlugins(const std::string& directory);
    std::vector<std::string> getLoadedPluginNames() const;
    std::vector<std::string> getAvailablePluginPaths() const;
    
    // Plugin information
    std::string getPluginInfo(const std::string& pluginName) const;
    bool isPluginEnabled(const std::string& pluginName) const;
    void setPluginEnabled(const std::string& pluginName, bool enabled);
    
    // Palette access through plugins
    std::vector<std::string> getAllAvailablePalettes() const;
    ColorPalette loadPaletteFromPlugin(const std::string& pluginName, const std::string& paletteName);
    std::vector<ColorPalette> generatePalettesFromPlugin(const std::string& pluginName, const std::string& context);
    
    // Plugin capabilities query
    std::vector<std::string> getPluginsWithCapability(const std::string& capability) const;
    bool hasPluginWithCapability(const std::string& capability) const;
    
    // Plugin hot-reloading
    void enableHotReloading(bool enable);
    void checkForPluginUpdates();
    void reloadModifiedPlugins();
    
private:
    struct PluginInfo {
        std::string name;
        std::string path;
        std::string type; // "cpp" or "lua"
        void* handle; // For C++ plugins
        std::shared_ptr<IColorPalettePlugin> plugin;
        std::chrono::system_clock::time_point lastModified;
        bool enabled;
        std::map<std::string, bool> capabilities;
    };
    
    std::map<std::string, PluginInfo> m_plugins;
    std::atomic<bool> m_hotReloadEnabled{false};
    std::thread m_hotReloadThread;
    
    // Plugin loading helpers
    bool loadCppPlugin(const std::string& path);
    bool loadLuaPluginInternal(const std::string& path);
    void initializePluginCapabilities(PluginInfo& info);
    
    // Hot reload helpers
    void hotReloadWorker();
    bool hasPluginChanged(const PluginInfo& info) const;
    void reloadPlugin(const std::string& pluginName);
};

// Lua plugin interface for color palette generation
class LuaColorPalettePlugin : public IColorPalettePlugin {
public:
    explicit LuaColorPalettePlugin(const std::string& scriptPath);
    ~LuaColorPalettePlugin() override;
    
    // IColorPalettePlugin implementation
    std::string getName() const override;
    std::string getVersion() const override;
    std::string getAuthor() const override;
    std::string getDescription() const override;
    
    bool initialize() override;
    void shutdown() override;
    bool isEnabled() const override;
    
    std::vector<std::string> getAvailablePalettes() const override;
    ColorPalette loadPalette(const std::string& name) override;
    bool savePalette(const ColorPalette& palette) override;
    bool deletePalette(const std::string& name) override;
    
    std::vector<ColorPalette> generatePalettes(const std::string& context) override;
    ColorPalette generatePaletteFromMood(const std::string& mood) override;
    ColorPalette generatePaletteFromTheme(const std::string& theme) override;
    
    bool supportsDynamicGeneration() const override;
    bool supportsMoodBasedGeneration() const override;
    bool supportsThemeBasedGeneration() const override;
    bool supportsRealTimeGeneration() const override;
    
    // Lua-specific methods
    void reloadScript();
    bool isScriptValid() const;
    std::string getLastError() const;
    
private:
    std::string m_scriptPath;
    std::string m_name;
    std::string m_version;
    std::string m_author;
    std::string m_description;
    bool m_enabled;
    bool m_initialized;
    std::string m_lastError;
    
    // Lua state management
    void* m_luaState; // lua_State*
    bool initializeLuaState();
    void cleanupLuaState();
    
    // Lua function wrappers
    bool callLuaFunction(const std::string& functionName);
    bool callLuaFunctionWithString(const std::string& functionName, const std::string& param);
    std::string getLuaString(const std::string& variableName);
    std::vector<std::string> getLuaStringArray(const std::string& variableName);
    ColorPalette getLuaColorPalette(const std::string& variableName);
    std::vector<ColorPalette> getLuaColorPaletteArray(const std::string& variableName);
};

// C++ plugin interface for color palette generation
class CppColorPalettePlugin : public IColorPalettePlugin {
public:
    explicit CppColorPalettePlugin(const std::string& libraryPath);
    ~CppColorPalettePlugin() override;
    
    // IColorPalettePlugin implementation
    std::string getName() const override;
    std::string getVersion() const override;
    std::string getAuthor() const override;
    std::string getDescription() const override;
    
    bool initialize() override;
    void shutdown() override;
    bool isEnabled() const override;
    
    std::vector<std::string> getAvailablePalettes() const override;
    ColorPalette loadPalette(const std::string& name) override;
    bool savePalette(const ColorPalette& palette) override;
    bool deletePalette(const std::string& name) override;
    
    std::vector<ColorPalette> generatePalettes(const std::string& context) override;
    ColorPalette generatePaletteFromMood(const std::string& mood) override;
    ColorPalette generatePaletteFromTheme(const std::string& theme) override;
    
    bool supportsDynamicGeneration() const override;
    bool supportsMoodBasedGeneration() const override;
    bool supportsThemeBasedGeneration() const override;
    bool supportsRealTimeGeneration() const override;
    
private:
    std::string m_libraryPath;
    void* m_libraryHandle;
    bool m_enabled;
    bool m_initialized;
    
    // Function pointers for plugin interface
    using GetNameFunc = const char* (*)();
    using GetVersionFunc = const char* (*)();
    using GetAuthorFunc = const char* (*)();
    using GetDescriptionFunc = const char* (*)();
    using InitializeFunc = bool (*)();
    using ShutdownFunc = void (*)();
    using IsEnabledFunc = bool (*)();
    using GetAvailablePalettesFunc = const char** (*)(int* count);
    using LoadPaletteFunc = bool (*)(const char* name, ColorPalette* palette);
    using SavePaletteFunc = bool (*)(const ColorPalette* palette);
    using DeletePaletteFunc = bool (*)(const char* name);
    using GeneratePalettesFunc = bool (*)(const char* context, ColorPalette* palettes, int* count);
    using GeneratePaletteFromMoodFunc = bool (*)(const char* mood, ColorPalette* palette);
    using GeneratePaletteFromThemeFunc = bool (*)(const char* theme, ColorPalette* palette);
    using SupportsCapabilityFunc = bool (*)(const char* capability);
    
    GetNameFunc m_getName;
    GetVersionFunc m_getVersion;
    GetAuthorFunc m_getAuthor;
    GetDescriptionFunc m_getDescription;
    InitializeFunc m_initialize;
    ShutdownFunc m_shutdown;
    IsEnabledFunc m_isEnabled;
    GetAvailablePalettesFunc m_getAvailablePalettes;
    LoadPaletteFunc m_loadPalette;
    SavePaletteFunc m_savePalette;
    DeletePaletteFunc m_deletePalette;
    GeneratePalettesFunc m_generatePalettes;
    GeneratePaletteFromMoodFunc m_generatePaletteFromMood;
    GeneratePaletteFromThemeFunc m_generatePaletteFromTheme;
    SupportsCapabilityFunc m_supportsCapability;
    
    bool loadFunctionPointers();
    void cleanupFunctionPointers();
};

// Enhanced color representation with advanced features
struct Color {
    glm::vec4 rgba;  // Linear space
    glm::vec3 hsv;   // Hue, Saturation, Value
    glm::vec3 lab;   // CIE LAB color space
    glm::vec3 xyz;   // CIE XYZ color space
    
    // Color psychology attributes
    float energy;     // Energy level (0-1)
    float warmth;     // Warmth level (0-1)
    float intensity;  // Intensity level (0-1)
    
    Color() : rgba(1.0f, 1.0f, 1.0f, 1.0f), hsv(0.0f, 0.0f, 1.0f), 
              lab(100.0f, 0.0f, 0.0f), xyz(0.95f, 1.0f, 1.09f),
              energy(0.5f), warmth(0.5f), intensity(0.5f) {
        updateAllSpaces();
    }
    
    Color(float r, float g, float b, float a = 1.0f) : rgba(r, g, b, a) {
        updateAllSpaces();
    }
    
    Color(const glm::vec4& color) : rgba(color) {
        updateAllSpaces();
    }
    
    // Color space conversions
    void updateAllSpaces();
    void updateHSV();
    void updateRGB();
    void updateLAB();
    void updateXYZ();
    
    // Advanced color analysis
    void updatePsychology();
    float getLuminance() const;
    float getPerceivedBrightness() const;
    float getColorTemperature() const;
    
    // Utility functions
    std::string toHex() const;
    static Color fromHex(const std::string& hex);
    static Color fromHSV(float h, float s, float v, float a = 1.0f);
    static Color fromLAB(float l, float a, float b, float alpha = 1.0f);
    static Color fromTemperature(float kelvin, float alpha = 1.0f);
    
    // Enhanced color harmonies
    Color complementary() const;
    Color analogous(float offset = 30.0f) const;
    Color triadic() const;
    Color splitComplementary() const;
    Color tetradic() const;
    Color monochromatic(float saturationOffset = 0.2f, float valueOffset = 0.2f) const;
    Color square() const;
    Color rectangle() const;
    Color pentadic() const;
    
    // Color psychology harmonies
    Color energetic() const;
    Color calming() const;
    Color warm() const;
    Color cool() const;
    Color intense() const;
    Color soft() const;
};

// Color gradient system
struct ColorGradient {
    std::vector<std::pair<float, Color>> stops;
    std::string name;
    std::string description;
    
    ColorGradient() = default;
    ColorGradient(const std::string& n) : name(n) {}
    
    void addStop(float position, const Color& color);
    void removeStop(size_t index);
    Color sample(float t) const;
    ColorGradient reverse() const;
    ColorGradient blend(const ColorGradient& other, float t) const;
    
    // Serialization
    nlohmann::json toJson() const;
    static ColorGradient fromJson(const nlohmann::json& json);
};

// Enhanced color palette with advanced features
struct ColorPalette {
    std::string name;
    std::vector<Color> colors;
    std::string description;
    std::vector<std::string> tags;
    
    // Advanced palette features
    ColorGradient gradient;
    float harmonyStrength;
    bool isAccessible;
    std::string mood;
    std::string season;
    
    ColorPalette() : harmonyStrength(0.8f), isAccessible(false) {}
    ColorPalette(const std::string& n) : name(n), harmonyStrength(0.8f), isAccessible(false) {}
    
    void addColor(const Color& color);
    void removeColor(size_t index);
    void clear();
    size_t size() const { return colors.size(); }
    bool empty() const { return colors.empty(); }
    
    // Advanced palette operations
    void optimizeForAccessibility();
    void generateHarmoniousColors(int count);
    void applyMood(const std::string& mood);
    void adjustForSeason(const std::string& season);
    Color getDominantColor() const;
    float getAverageSaturation() const;
    float getAverageValue() const;
    
    // Serialization
    nlohmann::json toJson() const;
    static ColorPalette fromJson(const nlohmann::json& json);
};

// Enhanced color theme with advanced features
struct ColorTheme {
    std::string name;
    std::string description;
    std::map<std::string, Color> colorMap;
    
    // Advanced theme features
    ColorGradient primaryGradient;
    ColorGradient secondaryGradient;
    std::string mood;
    std::string season;
    float intensity;
    bool isAccessible;
    
    ColorTheme() : intensity(0.7f), isAccessible(false) {}
    ColorTheme(const std::string& n) : name(n), intensity(0.7f), isAccessible(false) {}
    
    void setColor(const std::string& paramName, const Color& color);
    Color getColor(const std::string& paramName) const;
    bool hasColor(const std::string& paramName) const;
    
    // Advanced theme operations
    void generateFromMood(const std::string& mood);
    void adjustForSeason(const std::string& season);
    void optimizeForAccessibility();
    void setIntensity(float intensity);
    
    // Serialization
    nlohmann::json toJson() const;
    static ColorTheme fromJson(const nlohmann::json& json);
};

// Machine learning color assistant
class ColorAI {
public:
    static ColorAI& instance();
    
    // AI-powered color generation
    Color generateColorFromMood(const std::string& mood);
    Color generateColorFromDescription(const std::string& description);
    std::vector<Color> generateHarmoniousPalette(const Color& base, int count);
    Color suggestComplementary(const Color& color);
    Color suggestAnalogous(const Color& color, float offset = 30.0f);
    
    // Color psychology analysis
    std::string analyzeMood(const Color& color);
    float analyzeEnergy(const Color& color);
    float analyzeWarmth(const Color& color);
    float analyzeIntensity(const Color& color);
    
    // Learning and adaptation
    void learnFromUserPreference(const Color& color, bool liked);
    void learnFromContext(const std::string& context, const Color& color);
    void updateModel();
    
private:
    std::map<std::string, std::vector<Color>> moodDatabase;
    std::map<std::string, float> userPreferences;
    std::atomic<bool> modelDirty{false};
    std::thread learningThread;
    
    void backgroundLearning();
    Color interpolateFromDatabase(const std::string& mood);
};

// Enhanced color picker system with plugin support
class ColorPickerSystem {
public:
    static ColorPickerSystem& instance();
    
    // Enhanced color picker UI with plugin support
    bool drawColorPicker(const char* label, Color& color, 
                        const ColorPickerFlags& flags = ColorPickerFlags::Default);
    bool drawAdvancedColorPicker(const char* label, Color& color);
    bool drawGradientEditor(const char* label, ColorGradient& gradient);
    bool drawPaletteEditor(const char* label, ColorPalette& palette);
    bool drawThemeEditor(const char* label, ColorTheme& theme);
    
    // Plugin-aware palette management
    void drawPluginPaletteSelector(const char* label, Color& selectedColor);
    void drawPluginPaletteGenerator(const char* label, ColorPalette& generatedPalette);
    void drawPluginManager(const char* label);
    
    // AI-assisted color picking with plugin support
    bool drawAIColorPicker(const char* label, Color& color, const std::string& context = "");
    bool drawMoodBasedPicker(const char* label, Color& color, const std::string& mood = "");
    bool drawSeasonalPicker(const char* label, Color& color, const std::string& season = "");
    
    // Advanced palette management with plugins
    void drawAdvancedPaletteSelector(const char* label, Color& selectedColor);
    void drawHarmonyGenerator(const char* label, Color& baseColor);
    void drawGradientSelector(const char* label, ColorGradient& selectedGradient);
    
    // Enhanced theme management with plugins
    void drawAdvancedThemeSelector(const char* label, const std::string& assetType, 
                                 std::map<std::string, Color>& colors);
    void drawMoodBasedThemeSelector(const char* label, const std::string& mood,
                                   std::map<std::string, Color>& colors);
    
    // Global management with plugin integration
    void addPalette(const ColorPalette& palette);
    void removePalette(const std::string& name);
    ColorPalette* getPalette(const std::string& name);
    std::vector<std::string> getPaletteNames() const;
    
    void addTheme(const ColorTheme& theme);
    void removeTheme(const std::string& name);
    ColorTheme* getTheme(const std::string& name);
    std::vector<std::string> getThemeNames(const std::string& assetType) const;
    
    void addGradient(const ColorGradient& gradient);
    void removeGradient(const std::string& name);
    ColorGradient* getGradient(const std::string& name);
    std::vector<std::string> getGradientNames() const;
    
    // Plugin-aware palette loading
    std::vector<ColorPalette> loadAllPluginPalettes();
    std::vector<ColorPalette> generatePalettesFromPlugins(const std::string& context);
    std::vector<ColorPalette> generatePalettesFromPluginsByMood(const std::string& mood);
    std::vector<ColorPalette> generatePalettesFromPluginsByTheme(const std::string& theme);
    
    // Enhanced file I/O with plugin support
    void savePalettes(const std::string& filename, bool compress = true);
    void loadPalettes(const std::string& filename);
    void saveThemes(const std::string& filename, bool compress = true);
    void loadThemes(const std::string& filename);
    void saveGradients(const std::string& filename, bool compress = true);
    void loadGradients(const std::string& filename);
    
    // Plugin management
    ColorPalettePluginManager& getPluginManager();
    void reloadAllPlugins();
    void scanForNewPlugins();
    
    // Advanced randomization with plugin assistance
    Color randomColor(float saturation = 0.8f, float value = 0.9f);
    Color randomColorFromMood(const std::string& mood);
    Color randomHarmony(const Color& base, const std::string& harmonyType);
    void randomizePalette(ColorPalette& palette, const std::string& harmonyType = "complementary");
    ColorGradient randomGradient(int stops = 4);
    
    // Performance optimization with plugin awareness
    void enableAsyncProcessing(bool enable);
    void setCacheSize(size_t size);
    void clearCache();
    void optimizeMemory();
    
    // Utility functions with enhanced features
    static Color lerp(const Color& a, const Color& b, float t);
    static Color lerpLAB(const Color& a, const Color& b, float t);
    static float getContrastRatio(const Color& a, const Color& b);
    static bool isAccessible(const Color& foreground, const Color& background);
    static Color blend(const Color& a, const Color& b, float t, BlendMode mode = BlendMode::Normal);
    
private:
    std::map<std::string, ColorPalette> m_palettes;
    std::map<std::string, ColorTheme> m_themes;
    std::map<std::string, ColorGradient> m_gradients;
    
    // Plugin integration
    ColorPalettePluginManager m_pluginManager;
    std::atomic<bool> m_pluginsEnabled{true};
    
    // Performance optimization
    std::map<uint64_t, Color> m_colorCache;
    std::atomic<size_t> m_cacheSize{1000};
    std::atomic<bool> m_asyncEnabled{true};
    std::thread m_processingThread;
    
    // Internal UI helpers with plugin support
    void drawColorWheel(float* hsv, float* alpha);
    void drawAdvancedColorSliders(float* rgba, float* hsv, float* lab);
    void drawHarmonyButtons(Color& color);
    void drawHexInput(Color& color);
    void drawLABInput(float* lab);
    void drawPsychologyPanel(Color& color);
    void drawGradientStops(ColorGradient& gradient);
    void drawSwatchGrid(const std::vector<Color>& colors, Color& selected);
    void drawPluginPaletteList(const std::vector<ColorPalette>& palettes, Color& selected);
    void drawPluginCapabilities(const std::string& pluginName);
    
    // Enhanced color space conversions
    static glm::vec3 rgbToHsv(const glm::vec3& rgb);
    static glm::vec3 hsvToRgb(const glm::vec3& hsv);
    static glm::vec3 rgbToLAB(const glm::vec3& rgb);
    static glm::vec3 labToRGB(const glm::vec3& lab);
    static glm::vec3 rgbToXYZ(const glm::vec3& rgb);
    static glm::vec3 xyzToRGB(const glm::vec3& xyz);
    static glm::vec3 linearToSrgb(const glm::vec3& linear);
    static glm::vec3 srgbToLinear(const glm::vec3& srgb);
    
    // Background processing with plugin awareness
    void backgroundProcessing();
    void processColorQueue();
    void processPluginUpdates();
};

// Enhanced color picker flags
enum class ColorPickerFlags {
    Default = 0,
    NoAlpha = 1 << 0,
    NoPreview = 1 << 1,
    NoInputs = 1 << 2,
    NoLabel = 1 << 3,
    NoHarmony = 1 << 4,
    NoHex = 1 << 5,
    NoSliders = 1 << 6,
    NoWheel = 1 << 7,
    Compact = 1 << 8,
    Popup = 1 << 9,
    Advanced = 1 << 10,
    AISuggestions = 1 << 11,
    PsychologyPanel = 1 << 12,
    GradientMode = 1 << 13,
    LABMode = 1 << 14
};

// Blend modes for color operations
enum class BlendMode {
    Normal,
    Multiply,
    Screen,
    Overlay,
    SoftLight,
    HardLight,
    ColorDodge,
    ColorBurn,
    Darken,
    Lighten
};

// Enhanced utility functions
namespace ColorUtils {
    // Advanced color space conversions
    glm::vec3 rgbToHsv(const glm::vec3& rgb);
    glm::vec3 hsvToRgb(const glm::vec3& hsv);
    glm::vec3 rgbToLAB(const glm::vec3& rgb);
    glm::vec3 labToRGB(const glm::vec3& lab);
    glm::vec3 rgbToXYZ(const glm::vec3& rgb);
    glm::vec3 xyzToRGB(const glm::vec3& xyz);
    glm::vec3 linearToSrgb(const glm::vec3& linear);
    glm::vec3 srgbToLinear(const glm::vec3& srgb);
    
    // Enhanced color harmonies
    Color complementary(const Color& color);
    Color analogous(const Color& color, float offset = 30.0f);
    Color triadic(const Color& color);
    Color splitComplementary(const Color& color);
    Color tetradic(const Color& color);
    Color monochromatic(const Color& color, float saturationOffset = 0.2f, float valueOffset = 0.2f);
    Color square(const Color& color);
    Color rectangle(const Color& color);
    Color pentadic(const Color& color);
    
    // Color psychology analysis
    float getLuminance(const Color& color);
    float getPerceivedBrightness(const Color& color);
    float getColorTemperature(const Color& color);
    std::string analyzeMood(const Color& color);
    float analyzeEnergy(const Color& color);
    float analyzeWarmth(const Color& color);
    float analyzeIntensity(const Color& color);
    
    // Advanced color analysis
    float getContrastRatio(const Color& a, const Color& b);
    bool isAccessible(const Color& foreground, const Color& background);
    bool isColorBlindFriendly(const Color& a, const Color& b);
    Color ensureContrast(const Color& foreground, const Color& background, float minRatio = 4.5f);
    
    // Enhanced randomization
    Color randomColor(float saturation = 0.8f, float value = 0.9f);
    Color randomColorFromMood(const std::string& mood);
    Color randomHarmony(const Color& base, const std::string& harmonyType);
    ColorGradient randomGradient(int stops = 4);
    
    // Advanced string conversion
    std::string colorToHex(const Color& color);
    Color hexToColor(const std::string& hex);
    std::string colorToRgbString(const Color& color);
    std::string colorToHsvString(const Color& color);
    std::string colorToLABString(const Color& color);
    std::string colorToTemperatureString(const Color& color);
    
    // Color interpolation
    Color lerp(const Color& a, const Color& b, float t);
    Color lerpLAB(const Color& a, const Color& b, float t);
    Color blend(const Color& a, const Color& b, float t, BlendMode mode = BlendMode::Normal);
}

// Enhanced predefined themes with advanced features
namespace ColorThemes {
    // Fire themes with enhanced psychology
    ColorTheme createFireTheme();
    ColorTheme createInfernoTheme();
    ColorTheme createEmberTheme();
    ColorTheme createPhoenixTheme();
    
    // Ice themes with enhanced psychology
    ColorTheme createIceTheme();
    ColorTheme createFrostTheme();
    ColorTheme createCrystalTheme();
    ColorTheme createAuroraTheme();
    
    // Arcane themes with enhanced psychology
    ColorTheme createArcaneTheme();
    ColorTheme createMysticTheme();
    ColorTheme createEtherealTheme();
    ColorTheme createCelestialTheme();
    
    // Nature themes with enhanced psychology
    ColorTheme createNatureTheme();
    ColorTheme createOrganicTheme();
    ColorTheme createVerdantTheme();
    ColorTheme createPrimalTheme();
    
    // Metal themes with enhanced psychology
    ColorTheme createSteelTheme();
    ColorTheme createBronzeTheme();
    ColorTheme createGoldTheme();
    ColorTheme createPlatinumTheme();
    
    // Void themes with enhanced psychology
    ColorTheme createVoidTheme();
    ColorTheme createShadowTheme();
    ColorTheme createAbyssTheme();
    ColorTheme createEclipseTheme();
    
    // Seasonal themes
    ColorTheme createSpringTheme();
    ColorTheme createSummerTheme();
    ColorTheme createAutumnTheme();
    ColorTheme createWinterTheme();
    
    // Mood-based themes
    ColorTheme createEnergeticTheme();
    ColorTheme createCalmingTheme();
    ColorTheme createPassionateTheme();
    ColorTheme createSereneTheme();
}

// Enhanced accessibility features
namespace Accessibility {
    // Advanced color blind friendly palettes
    ColorPalette createColorBlindFriendlyPalette();
    ColorPalette createHighContrastPalette();
    ColorPalette createDeuteranopiaPalette();
    ColorPalette createProtanopiaPalette();
    ColorPalette createTritanopiaPalette();
    
    // Enhanced accessibility checks
    bool isColorBlindFriendly(const Color& a, const Color& b);
    bool hasSufficientContrast(const Color& foreground, const Color& background);
    bool isAccessibleForDeuteranopia(const Color& a, const Color& b);
    bool isAccessibleForProtanopia(const Color& a, const Color& b);
    bool isAccessibleForTritanopia(const Color& a, const Color& b);
    
    // Enhanced accessibility helpers
    Color adjustForColorBlindness(const Color& color, const std::string& type = "deuteranopia");
    Color ensureContrast(const Color& foreground, const Color& background, float minRatio = 4.5f);
    Color optimizeForAccessibility(const Color& color, const std::vector<Color>& background);
    
    // Accessibility testing
    void testColorAccessibility(const Color& foreground, const Color& background);
    void generateAccessibilityReport(const ColorPalette& palette);
}

// Plugin utility functions
namespace PluginUtils {
    // Plugin discovery and loading
    std::vector<std::string> findPluginFiles(const std::string& directory, const std::string& extension);
    bool isValidPluginFile(const std::string& filePath);
    std::string getPluginType(const std::string& filePath);
    
    // Plugin validation
    bool validateCppPlugin(const std::string& filePath);
    bool validateLuaPlugin(const std::string& filePath);
    std::string getPluginValidationError(const std::string& filePath);
    
    // Plugin metadata extraction
    std::string extractPluginName(const std::string& filePath);
    std::string extractPluginVersion(const std::string& filePath);
    std::string extractPluginAuthor(const std::string& filePath);
    std::string extractPluginDescription(const std::string& filePath);
    
    // Plugin capabilities detection
    std::vector<std::string> detectPluginCapabilities(const std::string& filePath);
    bool hasPluginCapability(const std::string& filePath, const std::string& capability);
    
    // Plugin file management
    bool backupPlugin(const std::string& filePath);
    bool restorePlugin(const std::string& filePath);
    bool updatePlugin(const std::string& filePath, const std::string& newVersion);
    
    // Plugin dependency management
    std::vector<std::string> getPluginDependencies(const std::string& filePath);
    bool checkPluginDependencies(const std::string& filePath);
    bool resolvePluginDependencies(const std::string& filePath);
}

// Plugin configuration and settings
namespace PluginConfig {
    struct PluginSettings {
        bool enableHotReloading = true;
        bool enableAsyncLoading = true;
        bool enablePluginValidation = true;
        bool enableDependencyChecking = true;
        std::string pluginDirectory = "plugins/color_palettes";
        std::vector<std::string> enabledPlugins;
        std::vector<std::string> disabledPlugins;
        std::map<std::string, std::map<std::string, std::string>> pluginOptions;
    };
    
    PluginSettings loadSettings(const std::string& configPath);
    void saveSettings(const PluginSettings& settings, const std::string& configPath);
    void applySettings(const PluginSettings& settings);
}

} // namespace ColorPicker
} // namespace MagiTech 
