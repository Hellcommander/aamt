#include "GeneratorAgent.hpp"
#include "core/utils/BlazeJsonHelper.hpp"
#include "core/utils/JsonHelper.hpp"
#include "core/utils/SafeCall.hpp"
#include "core/utils/EventPatternMatcher.hpp"
#include "core/plugins/AdaptiveBusPlugin.hpp"
#include <chrono>
#include <thread>
#include <filesystem>
#include <fstream>
#include <algorithm>
#include <random>

namespace MagiTech::GeneratorAgent {

GeneratorAgent::GeneratorAgent() 
    : m_lastMetricsTime(std::chrono::high_resolution_clock::now()) {
    // Initialize with default configuration
    m_config = AgentConfig{};
    m_stats = AgentStats{};
}

GeneratorAgent::~GeneratorAgent() {
    shutdown();
}

void GeneratorAgent::init() {
    if (m_initialized) {
        return;
    }

    try {
        initializeSystems();
        setupEventHandlers();
        setupAdvancedFeatures();
        validateConfiguration();
        m_initialized = true;
        
        // Log initialization
        logError("GeneratorAgent initialized successfully");
    } catch (const std::exception& e) {
        logError("Failed to initialize GeneratorAgent: " + std::string(e.what()));
        throw;
    }
}

void GeneratorAgent::shutdown() {
    if (!m_initialized) {
        return;
    }

    try {
        stopWatching();
        cleanupAdvancedFeatures();
        cleanupEventHandlers();
        shutdownSystems();
        clearCache();
        m_initialized = false;
        
        // Log shutdown
        logError("GeneratorAgent shutdown completed");
    } catch (const std::exception& e) {
        logError("Error during GeneratorAgent shutdown: " + std::string(e.what()));
    }
}

void GeneratorAgent::registerBindings(sol::state& lua) {
    // Register enums
    lua.new_enum("SynthesisGoalType",
        "Power", "Style", "Hybrid"
    );

    // Register structs
    lua.new_usertype<SynthesisGoal>("SynthesisGoal",
        "targetPower", &SynthesisGoal::targetPower,
        "styleTags", &SynthesisGoal::styleTags
    );

    lua.new_usertype<AgentConfig>("GeneratorAgentConfig",
        "enableSpellGeneration", &AgentConfig::enableSpellGeneration,
        "enableSynthesis", &AgentConfig::enableSynthesis,
        "enableGeneticEvolution", &AgentConfig::enableGeneticEvolution,
        "enableGrammarEngine", &AgentConfig::enableGrammarEngine,
        "enableHotReload", &AgentConfig::enableHotReload,
        "enablePatternMatching", &AgentConfig::enablePatternMatching,
        "enableLuaFactories", &AgentConfig::enableLuaFactories,
        "enableCppFactories", &AgentConfig::enableCppFactories,
        "maxConcurrentGenerations", &AgentConfig::maxConcurrentGenerations,
        "geneticPopulationSize", &AgentConfig::geneticPopulationSize,
        "geneticGenerations", &AgentConfig::geneticGenerations,
        "grammarMaxDepth", &AgentConfig::grammarMaxDepth,
        "defaultManifestPath", &AgentConfig::defaultManifestPath,
        "synthesisRulesPath", &AgentConfig::synthesisRulesPath,
        "grammarRulesPath", &AgentConfig::grammarRulesPath,
        "watchIntervalMs", &AgentConfig::watchIntervalMs,
        "enableFileWatching", &AgentConfig::enableFileWatching
    );

    lua.new_usertype<AgentStats>("GeneratorAgentStats",
        "totalSpellsGenerated", &AgentStats::totalSpellsGenerated,
        "successfulGenerations", &AgentStats::successfulGenerations,
        "failedGenerations", &AgentStats::failedGenerations,
        "synthesisAttempts", &AgentStats::synthesisAttempts,
        "geneticEvolutions", &AgentStats::geneticEvolutions,
        "averageGenerationTimeMs", &AgentStats::averageGenerationTimeMs,
        "averageSynthesisTimeMs", &AgentStats::averageSynthesisTimeMs,
        "averageEvolutionTimeMs", &AgentStats::averageEvolutionTimeMs,
        "cacheHits", &AgentStats::cacheHits,
        "cacheMisses", &AgentStats::cacheMisses,
        "cacheSize", &AgentStats::cacheSize,
        "syntaxErrors", &AgentStats::syntaxErrors,
        "semanticErrors", &AgentStats::semanticErrors,
        "factoryErrors", &AgentStats::factoryErrors,
        "reset", &AgentStats::reset
    );

    // Register GeneratorAgent class
    lua.new_usertype<GeneratorAgent>("GeneratorAgent",
        // Constructor
        sol::constructors<GeneratorAgent()>(),
        
        // IMagiTechModule methods
        "init", &GeneratorAgent::init,
        "shutdown", &GeneratorAgent::shutdown,
        "registerBindings", &GeneratorAgent::registerBindings,
        
        // Configuration
        "setConfig", &GeneratorAgent::setConfig,
        "getConfig", &GeneratorAgent::getConfig,
        
        // Core generation
        "generateSpell", &GeneratorAgent::generateSpell,
        "generateSpellFromDefinition", &GeneratorAgent::generateSpellFromDefinition,
        "getAvailableSpellIds", &GeneratorAgent::getAvailableSpellIds,
        "hasSpell", &GeneratorAgent::hasSpell,
        
        // Factory registration
        "registerCppFactory", &GeneratorAgent::registerCppFactory,
        "registerLuaFactory", &GeneratorAgent::registerLuaFactory,
        "registerPatternFactory", &GeneratorAgent::registerPatternFactory,
        "registerLuaPattern", &GeneratorAgent::registerLuaPattern,
        
        // Manifest management
        "loadManifest", &GeneratorAgent::loadManifest,
        "reloadManifest", &GeneratorAgent::reloadManifest,
        "getManifestPath", &GeneratorAgent::getManifestPath,
        "isManifestLoaded", &GeneratorAgent::isManifestLoaded,
        
        // Synthesis
        "synthesizeSpell", &GeneratorAgent::synthesizeSpell,
        "synthesizeSpellBatch", &GeneratorAgent::synthesizeSpellBatch,
        "setSynthesisGoal", &GeneratorAgent::setSynthesisGoal,
        "getSynthesisGoal", &GeneratorAgent::getSynthesisGoal,
        
        // Genetic evolution
        "evolveSpellPopulation", &GeneratorAgent::evolveSpellPopulation,
        "createInitialPopulation", &GeneratorAgent::createInitialPopulation,
        "setEvolutionParameters", &GeneratorAgent::setEvolutionParameters,
        
        // Grammar engine
        "expandGrammar", &GeneratorAgent::expandGrammar,
        "loadGrammarRules", &GeneratorAgent::loadGrammarRules,
        "addGrammarRule", &GeneratorAgent::addGrammarRule,
        "getGrammarRules", &GeneratorAgent::getGrammarRules,
        
        // Pattern matching
        "matchesPattern", &GeneratorAgent::matchesPattern,
        "findMatchingSpells", &GeneratorAgent::findMatchingSpells,
        "addPatternMatcher", &GeneratorAgent::addPatternMatcher,
        
        // Hot-reload
        "enableHotReload", &GeneratorAgent::enableHotReload,
        "setWatchInterval", &GeneratorAgent::setWatchInterval,
        "startWatching", &GeneratorAgent::startWatching,
        "stopWatching", &GeneratorAgent::stopWatching,
        "isWatching", &GeneratorAgent::isWatching,
        
        // Caching
        "enableCaching", &GeneratorAgent::enableCaching,
        "clearCache", &GeneratorAgent::clearCache,
        "setCacheSize", &GeneratorAgent::setCacheSize,
        "getCacheSize", &GeneratorAgent::getCacheSize,
        "getCacheHitRate", &GeneratorAgent::getCacheHitRate,
        
        // Performance monitoring
        "getStats", &GeneratorAgent::getStats,
        "resetStats", &GeneratorAgent::resetStats,
        "logPerformanceMetrics", &GeneratorAgent::logPerformanceMetrics,
        
        // Batch operations
        "generateSpellBatch", &GeneratorAgent::generateSpellBatch,
        "preloadSpells", &GeneratorAgent::preloadSpells,
        "warmupCache", &GeneratorAgent::warmupCache,
        
        // Utility methods
        "generateSpellId", &GeneratorAgent::generateSpellId,
        "validateSpellDefinition", &GeneratorAgent::validateSpellDefinition,
        "getSpellTags", &GeneratorAgent::getSpellTags,
        "addSpellTag", &GeneratorAgent::addSpellTag,
        "removeSpellTag", &GeneratorAgent::removeSpellTag,
        
        // Advanced features
        "enableAIEnhancement", &GeneratorAgent::enableAIEnhancement,
        "setAIParameters", &GeneratorAgent::setAIParameters,
        "generateAISpell", &GeneratorAgent::generateAISpell,
        "trainOnSpellData", &GeneratorAgent::trainOnSpellData,
        
        // Event system
        "onSpellGenerated", &GeneratorAgent::onSpellGenerated,
        "onSynthesisComplete", &GeneratorAgent::onSynthesisComplete,
        "onEvolutionProgress", &GeneratorAgent::onEvolutionProgress,
        "onError", &GeneratorAgent::onError,
        
        // Import/Export
        "exportSpellDefinitions", &GeneratorAgent::exportSpellDefinitions,
        "importSpellDefinitions", &GeneratorAgent::importSpellDefinitions,
        "exportToFile", &GeneratorAgent::exportToFile,
        "importFromFile", &GeneratorAgent::importFromFile,
        
        // Validation
        "validateSpell", &GeneratorAgent::validateSpell,
        "validateAllSpells", &GeneratorAgent::validateAllSpells,
        "runSpellTests", &GeneratorAgent::runSpellTests,
        
        // Performance optimization
        "enableParallelProcessing", &GeneratorAgent::enableParallelProcessing,
        "setThreadPoolSize", &GeneratorAgent::setThreadPoolSize,
        "enableMemoryPooling", &GeneratorAgent::enableMemoryPooling,
        "setMemoryPoolSize", &GeneratorAgent::setMemoryPoolSize
    );

    // Create global instance
    lua["GeneratorAgent"] = lua.create_named_table("GeneratorAgent");
    lua["GeneratorAgent"]["instance"] = [this]() -> GeneratorAgent* {
        return this;
    };
}

void GeneratorAgent::setConfig(const AgentConfig& config) {
    m_config = config;
    validateConfiguration();
}

const AgentConfig& GeneratorAgent::getConfig() const {
    return m_config;
}

AgentConfig& GeneratorAgent::getConfig() {
    return m_config;
}

// Core spell generation methods
std::expected<SpellInstance, std::string> GeneratorAgent::generateSpell(const std::string& spellId) {
    if (!m_initialized) {
        return std::unexpected("GeneratorAgent not initialized");
    }

    if (!m_config.enableSpellGeneration) {
        return std::unexpected("Spell generation is disabled");
    }

    // Check cache first
    {
        std::shared_lock lock(m_cacheMutex);
        if (auto it = m_spellCache.find(spellId); it != m_spellCache.end()) {
            m_stats.cacheHits++;
            return it->second;
        }
    }

    m_stats.cacheMisses++;
    m_stats.totalSpellsGenerated++;

    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        auto result = m_spellGenerator->create(spellId);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        if (result) {
            m_stats.successfulGenerations++;
            
            // Update performance metrics
            m_generationTimes.push_back(duration.count() / 1000.0);
            if (m_generationTimes.size() > 100) {
                m_generationTimes.erase(m_generationTimes.begin());
            }
            
            // Cache the result if caching is enabled
            if (m_cachingEnabled && shouldCache(spellId)) {
                std::unique_lock lock(m_cacheMutex);
                if (m_spellCache.size() >= m_maxCacheSize) {
                    cleanupCache();
                }
                m_spellCache[spellId] = *result;
                m_stats.cacheSize = m_spellCache.size();
            }
            
            emitSpellGeneratedEvent(*result);
            return result;
        } else {
            m_stats.failedGenerations++;
            m_stats.factoryErrors++;
            emitErrorEvent("Failed to generate spell '" + spellId + "': " + result.error());
            return result;
        }
    } catch (const std::exception& e) {
        m_stats.failedGenerations++;
        m_stats.factoryErrors++;
        std::string error = "Exception during spell generation: " + std::string(e.what());
        emitErrorEvent(error);
        return std::unexpected(error);
    }
}

std::expected<SpellInstance, std::string> GeneratorAgent::generateSpellFromDefinition(const SpellDefinition& def) {
    if (!m_initialized) {
        return std::unexpected("GeneratorAgent not initialized");
    }

    if (!validateSpellDefinition(def)) {
        return std::unexpected("Invalid spell definition");
    }

    m_stats.totalSpellsGenerated++;

    try {
        // Create spell instance directly from definition
        auto result = m_spellGenerator->create(def.id);
        
        if (result) {
            m_stats.successfulGenerations++;
            emitSpellGeneratedEvent(*result);
            return result;
        } else {
            m_stats.failedGenerations++;
            m_stats.factoryErrors++;
            emitErrorEvent("Failed to generate spell from definition: " + result.error());
            return result;
        }
    } catch (const std::exception& e) {
        m_stats.failedGenerations++;
        m_stats.factoryErrors++;
        std::string error = "Exception during spell generation from definition: " + std::string(e.what());
        emitErrorEvent(error);
        return std::unexpected(error);
    }
}

std::vector<std::string> GeneratorAgent::getAvailableSpellIds() const {
    if (!m_initialized || !m_spellGenerator) {
        return {};
    }

    // This would need to be implemented in SpellGenerator
    // For now, return empty vector
    return {};
}

bool GeneratorAgent::hasSpell(const std::string& spellId) const {
    if (!m_initialized || !m_spellGenerator) {
        return false;
    }

    // Check cache first
    {
        std::shared_lock lock(m_cacheMutex);
        if (m_spellCache.find(spellId) != m_spellCache.end()) {
            return true;
        }
    }

    // This would need to be implemented in SpellGenerator
    // For now, return false
    return false;
}

// Synthesis system methods
std::string GeneratorAgent::synthesizeSpell(const SynthesisGoal& goal) {
    if (!m_initialized) {
        emitErrorEvent("Cannot synthesize spell: GeneratorAgent not initialized");
        return "";
    }

    if (!m_config.enableSynthesis) {
        emitErrorEvent("Synthesis is disabled");
        return "";
    }

    m_stats.synthesisAttempts++;

    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        std::string result = m_synthesisManager->generateSpell(goal);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        // Update performance metrics
        m_synthesisTimes.push_back(duration.count() / 1000.0);
        if (m_synthesisTimes.size() > 100) {
            m_synthesisTimes.erase(m_synthesisTimes.begin());
        }
        
        emitSynthesisCompleteEvent(result, goal);
        return result;
    } catch (const std::exception& e) {
        std::string error = "Exception during spell synthesis: " + std::string(e.what());
        emitErrorEvent(error);
        return "";
    }
}

std::vector<std::string> GeneratorAgent::synthesizeSpellBatch(const std::vector<SynthesisGoal>& goals) {
    if (!m_initialized) {
        emitErrorEvent("Cannot synthesize spells: GeneratorAgent not initialized");
        return {};
    }

    if (!m_config.enableSynthesis) {
        emitErrorEvent("Synthesis is disabled");
        return {};
    }

    std::vector<std::string> results;
    results.reserve(goals.size());

    for (const auto& goal : goals) {
        auto result = synthesizeSpell(goal);
        if (!result.empty()) {
            results.push_back(result);
        }
    }

    return results;
}

void GeneratorAgent::setSynthesisGoal(const std::string& spellId, const SynthesisGoal& goal) {
    // This would need to be implemented to store synthesis goals
    // For now, just emit an event
    emitSynthesisCompleteEvent(spellId, goal);
}

SynthesisGoal GeneratorAgent::getSynthesisGoal(const std::string& spellId) const {
    // This would need to be implemented to retrieve synthesis goals
    // For now, return default goal
    return SynthesisGoal{};
}

// Genetic evolution methods
void GeneratorAgent::evolveSpellPopulation(std::vector<std::shared_ptr<SpellNode>>& population, 
    const SynthesisGoal& goal, int generations) {
    if (!m_initialized) {
        emitErrorEvent("Cannot evolve population: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableGeneticEvolution) {
        emitErrorEvent("Genetic evolution is disabled");
        return;
    }

    m_stats.geneticEvolutions++;

    auto startTime = std::chrono::high_resolution_clock::now();
    
    try {
        m_geneticEvolver->evolve(generations, population, goal);
        
        auto endTime = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(endTime - startTime);
        
        // Update performance metrics
        m_evolutionTimes.push_back(duration.count() / 1000.0);
        if (m_evolutionTimes.size() > 100) {
            m_evolutionTimes.erase(m_evolutionTimes.begin());
        }
        
        // Emit progress events for each generation
        for (int i = 0; i < generations; ++i) {
            emitEvolutionProgressEvent(i, 0.0); // Fitness would need to be calculated
        }
    } catch (const std::exception& e) {
        std::string error = "Exception during genetic evolution: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

std::vector<std::shared_ptr<SpellNode>> GeneratorAgent::createInitialPopulation(int size) {
    if (!m_initialized) {
        emitErrorEvent("Cannot create population: GeneratorAgent not initialized");
        return {};
    }

    if (!m_config.enableGeneticEvolution) {
        emitErrorEvent("Genetic evolution is disabled");
        return {};
    }

    std::vector<std::shared_ptr<SpellNode>> population;
    population.reserve(size);

    try {
        for (int i = 0; i < size; ++i) {
            // Create random spell nodes
            // This would need to be implemented based on SpellNode structure
            population.push_back(std::make_shared<SpellNode>());
        }
    } catch (const std::exception& e) {
        std::string error = "Exception during population creation: " + std::string(e.what());
        emitErrorEvent(error);
    }

    return population;
}

void GeneratorAgent::setEvolutionParameters(int populationSize, int generations, float mutationRate) {
    if (!m_initialized) {
        emitErrorEvent("Cannot set evolution parameters: GeneratorAgent not initialized");
        return;
    }

    m_config.geneticPopulationSize = populationSize;
    m_config.geneticGenerations = generations;
    
    // mutationRate would need to be stored in the genetic evolver
    // For now, just update config
}

// Grammar engine methods
std::shared_ptr<SpellNode> GeneratorAgent::expandGrammar(const SynthesisGoal& goal) {
    if (!m_initialized) {
        emitErrorEvent("Cannot expand grammar: GeneratorAgent not initialized");
        return nullptr;
    }

    if (!m_config.enableGrammarEngine) {
        emitErrorEvent("Grammar engine is disabled");
        return nullptr;
    }

    try {
        return m_grammarEngine->expand(goal);
    } catch (const std::exception& e) {
        std::string error = "Exception during grammar expansion: " + std::string(e.what());
        emitErrorEvent(error);
        return nullptr;
    }
}

void GeneratorAgent::loadGrammarRules(const std::string& rulesPath) {
    if (!m_initialized) {
        emitErrorEvent("Cannot load grammar rules: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableGrammarEngine) {
        emitErrorEvent("Grammar engine is disabled");
        return;
    }

    try {
        // This would need to be implemented in GrammarEngine
        // For now, just log the attempt
        logError("Loading grammar rules from: " + rulesPath);
    } catch (const std::exception& e) {
        std::string error = "Exception during grammar rules loading: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

void GeneratorAgent::addGrammarRule(const std::string& pattern, const std::string& expansion) {
    if (!m_initialized) {
        emitErrorEvent("Cannot add grammar rule: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableGrammarEngine) {
        emitErrorEvent("Grammar engine is disabled");
        return;
    }

    try {
        // This would need to be implemented in GrammarEngine
        // For now, just log the attempt
        logError("Adding grammar rule: " + pattern + " -> " + expansion);
    } catch (const std::exception& e) {
        std::string error = "Exception during grammar rule addition: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

std::vector<std::string> GeneratorAgent::getGrammarRules() const {
    if (!m_initialized) {
        return {};
    }

    if (!m_config.enableGrammarEngine) {
        return {};
    }

    // This would need to be implemented in GrammarEngine
    // For now, return empty vector
    return {};
}

// Pattern matching methods
bool GeneratorAgent::matchesPattern(const std::string& spellType, const std::string& pattern) const {
    if (!m_initialized) {
        return false;
    }

    if (!m_config.enablePatternMatching) {
        return false;
    }

    try {
        return EventPatternMatcher::matches(pattern, spellType);
    } catch (const std::exception& e) {
        std::string error = "Exception during pattern matching: " + std::string(e.what());
        const_cast<GeneratorAgent*>(this)->emitErrorEvent(error);
        return false;
    }
}

std::vector<std::string> GeneratorAgent::findMatchingSpells(const std::string& pattern) const {
    if (!m_initialized) {
        return {};
    }

    if (!m_config.enablePatternMatching) {
        return {};
    }

    std::vector<std::string> matches;
    
    try {
        // This would need to be implemented to search through available spells
        // For now, return empty vector
    } catch (const std::exception& e) {
        std::string error = "Exception during spell pattern search: " + std::string(e.what());
        const_cast<GeneratorAgent*>(this)->emitErrorEvent(error);
    }

    return matches;
}

void GeneratorAgent::addPatternMatcher(const std::string& pattern, std::function<bool(const std::string&)> matcher) {
    if (!m_initialized) {
        emitErrorEvent("Cannot add pattern matcher: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enablePatternMatching) {
        emitErrorEvent("Pattern matching is disabled");
        return;
    }

    try {
        // This would need to be implemented to store custom pattern matchers
        // For now, just log the attempt
        logError("Adding pattern matcher for: " + pattern);
    } catch (const std::exception& e) {
        std::string error = "Exception during pattern matcher addition: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

// Factory registration methods
void GeneratorAgent::registerCppFactory(std::string_view type, 
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> factory) {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot register factory: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableCppFactories) {
        emitErrorEvent("C++ factories are disabled");
        return;
    }

    try {
        m_spellGenerator->registerCppFactory(type, std::move(factory));
    } catch (const std::exception& e) {
        std::string error = "Failed to register C++ factory: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

void GeneratorAgent::registerLuaFactory(std::string_view type, sol::function factory) {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot register factory: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableLuaFactories) {
        emitErrorEvent("Lua factories are disabled");
        return;
    }

    try {
        m_spellGenerator->registerLuaFactory(type, std::move(factory));
    } catch (const std::exception& e) {
        std::string error = "Failed to register Lua factory: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

void GeneratorAgent::registerPatternFactory(std::string pattern,
    std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> factory) {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot register factory: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enablePatternMatching) {
        emitErrorEvent("Pattern matching is disabled");
        return;
    }

    try {
        m_spellGenerator->registerPatternFactory(std::move(pattern), std::move(factory));
    } catch (const std::exception& e) {
        std::string error = "Failed to register pattern factory: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

void GeneratorAgent::registerLuaPattern(std::string pattern, sol::function factory) {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot register factory: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableLuaFactories || !m_config.enablePatternMatching) {
        emitErrorEvent("Lua pattern factories are disabled");
        return;
    }

    try {
        m_spellGenerator->registerLuaPattern(std::move(pattern), std::move(factory));
    } catch (const std::exception& e) {
        std::string error = "Failed to register Lua pattern factory: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

// Manifest management methods
auto GeneratorAgent::loadManifest(std::filesystem::path const& path)
    -> std::expected<void, std::vector<BlazeJsonHelper::JsonErrorInfo>> {
    if (!m_initialized || !m_spellGenerator) {
        return std::unexpected(std::vector<BlazeJsonHelper::JsonErrorInfo>{
            {0, 0, "SystemError", "GeneratorAgent not initialized"}
        });
    }

    try {
        auto result = m_spellGenerator->loadManifest(path);
        
        if (!result) {
            m_stats.syntaxErrors += result.error().size();
            for (const auto& error : result.error()) {
                emitErrorEvent("Manifest error: " + error.msg);
            }
        } else {
            // Clear cache when manifest is reloaded
            clearCache();
        }
        
        return result;
    } catch (const std::exception& e) {
        std::string error = "Exception during manifest loading: " + std::string(e.what());
        emitErrorEvent(error);
        return std::unexpected(std::vector<BlazeJsonHelper::JsonErrorInfo>{
            {0, 0, "SystemError", error}
        });
    }
}

void GeneratorAgent::reloadManifest() {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot reload manifest: GeneratorAgent not initialized");
        return;
    }

    try {
        // Get current manifest path and reload
        auto manifestPath = getManifestPath();
        if (!manifestPath.empty()) {
            loadManifest(manifestPath);
        }
    } catch (const std::exception& e) {
        std::string error = "Failed to reload manifest: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

std::filesystem::path GeneratorAgent::getManifestPath() const {
    if (!m_spellGenerator) {
        return {};
    }
    
    // This would need to be implemented in SpellGenerator
    // For now, return default path
    return m_config.defaultManifestPath;
}

bool GeneratorAgent::isManifestLoaded() const {
    if (!m_spellGenerator) {
        return false;
    }
    
    // This would need to be implemented in SpellGenerator
    // For now, return false
    return false;
} 

// Hot-reload system methods
void GeneratorAgent::enableHotReload(bool enable) {
    m_config.enableHotReload = enable;
    if (enable && m_config.enableFileWatching) {
        startWatching();
    } else {
        stopWatching();
    }
}

void GeneratorAgent::setWatchInterval(std::chrono::milliseconds interval) {
    m_config.watchIntervalMs = interval.count();
    if (m_watching) {
        stopWatching();
        startWatching();
    }
}

void GeneratorAgent::startWatching() {
    if (!m_initialized || !m_spellGenerator) {
        emitErrorEvent("Cannot start watching: GeneratorAgent not initialized");
        return;
    }

    if (!m_config.enableHotReload || !m_config.enableFileWatching) {
        return;
    }

    if (m_watching) {
        return;
    }

    try {
        m_spellGenerator->watchManifest(std::chrono::milliseconds(m_config.watchIntervalMs));
        m_watching = true;
    } catch (const std::exception& e) {
        std::string error = "Failed to start watching: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

void GeneratorAgent::stopWatching() {
    if (!m_watching) {
        return;
    }

    try {
        m_spellGenerator->stopWatching();
        m_watching = false;
    } catch (const std::exception& e) {
        std::string error = "Failed to stop watching: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

bool GeneratorAgent::isWatching() const {
    return m_watching;
}

// Caching system methods
void GeneratorAgent::enableCaching(bool enable) {
    m_cachingEnabled = enable;
    if (!enable) {
        clearCache();
    }
}

void GeneratorAgent::clearCache() {
    std::unique_lock lock(m_cacheMutex);
    m_spellCache.clear();
    m_stats.cacheSize = 0;
}

void GeneratorAgent::setCacheSize(size_t maxSize) {
    m_maxCacheSize = maxSize;
    if (m_spellCache.size() > maxSize) {
        cleanupCache();
    }
}

size_t GeneratorAgent::getCacheSize() const {
    return m_spellCache.size();
}

double GeneratorAgent::getCacheHitRate() const {
    uint64_t total = m_stats.cacheHits + m_stats.cacheMisses;
    if (total == 0) {
        return 0.0;
    }
    return static_cast<double>(m_stats.cacheHits) / total;
}

// Performance monitoring methods
const AgentStats& GeneratorAgent::getStats() const {
    return m_stats;
}

AgentStats& GeneratorAgent::getStats() {
    return m_stats;
}

void GeneratorAgent::resetStats() {
    m_stats.reset();
    m_generationTimes.clear();
    m_synthesisTimes.clear();
    m_evolutionTimes.clear();
}

void GeneratorAgent::logPerformanceMetrics() {
    updatePerformanceMetrics();
    
    logError("GeneratorAgent Performance Metrics:");
    logError("  Total Spells Generated: " + std::to_string(m_stats.totalSpellsGenerated));
    logError("  Successful Generations: " + std::to_string(m_stats.successfulGenerations));
    logError("  Failed Generations: " + std::to_string(m_stats.failedGenerations));
    logError("  Synthesis Attempts: " + std::to_string(m_stats.synthesisAttempts));
    logError("  Genetic Evolutions: " + std::to_string(m_stats.geneticEvolutions));
    logError("  Average Generation Time: " + std::to_string(m_stats.averageGenerationTimeMs) + "ms");
    logError("  Average Synthesis Time: " + std::to_string(m_stats.averageSynthesisTimeMs) + "ms");
    logError("  Average Evolution Time: " + std::to_string(m_stats.averageEvolutionTimeMs) + "ms");
    logError("  Cache Hit Rate: " + std::to_string(getCacheHitRate() * 100) + "%");
    logError("  Cache Size: " + std::to_string(m_stats.cacheSize));
    logError("  Syntax Errors: " + std::to_string(m_stats.syntaxErrors));
    logError("  Semantic Errors: " + std::to_string(m_stats.semanticErrors));
    logError("  Factory Errors: " + std::to_string(m_stats.factoryErrors));
}

// Batch operations
std::vector<std::expected<SpellInstance, std::string>> GeneratorAgent::generateSpellBatch(
    const std::vector<std::string>& spellIds) {
    std::vector<std::expected<SpellInstance, std::string>> results;
    results.reserve(spellIds.size());

    for (const auto& spellId : spellIds) {
        results.push_back(generateSpell(spellId));
    }

    return results;
}

void GeneratorAgent::preloadSpells(const std::vector<std::string>& spellIds) {
    if (!m_cachingEnabled) {
        return;
    }

    for (const auto& spellId : spellIds) {
        generateSpell(spellId);
    }
}

void GeneratorAgent::warmupCache() {
    if (!m_cachingEnabled) {
        return;
    }

    // Preload common spells
    std::vector<std::string> commonSpells = {
        "fireball", "icebolt", "lightning", "heal", "shield"
    };
    
    preloadSpells(commonSpells);
}

// Utility methods
std::string GeneratorAgent::generateSpellId() const {
    return generateUniqueId();
}

bool GeneratorAgent::validateSpellDefinition(const SpellDefinition& def) const {
    if (def.id.empty()) {
        return false;
    }
    
    if (def.type.empty()) {
        return false;
    }
    
    return true;
}

std::vector<std::string> GeneratorAgent::getSpellTags(const std::string& spellId) const {
    // This would need to be implemented to retrieve spell tags
    // For now, return empty vector
    return {};
}

void GeneratorAgent::addSpellTag(const std::string& spellId, const std::string& tag) {
    // This would need to be implemented to add spell tags
    // For now, just log the attempt
    logError("Adding tag '" + tag + "' to spell '" + spellId + "'");
}

void GeneratorAgent::removeSpellTag(const std::string& spellId, const std::string& tag) {
    // This would need to be implemented to remove spell tags
    // For now, just log the attempt
    logError("Removing tag '" + tag + "' from spell '" + spellId + "'");
}

// Advanced features
void GeneratorAgent::enableAIEnhancement(bool enable) {
    m_aiEnabled = enable;
}

void GeneratorAgent::setAIParameters(const nlohmann::json& params) {
    m_aiParams = params;
}

std::string GeneratorAgent::generateAISpell(const std::string& prompt) {
    if (!m_aiEnabled) {
        emitErrorEvent("AI enhancement is disabled");
        return "";
    }

    // This would need to be implemented with actual AI integration
    // For now, return a placeholder
    return "ai_generated_spell_" + generateUniqueId();
}

void GeneratorAgent::trainOnSpellData(const std::vector<SpellDefinition>& trainingData) {
    if (!m_aiEnabled) {
        emitErrorEvent("AI enhancement is disabled");
        return;
    }

    m_trainingData = trainingData;
    logError("Training on " + std::to_string(trainingData.size()) + " spell definitions");
}

// Event system
void GeneratorAgent::onSpellGenerated(std::function<void(const SpellInstance&)> callback) {
    m_spellGeneratedCallbacks.push_back(std::move(callback));
}

void GeneratorAgent::onSynthesisComplete(std::function<void(const std::string&, const SynthesisGoal&)> callback) {
    m_synthesisCallbacks.push_back(std::move(callback));
}

void GeneratorAgent::onEvolutionProgress(std::function<void(int generation, double fitness)> callback) {
    m_evolutionCallbacks.push_back(std::move(callback));
}

void GeneratorAgent::onError(std::function<void(const std::string&)> callback) {
    m_errorCallbacks.push_back(std::move(callback));
}

// Import/Export
nlohmann::json GeneratorAgent::exportSpellDefinitions() const {
    // This would need to be implemented to export spell definitions
    // For now, return empty JSON
    return nlohmann::json::object();
}

void GeneratorAgent::importSpellDefinitions(const nlohmann::json& data) {
    // This would need to be implemented to import spell definitions
    // For now, just log the attempt
    logError("Importing spell definitions from JSON");
}

void GeneratorAgent::exportToFile(const std::string& filePath) const {
    try {
        auto data = exportSpellDefinitions();
        std::ofstream file(filePath);
        file << data.dump(2);
    } catch (const std::exception& e) {
        std::string error = "Failed to export to file: " + std::string(e.what());
        const_cast<GeneratorAgent*>(this)->emitErrorEvent(error);
    }
}

void GeneratorAgent::importFromFile(const std::string& filePath) {
    try {
        std::ifstream file(filePath);
        nlohmann::json data;
        file >> data;
        importSpellDefinitions(data);
    } catch (const std::exception& e) {
        std::string error = "Failed to import from file: " + std::string(e.what());
        emitErrorEvent(error);
    }
}

// Validation
bool GeneratorAgent::validateSpell(const std::string& spellId) const {
    // This would need to be implemented to validate spells
    // For now, return true
    return true;
}

std::vector<std::string> GeneratorAgent::validateAllSpells() const {
    // This would need to be implemented to validate all spells
    // For now, return empty vector
    return {};
}

void GeneratorAgent::runSpellTests(const std::string& spellId) {
    // This would need to be implemented to run spell tests
    // For now, just log the attempt
    logError("Running tests for spell: " + spellId);
}

// Performance optimization
void GeneratorAgent::enableParallelProcessing(bool enable) {
    // This would need to be implemented to enable parallel processing
    // For now, just log the attempt
    logError("Parallel processing " + std::string(enable ? "enabled" : "disabled"));
}

void GeneratorAgent::setThreadPoolSize(int size) {
    // This would need to be implemented to set thread pool size
    // For now, just log the attempt
    logError("Setting thread pool size to: " + std::to_string(size));
}

void GeneratorAgent::enableMemoryPooling(bool enable) {
    // This would need to be implemented to enable memory pooling
    // For now, just log the attempt
    logError("Memory pooling " + std::string(enable ? "enabled" : "disabled"));
}

void GeneratorAgent::setMemoryPoolSize(size_t size) {
    // This would need to be implemented to set memory pool size
    // For now, just log the attempt
    logError("Setting memory pool size to: " + std::to_string(size));
}

// Helper methods
void GeneratorAgent::initializeSystems() {
    m_spellGenerator = std::make_unique<SpellGenerator>();
    m_synthesisManager = std::make_unique<SpellSynthesisManager>();
    m_grammarEngine = std::make_unique<GrammarEngine>();
    m_geneticEvolver = std::make_unique<GeneticSpellEvolver>();
}

void GeneratorAgent::shutdownSystems() {
    m_spellGenerator.reset();
    m_synthesisManager.reset();
    m_grammarEngine.reset();
    m_geneticEvolver.reset();
}

void GeneratorAgent::setupEventHandlers() {
    // Event handlers are set up in the constructor
}

void GeneratorAgent::cleanupEventHandlers() {
    m_spellGeneratedCallbacks.clear();
    m_synthesisCallbacks.clear();
    m_evolutionCallbacks.clear();
    m_errorCallbacks.clear();
}

void GeneratorAgent::updateStats() {
    // Update average times
    if (!m_generationTimes.empty()) {
        double sum = 0.0;
        for (double time : m_generationTimes) {
            sum += time;
        }
        m_stats.averageGenerationTimeMs = sum / m_generationTimes.size();
    }
    
    if (!m_synthesisTimes.empty()) {
        double sum = 0.0;
        for (double time : m_synthesisTimes) {
            sum += time;
        }
        m_stats.averageSynthesisTimeMs = sum / m_synthesisTimes.size();
    }
    
    if (!m_evolutionTimes.empty()) {
        double sum = 0.0;
        for (double time : m_evolutionTimes) {
            sum += time;
        }
        m_stats.averageEvolutionTimeMs = sum / m_evolutionTimes.size();
    }
}

void GeneratorAgent::emitSpellGeneratedEvent(const SpellInstance& spell) {
    for (const auto& callback : m_spellGeneratedCallbacks) {
        try {
            callback(spell);
        } catch (const std::exception& e) {
            emitErrorEvent("Exception in spell generated callback: " + std::string(e.what()));
        }
    }
}

void GeneratorAgent::emitSynthesisCompleteEvent(const std::string& spellId, const SynthesisGoal& goal) {
    for (const auto& callback : m_synthesisCallbacks) {
        try {
            callback(spellId, goal);
        } catch (const std::exception& e) {
            emitErrorEvent("Exception in synthesis complete callback: " + std::string(e.what()));
        }
    }
}

void GeneratorAgent::emitEvolutionProgressEvent(int generation, double fitness) {
    for (const auto& callback : m_evolutionCallbacks) {
        try {
            callback(generation, fitness);
        } catch (const std::exception& e) {
            emitErrorEvent("Exception in evolution progress callback: " + std::string(e.what()));
        }
    }
}

void GeneratorAgent::emitErrorEvent(const std::string& error) {
    for (const auto& callback : m_errorCallbacks) {
        try {
            callback(error);
        } catch (const std::exception& e) {
            // Don't emit error events recursively
            logError("Exception in error callback: " + std::string(e.what()));
        }
    }
}

void GeneratorAgent::logError(const std::string& error) {
    // This would typically log to a proper logging system
    // For now, just emit as error event
    emitErrorEvent(error);
}

void GeneratorAgent::updatePerformanceMetrics() {
    updateStats();
    m_lastMetricsTime = std::chrono::high_resolution_clock::now();
}

void GeneratorAgent::cleanupCache() {
    // Simple LRU cache cleanup - remove oldest entries
    while (m_spellCache.size() > m_maxCacheSize) {
        m_spellCache.erase(m_spellCache.begin());
    }
    m_stats.cacheSize = m_spellCache.size();
}

bool GeneratorAgent::shouldCache(const std::string& spellId) const {
    // Cache frequently used spells
    return !spellId.empty();
}

std::string GeneratorAgent::generateUniqueId() const {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    static const char* hex = "0123456789abcdef";
    
    std::string id = "spell_";
    for (int i = 0; i < 8; ++i) {
        id += hex[dis(gen)];
    }
    return id;
}

void GeneratorAgent::validateConfiguration() const {
    if (m_config.geneticPopulationSize <= 0) {
        throw std::runtime_error("Genetic population size must be positive");
    }
    
    if (m_config.geneticGenerations <= 0) {
        throw std::runtime_error("Genetic generations must be positive");
    }
    
    if (m_config.grammarMaxDepth <= 0) {
        throw std::runtime_error("Grammar max depth must be positive");
    }
    
    if (m_config.maxConcurrentGenerations <= 0) {
        throw std::runtime_error("Max concurrent generations must be positive");
    }
}

void GeneratorAgent::setupLuaBindings(sol::state& lua) {
    // Lua bindings are set up in registerBindings method
}

void GeneratorAgent::setupAdvancedFeatures() {
    // Advanced features setup
    if (m_aiEnabled) {
        logError("AI enhancement enabled");
    }
}

void GeneratorAgent::cleanupAdvancedFeatures() {
    // Cleanup advanced features
    m_aiParams.clear();
    m_trainingData.clear();
}

} // namespace MagiTech::GeneratorAgent 
