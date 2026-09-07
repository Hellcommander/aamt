#include "ColorPickerSystem.hpp"
#include "core/Log.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <chrono>
#include <thread>

namespace MagiTech {
namespace ColorPicker {

// ColorPalettePluginManager implementation
ColorPalettePluginManager& ColorPalettePluginManager::instance() {
    static ColorPalettePluginManager instance;
    return instance;
}

bool ColorPalettePluginManager::loadPlugin(const std::string& pluginPath) {
    std::filesystem::path path(pluginPath);
    std::string extension = path.extension().string();
    
    if (extension == ".so" || extension == ".dll" || extension == ".dylib") {
        return loadCppPlugin(pluginPath);
    } else if (extension == ".lua") {
        return loadLuaPluginInternal(pluginPath);
    } else {
        Log::error("Unsupported plugin type: {}", extension);
        return false;
    }
}

bool ColorPalettePluginManager::loadLuaPlugin(const std::string& scriptPath) {
    return loadLuaPluginInternal(scriptPath);
}

bool ColorPalettePluginManager::unloadPlugin(const std::string& pluginName) {
    auto it = m_plugins.find(pluginName);
    if (it == m_plugins.end()) {
        Log::warning("Plugin not found: {}", pluginName);
        return false;
    }
    
    PluginInfo& info = it->second;
    if (info.plugin) {
        info.plugin->shutdown();
    }
    
    if (info.handle) {
        dlclose(info.handle);
    }
    
    m_plugins.erase(it);
    Log::info("Plugin unloaded: {}", pluginName);
    return true;
}

void ColorPalettePluginManager::unloadAllPlugins() {
    for (auto& [name, info] : m_plugins) {
        if (info.plugin) {
            info.plugin->shutdown();
        }
        if (info.handle) {
            dlclose(info.handle);
        }
    }
    m_plugins.clear();
    Log::info("All plugins unloaded");
}

void ColorPalettePluginManager::scanForPlugins(const std::string& directory) {
    if (!std::filesystem::exists(directory)) {
        Log::warning("Plugin directory does not exist: {}", directory);
        return;
    }
    
    std::vector<std::string> pluginFiles = PluginUtils::findPluginFiles(directory, ".so");
    auto luaFiles = PluginUtils::findPluginFiles(directory, ".lua");
    pluginFiles.insert(pluginFiles.end(), luaFiles.begin(), luaFiles.end());
    
    for (const auto& pluginFile : pluginFiles) {
        if (PluginUtils::isValidPluginFile(pluginFile)) {
            loadPlugin(pluginFile);
        }
    }
    
    Log::info("Scanned {} plugin files in {}", pluginFiles.size(), directory);
}

std::vector<std::string> ColorPalettePluginManager::getLoadedPluginNames() const {
    std::vector<std::string> names;
    for (const auto& [name, info] : m_plugins) {
        names.push_back(name);
    }
    return names;
}

std::vector<std::string> ColorPalettePluginManager::getAvailablePluginPaths() const {
    std::vector<std::string> paths;
    for (const auto& [name, info] : m_plugins) {
        paths.push_back(info.path);
    }
    return paths;
}

std::string ColorPalettePluginManager::getPluginInfo(const std::string& pluginName) const {
    auto it = m_plugins.find(pluginName);
    if (it == m_plugins.end()) {
        return "Plugin not found";
    }
    
    const PluginInfo& info = it->second;
    std::ostringstream oss;
    oss << "Name: " << info.name << "\n";
    oss << "Path: " << info.path << "\n";
    oss << "Type: " << info.type << "\n";
    oss << "Enabled: " << (info.enabled ? "Yes" : "No") << "\n";
    oss << "Capabilities: ";
    for (const auto& [capability, supported] : info.capabilities) {
        oss << capability << "(" << (supported ? "Yes" : "No") << ") ";
    }
    
    return oss.str();
}

bool ColorPalettePluginManager::isPluginEnabled(const std::string& pluginName) const {
    auto it = m_plugins.find(pluginName);
    return it != m_plugins.end() && it->second.enabled;
}

void ColorPalettePluginManager::setPluginEnabled(const std::string& pluginName, bool enabled) {
    auto it = m_plugins.find(pluginName);
    if (it != m_plugins.end()) {
        it->second.enabled = enabled;
        if (it->second.plugin) {
            if (enabled) {
                it->second.plugin->initialize();
            } else {
                it->second.plugin->shutdown();
            }
        }
    }
}

std::vector<std::string> ColorPalettePluginManager::getAllAvailablePalettes() const {
    std::vector<std::string> allPalettes;
    for (const auto& [name, info] : m_plugins) {
        if (info.enabled && info.plugin) {
            auto palettes = info.plugin->getAvailablePalettes();
            allPalettes.insert(allPalettes.end(), palettes.begin(), palettes.end());
        }
    }
    return allPalettes;
}

ColorPalette ColorPalettePluginManager::loadPaletteFromPlugin(const std::string& pluginName, const std::string& paletteName) {
    auto it = m_plugins.find(pluginName);
    if (it == m_plugins.end() || !it->second.enabled || !it->second.plugin) {
        return ColorPalette();
    }
    
    return it->second.plugin->loadPalette(paletteName);
}

std::vector<ColorPalette> ColorPalettePluginManager::generatePalettesFromPlugin(const std::string& pluginName, const std::string& context) {
    auto it = m_plugins.find(pluginName);
    if (it == m_plugins.end() || !it->second.enabled || !it->second.plugin) {
        return {};
    }
    
    return it->second.plugin->generatePalettes(context);
}

std::vector<std::string> ColorPalettePluginManager::getPluginsWithCapability(const std::string& capability) const {
    std::vector<std::string> plugins;
    for (const auto& [name, info] : m_plugins) {
        if (info.enabled && info.capabilities.count(capability) && info.capabilities.at(capability)) {
            plugins.push_back(name);
        }
    }
    return plugins;
}

bool ColorPalettePluginManager::hasPluginWithCapability(const std::string& capability) const {
    return !getPluginsWithCapability(capability).empty();
}

void ColorPalettePluginManager::enableHotReloading(bool enable) {
    m_hotReloadEnabled = enable;
    if (enable && !m_hotReloadThread.joinable()) {
        m_hotReloadThread = std::thread(&ColorPalettePluginManager::hotReloadWorker, this);
    }
}

void ColorPalettePluginManager::checkForPluginUpdates() {
    for (auto& [name, info] : m_plugins) {
        if (hasPluginChanged(info)) {
            Log::info("Plugin changed, reloading: {}", name);
            reloadPlugin(name);
        }
    }
}

void ColorPalettePluginManager::reloadModifiedPlugins() {
    checkForPluginUpdates();
}

bool ColorPalettePluginManager::loadCppPlugin(const std::string& path) {
    void* handle = dlopen(path.c_str(), RTLD_LAZY);
    if (!handle) {
        Log::error("Failed to load plugin: {} - {}", path, dlerror());
        return false;
    }
    
    // Get plugin creation function
    using CreatePluginFunc = IColorPalettePlugin* (*)();
    auto createPlugin = reinterpret_cast<CreatePluginFunc>(dlsym(handle, "createColorPalettePlugin"));
    if (!createPlugin) {
        Log::error("Failed to find createColorPalettePlugin function in: {}", path);
        dlclose(handle);
        return false;
    }
    
    // Create plugin instance
    auto plugin = std::shared_ptr<IColorPalettePlugin>(createPlugin());
    if (!plugin) {
        Log::error("Failed to create plugin instance: {}", path);
        dlclose(handle);
        return false;
    }
    
    // Initialize plugin
    if (!plugin->initialize()) {
        Log::error("Failed to initialize plugin: {}", path);
        dlclose(handle);
        return false;
    }
    
    // Create plugin info
    PluginInfo info;
    info.name = plugin->getName();
    info.path = path;
    info.type = "cpp";
    info.handle = handle;
    info.plugin = plugin;
    info.enabled = true;
    info.lastModified = std::filesystem::last_write_time(path);
    
    initializePluginCapabilities(info);
    
    m_plugins[info.name] = std::move(info);
    Log::info("C++ plugin loaded: {} ({})", info.name, path);
    return true;
}

bool ColorPalettePluginManager::loadLuaPluginInternal(const std::string& path) {
    auto plugin = std::make_shared<LuaColorPalettePlugin>(path);
    if (!plugin->initialize()) {
        Log::error("Failed to initialize Lua plugin: {}", path);
        return false;
    }
    
    // Create plugin info
    PluginInfo info;
    info.name = plugin->getName();
    info.path = path;
    info.type = "lua";
    info.handle = nullptr;
    info.plugin = plugin;
    info.enabled = true;
    info.lastModified = std::filesystem::last_write_time(path);
    
    initializePluginCapabilities(info);
    
    m_plugins[info.name] = std::move(info);
    Log::info("Lua plugin loaded: {} ({})", info.name, path);
    return true;
}

void ColorPalettePluginManager::initializePluginCapabilities(PluginInfo& info) {
    if (!info.plugin) return;
    
    info.capabilities["dynamic_generation"] = info.plugin->supportsDynamicGeneration();
    info.capabilities["mood_based_generation"] = info.plugin->supportsMoodBasedGeneration();
    info.capabilities["theme_based_generation"] = info.plugin->supportsThemeBasedGeneration();
    info.capabilities["real_time_generation"] = info.plugin->supportsRealTimeGeneration();
}

void ColorPalettePluginManager::hotReloadWorker() {
    while (m_hotReloadEnabled) {
        checkForPluginUpdates();
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}

bool ColorPalettePluginManager::hasPluginChanged(const PluginInfo& info) const {
    if (!std::filesystem::exists(info.path)) {
        return false;
    }
    
    auto currentModified = std::filesystem::last_write_time(info.path);
    return currentModified > info.lastModified;
}

void ColorPalettePluginManager::reloadPlugin(const std::string& pluginName) {
    auto it = m_plugins.find(pluginName);
    if (it == m_plugins.end()) {
        return;
    }
    
    std::string path = it->second.path;
    unloadPlugin(pluginName);
    loadPlugin(path);
}

// LuaColorPalettePlugin implementation
LuaColorPalettePlugin::LuaColorPalettePlugin(const std::string& scriptPath) 
    : m_scriptPath(scriptPath), m_enabled(false), m_initialized(false), m_luaState(nullptr) {
}

LuaColorPalettePlugin::~LuaColorPalettePlugin() {
    shutdown();
}

std::string LuaColorPalettePlugin::getName() const {
    return m_name;
}

std::string LuaColorPalettePlugin::getVersion() const {
    return m_version;
}

std::string LuaColorPalettePlugin::getAuthor() const {
    return m_author;
}

std::string LuaColorPalettePlugin::getDescription() const {
    return m_description;
}

bool LuaColorPalettePlugin::initialize() {
    if (m_initialized) {
        return true;
    }
    
    if (!initializeLuaState()) {
        return false;
    }
    
    // Load and execute the Lua script
    if (luaL_dofile(m_luaState, m_scriptPath.c_str()) != 0) {
        m_lastError = lua_tostring(m_luaState, -1);
        Log::error("Failed to load Lua script: {} - {}", m_scriptPath, m_lastError);
        return false;
    }
    
    // Extract plugin metadata
    m_name = getLuaString("plugin_name");
    m_version = getLuaString("plugin_version");
    m_author = getLuaString("plugin_author");
    m_description = getLuaString("plugin_description");
    
    if (m_name.empty()) {
        m_name = std::filesystem::path(m_scriptPath).stem().string();
    }
    
    m_enabled = true;
    m_initialized = true;
    return true;
}

void LuaColorPalettePlugin::shutdown() {
    if (m_initialized) {
        cleanupLuaState();
        m_initialized = false;
        m_enabled = false;
    }
}

bool LuaColorPalettePlugin::isEnabled() const {
    return m_enabled;
}

std::vector<std::string> LuaColorPalettePlugin::getAvailablePalettes() const {
    if (!m_initialized) return {};
    return getLuaStringArray("available_palettes");
}

ColorPalette LuaColorPalettePlugin::loadPalette(const std::string& name) {
    if (!m_initialized) return ColorPalette();
    
    // Call Lua function to load palette
    lua_getglobal(m_luaState, "load_palette");
    lua_pushstring(m_luaState, name.c_str());
    
    if (lua_pcall(m_luaState, 1, 1, 0) != 0) {
        m_lastError = lua_tostring(m_luaState, -1);
        return ColorPalette();
    }
    
    return getLuaColorPalette("loaded_palette");
}

bool LuaColorPalettePlugin::savePalette(const ColorPalette& palette) {
    if (!m_initialized) return false;
    
    // Convert palette to Lua table and call save function
    lua_getglobal(m_luaState, "save_palette");
    // Push palette data to Lua stack
    // Implementation depends on how palette data is structured
    
    return callLuaFunction("save_palette");
}

bool LuaColorPalettePlugin::deletePalette(const std::string& name) {
    if (!m_initialized) return false;
    return callLuaFunctionWithString("delete_palette", name);
}

std::vector<ColorPalette> LuaColorPalettePlugin::generatePalettes(const std::string& context) {
    if (!m_initialized) return {};
    return getLuaColorPaletteArray("generated_palettes");
}

ColorPalette LuaColorPalettePlugin::generatePaletteFromMood(const std::string& mood) {
    if (!m_initialized) return ColorPalette();
    return getLuaColorPalette("mood_palette");
}

ColorPalette LuaColorPalettePlugin::generatePaletteFromTheme(const std::string& theme) {
    if (!m_initialized) return ColorPalette();
    return getLuaColorPalette("theme_palette");
}

bool LuaColorPalettePlugin::supportsDynamicGeneration() const {
    if (!m_initialized) return false;
    return callLuaFunction("supports_dynamic_generation");
}

bool LuaColorPalettePlugin::supportsMoodBasedGeneration() const {
    if (!m_initialized) return false;
    return callLuaFunction("supports_mood_based_generation");
}

bool LuaColorPalettePlugin::supportsThemeBasedGeneration() const {
    if (!m_initialized) return false;
    return callLuaFunction("supports_theme_based_generation");
}

bool LuaColorPalettePlugin::supportsRealTimeGeneration() const {
    if (!m_initialized) return false;
    return callLuaFunction("supports_real_time_generation");
}

void LuaColorPalettePlugin::reloadScript() {
    shutdown();
    initialize();
}

bool LuaColorPalettePlugin::isScriptValid() const {
    return m_initialized && m_enabled;
}

std::string LuaColorPalettePlugin::getLastError() const {
    return m_lastError;
}

bool LuaColorPalettePlugin::initializeLuaState() {
    // Initialize Lua state (implementation depends on Lua version)
    // This is a simplified version - in practice you'd use the actual Lua C API
    m_luaState = nullptr; // luaL_newstate();
    if (!m_luaState) {
        m_lastError = "Failed to create Lua state";
        return false;
    }
    
    // Open standard libraries
    // luaL_openlibs(m_luaState);
    return true;
}

void LuaColorPalettePlugin::cleanupLuaState() {
    if (m_luaState) {
        // lua_close(m_luaState);
        m_luaState = nullptr;
    }
}

bool LuaColorPalettePlugin::callLuaFunction(const std::string& functionName) {
    if (!m_luaState) return false;
    
    lua_getglobal(m_luaState, functionName.c_str());
    if (!lua_isfunction(m_luaState, -1)) {
        return false;
    }
    
    if (lua_pcall(m_luaState, 0, 1, 0) != 0) {
        m_lastError = lua_tostring(m_luaState, -1);
        return false;
    }
    
    bool result = lua_toboolean(m_luaState, -1);
    lua_pop(m_luaState, 1);
    return result;
}

bool LuaColorPalettePlugin::callLuaFunctionWithString(const std::string& functionName, const std::string& param) {
    if (!m_luaState) return false;
    
    lua_getglobal(m_luaState, functionName.c_str());
    if (!lua_isfunction(m_luaState, -1)) {
        return false;
    }
    
    lua_pushstring(m_luaState, param.c_str());
    
    if (lua_pcall(m_luaState, 1, 1, 0) != 0) {
        m_lastError = lua_tostring(m_luaState, -1);
        return false;
    }
    
    bool result = lua_toboolean(m_luaState, -1);
    lua_pop(m_luaState, 1);
    return result;
}

std::string LuaColorPalettePlugin::getLuaString(const std::string& variableName) {
    if (!m_luaState) return "";
    
    lua_getglobal(m_luaState, variableName.c_str());
    if (!lua_isstring(m_luaState, -1)) {
        lua_pop(m_luaState, 1);
        return "";
    }
    
    std::string result = lua_tostring(m_luaState, -1);
    lua_pop(m_luaState, 1);
    return result;
}

std::vector<std::string> LuaColorPalettePlugin::getLuaStringArray(const std::string& variableName) {
    std::vector<std::string> result;
    if (!m_luaState) return result;
    
    lua_getglobal(m_luaState, variableName.c_str());
    if (!lua_istable(m_luaState, -1)) {
        lua_pop(m_luaState, 1);
        return result;
    }
    
    lua_pushnil(m_luaState);
    while (lua_next(m_luaState, -2) != 0) {
        if (lua_isstring(m_luaState, -1)) {
            result.push_back(lua_tostring(m_luaState, -1));
        }
        lua_pop(m_luaState, 1);
    }
    lua_pop(m_luaState, 1);
    
    return result;
}

ColorPalette LuaColorPalettePlugin::getLuaColorPalette(const std::string& variableName) {
    // Implementation to convert Lua table to ColorPalette
    // This would involve reading the palette data from Lua and constructing a ColorPalette
    return ColorPalette();
}

std::vector<ColorPalette> LuaColorPalettePlugin::getLuaColorPaletteArray(const std::string& variableName) {
    // Implementation to convert Lua table array to vector of ColorPalette
    return {};
}

// PluginUtils implementation
namespace PluginUtils {
    
std::vector<std::string> findPluginFiles(const std::string& directory, const std::string& extension) {
    std::vector<std::string> files;
    
    try {
        for (const auto& entry : std::filesystem::recursive_directory_iterator(directory)) {
            if (entry.is_regular_file() && entry.path().extension() == extension) {
                files.push_back(entry.path().string());
            }
        }
    } catch (const std::filesystem::filesystem_error& e) {
        Log::error("Error scanning plugin directory: {}", e.what());
    }
    
    return files;
}

bool isValidPluginFile(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".so" || extension == ".dll" || extension == ".dylib") {
        return validateCppPlugin(filePath);
    } else if (extension == ".lua") {
        return validateLuaPlugin(filePath);
    }
    
    return false;
}

std::string getPluginType(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".so" || extension == ".dll" || extension == ".dylib") {
        return "cpp";
    } else if (extension == ".lua") {
        return "lua";
    }
    
    return "unknown";
}

bool validateCppPlugin(const std::string& filePath) {
    void* handle = dlopen(filePath.c_str(), RTLD_LAZY);
    if (!handle) {
        return false;
    }
    
    // Check for required symbols
    auto createFunc = dlsym(handle, "createColorPalettePlugin");
    auto getNameFunc = dlsym(handle, "getPluginName");
    
    dlclose(handle);
    
    return createFunc != nullptr && getNameFunc != nullptr;
}

bool validateLuaPlugin(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        return false;
    }
    
    std::string line;
    bool hasPluginName = false;
    bool hasPluginVersion = false;
    
    while (std::getline(file, line)) {
        if (line.find("plugin_name") != std::string::npos) {
            hasPluginName = true;
        }
        if (line.find("plugin_version") != std::string::npos) {
            hasPluginVersion = true;
        }
    }
    
    return hasPluginName && hasPluginVersion;
}

std::string getPluginValidationError(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".so" || extension == ".dll" || extension == ".dylib") {
        void* handle = dlopen(filePath.c_str(), RTLD_LAZY);
        if (!handle) {
            return "Failed to load dynamic library: " + std::string(dlerror());
        }
        
        auto createFunc = dlsym(handle, "createColorPalettePlugin");
        if (!createFunc) {
            dlclose(handle);
            return "Missing createColorPalettePlugin function";
        }
        
        auto getNameFunc = dlsym(handle, "getPluginName");
        if (!getNameFunc) {
            dlclose(handle);
            return "Missing getPluginName function";
        }
        
        dlclose(handle);
        return "";
    } else if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return "Failed to open Lua script file";
        }
        
        std::string content((std::istreambuf_iterator<char>(file)),
                           std::istreambuf_iterator<char>());
        
        if (content.find("plugin_name") == std::string::npos) {
            return "Missing plugin_name variable";
        }
        if (content.find("plugin_version") == std::string::npos) {
            return "Missing plugin_version variable";
        }
        
        return "";
    }
    
    return "Unsupported plugin type";
}

std::string extractPluginName(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".so" || extension == ".dll" || extension == ".dylib") {
        void* handle = dlopen(filePath.c_str(), RTLD_LAZY);
        if (!handle) {
            return "";
        }
        
        auto getNameFunc = reinterpret_cast<const char* (*)()>(dlsym(handle, "getPluginName"));
        if (!getNameFunc) {
            dlclose(handle);
            return "";
        }
        
        std::string name = getNameFunc();
        dlclose(handle);
        return name;
    } else if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return "";
        }
        
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("plugin_name") != std::string::npos) {
                size_t start = line.find('"');
                size_t end = line.find('"', start + 1);
                if (start != std::string::npos && end != std::string::npos) {
                    return line.substr(start + 1, end - start - 1);
                }
            }
        }
    }
    
    return std::filesystem::path(filePath).stem().string();
}

std::string extractPluginVersion(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return "";
        }
        
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("plugin_version") != std::string::npos) {
                size_t start = line.find('"');
                size_t end = line.find('"', start + 1);
                if (start != std::string::npos && end != std::string::npos) {
                    return line.substr(start + 1, end - start - 1);
                }
            }
        }
    }
    
    return "1.0.0";
}

std::string extractPluginAuthor(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return "";
        }
        
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("plugin_author") != std::string::npos) {
                size_t start = line.find('"');
                size_t end = line.find('"', start + 1);
                if (start != std::string::npos && end != std::string::npos) {
                    return line.substr(start + 1, end - start - 1);
                }
            }
        }
    }
    
    return "Unknown";
}

std::string extractPluginDescription(const std::string& filePath) {
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return "";
        }
        
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("plugin_description") != std::string::npos) {
                size_t start = line.find('"');
                size_t end = line.find('"', start + 1);
                if (start != std::string::npos && end != std::string::npos) {
                    return line.substr(start + 1, end - start - 1);
                }
            }
        }
    }
    
    return "No description available";
}

std::vector<std::string> detectPluginCapabilities(const std::string& filePath) {
    std::vector<std::string> capabilities;
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return capabilities;
        }
        
        std::string content((std::istreambuf_iterator<char>(file)),
                           std::istreambuf_iterator<char>());
        
        if (content.find("supports_dynamic_generation") != std::string::npos) {
            capabilities.push_back("dynamic_generation");
        }
        if (content.find("supports_mood_based_generation") != std::string::npos) {
            capabilities.push_back("mood_based_generation");
        }
        if (content.find("supports_theme_based_generation") != std::string::npos) {
            capabilities.push_back("theme_based_generation");
        }
        if (content.find("supports_real_time_generation") != std::string::npos) {
            capabilities.push_back("real_time_generation");
        }
    }
    
    return capabilities;
}

bool hasPluginCapability(const std::string& filePath, const std::string& capability) {
    auto capabilities = detectPluginCapabilities(filePath);
    return std::find(capabilities.begin(), capabilities.end(), capability) != capabilities.end();
}

bool backupPlugin(const std::string& filePath) {
    std::filesystem::path path(filePath);
    std::filesystem::path backupPath = path.parent_path() / (path.stem().string() + "_backup" + path.extension().string());
    
    try {
        std::filesystem::copy_file(filePath, backupPath, std::filesystem::copy_options::overwrite_existing);
        return true;
    } catch (const std::filesystem::filesystem_error& e) {
        Log::error("Failed to backup plugin: {}", e.what());
        return false;
    }
}

bool restorePlugin(const std::string& filePath) {
    std::filesystem::path path(filePath);
    std::filesystem::path backupPath = path.parent_path() / (path.stem().string() + "_backup" + path.extension().string());
    
    if (!std::filesystem::exists(backupPath)) {
        return false;
    }
    
    try {
        std::filesystem::copy_file(backupPath, path, std::filesystem::copy_options::overwrite_existing);
        return true;
    } catch (const std::filesystem::filesystem_error& e) {
        Log::error("Failed to restore plugin: {}", e.what());
        return false;
    }
}

bool updatePlugin(const std::string& filePath, const std::string& newVersion) {
    // Implementation would depend on the update mechanism
    // This is a placeholder for plugin update functionality
    return false;
}

std::vector<std::string> getPluginDependencies(const std::string& filePath) {
    std::vector<std::string> dependencies;
    std::string extension = std::filesystem::path(filePath).extension().string();
    
    if (extension == ".lua") {
        std::ifstream file(filePath);
        if (!file.is_open()) {
            return dependencies;
        }
        
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("require") != std::string::npos) {
                size_t start = line.find('"');
                size_t end = line.find('"', start + 1);
                if (start != std::string::npos && end != std::string::npos) {
                    dependencies.push_back(line.substr(start + 1, end - start - 1));
                }
            }
        }
    }
    
    return dependencies;
}

bool checkPluginDependencies(const std::string& filePath) {
    auto dependencies = getPluginDependencies(filePath);
    for (const auto& dep : dependencies) {
        // Check if dependency is available
        // Implementation depends on how dependencies are managed
    }
    return true;
}

bool resolvePluginDependencies(const std::string& filePath) {
    // Implementation would attempt to resolve missing dependencies
    // This is a placeholder for dependency resolution
    return checkPluginDependencies(filePath);
}

} // namespace PluginUtils

// PluginConfig implementation
namespace PluginConfig {

PluginSettings loadSettings(const std::string& configPath) {
    PluginSettings settings;
    
    std::ifstream file(configPath);
    if (!file.is_open()) {
        return settings;
    }
    
    nlohmann::json j;
    file >> j;
    
    settings.enableHotReloading = j.value("enableHotReloading", true);
    settings.enableAsyncLoading = j.value("enableAsyncLoading", true);
    settings.enablePluginValidation = j.value("enablePluginValidation", true);
    settings.enableDependencyChecking = j.value("enableDependencyChecking", true);
    settings.pluginDirectory = j.value("pluginDirectory", "plugins/color_palettes");
    
    if (j.contains("enabledPlugins")) {
        settings.enabledPlugins = j["enabledPlugins"].get<std::vector<std::string>>();
    }
    
    if (j.contains("disabledPlugins")) {
        settings.disabledPlugins = j["disabledPlugins"].get<std::vector<std::string>>();
    }
    
    if (j.contains("pluginOptions")) {
        settings.pluginOptions = j["pluginOptions"].get<std::map<std::string, std::map<std::string, std::string>>>();
    }
    
    return settings;
}

void saveSettings(const PluginSettings& settings, const std::string& configPath) {
    nlohmann::json j;
    
    j["enableHotReloading"] = settings.enableHotReloading;
    j["enableAsyncLoading"] = settings.enableAsyncLoading;
    j["enablePluginValidation"] = settings.enablePluginValidation;
    j["enableDependencyChecking"] = settings.enableDependencyChecking;
    j["pluginDirectory"] = settings.pluginDirectory;
    j["enabledPlugins"] = settings.enabledPlugins;
    j["disabledPlugins"] = settings.disabledPlugins;
    j["pluginOptions"] = settings.pluginOptions;
    
    std::ofstream file(configPath);
    if (file.is_open()) {
        file << j.dump(2);
    }
}

void applySettings(const PluginSettings& settings) {
    auto& pluginManager = ColorPalettePluginManager::instance();
    
    pluginManager.enableHotReloading(settings.enableHotReloading);
    
    // Apply enabled/disabled plugin lists
    for (const auto& pluginName : settings.enabledPlugins) {
        pluginManager.setPluginEnabled(pluginName, true);
    }
    
    for (const auto& pluginName : settings.disabledPlugins) {
        pluginManager.setPluginEnabled(pluginName, false);
    }
}

} // namespace PluginConfig

} // namespace ColorPicker
} // namespace MagiTech 
