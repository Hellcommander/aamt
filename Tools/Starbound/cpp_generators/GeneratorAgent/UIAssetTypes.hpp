#pragma once
#include <string>
#include <vector>
#include <glm/glm.hpp>
#include "vendor/xxhash/xxhash.h"

namespace MagiTech {
namespace UIAssets {

using MeshHandle = uint32_t;
using TextureHandle = uint32_t;
using ShaderHandle = uint32_t;
using AnimationHandle = uint32_t;
using FontHandle = uint32_t;

enum class UIElementType { Panel, Button, Slider, ProgressBar, Icon, Text };
enum class TextAlign { Left, Center, Right };
enum class AnimEasing { Linear, EaseIn, EaseOut, EaseInOut, EaseOutBack, EaseOutElastic };

struct UIElementParams {
    std::string id = "default_element";
    UIElementType type = UIElementType::Panel;
    glm::vec2 size = {100.0f, 30.0f};
    float cornerRadius = 4.0f;
    glm::vec4 bgColor = {0.1f, 0.1f, 0.15f, 0.8f};
    glm::vec4 borderColor = {0.8f, 0.8f, 0.8f, 0.5f};
    float borderThickness = 1.0f;
    glm::vec4 accentColor = {0.2f, 0.5f, 0.9f, 1.0f};
    bool enableShadow = true;
    glm::vec2 shadowOffset = {2.0f, 2.0f};
    glm::vec4 shadowColor = {0.0f, 0.0f, 0.0f, 0.5f};
    float shadowBlur = 4.0f;

    // Text-specific
    std::string fontName = "Roboto-Regular";
    int fontSize = 14;
    glm::vec4 fontColor = {1.0f, 1.0f, 1.0f, 1.0f};
    TextAlign textAlign = TextAlign::Center;

    // Slider/ProgressBar
    float minValue = 0.0f;
    float maxValue = 100.0f;
    float currentValue = 50.0f;
    glm::vec2 handleSize = {10.0f, 20.0f};

    // Icon-specific
    std::string iconShape = "circle";
    glm::vec4 iconColor = {1.0f, 1.0f, 1.0f, 1.0f};

    // Animation
    bool enableAnim = true;
    float animDuration = 0.2f;
    AnimEasing animEasing = AnimEasing::EaseOut;

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        // Hashing complex structs requires careful handling
        XXH64_update(&hash_state, this, sizeof(UIElementParams) - (2*sizeof(std::string)));
        XXH64_update(&hash_state, id.c_str(), id.length());
        XXH64_update(&hash_state, fontName.c_str(), fontName.length());
        XXH64_update(&hash_state, iconShape.c_str(), iconShape.length());
        return XXH64_digest(&hash_state);
    }
};

struct UIThemeParams {
    std::string themeName = "Default";
    glm::vec4 primaryColor = {0.2f, 0.5f, 0.9f, 1.0f};
    glm::vec4 secondaryColor = {0.8f, 0.8f, 0.8f, 1.0f};
    glm::vec4 backgroundColor = {0.05f, 0.05f, 0.08f, 1.0f};
    glm::vec4 textColor = {0.9f, 0.9f, 0.9f, 1.0f};
    float borderRadius = 4.0f;
    float basePadding = 10.0f;
    std::vector<std::string> fontList = {"Roboto-Regular"};
    std::vector<glm::vec4> accentPalette = {{0.9f, 0.2f, 0.3f, 1.0f}};

    uint64_t hashKey() const noexcept {
        XXH64_state_t hash_state;
        XXH64_reset(&hash_state, 0);
        XXH64_update(&hash_state, this, sizeof(UIThemeParams) - (3*sizeof(std::vector<char*>)));
        XXH64_update(&hash_state, themeName.c_str(), themeName.length());
        for(const auto& font : fontList) {
             XXH64_update(&hash_state, font.c_str(), font.length());
        }
        XXH64_update(&hash_state, accentPalette.data(), accentPalette.size() * sizeof(glm::vec4));
        return XXH64_digest(&hash_state);
    }
};

struct UIAssetBundle {
    MeshHandle mesh;
    TextureHandle texture;
    ShaderHandle shader;
    AnimationHandle animations;
    FontHandle fontAtlas;
    TextureHandle iconTexture;
};

} // namespace UIAssets
} // namespace MagiTech
