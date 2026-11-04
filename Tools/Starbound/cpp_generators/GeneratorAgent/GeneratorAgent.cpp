#include "GeneratorAgent.hpp"
#include "core/utils/BlazeJsonHelper.hpp"
#include "core/utils/JsonHelper.hpp"
#include "core/utils/SafeCall.hpp"
#include "core/utils/EventPatternMatcher.hpp"
#include "core/plugins/AdaptiveBusPlugin.hpp"
#include "core/Log.hpp"
#include <cctype>
#include <cmath>
#include <numbers>
#include <sstream>
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
        "Power", 0,
        "Style", 1,
        "Hybrid", 2
    );

    // Register structs
    lua.new_usertype<SynthesisGoal>("SynthesisGoal",
        sol::constructors<SynthesisGoal()>(),
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

    lua.new_usertype<SpellDefinition>("SpellDefinition",
        sol::constructors<SpellDefinition()>(),
        "id", &SpellDefinition::id,
        "type", &SpellDefinition::type,
        "params", &SpellDefinition::params,
        "displayName", &SpellDefinition::displayName,
        "description", &SpellDefinition::description,
        "tags", &SpellDefinition::tags
    );

    using SpellResult = std::tuple<std::optional<SpellInstance>, std::string>;
    auto toLuaResult = [](std::expected<SpellInstance, std::string> r) -> SpellResult {
        if (r) return {std::move(*r), std::string()};
        return {std::nullopt, r.error()};
    };

    // Register GeneratorAgent class
    // (C++-only factory registration - registerCppFactory/registerPatternFactory take
    //  C++ ISpell factories - is not exposed; Lua registers registerLuaFactory/registerLuaPattern.)
    auto agentType = lua.new_usertype<GeneratorAgent>("GeneratorAgent",
        // Constructor
        sol::constructors<GeneratorAgent()>(),

        // IMagiTechModule methods
        "init", &GeneratorAgent::init,
        "shutdown", &GeneratorAgent::shutdown,
        "registerBindings", &GeneratorAgent::registerBindings,

        // Configuration
        "setConfig", &GeneratorAgent::setConfig,
        "getConfig", sol::resolve<AgentConfig&()>(&GeneratorAgent::getConfig),

        // Core generation (returns instance-or-nil, error message)
        "generateSpell", [toLuaResult](GeneratorAgent& self, const std::string& id) {
            return toLuaResult(self.generateSpell(id));
        },
        "generateSpellFromDefinition", [toLuaResult](GeneratorAgent& self, const SpellDefinition& def) {
            return toLuaResult(self.generateSpellFromDefinition(def));
        },
        "getAvailableSpellIds", &GeneratorAgent::getAvailableSpellIds,
        "hasSpell", &GeneratorAgent::hasSpell,

        // Factory registration
        "registerLuaFactory", [](GeneratorAgent& self, const std::string& type, sol::function factory) {
            self.registerLuaFactory(type, std::move(factory));
        },
        "registerLuaPattern", &GeneratorAgent::registerLuaPattern,

        // Manifest management (returns ok, errors)
        "loadManifest", [](GeneratorAgent& self, const std::string& path)
                -> std::tuple<bool, std::vector<BlazeJsonHelper::JsonErrorInfo>> {
            auto result = self.loadManifest(path);
            if (result) return {true, {}};
            return {false, result.error()};
        },
        "reloadManifest", &GeneratorAgent::reloadManifest,
        "getManifestPath", [](const GeneratorAgent& self) { return self.getManifestPath().string(); },
        "isManifestLoaded", &GeneratorAgent::isManifestLoaded,

        // Synthesis
        "synthesizeSpell", &GeneratorAgent::synthesizeSpell,
        "synthesizeSpellBatch", &GeneratorAgent::synthesizeSpellBatch,
        "setSynthesisGoal", &GeneratorAgent::setSynthesisGoal,
        "getSynthesisGoal", &GeneratorAgent::getSynthesisGoal,

        // Genetic evolution
        "evolveSpellPopulation", &GeneratorAgent::evolveSpellPopulation,
        "createInitialPopulation", &GeneratorAgent::createInitialPopulation,
        "setEvolutionParameters", sol::overload(
            sol::resolve<void(int, int, float)>(&GeneratorAgent::setEvolutionParameters),
            sol::resolve<void(float, float)>(&GeneratorAgent::setEvolutionParameters)),

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
        "setWatchInterval", [](GeneratorAgent& self, int milliseconds) {
            self.setWatchInterval(std::chrono::milliseconds(milliseconds));
        },
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
        "getStats", sol::resolve<AgentStats&()>(&GeneratorAgent::getStats),
        "resetStats", &GeneratorAgent::resetStats,
        "logPerformanceMetrics", &GeneratorAgent::logPerformanceMetrics,

        // Batch operations (returns generated instances, error messages)
        "generateSpellBatch", [](GeneratorAgent& self, const std::vector<std::string>& ids) {
            std::vector<SpellInstance> spells;
            std::vector<std::string> errors;
            for (auto& r : self.generateSpellBatch(ids)) {
                if (r) spells.push_back(std::move(*r));
                else errors.push_back(r.error());
            }
            return std::make_tuple(std::move(spells), std::move(errors));
        },
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

        // SpellStone generation
        "generateSpellStoneSeed", &GeneratorAgent::generateSpellStoneSeed,
        "generateSpellStoneFromIngredients", &GeneratorAgent::generateSpellStoneFromIngredients,
        "getSpellStoneRecipes", &GeneratorAgent::getSpellStoneRecipes,
        "hasSpellStoneRecipe", &GeneratorAgent::hasSpellStoneRecipe,
        "registerSpellStoneRecipe", &GeneratorAgent::registerSpellStoneRecipe,
        "removeSpellStoneRecipe", &GeneratorAgent::removeSpellStoneRecipe,

        // Event system
        "onSpellGenerated", &GeneratorAgent::onSpellGenerated,
        "onSynthesisComplete", &GeneratorAgent::onSynthesisComplete,
        "onEvolutionProgress", &GeneratorAgent::onEvolutionProgress,
        "onError", &GeneratorAgent::onError,

        // Import/Export (JSON as text on the Lua side)
        "exportSpellDefinitions", [](const GeneratorAgent& self) { return self.exportSpellDefinitions().dump(); },
        "importSpellDefinitions", [](GeneratorAgent& self, const std::string& jsonText) {
            self.importSpellDefinitions(nlohmann::json::parse(jsonText));
        },
        "exportToFile", &GeneratorAgent::exportToFile,
        "importFromFile", &GeneratorAgent::importFromFile,

        // Validation
        "validateSpell", sol::resolve<bool(const std::string&) const>(&GeneratorAgent::validateSpell),
        "validateAllSpells", &GeneratorAgent::validateAllSpells,
        "runSpellTests", &GeneratorAgent::runSpellTests,

        // Performance optimization
        "enableParallelProcessing", &GeneratorAgent::enableParallelProcessing,
        "setThreadPoolSize", &GeneratorAgent::setThreadPoolSize,
        "enableMemoryPooling", &GeneratorAgent::enableMemoryPooling,
        "setMemoryPoolSize", &GeneratorAgent::setMemoryPoolSize
    );

    // Access to this agent instance: GeneratorAgent.instance()
    agentType["instance"] = [this]() -> GeneratorAgent* {
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
                m_spellCache.insert_or_assign(spellId, *result);
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
        auto result = m_spellGenerator->createFromDefinition(def);
        
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

    auto ids = m_spellGenerator->definitionIds();
    std::sort(ids.begin(), ids.end());
    return ids;
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

    return m_spellGenerator->hasDefinition(spellId);
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
    {
        std::lock_guard<std::mutex> lock(m_registryMutex);
        m_synthesisGoals[spellId] = goal;
    }
    emitSynthesisCompleteEvent(spellId, goal);
}

SynthesisGoal GeneratorAgent::getSynthesisGoal(const std::string& spellId) const {
    std::lock_guard<std::mutex> lock(m_registryMutex);
    auto it = m_synthesisGoals.find(spellId);
    return it != m_synthesisGoals.end() ? it->second : SynthesisGoal{};
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
        
        // Report the best fitness reached (population is sorted best-first)
        const double bestFitness = population.empty() || !population.front()
            ? 0.0 : synthesis_detail::fitness(*population.front(), goal);
        for (int i = 0; i < generations; ++i) {
            emitEvolutionProgressEvent(i, bestFitness);
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
        // Random goals over the grammar's vocabulary give a diverse starting population
        static const std::vector<std::string> vocabulary = {
            "beam", "aoe", "heal", "frost", "lightning", "poison", "chain", "bounce", "repeat", "explosive"};
        std::uniform_int_distribution<size_t> pickTag(0, vocabulary.size() - 1);
        std::uniform_int_distribution<int> tagCount(0, 3);
        std::uniform_real_distribution<float> power(5.0f, 100.0f);
        for (int i = 0; i < size; ++i) {
            SynthesisGoal goal;
            goal.targetPower = power(m_shapeRng);
            for (int t = tagCount(m_shapeRng); t > 0; --t) goal.styleTags.push_back(vocabulary[pickTag(m_shapeRng)]);
            population.push_back(m_grammarEngine->expand(goal));
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
    m_mutationRate = mutationRate;
    m_geneticEvolver->setMutationRate(mutationRate);
    m_synthesisManager->setEvolutionParameters(static_cast<size_t>(std::max(populationSize, 2)), generations, mutationRate);
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
        // Accepts {"rules": [{"pattern": "...", "expansion": "..."}]} or {"pattern": "expansion", ...}
        std::ifstream file(rulesPath);
        if (!file) {
            emitErrorEvent("Cannot open grammar rules file: " + rulesPath);
            return;
        }
        nlohmann::json data = nlohmann::json::parse(file);
        size_t loaded = 0;
        if (data.contains("rules") && data["rules"].is_array()) {
            for (const auto& rule : data["rules"]) {
                if (rule.contains("pattern") && rule.contains("expansion") &&
                    rule["pattern"].is_string() && rule["expansion"].is_string()) {
                    addGrammarRule(rule["pattern"].get<std::string>(), rule["expansion"].get<std::string>());
                    ++loaded;
                }
            }
        } else if (data.is_object()) {
            for (const auto& [pattern, expansion] : data.items()) {
                if (expansion.is_string()) {
                    addGrammarRule(pattern, expansion.get<std::string>());
                    ++loaded;
                }
            }
        }
        Log::info("GeneratorAgent", "Loaded {} grammar rules from {}", loaded, rulesPath);
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
        m_grammarEngine->addRule(pattern, expansion);
        m_synthesisManager->addGrammarRule(pattern, expansion);
        std::lock_guard<std::mutex> lock(m_registryMutex);
        m_grammarRules.emplace_back(pattern, expansion);
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

    std::lock_guard<std::mutex> lock(m_registryMutex);
    std::vector<std::string> rules;
    rules.reserve(m_grammarRules.size());
    for (const auto& [pattern, expansion] : m_grammarRules) {
        rules.push_back(pattern + " -> " + expansion);
    }
    return rules;
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
        // A custom matcher registered for this pattern takes precedence
        std::function<bool(const std::string&)> custom;
        {
            std::lock_guard<std::mutex> lock(m_registryMutex);
            if (auto it = m_patternMatchers.find(pattern); it != m_patternMatchers.end()) custom = it->second;
        }
        if (custom) return custom(spellType);
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
        // Match against spell types (and ids) of all known definitions
        for (const auto& def : m_spellGenerator->definitions()) {
            if (matchesPattern(def.type, pattern) || matchesPattern(def.id, pattern)) {
                matches.push_back(def.id);
            }
        }
        std::sort(matches.begin(), matches.end());
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
        std::lock_guard<std::mutex> lock(m_registryMutex);
        m_patternMatchers[pattern] = std::move(matcher);
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
                emitErrorEvent("Manifest error: " + error.message);
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

    // The path of the last successfully loaded manifest, else the configured default
    auto path = m_spellGenerator->manifestPath();
    return path.empty() ? std::filesystem::path(m_config.defaultManifestPath) : path;
}

bool GeneratorAgent::isManifestLoaded() const {
    if (!m_spellGenerator) {
        return false;
    }
    return m_spellGenerator->isManifestLoaded();
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
    if (!m_spellGenerator) return {};
    auto def = m_spellGenerator->findDefinition(spellId);
    return def ? def->tags : std::vector<std::string>{};
}

void GeneratorAgent::addSpellTag(const std::string& spellId, const std::string& tag) {
    if (!m_spellGenerator) return;
    const bool found = m_spellGenerator->updateDefinition(spellId, [&](SpellDefinition& def) {
        if (std::find(def.tags.begin(), def.tags.end(), tag) == def.tags.end()) def.tags.push_back(tag);
    });
    if (!found) emitErrorEvent("Cannot tag unknown spell '" + spellId + "'");
}

void GeneratorAgent::removeSpellTag(const std::string& spellId, const std::string& tag) {
    if (!m_spellGenerator) return;
    const bool found = m_spellGenerator->updateDefinition(spellId, [&](SpellDefinition& def) {
        def.tags.erase(std::remove(def.tags.begin(), def.tags.end(), tag), def.tags.end());
    });
    if (!found) emitErrorEvent("Cannot untag unknown spell '" + spellId + "'");
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

    // Turn the prompt into a synthesis goal: words become style tags, numbers set the power.
    SynthesisGoal goal;
    goal.targetPower = m_aiParams.value("defaultPower", 25.0f);
    std::string word;
    auto flush = [&]() {
        if (word.empty()) return;
        if (std::all_of(word.begin(), word.end(), [](unsigned char c) { return std::isdigit(c) != 0; })) {
            goal.targetPower = std::stof(word);
        } else {
            goal.styleTags.push_back(word);
        }
        word.clear();
    };
    for (unsigned char c : prompt) {
        if (std::isalnum(c)) word.push_back(static_cast<char>(std::tolower(c)));
        else flush();
    }
    flush();

    // Bias towards tags seen in the training data
    for (const auto& def : m_trainingData) {
        for (const auto& tag : def.tags) {
            if (std::find(goal.styleTags.begin(), goal.styleTags.end(), def.type) != goal.styleTags.end() &&
                std::find(goal.styleTags.begin(), goal.styleTags.end(), tag) == goal.styleTags.end()) {
                goal.styleTags.push_back(tag);
            }
        }
    }

    const std::string spellJson = synthesizeSpell(goal);
    if (spellJson.empty()) return "";
    const std::string id = "ai_generated_spell_" + generateUniqueId();
    setSynthesisGoal(id, goal);
    return spellJson;
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
    // Same layout as the manifest: {"spells": [...]}
    nlohmann::json spells = nlohmann::json::array();
    if (m_spellGenerator) {
        for (const auto& def : m_spellGenerator->definitions()) {
            spells.push_back({
                {"id", def.id},
                {"type", def.type},
                {"params", def.params},
                {"displayName", def.displayName},
                {"description", def.description},
                {"tags", def.tags}
            });
        }
    }
    return nlohmann::json{{"spells", std::move(spells)}};
}

void GeneratorAgent::importSpellDefinitions(const nlohmann::json& data) {
    if (!m_spellGenerator) {
        emitErrorEvent("Cannot import spell definitions: GeneratorAgent not initialized");
        return;
    }
    const nlohmann::json& spells = data.is_array() ? data : data.value("spells", nlohmann::json::array());
    size_t imported = 0;
    for (const auto& sj : spells) {
        if (!sj.is_object()) continue;
        SpellDefinition def;
        def.id = sj.value("id", std::string());
        def.type = sj.value("type", std::string());
        def.params = sj.value("params", nlohmann::json::object());
        def.displayName = sj.value("displayName", def.id);
        def.description = sj.value("description", std::string());
        if (sj.contains("tags") && sj["tags"].is_array()) {
            for (const auto& t : sj["tags"]) if (t.is_string()) def.tags.push_back(t.get<std::string>());
        }
        if (!validateSpellDefinition(def)) {
            m_stats.semanticErrors++;
            emitErrorEvent("Skipping invalid imported spell definition '" + def.id + "'");
            continue;
        }
        m_spellGenerator->upsertDefinition(std::move(def));
        ++imported;
    }
    clearCache();
    Log::info("GeneratorAgent", "Imported {} spell definitions", imported);
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
    if (!m_spellGenerator) return false;
    auto def = m_spellGenerator->findDefinition(spellId);
    // Valid = well-formed definition that some registered factory can build
    return def && validateSpellDefinition(*def) && m_spellGenerator->hasFactoryFor(def->type);
}

std::vector<std::string> GeneratorAgent::validateAllSpells() const {
    // Returns the ids of spells that fail validation
    std::vector<std::string> invalid;
    if (!m_spellGenerator) return invalid;
    for (const auto& id : m_spellGenerator->definitionIds()) {
        if (!validateSpell(id)) invalid.push_back(id);
    }
    std::sort(invalid.begin(), invalid.end());
    return invalid;
}

void GeneratorAgent::runSpellTests(const std::string& spellId) {
    // Instantiation test: validation, then a real factory build (without casting).
    if (!validateSpell(spellId)) {
        emitErrorEvent("Spell test failed for '" + spellId + "': definition invalid or no factory");
        return;
    }
    auto result = m_spellGenerator->create(spellId);
    if (!result) {
        emitErrorEvent("Spell test failed for '" + spellId + "': " + result.error());
        return;
    }
    Log::info("GeneratorAgent", "Spell test passed for '{}'", spellId);
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
    Log::info("GeneratorAgent", "{}", error);
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

// ============================================================================
// SpellStone generation
// ============================================================================

uint64_t GeneratorAgent::generateSpellStoneSeed(int entityId, const std::vector<std::string>& ingredients,
                                                uint64_t userSeed, uint64_t worldSeed) {
    return SpellStoneAPI::generateSeed(entityId, ingredients, userSeed, worldSeed);
}

std::string GeneratorAgent::generateSpellStoneFromIngredients(const std::vector<std::string>& ingredients,
                                                              int entityId, uint64_t userSeed, uint64_t worldSeed) {
    if (ingredients.empty()) {
        emitErrorEvent("Cannot generate a spellstone without ingredients");
        return "";
    }

    const uint64_t seed = generateSpellStoneSeed(entityId, ingredients, userSeed, worldSeed);

    // A registered recipe with the same ingredient multiset names the stone
    std::vector<std::string> sorted = ingredients;
    std::sort(sorted.begin(), sorted.end());
    std::string recipeId;
    {
        std::lock_guard<std::mutex> lock(m_spellStoneRecipesMutex);
        for (const auto& [id, recipe] : m_spellStoneRecipes) {
            std::vector<std::string> r = recipe;
            std::sort(r.begin(), r.end());
            if (r == sorted) { recipeId = id; break; }
        }
    }

    // The ingredients drive the spell's style; the seed fixes its power deterministically
    SynthesisGoal goal;
    goal.styleTags = sorted;
    goal.targetPower = 10.0f + static_cast<float>(seed % 9001) / 100.0f;   // 10 .. 100

    nlohmann::json stone;
    stone["seed"] = seed;
    stone["recipe"] = recipeId;
    stone["ingredients"] = sorted;
    stone["targetPower"] = goal.targetPower;
    const std::string spell = synthesizeSpell(goal);
    stone["spell"] = spell.empty() ? nlohmann::json() : nlohmann::json::parse(spell);
    return stone.dump();
}

std::vector<std::string> GeneratorAgent::getSpellStoneRecipes() const {
    std::lock_guard<std::mutex> lock(m_spellStoneRecipesMutex);
    std::vector<std::string> ids;
    ids.reserve(m_spellStoneRecipes.size());
    for (const auto& [id, recipe] : m_spellStoneRecipes) ids.push_back(id);
    std::sort(ids.begin(), ids.end());
    return ids;
}

bool GeneratorAgent::hasSpellStoneRecipe(const std::string& recipeId) const {
    std::lock_guard<std::mutex> lock(m_spellStoneRecipesMutex);
    return m_spellStoneRecipes.count(recipeId) != 0;
}

void GeneratorAgent::registerSpellStoneRecipe(const std::string& recipeId, const std::vector<std::string>& ingredients) {
    if (recipeId.empty() || ingredients.empty()) {
        emitErrorEvent("Spellstone recipe needs an id and at least one ingredient");
        return;
    }
    std::lock_guard<std::mutex> lock(m_spellStoneRecipesMutex);
    m_spellStoneRecipes[recipeId] = ingredients;
}

void GeneratorAgent::removeSpellStoneRecipe(const std::string& recipeId) {
    std::lock_guard<std::mutex> lock(m_spellStoneRecipesMutex);
    m_spellStoneRecipes.erase(recipeId);
}

// ============================================================================
// Balanced spell shapes (ShapeDef from core/ShapeTypes.hpp)
//
// power = covered area of the shape; cost = power * per-shape multiplier.
// Shapes built for a budget have cost == budget. A spell is balanced when its
// cost stays within m_costThreshold * kMaxBudget and its efficiency
// (power per cost) does not exceed m_powerThreshold * kMaxEfficiency.
// ============================================================================

namespace {
    constexpr float kMaxBudget = 10.0f;
    constexpr float kMaxEfficiency = 1.25f;
    constexpr float kLineWidth = 0.1f;

    const char* shapeTypeName(::ShapeType type) {
        switch (type) {
            case ::ShapeType::Circle: return "Circle";
            case ::ShapeType::Square: return "Square";
            case ::ShapeType::Line: return "Line";
            case ::ShapeType::Cone: return "Cone";
        }
        return "Circle";
    }

    std::optional<::ShapeType> shapeTypeFromName(const std::string& name) {
        std::string lower;
        for (unsigned char c : name) lower.push_back(static_cast<char>(std::tolower(c)));
        if (lower == "circle") return ::ShapeType::Circle;
        if (lower == "square") return ::ShapeType::Square;
        if (lower == "line") return ::ShapeType::Line;
        if (lower == "cone") return ::ShapeType::Cone;
        return std::nullopt;
    }

    float costMultiplier(::ShapeType type) {
        switch (type) {
            case ::ShapeType::Circle: return 1.0f;
            case ::ShapeType::Square: return 1.1f;
            case ::ShapeType::Line: return 0.8f;
            case ::ShapeType::Cone: return 0.9f;
        }
        return 1.0f;
    }

    float shapeArea(const ShapeDef& s) {
        constexpr float pi = std::numbers::pi_v<float>;
        switch (s.shape) {
            case ::ShapeType::Circle: return pi * s.radius * s.radius;
            case ::ShapeType::Square: return (2.0f * s.radius) * (2.0f * s.radius);
            case ::ShapeType::Line: return s.radius * s.width;
            case ::ShapeType::Cone: return (s.angle / 360.0f) * pi * s.radius * s.radius;
        }
        return 0.0f;
    }

    // Radius giving the requested area for the shape (width/angle fixed)
    float radiusForArea(const ShapeDef& s, float area) {
        constexpr float pi = std::numbers::pi_v<float>;
        area = std::max(area, 1e-4f);
        switch (s.shape) {
            case ::ShapeType::Circle: return std::sqrt(area / pi);
            case ::ShapeType::Square: return std::sqrt(area) * 0.5f;
            case ::ShapeType::Line: return area / std::max(s.width, 1e-4f);
            case ::ShapeType::Cone: return std::sqrt(area / ((std::max(s.angle, 1.0f) / 360.0f) * pi));
        }
        return 1.0f;
    }
}

::ShapeType GeneratorAgent::pickShapeType(const std::vector<::ShapeType>& candidates) const {
    std::vector<float> weights;
    weights.reserve(candidates.size());
    for (auto type : candidates) {
        auto it = m_shapePreferences.find(shapeTypeName(type));
        weights.push_back(it != m_shapePreferences.end() ? std::max(it->second, 0.0f) : 1.0f);
    }
    if (std::all_of(weights.begin(), weights.end(), [](float w) { return w <= 0.0f; })) {
        std::fill(weights.begin(), weights.end(), 1.0f);
    }
    std::discrete_distribution<size_t> pick(weights.begin(), weights.end());
    return candidates[pick(m_shapeRng)];
}

ShapeDef GeneratorAgent::buildShape(::ShapeType type, float budget) const {
    ShapeDef s;
    s.shape = type;
    s.typeStr = shapeTypeName(type);
    s.width = kLineWidth;
    if (type == ::ShapeType::Cone) {
        s.angle = std::uniform_real_distribution<float>(20.0f, 90.0f)(m_shapeRng);
    }
    // Choose the size so that cost == budget
    s.radius = radiusForArea(s, std::max(budget, 0.01f) / costMultiplier(type));
    s.params = {s.radius, s.width, s.angle};
    s.id = std::string("shape_") + s.typeStr + "_" + generateUniqueId().substr(6);
    return s;
}

ShapeDef GeneratorAgent::makeSpellShape() {
    return makeSpellShapeWithBudget(1.0f);
}

ShapeDef GeneratorAgent::makeSpellShapeWithBudget(float budget) {
    return makeSpellShapeWithConstraints({}, {}, budget);
}

ShapeDef GeneratorAgent::makeSpellShapeWithConstraints(const std::vector<std::string>& requiredShapes,
                                                       const std::vector<std::string>& forbiddenShapes,
                                                       float budget) {
    std::vector<::ShapeType> candidates;
    if (!requiredShapes.empty()) {
        for (const auto& name : requiredShapes) {
            if (auto type = shapeTypeFromName(name)) candidates.push_back(*type);
        }
    } else {
        candidates = {::ShapeType::Circle, ::ShapeType::Square, ::ShapeType::Line, ::ShapeType::Cone};
    }
    candidates.erase(std::remove_if(candidates.begin(), candidates.end(), [&](::ShapeType type) {
        return std::any_of(forbiddenShapes.begin(), forbiddenShapes.end(), [&](const std::string& name) {
            auto forbidden = shapeTypeFromName(name);
            return forbidden && *forbidden == type;
        });
    }), candidates.end());

    if (candidates.empty()) {
        emitErrorEvent("No spell shape satisfies the given constraints; using Circle");
        candidates.push_back(::ShapeType::Circle);
    }
    return buildShape(pickShapeType(candidates), budget);
}

std::vector<ShapeDef> GeneratorAgent::generateSpellVariations(int count, float budget) {
    std::vector<ShapeDef> variations;
    variations.reserve(static_cast<size_t>(std::max(count, 0)));
    std::uniform_real_distribution<float> jitter(0.8f, 1.2f);
    for (int i = 0; i < count; ++i) {
        variations.push_back(makeSpellShapeWithBudget(budget * jitter(m_shapeRng)));
    }
    return variations;
}

ShapeDef GeneratorAgent::combineShapes(const std::vector<ShapeDef>& shapes) {
    if (shapes.empty()) return ShapeDef{};
    // The most powerful shape decides the primitive; areas add up.
    const auto strongest = std::max_element(shapes.begin(), shapes.end(), [&](const ShapeDef& a, const ShapeDef& b) {
        return calculateSpellPower(a) < calculateSpellPower(b);
    });
    ShapeDef combined;
    combined.shape = strongest->shape;
    combined.typeStr = shapeTypeName(combined.shape);
    combined.width = 0.0f;
    combined.angle = 0.0f;
    float totalArea = 0.0f;
    std::string id = "combo";
    for (const auto& s : shapes) {
        totalArea += shapeArea(s);
        combined.width += s.width;
        combined.angle = std::max(combined.angle, s.angle);
        combined.points.insert(combined.points.end(), s.points.begin(), s.points.end());
        id += "_" + (s.id.empty() ? std::string(shapeTypeName(s.shape)) : s.id);
    }
    combined.width /= static_cast<float>(shapes.size());
    combined.radius = radiusForArea(combined, totalArea);
    combined.params = {combined.radius, combined.width, combined.angle};
    combined.id = id;
    return combined;
}

ShapeDef GeneratorAgent::evolveSpell(const ShapeDef& baseSpell, float evolutionFactor) {
    ShapeDef evolved = baseSpell;
    const float sigma = std::max(0.0f, evolutionFactor) * std::max(m_mutationRate, 0.01f);
    std::normal_distribution<float> scale(1.0f, sigma);
    std::uniform_real_distribution<float> unit(0.0f, 1.0f);

    evolved.radius = std::max(0.05f, evolved.radius * scale(m_shapeRng));
    if (evolved.shape == ::ShapeType::Line) evolved.width = std::max(0.01f, evolved.width * scale(m_shapeRng));
    if (evolved.shape == ::ShapeType::Cone) evolved.angle = std::clamp(evolved.angle * scale(m_shapeRng), 5.0f, 360.0f);

    // Crossover towards a preferred primitive, keeping the area
    if (unit(m_shapeRng) < m_crossoverRate * std::min(evolutionFactor, 1.0f)) {
        const float area = shapeArea(evolved);
        evolved.shape = pickShapeType({::ShapeType::Circle, ::ShapeType::Square, ::ShapeType::Line, ::ShapeType::Cone});
        evolved.typeStr = shapeTypeName(evolved.shape);
        if (evolved.shape == ::ShapeType::Line && evolved.width <= 0.0f) evolved.width = kLineWidth;
        if (evolved.shape == ::ShapeType::Cone && evolved.angle <= 0.0f) evolved.angle = 45.0f;
        evolved.radius = radiusForArea(evolved, area);
    }
    evolved.params = {evolved.radius, evolved.width, evolved.angle};
    evolved.id = baseSpell.id + "_evo";
    return evolved;
}

bool GeneratorAgent::isSpellBalanced(const ShapeDef& spell) const {
    if (!validateSpell(spell)) return false;
    const float cost = calculateSpellCost(spell);
    if (cost <= 0.0f) return false;
    const float efficiency = calculateSpellPower(spell) / cost;
    return cost <= m_costThreshold * kMaxBudget && efficiency <= m_powerThreshold * kMaxEfficiency;
}

float GeneratorAgent::calculateSpellPower(const ShapeDef& spell) const {
    return shapeArea(spell);
}

float GeneratorAgent::calculateSpellCost(const ShapeDef& spell) const {
    return calculateSpellPower(spell) * costMultiplier(spell.shape);
}

bool GeneratorAgent::validateSpell(const ShapeDef& spell) const {
    if (!(spell.radius > 0.0f) || !std::isfinite(spell.radius)) return false;
    switch (spell.shape) {
        case ::ShapeType::Line: return spell.width > 0.0f;
        case ::ShapeType::Cone: return spell.angle > 0.0f && spell.angle <= 360.0f;
        default: return true;
    }
}

void GeneratorAgent::setBalanceParameters(float powerThreshold, float costThreshold) {
    m_powerThreshold = std::max(powerThreshold, 0.0f);
    m_costThreshold = std::max(costThreshold, 0.0f);
}

void GeneratorAgent::setShapePreferences(const std::unordered_map<std::string, float>& preferences) {
    m_shapePreferences = preferences;
}

void GeneratorAgent::setEvolutionParameters(float mutationRate, float crossoverRate) {
    m_mutationRate = std::clamp(mutationRate, 0.0f, 1.0f);
    m_crossoverRate = std::clamp(crossoverRate, 0.0f, 1.0f);
    if (m_geneticEvolver) m_geneticEvolver->setMutationRate(m_mutationRate);
}

} // namespace MagiTech::GeneratorAgent 
