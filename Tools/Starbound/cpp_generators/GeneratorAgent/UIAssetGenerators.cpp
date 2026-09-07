#include "UIAssetFactory.hpp"
#include "core/Log.hpp"
#include "core/graphics/Common.hpp" // For Mesh, Image, etc.
#include <cmath>

namespace MagiTech {
namespace UIAssets {

#define LOG_GEN(Asset, Id) Log::info("Building UI Asset {}: {}", #Asset, Id)

namespace MeshGen {
    // Helper to build a simple quad
    MeshHandle buildQuad(const glm::vec2& size) {
        Graphics::Mesh mesh;
        mesh.vertices = {
            {{-0.5f * size.x, -0.5f * size.y, 0.0f}, {0.0f, 0.0f}, {1,1,1,1}},
            {{ 0.5f * size.x, -0.5f * size.y, 0.0f}, {1.0f, 0.0f}, {1,1,1,1}},
            {{ 0.5f * size.x,  0.5f * size.y, 0.0f}, {1.0f, 1.0f}, {1,1,1,1}},
            {{-0.5f * size.x,  0.5f * size.y, 0.0f}, {0.0f, 1.0f}, {1,1,1,1}}
        };
        mesh.indices = {0, 1, 2, 0, 2, 3};
        return Graphics::AssetRegistry::registerMesh(mesh);
    }

    // A more complex 9-slice mesh generator would be needed for production
    MeshHandle buildNineSlice(const glm::vec2& size, float cornerRadius) {
        LOG_GEN("9-Slice Mesh", "...");
        return buildQuad(size); // Placeholder for 9-slice
    }

    MeshHandle buildTrackAndHandle(const glm::vec2& size, const glm::vec2& handleSize, float cornerRadius) {
        LOG_GEN("Slider Mesh", "...");
        return buildQuad(size); // Placeholder for slider
    }

    MeshHandle buildUIElement(const UIElementParams& p, const UIThemeParams& t) {
        LOG_GEN(Mesh, p.id);
        switch (p.type) {
            case UIElementType::Panel:
            case UIElementType::Button:
                return buildNineSlice(p.size, p.cornerRadius);
            case UIElementType::Slider:
            case UIElementType::ProgressBar:
                return buildTrackAndHandle(p.size, p.handleSize, p.cornerRadius);
            case UIElementType::Icon:
            case UIElementType::Text:
            default:
                return buildQuad(p.size);
        }
    }
} // namespace MeshGen

namespace TextureGen {
    TextureHandle buildUITexture(const UIElementParams& p, const UIThemeParams& t) {
        LOG_GEN(Texture, p.id);
        Graphics::Image image(static_cast<int>(p.size.x), static_cast<int>(p.size.y));
        
        for (int y = 0; y < image.getHeight(); ++y) {
            for (int x = 0; x < image.getWidth(); ++x) {
                float u = static_cast<float>(x) / image.getWidth();
                glm::vec4 color = glm::mix(p.bgColor, p.accentColor, u);
                image.setPixel(x, y, color);
            }
        }
        return Graphics::AssetRegistry::registerTexture(image);
    }
} // namespace TextureGen

namespace ShaderGen {
    ShaderHandle buildUIShader(const UIElementParams& p, const UIThemeParams& t) {
        LOG_GEN(Shader, p.id);
        // In a real engine, this would compile shader code from strings or files
        // and upload it to the GPU, returning a handle.
        static uint32_t nextShaderId = 1;
        return nextShaderId++;
    }
} // namespace ShaderGen

namespace AnimGen {
    AnimationHandle buildUIAnimations(const UIElementParams& p) {
        LOG_GEN(Animations, p.id);
        // This would generate animation curve data or state machine definitions.
        static uint32_t nextAnimId = 1;
        return p.enableAnim ? nextAnimId++ : 0;
    }
} // namespace AnimGen

namespace FontGen {
    FontHandle buildFontAtlas(const std::string& fontName, int fontSize, TextAlign align) {
        Log::info("Building Font Atlas: {}", fontName);
        // This would use a library like FreeType to rasterize characters into a texture atlas.
        static uint32_t nextFontId = 1;
        return nextFontId++;
    }
} // namespace FontGen

namespace IconGen {
    TextureHandle buildUIIcon(const std::string& shape, const glm::vec4& color, const glm::vec2& size) {
        Log::info("Building UI Icon: {}", shape);
        Graphics::Image image(static_cast<int>(size.x), static_cast<int>(size.y));
        // Simple circle drawing logic for demonstration
        if (shape == "circle") {
            glm::vec2 center = size * 0.5f;
            float radius = glm::min(size.x, size.y) * 0.5f;
            for (int y = 0; y < image.getHeight(); ++y) {
                for (int x = 0; x < image.getWidth(); ++x) {
                    if (glm::distance(glm::vec2(x, y), center) < radius) {
                        image.setPixel(x, y, color);
                    }
                }
            }
        }
        return Graphics::AssetRegistry::registerTexture(image);
    }
} // namespace IconGen

} // namespace UIAssets
} // namespace MagiTech
