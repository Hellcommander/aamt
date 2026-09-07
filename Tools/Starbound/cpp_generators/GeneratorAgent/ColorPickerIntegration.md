# Color Picker Integration for Alchemical Launcher Generator

## Overview

The Color Picker Integration system provides comprehensive color control for the Alchemical Launcher Generator, enabling designers to create visually stunning and thematically consistent launchers through intuitive color management tools.

## Core Features

### 1. Advanced Color Picker UI
- **HSV Color Wheel**: Intuitive hue selection with saturation/value controls
- **RGB Sliders**: Precise RGB value adjustment
- **Hex Input**: Web-standard hex color codes (#RRGGBB)
- **Alpha Channel**: Transparency control for advanced effects
- **Real-time Preview**: Instant color visualization

### 2. Color Harmonies
- **Complementary**: Opposite colors on the color wheel
- **Analogous**: Adjacent colors for harmonious schemes
- **Triadic**: Three colors equally spaced around the wheel
- **Split Complementary**: Base color plus two colors adjacent to its complement
- **Tetradic**: Four colors forming a rectangle on the wheel
- **Monochromatic**: Variations of a single hue

### 3. Predefined Color Themes
- **Fire Themes**: Intense reds, oranges, and yellows
- **Ice Themes**: Cool blues and cyans
- **Arcane Themes**: Mystical purples and magentas
- **Nature Themes**: Organic greens and earth tones
- **Metal Themes**: Industrial grays and metallic colors
- **Void Themes**: Dark purples and deep blacks

### 4. Palette Management
- **Custom Palettes**: User-defined color collections
- **Theme Palettes**: Pre-built thematic color sets
- **Accessibility Palettes**: Color-blind friendly options
- **High Contrast Palettes**: WCAG AA compliant combinations

### 5. Accessibility Features
- **Color Blind Support**: Deuteranopia, protanopia, tritanopia adjustments
- **WCAG Compliance**: Automatic contrast ratio checking
- **High Contrast Modes**: Enhanced visibility options
- **Accessibility Testing**: Built-in compliance validation

## Integration Points

### C++ Integration

```cpp
// Color picker system instance
auto& colorPicker = ColorPicker::ColorPickerSystem::instance();

// Draw color picker UI
Color color(0.8f, 0.2f, 0.1f, 1.0f);
bool changed = colorPicker.drawColorPicker("Primary Color", color);

// Apply theme to launcher parameters
ColorTheme fireTheme = ColorThemes::createFireTheme();
if (fireTheme.hasColor("colorPrimary")) {
    Color primaryColor = fireTheme.getColor("colorPrimary");
    launcherParams.colorPrimary = {primaryColor.rgba.r, primaryColor.rgba.g, primaryColor.rgba.b};
}
```

### Lua Integration

```lua
-- Get color picker system
local colorPicker = ColorPickerSystem.instance()

-- Create colors
local primaryColor = Color(0.8, 0.2, 0.1, 1.0)
local complementary = primaryColor:complementary()

-- Apply theme
local fireTheme = createFireTheme()
local params = createDefaultLauncherParams()
if fireTheme:hasColor("colorPrimary") then
    local color = fireTheme:getColor("colorPrimary")
    params.colorPrimary = {color.rgba.r, color.rgba.g, color.rgba.b}
end

-- Generate launcher with theme
local bundle = spawn_launcher(params, uiParams)
```

## Color Space Management

### RGB/HSV Conversion
- **Linear RGB**: Internal storage for accurate calculations
- **sRGB**: Display and web compatibility
- **HSV**: Intuitive color manipulation
- **Hex**: Web-standard color representation

### Color Space Conversions
```cpp
// RGB to HSV
glm::vec3 hsv = ColorUtils::rgbToHsv(rgb);

// HSV to RGB
glm::vec3 rgb = ColorUtils::hsvToRgb(hsv);

// Linear to sRGB
glm::vec3 srgb = ColorUtils::linearToSrgb(linear);

// sRGB to Linear
glm::vec3 linear = ColorUtils::srgbToLinear(srgb);
```

## Theme System

### Creating Custom Themes
```cpp
ColorTheme customTheme("Custom Theme");
customTheme.description = "A custom color theme for special launchers";
customTheme.setColor("colorPrimary", Color(0.8f, 0.2f, 0.1f));
customTheme.setColor("colorSecondary", Color(0.2f, 0.6f, 1.0f));
customTheme.setColor("glowColor", Color(1.0f, 0.8f, 0.4f));
```

### Theme Application
```cpp
// Apply theme to launcher parameters
void applyThemeToLauncher(const ColorTheme& theme, AlchemicalLauncherParams& params) {
    if (theme.hasColor("colorPrimary")) {
        Color color = theme.getColor("colorPrimary");
        params.colorPrimary = {color.rgba.r, color.rgba.g, color.rgba.b};
    }
    if (theme.hasColor("colorSecondary")) {
        Color color = theme.getColor("colorSecondary");
        params.colorSecondary = {color.rgba.r, color.rgba.g, color.rgba.b};
    }
    // ... apply other colors
}
```

## Accessibility Features

### Color Blind Support
```cpp
// Check if colors are color-blind friendly
bool isFriendly = Accessibility::isColorBlindFriendly(color1, color2);

// Adjust colors for specific color blindness types
Color adjusted = Accessibility::adjustForColorBlindness(color, "deuteranopia");
```

### WCAG Compliance
```cpp
// Check contrast ratio
float ratio = ColorUtils::getContrastRatio(foreground, background);

// Ensure minimum contrast
Color ensured = Accessibility::ensureContrast(foreground, background, 4.5f);
```

## Performance Optimization

### Caching System
- **Color Cache**: Frequently used colors cached for instant access
- **Theme Cache**: Pre-built themes stored for quick application
- **Harmony Cache**: Generated harmonies cached to avoid recalculation

### Performance Metrics
```cpp
// Measure color generation performance
auto start = std::chrono::high_resolution_clock::now();
Color color = ColorUtils::randomColor(0.8f, 0.9f);
auto end = std::chrono::high_resolution_clock::now();
auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
```

## File I/O

### Palette Persistence
```cpp
// Save palettes to file
colorPicker.savePalettes("palettes.json");

// Load palettes from file
colorPicker.loadPalettes("palettes.json");
```

### Theme Persistence
```cpp
// Save themes to file
colorPicker.saveThemes("themes.json");

// Load themes from file
colorPicker.loadThemes("themes.json");
```

## UI Integration

### ImGui Integration
```cpp
// Draw color picker in ImGui
bool ColorPickerSystem::drawColorPicker(const char* label, Color& color) {
    ImVec4 imColor(color.rgba.r, color.rgba.g, color.rgba.b, color.rgba.a);
    return ImGui::ColorPicker4(label, &imColor.x, 
                               ImGuiColorEditFlags_DisplayHSV |
                               ImGuiColorEditFlags_PickerHueWheel);
}
```

### Real-time Preview
```cpp
// Update launcher preview when color changes
if (colorPicker.drawColorPicker("Launcher Color", launcherColor)) {
    // Trigger asset regeneration
    regenerateLauncherAssets(launcherParams);
}
```

## Advanced Features

### Random Color Generation
```cpp
// Generate random colors with constraints
Color randomColor = ColorUtils::randomColor(0.8f, 0.9f);

// Generate random harmonies
Color harmony = ColorUtils::randomHarmony(baseColor, "complementary");
```

### Color Interpolation
```cpp
// Lerp between colors
Color interpolated = ColorPickerSystem::lerp(color1, color2, 0.5f);
```

### Color Analysis
```cpp
// Get color luminance
float luminance = ColorUtils::getLuminance(color);

// Check accessibility
bool accessible = ColorUtils::isAccessible(foreground, background);
```

## Usage Examples

### Basic Color Picker
```lua
-- Create a color picker for launcher primary color
local primaryColor = Color(0.8, 0.2, 0.1, 1.0)
if openColorPicker("Primary Color", primaryColor) then
    params.colorPrimary = {primaryColor.rgba.r, primaryColor.rgba.g, primaryColor.rgba.b}
    -- Regenerate launcher with new color
    local bundle = spawn_launcher(params, uiParams)
end
```

### Theme Application
```lua
-- Apply fire theme to launcher
local fireTheme = createFireTheme()
local params = createDefaultLauncherParams()

-- Apply all theme colors
if fireTheme:hasColor("colorPrimary") then
    local color = fireTheme:getColor("colorPrimary")
    params.colorPrimary = {color.rgba.r, color.rgba.g, color.rgba.b}
end

local bundle = spawn_launcher(params, uiParams)
```

### Custom Palette Creation
```lua
-- Create custom palette
local palette = ColorPalette("My Custom Palette")
palette:addColor(Color(0.8, 0.2, 0.1, 1.0))  -- Fire red
palette:addColor(Color(0.2, 0.6, 1.0, 1.0))  -- Ice blue
palette:addColor(Color(0.4, 0.2, 0.8, 1.0))  -- Arcane purple

-- Add to system
ColorPickerSystem.instance():addPalette(palette)
```

### Accessibility Testing
```lua
-- Test color accessibility
local foreground = Color(0.2, 0.2, 0.2, 1.0)
local background = Color(1.0, 1.0, 1.0, 1.0)

local contrastRatio = ColorPickerSystem.instance():getContrastRatio(foreground, background)
local isAccessible = hasSufficientContrast(foreground, background)

print("Contrast ratio: " .. contrastRatio)
print("WCAG AA compliant: " .. tostring(isAccessible))
```

## Best Practices

### Color Selection
1. **Use Color Harmonies**: Leverage complementary, analogous, and triadic relationships
2. **Consider Accessibility**: Ensure sufficient contrast ratios for all users
3. **Test Color Blindness**: Verify colors work for users with color vision deficiency
4. **Maintain Consistency**: Use consistent color schemes across related assets

### Performance
1. **Cache Frequently Used Colors**: Store commonly used colors for instant access
2. **Batch Color Operations**: Group color changes to minimize regeneration
3. **Use Efficient Color Spaces**: Choose appropriate color spaces for operations
4. **Profile Color Operations**: Monitor performance of color-intensive operations

### Accessibility
1. **WCAG AA Compliance**: Maintain 4.5:1 contrast ratio for normal text
2. **Color Blind Friendly**: Ensure colors are distinguishable for all users
3. **High Contrast Options**: Provide alternative high-contrast color schemes
4. **Testing**: Regularly test color combinations with accessibility tools

## Future Enhancements

### Planned Features
1. **Advanced Color Spaces**: Support for LAB, CMYK, and other color spaces
2. **Color Gradients**: Smooth color transitions and gradients
3. **Color Animation**: Animated color transitions and effects
4. **Machine Learning**: AI-powered color scheme generation
5. **Color Psychology**: Color schemes based on psychological principles

### Integration Extensions
1. **Material System**: Advanced material-based color management
2. **Lighting Integration**: Dynamic color adjustment based on lighting
3. **Weather Effects**: Color adaptation for different weather conditions
4. **Time of Day**: Automatic color adjustment based on time

## Troubleshooting

### Common Issues
1. **Color Mismatch**: Ensure proper color space conversion
2. **Performance Issues**: Check color caching and batch operations
3. **Accessibility Problems**: Verify contrast ratios and color blindness compatibility
4. **Theme Application**: Confirm theme colors are properly mapped to parameters

### Debug Tools
```cpp
// Debug color values
std::cout << "RGB: " << color.rgba.r << ", " << color.rgba.g << ", " << color.rgba.b << std::endl;
std::cout << "HSV: " << color.hsv.x << ", " << color.hsv.y << ", " << color.hsv.z << std::endl;
std::cout << "Hex: " << color.toHex() << std::endl;
```

This comprehensive color picker integration system provides designers with powerful, intuitive tools for creating visually stunning and thematically consistent alchemical launchers while maintaining accessibility and performance standards. 