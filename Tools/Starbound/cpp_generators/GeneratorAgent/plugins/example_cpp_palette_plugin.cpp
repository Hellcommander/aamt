#include "ColorPickerSystem.hpp"
#include <random>
#include <algorithm>
#include <memory>

namespace MagiTech {
namespace ColorPicker {

// Example C++ Color Palette Plugin
class ExampleCppPalettePlugin : public IColorPalettePlugin {
private:
    std::string m_name;
    std::string m_version;
    std::string m_author;
    std::string m_description;
    bool m_enabled;
    bool m_initialized;
    
    // Plugin data
    std::map<std::string, ColorPalette> m_palettes;
    std::vector<std::string> m_availablePalettes;
    std::mt19937 m_randomGenerator;
    
public:
    ExampleCppPalettePlugin() 
        : m_name("ExampleCppPalettePlugin")
        , m_version("1.0.0")
        , m_author("MagiTech Developer")
        , m_description("An example C++ plugin demonstrating color palette generation")
        , m_enabled(false)
        , m_initialized(false)
        , m_randomGenerator(std::random_device{}()) {
    }
    
    ~ExampleCppPalettePlugin() override = default;
    
    // IColorPalettePlugin implementation
    std::string getName() const override { return m_name; }
    std::string getVersion() const override { return m_version; }
    std::string getAuthor() const override { return m_author; }
    std::string getDescription() const override { return m_description; }
    
    bool initialize() override {
        if (m_initialized) return true;
        
        // Initialize plugin data
        initializePalettes();
        m_availablePalettes = {
            "cpp_metallic",
            "cpp_neon",
            "cpp_pastel",
            "cpp_earth",
            "cpp_cyber",
            "cpp_vintage",
            "cpp_nature",
            "cpp_abstract"
        };
        
        m_enabled = true;
        m_initialized = true;
        
        Log::info("C++ Plugin initialized: {} v{}", m_name, m_version);
        return true;
    }
    
    void shutdown() override {
        if (m_initialized) {
            m_enabled = false;
            m_initialized = false;
            m_palettes.clear();
            m_availablePalettes.clear();
            Log::info("C++ Plugin shutdown: {}", m_name);
        }
    }
    
    bool isEnabled() const override { return m_enabled; }
    
    std::vector<std::string> getAvailablePalettes() const override {
        return m_availablePalettes;
    }
    
    ColorPalette loadPalette(const std::string& name) override {
        auto it = m_palettes.find(name);
        if (it != m_palettes.end()) {
            return it->second;
        }
        
        // Generate palette if not found
        return generatePaletteByName(name);
    }
    
    bool savePalette(const ColorPalette& palette) override {
        m_palettes[palette.name] = palette;
        
        // Add to available palettes if not already present
        if (std::find(m_availablePalettes.begin(), m_availablePalettes.end(), palette.name) 
            == m_availablePalettes.end()) {
            m_availablePalettes.push_back(palette.name);
        }
        
        return true;
    }
    
    bool deletePalette(const std::string& name) override {
        auto it = m_palettes.find(name);
        if (it != m_palettes.end()) {
            m_palettes.erase(it);
            
            // Remove from available palettes
            auto palIt = std::find(m_availablePalettes.begin(), m_availablePalettes.end(), name);
            if (palIt != m_availablePalettes.end()) {
                m_availablePalettes.erase(palIt);
            }
            
            return true;
        }
        return false;
    }
    
    std::vector<ColorPalette> generatePalettes(const std::string& context) override {
        std::vector<ColorPalette> generated;
        
        if (context == "metallic") {
            generated.push_back(createMetallicPalette());
        } else if (context == "neon") {
            generated.push_back(createNeonPalette());
        } else if (context == "pastel") {
            generated.push_back(createPastelPalette());
        } else if (context == "earth") {
            generated.push_back(createEarthPalette());
        } else if (context == "cyber") {
            generated.push_back(createCyberPalette());
        } else if (context == "vintage") {
            generated.push_back(createVintagePalette());
        } else if (context == "nature") {
            generated.push_back(createNaturePalette());
        } else if (context == "abstract") {
            generated.push_back(createAbstractPalette());
        } else {
            // Generate random palette
            generated.push_back(createRandomPalette(context));
        }
        
        return generated;
    }
    
    ColorPalette generatePaletteFromMood(const std::string& mood) override {
        if (mood == "energetic") {
            return createEnergeticPalette();
        } else if (mood == "calming") {
            return createCalmingPalette();
        } else if (mood == "mystical") {
            return createMysticalPalette();
        } else if (mood == "warm") {
            return createWarmPalette();
        } else if (mood == "cool") {
            return createCoolPalette();
        } else {
            return createNeutralPalette();
        }
    }
    
    ColorPalette generatePaletteFromTheme(const std::string& theme) override {
        if (theme == "fire") {
            return createFireThemePalette();
        } else if (theme == "water") {
            return createWaterThemePalette();
        } else if (theme == "earth") {
            return createEarthThemePalette();
        } else if (theme == "air") {
            return createAirThemePalette();
        } else {
            return createGenericThemePalette(theme);
        }
    }
    
    bool supportsDynamicGeneration() const override { return true; }
    bool supportsMoodBasedGeneration() const override { return true; }
    bool supportsThemeBasedGeneration() const override { return true; }
    bool supportsRealTimeGeneration() const override { return false; }
    
private:
    void initializePalettes() {
        // Initialize predefined palettes
        m_palettes["cpp_metallic"] = createMetallicPalette();
        m_palettes["cpp_neon"] = createNeonPalette();
        m_palettes["cpp_pastel"] = createPastelPalette();
        m_palettes["cpp_earth"] = createEarthPalette();
        m_palettes["cpp_cyber"] = createCyberPalette();
        m_palettes["cpp_vintage"] = createVintagePalette();
        m_palettes["cpp_nature"] = createNaturePalette();
        m_palettes["cpp_abstract"] = createAbstractPalette();
    }
    
    ColorPalette generatePaletteByName(const std::string& name) {
        if (name.find("metallic") != std::string::npos) {
            return createMetallicPalette();
        } else if (name.find("neon") != std::string::npos) {
            return createNeonPalette();
        } else if (name.find("pastel") != std::string::npos) {
            return createPastelPalette();
        } else if (name.find("earth") != std::string::npos) {
            return createEarthPalette();
        } else if (name.find("cyber") != std::string::npos) {
            return createCyberPalette();
        } else if (name.find("vintage") != std::string::npos) {
            return createVintagePalette();
        } else if (name.find("nature") != std::string::npos) {
            return createNaturePalette();
        } else if (name.find("abstract") != std::string::npos) {
            return createAbstractPalette();
        } else {
            return createRandomPalette(name);
        }
    }
    
    // Palette creation methods
    ColorPalette createMetallicPalette() {
        ColorPalette palette("C++ Metallic");
        palette.description = "Metallic colors with chrome and steel tones";
        palette.tags = {"metallic", "chrome", "steel", "industrial"};
        palette.mood = "industrial";
        palette.season = "winter";
        
        palette.addColor(Color(0.8f, 0.8f, 0.8f, 1.0f));  // Silver
        palette.addColor(Color(0.6f, 0.6f, 0.6f, 1.0f));  // Steel
        palette.addColor(Color(0.9f, 0.9f, 0.9f, 1.0f));  // Chrome
        palette.addColor(Color(0.4f, 0.4f, 0.4f, 1.0f));  // Dark steel
        palette.addColor(Color(0.7f, 0.7f, 0.7f, 1.0f));  // Light steel
        
        return palette;
    }
    
    ColorPalette createNeonPalette() {
        ColorPalette palette("C++ Neon");
        palette.description = "Bright neon colors with high saturation";
        palette.tags = {"neon", "bright", "vibrant", "cyber"};
        palette.mood = "energetic";
        palette.season = "summer";
        
        palette.addColor(Color(1.0f, 0.0f, 1.0f, 1.0f));  // Magenta
        palette.addColor(Color(0.0f, 1.0f, 1.0f, 1.0f));  // Cyan
        palette.addColor(Color(1.0f, 1.0f, 0.0f, 1.0f));  // Yellow
        palette.addColor(Color(1.0f, 0.0f, 0.0f, 1.0f));  // Red
        palette.addColor(Color(0.0f, 1.0f, 0.0f, 1.0f));  // Green
        
        return palette;
    }
    
    ColorPalette createPastelPalette() {
        ColorPalette palette("C++ Pastel");
        palette.description = "Soft pastel colors with low saturation";
        palette.tags = {"pastel", "soft", "gentle", "calming"};
        palette.mood = "calming";
        palette.season = "spring";
        
        palette.addColor(Color(1.0f, 0.8f, 0.8f, 1.0f));  // Light pink
        palette.addColor(Color(0.8f, 0.8f, 1.0f, 1.0f));  // Light blue
        palette.addColor(Color(0.8f, 1.0f, 0.8f, 1.0f));  // Light green
        palette.addColor(Color(1.0f, 1.0f, 0.8f, 1.0f));  // Light yellow
        palette.addColor(Color(1.0f, 0.8f, 1.0f, 1.0f));  // Light purple
        
        return palette;
    }
    
    ColorPalette createEarthPalette() {
        ColorPalette palette("C++ Earth");
        palette.description = "Natural earth tones with brown and green";
        palette.tags = {"earth", "natural", "organic", "warm"};
        palette.mood = "natural";
        palette.season = "autumn";
        
        palette.addColor(Color(0.6f, 0.4f, 0.2f, 1.0f));  // Brown
        palette.addColor(Color(0.4f, 0.6f, 0.2f, 1.0f));  // Olive
        palette.addColor(Color(0.8f, 0.6f, 0.4f, 1.0f));  // Tan
        palette.addColor(Color(0.3f, 0.5f, 0.3f, 1.0f));  // Forest green
        palette.addColor(Color(0.5f, 0.3f, 0.1f, 1.0f));  // Dark brown
        
        return palette;
    }
    
    ColorPalette createCyberPalette() {
        ColorPalette palette("C++ Cyber");
        palette.description = "Cyberpunk colors with neon and dark tones";
        palette.tags = {"cyber", "neon", "dark", "futuristic"};
        palette.mood = "energetic";
        palette.season = "winter";
        
        palette.addColor(Color(0.0f, 0.0f, 0.0f, 1.0f));  // Black
        palette.addColor(Color(0.0f, 1.0f, 1.0f, 1.0f));  // Cyan
        palette.addColor(Color(1.0f, 0.0f, 1.0f, 1.0f));  // Magenta
        palette.addColor(Color(0.2f, 0.2f, 0.4f, 1.0f));  // Dark blue
        palette.addColor(Color(0.0f, 0.8f, 0.4f, 1.0f));  // Neon green
        
        return palette;
    }
    
    ColorPalette createVintagePalette() {
        ColorPalette palette("C++ Vintage");
        palette.description = "Vintage colors with sepia and warm tones";
        palette.tags = {"vintage", "sepia", "warm", "retro"};
        palette.mood = "warm";
        palette.season = "autumn";
        
        palette.addColor(Color(0.8f, 0.6f, 0.4f, 1.0f));  // Sepia
        palette.addColor(Color(0.9f, 0.7f, 0.5f, 1.0f));  // Light sepia
        palette.addColor(Color(0.6f, 0.4f, 0.2f, 1.0f));  // Dark sepia
        palette.addColor(Color(0.7f, 0.5f, 0.3f, 1.0f));  // Medium sepia
        palette.addColor(Color(1.0f, 0.8f, 0.6f, 1.0f));  // Cream
        
        return palette;
    }
    
    ColorPalette createNaturePalette() {
        ColorPalette palette("C++ Nature");
        palette.description = "Natural colors inspired by nature";
        palette.tags = {"nature", "natural", "organic", "fresh"};
        palette.mood = "natural";
        palette.season = "spring";
        
        palette.addColor(Color(0.2f, 0.8f, 0.4f, 1.0f));  // Green
        palette.addColor(Color(0.4f, 0.6f, 0.2f, 1.0f));  // Olive
        palette.addColor(Color(0.8f, 0.9f, 0.6f, 1.0f));  // Light green
        palette.addColor(Color(0.6f, 0.4f, 0.2f, 1.0f));  // Brown
        palette.addColor(Color(0.9f, 0.8f, 0.6f, 1.0f));  // Sand
        
        return palette;
    }
    
    ColorPalette createAbstractPalette() {
        ColorPalette palette("C++ Abstract");
        palette.description = "Abstract colors with artistic combinations";
        palette.tags = {"abstract", "artistic", "creative", "modern"};
        palette.mood = "creative";
        palette.season = "summer";
        
        palette.addColor(Color(0.8f, 0.2f, 0.6f, 1.0f));  // Purple-pink
        palette.addColor(Color(0.2f, 0.8f, 0.6f, 1.0f));  // Teal
        palette.addColor(Color(0.8f, 0.6f, 0.2f, 1.0f));  // Orange
        palette.addColor(Color(0.6f, 0.2f, 0.8f, 1.0f));  // Purple
        palette.addColor(Color(0.2f, 0.6f, 0.8f, 1.0f));  // Blue-green
        
        return palette;
    }
    
    ColorPalette createEnergeticPalette() {
        ColorPalette palette("C++ Energetic");
        palette.description = "Energetic colors with high saturation";
        palette.tags = {"energetic", "vibrant", "passionate", "dynamic"};
        palette.mood = "energetic";
        palette.season = "summer";
        
        palette.addColor(Color(1.0f, 0.0f, 0.0f, 1.0f));  // Red
        palette.addColor(Color(1.0f, 0.5f, 0.0f, 1.0f));  // Orange
        palette.addColor(Color(1.0f, 1.0f, 0.0f, 1.0f));  // Yellow
        palette.addColor(Color(0.8f, 0.2f, 0.0f, 1.0f));  // Dark red
        palette.addColor(Color(1.0f, 0.8f, 0.2f, 1.0f));  // Gold
        
        return palette;
    }
    
    ColorPalette createCalmingPalette() {
        ColorPalette palette("C++ Calming");
        palette.description = "Calming colors with cool tones";
        palette.tags = {"calming", "cool", "serene", "peaceful"};
        palette.mood = "calming";
        palette.season = "winter";
        
        palette.addColor(Color(0.2f, 0.6f, 1.0f, 1.0f));  // Blue
        palette.addColor(Color(0.4f, 0.8f, 1.0f, 1.0f));  // Light blue
        palette.addColor(Color(0.6f, 0.9f, 1.0f, 1.0f));  // Cyan
        palette.addColor(Color(0.0f, 0.4f, 0.8f, 1.0f));  // Dark blue
        palette.addColor(Color(0.8f, 0.9f, 1.0f, 1.0f));  // Very light blue
        
        return palette;
    }
    
    ColorPalette createMysticalPalette() {
        ColorPalette palette("C++ Mystical");
        palette.description = "Mystical colors with purple and magical tones";
        palette.tags = {"mystical", "magical", "purple", "enchanting"};
        palette.mood = "mystical";
        palette.season = "autumn";
        
        palette.addColor(Color(0.6f, 0.2f, 1.0f, 1.0f));  // Purple
        palette.addColor(Color(0.8f, 0.4f, 1.0f, 1.0f));  // Light purple
        palette.addColor(Color(0.4f, 0.0f, 0.8f, 1.0f));  // Dark purple
        palette.addColor(Color(1.0f, 0.6f, 1.0f, 1.0f));  // Pink
        palette.addColor(Color(0.2f, 0.0f, 0.6f, 1.0f));  // Deep purple
        
        return palette;
    }
    
    ColorPalette createWarmPalette() {
        ColorPalette palette("C++ Warm");
        palette.description = "Warm colors with red and orange tones";
        palette.tags = {"warm", "cozy", "comforting", "inviting"};
        palette.mood = "warm";
        palette.season = "autumn";
        
        palette.addColor(Color(1.0f, 0.4f, 0.2f, 1.0f));  // Orange
        palette.addColor(Color(1.0f, 0.6f, 0.3f, 1.0f));  // Light orange
        palette.addColor(Color(0.8f, 0.3f, 0.1f, 1.0f));  // Dark red
        palette.addColor(Color(1.0f, 0.8f, 0.4f, 1.0f));  // Peach
        palette.addColor(Color(0.9f, 0.5f, 0.2f, 1.0f));  // Terracotta
        
        return palette;
    }
    
    ColorPalette createCoolPalette() {
        ColorPalette palette("C++ Cool");
        palette.description = "Cool colors with blue and green tones";
        palette.tags = {"cool", "refreshing", "calm", "soothing"};
        palette.mood = "cool";
        palette.season = "winter";
        
        palette.addColor(Color(0.2f, 0.6f, 1.0f, 1.0f));  // Blue
        palette.addColor(Color(0.4f, 0.8f, 1.0f, 1.0f));  // Light blue
        palette.addColor(Color(0.2f, 0.8f, 0.4f, 1.0f));  // Green
        palette.addColor(Color(0.0f, 0.4f, 0.8f, 1.0f));  // Dark blue
        palette.addColor(Color(0.6f, 0.9f, 1.0f, 1.0f));  // Cyan
        
        return palette;
    }
    
    ColorPalette createNeutralPalette() {
        ColorPalette palette("C++ Neutral");
        palette.description = "Neutral colors with gray tones";
        palette.tags = {"neutral", "balanced", "subtle", "minimal"};
        palette.mood = "neutral";
        palette.season = "winter";
        
        palette.addColor(Color(0.5f, 0.5f, 0.5f, 1.0f));  // Gray
        palette.addColor(Color(0.7f, 0.7f, 0.7f, 1.0f));  // Light gray
        palette.addColor(Color(0.3f, 0.3f, 0.3f, 1.0f));  // Dark gray
        palette.addColor(Color(0.9f, 0.9f, 0.9f, 1.0f));  // Very light gray
        palette.addColor(Color(0.1f, 0.1f, 0.1f, 1.0f));  // Very dark gray
        
        return palette;
    }
    
    ColorPalette createFireThemePalette() {
        ColorPalette palette("C++ Fire Theme");
        palette.description = "Fire-themed colors with red and orange";
        palette.tags = {"fire", "hot", "passionate", "energetic"};
        palette.mood = "energetic";
        palette.season = "summer";
        
        palette.addColor(Color(1.0f, 0.0f, 0.0f, 1.0f));  // Red
        palette.addColor(Color(1.0f, 0.4f, 0.2f, 1.0f));  // Orange
        palette.addColor(Color(1.0f, 0.8f, 0.4f, 1.0f));  // Light orange
        palette.addColor(Color(0.8f, 0.2f, 0.0f, 1.0f));  // Dark red
        palette.addColor(Color(1.0f, 0.6f, 0.3f, 1.0f));  // Terracotta
        
        return palette;
    }
    
    ColorPalette createWaterThemePalette() {
        ColorPalette palette("C++ Water Theme");
        palette.description = "Water-themed colors with blue and cyan";
        palette.tags = {"water", "fluid", "refreshing", "calming"};
        palette.mood = "calming";
        palette.season = "summer";
        
        palette.addColor(Color(0.2f, 0.6f, 1.0f, 1.0f));  // Blue
        palette.addColor(Color(0.4f, 0.8f, 1.0f, 1.0f));  // Light blue
        palette.addColor(Color(0.6f, 0.9f, 1.0f, 1.0f));  // Cyan
        palette.addColor(Color(0.0f, 0.4f, 0.8f, 1.0f));  // Dark blue
        palette.addColor(Color(0.8f, 0.9f, 1.0f, 1.0f));  // Very light blue
        
        return palette;
    }
    
    ColorPalette createEarthThemePalette() {
        ColorPalette palette("C++ Earth Theme");
        palette.description = "Earth-themed colors with brown and green";
        palette.tags = {"earth", "grounded", "natural", "stable"};
        palette.mood = "natural";
        palette.season = "autumn";
        
        palette.addColor(Color(0.6f, 0.4f, 0.2f, 1.0f));  // Brown
        palette.addColor(Color(0.4f, 0.6f, 0.2f, 1.0f));  // Olive
        palette.addColor(Color(0.8f, 0.6f, 0.4f, 1.0f));  // Tan
        palette.addColor(Color(0.3f, 0.5f, 0.3f, 1.0f));  // Forest green
        palette.addColor(Color(0.5f, 0.3f, 0.1f, 1.0f));  // Dark brown
        
        return palette;
    }
    
    ColorPalette createAirThemePalette() {
        ColorPalette palette("C++ Air Theme");
        palette.description = "Air-themed colors with white and light blue";
        palette.tags = {"air", "light", "ethereal", "free"};
        palette.mood = "light";
        palette.season = "spring";
        
        palette.addColor(Color(1.0f, 1.0f, 1.0f, 1.0f));  // White
        palette.addColor(Color(0.9f, 0.95f, 1.0f, 1.0f)); // Very light blue
        palette.addColor(Color(0.8f, 0.9f, 1.0f, 1.0f));  // Light blue
        palette.addColor(Color(0.95f, 0.97f, 1.0f, 1.0f)); // Almost white
        palette.addColor(Color(0.7f, 0.85f, 1.0f, 1.0f)); // Sky blue
        
        return palette;
    }
    
    ColorPalette createGenericThemePalette(const std::string& theme) {
        ColorPalette palette("C++ " + theme + " Theme");
        palette.description = "Generated theme palette for: " + theme;
        palette.tags = {"generated", "theme", theme};
        palette.mood = "neutral";
        palette.season = "summer";
        
        // Generate colors based on theme name hash
        std::hash<std::string> hasher;
        size_t hash = hasher(theme);
        
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        m_randomGenerator.seed(hash);
        
        for (int i = 0; i < 5; ++i) {
            float r = dist(m_randomGenerator);
            float g = dist(m_randomGenerator);
            float b = dist(m_randomGenerator);
            palette.addColor(Color(r, g, b, 1.0f));
        }
        
        return palette;
    }
    
    ColorPalette createRandomPalette(const std::string& name) {
        ColorPalette palette("C++ Random " + name);
        palette.description = "Randomly generated palette";
        palette.tags = {"random", "generated", "dynamic"};
        palette.mood = "neutral";
        palette.season = "summer";
        
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        
        for (int i = 0; i < 5; ++i) {
            float r = dist(m_randomGenerator);
            float g = dist(m_randomGenerator);
            float b = dist(m_randomGenerator);
            palette.addColor(Color(r, g, b, 1.0f));
        }
        
        return palette;
    }
};

// Plugin creation function (required for C++ plugins)
extern "C" IColorPalettePlugin* createColorPalettePlugin() {
    return new ExampleCppPalettePlugin();
}

// Plugin metadata functions (required for C++ plugins)
extern "C" const char* getPluginName() {
    return "ExampleCppPalettePlugin";
}

extern "C" const char* getPluginVersion() {
    return "1.0.0";
}

extern "C" const char* getPluginAuthor() {
    return "MagiTech Developer";
}

extern "C" const char* getPluginDescription() {
    return "An example C++ plugin demonstrating color palette generation";
}

} // namespace ColorPicker
} // namespace MagiTech 
