#include "ColorPickerSystem.hpp"
#include "core/Log.hpp"
#include <sstream>
#include <iomanip>
#include <random>
#include <algorithm>
#include <fstream>
#include <future>
#include <chrono>

namespace MagiTech {
namespace ColorPicker {

// Enhanced Color implementation
void Color::updateAllSpaces() {
    updateHSV();
    updateLAB();
    updateXYZ();
    updatePsychology();
}

void Color::updateHSV() {
    hsv = ColorUtils::rgbToHsv(glm::vec3(rgba.r, rgba.g, rgba.b));
}

void Color::updateRGB() {
    glm::vec3 rgb = ColorUtils::hsvToRgb(hsv);
    rgba.r = rgb.r;
    rgba.g = rgb.g;
    rgba.b = rgb.b;
    updateLAB();
    updateXYZ();
    updatePsychology();
}

void Color::updateLAB() {
    lab = ColorUtils::rgbToLAB(glm::vec3(rgba.r, rgba.g, rgba.b));
}

void Color::updateXYZ() {
    xyz = ColorUtils::rgbToXYZ(glm::vec3(rgba.r, rgba.g, rgba.b));
}

void Color::updatePsychology() {
    // Calculate color psychology attributes
    energy = (hsv.z * 0.6f + hsv.y * 0.4f);
    warmth = (hsv.x < 60.0f || hsv.x > 300.0f) ? 1.0f : 0.0f;
    intensity = (hsv.y * 0.7f + hsv.z * 0.3f);
}

float Color::getLuminance() const {
    return ColorUtils::getLuminance(*this);
}

float Color::getPerceivedBrightness() const {
    return ColorUtils::getPerceivedBrightness(*this);
}

float Color::getColorTemperature() const {
    return ColorUtils::getColorTemperature(*this);
}

std::string Color::toHex() const {
    return ColorUtils::colorToHex(*this);
}

Color Color::fromHex(const std::string& hex) {
    return ColorUtils::hexToColor(hex);
}

Color Color::fromHSV(float h, float s, float v, float a) {
    Color color;
    color.hsv = glm::vec3(h, s, v);
    color.rgba.a = a;
    color.updateRGB();
    return color;
}

Color Color::fromLAB(float l, float a, float b, float alpha) {
    Color color;
    color.lab = glm::vec3(l, a, b);
    color.rgba.a = alpha;
    glm::vec3 rgb = ColorUtils::labToRGB(color.lab);
    color.rgba.r = rgb.r;
    color.rgba.g = rgb.g;
    color.rgba.b = rgb.b;
    color.updateAllSpaces();
    return color;
}

Color Color::fromTemperature(float kelvin, float alpha) {
    // Convert color temperature to RGB
    float temp = kelvin / 100.0f;
    float red, green, blue;
    
    if (temp <= 66.0f) {
        red = 255.0f;
        green = temp;
        green = 99.4708025861f * log(green) - 161.1195681661f;
        if (temp <= 19.0f) {
            blue = 0.0f;
        } else {
            blue = temp - 10.0f;
            blue = 138.5177312231f * log(blue) - 305.0447927307f;
        }
    } else {
        red = temp - 60.0f;
        red = 329.698727446f * pow(red, -0.1332047592f);
        green = temp - 60.0f;
        green = 288.1221695283f * pow(green, -0.0755148492f);
        blue = 255.0f;
    }
    
    return Color(
        std::clamp(red / 255.0f, 0.0f, 1.0f),
        std::clamp(green / 255.0f, 0.0f, 1.0f),
        std::clamp(blue / 255.0f, 0.0f, 1.0f),
        alpha
    );
}

// Enhanced color harmonies
Color Color::complementary() const {
    return ColorUtils::complementary(*this);
}

Color Color::analogous(float offset) const {
    return ColorUtils::analogous(*this, offset);
}

Color Color::triadic() const {
    return ColorUtils::triadic(*this);
}

Color Color::splitComplementary() const {
    return ColorUtils::splitComplementary(*this);
}

Color Color::tetradic() const {
    return ColorUtils::tetradic(*this);
}

Color Color::monochromatic(float saturationOffset, float valueOffset) const {
    return ColorUtils::monochromatic(*this, saturationOffset, valueOffset);
}

Color Color::square() const {
    return ColorUtils::square(*this);
}

Color Color::rectangle() const {
    return ColorUtils::rectangle(*this);
}

Color Color::pentadic() const {
    return ColorUtils::pentadic(*this);
}

// Color psychology harmonies
Color Color::energetic() const {
    Color result = *this;
    result.hsv.y = std::min(result.hsv.y * 1.3f, 1.0f);
    result.hsv.z = std::min(result.hsv.z * 1.2f, 1.0f);
    result.updateRGB();
    return result;
}

Color Color::calming() const {
    Color result = *this;
    result.hsv.y = std::max(result.hsv.y * 0.7f, 0.1f);
    result.hsv.z = std::max(result.hsv.z * 0.8f, 0.3f);
    result.updateRGB();
    return result;
}

Color Color::warm() const {
    Color result = *this;
    if (result.hsv.x > 180.0f) {
        result.hsv.x = std::max(result.hsv.x - 60.0f, 0.0f);
    }
    result.updateRGB();
    return result;
}

Color Color::cool() const {
    Color result = *this;
    if (result.hsv.x < 180.0f) {
        result.hsv.x = std::min(result.hsv.x + 60.0f, 360.0f);
    }
    result.updateRGB();
    return result;
}

Color Color::intense() const {
    Color result = *this;
    result.hsv.y = 1.0f;
    result.hsv.z = 1.0f;
    result.updateRGB();
    return result;
}

Color Color::soft() const {
    Color result = *this;
    result.hsv.y = std::max(result.hsv.y * 0.5f, 0.1f);
    result.hsv.z = std::max(result.hsv.z * 0.7f, 0.4f);
    result.updateRGB();
    return result;
}

// ColorGradient implementation
void ColorGradient::addStop(float position, const Color& color) {
    stops.emplace_back(position, color);
    std::sort(stops.begin(), stops.end());
}

void ColorGradient::removeStop(size_t index) {
    if (index < stops.size()) {
        stops.erase(stops.begin() + index);
    }
}

Color ColorGradient::sample(float t) const {
    if (stops.empty()) return Color();
    if (stops.size() == 1) return stops[0].second;
    
    t = std::clamp(t, 0.0f, 1.0f);
    
    // Find the two stops to interpolate between
    for (size_t i = 0; i < stops.size() - 1; ++i) {
        if (t >= stops[i].first && t <= stops[i + 1].first) {
            float localT = (t - stops[i].first) / (stops[i + 1].first - stops[i].first);
            return ColorUtils::lerp(stops[i].second, stops[i + 1].second, localT);
        }
    }
    
    return stops.back().second;
}

ColorGradient ColorGradient::reverse() const {
    ColorGradient reversed(name + "_reversed");
    for (const auto& stop : stops) {
        reversed.addStop(1.0f - stop.first, stop.second);
    }
    return reversed;
}

ColorGradient ColorGradient::blend(const ColorGradient& other, float t) const {
    ColorGradient blended(name + "_blended");
    
    // Collect all unique positions
    std::set<float> positions;
    for (const auto& stop : stops) positions.insert(stop.first);
    for (const auto& stop : other.stops) positions.insert(stop.first);
    
    // Create blended stops
    for (float pos : positions) {
        Color color1 = sample(pos);
        Color color2 = other.sample(pos);
        Color blendedColor = ColorUtils::lerp(color1, color2, t);
        blended.addStop(pos, blendedColor);
    }
    
    return blended;
}

nlohmann::json ColorGradient::toJson() const {
    nlohmann::json j;
    j["name"] = name;
    j["description"] = description;
    
    nlohmann::json stopsArray = nlohmann::json::array();
    for (const auto& stop : stops) {
        stopsArray.push_back({
            {"position", stop.first},
            {"color", {
                {"r", stop.second.rgba.r},
                {"g", stop.second.rgba.g},
                {"b", stop.second.rgba.b},
                {"a", stop.second.rgba.a}
            }}
        });
    }
    j["stops"] = stopsArray;
    
    return j;
}

ColorGradient ColorGradient::fromJson(const nlohmann::json& json) {
    ColorGradient gradient;
    gradient.name = json["name"];
    gradient.description = json["description"];
    
    for (const auto& stopJson : json["stops"]) {
        float position = stopJson["position"];
        Color color(
            stopJson["color"]["r"],
            stopJson["color"]["g"],
            stopJson["color"]["b"],
            stopJson["color"]["a"]
        );
        gradient.addStop(position, color);
    }
    
    return gradient;
}

// Enhanced ColorPalette implementation
void ColorPalette::addColor(const Color& color) {
    colors.push_back(color);
}

void ColorPalette::removeColor(size_t index) {
    if (index < colors.size()) {
        colors.erase(colors.begin() + index);
    }
}

void ColorPalette::clear() {
    colors.clear();
}

void ColorPalette::optimizeForAccessibility() {
    for (auto& color : colors) {
        color = Accessibility::optimizeForAccessibility(color, colors);
    }
    isAccessible = true;
}

void ColorPalette::generateHarmoniousColors(int count) {
    if (colors.empty()) return;
    
    Color baseColor = colors[0];
    std::vector<Color> harmonious;
    
    // Generate different harmony types
    harmonious.push_back(baseColor.complementary());
    harmonious.push_back(baseColor.analogous(30.0f));
    harmonious.push_back(baseColor.analogous(-30.0f));
    harmonious.push_back(baseColor.triadic());
    harmonious.push_back(baseColor.splitComplementary());
    
    // Add to palette
    for (size_t i = 0; i < std::min(static_cast<size_t>(count), harmonious.size()); ++i) {
        addColor(harmonious[i]);
    }
}

void ColorPalette::applyMood(const std::string& mood) {
    this->mood = mood;
    
    if (mood == "energetic") {
        for (auto& color : colors) {
            color = color.energetic();
        }
    } else if (mood == "calming") {
        for (auto& color : colors) {
            color = color.calming();
        }
    } else if (mood == "warm") {
        for (auto& color : colors) {
            color = color.warm();
        }
    } else if (mood == "cool") {
        for (auto& color : colors) {
            color = color.cool();
        }
    }
}

void ColorPalette::adjustForSeason(const std::string& season) {
    this->season = season;
    
    if (season == "spring") {
        for (auto& color : colors) {
            color.hsv.y = std::min(color.hsv.y * 1.2f, 1.0f);
            color.hsv.z = std::min(color.hsv.z * 1.1f, 1.0f);
            color.updateRGB();
        }
    } else if (season == "summer") {
        for (auto& color : colors) {
            color.hsv.z = std::min(color.hsv.z * 1.3f, 1.0f);
            color.updateRGB();
        }
    } else if (season == "autumn") {
        for (auto& color : colors) {
            color.hsv.x = std::fmod(color.hsv.x + 30.0f, 360.0f);
            color.updateRGB();
        }
    } else if (season == "winter") {
        for (auto& color : colors) {
            color.hsv.y = std::max(color.hsv.y * 0.8f, 0.2f);
            color.hsv.z = std::max(color.hsv.z * 0.9f, 0.4f);
            color.updateRGB();
        }
    }
}

Color ColorPalette::getDominantColor() const {
    if (colors.empty()) return Color();
    
    // Find color with highest saturation and value
    Color dominant = colors[0];
    float maxScore = dominant.hsv.y * dominant.hsv.z;
    
    for (const auto& color : colors) {
        float score = color.hsv.y * color.hsv.z;
        if (score > maxScore) {
            maxScore = score;
            dominant = color;
        }
    }
    
    return dominant;
}

float ColorPalette::getAverageSaturation() const {
    if (colors.empty()) return 0.0f;
    
    float total = 0.0f;
    for (const auto& color : colors) {
        total += color.hsv.y;
    }
    return total / colors.size();
}

float ColorPalette::getAverageValue() const {
    if (colors.empty()) return 0.0f;
    
    float total = 0.0f;
    for (const auto& color : colors) {
        total += color.hsv.z;
    }
    return total / colors.size();
}

nlohmann::json ColorPalette::toJson() const {
    nlohmann::json j;
    j["name"] = name;
    j["description"] = description;
    j["tags"] = tags;
    j["harmonyStrength"] = harmonyStrength;
    j["isAccessible"] = isAccessible;
    j["mood"] = mood;
    j["season"] = season;
    j["gradient"] = gradient.toJson();
    
    nlohmann::json colorsArray = nlohmann::json::array();
    for (const auto& color : colors) {
        colorsArray.push_back({
            {"r", color.rgba.r},
            {"g", color.rgba.g},
            {"b", color.rgba.b},
            {"a", color.rgba.a},
            {"energy", color.energy},
            {"warmth", color.warmth},
            {"intensity", color.intensity}
        });
    }
    j["colors"] = colorsArray;
    
    return j;
}

ColorPalette ColorPalette::fromJson(const nlohmann::json& json) {
    ColorPalette palette;
    palette.name = json["name"];
    palette.description = json["description"];
    palette.tags = json["tags"].get<std::vector<std::string>>();
    palette.harmonyStrength = json["harmonyStrength"];
    palette.isAccessible = json["isAccessible"];
    palette.mood = json["mood"];
    palette.season = json["season"];
    palette.gradient = ColorGradient::fromJson(json["gradient"]);
    
    for (const auto& colorJson : json["colors"]) {
        Color color(
            colorJson["r"],
            colorJson["g"],
            colorJson["b"],
            colorJson["a"]
        );
        color.energy = colorJson["energy"];
        color.warmth = colorJson["warmth"];
        color.intensity = colorJson["intensity"];
        palette.colors.push_back(color);
    }
    
    return palette;
}

// Enhanced ColorTheme implementation
void ColorTheme::setColor(const std::string& paramName, const Color& color) {
    colorMap[paramName] = color;
}

Color ColorTheme::getColor(const std::string& paramName) const {
    auto it = colorMap.find(paramName);
    return it != colorMap.end() ? it->second : Color();
}

bool ColorTheme::hasColor(const std::string& paramName) const {
    return colorMap.find(paramName) != colorMap.end();
}

void ColorTheme::generateFromMood(const std::string& mood) {
    this->mood = mood;
    
    // Generate colors based on mood using AI
    auto& ai = ColorAI::instance();
    
    Color primary = ai.generateColorFromMood(mood);
    Color secondary = ai.suggestComplementary(primary);
    Color accent = ai.suggestAnalogous(primary, 60.0f);
    
    setColor("colorPrimary", primary);
    setColor("colorSecondary", secondary);
    setColor("colorAccent", accent);
    setColor("glowColor", primary.energetic());
    setColor("muzzleFlashColor", primary.intense());
    setColor("muzzleSmokeColor", secondary.calming());
}

void ColorTheme::adjustForSeason(const std::string& season) {
    this->season = season;
    
    for (auto& [paramName, color] : colorMap) {
        if (season == "spring") {
            color.hsv.y = std::min(color.hsv.y * 1.2f, 1.0f);
            color.hsv.z = std::min(color.hsv.z * 1.1f, 1.0f);
        } else if (season == "summer") {
            color.hsv.z = std::min(color.hsv.z * 1.3f, 1.0f);
        } else if (season == "autumn") {
            color.hsv.x = std::fmod(color.hsv.x + 30.0f, 360.0f);
        } else if (season == "winter") {
            color.hsv.y = std::max(color.hsv.y * 0.8f, 0.2f);
            color.hsv.z = std::max(color.hsv.z * 0.9f, 0.4f);
        }
        color.updateRGB();
    }
}

void ColorTheme::optimizeForAccessibility() {
    for (auto& [paramName, color] : colorMap) {
        color = Accessibility::optimizeForAccessibility(color, {});
    }
    isAccessible = true;
}

void ColorTheme::setIntensity(float intensity) {
    this->intensity = intensity;
    
    for (auto& [paramName, color] : colorMap) {
        color.hsv.y = std::clamp(color.hsv.y * intensity, 0.1f, 1.0f);
        color.hsv.z = std::clamp(color.hsv.z * intensity, 0.3f, 1.0f);
        color.updateRGB();
    }
}

nlohmann::json ColorTheme::toJson() const {
    nlohmann::json j;
    j["name"] = name;
    j["description"] = description;
    j["mood"] = mood;
    j["season"] = season;
    j["intensity"] = intensity;
    j["isAccessible"] = isAccessible;
    j["primaryGradient"] = primaryGradient.toJson();
    j["secondaryGradient"] = secondaryGradient.toJson();
    
    nlohmann::json colorsObj;
    for (const auto& [paramName, color] : colorMap) {
        colorsObj[paramName] = {
            {"r", color.rgba.r},
            {"g", color.rgba.g},
            {"b", color.rgba.b},
            {"a", color.rgba.a},
            {"energy", color.energy},
            {"warmth", color.warmth},
            {"intensity", color.intensity}
        };
    }
    j["colors"] = colorsObj;
    
    return j;
}

ColorTheme ColorTheme::fromJson(const nlohmann::json& json) {
    ColorTheme theme;
    theme.name = json["name"];
    theme.description = json["description"];
    theme.mood = json["mood"];
    theme.season = json["season"];
    theme.intensity = json["intensity"];
    theme.isAccessible = json["isAccessible"];
    theme.primaryGradient = ColorGradient::fromJson(json["primaryGradient"]);
    theme.secondaryGradient = ColorGradient::fromJson(json["secondaryGradient"]);
    
    for (const auto& [paramName, colorJson] : json["colors"].items()) {
        Color color(
            colorJson["r"],
            colorJson["g"],
            colorJson["b"],
            colorJson["a"]
        );
        color.energy = colorJson["energy"];
        color.warmth = colorJson["warmth"];
        color.intensity = colorJson["intensity"];
        theme.colorMap[paramName] = color;
    }
    
    return theme;
}

// ColorAI implementation
ColorAI& ColorAI::instance() {
    static ColorAI instance;
    return instance;
}

Color ColorAI::generateColorFromMood(const std::string& mood) {
    // Check if we have colors for this mood in database
    auto it = moodDatabase.find(mood);
    if (it != moodDatabase.end() && !it->second.empty()) {
        return interpolateFromDatabase(mood);
    }
    
    // Generate based on mood keywords
    if (mood.find("energetic") != std::string::npos || mood.find("fire") != std::string::npos) {
        return Color::fromHSV(0.0f, 0.9f, 1.0f); // Bright red
    } else if (mood.find("calming") != std::string::npos || mood.find("ice") != std::string::npos) {
        return Color::fromHSV(200.0f, 0.7f, 0.9f); // Cool blue
    } else if (mood.find("mystical") != std::string::npos || mood.find("arcane") != std::string::npos) {
        return Color::fromHSV(280.0f, 0.8f, 0.9f); // Purple
    } else if (mood.find("natural") != std::string::npos || mood.find("earth") != std::string::npos) {
        return Color::fromHSV(120.0f, 0.7f, 0.8f); // Green
    }
    
    // Default to a neutral color
    return Color::fromHSV(0.0f, 0.0f, 0.8f);
}

Color ColorAI::generateColorFromDescription(const std::string& description) {
    // Simple keyword-based color generation
    std::string desc = description;
    std::transform(desc.begin(), desc.end(), desc.begin(), ::tolower);
    
    if (desc.find("red") != std::string::npos) return Color::fromHSV(0.0f, 0.9f, 1.0f);
    if (desc.find("blue") != std::string::npos) return Color::fromHSV(240.0f, 0.9f, 1.0f);
    if (desc.find("green") != std::string::npos) return Color::fromHSV(120.0f, 0.9f, 1.0f);
    if (desc.find("yellow") != std::string::npos) return Color::fromHSV(60.0f, 0.9f, 1.0f);
    if (desc.find("purple") != std::string::npos) return Color::fromHSV(280.0f, 0.9f, 1.0f);
    if (desc.find("orange") != std::string::npos) return Color::fromHSV(30.0f, 0.9f, 1.0f);
    
    return Color::fromHSV(0.0f, 0.0f, 0.8f);
}

std::vector<Color> ColorAI::generateHarmoniousPalette(const Color& base, int count) {
    std::vector<Color> palette;
    palette.push_back(base);
    
    if (count > 1) palette.push_back(base.complementary());
    if (count > 2) palette.push_back(base.analogous(30.0f));
    if (count > 3) palette.push_back(base.analogous(-30.0f));
    if (count > 4) palette.push_back(base.triadic());
    if (count > 5) palette.push_back(base.splitComplementary());
    
    return palette;
}

Color ColorAI::suggestComplementary(const Color& color) {
    return color.complementary();
}

Color ColorAI::suggestAnalogous(const Color& color, float offset) {
    return color.analogous(offset);
}

std::string ColorAI::analyzeMood(const Color& color) {
    if (color.energy > 0.8f) return "energetic";
    if (color.energy < 0.3f) return "calming";
    if (color.warmth > 0.7f) return "warm";
    if (color.warmth < 0.3f) return "cool";
    if (color.intensity > 0.8f) return "intense";
    if (color.intensity < 0.3f) return "soft";
    return "neutral";
}

float ColorAI::analyzeEnergy(const Color& color) {
    return color.energy;
}

float ColorAI::analyzeWarmth(const Color& color) {
    return color.warmth;
}

float ColorAI::analyzeIntensity(const Color& color) {
    return color.intensity;
}

void ColorAI::learnFromUserPreference(const Color& color, bool liked) {
    std::string mood = analyzeMood(color);
    if (liked) {
        moodDatabase[mood].push_back(color);
    }
    modelDirty = true;
}

void ColorAI::learnFromContext(const std::string& context, const Color& color) {
    moodDatabase[context].push_back(color);
    modelDirty = true;
}

void ColorAI::updateModel() {
    if (modelDirty) {
        // In a real implementation, this would update the AI model
        modelDirty = false;
    }
}

void ColorAI::backgroundLearning() {
    while (true) {
        if (modelDirty) {
            updateModel();
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

Color ColorAI::interpolateFromDatabase(const std::string& mood) {
    auto it = moodDatabase.find(mood);
    if (it == moodDatabase.end() || it->second.empty()) {
        return Color();
    }
    
    const auto& colors = it->second;
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_int_distribution<size_t> dist(0, colors.size() - 1);
    
    return colors[dist(gen)];
}

// Enhanced ColorPickerSystem implementation
ColorPickerSystem& ColorPickerSystem::instance() {
    static ColorPickerSystem instance;
    return instance;
}

bool ColorPickerSystem::drawColorPicker(const char* label, Color& color, const ColorPickerFlags& flags) {
    bool changed = false;
    
    // Draw label if not disabled
    if (!(flags & ColorPickerFlags::NoLabel)) {
        ImGui::Text("%s", label);
        ImGui::SameLine();
    }
    
    // Draw preview swatch
    if (!(flags & ColorPickerFlags::NoPreview)) {
        ImVec4 imColor(color.rgba.r, color.rgba.g, color.rgba.b, color.rgba.a);
        ImGui::ColorButton("##preview", imColor, 
                          (flags & ColorPickerFlags::NoAlpha) ? ImGuiColorEditFlags_NoAlpha : 0,
                          ImVec2(20, 20));
        
        // Open color picker on click
        if (ImGui::BeginPopupContextItem("color_picker_popup")) {
            float rgba[4] = {color.rgba.r, color.rgba.g, color.rgba.b, color.rgba.a};
            float hsv[3] = {color.hsv.x, color.hsv.y, color.hsv.z};
            
            // Main color picker
            if (!(flags & ColorPickerFlags::NoWheel)) {
                drawColorWheel(hsv, &rgba[3]);
            }
            
            // Color sliders
            if (!(flags & ColorPickerFlags::NoSliders)) {
                drawAdvancedColorSliders(rgba, hsv, nullptr);
            }
            
            // Hex input
            if (!(flags & ColorPickerFlags::NoHex)) {
                drawHexInput(color);
            }
            
            // Harmony buttons
            if (!(flags & ColorPickerFlags::NoHarmony)) {
                drawHarmonyButtons(color);
            }
            
            // Psychology panel
            if (flags & ColorPickerFlags::PsychologyPanel) {
                drawPsychologyPanel(color);
            }
            
            // Update color if changed
            if (rgba[0] != color.rgba.r || rgba[1] != color.rgba.g || 
                rgba[2] != color.rgba.b || rgba[3] != color.rgba.a) {
                color.rgba = glm::vec4(rgba[0], rgba[1], rgba[2], rgba[3]);
                color.updateAllSpaces();
                changed = true;
            }
            
            ImGui::EndPopup();
        }
    }
    
    return changed;
}

bool ColorPickerSystem::drawAdvancedColorPicker(const char* label, Color& color) {
    bool changed = false;
    
    ImGui::Text("%s", label);
    
    if (ImGui::BeginTabBar("ColorPickerTabs")) {
        if (ImGui::BeginTabItem("HSV")) {
            float hsv[3] = {color.hsv.x, color.hsv.y, color.hsv.z};
            float alpha = color.rgba.a;
            
            drawColorWheel(hsv, &alpha);
            drawAdvancedColorSliders(nullptr, hsv, nullptr);
            
            if (hsv[0] != color.hsv.x || hsv[1] != color.hsv.y || hsv[2] != color.hsv.z || alpha != color.rgba.a) {
                color.hsv = glm::vec3(hsv[0], hsv[1], hsv[2]);
                color.rgba.a = alpha;
                color.updateRGB();
                changed = true;
            }
            
            ImGui::EndTabItem();
        }
        
        if (ImGui::BeginTabItem("LAB")) {
            float lab[3] = {color.lab.x, color.lab.y, color.lab.z};
            float alpha = color.rgba.a;
            
            drawLABInput(lab);
            ImGui::SameLine();
            ImGui::ColorPicker4("##alpha", &alpha, ImGuiColorEditFlags_AlphaBar);
            
            if (lab[0] != color.lab.x || lab[1] != color.lab.y || lab[2] != color.lab.z || alpha != color.rgba.a) {
                color.lab = glm::vec3(lab[0], lab[1], lab[2]);
                color.rgba.a = alpha;
                glm::vec3 rgb = ColorUtils::labToRGB(color.lab);
                color.rgba.r = rgb.r;
                color.rgba.g = rgb.g;
                color.rgba.b = rgb.b;
                color.updateAllSpaces();
                changed = true;
            }
            
            ImGui::EndTabItem();
        }
        
        if (ImGui::BeginTabItem("Psychology")) {
            drawPsychologyPanel(color);
            ImGui::EndTabItem();
        }
        
        ImGui::EndTabBar();
    }
    
    return changed;
}

void ColorPickerSystem::drawColorWheel(float* hsv, float* alpha) {
    ImGui::ColorPicker3("##wheel", hsv, 
                        ImGuiColorEditFlags_DisplayHSV |
                        ImGuiColorEditFlags_PickerHueWheel |
                        ImGuiColorEditFlags_NoInputs);
    
    if (alpha) {
        ImGui::SameLine();
        ImGui::ColorPicker4("##alpha", alpha, ImGuiColorEditFlags_AlphaBar);
    }
}

void ColorPickerSystem::drawAdvancedColorSliders(float* rgba, float* hsv, float* lab) {
    ImGui::Separator();
    
    if (rgba) {
        // RGB sliders
        ImGui::Text("RGB:");
        ImGui::SameLine();
        ImGui::PushItemWidth(60);
        bool changed = false;
        changed |= ImGui::DragFloat("##R", &rgba[0], 0.01f, 0.0f, 1.0f, "R: %.2f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##G", &rgba[1], 0.01f, 0.0f, 1.0f, "G: %.2f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##B", &rgba[2], 0.01f, 0.0f, 1.0f, "B: %.2f");
        if (rgba[3]) {
            ImGui::SameLine();
            changed |= ImGui::DragFloat("##A", rgba + 3, 0.01f, 0.0f, 1.0f, "A: %.2f");
        }
        ImGui::PopItemWidth();
    }
    
    if (hsv) {
        // HSV sliders
        ImGui::Text("HSV:");
        ImGui::SameLine();
        ImGui::PushItemWidth(60);
        bool changed = false;
        changed |= ImGui::DragFloat("##H", &hsv[0], 1.0f, 0.0f, 360.0f, "H: %.0f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##S", &hsv[1], 0.01f, 0.0f, 1.0f, "S: %.2f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##V", &hsv[2], 0.01f, 0.0f, 1.0f, "V: %.2f");
        ImGui::PopItemWidth();
    }
    
    if (lab) {
        // LAB sliders
        ImGui::Text("LAB:");
        ImGui::SameLine();
        ImGui::PushItemWidth(60);
        bool changed = false;
        changed |= ImGui::DragFloat("##L", &lab[0], 1.0f, 0.0f, 100.0f, "L: %.1f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##A", &lab[1], 1.0f, -128.0f, 127.0f, "A: %.1f");
        ImGui::SameLine();
        changed |= ImGui::DragFloat("##B", &lab[2], 1.0f, -128.0f, 127.0f, "B: %.1f");
        ImGui::PopItemWidth();
    }
}

void ColorPickerSystem::drawLABInput(float* lab) {
    ImGui::Text("LAB Color Space:");
    ImGui::PushItemWidth(80);
    ImGui::DragFloat("L", &lab[0], 1.0f, 0.0f, 100.0f, "L: %.1f");
    ImGui::SameLine();
    ImGui::DragFloat("A", &lab[1], 1.0f, -128.0f, 127.0f, "A: %.1f");
    ImGui::SameLine();
    ImGui::DragFloat("B", &lab[2], 1.0f, -128.0f, 127.0f, "B: %.1f");
    ImGui::PopItemWidth();
}

void ColorPickerSystem::drawPsychologyPanel(Color& color) {
    ImGui::Separator();
    ImGui::Text("Color Psychology:");
    
    ImGui::Text("Energy: %.2f", color.energy);
    ImGui::SameLine();
    ImGui::Text("Warmth: %.2f", color.warmth);
    ImGui::SameLine();
    ImGui::Text("Intensity: %.2f", color.intensity);
    
    ImGui::Text("Mood: %s", ColorAI::instance().analyzeMood(color).c_str());
    
    if (ImGui::Button("Make Energetic")) {
        color = color.energetic();
    }
    ImGui::SameLine();
    if (ImGui::Button("Make Calming")) {
        color = color.calming();
    }
    ImGui::SameLine();
    if (ImGui::Button("Make Warm")) {
        color = color.warm();
    }
    ImGui::SameLine();
    if (ImGui::Button("Make Cool")) {
        color = color.cool();
    }
}

void ColorPickerSystem::drawHexInput(Color& color) {
    ImGui::Separator();
    
    static char hexBuf[9] = "#FFFFFF";
    if (ImGui::InputText("Hex", hexBuf, sizeof(hexBuf), ImGuiInputTextFlags_CharsHexadecimal)) {
        Color newColor = Color::fromHex(hexBuf);
        if (newColor.rgba != color.rgba) {
            color = newColor;
        }
    }
    
    // Update hex buffer when color changes
    std::string currentHex = color.toHex();
    if (strcmp(hexBuf, currentHex.c_str()) != 0) {
        strcpy(hexBuf, currentHex.c_str());
    }
}

void ColorPickerSystem::drawHarmonyButtons(Color& color) {
    ImGui::Separator();
    ImGui::Text("Harmonies:");
    
    if (ImGui::Button("Complementary")) {
        color = color.complementary();
    }
    ImGui::SameLine();
    if (ImGui::Button("Analogous")) {
        color = color.analogous();
    }
    ImGui::SameLine();
    if (ImGui::Button("Triadic")) {
        color = color.triadic();
    }
    
    if (ImGui::Button("Split Comp")) {
        color = color.splitComplementary();
    }
    ImGui::SameLine();
    if (ImGui::Button("Tetradic")) {
        color = color.tetradic();
    }
    ImGui::SameLine();
    if (ImGui::Button("Square")) {
        color = color.square();
    }
    
    if (ImGui::Button("Mono")) {
        color = color.monochromatic();
    }
    ImGui::SameLine();
    if (ImGui::Button("Rectangle")) {
        color = color.rectangle();
    }
    ImGui::SameLine();
    if (ImGui::Button("Pentadic")) {
        color = color.pentadic();
    }
}

// Enhanced color space conversions
glm::vec3 ColorPickerSystem::rgbToHsv(const glm::vec3& rgb) {
    return ColorUtils::rgbToHsv(rgb);
}

glm::vec3 ColorPickerSystem::hsvToRgb(const glm::vec3& hsv) {
    return ColorUtils::hsvToRgb(hsv);
}

glm::vec3 ColorPickerSystem::rgbToLAB(const glm::vec3& rgb) {
    return ColorUtils::rgbToLAB(rgb);
}

glm::vec3 ColorPickerSystem::labToRGB(const glm::vec3& lab) {
    return ColorUtils::labToRGB(lab);
}

glm::vec3 ColorPickerSystem::rgbToXYZ(const glm::vec3& rgb) {
    return ColorUtils::rgbToXYZ(rgb);
}

glm::vec3 ColorPickerSystem::xyzToRGB(const glm::vec3& xyz) {
    return ColorUtils::xyzToRGB(xyz);
}

glm::vec3 ColorPickerSystem::linearToSrgb(const glm::vec3& linear) {
    return ColorUtils::linearToSrgb(linear);
}

glm::vec3 ColorPickerSystem::srgbToLinear(const glm::vec3& srgb) {
    return ColorUtils::srgbToLinear(srgb);
}

// Performance optimization methods
void ColorPickerSystem::enableAsyncProcessing(bool enable) {
    m_asyncEnabled = enable;
}

void ColorPickerSystem::setCacheSize(size_t size) {
    m_cacheSize = size;
}

void ColorPickerSystem::clearCache() {
    m_colorCache.clear();
}

void ColorPickerSystem::optimizeMemory() {
    // Trim cache to size limit
    if (m_colorCache.size() > m_cacheSize) {
        std::map<uint64_t, Color> newCache;
        size_t count = 0;
        for (const auto& [key, color] : m_colorCache) {
            if (count++ < m_cacheSize) {
                newCache[key] = color;
            }
        }
        m_colorCache = std::move(newCache);
    }
}

void ColorPickerSystem::backgroundProcessing() {
    while (m_asyncEnabled) {
        processColorQueue();
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

void ColorPickerSystem::processColorQueue() {
    // Process any pending color operations
    // This would handle background color generation, caching, etc.
}

} // namespace ColorPicker
} // namespace MagiTech 
