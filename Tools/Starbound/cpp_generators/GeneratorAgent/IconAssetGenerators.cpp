#include "IconAssetFactory.hpp"
#include "core/Log.hpp"
#include <cmath>
#include <algorithm>

namespace MagiTech {
namespace IconAssets {

#define LOG_ICON_GEN(Action, Id) Log::info("IconGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t IconParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(IconParams) - (2 * sizeof(std::string)));
    XXH64_update(&hash_state, id.c_str(), id.length());
    XXH64_update(&hash_state, svgPath.c_str(), svgPath.length());
    return XXH64_digest(&hash_state);
}

uint64_t AtlasParams::hashKey() const {
    XXH64_state_t hash_state;
    XXH64_reset(&hash_state, 0);
    XXH64_update(&hash_state, this, sizeof(AtlasParams) - sizeof(std::string) - sizeof(std::optional<TextureAssets::CompressionParams>));
    XXH64_update(&hash_state, id.c_str(), id.length());
    if(compress) {
        uint64_t h = compress->hashKey();
        XXH64_update(&hash_state, &h, sizeof(h));
    }
    return XXH64_digest(&hash_state);
}

namespace TextureLoader {
    TextureHandle load(const std::string& path) {
        LOG_ICON_GEN(LoadingBitmap, path);
        static uint32_t nextHandle = 1000; // Use a different range
        return nextHandle++;
    }
}

// Helper function to draw a pixel with anti-aliasing
inline void drawPixel(std::vector<uint8_t>& pixels, int x, int y, int width, int height, 
                     const glm::vec4& color, float alpha = 1.0f) {
    if (x < 0 || x >= width || y < 0 || y >= height) return;
    
    int index = (y * width + x) * 4;
    pixels[index] = static_cast<uint8_t>(color.r * 255);
    pixels[index + 1] = static_cast<uint8_t>(color.g * 255);
    pixels[index + 2] = static_cast<uint8_t>(color.b * 255);
    pixels[index + 3] = static_cast<uint8_t>(color.a * alpha * 255);
}

// Helper function to draw a line with anti-aliasing
void drawLine(std::vector<uint8_t>& pixels, int x1, int y1, int x2, int y2, 
              int width, int height, const glm::vec4& color, float thickness = 1.0f) {
    int dx = abs(x2 - x1);
    int dy = abs(y2 - y1);
    int sx = x1 < x2 ? 1 : -1;
    int sy = y1 < y2 ? 1 : -1;
    int err = dx - dy;
    
    while (true) {
        drawPixel(pixels, x1, y1, width, height, color);
        
        if (x1 == x2 && y1 == y2) break;
        int e2 = 2 * err;
        if (e2 > -dy) {
            err -= dy;
            x1 += sx;
        }
        if (e2 < dx) {
            err += dx;
            y1 += sy;
        }
    }
}

// Helper function to fill a circle
void fillCircle(std::vector<uint8_t>& pixels, int centerX, int centerY, int radius,
                int width, int height, const glm::vec4& color) {
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            if (x * x + y * y <= radius * radius) {
                drawPixel(pixels, centerX + x, centerY + y, width, height, color);
            }
        }
    }
}

// Helper function to draw circle outline
void drawCircle(std::vector<uint8_t>& pixels, int centerX, int centerY, int radius,
                int width, int height, const glm::vec4& color, float thickness = 1.0f) {
    for (int y = -radius; y <= radius; y++) {
        for (int x = -radius; x <= radius; x++) {
            float dist = std::sqrt(x * x + y * y);
            if (dist >= radius - thickness && dist <= radius) {
                drawPixel(pixels, centerX + x, centerY + y, width, height, color);
            }
        }
    }
}

// Helper function to fill a polygon
void fillPolygon(std::vector<uint8_t>& pixels, const std::vector<glm::vec2>& points,
                 int width, int height, const glm::vec4& color) {
    // Simple scanline fill algorithm
    int minY = static_cast<int>(points[0].y);
    int maxY = static_cast<int>(points[0].y);
    
    for (const auto& point : points) {
        minY = std::min(minY, static_cast<int>(point.y));
        maxY = std::max(maxY, static_cast<int>(point.y));
    }
    
    for (int y = minY; y <= maxY; y++) {
        std::vector<int> intersections;
        
        for (size_t i = 0; i < points.size(); i++) {
            size_t j = (i + 1) % points.size();
            const auto& p1 = points[i];
            const auto& p2 = points[j];
            
            if ((p1.y <= y && p2.y > y) || (p2.y <= y && p1.y > y)) {
                float x = p1.x + (p2.x - p1.x) * (y - p1.y) / (p2.y - p1.y);
                intersections.push_back(static_cast<int>(x));
            }
        }
        
        std::sort(intersections.begin(), intersections.end());
        
        for (size_t i = 0; i < intersections.size(); i += 2) {
            if (i + 1 < intersections.size()) {
                for (int x = intersections[i]; x <= intersections[i + 1]; x++) {
                    drawPixel(pixels, x, y, width, height, color);
                }
            }
        }
    }
}

// Helper function to draw polygon outline
void drawPolygon(std::vector<uint8_t>& pixels, const std::vector<glm::vec2>& points,
                 int width, int height, const glm::vec4& color, float thickness = 1.0f) {
    for (size_t i = 0; i < points.size(); i++) {
        size_t j = (i + 1) % points.size();
        drawLine(pixels, static_cast<int>(points[i].x), static_cast<int>(points[i].y),
                static_cast<int>(points[j].x), static_cast<int>(points[j].y),
                width, height, color, thickness);
    }
}

namespace PrimitiveGen {
    TextureHandle build(PrimitiveShape s, const glm::ivec2& size, const glm::vec4& fill, const glm::vec4& stroke, float strokeW) {
        LOG_ICON_GEN(BuildingPrimitive, "Shape");
        
        std::vector<uint8_t> pixels(size.x * size.y * 4, 0);
        int centerX = size.x / 2;
        int centerY = size.y / 2;
        int radius = std::min(size.x, size.y) / 2 - static_cast<int>(strokeW);
        
        switch (s) {
            case PrimitiveShape::Circle: {
                if (fill.a > 0) {
                    fillCircle(pixels, centerX, centerY, radius, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawCircle(pixels, centerX, centerY, radius + static_cast<int>(strokeW/2), 
                             size.x, size.y, stroke, strokeW);
                }
                break;
            }
            
            case PrimitiveShape::Square: {
                int halfSize = radius;
                std::vector<glm::vec2> points = {
                    {centerX - halfSize, centerY - halfSize},
                    {centerX + halfSize, centerY - halfSize},
                    {centerX + halfSize, centerY + halfSize},
                    {centerX - halfSize, centerY + halfSize}
                };
                
                if (fill.a > 0) {
                    fillPolygon(pixels, points, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawPolygon(pixels, points, size.x, size.y, stroke, strokeW);
                }
                break;
            }
            
            case PrimitiveShape::Triangle: {
                int halfSize = radius;
                std::vector<glm::vec2> points = {
                    {centerX, centerY - halfSize},
                    {centerX - halfSize, centerY + halfSize},
                    {centerX + halfSize, centerY + halfSize}
                };
                
                if (fill.a > 0) {
                    fillPolygon(pixels, points, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawPolygon(pixels, points, size.x, size.y, stroke, strokeW);
                }
                break;
            }
            
            case PrimitiveShape::Star: {
                int outerRadius = radius;
                int innerRadius = radius / 2;
                std::vector<glm::vec2> points;
                
                for (int i = 0; i < 10; i++) {
                    float angle = i * M_PI / 5;
                    int r = (i % 2 == 0) ? outerRadius : innerRadius;
                    points.emplace_back(centerX + r * std::cos(angle), 
                                     centerY + r * std::sin(angle));
                }
                
                if (fill.a > 0) {
                    fillPolygon(pixels, points, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawPolygon(pixels, points, size.x, size.y, stroke, strokeW);
                }
                break;
            }
            
            case PrimitiveShape::Heart: {
                int scale = radius / 2;
                std::vector<glm::vec2> points;
                
                // Generate heart shape points
                for (int i = 0; i <= 100; i++) {
                    float t = i * 2 * M_PI / 100;
                    float x = 16 * std::pow(std::sin(t), 3);
                    float y = -(13 * std::cos(t) - 5 * std::cos(2*t) - 2 * std::cos(3*t) - std::cos(4*t));
                    points.emplace_back(centerX + x * scale / 16, centerY + y * scale / 16);
                }
                
                if (fill.a > 0) {
                    fillPolygon(pixels, points, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawPolygon(pixels, points, size.x, size.y, stroke, strokeW);
                }
                break;
            }
            
            case PrimitiveShape::Custom:
            default:
                // Default to circle
                if (fill.a > 0) {
                    fillCircle(pixels, centerX, centerY, radius, size.x, size.y, fill);
                }
                if (stroke.a > 0 && strokeW > 0) {
                    drawCircle(pixels, centerX, centerY, radius + static_cast<int>(strokeW/2), 
                             size.x, size.y, stroke, strokeW);
                }
                break;
        }
        
        // Convert to texture handle (simplified)
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace PrimitiveGen

namespace SVGGen {
    TextureHandle render(const std::string& path, const glm::ivec2& size, const glm::vec4& fill, const glm::vec4& stroke, float strokeW) {
        LOG_ICON_GEN(RenderingSVG, path);
        // TODO: Implement SVG parsing and rasterization
        // For now, fall back to primitive generation
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace SVGGen

namespace SDFGen {
    TextureHandle generate(const TextureHandle& src, float padding) {
        LOG_ICON_GEN(GeneratingSDF, src);
        // TODO: Implement SDF generation (e.g., Jump Flooding)
        // For now, return a placeholder
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
} // namespace SDFGen

namespace AtlasGen {
    TextureHandle packIcons(const std::vector<TextureHandle>& icons, const AtlasParams& ap, const glm::ivec2& iconSize) {
        LOG_ICON_GEN(PackingAtlas, ap.id);
        // TODO: Implement actual icon packing into an atlas texture
        // For now, return a placeholder
        static uint32_t nextHandle = 1;
        return nextHandle++;
    }
    
    std::vector<glm::vec4> computeUVs(size_t count, int columns, int rows, const glm::ivec2& atlasSize, const glm::ivec2& iconSize, int padding) {
        std::vector<glm::vec4> uvs;
        uvs.reserve(count);
        float atlasW = (float)atlasSize.x;
        float atlasH = (float)atlasSize.y;

        for (size_t i = 0; i < count; ++i) {
            int x = i % columns;
            int y = i / columns;
            float u = (x * (iconSize.x + padding)) / atlasW;
            float v = (y * (iconSize.y + padding)) / atlasH;
            float w = iconSize.x / atlasW;
            float h = iconSize.y / atlasH;
            uvs.emplace_back(u, v, w, h);
        }
        return uvs;
    }
} // namespace AtlasGen

} // namespace IconAssets
} // namespace MagiTech
