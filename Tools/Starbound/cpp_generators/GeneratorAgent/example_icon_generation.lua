-- Icon Asset Generation Example
-- This script demonstrates the comprehensive icon asset generation pipeline

print("=== Icon Asset Generation Example ===")

-- Initialize the icon asset factory
local function initialize_icon_system()
    print("Initializing icon asset generation system...")
    -- The factory should be initialized by the C++ backend
    -- This is just a placeholder for demonstration
end

-- Example 1: Basic primitive icons
local function create_basic_icons()
    print("\n--- Creating Basic Primitive Icons ---")
    
    -- Health icon (heart shape)
    local healthIcon = create_health_icon(64)
    spawn_icon(healthIcon)
    
    -- Mana icon (circle)
    local manaIcon = create_mana_icon(64)
    spawn_icon(manaIcon)
    
    -- Stamina icon (square)
    local staminaIcon = create_stamina_icon(64)
    spawn_icon(staminaIcon)
    
    -- Magic icon (star)
    local magicIcon = create_magic_icon(64)
    spawn_icon(magicIcon)
    
    print("Basic icons queued for generation")
end

-- Example 2: Elemental icons
local function create_elemental_icons()
    print("\n--- Creating Elemental Icons ---")
    
    local elements = {"fire", "ice", "lightning", "earth"}
    local elementalIcons = {}
    
    for i, element in ipairs(elements) do
        local icon = create_elemental_icon(element, 64)
        table.insert(elementalIcons, icon)
        spawn_icon(icon)
    end
    
    print("Elemental icons queued for generation")
    return elementalIcons
end

-- Example 3: Custom icons with specific parameters
local function create_custom_icons()
    print("\n--- Creating Custom Icons ---")
    
    -- Custom circle with specific colors
    local customCircle = IconParams()
    customCircle.id = "custom_circle"
    customCircle.type = IconType.Primitive
    customCircle.shape = PrimitiveShape.Circle
    customCircle.size = {128, 128}
    customCircle.fillColor = color_rgba(0.2, 0.8, 0.2, 1.0)  -- Green
    customCircle.strokeColor = color_rgba(0.1, 0.6, 0.1, 1.0) -- Dark green
    customCircle.strokeWidth = 3.0
    customCircle.generateSDF = true
    customCircle.sdfPadding = 12.0
    spawn_icon(customCircle)
    
    -- Custom triangle with HSV color
    local customTriangle = IconParams()
    customTriangle.id = "custom_triangle"
    customTriangle.type = IconType.Primitive
    customTriangle.shape = PrimitiveShape.Triangle
    customTriangle.size = {96, 96}
    customTriangle.fillColor = color_hsv(280, 0.8, 1.0, 1.0)  -- Purple
    customTriangle.strokeColor = color_hsv(280, 0.6, 0.8, 1.0) -- Dark purple
    customTriangle.strokeWidth = 2.5
    customTriangle.generateSDF = true
    customTriangle.sdfPadding = 10.0
    spawn_icon(customTriangle)
    
    print("Custom icons queued for generation")
end

-- Example 4: Creating icon atlases
local function create_icon_atlases()
    print("\n--- Creating Icon Atlases ---")
    
    -- Create a collection of UI icons
    local uiIcons = {}
    local iconShapes = {PrimitiveShape.Circle, PrimitiveShape.Square, PrimitiveShape.Triangle, PrimitiveShape.Star}
    local colors = {
        color_rgba(1.0, 0.0, 0.0, 1.0),  -- Red
        color_rgba(0.0, 1.0, 0.0, 1.0),  -- Green
        color_rgba(0.0, 0.0, 1.0, 1.0),  -- Blue
        color_rgba(1.0, 1.0, 0.0, 1.0),  -- Yellow
        color_rgba(1.0, 0.0, 1.0, 1.0),  -- Magenta
        color_rgba(0.0, 1.0, 1.0, 1.0),  -- Cyan
        color_rgba(1.0, 0.5, 0.0, 1.0),  -- Orange
        color_rgba(0.5, 0.0, 1.0, 1.0)   -- Purple
    }
    
    for i = 1, 8 do
        local icon = IconParams()
        icon.id = "ui_icon_" .. i
        icon.type = IconType.Primitive
        icon.shape = iconShapes[((i-1) % #iconShapes) + 1]
        icon.size = {64, 64}
        icon.fillColor = colors[i]
        icon.strokeColor = color_rgba(0.2, 0.2, 0.2, 1.0)
        icon.strokeWidth = 2.0
        icon.generateSDF = true
        icon.sdfPadding = 8.0
        table.insert(uiIcons, icon)
    end
    
    -- Create UI atlas
    local uiAtlas = create_ui_atlas(uiIcons, 64, 4, 2)
    spawn_icon_atlas(uiIcons, uiAtlas)
    
    -- Create spell icons for a spell atlas
    local spellIcons = {}
    local spellElements = {"fire", "ice", "lightning", "earth"}
    
    for i, element in ipairs(spellElements) do
        local spellIcon = create_elemental_icon(element, 128)
        spellIcon.id = "spell_" .. element
        table.insert(spellIcons, spellIcon)
    end
    
    -- Create spell atlas
    local spellAtlas = create_spell_atlas(spellIcons, 128, 2, 2)
    spawn_icon_atlas(spellIcons, spellAtlas)
    
    print("Icon atlases queued for generation")
end

-- Example 5: Advanced icon generation with different sizes and effects
local function create_advanced_icons()
    print("\n--- Creating Advanced Icons ---")
    
    -- Large spell icon with glow effect (simulated with stroke)
    local glowSpell = IconParams()
    glowSpell.id = "glow_spell"
    glowSpell.type = IconType.Primitive
    glowSpell.shape = PrimitiveShape.Star
    glowSpell.size = {256, 256}
    glowSpell.fillColor = color_hsv(60, 1.0, 1.0, 1.0)  -- Bright yellow
    glowSpell.strokeColor = color_hsv(60, 0.8, 1.0, 0.8) -- Glow effect
    glowSpell.strokeWidth = 8.0
    glowSpell.generateSDF = true
    glowSpell.sdfPadding = 20.0
    spawn_icon(glowSpell)
    
    -- Small status effect icon
    local statusIcon = IconParams()
    statusIcon.id = "status_poison"
    statusIcon.type = IconType.Primitive
    statusIcon.shape = PrimitiveShape.Circle
    statusIcon.size = {32, 32}
    statusIcon.fillColor = color_rgba(0.0, 0.8, 0.0, 1.0)  -- Green
    statusIcon.strokeColor = color_rgba(0.0, 0.6, 0.0, 1.0) -- Dark green
    statusIcon.strokeWidth = 1.0
    statusIcon.generateSDF = true
    statusIcon.sdfPadding = 4.0
    spawn_icon(statusIcon)
    
    -- Medium-sized buff icon
    local buffIcon = IconParams()
    buffIcon.id = "buff_strength"
    buffIcon.type = IconType.Primitive
    buffIcon.shape = PrimitiveShape.Square
    buffIcon.size = {48, 48}
    buffIcon.fillColor = color_rgba(0.8, 0.4, 0.0, 1.0)  -- Orange
    buffIcon.strokeColor = color_rgba(0.6, 0.3, 0.0, 1.0) -- Dark orange
    buffIcon.strokeWidth = 2.0
    buffIcon.generateSDF = true
    buffIcon.sdfPadding = 6.0
    spawn_icon(buffIcon)
    
    print("Advanced icons queued for generation")
end

-- Example 6: Batch icon generation for different UI themes
local function create_theme_icons()
    print("\n--- Creating Theme-Based Icons ---")
    
    local themes = {
        {name = "fire", color = color_rgba(1.0, 0.3, 0.0, 1.0), stroke = color_rgba(0.8, 0.2, 0.0, 1.0)},
        {name = "ice", color = color_rgba(0.5, 0.8, 1.0, 1.0), stroke = color_rgba(0.3, 0.6, 0.8, 1.0)},
        {name = "nature", color = color_rgba(0.2, 0.8, 0.2, 1.0), stroke = color_rgba(0.1, 0.6, 0.1, 1.0)},
        {name = "shadow", color = color_rgba(0.3, 0.0, 0.5, 1.0), stroke = color_rgba(0.2, 0.0, 0.3, 1.0)}
    }
    
    local themeIcons = {}
    
    for i, theme in ipairs(themes) do
        -- Create different shapes for each theme
        local shapes = {PrimitiveShape.Circle, PrimitiveShape.Square, PrimitiveShape.Triangle, PrimitiveShape.Star}
        
        for j, shape in ipairs(shapes) do
            local icon = IconParams()
            icon.id = theme.name .. "_" .. j
            icon.type = IconType.Primitive
            icon.shape = shape
            icon.size = {64, 64}
            icon.fillColor = theme.color
            icon.strokeColor = theme.stroke
            icon.strokeWidth = 2.0
            icon.generateSDF = true
            icon.sdfPadding = 8.0
            table.insert(themeIcons, icon)
            spawn_icon(icon)
        end
    end
    
    -- Create theme atlas
    local themeAtlas = AtlasParams()
    themeAtlas.id = "theme_atlas"
    themeAtlas.iconSize = {64, 64}
    themeAtlas.columns = 4
    themeAtlas.rows = 4
    themeAtlas.padding = 2
    themeAtlas.generateMips = true
    
    -- Set up compression
    local compress = TextureAssets.CompressionParams()
    compress.format = "PNG"
    compress.quality = 90
    compress.generateMipmaps = true
    compress.sRGB = true
    themeAtlas.compress = compress
    
    spawn_icon_atlas(themeIcons, themeAtlas)
    
    print("Theme-based icons queued for generation")
end

-- Main execution function
local function run_icon_generation_example()
    print("Starting Icon Asset Generation Example...")
    
    -- Initialize the system
    initialize_icon_system()
    
    -- Create various types of icons
    create_basic_icons()
    create_elemental_icons()
    create_custom_icons()
    create_icon_atlases()
    create_advanced_icons()
    create_theme_icons()
    
    print("\n=== Icon Generation Complete ===")
    print("All icons have been queued for generation.")
    print("Use poll_assets() to check for completed assets.")
end

-- Export the main function
return {
    run_example = run_icon_generation_example,
    create_basic_icons = create_basic_icons,
    create_elemental_icons = create_elemental_icons,
    create_custom_icons = create_custom_icons,
    create_icon_atlases = create_icon_atlases,
    create_advanced_icons = create_advanced_icons,
    create_theme_icons = create_theme_icons
} 