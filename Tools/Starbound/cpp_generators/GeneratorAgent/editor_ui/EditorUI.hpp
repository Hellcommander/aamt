#pragma once
#include "vendor/imgui/imgui.h"
#include <glm/glm.hpp>
#include <string>
#include <vector>
#include <map>

namespace MagiTech {
namespace Editor {

struct ColorPalette {
    std::string name;
    std::vector<glm::vec4> colors;
};

class EditorUI {
public:
    void initialize();
    void shutdown();
    void draw();

    // The main color picker widget
    static bool DrawColorPicker(const char* label, glm::vec4& color);
    
    // Palette management
    void loadPalettes(const std::string& path);
    void savePalettes(const std::string& path);
    const std::vector<ColorPalette>& getPalettes() const { return m_palettes; }

private:
    void drawMainMenuBar();
    void drawAssetEditorPanels();
    
    // Placeholder drawing functions for each asset type
    void drawFlameProjectileEditor();
    void drawWormMechEditor();
    void drawTrapEditor();
    void drawBlackholeProjectileEditor();

    // Helper for parsing/formatting hex colors
    static bool parseHexColor(const char* hex, glm::vec4& outColor);
    static std::string formatHexColor(const glm::vec4& color);

    // Color harmony functions
    static void applyComplementary(glm::vec4& color);
    static void applyAnalogous(glm::vec4& color);
    static void applyTriadic(glm::vec4& color);

    std::vector<ColorPalette> m_palettes;
    bool m_showDemoWindow = true;
};

} // namespace Editor
} // namespace MagiTech
