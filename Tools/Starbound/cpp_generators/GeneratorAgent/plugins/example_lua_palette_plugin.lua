--[[
    Example Lua Color Palette Plugin
    
    This plugin demonstrates how to create a Lua-based color palette plugin
    for the enhanced color picker system.
    
    Plugin Interface:
    - plugin_name: Plugin identifier
    - plugin_version: Plugin version
    - plugin_author: Plugin author
    - plugin_description: Plugin description
    - available_palettes: List of available palette names
    - load_palette(name): Function to load a palette by name
    - save_palette(palette): Function to save a palette
    - delete_palette(name): Function to delete a palette
    - generate_palettes(context): Function to generate palettes based on context
    - generate_palette_from_mood(mood): Function to generate palette from mood
    - generate_palette_from_theme(theme): Function to generate palette from theme
    - supports_*: Capability flags
]]

-- Plugin metadata
plugin_name = "ExampleLuaPalettePlugin"
plugin_version = "1.0.0"
plugin_author = "MagiTech Developer"
plugin_description = "An example Lua plugin demonstrating color palette generation"

-- Available palettes
available_palettes = {
    "sunset_warm",
    "ocean_cool", 
    "forest_natural",
    "fire_energetic",
    "ice_calming",
    "mystic_purple",
    "desert_sand",
    "night_dark"
}

-- Capability flags
supports_dynamic_generation = true
supports_mood_based_generation = true
supports_theme_based_generation = true
supports_real_time_generation = false

-- Palette definitions
local palettes = {
    sunset_warm = {
        name = "Sunset Warm",
        description = "Warm sunset colors with orange and red tones",
        colors = {
            {r = 1.0, g = 0.4, b = 0.2, a = 1.0},  -- Orange
            {r = 1.0, g = 0.6, b = 0.3, a = 1.0},  -- Light orange
            {r = 1.0, g = 0.8, b = 0.4, a = 1.0},  -- Peach
            {r = 0.8, g = 0.3, b = 0.1, a = 1.0},  -- Dark red
            {r = 1.0, g = 0.2, b = 0.1, a = 1.0}   -- Bright red
        },
        mood = "warm",
        season = "summer",
        tags = {"warm", "sunset", "energetic"}
    },
    
    ocean_cool = {
        name = "Ocean Cool",
        description = "Cool ocean colors with blue and cyan tones",
        colors = {
            {r = 0.2, g = 0.6, b = 1.0, a = 1.0},  -- Blue
            {r = 0.4, g = 0.8, b = 1.0, a = 1.0},  -- Light blue
            {r = 0.0, g = 0.4, b = 0.8, a = 1.0},  -- Dark blue
            {r = 0.6, g = 0.9, b = 1.0, a = 1.0},  -- Cyan
            {r = 0.1, g = 0.3, b = 0.6, a = 1.0}   -- Navy
        },
        mood = "cool",
        season = "summer",
        tags = {"cool", "ocean", "calming"}
    },
    
    forest_natural = {
        name = "Forest Natural",
        description = "Natural forest colors with green and brown tones",
        colors = {
            {r = 0.2, g = 0.8, b = 0.4, a = 1.0},  -- Green
            {r = 0.4, g = 0.6, b = 0.2, a = 1.0},  -- Olive
            {r = 0.6, g = 0.4, b = 0.2, a = 1.0},  -- Brown
            {r = 0.3, g = 0.5, b = 0.3, a = 1.0},  -- Forest green
            {r = 0.8, g = 0.6, b = 0.4, a = 1.0}   -- Tan
        },
        mood = "natural",
        season = "spring",
        tags = {"natural", "forest", "organic"}
    },
    
    fire_energetic = {
        name = "Fire Energetic",
        description = "Energetic fire colors with red and yellow tones",
        colors = {
            {r = 1.0, g = 0.0, b = 0.0, a = 1.0},  -- Red
            {r = 1.0, g = 0.5, b = 0.0, a = 1.0},  -- Orange
            {r = 1.0, g = 1.0, b = 0.0, a = 1.0},  -- Yellow
            {r = 0.8, g = 0.2, b = 0.0, a = 1.0},  -- Dark red
            {r = 1.0, g = 0.8, b = 0.2, a = 1.0}   -- Gold
        },
        mood = "energetic",
        season = "summer",
        tags = {"energetic", "fire", "passionate"}
    },
    
    ice_calming = {
        name = "Ice Calming",
        description = "Calming ice colors with white and blue tones",
        colors = {
            {r = 1.0, g = 1.0, b = 1.0, a = 1.0},  -- White
            {r = 0.8, g = 0.9, b = 1.0, a = 1.0},  -- Light blue
            {r = 0.6, g = 0.8, b = 1.0, a = 1.0},  -- Ice blue
            {r = 0.9, g = 0.95, b = 1.0, a = 1.0}, -- Very light blue
            {r = 0.4, g = 0.6, b = 0.8, a = 1.0}   -- Steel blue
        },
        mood = "calming",
        season = "winter",
        tags = {"calming", "ice", "serene"}
    },
    
    mystic_purple = {
        name = "Mystic Purple",
        description = "Mystical purple colors with magical tones",
        colors = {
            {r = 0.6, g = 0.2, b = 1.0, a = 1.0},  -- Purple
            {r = 0.8, g = 0.4, b = 1.0, a = 1.0},  -- Light purple
            {r = 0.4, g = 0.0, b = 0.8, a = 1.0},  -- Dark purple
            {r = 1.0, g = 0.6, b = 1.0, a = 1.0},  -- Pink
            {r = 0.2, g = 0.0, b = 0.6, a = 1.0}   -- Deep purple
        },
        mood = "mystical",
        season = "autumn",
        tags = {"mystical", "purple", "magical"}
    },
    
    desert_sand = {
        name = "Desert Sand",
        description = "Desert sand colors with warm earth tones",
        colors = {
            {r = 0.9, g = 0.8, b = 0.6, a = 1.0},  -- Sand
            {r = 0.8, g = 0.7, b = 0.5, a = 1.0},  -- Tan
            {r = 0.7, g = 0.6, b = 0.4, a = 1.0},  -- Brown
            {r = 1.0, g = 0.9, b = 0.7, a = 1.0},  -- Light sand
            {r = 0.6, g = 0.5, b = 0.3, a = 1.0}   -- Dark brown
        },
        mood = "warm",
        season = "summer",
        tags = {"warm", "desert", "earth"}
    },
    
    night_dark = {
        name = "Night Dark",
        description = "Dark night colors with deep tones",
        colors = {
            {r = 0.0, g = 0.0, b = 0.0, a = 1.0},  -- Black
            {r = 0.1, g = 0.1, b = 0.2, a = 1.0},  -- Dark blue
            {r = 0.2, g = 0.2, b = 0.3, a = 1.0},  -- Dark gray
            {r = 0.0, g = 0.0, b = 0.4, a = 1.0},  -- Navy
            {r = 0.3, g = 0.3, b = 0.4, a = 1.0}   -- Gray
        },
        mood = "dark",
        season = "winter",
        tags = {"dark", "night", "mysterious"}
    }
}

-- Load palette function
function load_palette(name)
    if palettes[name] then
        local palette = palettes[name]
        -- Convert to ColorPalette format
        loaded_palette = {
            name = palette.name,
            description = palette.description,
            colors = palette.colors,
            mood = palette.mood,
            season = palette.season,
            tags = palette.tags
        }
        return true
    end
    return false
end

-- Save palette function
function save_palette(palette)
    -- Implementation for saving palette
    -- This would typically save to a file or database
    return true
end

-- Delete palette function
function delete_palette(name)
    if palettes[name] then
        palettes[name] = nil
        -- Remove from available_palettes list
        for i, palette_name in ipairs(available_palettes) do
            if palette_name == name then
                table.remove(available_palettes, i)
                break
            end
        end
        return true
    end
    return false
end

-- Generate palettes based on context
function generate_palettes(context)
    local generated = {}
    
    if context == "warm" then
        generated = {
            {
                name = "Generated Warm Palette",
                description = "Dynamically generated warm palette",
                colors = {
                    {r = 1.0, g = 0.5, b = 0.2, a = 1.0},
                    {r = 1.0, g = 0.7, b = 0.4, a = 1.0},
                    {r = 0.9, g = 0.6, b = 0.3, a = 1.0}
                },
                mood = "warm",
                tags = {"generated", "warm"}
            }
        }
    elseif context == "cool" then
        generated = {
            {
                name = "Generated Cool Palette",
                description = "Dynamically generated cool palette",
                colors = {
                    {r = 0.2, g = 0.6, b = 1.0, a = 1.0},
                    {r = 0.4, g = 0.8, b = 1.0, a = 1.0},
                    {r = 0.6, g = 0.9, b = 1.0, a = 1.0}
                },
                mood = "cool",
                tags = {"generated", "cool"}
            }
        }
    end
    
    generated_palettes = generated
    return true
end

-- Generate palette from mood
function generate_palette_from_mood(mood)
    local mood_palette = {
        name = "Mood Generated Palette",
        description = "Generated from mood: " .. mood,
        colors = {},
        mood = mood,
        tags = {"generated", "mood-based"}
    }
    
    if mood == "energetic" then
        mood_palette.colors = {
            {r = 1.0, g = 0.0, b = 0.0, a = 1.0},  -- Red
            {r = 1.0, g = 0.5, b = 0.0, a = 1.0},  -- Orange
            {r = 1.0, g = 1.0, b = 0.0, a = 1.0}   -- Yellow
        }
    elseif mood == "calming" then
        mood_palette.colors = {
            {r = 0.2, g = 0.6, b = 1.0, a = 1.0},  -- Blue
            {r = 0.4, g = 0.8, b = 1.0, a = 1.0},  -- Light blue
            {r = 0.6, g = 0.9, b = 1.0, a = 1.0}   -- Cyan
        }
    elseif mood == "mystical" then
        mood_palette.colors = {
            {r = 0.6, g = 0.2, b = 1.0, a = 1.0},  -- Purple
            {r = 0.8, g = 0.4, b = 1.0, a = 1.0},  -- Light purple
            {r = 0.4, g = 0.0, b = 0.8, a = 1.0}   -- Dark purple
        }
    else
        -- Default neutral palette
        mood_palette.colors = {
            {r = 0.5, g = 0.5, b = 0.5, a = 1.0},  -- Gray
            {r = 0.7, g = 0.7, b = 0.7, a = 1.0},  -- Light gray
            {r = 0.3, g = 0.3, b = 0.3, a = 1.0}   -- Dark gray
        }
    end
    
    return true
end

-- Generate palette from theme
function generate_palette_from_theme(theme)
    local theme_palette = {
        name = "Theme Generated Palette",
        description = "Generated from theme: " .. theme,
        colors = {},
        theme = theme,
        tags = {"generated", "theme-based"}
    }
    
    if theme == "fire" then
        theme_palette.colors = {
            {r = 1.0, g = 0.0, b = 0.0, a = 1.0},  -- Red
            {r = 1.0, g = 0.4, b = 0.2, a = 1.0},  -- Orange
            {r = 1.0, g = 0.8, b = 0.4, a = 1.0}   -- Light orange
        }
    elseif theme == "water" then
        theme_palette.colors = {
            {r = 0.2, g = 0.6, b = 1.0, a = 1.0},  -- Blue
            {r = 0.4, g = 0.8, b = 1.0, a = 1.0},  -- Light blue
            {r = 0.0, g = 0.4, b = 0.8, a = 1.0}   -- Dark blue
        }
    elseif theme == "earth" then
        theme_palette.colors = {
            {r = 0.6, g = 0.4, b = 0.2, a = 1.0},  -- Brown
            {r = 0.8, g = 0.6, b = 0.4, a = 1.0},  -- Tan
            {r = 0.4, g = 0.3, b = 0.1, a = 1.0}   -- Dark brown
        }
    else
        -- Default neutral palette
        theme_palette.colors = {
            {r = 0.5, g = 0.5, b = 0.5, a = 1.0},  -- Gray
            {r = 0.7, g = 0.7, b = 0.7, a = 1.0},  -- Light gray
            {r = 0.3, g = 0.3, b = 0.3, a = 1.0}   -- Dark gray
        }
    end
    
    return true
end

-- Utility function to create a color from RGB values
function create_color(r, g, b, a)
    return {r = r, g = g, b = b, a = a or 1.0}
end

-- Utility function to create a palette
function create_palette(name, description, colors, mood, season, tags)
    return {
        name = name,
        description = description,
        colors = colors,
        mood = mood,
        season = season,
        tags = tags or {}
    }
end

-- Plugin initialization
print("Example Lua Color Palette Plugin loaded successfully!")
print("Plugin: " .. plugin_name .. " v" .. plugin_version)
print("Author: " .. plugin_author)
print("Description: " .. plugin_description)
print("Available palettes: " .. #available_palettes)
print("Capabilities:")
print("  - Dynamic generation: " .. tostring(supports_dynamic_generation))
print("  - Mood-based generation: " .. tostring(supports_mood_based_generation))
print("  - Theme-based generation: " .. tostring(supports_theme_based_generation))
print("  - Real-time generation: " .. tostring(supports_real_time_generation)) 