-- OllamaLuaHelper.lua
-- Lua helper for integrating Ollama AI image generation into Starbound C++ backend
-- This can be called from C++ generators or Lua scripts
-- Uses PowerShell bridge to communicate with Ollama

local OllamaHelper = {}

-- Configuration
OllamaHelper.OLLAMA_URL = "http://localhost:11434"
OllamaHelper.IMAGE_MODEL = "flux"  -- Image generation model
OllamaHelper.TIMEOUT = 120  -- seconds

-- Path to PowerShell bridge (relative to script location or absolute)
OllamaHelper.BRIDGE_SCRIPT = "OllamaCppBridge.ps1"

-- Check if Ollama is available via PowerShell bridge
function OllamaHelper.isAvailable()
    -- Try to execute PowerShell bridge to check connection
    local bridgePath = OllamaHelper.BRIDGE_SCRIPT
    if not bridgePath:match("^[A-Za-z]:") then
        -- Relative path - try to find it
        bridgePath = os.getenv("PSScriptRoot") or "." .. "/" .. bridgePath
    end
    
    -- Execute PowerShell bridge to check connection
    local command = string.format(
        'powershell.exe -ExecutionPolicy Bypass -File "%s" -Action check_connection',
        bridgePath
    )
    
    local handle = io.popen(command)
    if handle then
        local result = handle:read("*a")
        handle:close()
        return result:match("OK") ~= nil
    end
    
    return false
end

-- Generate image using Ollama (if HTTP support is available)
function OllamaHelper.generateImage(description, width, height, outputPath)
    if not OllamaHelper.isAvailable() then
        return nil, "Ollama not available or HTTP support not enabled"
    end
    
    -- Create enhanced prompt for Starbound-style assets
    local prompt = string.format(
        "Starbound game asset: %s\nStyle: pixel art, 2D sprite, game asset\nSize: %dx%d pixels\nFormat: PNG with transparency support\nQuality: high detail, clean lines, Starbound art style",
        description, width, height
    )
    
    -- Make HTTP request to Ollama
    -- This would require HTTP library support in Starbound Lua
    -- For now, return nil to indicate fallback needed
    return nil, "HTTP support required for Ollama integration"
end

-- Enhanced image generation that tries Ollama first, falls back to procedural
function OllamaHelper.generateImageWithFallback(description, width, height, outputPath, proceduralGenerator)
    local image, error = OllamaHelper.generateImage(description, width, height, outputPath)
    
    if image then
        print("✓ Image generated with Ollama")
        return image
    else
        print("⚠ Ollama generation failed: " .. (error or "unknown error"))
        print("  Falling back to procedural generation...")
        
        if proceduralGenerator then
            return proceduralGenerator(description, width, height, outputPath)
        else
            return nil, "No fallback generator provided"
        end
    end
end

-- Helper to enhance procedural generation with description (uses Ollama if available)
function OllamaHelper.enhanceProceduralParams(params, description)
    if description and description ~= "" then
        -- First, try to enhance description with Ollama
        local enhancedDesc = OllamaHelper.enhanceDescription(description)
        
        -- Extract parameters using Ollama if available
        local extractedParams = OllamaHelper.extractParameters(enhancedDesc)
        
        -- Merge extracted parameters into params
        if extractedParams and type(extractedParams) == "table" then
            if extractedParams.colorPalette then
                params.colorPalette = extractedParams.colorPalette
            end
            if extractedParams.style then
                params.style = extractedParams.style
            end
            if extractedParams.hasGradient ~= nil then
                params.hasGradient = extractedParams.hasGradient
            end
            if extractedParams.hasPattern ~= nil then
                params.hasPattern = extractedParams.hasPattern
            end
            if extractedParams.hasSparkles ~= nil then
                params.hasSparkles = extractedParams.hasSparkles
            end
        else
            -- Fallback to basic extraction from description
            local descLower = string.lower(enhancedDesc)
            
            -- Color hints
            if string.find(descLower, "purple") or string.find(descLower, "violet") then
                params.colorPalette = params.colorPalette or {}
                table.insert(params.colorPalette, {200, 100, 255})
                table.insert(params.colorPalette, {150, 50, 200})
                table.insert(params.colorPalette, {100, 25, 150})
            elseif string.find(descLower, "blue") or string.find(descLower, "azure") then
                params.colorPalette = params.colorPalette or {}
                table.insert(params.colorPalette, {100, 150, 255})
                table.insert(params.colorPalette, {50, 100, 200})
                table.insert(params.colorPalette, {25, 50, 150})
            elseif string.find(descLower, "red") or string.find(descLower, "fire") then
                params.colorPalette = params.colorPalette or {}
                table.insert(params.colorPalette, {255, 100, 100})
                table.insert(params.colorPalette, {200, 50, 50})
                table.insert(params.colorPalette, {150, 25, 25})
            end
            
            -- Style hints
            if string.find(descLower, "magic") or string.find(descLower, "arcane") then
                params.style = "magical"
                params.hasGradient = true
                params.hasSparkles = true
            elseif string.find(descLower, "metal") or string.find(descLower, "mech") then
                params.style = "metallic"
                params.hasPattern = true
            elseif string.find(descLower, "crystal") or string.find(descLower, "gem") then
                params.style = "crystalline"
                params.hasGradient = true
                params.hasSparkles = true
            end
        end
        
        -- Mark that description was used
        params.useDescription = true
        params.description = enhancedDesc  -- Use enhanced description
        params.originalDescription = description  -- Keep original too
        params.ollamaEnhanced = (enhancedDesc ~= description)
    end
    
    return params
end

-- Extract parameters from description using Ollama
function OllamaHelper.extractParameters(description)
    if not description or description == "" then
        return {}
    end
    
    if not OllamaHelper.isAvailable() then
        return {}
    end
    
    local bridgePath = OllamaHelper.BRIDGE_SCRIPT
    if not bridgePath:match("^[A-Za-z]:") then
        bridgePath = os.getenv("PSScriptRoot") or "." .. "/" .. bridgePath
    end
    
    -- Escape description for command line
    local escapedDesc = description:gsub('"', '\\"')
    
    -- Execute PowerShell bridge to extract parameters
    local command = string.format(
        'powershell.exe -ExecutionPolicy Bypass -File "%s" -Action extract_parameters -Description "%s"',
        bridgePath, escapedDesc
    )
    
    local handle = io.popen(command)
    if handle then
        local result = handle:read("*a"):gsub("^%s+", ""):gsub("%s+$", "")
        handle:close()
        
        if result and result ~= "" and result ~= "{}" then
            -- Try to parse JSON
            local success, parsed = pcall(function()
                -- Simple JSON parsing (Lua doesn't have built-in JSON)
                -- For now, return empty table - C++ can parse JSON better
                return {}
            end)
            
            -- Return raw JSON string - C++ backend can parse it
            return result
        end
    end
    
    return {}
end

return OllamaHelper
