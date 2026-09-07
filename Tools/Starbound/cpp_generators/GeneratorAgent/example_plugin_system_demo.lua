--[[
    Enhanced Color Picker Plugin System Demo
    
    This script demonstrates the comprehensive plugin system that allows
    dynamic loading of color palette plugins from both C++ and Lua sources.
    
    Features demonstrated:
    1. Plugin discovery and loading
    2. Plugin management and hot-reloading
    3. Palette generation from plugins
    4. Plugin capabilities and validation
    5. Plugin configuration and settings
    6. Cross-platform plugin support
]]

print("=== Enhanced Color Picker Plugin System Demo ===")

-- Get the color picker system and plugin manager instances
local colorPicker = ColorPickerSystem.instance()
local pluginManager = colorPicker:getPluginManager()

-- Example 1: Plugin Discovery and Loading
print("\n--- Example 1: Plugin Discovery and Loading ---")

-- Scan for plugins in the plugins directory
local pluginDirectory = "cpp_backend/core/modules/alchemical_launcher_generator/plugins"
print("Scanning for plugins in: " .. pluginDirectory)

pluginManager:scanForPlugins(pluginDirectory)

-- List loaded plugins
local loadedPlugins = pluginManager:getLoadedPluginNames()
print("Loaded plugins:")
for i, pluginName in ipairs(loadedPlugins) do
    local pluginInfo = pluginManager:getPluginInfo(pluginName)
    print(string.format("  %d. %s", i, pluginName))
    print("     " .. pluginInfo:gsub("\n", "\n     "))
end

-- Example 2: Plugin Capabilities and Validation
print("\n--- Example 2: Plugin Capabilities and Validation ---")

-- Check plugin capabilities
local capabilities = {
    "dynamic_generation",
    "mood_based_generation", 
    "theme_based_generation",
    "real_time_generation"
}

for _, capability in ipairs(capabilities) do
    local pluginsWithCapability = pluginManager:getPluginsWithCapability(capability)
    print(string.format("Plugins with %s capability: %d", capability, #pluginsWithCapability))
    for _, pluginName in ipairs(pluginsWithCapability) do
        print(string.format("  - %s", pluginName))
    end
end

-- Example 3: Loading Palettes from Plugins
print("\n--- Example 3: Loading Palettes from Plugins ---")

-- Get all available palettes from plugins
local allPalettes = pluginManager:getAllAvailablePalettes()
print("All available palettes from plugins:")
for i, paletteName in ipairs(allPalettes) do
    print(string.format("  %d. %s", i, paletteName))
end

-- Load specific palettes from plugins
for _, pluginName in ipairs(loadedPlugins) do
    local availablePalettes = pluginManager:getAllAvailablePalettes()
    if #availablePalettes > 0 then
        local samplePaletteName = availablePalettes[1]
        local palette = pluginManager:loadPaletteFromPlugin(pluginName, samplePaletteName)
        
        if palette and palette:size() > 0 then
            print(string.format("Loaded palette '%s' from plugin '%s':", samplePaletteName, pluginName))
            print(string.format("  Name: %s", palette.name))
            print(string.format("  Description: %s", palette.description))
            print(string.format("  Colors: %d", palette:size()))
            print(string.format("  Mood: %s", palette.mood))
            print(string.format("  Season: %s", palette.season))
            print("  Tags: " .. table.concat(palette.tags, ", "))
            
            -- Show first few colors
            print("  Sample colors:")
            for i = 1, math.min(3, palette:size()) do
                local color = palette.colors[i]
                print(string.format("    %d. %s (Energy: %.2f, Warmth: %.2f)", 
                                  i, color:toHex(), color.energy, color.warmth))
            end
        end
    end
end

-- Example 4: Plugin-Aware Palette Generation
print("\n--- Example 4: Plugin-Aware Palette Generation ---")

-- Generate palettes from plugins based on context
local contexts = {"warm", "cool", "metallic", "neon", "pastel", "earth", "cyber", "vintage", "nature", "abstract"}

for _, context in ipairs(contexts) do
    local generatedPalettes = colorPicker:generatePalettesFromPlugins(context)
    if #generatedPalettes > 0 then
        print(string.format("Generated %d palettes for context '%s':", #generatedPalettes, context))
        for i, palette in ipairs(generatedPalettes) do
            print(string.format("  %d. %s (%d colors)", i, palette.name, palette:size()))
        end
    end
end

-- Example 5: Mood-Based Palette Generation
print("\n--- Example 5: Mood-Based Palette Generation ---")

local moods = {"energetic", "calming", "mystical", "warm", "cool", "natural", "creative", "passionate", "serene", "industrial"}

for _, mood in ipairs(moods) do
    local moodPalettes = colorPicker:generatePalettesFromPluginsByMood(mood)
    if #moodPalettes > 0 then
        print(string.format("Generated %d palettes for mood '%s':", #moodPalettes, mood))
        for i, palette in ipairs(moodPalettes) do
            print(string.format("  %d. %s (Energy: %.2f, Intensity: %.2f)", 
                              i, palette.name, palette:getAverageSaturation(), palette:getAverageValue()))
        end
    end
end

-- Example 6: Theme-Based Palette Generation
print("\n--- Example 6: Theme-Based Palette Generation ---")

local themes = {"fire", "water", "earth", "air", "metal", "wood", "light", "dark", "nature", "urban"}

for _, theme in ipairs(themes) do
    local themePalettes = colorPicker:generatePalettesFromPluginsByTheme(theme)
    if #themePalettes > 0 then
        print(string.format("Generated %d palettes for theme '%s':", #themePalettes, theme))
        for i, palette in ipairs(themePalettes) do
            print(string.format("  %d. %s (Mood: %s, Season: %s)", 
                              i, palette.name, palette.mood, palette.season))
        end
    end
end

-- Example 7: Plugin Management and Hot-Reloading
print("\n--- Example 7: Plugin Management and Hot-Reloading ---")

-- Enable hot-reloading
pluginManager:enableHotReloading(true)
print("Hot-reloading enabled")

-- Check plugin status
for _, pluginName in ipairs(loadedPlugins) do
    local isEnabled = pluginManager:isPluginEnabled(pluginName)
    print(string.format("Plugin '%s' enabled: %s", pluginName, tostring(isEnabled)))
end

-- Disable a plugin temporarily
if #loadedPlugins > 0 then
    local testPlugin = loadedPlugins[1]
    pluginManager:setPluginEnabled(testPlugin, false)
    print(string.format("Temporarily disabled plugin: %s", testPlugin))
    
    -- Re-enable it
    pluginManager:setPluginEnabled(testPlugin, true)
    print(string.format("Re-enabled plugin: %s", testPlugin))
end

-- Example 8: Plugin Configuration and Settings
print("\n--- Example 8: Plugin Configuration and Settings ---")

-- Load plugin settings
local settings = PluginConfig.loadSettings("plugin_config.json")
print("Plugin settings loaded:")
print("  Hot reloading: " .. tostring(settings.enableHotReloading))
print("  Async loading: " .. tostring(settings.enableAsyncLoading))
print("  Plugin validation: " .. tostring(settings.enablePluginValidation))
print("  Dependency checking: " .. tostring(settings.enableDependencyChecking))
print("  Plugin directory: " .. settings.pluginDirectory)

-- Apply settings
PluginConfig.applySettings(settings)
print("Plugin settings applied")

-- Example 9: Plugin Validation and Error Handling
print("\n--- Example 9: Plugin Validation and Error Handling ---")

-- Test plugin validation
local testPluginPaths = {
    "plugins/valid_lua_plugin.lua",
    "plugins/invalid_lua_plugin.lua",
    "plugins/valid_cpp_plugin.so",
    "plugins/invalid_cpp_plugin.so"
}

for _, pluginPath in ipairs(testPluginPaths) do
    local isValid = PluginUtils.isValidPluginFile(pluginPath)
    local validationError = PluginUtils.getPluginValidationError(pluginPath)
    
    print(string.format("Plugin '%s':", pluginPath))
    print(string.format("  Valid: %s", tostring(isValid)))
    if not isValid and validationError ~= "" then
        print(string.format("  Error: %s", validationError))
    end
end

-- Example 10: Plugin Metadata Extraction
print("\n--- Example 10: Plugin Metadata Extraction ---")

-- Extract metadata from plugin files
for _, pluginPath in ipairs(testPluginPaths) do
    if PluginUtils.isValidPluginFile(pluginPath) then
        local pluginName = PluginUtils.extractPluginName(pluginPath)
        local pluginVersion = PluginUtils.extractPluginVersion(pluginPath)
        local pluginAuthor = PluginUtils.extractPluginAuthor(pluginPath)
        local pluginDescription = PluginUtils.extractPluginDescription(pluginPath)
        
        print(string.format("Plugin metadata for '%s':", pluginPath))
        print(string.format("  Name: %s", pluginName))
        print(string.format("  Version: %s", pluginVersion))
        print(string.format("  Author: %s", pluginAuthor))
        print(string.format("  Description: %s", pluginDescription))
    end
end

-- Example 11: Plugin Capabilities Detection
print("\n--- Example 11: Plugin Capabilities Detection ---")

-- Detect plugin capabilities
for _, pluginPath in ipairs(testPluginPaths) do
    if PluginUtils.isValidPluginFile(pluginPath) then
        local capabilities = PluginUtils.detectPluginCapabilities(pluginPath)
        print(string.format("Capabilities for '%s':", pluginPath))
        for _, capability in ipairs(capabilities) do
            print(string.format("  - %s", capability))
        end
    end
end

-- Example 12: Plugin File Management
print("\n--- Example 12: Plugin File Management ---")

-- Test plugin backup and restore
for _, pluginPath in ipairs(testPluginPaths) do
    if PluginUtils.isValidPluginFile(pluginPath) then
        local backupSuccess = PluginUtils.backupPlugin(pluginPath)
        print(string.format("Backup for '%s': %s", pluginPath, tostring(backupSuccess)))
        
        if backupSuccess then
            local restoreSuccess = PluginUtils.restorePlugin(pluginPath)
            print(string.format("Restore for '%s': %s", pluginPath, tostring(restoreSuccess)))
        end
    end
end

-- Example 13: Plugin Dependency Management
print("\n--- Example 13: Plugin Dependency Management ---")

-- Check plugin dependencies
for _, pluginPath in ipairs(testPluginPaths) do
    if PluginUtils.isValidPluginFile(pluginPath) then
        local dependencies = PluginUtils.getPluginDependencies(pluginPath)
        print(string.format("Dependencies for '%s':", pluginPath))
        if #dependencies > 0 then
            for _, dependency in ipairs(dependencies) do
                print(string.format("  - %s", dependency))
            end
        else
            print("  No dependencies found")
        end
        
        local dependenciesOk = PluginUtils.checkPluginDependencies(pluginPath)
        print(string.format("  Dependencies OK: %s", tostring(dependenciesOk)))
    end
end

-- Example 14: Advanced Plugin Integration
print("\n--- Example 14: Advanced Plugin Integration ---")

-- Create a comprehensive palette using multiple plugins
local comprehensivePalette = ColorPalette("Comprehensive Plugin Palette")
comprehensivePalette.description = "A palette created using multiple plugins"
comprehensivePalette.tags = {"comprehensive", "multi-plugin", "demo"}

-- Load palettes from all plugins and combine them
for _, pluginName in ipairs(loadedPlugins) do
    local availablePalettes = pluginManager:getAllAvailablePalettes()
    if #availablePalettes > 0 then
        local samplePalette = pluginManager:loadPaletteFromPlugin(pluginName, availablePalettes[1])
        if samplePalette and samplePalette:size() > 0 then
            -- Add colors from this palette to our comprehensive palette
            for i = 1, math.min(2, samplePalette:size()) do
                comprehensivePalette:addColor(samplePalette.colors[i])
            end
        end
    end
end

print(string.format("Created comprehensive palette with %d colors from %d plugins", 
                   comprehensivePalette:size(), #loadedPlugins))

-- Example 15: Plugin Performance Testing
print("\n--- Example 15: Plugin Performance Testing ---")

-- Test plugin loading performance
local startTime = os.clock()
for i = 1, 10 do
    pluginManager:checkForPluginUpdates()
end
local endTime = os.clock()
print(string.format("Plugin update check performance: %.3f seconds for 10 checks", endTime - startTime))

-- Test palette generation performance
startTime = os.clock()
for i = 1, 50 do
    local palettes = colorPicker:generatePalettesFromPlugins("warm")
end
endTime = os.clock()
print(string.format("Palette generation performance: %.3f seconds for 50 generations", endTime - startTime))

-- Example 16: Plugin Error Recovery
print("\n--- Example 16: Plugin Error Recovery ---")

-- Simulate plugin errors and recovery
for _, pluginName in ipairs(loadedPlugins) do
    print(string.format("Testing error recovery for plugin: %s", pluginName))
    
    -- Temporarily disable plugin
    pluginManager:setPluginEnabled(pluginName, false)
    print(string.format("  Disabled plugin: %s", pluginName))
    
    -- Try to load palette (should fail gracefully)
    local palette = pluginManager:loadPaletteFromPlugin(pluginName, "test_palette")
    if palette and palette:size() > 0 then
        print(string.format("  Error: Plugin still accessible when disabled"))
    else
        print(string.format("  Success: Plugin properly disabled"))
    end
    
    -- Re-enable plugin
    pluginManager:setPluginEnabled(pluginName, true)
    print(string.format("  Re-enabled plugin: %s", pluginName))
end

-- Example 17: Plugin Hot-Reloading Demo
print("\n--- Example 17: Plugin Hot-Reloading Demo ---")

-- Enable hot-reloading
pluginManager:enableHotReloading(true)
print("Hot-reloading enabled")

-- Check for plugin updates
pluginManager:checkForPluginUpdates()
print("Plugin update check completed")

-- Reload modified plugins
pluginManager:reloadModifiedPlugins()
print("Modified plugins reloaded")

-- Example 18: Plugin Configuration Persistence
print("\n--- Example 18: Plugin Configuration Persistence ---")

-- Create and save plugin settings
local testSettings = PluginConfig.PluginSettings()
testSettings.enableHotReloading = true
testSettings.enableAsyncLoading = true
testSettings.enablePluginValidation = true
testSettings.enableDependencyChecking = true
testSettings.pluginDirectory = "custom_plugins"
testSettings.enabledPlugins = {"ExampleLuaPalettePlugin", "ExampleCppPalettePlugin"}
testSettings.disabledPlugins = {"TestPlugin"}
testSettings.pluginOptions = {
    ["ExampleLuaPalettePlugin"] = {
        ["max_palettes"] = "10",
        ["cache_enabled"] = "true"
    },
    ["ExampleCppPalettePlugin"] = {
        ["thread_count"] = "4",
        ["memory_limit"] = "100MB"
    }
}

-- Save settings
PluginConfig.saveSettings(testSettings, "test_plugin_config.json")
print("Plugin settings saved to test_plugin_config.json")

-- Load and apply settings
local loadedSettings = PluginConfig.loadSettings("test_plugin_config.json")
PluginConfig.applySettings(loadedSettings)
print("Plugin settings loaded and applied")

print("\n=== Enhanced Color Picker Plugin System Demo Complete ===")
print("Plugin system features demonstrated:")
print("  ✓ Plugin discovery and loading (C++ and Lua)")
print("  ✓ Plugin capabilities and validation")
print("  ✓ Palette loading from plugins")
print("  ✓ Context-based palette generation")
print("  ✓ Mood-based palette generation")
print("  ✓ Theme-based palette generation")
print("  ✓ Plugin management and hot-reloading")
print("  ✓ Plugin configuration and settings")
print("  ✓ Plugin validation and error handling")
print("  ✓ Plugin metadata extraction")
print("  ✓ Plugin capabilities detection")
print("  ✓ Plugin file management (backup/restore)")
print("  ✓ Plugin dependency management")
print("  ✓ Advanced plugin integration")
print("  ✓ Plugin performance testing")
print("  ✓ Plugin error recovery")
print("  ✓ Plugin hot-reloading demo")
print("  ✓ Plugin configuration persistence")
print("  ✓ Cross-platform plugin support")
print("  ✓ Plugin lifecycle management")
print("  ✓ Plugin capability querying")
print("  ✓ Plugin-enabled color picker integration") 