#pragma once

#include "systems/SpellGenerator.hpp"
#include "systems/SpellSynthesisManager.hpp"
#include "IMagiTechModule.hpp"
#include "vendor/json/include/nlohmann/json.hpp"
#include <sol/sol.hpp>
#include "SpellStoneAPI.h"
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>

namespace MagiTech::GeneratorAgent {

// Configuration structure for the GeneratorAgent
struct AgentConfig {
    bool enableSpellGeneration = true;
    bool enableSynthesis = true;
    bool enableGeneticEvolution = true;
    bool enableGrammarEngine = true;
    bool enableHotReload = true;
    bool enablePatternMatching = true;
    bool enableLuaFactories = true;
    bool enableCppFactories = true;
    
    // Performance settings
    int maxConcurrentGenerations = 4;
    int geneticPopulationSize = 100;
    int geneticGenerations = 50;
    int grammarMaxDepth = 10;
    
    // File paths
    std::string defaultManifestPath = "spells/manifest.json";
    std::string synthesisRulesPath = "spells/synthesis_rules.json";
    std::string grammarRulesPath = "spells/grammar_rules.json";
    
    // Hot-reload settings
    int watchIntervalMs = 1000;
    bool enableFileWatching = true;
};

// Statistics structure for monitoring performance
struct AgentStats {
    // Generation stats
    uint64_t totalSpellsGenerated = 0;
    uint64_t successfulGenerations = 0;
    uint64_t failedGenerations = 0;
    uint64_t synthesisAttempts = 0;
    uint64_t geneticEvolutions = 0;
    
    // Performance stats
    double averageGenerationTimeMs = 0.0;
    double averageSynthesisTimeMs = 0.0;
    double averageEvolutionTimeMs = 0.0;
    
    // Cache stats
    uint64_t cacheHits = 0;
    uint64_t cacheMisses = 0;
    uint64_t cacheSize = 0;
    
    // Error stats
    uint64_t syntaxErrors = 0;
    uint64_t semanticErrors = 0;
    uint64_t factoryErrors = 0;
    
    // Reset stats
    void reset() {
        totalSpellsGenerated = 0;
        successfulGenerations = 0;
        failedGenerations = 0;
        synthesisAttempts = 0;
        geneticEvolutions = 0;
        averageGenerationTimeMs = 0.0;
        averageSynthesisTimeMs = 0.0;
        averageEvolutionTimeMs = 0.0;
        cacheHits = 0;
        cacheMisses = 0;
        cacheSize = 0;
        syntaxErrors = 0;
        semanticErrors = 0;
        factoryErrors = 0;
    }
};

// Main GeneratorAgent class - unified interface for spell generation
class GeneratorAgent : public IMagiTechModule {
public:
    GeneratorAgent();
    ~GeneratorAgent() override;

    // IMagiTechModule implementation
    void init() override;
    void shutdown() override;
    void registerBindings(sol::state& lua) override;

    // Configuration management
    void setConfig(const AgentConfig& config);
    const AgentConfig& getConfig() const;
    AgentConfig& getConfig();

    // Core spell generation
    std::expected<SpellInstance, std::string> generateSpell(const std::string& spellId);
    std::expected<SpellInstance, std::string> generateSpellFromDefinition(const SpellDefinition& def);
    std::vector<std::string> getAvailableSpellIds() const;
    bool hasSpell(const std::string& spellId) const;

    // Factory registration
    void registerCppFactory(std::string_view type, 
        std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> factory);
    void registerLuaFactory(std::string_view type, sol::function factory);
    void registerPatternFactory(std::string pattern,
        std::function<std::unique_ptr<ISpell>(SpellDefinition const&)> factory);
    void registerLuaPattern(std::string pattern, sol::function factory);

    // Manifest management
    auto loadManifest(std::filesystem::path const& path)
        -> std::expected<void, std::vector<BlazeJsonHelper::JsonErrorInfo>>;
    void reloadManifest();
    std::filesystem::path getManifestPath() const;
    bool isManifestLoaded() const;

    // Synthesis system
    std::string synthesizeSpell(const SynthesisGoal& goal);
    std::vector<std::string> synthesizeSpellBatch(const std::vector<SynthesisGoal>& goals);
    void setSynthesisGoal(const std::string& spellId, const SynthesisGoal& goal);
    SynthesisGoal getSynthesisGoal(const std::string& spellId) const;

    // Genetic evolution
    void evolveSpellPopulation(std::vector<std::shared_ptr<SpellNode>>& population, 
        const SynthesisGoal& goal, int generations = 50);
    std::vector<std::shared_ptr<SpellNode>> createInitialPopulation(int size = 100);
    void setEvolutionParameters(int populationSize, int generations, float mutationRate = 0.1f);

    // Grammar engine
    std::shared_ptr<SpellNode> expandGrammar(const SynthesisGoal& goal);
    void loadGrammarRules(const std::string& rulesPath);
    void addGrammarRule(const std::string& pattern, const std::string& expansion);
    std::vector<std::string> getGrammarRules() const;

    // Pattern matching
    bool matchesPattern(const std::string& spellType, const std::string& pattern) const;
    std::vector<std::string> findMatchingSpells(const std::string& pattern) const;
    void addPatternMatcher(const std::string& pattern, std::function<bool(const std::string&)> matcher);

    // Hot-reload system
    void enableHotReload(bool enable = true);
    void setWatchInterval(std::chrono::milliseconds interval);
    void startWatching();
    void stopWatching();
    bool isWatching() const;

    // Caching system
    void enableCaching(bool enable = true);
    void clearCache();
    void setCacheSize(size_t maxSize);
    size_t getCacheSize() const;
    double getCacheHitRate() const;

    // Performance monitoring
    const AgentStats& getStats() const;
    AgentStats& getStats();
    void resetStats();
    void logPerformanceMetrics();

    // Batch operations
    std::vector<std::expected<SpellInstance, std::string>> generateSpellBatch(
        const std::vector<std::string>& spellIds);
    void preloadSpells(const std::vector<std::string>& spellIds);
    void warmupCache();

    // Utility methods
    std::string generateSpellId() const;
    bool validateSpellDefinition(const SpellDefinition& def) const;
    std::vector<std::string> getSpellTags(const std::string& spellId) const;
    void addSpellTag(const std::string& spellId, const std::string& tag);
    void removeSpellTag(const std::string& spellId, const std::string& tag);

    // Advanced features
    void enableAIEnhancement(bool enable = true);
    void setAIParameters(const nlohmann::json& params);
    std::string generateAISpell(const std::string& prompt);
    void trainOnSpellData(const std::vector<SpellDefinition>& trainingData);
    
    // SpellStone Generation
    uint64_t generateSpellStoneSeed(int entityId, const std::vector<std::string>& ingredients, 
                                   uint64_t userSeed = 0, uint64_t worldSeed = 0);
    std::string generateSpellStoneFromIngredients(const std::vector<std::string>& ingredients,
                                                 int entityId, uint64_t userSeed = 0, uint64_t worldSeed = 0);
    std::vector<std::string> getSpellStoneRecipes() const;
    bool hasSpellStoneRecipe(const std::string& recipeId) const;
    void registerSpellStoneRecipe(const std::string& recipeId, const std::vector<std::string>& ingredients);
    void removeSpellStoneRecipe(const std::string& recipeId);
    
    // BalancedSpellFactory Integration
    ShapeDef makeSpellShape();
    ShapeDef makeSpellShapeWithBudget(float budget);
    ShapeDef makeSpellShapeWithConstraints(const std::vector<std::string>& requiredShapes,
                                         const std::vector<std::string>& forbiddenShapes,
                                         float budget);
    std::vector<ShapeDef> generateSpellVariations(int count, float budget);
    ShapeDef combineShapes(const std::vector<ShapeDef>& shapes);
    ShapeDef evolveSpell(const ShapeDef& baseSpell, float evolutionFactor);
    bool isSpellBalanced(const ShapeDef& spell) const;
    float calculateSpellPower(const ShapeDef& spell) const;
    float calculateSpellCost(const ShapeDef& spell) const;
    bool validateSpell(const ShapeDef& spell) const;
    void setBalanceParameters(float powerThreshold, float costThreshold);
    void setShapePreferences(const std::unordered_map<std::string, float>& preferences);
    void setEvolutionParameters(float mutationRate, float crossoverRate);

    // Event system
    void onSpellGenerated(std::function<void(const SpellInstance&)> callback);
    void onSynthesisComplete(std::function<void(const std::string&, const SynthesisGoal&)> callback);
    void onEvolutionProgress(std::function<void(int generation, double fitness)> callback);
    void onError(std::function<void(const std::string&)> callback);

    // Import/Export
    nlohmann::json exportSpellDefinitions() const;
    void importSpellDefinitions(const nlohmann::json& data);
    void exportToFile(const std::string& filePath) const;
    void importFromFile(const std::string& filePath);

    // Validation
    bool validateSpell(const std::string& spellId) const;
    std::vector<std::string> validateAllSpells() const;
    void runSpellTests(const std::string& spellId);

    // Performance optimization
    void enableParallelProcessing(bool enable = true);
    void setThreadPoolSize(int size);
    void enableMemoryPooling(bool enable = true);
    void setMemoryPoolSize(size_t size);

private:
    // Configuration and state
    AgentConfig m_config;
    AgentStats m_stats;
    bool m_initialized = false;
    bool m_watching = false;
    bool m_cachingEnabled = true;
    bool m_aiEnabled = false;

    // Core systems
    std::unique_ptr<SpellGenerator> m_spellGenerator;
    std::unique_ptr<SpellSynthesisManager> m_synthesisManager;
    std::unique_ptr<GrammarEngine> m_grammarEngine;
    std::unique_ptr<GeneticSpellEvolver> m_geneticEvolver;

    // Caching
    mutable std::shared_mutex m_cacheMutex;
    std::unordered_map<std::string, SpellInstance> m_spellCache;
    size_t m_maxCacheSize = 1000;

    // Event handlers
    std::vector<std::function<void(const SpellInstance&)>> m_spellGeneratedCallbacks;
    std::vector<std::function<void(const std::string&, const SynthesisGoal&)>> m_synthesisCallbacks;
    std::vector<std::function<void(int, double)>> m_evolutionCallbacks;
    std::vector<std::function<void(const std::string&)>> m_errorCallbacks;

    // AI enhancement
    nlohmann::json m_aiParams;
    std::vector<SpellDefinition> m_trainingData;
    
    // Spell Generation Module Integration
    std::unique_ptr<BalancedSpellFactory> m_balancedSpellFactory;
    std::unique_ptr<ShapeWeightManager> m_shapeWeightManager;
    std::unique_ptr<SpellBalanceSimulator> m_spellBalanceSimulator;
    std::unique_ptr<SpellEvolutionManager> m_spellEvolutionManager;
    std::unique_ptr<SpellShapeBalanceConfigManager> m_spellShapeBalanceConfigManager;
    std::unique_ptr<SpellShapeCacheManager> m_spellShapeCacheManager;
    std::unique_ptr<SpellShapeCostManager> m_spellShapeCostManager;
    std::unique_ptr<SpellShapeDefinitionManager> m_spellShapeDefinitionManager;
    
    // Balance parameters
    float m_powerThreshold = 1.0f;
    float m_costThreshold = 1.0f;
    float m_mutationRate = 0.1f;
    float m_crossoverRate = 0.3f;
    std::unordered_map<std::string, float> m_shapePreferences;
    
    // SpellStone generation
    std::unordered_map<std::string, std::vector<std::string>> m_spellStoneRecipes;
    std::mutex m_spellStoneRecipesMutex;

    // Performance monitoring
    std::chrono::high_resolution_clock::time_point m_lastMetricsTime;
    std::vector<double> m_generationTimes;
    std::vector<double> m_synthesisTimes;
    std::vector<double> m_evolutionTimes;

    // Helper methods
    void initializeSystems();
    void shutdownSystems();
    void setupEventHandlers();
    void cleanupEventHandlers();
    void updateStats();
    void emitSpellGeneratedEvent(const SpellInstance& spell);
    void emitSynthesisCompleteEvent(const std::string& spellId, const SynthesisGoal& goal);
    void emitEvolutionProgressEvent(int generation, double fitness);
    void emitErrorEvent(const std::string& error);
    void logError(const std::string& error);
    void updatePerformanceMetrics();
    void cleanupCache();
    bool shouldCache(const std::string& spellId) const;
    std::string generateUniqueId() const;
    void validateConfiguration() const;
    void setupLuaBindings(sol::state& lua);
    void setupAdvancedFeatures();
    void cleanupAdvancedFeatures();
};

} // namespace MagiTech::GeneratorAgent 
