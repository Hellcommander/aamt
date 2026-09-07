#include "IconAssetLuaBindings.hpp"
#include "IconAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace IconAssets {

static std::vector<std::pair<std::future<IconAsset>, std::string>> pendingIcons;
static std::vector<std::pair<std::future<IconAtlas>, std::string>> pendingAtlases;

void IconAssetLuaBindings::bind(sol::state& lua) {
    lua.new_enum("IconType",
        "Primitive", IconType::Primitive,
        "SVG", IconType::SVG,
        "Bitmap", IconType::Bitmap,
        "SDF", IconType::SDF
    );

    lua.new_enum("PrimitiveShape",
        "Circle", PrimitiveShape::Circle,
        "Square", PrimitiveShape::Square,
        "Triangle", PrimitiveShape::Triangle,
        "Star", PrimitiveShape::Star,
        "Custom", PrimitiveShape::Custom,
        "Heart", PrimitiveShape::Heart
    );
    
    lua.new_usertype<IconParams>("IconParams",
        sol::constructors<IconParams()>(),
        "id", &IconParams::id,
        "type", &IconParams::type,
        "shape", &IconParams::shape,
        "svgPath", &IconParams::svgPath,
        "size", &IconParams::size,
        "strokeWidth", &IconParams::strokeWidth,
        "fillColor", &IconParams::fillColor,
        "strokeColor", &IconParams::strokeColor,
        "generateSDF", &IconParams::generateSDF,
        "sdfPadding", &IconParams::sdfPadding
    );

    lua.new_usertype<AtlasParams>("AtlasParams",
        sol::constructors<AtlasParams()>(),
        "id", &AtlasParams::id,
        "iconSize", &AtlasParams::iconSize,
        "columns", &AtlasParams::columns,
        "rows", &AtlasParams::rows,
        "padding", &AtlasParams::padding,
        "generateMips", &AtlasParams::generateMips,
        "compress", &AtlasParams::compress
    );

    lua.new_usertype<IconAsset>("IconAsset",
        sol::no_constructor,
        "bitmap", &IconAsset::bitmap,
        "sdf", &IconAsset::sdf
    );

    lua.new_usertype<IconAtlas>("IconAtlas",
        sol::no_constructor,
        "atlasTexture", &IconAtlas::atlasTexture,
        "uvRects", &IconAtlas::uvRects
    );

    // Convenience functions for common icon types
    lua.set_function("create_health_icon", [](int size = 64) {
        IconParams params;
        params.id = "health_icon";
        params.type = IconType::Primitive;
        params.shape = PrimitiveShape::Heart;
        params.size = {size, size};
        params.fillColor = {1.0f, 0.0f, 0.0f, 1.0f};
        params.strokeColor = {0.8f, 0.0f, 0.0f, 1.0f};
        params.strokeWidth = 2.0f;
        params.generateSDF = true;
        params.sdfPadding = 8.0f;
        return params;
    });

    lua.set_function("create_mana_icon", [](int size = 64) {
        IconParams params;
        params.id = "mana_icon";
        params.type = IconType::Primitive;
        params.shape = PrimitiveShape::Circle;
        params.size = {size, size};
        params.fillColor = {0.0f, 0.5f, 1.0f, 1.0f};
        params.strokeColor = {0.0f, 0.3f, 0.8f, 1.0f};
        params.strokeWidth = 2.0f;
        params.generateSDF = true;
        params.sdfPadding = 8.0f;
        return params;
    });

    lua.set_function("create_stamina_icon", [](int size = 64) {
        IconParams params;
        params.id = "stamina_icon";
        params.type = IconType::Primitive;
        params.shape = PrimitiveShape::Square;
        params.size = {size, size};
        params.fillColor = {1.0f, 1.0f, 0.0f, 1.0f};
        params.strokeColor = {0.8f, 0.8f, 0.0f, 1.0f};
        params.strokeWidth = 2.0f;
        params.generateSDF = true;
        params.sdfPadding = 8.0f;
        return params;
    });

    lua.set_function("create_magic_icon", [](int size = 64) {
        IconParams params;
        params.id = "magic_icon";
        params.type = IconType::Primitive;
        params.shape = PrimitiveShape::Star;
        params.size = {size, size};
        params.fillColor = {0.8f, 0.0f, 1.0f, 1.0f};
        params.strokeColor = {0.6f, 0.0f, 0.8f, 1.0f};
        params.strokeWidth = 2.0f;
        params.generateSDF = true;
        params.sdfPadding = 8.0f;
        return params;
    });

    lua.set_function("create_elemental_icon", [](const std::string& element, int size = 64) {
        IconParams params;
        params.id = "elemental_" + element + "_icon";
        params.type = IconType::Primitive;
        params.shape = PrimitiveShape::Triangle;
        params.size = {size, size};
        
        if (element == "fire") {
            params.fillColor = {1.0f, 0.3f, 0.0f, 1.0f};
            params.strokeColor = {0.8f, 0.2f, 0.0f, 1.0f};
        } else if (element == "ice") {
            params.fillColor = {0.5f, 0.8f, 1.0f, 1.0f};
            params.strokeColor = {0.3f, 0.6f, 0.8f, 1.0f};
        } else if (element == "lightning") {
            params.fillColor = {1.0f, 1.0f, 0.0f, 1.0f};
            params.strokeColor = {0.8f, 0.8f, 0.0f, 1.0f};
        } else if (element == "earth") {
            params.fillColor = {0.6f, 0.4f, 0.2f, 1.0f};
            params.strokeColor = {0.4f, 0.3f, 0.1f, 1.0f};
        } else {
            params.fillColor = {0.5f, 0.5f, 0.5f, 1.0f};
            params.strokeColor = {0.3f, 0.3f, 0.3f, 1.0f};
        }
        
        params.strokeWidth = 2.0f;
        params.generateSDF = true;
        params.sdfPadding = 8.0f;
        return params;
    });

    // Main icon generation functions
    lua.set_function("spawn_icon",
        [&](const IconParams& ip) {
            auto factory = MainPlugin::instance().getIconAssetFactory();
            pendingIcons.emplace_back(factory->generateIconAsync(ip), ip.id);
        }
    );

    lua.set_function("spawn_icon_atlas",
        [&](const sol::table& icons, const AtlasParams& ap) {
            std::vector<IconParams> iconParamsVec;
            for (const auto& kv : icons) {
                if (kv.second.is<IconParams>()) {
                    iconParamsVec.push_back(kv.second.as<IconParams>());
                }
            }
            auto factory = MainPlugin::instance().getIconAssetFactory();
            pendingAtlases.emplace_back(factory->generateAtlasAsync(iconParamsVec, ap), ap.id);
        }
    );

    // Utility functions
    lua.set_function("create_ui_atlas", [](const sol::table& icons, int iconSize = 64, int columns = 8, int rows = 8) {
        AtlasParams ap;
        ap.id = "ui_atlas";
        ap.iconSize = {iconSize, iconSize};
        ap.columns = columns;
        ap.rows = rows;
        ap.padding = 2;
        ap.generateMips = true;
        
        // Set up compression
        TextureAssets::CompressionParams compress;
        compress.format = "PNG";
        compress.quality = 90;
        compress.generateMipmaps = true;
        compress.sRGB = true;
        ap.compress = compress;
        
        return ap;
    });

    lua.set_function("create_spell_atlas", [](const sol::table& icons, int iconSize = 128, int columns = 4, int rows = 4) {
        AtlasParams ap;
        ap.id = "spell_atlas";
        ap.iconSize = {iconSize, iconSize};
        ap.columns = columns;
        ap.rows = rows;
        ap.padding = 4;
        ap.generateMips = true;
        
        // Set up compression for spell icons (higher quality)
        TextureAssets::CompressionParams compress;
        compress.format = "PNG";
        compress.quality = 95;
        compress.generateMipmaps = true;
        compress.sRGB = true;
        ap.compress = compress;
        
        return ap;
    });

    // Color utility functions
    lua.set_function("color_rgba", [](float r, float g, float b, float a = 1.0f) {
        return glm::vec4(r, g, b, a);
    });

    lua.set_function("color_hsv", [](float h, float s, float v, float a = 1.0f) {
        // Simple HSV to RGB conversion
        float c = v * s;
        float x = c * (1 - std::abs(std::fmod(h / 60.0f, 2.0f) - 1));
        float m = v - c;
        
        float r, g, b;
        if (h < 60) { r = c; g = x; b = 0; }
        else if (h < 120) { r = x; g = c; b = 0; }
        else if (h < 180) { r = 0; g = c; b = x; }
        else if (h < 240) { r = 0; g = x; b = c; }
        else if (h < 300) { r = x; g = 0; b = c; }
        else { r = c; g = 0; b = x; }
        
        return glm::vec4(r + m, g + m, b + m, a);
    });
}

void IconAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingIcons.begin(); it != pendingIcons.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto asset = it->first.get();
                lua["print"]("Icon asset ready: " + it->second + " (bitmap: " + std::to_string(asset.bitmap) + 
                            ", sdf: " + std::to_string(asset.sdf) + ")");
            } catch (const std::exception& e) { 
                lua["print"]("Icon asset error: " + it->second + " - " + e.what());
            }
            it = pendingIcons.erase(it);
        } else { ++it; }
    }
    
    for (auto it = pendingAtlases.begin(); it != pendingAtlases.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto atlas = it->first.get();
                lua["print"]("Icon atlas ready: " + it->second + " (texture: " + std::to_string(atlas.atlasTexture) + 
                            ", UVs: " + std::to_string(atlas.uvRects.size()) + ")");
            } catch (const std::exception& e) { 
                lua["print"]("Icon atlas error: " + it->second + " - " + e.what());
            }
            it = pendingAtlases.erase(it);
        } else { ++it; }
    }
}

} // namespace IconAssets
} // namespace MagiTech
