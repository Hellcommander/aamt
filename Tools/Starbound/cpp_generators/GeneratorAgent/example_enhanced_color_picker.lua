--[[
    Enhanced Color Picker System - Advanced Features Demo
    
    This script demonstrates the comprehensive enhanced color picker system with:
    
    1. AI-powered color generation and suggestions
    2. Color psychology analysis and mood-based generation
    3. Advanced color spaces (RGB, HSV, LAB, XYZ)
    4. Color gradients and blending
    5. Enhanced accessibility features
    6. Performance optimizations and caching
    7. Seasonal and mood-based theme generation
    8. Advanced color harmonies and psychology
]]

print("=== Enhanced Color Picker System Demo ===")

-- Get the enhanced color picker system instance
local colorPicker = ColorPickerSystem.instance()

-- Example 1: AI-Powered Color Generation
print("\n--- Example 1: AI-Powered Color Generation ---")

-- Get AI instance
local colorAI = ColorAI.instance()

-- Generate colors from mood descriptions
local moods = {"energetic", "calming", "mystical", "natural", "passionate", "serene"}
for _, mood in ipairs(moods) do
    local aiColor = colorAI:generateColorFromMood(mood)
    local moodAnalysis = colorAI:analyzeMood(aiColor)
    print(string.format("Mood: %-12s | Color: %s | Analysis: %s", 
                       mood, aiColor:toHex(), moodAnalysis))
end

-- Generate colors from descriptions
local descriptions = {"fiery red", "deep blue", "forest green", "golden yellow", "royal purple"}
for _, desc in ipairs(descriptions) do
    local descColor = colorAI:generateColorFromDescription(desc)
    print(string.format("Description: %-15s | Color: %s", desc, descColor:toHex()))
end

-- Example 2: Advanced Color Psychology
print("\n--- Example 2: Advanced Color Psychology ---")

-- Create colors and analyze their psychology
local psychologyColors = {
    {color = Color(1.0, 0.0, 0.0, 1.0), name = "Pure Red"},
    {color = Color(0.0, 0.0, 1.0, 1.0), name = "Pure Blue"},
    {color = Color(0.0, 1.0, 0.0, 1.0), name = "Pure Green"},
    {color = Color(1.0, 1.0, 0.0, 1.0), name = "Yellow"},
    {color = Color(1.0, 0.0, 1.0, 1.0), name = "Magenta"}
}

for _, colorInfo in ipairs(psychologyColors) do
    local color = colorInfo.color
    print(string.format("%-15s | Energy: %.2f | Warmth: %.2f | Intensity: %.2f | Mood: %s",
                       colorInfo.name, color.energy, color.warmth, color.intensity,
                       colorAI:analyzeMood(color)))
end

-- Example 3: Advanced Color Spaces
print("\n--- Example 3: Advanced Color Spaces ---")

-- Demonstrate different color space representations
local testColor = Color(0.8, 0.2, 0.6, 1.0)
print("Original Color: " .. testColor:toHex())
print("RGB: " .. colorToRgbString(testColor))
print("HSV: " .. colorToHsvString(testColor))
print("LAB: " .. colorToLABString(testColor))
print("Temperature: " .. colorToTemperatureString(testColor))

-- Create colors from different spaces
local labColor = Color.fromLAB(50.0, 20.0, -30.0, 1.0)
print("LAB Color: " .. labColor:toHex())

local tempColor = Color.fromTemperature(6500.0, 1.0)  -- Daylight
print("Temperature Color (6500K): " .. tempColor:toHex())

-- Example 4: Enhanced Color Harmonies
print("\n--- Example 4: Enhanced Color Harmonies ---")

local baseColor = Color(0.6, 0.3, 0.8, 1.0)  -- Purple
print("Base Color: " .. baseColor:toHex())

-- Generate all harmony types
local harmonies = {
    {name = "Complementary", func = function(c) return c:complementary() end},
    {name = "Analogous", func = function(c) return c:analogous(30.0) end},
    {name = "Triadic", func = function(c) return c:triadic() end},
    {name = "Split Complementary", func = function(c) return c:splitComplementary() end},
    {name = "Tetradic", func = function(c) return c:tetradic() end},
    {name = "Square", func = function(c) return c:square() end},
    {name = "Rectangle", func = function(c) return c:rectangle() end},
    {name = "Pentadic", func = function(c) return c:pentadic() end},
    {name = "Monochromatic", func = function(c) return c:monochromatic(0.2, 0.2) end}
}

for _, harmony in ipairs(harmonies) do
    local harmonyColor = harmony.func(baseColor)
    print(string.format("  %-20s: %s", harmony.name, harmonyColor:toHex()))
end

-- Example 5: Color Psychology Harmonies
print("\n--- Example 5: Color Psychology Harmonies ---")

local neutralColor = Color(0.5, 0.5, 0.5, 1.0)
print("Neutral Color: " .. neutralColor:toHex())

local psychologyHarmonies = {
    {name = "Energetic", func = function(c) return c:energetic() end},
    {name = "Calming", func = function(c) return c:calming() end},
    {name = "Warm", func = function(c) return c:warm() end},
    {name = "Cool", func = function(c) return c:cool() end},
    {name = "Intense", func = function(c) return c:intense() end},
    {name = "Soft", func = function(c) return c:soft() end}
}

for _, harmony in ipairs(psychologyHarmonies) do
    local harmonyColor = harmony.func(neutralColor)
    print(string.format("  %-12s: %s | Energy: %.2f | Warmth: %.2f | Intensity: %.2f",
                       harmony.name, harmonyColor:toHex(), 
                       harmonyColor.energy, harmonyColor.warmth, harmonyColor.intensity))
end

-- Example 6: Color Gradients
print("\n--- Example 6: Color Gradients ---")

-- Create a gradient
local gradient = ColorGradient("Sunset Gradient")
gradient:addStop(0.0, Color(1.0, 0.4, 0.2, 1.0))  -- Orange
gradient:addStop(0.5, Color(1.0, 0.2, 0.6, 1.0))  -- Pink
gradient:addStop(1.0, Color(0.4, 0.2, 0.8, 1.0))  -- Purple

print("Gradient: " .. gradient.name)
for i = 0, 10 do
    local t = i / 10.0
    local sampledColor = gradient:sample(t)
    print(string.format("  %.1f: %s", t, sampledColor:toHex()))
end

-- Create gradient blend
local gradient2 = ColorGradient("Ocean Gradient")
gradient2:addStop(0.0, Color(0.2, 0.6, 1.0, 1.0))  -- Light blue
gradient2:addStop(1.0, Color(0.0, 0.2, 0.6, 1.0))  -- Dark blue

local blendedGradient = gradient:blend(gradient2, 0.5)
print("Blended Gradient:")
for i = 0, 5 do
    local t = i / 5.0
    local sampledColor = blendedGradient:sample(t)
    print(string.format("  %.1f: %s", t, sampledColor:toHex()))
end

-- Example 7: Enhanced Palettes with Psychology
print("\n--- Example 7: Enhanced Palettes with Psychology ---")

-- Create an enhanced palette
local enhancedPalette = ColorPalette("Enhanced Psychology Palette")
enhancedPalette.description = "A palette with psychological attributes"
enhancedPalette.tags = {"psychology", "enhanced", "mood-based"}
enhancedPalette.mood = "energetic"
enhancedPalette.season = "summer"

-- Add colors with psychology
enhancedPalette:addColor(Color(1.0, 0.2, 0.2, 1.0))  -- Energetic red
enhancedPalette:addColor(Color(1.0, 0.8, 0.2, 1.0))  -- Warm orange
enhancedPalette:addColor(Color(1.0, 1.0, 0.2, 1.0))  -- Bright yellow

print("Enhanced Palette: " .. enhancedPalette.name)
print("  Mood: " .. enhancedPalette.mood)
print("  Season: " .. enhancedPalette.season)
print("  Colors: " .. enhancedPalette:size())
print("  Average Saturation: " .. string.format("%.2f", enhancedPalette:getAverageSaturation()))
print("  Average Value: " .. string.format("%.2f", enhancedPalette:getAverageValue()))

-- Apply mood transformation
enhancedPalette:applyMood("calming")
print("After calming transformation:")
for i, color in ipairs(enhancedPalette.colors) do
    print(string.format("  Color %d: %s | Energy: %.2f", i, color:toHex(), color.energy))
end

-- Example 8: Enhanced Themes with AI
print("\n--- Example 8: Enhanced Themes with AI ---")

-- Create mood-based themes
local moods = {"energetic", "calming", "mystical", "natural"}
for _, mood in ipairs(moods) do
    local theme = ColorTheme("AI_" .. mood .. "_Theme")
    theme:generateFromMood(mood)
    
    print("Theme: " .. theme.name)
    print("  Mood: " .. theme.mood)
    print("  Intensity: " .. string.format("%.2f", theme.intensity))
    
    -- Apply seasonal adjustment
    theme:adjustForSeason("autumn")
    print("  After autumn adjustment:")
    for paramName, color in pairs(theme.colorMap) do
        print(string.format("    %s: %s", paramName, color:toHex()))
    end
end

-- Example 9: Advanced Accessibility Features
print("\n--- Example 9: Advanced Accessibility Features ---")

-- Test different accessibility scenarios
local testPairs = {
    {foreground = Color(0.2, 0.2, 0.2, 1.0), background = Color(1.0, 1.0, 1.0, 1.0), name = "Dark on White"},
    {foreground = Color(1.0, 1.0, 1.0, 1.0), background = Color(0.2, 0.2, 0.2, 1.0), name = "White on Dark"},
    {foreground = Color(0.8, 0.2, 0.2, 1.0), background = Color(0.2, 0.8, 0.2, 1.0), name = "Red on Green"}
}

for _, pair in ipairs(testPairs) do
    local contrastRatio = colorPicker:getContrastRatio(pair.foreground, pair.background)
    local isAccessible = colorPicker:isAccessible(pair.foreground, pair.background)
    local isColorBlindFriendly = isColorBlindFriendly(pair.foreground, pair.background)
    
    print(string.format("%-15s | Contrast: %.2f | WCAG AA: %s | Color Blind: %s",
                       pair.name, contrastRatio, tostring(isAccessible), tostring(isColorBlindFriendly)))
end

-- Example 10: Performance Optimization
print("\n--- Example 10: Performance Optimization ---")

-- Enable performance optimizations
colorPicker:enableAsyncProcessing(true)
colorPicker:setCacheSize(2000)

-- Test performance with batch operations
local startTime = os.clock()
for i = 1, 100 do
    local randomColor = createRandomColor(0.8, 0.9)
    local harmony = createRandomHarmony(randomColor, "complementary")
    local aiColor = colorAI:generateColorFromMood("energetic")
end
local endTime = os.clock()
print(string.format("Generated 100 colors with AI in %.3f seconds", endTime - startTime))

-- Test gradient performance
startTime = os.clock()
for i = 1, 50 do
    local gradient = randomGradient(5)
    for j = 0, 10 do
        local t = j / 10.0
        local sampledColor = gradient:sample(t)
    end
end
endTime = os.clock()
print(string.format("Generated 50 gradients with 11 samples each in %.3f seconds", endTime - startTime))

-- Example 11: Advanced Color Interpolation
print("\n--- Example 11: Advanced Color Interpolation ---")

local color1 = Color(1.0, 0.0, 0.0, 1.0)  -- Red
local color2 = Color(0.0, 0.0, 1.0, 1.0)  -- Blue

print("Interpolation between Red and Blue:")
for i = 0, 10 do
    local t = i / 10.0
    local lerpedColor = ColorPickerSystem.lerp(color1, color2, t)
    local lerpedLAB = ColorPickerSystem.lerpLAB(color1, color2, t)
    print(string.format("  %.1f: RGB=%s | LAB=%s", t, lerpedColor:toHex(), lerpedLAB:toHex()))
end

-- Example 12: AI Learning and Adaptation
print("\n--- Example 12: AI Learning and Adaptation ---")

-- Teach the AI some preferences
colorAI:learnFromUserPreference(Color(1.0, 0.8, 0.2, 1.0), true)   -- Like warm yellow
colorAI:learnFromUserPreference(Color(0.2, 0.2, 0.8, 1.0), true)   -- Like cool blue
colorAI:learnFromUserPreference(Color(0.8, 0.2, 0.2, 1.0), false)  -- Dislike bright red

-- Learn from context
colorAI:learnFromContext("fire_theme", Color(1.0, 0.4, 0.2, 1.0))
colorAI:learnFromContext("ice_theme", Color(0.4, 0.8, 1.0, 1.0))
colorAI:learnFromContext("nature_theme", Color(0.2, 0.8, 0.4, 1.0))

-- Generate colors using learned preferences
print("AI-generated colors based on learned preferences:")
for i = 1, 5 do
    local aiColor = colorAI:generateColorFromMood("energetic")
    local mood = colorAI:analyzeMood(aiColor)
    print(string.format("  Color %d: %s | Mood: %s", i, aiColor:toHex(), mood))
end

-- Example 13: Seasonal Color Adaptation
print("\n--- Example 13: Seasonal Color Adaptation ---")

local baseTheme = ColorTheme("Seasonal_Base")
baseTheme:setColor("colorPrimary", Color(0.6, 0.6, 0.6, 1.0))
baseTheme:setColor("colorSecondary", Color(0.4, 0.4, 0.4, 1.0))
baseTheme:setColor("colorAccent", Color(0.8, 0.8, 0.8, 1.0))

local seasons = {"spring", "summer", "autumn", "winter"}
for _, season in ipairs(seasons) do
    local seasonalTheme = ColorTheme("Seasonal_" .. season)
    seasonalTheme.colorMap = baseTheme.colorMap
    seasonalTheme:adjustForSeason(season)
    
    print("Season: " .. season)
    for paramName, color in pairs(seasonalTheme.colorMap) do
        print(string.format("  %s: %s", paramName, color:toHex()))
    end
end

-- Example 14: Advanced Color Analysis
print("\n--- Example 14: Advanced Color Analysis ---")

local analysisColors = {
    Color(1.0, 0.0, 0.0, 1.0),  -- Pure red
    Color(0.0, 1.0, 0.0, 1.0),  -- Pure green
    Color(0.0, 0.0, 1.0, 1.0),  -- Pure blue
    Color(1.0, 1.0, 1.0, 1.0),  -- White
    Color(0.0, 0.0, 0.0, 1.0)   -- Black
}

for i, color in ipairs(analysisColors) do
    local luminance = color:getLuminance()
    local perceivedBrightness = color:getPerceivedBrightness()
    local colorTemperature = color:getColorTemperature()
    
    print(string.format("Color %d (%s):", i, color:toHex()))
    print(string.format("  Luminance: %.3f", luminance))
    print(string.format("  Perceived Brightness: %.3f", perceivedBrightness))
    print(string.format("  Color Temperature: %.0f K", colorTemperature))
end

print("\n=== Enhanced Color Picker System Demo Complete ===")
print("Advanced features demonstrated:")
print("  ✓ AI-powered color generation and mood analysis")
print("  ✓ Advanced color spaces (RGB, HSV, LAB, XYZ)")
print("  ✓ Color psychology and emotional analysis")
print("  ✓ Enhanced color harmonies (square, rectangle, pentadic)")
print("  ✓ Color gradients with blending and interpolation")
print("  ✓ Seasonal and mood-based color adaptation")
print("  ✓ Advanced accessibility testing and optimization")
print("  ✓ Performance optimization with caching and async processing")
print("  ✓ AI learning and adaptation from user preferences")
print("  ✓ Advanced color analysis (luminance, brightness, temperature)")
print("  ✓ Enhanced palette and theme management")
print("  ✓ Real-time color psychology feedback") 