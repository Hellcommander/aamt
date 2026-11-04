#include "UnifiedAssetGeneratorUI.hpp"
#include <imgui.h>
#include <imgui_internal.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <typeinfo>
#include <nlohmann/json.hpp>

namespace MagiTech {
namespace AssetGen {

namespace {

nlohmann::json parametersToJson(const std::unordered_map<std::string, std::any>& parameters) {
    nlohmann::json params = nlohmann::json::object();
    for (const auto& [key, value] : parameters) {
        if (!value.has_value()) continue;
        if (value.type() == typeid(float)) {
            params[key] = std::any_cast<float>(value);
        } else if (value.type() == typeid(double)) {
            params[key] = std::any_cast<double>(value);
        } else if (value.type() == typeid(int)) {
            params[key] = std::any_cast<int>(value);
        } else if (value.type() == typeid(bool)) {
            params[key] = std::any_cast<bool>(value);
        } else if (value.type() == typeid(std::string)) {
            params[key] = std::any_cast<std::string>(value);
        }
    }
    return params;
}

nlohmann::json assetToJson(const AssetMetadata& asset) {
    nlohmann::json assetJson;
    assetJson["name"] = asset.name;
    assetJson["description"] = asset.description;
    assetJson["category"] = static_cast<int>(asset.category);
    assetJson["category_name"] = UIUtils::getCategoryDisplayName(asset.category);
    assetJson["type"] = static_cast<int>(asset.type);
    assetJson["type_name"] = UIUtils::getAssetTypeDisplayName(asset.type);
    assetJson["version"] = asset.version;
    assetJson["author"] = asset.author;
    assetJson["tags"] = asset.tags;
    assetJson["is_generated"] = asset.isGenerated;
    assetJson["output_path"] = asset.outputPath;
    assetJson["creation_time"] = std::chrono::duration_cast<std::chrono::seconds>(
        asset.creationTime.time_since_epoch()).count();
    assetJson["parameters"] = parametersToJson(asset.parameters);
    return assetJson;
}

// Minimal YAML emitter for the JSON shapes produced by assetToJson (objects, arrays, scalars).
void writeYaml(std::ostringstream& out, const nlohmann::json& value, int indent) {
    const std::string pad(static_cast<size_t>(indent) * 2, ' ');
    auto scalar = [](const nlohmann::json& v) -> std::string {
        if (v.is_string()) {
            return v.dump();  // JSON string quoting is valid YAML double-quoted style
        }
        return v.dump();
    };
    if (value.is_object()) {
        for (const auto& [key, child] : value.items()) {
            if ((child.is_object() && !child.empty()) || (child.is_array() && !child.empty())) {
                out << pad << key << ":\n";
                writeYaml(out, child, indent + 1);
            } else if (child.is_object()) {
                out << pad << key << ": {}\n";
            } else if (child.is_array()) {
                out << pad << key << ": []\n";
            } else {
                out << pad << key << ": " << scalar(child) << "\n";
            }
        }
    } else if (value.is_array()) {
        for (const auto& child : value) {
            if (child.is_object() || child.is_array()) {
                out << pad << "-\n";
                writeYaml(out, child, indent + 1);
            } else {
                out << pad << "- " << scalar(child) << "\n";
            }
        }
    } else {
        out << pad << scalar(value) << "\n";
    }
}

} // namespace

// UnifiedAssetGeneratorUI Implementation
UnifiedAssetGeneratorUI::UnifiedAssetGeneratorUI() {
    // Initialize default asset metadata
    m_currentAsset.name = "New Asset";
    m_currentAsset.description = "Asset description";
    m_currentAsset.category = AssetCategory::MECHS;
    m_currentAsset.type = AssetType::MECH_BASIC;
    m_currentAsset.version = "1.0.0";
    m_currentAsset.author = "MagiTech";
    m_currentAsset.creationTime = std::chrono::system_clock::now();
}

UnifiedAssetGeneratorUI::~UnifiedAssetGeneratorUI() {
    // Cleanup generators
    for (auto& [name, generator] : m_generators) {
        if (generator) {
            generator->shutdown();
        }
    }
}

void UnifiedAssetGeneratorUI::showMainWindow() {
    if (!m_mainWindowOpen) {
        return;
    }

    ImGui::SetNextWindowSize(ImVec2(1200, 800), ImGuiCond_FirstUseEver);

    ImGui::Begin("MagiTech Asset Generator", &m_mainWindowOpen,
                 ImGuiWindowFlags_MenuBar | ImGuiWindowFlags_NoCollapse);

    // Menu bar
    if (ImGui::BeginMenuBar()) {
        if (ImGui::BeginMenu("File")) {
            if (ImGui::MenuItem("New Asset", "Ctrl+N")) {
                // Reset current asset
                m_currentAsset = AssetMetadata{};
                m_currentAsset.name = "New Asset";
                m_currentAsset.version = "1.0.0";
                m_currentAsset.author = "MagiTech";
                m_currentAsset.category = m_activeCategory;
                m_currentAsset.type = m_activeAssetType;
                m_currentAsset.creationTime = std::chrono::system_clock::now();
            }
            if (ImGui::MenuItem("Open Asset", "Ctrl+O")) {
                // Reload the asset library and UI state from the settings file
                if (loadConfiguration(m_settingsPath)) {
                    if (AssetMetadata* found = findAssetInLibrary(m_currentAsset.name)) {
                        m_currentAsset = *found;
                    } else if (!m_assetLibrary.empty()) {
                        m_currentAsset = m_assetLibrary.back();
                    }
                    m_statusMessage = "Loaded " + m_settingsPath;
                } else {
                    m_statusMessage = "Could not load " + m_settingsPath;
                }
            }
            if (ImGui::MenuItem("Save Asset", "Ctrl+S")) {
                updateAssetInLibrary(m_currentAsset);
                m_statusMessage = saveConfiguration(m_settingsPath) ? "Saved " + m_settingsPath
                                                                    : "Could not save " + m_settingsPath;
            }
            if (ImGui::MenuItem("Export Asset", "Ctrl+E")) {
                if (m_currentAsset.outputPath.empty()) {
                    m_currentAsset.outputPath = generateOutputPath(m_currentAsset);
                }
                exportAsset(m_currentAsset, m_currentAsset.outputPath);
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Exit")) {
                saveUISettings();
                m_mainWindowOpen = false;
            }
            ImGui::EndMenu();
        }
        
        if (ImGui::BeginMenu("View")) {
            ImGui::MenuItem("Asset Browser", nullptr, &m_showAssetBrowser);
            ImGui::MenuItem("Generator Panel", nullptr, &m_showGeneratorPanel);
            ImGui::MenuItem("Preview Panel", nullptr, &m_showPreviewPanel);
            ImGui::MenuItem("Export Panel", nullptr, &m_showExportPanel);
            ImGui::MenuItem("Settings", nullptr, &m_showSettingsPanel);
            ImGui::EndMenu();
        }
        
        if (ImGui::BeginMenu("Tools")) {
            if (ImGui::MenuItem("Batch Generate", nullptr, false, !m_activeGenerator.empty())) {
                // Regenerate every library asset that belongs to the active generator's category
                std::vector<AssetMetadata> batch;
                if (IAssetGenerator* generator = getGenerator(m_activeGenerator)) {
                    for (const auto& asset : m_assetLibrary) {
                        if (asset.category == generator->getCategory()) batch.push_back(asset);
                    }
                }
                const bool ok = batchGenerateAssets(batch);
                m_statusMessage = "Batch generated " + std::to_string(batch.size()) + " assets" + (ok ? "" : " (with errors)");
            }
            if (ImGui::MenuItem("Asset Library", nullptr, &m_showAssetBrowser)) {
                // Toggles the asset browser column
            }
            if (ImGui::MenuItem("Settings")) {
                m_showSettingsPanel = true;
            }
            ImGui::EndMenu();
        }
        
        if (ImGui::BeginMenu("Help")) {
            if (ImGui::MenuItem("Documentation")) {
                m_showDocsPopup = true;
            }
            if (ImGui::MenuItem("About")) {
                m_showAboutPopup = true;
            }
            ImGui::EndMenu();
        }

        ImGui::EndMenuBar();
    }

    // Help popups
    if (m_showDocsPopup) {
        ImGui::OpenPopup("Asset Generator Help");
        m_showDocsPopup = false;
    }
    if (ImGui::BeginPopupModal("Asset Generator Help", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::TextUnformatted("1. Pick a category tab and a generator.");
        ImGui::TextUnformatted("2. Choose an asset type and edit its parameters.");
        ImGui::TextUnformatted("3. Press 'Generate Asset' to run the generator and add it to the library.");
        ImGui::TextUnformatted("4. Use the Export panel to write the asset (JSON / YAML / MessagePack / CBOR).");
        ImGui::TextUnformatted("File > Save/Open stores the library and UI state in the settings file.");
        if (ImGui::Button("Close")) ImGui::CloseCurrentPopup();
        ImGui::EndPopup();
    }
    if (m_showAboutPopup) {
        ImGui::OpenPopup("About Asset Generator");
        m_showAboutPopup = false;
    }
    if (ImGui::BeginPopupModal("About Asset Generator", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
        ImGui::Text("MagiTech Unified Asset Generator");
        ImGui::Text("Registered generators: %zu", m_generators.size());
        ImGui::Text("Library assets: %zu", m_assetLibrary.size());
        if (ImGui::Button("Close")) ImGui::CloseCurrentPopup();
        ImGui::EndPopup();
    }
    
    // Main content area
    ImGui::Columns(4, "MainLayout", true);
    
    // Left panel - Asset Browser
    if (m_showAssetBrowser) {
        ImGui::BeginChild("AssetBrowser", ImVec2(0, 0), true);
        renderAssetBrowser();
        ImGui::EndChild();
    }
    ImGui::NextColumn();
    
    // Center panel - Generator
    if (m_showGeneratorPanel) {
        ImGui::BeginChild("GeneratorPanel", ImVec2(0, 0), true);
        renderCategoryTabs();
        renderGeneratorList();
        renderAssetTypeList();
        renderParameterPanel();
        ImGui::EndChild();
    }
    ImGui::NextColumn();
    
    // Right panel - Preview
    if (m_showPreviewPanel) {
        ImGui::BeginChild("PreviewPanel", ImVec2(0, 0), true);
        renderPreviewPanel();
        ImGui::EndChild();
    }
    ImGui::NextColumn();
    
    // Far right panel - Export
    if (m_showExportPanel) {
        ImGui::BeginChild("ExportPanel", ImVec2(0, 0), true);
        renderExportPanel();
        ImGui::EndChild();
    }
    
    ImGui::Columns(1);

    // Settings (toggled from View/Tools menus)
    if (m_showSettingsPanel) {
        ImGui::Separator();
        renderSettingsPanel();
    }

    // Status bar
    renderQuickActions();
    renderStatusBar();

    ImGui::End();
}

void UnifiedAssetGeneratorUI::showAssetBrowser() {
    if (!m_showAssetBrowser) return;
    if (ImGui::Begin("Asset Browser", &m_showAssetBrowser)) {
        renderAssetBrowser();
    }
    ImGui::End();
}

void UnifiedAssetGeneratorUI::showGeneratorPanel() {
    if (!m_showGeneratorPanel) return;
    if (ImGui::Begin("Generator", &m_showGeneratorPanel)) {
        renderCategoryTabs();
        renderGeneratorList();
        renderAssetTypeList();
        renderParameterPanel();
    }
    ImGui::End();
}

void UnifiedAssetGeneratorUI::showPreviewPanel() {
    if (!m_showPreviewPanel) return;
    if (ImGui::Begin("Asset Preview", &m_showPreviewPanel)) {
        renderPreviewPanel();
    }
    ImGui::End();
}

void UnifiedAssetGeneratorUI::showExportPanel() {
    if (!m_showExportPanel) return;
    if (ImGui::Begin("Asset Export", &m_showExportPanel)) {
        renderExportPanel();
    }
    ImGui::End();
}

void UnifiedAssetGeneratorUI::showSettingsPanel() {
    if (!m_showSettingsPanel) return;
    if (ImGui::Begin("Asset Generator Settings", &m_showSettingsPanel)) {
        renderSettingsPanel();
    }
    ImGui::End();
}

void UnifiedAssetGeneratorUI::renderSettingsPanel() {
    ImGui::Text("Settings");
    ImGui::Separator();

    char settingsPath[512];
    std::snprintf(settingsPath, sizeof(settingsPath), "%s", m_settingsPath.c_str());
    if (ImGui::InputText("Settings File", settingsPath, sizeof(settingsPath))) {
        m_settingsPath = settingsPath;
    }
    char exportDir[512];
    std::snprintf(exportDir, sizeof(exportDir), "%s", m_exportDirectory.c_str());
    if (ImGui::InputText("Export Directory", exportDir, sizeof(exportDir))) {
        m_exportDirectory = exportDir;
    }

    ImGui::Checkbox("Show Asset Browser", &m_showAssetBrowser);
    ImGui::Checkbox("Show Generator Panel", &m_showGeneratorPanel);
    ImGui::Checkbox("Show Preview Panel", &m_showPreviewPanel);
    ImGui::Checkbox("Show Export Panel", &m_showExportPanel);

    if (ImGui::Button("Save Settings")) {
        saveUISettings();
    }
    ImGui::SameLine();
    if (ImGui::Button("Load Settings")) {
        loadUISettings();
    }
    ImGui::SameLine();
    if (ImGui::Button("Reset to Defaults")) {
        resetToDefaults();
    }
}

void UnifiedAssetGeneratorUI::renderQuickActions() {
    if (m_recentAssets.empty()) {
        return;
    }
    ImGui::Text("Recent:");
    const int count = std::min(static_cast<int>(m_recentAssets.size()), MAX_QUICK_ACTIONS);
    for (int i = 0; i < count; ++i) {
        ImGui::SameLine();
        const std::string& name = m_recentAssets[static_cast<size_t>(i)];
        if (ImGui::SmallButton((name + "##recent" + std::to_string(i)).c_str())) {
            if (AssetMetadata* asset = findAssetInLibrary(name)) {
                m_currentAsset = *asset;
                m_activeAssetType = asset->type;
                m_activeCategory = asset->category;
            }
        }
    }
}

void UnifiedAssetGeneratorUI::saveUISettings() {
    if (!saveConfiguration(m_settingsPath)) {
        m_statusMessage = "Could not save settings to " + m_settingsPath;
    } else {
        m_statusMessage = "Settings saved to " + m_settingsPath;
    }
}

void UnifiedAssetGeneratorUI::loadUISettings() {
    if (!loadConfiguration(m_settingsPath)) {
        m_statusMessage = "Could not load settings from " + m_settingsPath;
    } else {
        m_statusMessage = "Settings loaded from " + m_settingsPath;
    }
}

void UnifiedAssetGeneratorUI::resetToDefaults() {
    m_activeCategory = AssetCategory::MECHS;
    m_activeGenerator.clear();
    m_activeAssetType = AssetType::MECH_BASIC;
    m_showAssetBrowser = true;
    m_showGeneratorPanel = true;
    m_showPreviewPanel = true;
    m_showExportPanel = true;
    m_showSettingsPanel = false;
    m_previewZoom = 1.0f;
    m_exportFormatIndex = 0;
    m_exportDirectory = "assets/export";
    m_statusMessage = "Settings reset to defaults";
}

void UnifiedAssetGeneratorUI::renderCategoryTabs() {
    ImGui::Text("Asset Categories");
    ImGui::Separator();
    
    const char* categories[] = {
        "Mechs", "Projectiles", "Weapons", "Creatures", "Effects",
        "Audio", "Visual", "Utility", "Cosmetic", "System"
    };
    
    static int selectedCategory = 0;
    if (ImGui::BeginTabBar("CategoryTabs")) {
        for (int i = 0; i < IM_ARRAYSIZE(categories); i++) {
            if (ImGui::BeginTabItem(categories[i])) {
                selectedCategory = i;
                m_activeCategory = static_cast<AssetCategory>(i);
                ImGui::EndTabItem();
            }
        }
        ImGui::EndTabBar();
    }
}

void UnifiedAssetGeneratorUI::renderGeneratorList() {
    ImGui::Text("Generators");
    ImGui::Separator();
    
    auto generators = getGeneratorsForCategory(m_activeCategory);
    if (generators.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No generators available for this category");
        return;
    }
    
    for (const auto& generatorName : generators) {
        bool isSelected = (m_activeGenerator == generatorName);
        if (ImGui::Selectable(generatorName.c_str(), isSelected)) {
            m_activeGenerator = generatorName;
        }
        
        if (isSelected) {
            ImGui::SetItemDefaultFocus();
        }
    }
}

void UnifiedAssetGeneratorUI::renderAssetTypeList() {
    ImGui::Text("Asset Types");
    ImGui::Separator();
    
    if (m_activeGenerator.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "Select a generator first");
        return;
    }
    
    auto generator = getGenerator(m_activeGenerator);
    if (!generator) {
        ImGui::TextColored(ImVec4(1.0f, 0.0f, 0.0f, 1.0f), "Generator not found: %s", m_activeGenerator.c_str());
        return;
    }
    
    auto assetTypes = generator->getSupportedAssetTypes();
    for (const auto& assetType : assetTypes) {
        bool isSelected = (m_activeAssetType == assetType);
        std::string displayName = UIUtils::getAssetTypeDisplayName(assetType);
        
        if (ImGui::Selectable(displayName.c_str(), isSelected)) {
            m_activeAssetType = assetType;
            m_currentAsset.type = assetType;
        }
        
        if (isSelected) {
            ImGui::SetItemDefaultFocus();
        }
    }
}

void UnifiedAssetGeneratorUI::renderParameterPanel() {
    ImGui::Text("Parameters");
    ImGui::Separator();
    
    if (m_activeGenerator.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "Select a generator to see parameters");
        return;
    }
    
    auto generator = getGenerator(m_activeGenerator);
    if (!generator) {
        return;
    }
    
    // Asset name
    static char assetName[256];
    strncpy(assetName, m_currentAsset.name.c_str(), sizeof(assetName) - 1);
    if (ImGui::InputText("Asset Name", assetName, sizeof(assetName))) {
        m_currentAsset.name = assetName;
    }
    
    // Asset description
    static char description[512];
    strncpy(description, m_currentAsset.description.c_str(), sizeof(description) - 1);
    if (ImGui::InputTextMultiline("Description", description, sizeof(description))) {
        m_currentAsset.description = description;
    }
    
    // Version
    static char version[64];
    strncpy(version, m_currentAsset.version.c_str(), sizeof(version) - 1);
    if (ImGui::InputText("Version", version, sizeof(version))) {
        m_currentAsset.version = version;
    }
    
    // Author
    static char author[128];
    strncpy(author, m_currentAsset.author.c_str(), sizeof(author) - 1);
    if (ImGui::InputText("Author", author, sizeof(author))) {
        m_currentAsset.author = author;
    }
    
    // Tags
    ImGui::Text("Tags");
    static char tagInput[128];
    if (ImGui::InputText("##TagInput", tagInput, sizeof(tagInput), ImGuiInputTextFlags_EnterReturnsTrue)) {
        if (strlen(tagInput) > 0) {
            m_currentAsset.tags.push_back(tagInput);
            tagInput[0] = '\0';
        }
    }
    
    // Display existing tags
    for (size_t i = 0; i < m_currentAsset.tags.size(); i++) {
        ImGui::SameLine();
        if (ImGui::Button(("X##Tag" + std::to_string(i)).c_str())) {
            m_currentAsset.tags.erase(m_currentAsset.tags.begin() + i);
            break;
        }
        ImGui::SameLine();
        ImGui::Text("%s", m_currentAsset.tags[i].c_str());
    }
    
    // Generator-specific parameters
    ImGui::Separator();
    ImGui::Text("Generator Parameters");
    
    auto supportedParams = generator->getSupportedParameters();
    for (const auto& paramName : supportedParams) {
        auto it = m_currentAsset.parameters.find(paramName);
        if (it != m_currentAsset.parameters.end()) {
            // Render parameter based on type
            if (it->second.type() == typeid(float)) {
                float value = std::any_cast<float>(it->second);
                if (ImGui::SliderFloat(paramName.c_str(), &value, 0.0f, 1.0f)) {
                    it->second = value;
                }
            } else if (it->second.type() == typeid(int)) {
                int value = std::any_cast<int>(it->second);
                if (ImGui::InputInt(paramName.c_str(), &value)) {
                    it->second = value;
                }
            } else if (it->second.type() == typeid(bool)) {
                bool value = std::any_cast<bool>(it->second);
                if (ImGui::Checkbox(paramName.c_str(), &value)) {
                    it->second = value;
                }
            } else if (it->second.type() == typeid(std::string)) {
                std::string value = std::any_cast<std::string>(it->second);
                static char buffer[256];
                strncpy(buffer, value.c_str(), sizeof(buffer) - 1);
                if (ImGui::InputText(paramName.c_str(), buffer, sizeof(buffer))) {
                    it->second = std::string(buffer);
                }
            }
        } else {
            // Add default parameter
            m_currentAsset.parameters[paramName] = 0.0f;
        }
    }
    
    // Generate button
    ImGui::Separator();
    if (ImGui::Button("Generate Asset", ImVec2(200, 30))) {
        if (validateAssetMetadata(m_currentAsset)) {
            generateAsset(m_activeGenerator, m_currentAsset);
        }
    }
}

void UnifiedAssetGeneratorUI::renderPreviewPanel() {
    ImGui::Text("Preview");
    ImGui::Separator();
    
    if (m_currentAsset.name.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No asset selected");
        return;
    }
    
    // Asset info
    ImGui::Text("Name: %s", m_currentAsset.name.c_str());
    ImGui::Text("Type: %s", UIUtils::getAssetTypeDisplayName(m_currentAsset.type).c_str());
    ImGui::Text("Category: %s", UIUtils::getCategoryDisplayName(m_currentAsset.category).c_str());
    ImGui::Text("Version: %s", m_currentAsset.version.c_str());
    ImGui::Text("Author: %s", m_currentAsset.author.c_str());
    
    if (!m_currentAsset.description.empty()) {
        ImGui::Text("Description: %s", m_currentAsset.description.c_str());
    }
    
    // Preview area: a card in the category colour, scaled by the preview zoom
    ImGui::BeginChild("PreviewArea", ImVec2(0, 200), true);
    {
        const ImVec2 areaMin = ImGui::GetCursorScreenPos();
        const ImVec2 avail = ImGui::GetContentRegionAvail();
        const float cardW = std::clamp(160.0f * m_previewZoom, 20.0f, std::max(20.0f, avail.x));
        const float cardH = std::clamp(110.0f * m_previewZoom, 20.0f, std::max(20.0f, avail.y - 30.0f));
        const ImVec2 cardMin(areaMin.x + (avail.x - cardW) * 0.5f, areaMin.y + 4.0f);
        const ImVec2 cardMax(cardMin.x + cardW, cardMin.y + cardH);
        ImDrawList* drawList = ImGui::GetWindowDrawList();
        const ImVec4 color = UIUtils::getAssetTypeColor(m_currentAsset.type);
        drawList->AddRectFilled(cardMin, cardMax, ImGui::ColorConvertFloat4ToU32(ImVec4(color.x * 0.4f, color.y * 0.4f, color.z * 0.4f, 1.0f)), 6.0f);
        drawList->AddRect(cardMin, cardMax, ImGui::ColorConvertFloat4ToU32(color), 6.0f, 0, 2.0f);
        drawList->AddText(ImVec2(cardMin.x + 8.0f, cardMin.y + 8.0f), IM_COL32(255, 255, 255, 255), m_currentAsset.name.c_str());
        const std::string typeName = UIUtils::getAssetTypeDisplayName(m_currentAsset.type);
        drawList->AddText(ImVec2(cardMin.x + 8.0f, cardMin.y + 26.0f), IM_COL32(200, 200, 200, 255), typeName.c_str());
        const std::string paramInfo = std::to_string(m_currentAsset.parameters.size()) + " parameters" +
                                      (m_currentAsset.isGenerated ? ", generated" : "");
        drawList->AddText(ImVec2(cardMin.x + 8.0f, cardMin.y + 44.0f), IM_COL32(180, 180, 180, 255), paramInfo.c_str());
        ImGui::Dummy(ImVec2(avail.x, cardH + 8.0f));
    }

    // Preview controls
    if (ImGui::Button("Refresh", ImVec2(80, 25))) {
        // Pull the latest stored copy of this asset from the library
        if (AssetMetadata* stored = findAssetInLibrary(m_currentAsset.name)) {
            m_currentAsset = *stored;
        }
    }
    ImGui::SameLine();
    if (ImGui::Button("Zoom In", ImVec2(80, 25))) {
        m_previewZoom = std::min(m_previewZoom * 1.25f, 4.0f);
    }
    ImGui::SameLine();
    if (ImGui::Button("Zoom Out", ImVec2(80, 25))) {
        m_previewZoom = std::max(m_previewZoom / 1.25f, 0.25f);
    }

    ImGui::EndChild();

    // Quick actions
    ImGui::Text("Quick Actions");
    ImGui::Separator();

    if (ImGui::Button("Duplicate", ImVec2(100, 25))) {
        AssetMetadata copy = m_currentAsset;
        std::string name = m_currentAsset.name + "_copy";
        for (int n = 2; findAssetInLibrary(name) != nullptr; ++n) {
            name = m_currentAsset.name + "_copy" + std::to_string(n);
        }
        copy.name = name;
        copy.isGenerated = false;
        copy.outputPath.clear();
        copy.creationTime = std::chrono::system_clock::now();
        addAssetToLibrary(copy);
        m_currentAsset = copy;
    }
    ImGui::SameLine();
    if (ImGui::Button("Export", ImVec2(100, 25))) {
        if (m_currentAsset.outputPath.empty()) {
            m_currentAsset.outputPath = generateOutputPath(m_currentAsset);
        }
        exportAsset(m_currentAsset, m_currentAsset.outputPath);
    }
    ImGui::SameLine();
    if (ImGui::Button("Delete", ImVec2(100, 25))) {
        const std::string name = m_currentAsset.name;
        removeAssetFromLibrary(name);
        m_recentAssets.erase(std::remove(m_recentAssets.begin(), m_recentAssets.end(), name), m_recentAssets.end());
        m_currentAsset = m_assetLibrary.empty() ? AssetMetadata{} : m_assetLibrary.back();
        m_statusMessage = "Deleted " + name;
    }
}

void UnifiedAssetGeneratorUI::renderExportPanel() {
    ImGui::Text("Export");
    ImGui::Separator();
    
    if (m_currentAsset.name.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No asset to export");
        return;
    }
    
    // Export path
    static char exportPath[512];
    strncpy(exportPath, m_currentAsset.outputPath.c_str(), sizeof(exportPath) - 1);
    if (ImGui::InputText("Export Path", exportPath, sizeof(exportPath))) {
        m_currentAsset.outputPath = exportPath;
    }
    
    ImGui::SameLine();
    if (ImGui::Button("Default Path")) {
        // No native file dialog is available in-game: fill in the conventional asset path
        m_currentAsset.outputPath = generateOutputPath(m_currentAsset);
    }
    
    // Export options
    ImGui::Text("Export Options");
    
    static bool exportMetadata = true;
    ImGui::Checkbox("Export Metadata", &exportMetadata);
    
    static bool exportPreview = true;
    ImGui::Checkbox("Export Preview", &exportPreview);
    
    static bool exportSource = false;
    ImGui::Checkbox("Export Source", &exportSource);
    
    // Export formats
    ImGui::Text("Export Format");
    const char* formats[] = {"JSON", "YAML", "Binary", "Custom"};
    ImGui::Combo("##Format", &m_exportFormatIndex, formats, IM_ARRAYSIZE(formats));
    
    // Export button
    ImGui::Separator();
    if (ImGui::Button("Export Asset", ImVec2(200, 30))) {
        if (!m_currentAsset.outputPath.empty()) {
            exportAsset(m_currentAsset, m_currentAsset.outputPath);
        }
    }
    
    // Batch export
    ImGui::Separator();
    ImGui::Text("Batch Export");
    
    if (ImGui::Button("Export All", ImVec2(100, 25))) {
        exportBatch(m_assetLibrary, m_exportDirectory);
    }
    ImGui::SameLine();
    if (ImGui::Button("Export Category", ImVec2(100, 25))) {
        std::vector<AssetMetadata> categoryAssets;
        for (const auto& asset : m_assetLibrary) {
            if (asset.category == m_currentAsset.category) categoryAssets.push_back(asset);
        }
        exportBatch(categoryAssets, m_exportDirectory + "/" + UIUtils::getCategoryDisplayName(m_currentAsset.category));
    }
}

void UnifiedAssetGeneratorUI::renderAssetBrowser() {
    ImGui::Text("Asset Library");
    ImGui::Separator();
    
    // Search
    static char searchText[256];
    ImGui::InputText("Search Assets", searchText, sizeof(searchText));
    
    // Filter by category
    ImGui::Text("Filter by Category");
    static int filterCategory = -1;
    const char* categories[] = {
        "All", "Mechs", "Projectiles", "Weapons", "Creatures", "Effects",
        "Audio", "Visual", "Utility", "Cosmetic", "System"
    };
    ImGui::Combo("##CategoryFilter", &filterCategory, categories, IM_ARRAYSIZE(categories));
    
    // Asset list
    ImGui::Text("Assets");
    ImGui::Separator();
    
    if (m_assetLibrary.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No assets in library");
        return;
    }
    
    for (const auto& asset : m_assetLibrary) {
        // Apply filters
        if (filterCategory > 0 && static_cast<int>(asset.category) != filterCategory - 1) {
            continue;
        }
        
        if (strlen(searchText) > 0) {
            if (asset.name.find(searchText) == std::string::npos &&
                asset.description.find(searchText) == std::string::npos) {
                continue;
            }
        }
        
        // Asset item
        bool isSelected = (m_currentAsset.name == asset.name);
        if (ImGui::Selectable(asset.name.c_str(), isSelected)) {
            m_currentAsset = asset;
        }
        
        if (isSelected) {
            ImGui::SetItemDefaultFocus();
        }
        
        // Asset info
        ImGui::SameLine();
        ImGui::TextColored(ImVec4(0.7f, 0.7f, 0.7f, 1.0f), 
                          "(%s)", UIUtils::getAssetTypeDisplayName(asset.type).c_str());
    }
}

void UnifiedAssetGeneratorUI::renderStatusBar() {
    ImGui::Text("Status: ");
    ImGui::SameLine();
    
    if (m_currentAsset.name.empty()) {
        ImGui::TextColored(ImVec4(1.0f, 1.0f, 0.0f, 1.0f), "No asset selected");
    } else {
        ImGui::TextColored(ImVec4(0.0f, 1.0f, 0.0f, 1.0f), 
                          "Asset: %s (%s)", 
                          m_currentAsset.name.c_str(),
                          UIUtils::getAssetTypeDisplayName(m_currentAsset.type).c_str());
    }
    
    ImGui::SameLine();
    ImGui::Text(" | ");
    ImGui::SameLine();
    
    ImGui::Text("Generators: %zu", m_generators.size());
    ImGui::SameLine();
    ImGui::Text(" | ");
    ImGui::SameLine();
    
    ImGui::Text("Assets: %zu", m_assetLibrary.size());

    if (!m_statusMessage.empty()) {
        ImGui::SameLine();
        ImGui::Text(" | ");
        ImGui::SameLine();
        ImGui::TextUnformatted(m_statusMessage.c_str());
    }
}

// Helper functions
std::string UnifiedAssetGeneratorUI::getCategoryName(AssetCategory category) {
    return UIUtils::getCategoryDisplayName(category);
}

std::string UnifiedAssetGeneratorUI::getAssetTypeName(AssetType type) {
    return UIUtils::getAssetTypeDisplayName(type);
}

ImVec4 UnifiedAssetGeneratorUI::getCategoryColor(AssetCategory category) {
    return UIUtils::getCategoryColor(category);
}

std::vector<std::string> UnifiedAssetGeneratorUI::getGeneratorsForCategory(AssetCategory category) {
    auto it = m_categoryGenerators.find(category);
    if (it != m_categoryGenerators.end()) {
        return it->second;
    }
    return {};
}

std::vector<AssetType> UnifiedAssetGeneratorUI::getAssetTypesForGenerator(const std::string& generatorName) {
    auto generator = getGenerator(generatorName);
    if (generator) {
        return generator->getSupportedAssetTypes();
    }
    return {};
}

// Asset management
bool UnifiedAssetGeneratorUI::registerGenerator(const std::string& name, std::unique_ptr<IAssetGenerator> generator) {
    if (m_generators.find(name) != m_generators.end()) {
        return false; // Already registered
    }
    
    if (generator && generator->initialize()) {
        m_generators[name] = std::move(generator);
        
        // Register with category
        auto category = m_generators[name]->getCategory();
        m_categoryGenerators[category].push_back(name);
        
        return true;
    }
    
    return false;
}

bool UnifiedAssetGeneratorUI::unregisterGenerator(const std::string& name) {
    auto it = m_generators.find(name);
    if (it != m_generators.end()) {
        it->second->shutdown();
        m_generators.erase(it);
        
        // Remove from category
        for (auto& [category, generators] : m_categoryGenerators) {
            generators.erase(std::remove(generators.begin(), generators.end(), name), generators.end());
        }
        
        return true;
    }
    
    return false;
}

IAssetGenerator* UnifiedAssetGeneratorUI::getGenerator(const std::string& name) {
    auto it = m_generators.find(name);
    if (it != m_generators.end()) {
        return it->second.get();
    }
    return nullptr;
}

// Asset generation
bool UnifiedAssetGeneratorUI::generateAsset(const std::string& generatorName, const AssetMetadata& metadata) {
    auto generator = getGenerator(generatorName);
    if (!generator) {
        return false;
    }
    
    if (generator->generateAsset(metadata)) {
        addAssetToLibrary(metadata);
        return true;
    }
    
    return false;
}

bool UnifiedAssetGeneratorUI::batchGenerateAssets(const std::vector<AssetMetadata>& assets) {
    bool success = true;
    
    for (const auto& asset : assets) {
        if (!generateAsset(m_activeGenerator, asset)) {
            success = false;
        }
    }
    
    return success;
}

// UI state management
void UnifiedAssetGeneratorUI::setActiveCategory(AssetCategory category) {
    m_activeCategory = category;
}

void UnifiedAssetGeneratorUI::setActiveGenerator(const std::string& generatorName) {
    m_activeGenerator = generatorName;
}

void UnifiedAssetGeneratorUI::setActiveAssetType(AssetType assetType) {
    m_activeAssetType = assetType;
    m_currentAsset.type = assetType;
}

// Configuration
bool UnifiedAssetGeneratorUI::saveConfiguration(const std::string& filePath) {
    try {
        nlohmann::json config;
        
        // Save UI state
        config["ui_state"] = {
            {"active_category", static_cast<int>(m_activeCategory)},
            {"active_generator", m_activeGenerator},
            {"active_asset_type", static_cast<int>(m_activeAssetType)},
            {"show_asset_browser", m_showAssetBrowser},
            {"show_generator_panel", m_showGeneratorPanel},
            {"show_preview_panel", m_showPreviewPanel},
            {"show_export_panel", m_showExportPanel},
            {"show_settings_panel", m_showSettingsPanel},
            {"preview_zoom", m_previewZoom},
            {"export_format", m_exportFormatIndex},
            {"export_directory", m_exportDirectory},
            {"recent_assets", m_recentAssets}
        };

        // Save asset library
        nlohmann::json assets = nlohmann::json::array();
        for (const auto& asset : m_assetLibrary) {
            assets.push_back(assetToJson(asset));
        }
        config["asset_library"] = assets;

        const std::filesystem::path parent = std::filesystem::path(filePath).parent_path();
        if (!parent.empty()) {
            std::error_code ec;
            std::filesystem::create_directories(parent, ec);
        }
        std::ofstream file(filePath);
        if (!file.is_open()) {
            return false;
        }
        file << config.dump(2);
        return file.good();
        
    } catch (const std::exception& e) {
        return false;
    }
}

bool UnifiedAssetGeneratorUI::loadConfiguration(const std::string& filePath) {
    try {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return false;
        }
        
        nlohmann::json config;
        file >> config;
        
        // Load UI state
        if (config.contains("ui_state")) {
            auto uiState = config["ui_state"];
            m_activeCategory = static_cast<AssetCategory>(uiState.value("active_category", 0));
            m_activeGenerator = uiState.value("active_generator", "");
            m_activeAssetType = static_cast<AssetType>(uiState.value("active_asset_type", 0));
            m_showAssetBrowser = uiState.value("show_asset_browser", true);
            m_showGeneratorPanel = uiState.value("show_generator_panel", true);
            m_showPreviewPanel = uiState.value("show_preview_panel", true);
            m_showExportPanel = uiState.value("show_export_panel", true);
            m_showSettingsPanel = uiState.value("show_settings_panel", false);
            m_previewZoom = uiState.value("preview_zoom", 1.0f);
            m_exportFormatIndex = std::clamp(uiState.value("export_format", 0), 0, 3);
            m_exportDirectory = uiState.value("export_directory", std::string("assets/export"));
            m_recentAssets = uiState.value("recent_assets", std::vector<std::string>{});
        }
        
        // Load asset library
        if (config.contains("asset_library")) {
            m_assetLibrary.clear();
            for (const auto& assetJson : config["asset_library"]) {
                AssetMetadata asset;
                asset.name = assetJson.value("name", "");
                asset.description = assetJson.value("description", "");
                asset.category = static_cast<AssetCategory>(assetJson.value("category", 0));
                asset.type = static_cast<AssetType>(assetJson.value("type", 0));
                asset.version = assetJson.value("version", "1.0.0");
                asset.author = assetJson.value("author", "");
                asset.tags = assetJson.value("tags", std::vector<std::string>{});
                asset.isGenerated = assetJson.value("is_generated", false);
                asset.outputPath = assetJson.value("output_path", "");
                
                // Load parameters
                if (assetJson.contains("parameters")) {
                    for (const auto& [key, value] : assetJson["parameters"].items()) {
                        if (value.is_number()) {
                            asset.parameters[key] = value.get<double>();
                        } else if (value.is_string()) {
                            asset.parameters[key] = value.get<std::string>();
                        } else if (value.is_boolean()) {
                            asset.parameters[key] = value.get<bool>();
                        }
                    }
                }
                
                m_assetLibrary.push_back(asset);
            }
        }
        
        return true;
        
    } catch (const std::exception& e) {
        return false;
    }
}

// Export management
bool UnifiedAssetGeneratorUI::exportAsset(const AssetMetadata& metadata, const std::string& outputPath) {
    if (!validateAssetMetadata(metadata) || outputPath.empty()) {
        m_statusMessage = "Export failed: asset needs a name, version, author and output path";
        return false;
    }
    try {
        const nlohmann::json j = assetToJson(metadata);
        std::filesystem::path path(outputPath);
        static const char* extensions[] = { ".json", ".yaml", ".msgpack", ".cbor" };
        const int format = std::clamp(m_exportFormatIndex, 0, 3);
        if (path.extension().empty() || path.extension() == ".json") {
            path.replace_extension(extensions[format]);
        }
        if (!path.parent_path().empty()) {
            std::error_code ec;
            std::filesystem::create_directories(path.parent_path(), ec);
        }
        std::ofstream out(path, std::ios::binary);
        if (!out.is_open()) {
            m_statusMessage = "Export failed: cannot open " + path.string();
            return false;
        }
        switch (format) {
            case 1: {  // YAML
                std::ostringstream yaml;
                writeYaml(yaml, j, 0);
                out << yaml.str();
                break;
            }
            case 2: {  // Binary (MessagePack)
                const std::vector<std::uint8_t> bytes = nlohmann::json::to_msgpack(j);
                out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
                break;
            }
            case 3: {  // Custom (CBOR)
                const std::vector<std::uint8_t> bytes = nlohmann::json::to_cbor(j);
                out.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
                break;
            }
            default:
                out << j.dump(2);
                break;
        }
        if (!out.good()) {
            m_statusMessage = "Export failed: write error on " + path.string();
            return false;
        }
        AssetMetadata exported = metadata;
        exported.outputPath = path.string();
        updateAssetInLibrary(exported);
        m_statusMessage = "Exported " + metadata.name + " to " + path.string();
        return true;
    } catch (const std::exception& e) {
        m_statusMessage = std::string("Export failed: ") + e.what();
        return false;
    }
}

bool UnifiedAssetGeneratorUI::exportBatch(const std::vector<AssetMetadata>& assets, const std::string& outputDir) {
    bool success = true;
    size_t exported = 0;
    // Copy: exportAsset updates the library, and `assets` may be the library itself
    const std::vector<AssetMetadata> toExport = assets;
    for (const auto& asset : toExport) {
        const std::string fileName = UIUtils::sanitizeAssetName(asset.name.empty() ? generateAssetName(asset.type) : asset.name);
        const std::string path = (std::filesystem::path(outputDir) / (fileName + ".json")).string();
        if (exportAsset(asset, path)) {
            ++exported;
        } else {
            success = false;
        }
    }
    m_statusMessage = "Exported " + std::to_string(exported) + "/" + std::to_string(assets.size()) + " assets to " + outputDir;
    return success;
}

// Helper functions
bool UnifiedAssetGeneratorUI::validateAssetMetadata(const AssetMetadata& metadata) {
    return !metadata.name.empty() && 
           !metadata.version.empty() && 
           !metadata.author.empty();
}

std::string UnifiedAssetGeneratorUI::generateAssetName(AssetType type) {
    return UIUtils::generateUniqueAssetName(type);
}

std::string UnifiedAssetGeneratorUI::generateOutputPath(const AssetMetadata& metadata) {
    std::string basePath = "assets/";
    basePath += UIUtils::getCategoryDisplayName(metadata.category);
    basePath += "/";
    basePath += UIUtils::getAssetTypeDisplayName(metadata.type);
    basePath += "/";
    basePath += metadata.name;
    basePath += ".json";
    return basePath;
}

// Asset management helpers
void UnifiedAssetGeneratorUI::addAssetToLibrary(const AssetMetadata& asset) {
    // Remove existing asset with same name
    removeAssetFromLibrary(asset.name);
    
    // Add new asset
    m_assetLibrary.push_back(asset);

    // Track it as the most recent asset
    m_recentAssets.erase(std::remove(m_recentAssets.begin(), m_recentAssets.end(), asset.name), m_recentAssets.end());
    m_recentAssets.insert(m_recentAssets.begin(), asset.name);
    if (m_recentAssets.size() > static_cast<size_t>(MAX_RECENT_ASSETS)) {
        m_recentAssets.resize(static_cast<size_t>(MAX_RECENT_ASSETS));
    }
}

void UnifiedAssetGeneratorUI::removeAssetFromLibrary(const std::string& assetName) {
    m_assetLibrary.erase(
        std::remove_if(m_assetLibrary.begin(), m_assetLibrary.end(),
                      [&](const AssetMetadata& asset) { return asset.name == assetName; }),
        m_assetLibrary.end()
    );
}

void UnifiedAssetGeneratorUI::updateAssetInLibrary(const AssetMetadata& asset) {
    auto existingAsset = findAssetInLibrary(asset.name);
    if (existingAsset) {
        *existingAsset = asset;
    } else {
        addAssetToLibrary(asset);
    }
}

AssetMetadata* UnifiedAssetGeneratorUI::findAssetInLibrary(const std::string& assetName) {
    for (auto& asset : m_assetLibrary) {
        if (asset.name == assetName) {
            return &asset;
        }
    }
    return nullptr;
}

// AssetGeneratorFactory Implementation
AssetGeneratorFactory& AssetGeneratorFactory::getInstance() {
    static AssetGeneratorFactory instance;
    return instance;
}

void AssetGeneratorFactory::registerGenerator(const std::string& name, GeneratorCreator creator) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators[name] = creator;
}

void AssetGeneratorFactory::unregisterGenerator(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_creators.erase(name);
}

std::unique_ptr<IAssetGenerator> AssetGeneratorFactory::createGenerator(const std::string& name) {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_creators.find(name);
    if (it != m_creators.end()) {
        return it->second();
    }
    return nullptr;
}

std::vector<std::string> AssetGeneratorFactory::getAvailableGenerators() const {
    std::lock_guard<std::mutex> lock(m_mutex);
    std::vector<std::string> names;
    for (const auto& pair : m_creators) {
        names.push_back(pair.first);
    }
    return names;
}

void AssetGeneratorFactory::registerCategoryGenerator(AssetCategory category, const std::string& generatorName) {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_categoryGenerators[category].push_back(generatorName);
}

std::vector<std::string> AssetGeneratorFactory::getGeneratorsForCategory(AssetCategory category) const {
    std::lock_guard<std::mutex> lock(m_mutex);
    auto it = m_categoryGenerators.find(category);
    if (it != m_categoryGenerators.end()) {
        return it->second;
    }
    return {};
}

// UIUtils Implementation
namespace UIUtils {
    std::string getCategoryDisplayName(AssetCategory category) {
        switch (category) {
            case AssetCategory::MECHS: return "Mechs";
            case AssetCategory::PROJECTILES: return "Projectiles";
            case AssetCategory::WEAPONS: return "Weapons";
            case AssetCategory::CREATURES: return "Creatures";
            case AssetCategory::EFFECTS: return "Effects";
            case AssetCategory::AUDIO: return "Audio";
            case AssetCategory::VISUAL: return "Visual";
            case AssetCategory::UTILITY: return "Utility";
            case AssetCategory::COSMETIC: return "Cosmetic";
            case AssetCategory::SYSTEM: return "System";
            default: return "Unknown";
        }
    }
    
    std::string getAssetTypeDisplayName(AssetType type) {
        switch (type) {
            // Mech types
            case AssetType::MECH_BASIC: return "Basic Mech";
            case AssetType::MECH_MINI_JET: return "Mini Jet";
            case AssetType::MECH_QUAD: return "Quad Mech";
            case AssetType::MECH_CENTIPEDE: return "Centipede Mech";
            case AssetType::MECH_WORM: return "Worm Mech";
            case AssetType::MECH_SNAKE: return "Snake Mech";
            
            // Projectile types
            case AssetType::PROJECTILE_BASIC: return "Basic Projectile";
            case AssetType::PROJECTILE_BLACKHOLE: return "Blackhole Projectile";
            case AssetType::PROJECTILE_LIGHTNING: return "Lightning Projectile";
            case AssetType::PROJECTILE_COMET: return "Comet Projectile";
            case AssetType::PROJECTILE_FLAME: return "Flame Projectile";
            case AssetType::PROJECTILE_GYRO: return "Gyro Projectile";
            case AssetType::PROJECTILE_ICE_SHARD: return "Ice Shard";
            case AssetType::PROJECTILE_EXPLOSIVE: return "Explosive Projectile";
            case AssetType::PROJECTILE_HOMING: return "Homing Missile";
            case AssetType::PROJECTILE_ACID: return "Acid Projectile";
            case AssetType::PROJECTILE_CLUSTER: return "Cluster Bomb";
            case AssetType::PROJECTILE_SHOTGUN: return "Shotgun Pellet";
            case AssetType::PROJECTILE_BOOMERANG: return "Boomerang Disc";
            
            // Weapon types
            case AssetType::WEAPON_SEGMENTED: return "Segmented Weapon";
            case AssetType::WEAPON_CROSSBOW: return "Crossbow";
            case AssetType::WEAPON_BEAM_NET: return "Beam Net";
            case AssetType::WEAPON_GRAPPLE_HOOK: return "Grapple Hook";
            
            // Effect types
            case AssetType::EFFECT_STATUS: return "Status Effect";
            case AssetType::EFFECT_VORTEX: return "Vortex Spell";
            case AssetType::EFFECT_FROST_NOVA: return "Frost Nova";
            case AssetType::EFFECT_PARTICLE_FIELD: return "Particle Field";
            case AssetType::EFFECT_PORTAL: return "Portal";
            
            // Launcher types
            case AssetType::LAUNCHER_ALCHEMICAL: return "Alchemical Launcher";
            case AssetType::GRENADE_ALCHEMICAL: return "Alchemical Grenade";
            case AssetType::GRENADE_GAS: return "Gas Grenade";
            
            // Creature types
            case AssetType::CREATURE_SEGMENTED: return "Segmented Creature";
            case AssetType::CREATURE_MONSTER: return "Monster";
            
            // Audio types
            case AssetType::AUDIO_ASSET: return "Audio Asset";
            
            // Visual types
            case AssetType::LIGHT: return "Light";
            case AssetType::TRAIL: return "Trail";
            case AssetType::PARTICLE: return "Particle";
            case AssetType::GEOMETRY: return "Geometry";
            case AssetType::ATLAS: return "Atlas";
            case AssetType::TEXTURE: return "Texture";
            case AssetType::MESH: return "Mesh";
            case AssetType::ANIMATION: return "Animation";
            case AssetType::SHADER: return "Shader";
            
            // UI types
            case AssetType::UI_ASSET: return "UI Asset";
            case AssetType::ICON_ASSET: return "Icon Asset";
            case AssetType::COCKPIT: return "Cockpit";
            
            // Utility types
            case AssetType::DAMAGE_SYSTEM: return "Damage System";
            case AssetType::INGREDIENT: return "Ingredient";
            case AssetType::SPELLSTONE: return "Spellstone";
            case AssetType::ROOM: return "Room";
            case AssetType::MAGICAL_ITEM: return "Magical Item";
            case AssetType::ORB: return "Orb";
            case AssetType::TRAP: return "Trap";
            
            // Cosmic types
            case AssetType::COSMIC: return "Cosmic";
            case AssetType::BEAM: return "Beam";
            case AssetType::SPELL: return "Spell";
            case AssetType::SNAKE_SPELL: return "Snake Spell";
            
            // System types
            case AssetType::DYNAMIC_ASSET: return "Dynamic Asset";
            case AssetType::PROCEDURAL: return "Procedural";
            case AssetType::FIREBALL: return "Fireball";
            case AssetType::PLASMA_DISC: return "Plasma Disc";
            case AssetType::DRONE_MINION: return "Drone Minion";
            
            default: return "Unknown";
        }
    }
    
    ImVec4 getCategoryColor(AssetCategory category) {
        switch (category) {
            case AssetCategory::MECHS: return ImVec4(0.8f, 0.4f, 0.2f, 1.0f);
            case AssetCategory::PROJECTILES: return ImVec4(0.2f, 0.6f, 0.8f, 1.0f);
            case AssetCategory::WEAPONS: return ImVec4(0.8f, 0.2f, 0.2f, 1.0f);
            case AssetCategory::CREATURES: return ImVec4(0.2f, 0.8f, 0.4f, 1.0f);
            case AssetCategory::EFFECTS: return ImVec4(0.8f, 0.2f, 0.8f, 1.0f);
            case AssetCategory::AUDIO: return ImVec4(0.8f, 0.8f, 0.2f, 1.0f);
            case AssetCategory::VISUAL: return ImVec4(0.2f, 0.8f, 0.8f, 1.0f);
            case AssetCategory::UTILITY: return ImVec4(0.6f, 0.6f, 0.6f, 1.0f);
            case AssetCategory::COSMETIC: return ImVec4(0.8f, 0.6f, 0.8f, 1.0f);
            case AssetCategory::SYSTEM: return ImVec4(0.4f, 0.4f, 0.4f, 1.0f);
            default: return ImVec4(0.5f, 0.5f, 0.5f, 1.0f);
        }
    }
    
    ImVec4 getAssetTypeColor(AssetType type) {
        // Use category colors for asset types
        AssetCategory category;
        switch (type) {
            case AssetType::MECH_BASIC:
            case AssetType::MECH_MINI_JET:
            case AssetType::MECH_QUAD:
            case AssetType::MECH_CENTIPEDE:
            case AssetType::MECH_WORM:
            case AssetType::MECH_SNAKE:
                category = AssetCategory::MECHS;
                break;
            case AssetType::PROJECTILE_BASIC:
            case AssetType::PROJECTILE_BLACKHOLE:
            case AssetType::PROJECTILE_LIGHTNING:
            case AssetType::PROJECTILE_COMET:
            case AssetType::PROJECTILE_FLAME:
            case AssetType::PROJECTILE_GYRO:
            case AssetType::PROJECTILE_ICE_SHARD:
            case AssetType::PROJECTILE_EXPLOSIVE:
            case AssetType::PROJECTILE_HOMING:
            case AssetType::PROJECTILE_ACID:
            case AssetType::PROJECTILE_CLUSTER:
            case AssetType::PROJECTILE_SHOTGUN:
            case AssetType::PROJECTILE_BOOMERANG:
                category = AssetCategory::PROJECTILES;
                break;
            default:
                category = AssetCategory::UTILITY;
                break;
        }
        return getCategoryColor(category);
    }
    
    std::string getAssetTypeIcon(AssetType type) {
        // Return appropriate icon for asset type
        switch (type) {
            case AssetType::MECH_BASIC: return "🤖";
            case AssetType::PROJECTILE_BASIC: return "⚡";
            case AssetType::WEAPON_SEGMENTED: return "⚔️";
            case AssetType::EFFECT_STATUS: return "✨";
            case AssetType::AUDIO_ASSET: return "🎵";
            case AssetType::LIGHT: return "💡";
            case AssetType::TRAIL: return "🌊";
            case AssetType::PARTICLE: return "✨";
            case AssetType::GEOMETRY: return "📐";
            case AssetType::TEXTURE: return "🖼️";
            case AssetType::MESH: return "🔷";
            case AssetType::ANIMATION: return "🎬";
            case AssetType::SHADER: return "🎨";
            case AssetType::UI_ASSET: return "🖥️";
            case AssetType::ICON_ASSET: return "📱";
            case AssetType::COCKPIT: return "🚁";
            default: return "📦";
        }
    }
    
    bool isValidAssetName(const std::string& name) {
        if (name.empty()) return false;
        
        // Check for invalid characters
        const std::string invalidChars = "<>:\"|?*\\/";
        for (char c : name) {
            if (invalidChars.find(c) != std::string::npos) {
                return false;
            }
        }
        
        return true;
    }
    
    std::string sanitizeAssetName(const std::string& name) {
        std::string sanitized = name;
        const std::string invalidChars = "<>:\"|?*\\/";
        
        for (char& c : sanitized) {
            if (invalidChars.find(c) != std::string::npos) {
                c = '_';
            }
        }
        
        return sanitized;
    }
    
    std::string generateUniqueAssetName(AssetType type, const std::string& baseName) {
        std::string prefix = getAssetTypeDisplayName(type);
        std::transform(prefix.begin(), prefix.end(), prefix.begin(), ::tolower);
        std::replace(prefix.begin(), prefix.end(), ' ', '_');
        
        if (baseName.empty()) {
            auto now = std::chrono::system_clock::now();
            auto duration = now.time_since_epoch();
            auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(duration).count();
            return prefix + "_" + std::to_string(millis);
        } else {
            return prefix + "_" + sanitizeAssetName(baseName);
        }
    }
}

} // namespace AssetGen
} // namespace MagiTech 
