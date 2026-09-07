#include "EditorUILuaBindings.hpp"
#include "EditorUI.hpp"
#include <glm/glm.hpp>

namespace MagiTech {
namespace Editor {

void EditorUILuaBindings::bind(sol::state& lua) {
    lua.set_function("open_color_picker", [&](const std::string& name, sol::table colorTable) -> bool {
        // Unpack color from Lua table
        glm::vec4 c(
            colorTable.get_or<float>(1, 0.0f),
            colorTable.get_or<float>(2, 0.0f),
            colorTable.get_or<float>(3, 0.0f),
            colorTable.get_or<float>(4, 1.0f)
        );

        // This is a conceptual binding. In a real ImGui app, drawing is stateful and happens
        // inside a loop. We can't just "pop up" a window from a simple function call.
        // This function would likely set a flag or some state that the main UI loop would
        // check to then draw the picker. For this example, we'll just log it.
        // bool changed = EditorUI::DrawColorPicker(name.c_str(), c);
        
        // Log the conceptual call
        printf("Lua requested color picker for '%s'. In a real app, this would be handled in the UI loop.\\n", name.c_str());

        bool changed = false; // In a real app, this would come from the widget.
        if (changed) {
            colorTable[1] = c.x;
            colorTable[2] = c.y;
            colorTable[3] = c.z;
            colorTable[4] = c.w;
        }
        
        return changed;
    });
}

} // namespace Editor
} // namespace MagiTech
