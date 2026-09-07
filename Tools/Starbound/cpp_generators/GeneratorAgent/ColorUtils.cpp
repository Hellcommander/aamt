#include "ColorPickerSystem.hpp"
#include <random>
#include <sstream>
#include <iomanip>
#include <cmath>

namespace MagiTech {
namespace ColorPicker {

namespace ColorUtils {

// Color space conversions
glm::vec3 rgbToHsv(const glm::vec3& rgb) {
    float r = rgb.r, g = rgb.g, b = rgb.b;
    float max = std::max({r, g, b});
    float min = std::min({r, g, b});
    float delta = max - min;
    
    float h = 0.0f, s = 0.0f, v = max;
    
    if (delta != 0.0f) {
        s = delta / max;
        
        if (max == r) {
            h = fmod((g - b) / delta, 6.0f);
        } else if (max == g) {
            h = (b - r) / delta + 2.0f;
        } else {
            h = (r - g) / delta + 4.0f;
        }
        
        h *= 60.0f;
        if (h < 0.0f) h += 360.0f;
    }
    
    return glm::vec3(h, s, v);
}

glm::vec3 hsvToRgb(const glm::vec3& hsv) {
    float h = hsv.x, s = hsv.y, v = hsv.z;
    
    if (s == 0.0f) {
        return glm::vec3(v, v, v);
    }
    
    h /= 60.0f;
    int i = static_cast<int>(h);
    float f = h - i;
    float p = v * (1.0f - s);
    float q = v * (1.0f - s * f);
    float t = v * (1.0f - s * (1.0f - f));
    
    switch (i) {
        case 0: return glm::vec3(v, t, p);
        case 1: return glm::vec3(q, v, p);
        case 2: return glm::vec3(p, v, t);
        case 3: return glm::vec3(p, q, v);
        case 4: return glm::vec3(t, p, v);
        default: return glm::vec3(v, p, q);
    }
}

glm::vec3 linearToSrgb(const glm::vec3& linear) {
    glm::vec3 srgb;
    for (int i = 0; i < 3; i++) {
        if (linear[i] <= 0.0031308f) {
            srgb[i] = linear[i] * 12.92f;
        } else {
            srgb[i] = 1.055f * pow(linear[i], 1.0f / 2.4f) - 0.055f;
        }
    }
    return srgb;
}

glm::vec3 srgbToLinear(const glm::vec3& srgb) {
    glm::vec3 linear;
    for (int i = 0; i < 3; i++) {
        if (srgb[i] <= 0.04045f) {
            linear[i] = srgb[i] / 12.92f;
        } else {
            linear[i] = pow((srgb[i] + 0.055f) / 1.055f, 2.4f);
        }
    }
    return linear;
}

// Color harmonies
Color complementary(const Color& color) {
    float newHue = fmod(color.hsv.x + 180.0f, 360.0f);
    return Color::fromHSV(newHue, color.hsv.y, color.hsv.z, color.rgba.a);
}

Color analogous(const Color& color, float offset) {
    float newHue = fmod(color.hsv.x + offset, 360.0f);
    if (newHue < 0.0f) newHue += 360.0f;
    return Color::fromHSV(newHue, color.hsv.y, color.hsv.z, color.rgba.a);
}

Color triadic(const Color& color) {
    float newHue = fmod(color.hsv.x + 120.0f, 360.0f);
    return Color::fromHSV(newHue, color.hsv.y, color.hsv.z, color.rgba.a);
}

Color splitComplementary(const Color& color) {
    float newHue = fmod(color.hsv.x + 150.0f, 360.0f);
    return Color::fromHSV(newHue, color.hsv.y, color.hsv.z, color.rgba.a);
}

Color tetradic(const Color& color) {
    float newHue = fmod(color.hsv.x + 90.0f, 360.0f);
    return Color::fromHSV(newHue, color.hsv.y, color.hsv.z, color.rgba.a);
}

Color monochromatic(const Color& color, float saturationOffset, float valueOffset) {
    float newS = std::clamp(color.hsv.y + saturationOffset, 0.0f, 1.0f);
    float newV = std::clamp(color.hsv.z + valueOffset, 0.0f, 1.0f);
    return Color::fromHSV(color.hsv.x, newS, newV, color.rgba.a);
}

// Color analysis
float getLuminance(const Color& color) {
    // Convert to linear RGB and apply luminance weights
    glm::vec3 linear = srgbToLinear(glm::vec3(color.rgba.r, color.rgba.g, color.rgba.b));
    return 0.2126f * linear.r + 0.7152f * linear.g + 0.0722f * linear.b;
}

float getContrastRatio(const Color& a, const Color& b) {
    float lumA = getLuminance(a);
    float lumB = getLuminance(b);
    
    float lighter = std::max(lumA, lumB);
    float darker = std::min(lumA, lumB);
    
    return (lighter + 0.05f) / (darker + 0.05f);
}

bool isAccessible(const Color& foreground, const Color& background) {
    float ratio = getContrastRatio(foreground, background);
    return ratio >= 4.5f; // WCAG AA standard for normal text
}

// Randomization
Color randomColor(float saturation, float value) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<float> hueDist(0.0f, 360.0f);
    static std::uniform_real_distribution<float> satDist(0.0f, 1.0f);
    static std::uniform_real_distribution<float> valDist(0.0f, 1.0f);
    
    float h = hueDist(gen);
    float s = std::clamp(satDist(gen) * saturation, 0.0f, 1.0f);
    float v = std::clamp(valDist(gen) * value, 0.0f, 1.0f);
    
    return Color::fromHSV(h, s, v);
}

Color randomHarmony(const Color& base, const std::string& harmonyType) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_real_distribution<float> offsetDist(-30.0f, 30.0f);
    
    if (harmonyType == "complementary") {
        return base.complementary();
    } else if (harmonyType == "analogous") {
        float offset = offsetDist(gen);
        return base.analogous(offset);
    } else if (harmonyType == "triadic") {
        return base.triadic();
    } else if (harmonyType == "split_complementary") {
        return base.splitComplementary();
    } else if (harmonyType == "tetradic") {
        return base.tetradic();
    } else if (harmonyType == "monochromatic") {
        static std::uniform_real_distribution<float> monoDist(-0.3f, 0.3f);
        float satOffset = monoDist(gen);
        float valOffset = monoDist(gen);
        return base.monochromatic(satOffset, valOffset);
    } else {
        return randomColor();
    }
}

// String conversion
std::string colorToHex(const Color& color) {
    // Convert to sRGB for hex representation
    glm::vec3 srgb = linearToSrgb(glm::vec3(color.rgba.r, color.rgba.g, color.rgba.b));
    
    std::stringstream ss;
    ss << "#";
    ss << std::hex << std::setfill('0') << std::setw(2) 
       << static_cast<int>(srgb.r * 255.0f);
    ss << std::hex << std::setfill('0') << std::setw(2) 
       << static_cast<int>(srgb.g * 255.0f);
    ss << std::hex << std::setfill('0') << std::setw(2) 
       << static_cast<int>(srgb.b * 255.0f);
    
    return ss.str();
}

Color hexToColor(const std::string& hex) {
    if (hex.empty() || hex[0] != '#') {
        return Color();
    }
    
    std::string hexStr = hex.substr(1);
    if (hexStr.length() != 6) {
        return Color();
    }
    
    unsigned int rgb;
    std::stringstream ss(hexStr);
    ss >> std::hex >> rgb;
    
    float r = ((rgb >> 16) & 0xFF) / 255.0f;
    float g = ((rgb >> 8) & 0xFF) / 255.0f;
    float b = (rgb & 0xFF) / 255.0f;
    
    // Convert sRGB to linear
    glm::vec3 linear = srgbToLinear(glm::vec3(r, g, b));
    
    return Color(linear.r, linear.g, linear.b);
}

std::string colorToRgbString(const Color& color) {
    std::stringstream ss;
    ss << "RGB(" 
       << static_cast<int>(color.rgba.r * 255.0f) << ", "
       << static_cast<int>(color.rgba.g * 255.0f) << ", "
       << static_cast<int>(color.rgba.b * 255.0f) << ")";
    return ss.str();
}

std::string colorToHsvString(const Color& color) {
    std::stringstream ss;
    ss << "HSV(" 
       << static_cast<int>(color.hsv.x) << "°, "
       << static_cast<int>(color.hsv.y * 100.0f) << "%, "
       << static_cast<int>(color.hsv.z * 100.0f) << "%)";
    return ss.str();
}

} // namespace ColorUtils

// Predefined color themes
namespace ColorThemes {

ColorTheme createFireTheme() {
    ColorTheme theme("Fire");
    theme.description = "Intense fire colors with orange and red hues";
    theme.setColor("colorPrimary", Color(0.8f, 0.2f, 0.1f));
    theme.setColor("colorSecondary", Color(1.0f, 0.6f, 0.2f));
    theme.setColor("colorAccent", Color(1.0f, 0.8f, 0.4f));
    theme.setColor("glowColor", Color(1.0f, 0.4f, 0.2f));
    theme.setColor("muzzleFlashColor", Color(1.0f, 0.8f, 0.4f));
    theme.setColor("muzzleSmokeColor", Color(0.3f, 0.1f, 0.05f));
    return theme;
}

ColorTheme createInfernoTheme() {
    ColorTheme theme("Inferno");
    theme.description = "Dark fire theme with deep reds and blacks";
    theme.setColor("colorPrimary", Color(0.6f, 0.1f, 0.05f));
    theme.setColor("colorSecondary", Color(0.8f, 0.3f, 0.1f));
    theme.setColor("colorAccent", Color(1.0f, 0.5f, 0.2f));
    theme.setColor("glowColor", Color(1.0f, 0.3f, 0.1f));
    theme.setColor("muzzleFlashColor", Color(1.0f, 0.6f, 0.3f));
    theme.setColor("muzzleSmokeColor", Color(0.2f, 0.05f, 0.02f));
    return theme;
}

ColorTheme createEmberTheme() {
    ColorTheme theme("Ember");
    theme.description = "Soft ember colors with warm oranges";
    theme.setColor("colorPrimary", Color(0.7f, 0.3f, 0.1f));
    theme.setColor("colorSecondary", Color(0.9f, 0.5f, 0.2f));
    theme.setColor("colorAccent", Color(1.0f, 0.7f, 0.4f));
    theme.setColor("glowColor", Color(1.0f, 0.6f, 0.3f));
    theme.setColor("muzzleFlashColor", Color(1.0f, 0.7f, 0.4f));
    theme.setColor("muzzleSmokeColor", Color(0.4f, 0.2f, 0.1f));
    return theme;
}

ColorTheme createIceTheme() {
    ColorTheme theme("Ice");
    theme.description = "Cool ice colors with blue and cyan hues";
    theme.setColor("colorPrimary", Color(0.2f, 0.6f, 1.0f));
    theme.setColor("colorSecondary", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("colorAccent", Color(0.4f, 0.8f, 1.0f));
    theme.setColor("glowColor", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("muzzleFlashColor", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("muzzleSmokeColor", Color(0.4f, 0.6f, 0.8f));
    return theme;
}

ColorTheme createFrostTheme() {
    ColorTheme theme("Frost");
    theme.description = "Pale frost colors with light blues";
    theme.setColor("colorPrimary", Color(0.4f, 0.7f, 1.0f));
    theme.setColor("colorSecondary", Color(0.8f, 0.9f, 1.0f));
    theme.setColor("colorAccent", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("glowColor", Color(0.7f, 0.9f, 1.0f));
    theme.setColor("muzzleFlashColor", Color(0.7f, 0.9f, 1.0f));
    theme.setColor("muzzleSmokeColor", Color(0.5f, 0.7f, 0.9f));
    return theme;
}

ColorTheme createCrystalTheme() {
    ColorTheme theme("Crystal");
    theme.description = "Transparent crystal colors with refraction";
    theme.setColor("colorPrimary", Color(0.3f, 0.7f, 1.0f));
    theme.setColor("colorSecondary", Color(0.7f, 0.9f, 1.0f));
    theme.setColor("colorAccent", Color(0.5f, 0.8f, 1.0f));
    theme.setColor("glowColor", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("muzzleFlashColor", Color(0.6f, 0.8f, 1.0f));
    theme.setColor("muzzleSmokeColor", Color(0.4f, 0.6f, 0.8f));
    return theme;
}

ColorTheme createArcaneTheme() {
    ColorTheme theme("Arcane");
    theme.description = "Mystical arcane colors with purple and blue";
    theme.setColor("colorPrimary", Color(0.4f, 0.2f, 0.8f));
    theme.setColor("colorSecondary", Color(0.6f, 0.4f, 1.0f));
    theme.setColor("colorAccent", Color(0.8f, 0.6f, 1.0f));
    theme.setColor("glowColor", Color(0.6f, 0.4f, 1.0f));
    theme.setColor("muzzleFlashColor", Color(0.7f, 0.5f, 1.0f));
    theme.setColor("muzzleSmokeColor", Color(0.3f, 0.2f, 0.5f));
    return theme;
}

ColorTheme createMysticTheme() {
    ColorTheme theme("Mystic");
    theme.description = "Deep mystic colors with dark purples";
    theme.setColor("colorPrimary", Color(0.3f, 0.1f, 0.6f));
    theme.setColor("colorSecondary", Color(0.5f, 0.3f, 0.8f));
    theme.setColor("colorAccent", Color(0.7f, 0.5f, 1.0f));
    theme.setColor("glowColor", Color(0.5f, 0.3f, 0.8f));
    theme.setColor("muzzleFlashColor", Color(0.6f, 0.4f, 0.9f));
    theme.setColor("muzzleSmokeColor", Color(0.2f, 0.1f, 0.4f));
    return theme;
}

ColorTheme createEtherealTheme() {
    ColorTheme theme("Ethereal");
    theme.description = "Light ethereal colors with soft purples";
    theme.setColor("colorPrimary", Color(0.6f, 0.4f, 0.8f));
    theme.setColor("colorSecondary", Color(0.8f, 0.6f, 1.0f));
    theme.setColor("colorAccent", Color(0.9f, 0.7f, 1.0f));
    theme.setColor("glowColor", Color(0.8f, 0.6f, 1.0f));
    theme.setColor("muzzleFlashColor", Color(0.8f, 0.6f, 1.0f));
    theme.setColor("muzzleSmokeColor", Color(0.4f, 0.3f, 0.6f));
    return theme;
}

ColorTheme createNatureTheme() {
    ColorTheme theme("Nature");
    theme.description = "Natural earth colors with greens and browns";
    theme.setColor("colorPrimary", Color(0.2f, 0.6f, 0.3f));
    theme.setColor("colorSecondary", Color(0.4f, 0.7f, 0.4f));
    theme.setColor("colorAccent", Color(0.6f, 0.8f, 0.5f));
    theme.setColor("glowColor", Color(0.4f, 0.7f, 0.4f));
    theme.setColor("muzzleFlashColor", Color(0.5f, 0.8f, 0.5f));
    theme.setColor("muzzleSmokeColor", Color(0.2f, 0.4f, 0.2f));
    return theme;
}

ColorTheme createOrganicTheme() {
    ColorTheme theme("Organic");
    theme.description = "Organic living colors with vibrant greens";
    theme.setColor("colorPrimary", Color(0.3f, 0.7f, 0.4f));
    theme.setColor("colorSecondary", Color(0.5f, 0.8f, 0.5f));
    theme.setColor("colorAccent", Color(0.7f, 0.9f, 0.6f));
    theme.setColor("glowColor", Color(0.5f, 0.8f, 0.5f));
    theme.setColor("muzzleFlashColor", Color(0.6f, 0.9f, 0.6f));
    theme.setColor("muzzleSmokeColor", Color(0.3f, 0.5f, 0.3f));
    return theme;
}

ColorTheme createVerdantTheme() {
    ColorTheme theme("Verdant");
    theme.description = "Deep verdant colors with rich greens";
    theme.setColor("colorPrimary", Color(0.1f, 0.5f, 0.2f));
    theme.setColor("colorSecondary", Color(0.3f, 0.6f, 0.3f));
    theme.setColor("colorAccent", Color(0.5f, 0.7f, 0.4f));
    theme.setColor("glowColor", Color(0.3f, 0.6f, 0.3f));
    theme.setColor("muzzleFlashColor", Color(0.4f, 0.7f, 0.4f));
    theme.setColor("muzzleSmokeColor", Color(0.1f, 0.3f, 0.1f));
    return theme;
}

ColorTheme createSteelTheme() {
    ColorTheme theme("Steel");
    theme.description = "Industrial steel colors with metallic grays";
    theme.setColor("colorPrimary", Color(0.6f, 0.6f, 0.6f));
    theme.setColor("colorSecondary", Color(0.8f, 0.8f, 0.8f));
    theme.setColor("colorAccent", Color(0.4f, 0.4f, 0.4f));
    theme.setColor("glowColor", Color(0.7f, 0.7f, 0.7f));
    theme.setColor("muzzleFlashColor", Color(0.8f, 0.8f, 0.8f));
    theme.setColor("muzzleSmokeColor", Color(0.3f, 0.3f, 0.3f));
    return theme;
}

ColorTheme createBronzeTheme() {
    ColorTheme theme("Bronze");
    theme.description = "Warm bronze colors with golden browns";
    theme.setColor("colorPrimary", Color(0.8f, 0.5f, 0.2f));
    theme.setColor("colorSecondary", Color(0.9f, 0.6f, 0.3f));
    theme.setColor("colorAccent", Color(0.7f, 0.4f, 0.1f));
    theme.setColor("glowColor", Color(0.9f, 0.6f, 0.3f));
    theme.setColor("muzzleFlashColor", Color(1.0f, 0.7f, 0.4f));
    theme.setColor("muzzleSmokeColor", Color(0.4f, 0.3f, 0.1f));
    return theme;
}

ColorTheme createGoldTheme() {
    ColorTheme theme("Gold");
    theme.description = "Precious gold colors with bright yellows";
    theme.setColor("colorPrimary", Color(1.0f, 0.8f, 0.2f));
    theme.setColor("colorSecondary", Color(1.0f, 0.9f, 0.4f));
    theme.setColor("colorAccent", Color(0.8f, 0.6f, 0.1f));
    theme.setColor("glowColor", Color(1.0f, 0.9f, 0.4f));
    theme.setColor("muzzleFlashColor", Color(1.0f, 0.9f, 0.5f));
    theme.setColor("muzzleSmokeColor", Color(0.5f, 0.4f, 0.1f));
    return theme;
}

ColorTheme createVoidTheme() {
    ColorTheme theme("Void");
    theme.description = "Dark void colors with deep blacks";
    theme.setColor("colorPrimary", Color(0.1f, 0.1f, 0.2f));
    theme.setColor("colorSecondary", Color(0.2f, 0.2f, 0.3f));
    theme.setColor("colorAccent", Color(0.3f, 0.3f, 0.4f));
    theme.setColor("glowColor", Color(0.2f, 0.2f, 0.3f));
    theme.setColor("muzzleFlashColor", Color(0.3f, 0.3f, 0.4f));
    theme.setColor("muzzleSmokeColor", Color(0.05f, 0.05f, 0.1f));
    return theme;
}

ColorTheme createShadowTheme() {
    ColorTheme theme("Shadow");
    theme.description = "Mysterious shadow colors with dark purples";
    theme.setColor("colorPrimary", Color(0.2f, 0.1f, 0.3f));
    theme.setColor("colorSecondary", Color(0.3f, 0.2f, 0.4f));
    theme.setColor("colorAccent", Color(0.4f, 0.3f, 0.5f));
    theme.setColor("glowColor", Color(0.3f, 0.2f, 0.4f));
    theme.setColor("muzzleFlashColor", Color(0.4f, 0.3f, 0.5f));
    theme.setColor("muzzleSmokeColor", Color(0.1f, 0.05f, 0.2f));
    return theme;
}

ColorTheme createAbyssTheme() {
    ColorTheme theme("Abyss");
    theme.description = "Deep abyss colors with black and blue";
    theme.setColor("colorPrimary", Color(0.05f, 0.05f, 0.1f));
    theme.setColor("colorSecondary", Color(0.1f, 0.1f, 0.2f));
    theme.setColor("colorAccent", Color(0.2f, 0.2f, 0.3f));
    theme.setColor("glowColor", Color(0.1f, 0.1f, 0.2f));
    theme.setColor("muzzleFlashColor", Color(0.2f, 0.2f, 0.3f));
    theme.setColor("muzzleSmokeColor", Color(0.02f, 0.02f, 0.05f));
    return theme;
}

} // namespace ColorThemes

// Accessibility features
namespace Accessibility {

ColorPalette createColorBlindFriendlyPalette() {
    ColorPalette palette("Color Blind Friendly");
    palette.description = "Colors optimized for color vision deficiency";
    palette.tags = {"accessibility", "colorblind", "deuteranopia", "protanopia", "tritanopia"};
    
    // Colors that work well for all types of color blindness
    palette.addColor(Color(0.0f, 0.0f, 0.0f));      // Black
    palette.addColor(Color(1.0f, 1.0f, 1.0f));      // White
    palette.addColor(Color(0.8f, 0.4f, 0.0f));      // Orange
    palette.addColor(Color(0.0f, 0.6f, 0.8f));      // Blue
    palette.addColor(Color(0.8f, 0.0f, 0.0f));      // Red
    palette.addColor(Color(0.0f, 0.8f, 0.0f));      // Green
    palette.addColor(Color(0.8f, 0.8f, 0.0f));      // Yellow
    palette.addColor(Color(0.8f, 0.0f, 0.8f));      // Magenta
    
    return palette;
}

ColorPalette createHighContrastPalette() {
    ColorPalette palette("High Contrast");
    palette.description = "High contrast colors for accessibility";
    palette.tags = {"accessibility", "high-contrast", "wcag"};
    
    palette.addColor(Color(0.0f, 0.0f, 0.0f));      // Black
    palette.addColor(Color(1.0f, 1.0f, 1.0f));      // White
    palette.addColor(Color(1.0f, 0.0f, 0.0f));      // Red
    palette.addColor(Color(0.0f, 1.0f, 0.0f));      // Green
    palette.addColor(Color(0.0f, 0.0f, 1.0f));      // Blue
    palette.addColor(Color(1.0f, 1.0f, 0.0f));      // Yellow
    palette.addColor(Color(1.0f, 0.0f, 1.0f));      // Magenta
    palette.addColor(Color(0.0f, 1.0f, 1.0f));      // Cyan
    
    return palette;
}

bool isColorBlindFriendly(const Color& a, const Color& b) {
    // Check if colors are distinguishable for color blind users
    float contrast = getContrastRatio(a, b);
    return contrast >= 3.0f; // Lower threshold for color blind users
}

bool hasSufficientContrast(const Color& foreground, const Color& background) {
    float ratio = getContrastRatio(foreground, background);
    return ratio >= 4.5f; // WCAG AA standard
}

Color adjustForColorBlindness(const Color& color, const std::string& type) {
    // Adjust colors for specific types of color blindness
    if (type == "deuteranopia") {
        // Red-green color blindness (most common)
        // Increase blue component to make colors more distinguishable
        return Color(color.rgba.r * 0.8f, color.rgba.g * 0.8f, 
                   std::min(color.rgba.b * 1.2f, 1.0f), color.rgba.a);
    } else if (type == "protanopia") {
        // Red color blindness
        // Increase green and blue components
        return Color(color.rgba.r * 0.7f, std::min(color.rgba.g * 1.1f, 1.0f), 
                   std::min(color.rgba.b * 1.1f, 1.0f), color.rgba.a);
    } else if (type == "tritanopia") {
        // Blue-yellow color blindness
        // Increase red component
        return Color(std::min(color.rgba.r * 1.1f, 1.0f), color.rgba.g * 0.9f, 
                   color.rgba.b * 0.9f, color.rgba.a);
    }
    
    return color;
}

Color ensureContrast(const Color& foreground, const Color& background, float minRatio) {
    float currentRatio = getContrastRatio(foreground, background);
    
    if (currentRatio >= minRatio) {
        return foreground;
    }
    
    // Adjust foreground color to improve contrast
    float targetRatio = minRatio;
    float adjustment = (targetRatio - currentRatio) / targetRatio;
    
    // Increase luminance difference
    float newLuminance = getLuminance(foreground) + adjustment * 0.5f;
    newLuminance = std::clamp(newLuminance, 0.0f, 1.0f);
    
    // Convert back to RGB
    glm::vec3 linear = glm::vec3(newLuminance, newLuminance, newLuminance);
    glm::vec3 srgb = linearToSrgb(linear);
    
    return Color(srgb.r, srgb.g, srgb.b, foreground.rgba.a);
}

} // namespace Accessibility

} // namespace ColorPicker
} // namespace MagiTech 
