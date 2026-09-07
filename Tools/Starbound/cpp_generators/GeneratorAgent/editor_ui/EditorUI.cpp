#include "EditorUI.hpp"
#include "core/Log.hpp"
#include "vendor/imgui/imgui_internal.h"
#include <charconv>

// Dummy param structs for placeholder panels
namespace MagiTech {
    struct FlameProjectileParams { glm::vec4 coreColor, outerColor, emberColor; };
    namespace WormMechs { struct WormMechParams { glm::vec3 colorPrimary, colorSecondary; }; }
    namespace Traps { struct TrapParams { glm::vec4 liquidColor; }; }
    namespace BlackholeProjectiles { struct BlackholeProjectileParams { glm::vec4 starAbsorbColor; }; }
}

namespace MagiTech {
namespace Editor {

// --- Public API ---

void EditorUI::initialize() {
    Log::info("Initializing EditorUI...");
    // In a real application, you would load palettes here
}

void EditorUI::shutdown() {
    Log::info("Shutting down EditorUI...");
}

void EditorUI::draw() {
    drawMainMenuBar();
    drawAssetEditorPanels();

    if (m_showDemoWindow) {
        ImGui::ShowDemoWindow(&m_showDemoWindow);
    }
}

// --- Main Widgets ---

void EditorUI::drawMainMenuBar() {
    if (ImGui::BeginMainMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("Load Palettes...")) { /* ... */ }
            if (ImGui::MenuItem("Save Palettes...")) { /* ... */ }
            ImGui::EndMenu();
        }
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Show ImGui Demo", nullptr, &m_showDemoWindow);
            ImGui::EndMenu();
        }
        ImGui::EndMainMenuBar();
    }
}

void EditorUI::drawAssetEditorPanels() {
    ImGui::Begin("Asset Editors");
    if (ImGui::CollapsingHeader("Flame Projectile")) {
        drawFlameProjectileEditor();
    }
    if (ImGui::CollapsingHeader("Worm Mech")) {
        drawWormMechEditor();
    }
    if (ImGui::CollapsingHeader("Traps")) {
        drawTrapEditor();
    }
     if (ImGui::CollapsingHeader("Blackhole Projectile")) {
        drawBlackholeProjectileEditor();
    }
    ImGui::End();
}

// --- Placeholder Asset Editors ---

void EditorUI::drawFlameProjectileEditor() {
    static FlameProjectileParams p;
    DrawColorPicker("Core Color", p.coreColor);
    DrawColorPicker("Outer Color", p.outerColor);
    DrawColorPicker("Ember Color", p.emberColor);
}

void EditorUI::drawWormMechEditor() {
    static WormMechs::WormMechParams m;
    // ImGui colors are 4-component, so we need a temp vec4
    glm::vec4 primary(m.colorPrimary, 1.0f);
    glm::vec4 secondary(m.colorSecondary, 1.0f);
    if (DrawColorPicker("Primary Tint", primary)) m.colorPrimary = primary;
    if (DrawColorPicker("Secondary Accent", secondary)) m.colorSecondary = secondary;
}

void EditorUI::drawTrapEditor() {
    static Traps::TrapParams t;
    DrawColorPicker("Liquid/Gas Color", t.liquidColor);
}

void EditorUI::drawBlackholeProjectileEditor() {
    static BlackholeProjectiles::BlackholeProjectileParams b;
    DrawColorPicker("Star Absorb Color", b.starAbsorbColor);
}


// --- Static Color Picker Implementation ---

bool EditorUI::DrawColorPicker(const char* label, glm::vec4& color) {
    bool value_changed = false;
    ImGui::PushID(label);

    ImGui::Text("%s", label);
    ImGui::SameLine();

    // Preview button
    if (ImGui::ColorButton("##preview", ImVec4(color.r, color.g, color.b, color.a), ImGuiColorEditFlags_NoTooltip, ImVec2(20, 20))) {
        ImGui::OpenPopup("picker");
    }

    // Popup window
    if (ImGui::BeginPopup("picker")) {
        value_changed |= ImGui::ColorPicker4("##picker", &color.x, ImGuiColorEditFlags_DisplayHSV | ImGuiColorEditFlags_PickerHueWheel | ImGuiColorEditFlags_AlphaBar);
        
        // Hex input
        char hex_buf[10];
        snprintf(hex_buf, sizeof(hex_buf), "%s", formatHexColor(color).c_str());
        if (ImGui::InputText("Hex", hex_buf, sizeof(hex_buf), ImGuiInputTextFlags_EnterReturnsTrue)) {
             if(parseHexColor(hex_buf, color)) value_changed = true;
        }

        ImGui::Separator();

        // Harmony buttons
        if (ImGui::Button("Complementary")) { applyComplementary(color); value_changed = true; }
        ImGui::SameLine();
        if (ImGui::Button("Analogous"))  { applyAnalogous(color); value_changed = true; }
        ImGui::SameLine();
        if (ImGui::Button("Triadic"))    { applyTriadic(color); value_changed = true; }

        ImGui::EndPopup();
    }
    ImGui::PopID();
    return value_changed;
}

// --- Color Utility Functions (Stubs) ---

bool EditorUI::parseHexColor(const char* hex, glm::vec4& outColor) {
    // Basic hex parsing, e.g., #RRGGBB or RRGGBB
    const char* p = (hex[0] == '#') ? hex + 1 : hex;
    int r, g, b;
    if (sscanf(p, "%02x%02x%02x", &r, &g, &b) == 3) {
        outColor.r = r / 255.0f;
        outColor.g = g / 255.0f;
        outColor.b = b / 255.0f;
        return true;
    }
    return false;
}

std::string EditorUI::formatHexColor(const glm::vec4& color) {
    char buf[8];
    snprintf(buf, sizeof(buf), "%02X%02X%02X", 
        (int)(color.r * 255.0f), 
        (int)(color.g * 255.0f), 
        (int)(color.b * 255.0f));
    return std::string(buf);
}

void EditorUI::applyComplementary(glm::vec4& color) {
    float h, s, v;
    ImGui::ColorConvertRGBtoHSV(color.r, color.g, color.b, h, s, v);
    h = fmod(h + 0.5f, 1.0f);
    ImGui::ColorConvertHSVtoRGB(h, s, v, color.r, color.g, color.b);
}

void EditorUI::applyAnalogous(glm::vec4& color) {
    // Just a stub - would generate a palette, not modify in place
}

void EditorUI::applyTriadic(glm::vec4& color) {
    // Just a stub
}


} // namespace Editor
} // namespace MagiTech
