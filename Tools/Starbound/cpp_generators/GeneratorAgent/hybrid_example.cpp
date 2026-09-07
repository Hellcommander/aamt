#include "MechFactory.hpp"
#include "MechGenerators.hpp"
#include "MechLuaBindings.hpp"
#include <iostream>
#include <chrono>
#include <thread>
#include <future>
#include <vector>
#include <memory>

// Example: Hybrid C++23/26 + Lua In-Game Multi-Form Mech Generator
// This demonstrates the enhanced pipeline with procedural generation,
// multi-form support, and comprehensive Lua integration.

class HybridMechGameSystem {
private:
    std::unique_ptr<MechFactory> mechFactory_;
    std::vector<MechInstanceState> activeInstances_;
    std::chrono::high_resolution_clock::time_point lastUpdate_;
    lua_State* luaState_;
    
public:
    HybridMechGameSystem() {
        // Initialize the enhanced mech factory
        mechFactory_ = std::make_unique<MechFactory>();
        mechFactory_->initialize(100, 4); // 100 cache entries, 4 threads
        mechFactory_->setGPUAcceleration(true);
        
        // Initialize Lua state
        luaState_ = luaL_newstate();
        luaL_openlibs(luaState_);
        
        // Register enhanced Lua bindings
        registerMechLuaBindings(luaState_);
        
        lastUpdate_ = std::chrono::high_resolution_clock::now();
        
        std::cout << "HybridMechGameSystem: Initialized enhanced pipeline" << std::endl;
    }
    
    ~HybridMechGameSystem() {
        // Clean up instances
        for (auto& instance : activeInstances_) {
            mechFactory_->destroyInstance(instance);
        }
        activeInstances_.clear();
        
        // Clean up Lua
        if (luaState_) {
            lua_close(luaState_);
        }
        
        std::cout << "HybridMechGameSystem: Cleaned up all resources" << std::endl;
    }
    
    // Demonstrate hybrid C++23/26 + Lua mech generation
    void demonstrateHybridGeneration() {
        std::cout << "\n=== Hybrid C++23/26 + Lua Mech Generation Demo ===" << std::endl;
        
        // 1. Create mech parameters in Lua
        const char* luaScript = R"(
            -- Create a scout mech with hybrid features
            local scoutParams = {
                id = "recon_biped",
                style = "scout",
                forms = {"mobile", "siege", "stealth"},
                colorPrimary = {0.2, 0.8, 0.3},
                colorAccent = {1.0, 0.6, 0.1},
                limbCount = 2,
                torsoSize = {1.0, 1.2, 0.6},
                limbLength = 0.8,
                armorPlates = true,
                weaponMounts = {"shoulder", "arm"},
                pattern = "hexCamouflage",
                detailLevel = 2,
                pulseEmission = true,
                
                -- Enhanced hybrid features
                variant = "recon",
                armorTypes = {"light", "reactive"},
                weaponTypes = {"pulse_rifle", "missile_pod"},
                scale = {1.0, 1.0, 1.0},
                mass = 800.0,
                enableGlow = true,
                enableShield = false,
                aiBehavior = "stealth",
                crewCapacity = 1,
                maxSpeed = 15.0,
                jumpHeight = 3.0,
                canFly = false,
                canSwim = true,
                faction = "alliance",
                abilities = {"cloak", "emp_blast", "rapid_fire"},
                stats = {
                    armor = 0.7,
                    speed = 0.9,
                    firepower = 0.6,
                    stealth = 0.8
                },
                
                -- Procedural generation
                noiseScale = 2.0,
                patternIntensity = 0.7,
                textureResolution = 1024,
                generateNormalMap = true,
                generateRoughnessMap = true,
                generateMetallicMap = true,
                
                -- Animation
                morphDuration = 1.2,
                morphCurve = "easeInOut",
                enableIK = true,
                enablePhysics = true
            }
            
            -- Create a heavy mech
            local heavyParams = {
                id = "atlas_tank",
                style = "heavy",
                forms = {"drive", "tower", "siege"},
                colorPrimary = {0.2, 0.2, 0.2},
                colorAccent = {1.0, 0.1, 0.1},
                limbCount = 0,
                torsoSize = {1.5, 0.8, 1.2},
                armorPlates = true,
                weaponMounts = {"top", "sides"},
                pattern = "techDamaged",
                detailLevel = 2,
                pulseEmission = false,
                
                -- Enhanced features
                variant = "assault",
                armorTypes = {"heavy", "reactive", "ablative"},
                weaponTypes = {"railgun", "plasma_cannon", "mortar"},
                scale = {1.2, 1.0, 1.1},
                mass = 2500.0,
                enableGlow = false,
                enableShield = true,
                aiBehavior = "aggressive",
                crewCapacity = 3,
                maxSpeed = 8.0,
                jumpHeight = 1.0,
                canFly = false,
                canSwim = false,
                faction = "empire",
                abilities = {"shield_wall", "artillery_strike", "emp_blast"},
                stats = {
                    armor = 0.9,
                    speed = 0.4,
                    firepower = 0.9,
                    stealth = 0.2
                }
            }
            
            -- Generate mechs using the hybrid pipeline
            print("Generating scout mech...")
            local scoutFuture = mt_mech.generateAsync(scoutParams)
            
            print("Generating heavy mech...")
            local heavyFuture = mt_mech.generateSync(heavyParams)
            
            -- Create instances
            local scoutInstance = mt_mech.createInstance(scoutParams)
            local heavyInstance = mt_mech.createInstance(heavyParams)
            
            -- Start morphing
            mt_mech.startMorph(scoutInstance, "mobile")
            mt_mech.startMorph(heavyInstance, "drive")
            
            print("Hybrid mech generation completed!")
        )";
        
        // Execute Lua script
        if (luaL_dostring(luaState_, luaScript) != LUA_OK) {
            std::cerr << "Lua script error: " << lua_tostring(luaState_, -1) << std::endl;
            lua_pop(luaState_, 1);
            return;
        }
        
        std::cout << "Lua script executed successfully!" << std::endl;
    }
    
    // Demonstrate procedural generation
    void demonstrateProceduralGeneration() {
        std::cout << "\n=== Procedural Generation Demo ===" << std::endl;
        
        // Create procedural parameters
        ProceduralParams procParams;
        procParams.frequency = 2.0f;
        procParams.amplitude = 1.5f;
        procParams.octaves = 6;
        procParams.patternType = "hexagonal";
        procParams.patternScale = 1.2f;
        procParams.roughness = 0.3f;
        procParams.metallic = 0.8f;
        procParams.emissive = 0.2f;
        
        mechFactory_->setProceduralParams(procParams);
        
        // Generate procedural mechs
        std::vector<MechParams> proceduralMechs;
        
        // Scout variant
        MechParams scout = createScoutTemplate();
        scout.id = "proc_scout_01";
        scout.pattern = "hexCamouflage";
        scout.colorPrimary = glm::vec3(0.1f, 0.7f, 0.2f);
        scout.colorAccent = glm::vec3(0.9f, 0.5f, 0.1f);
        proceduralMechs.push_back(scout);
        
        // Heavy variant
        MechParams heavy = createHeavyTemplate();
        heavy.id = "proc_heavy_01";
        heavy.pattern = "techDamaged";
        heavy.colorPrimary = glm::vec3(0.3f, 0.3f, 0.3f);
        heavy.colorAccent = glm::vec3(0.8f, 0.1f, 0.1f);
        proceduralMechs.push_back(heavy);
        
        // Support variant
        MechParams support = createSupportTemplate();
        support.id = "proc_support_01";
        support.pattern = "techClean";
        support.colorPrimary = glm::vec3(0.2f, 0.2f, 0.6f);
        support.colorAccent = glm::vec3(0.1f, 0.8f, 0.9f);
        proceduralMechs.push_back(support);
        
        // Generate batch
        std::vector<std::future<MechBundle>> futures;
        for (const auto& params : proceduralMechs) {
            futures.push_back(mechFactory_->generateAsync(params));
        }
        
        // Wait for completion and create instances
        for (size_t i = 0; i < futures.size(); ++i) {
            try {
                MechBundle bundle = futures[i].get();
                MechInstanceState instance = mechFactory_->createInstance(proceduralMechs[i]);
                instance.bundle = bundle;
                activeInstances_.push_back(instance);
                
                std::cout << "Generated procedural mech: " << proceduralMechs[i].id << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "Failed to generate mech " << proceduralMechs[i].id << ": " << e.what() << std::endl;
            }
        }
    }
    
    // Demonstrate multi-form morphing
    void demonstrateMultiFormMorphing() {
        std::cout << "\n=== Multi-Form Morphing Demo ===" << std::endl;
        
        if (activeInstances_.empty()) {
            std::cout << "No instances available for morphing demo" << std::endl;
            return;
        }
        
        // Get first instance
        MechInstanceState& instance = activeInstances_[0];
        
        // Demonstrate form transitions
        std::vector<std::string> forms = {"mobile", "siege", "stealth", "mobile"};
        
        for (size_t i = 0; i < forms.size(); ++i) {
            std::cout << "Morphing to form: " << forms[i] << std::endl;
            
            if (mechFactory_->startMorph(instance, forms[i])) {
                // Simulate morphing process
                for (int frame = 0; frame < 60; ++frame) { // 1 second at 60fps
                    float progress = frame / 60.0f;
                    mechFactory_->setMorphProgress(instance, progress);
                    
                    // Update instance
                    mechFactory_->updateInstance(instance, 1.0f / 60.0f);
                    
                    if (frame % 20 == 0) {
                        std::cout << "  Morph progress: " << (progress * 100.0f) << "%" << std::endl;
                    }
                    
                    std::this_thread::sleep_for(std::chrono::milliseconds(16));
                }
            }
            
            // Pause between forms
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }
    
    // Demonstrate performance monitoring
    void demonstratePerformanceMonitoring() {
        std::cout << "\n=== Performance Monitoring Demo ===" << std::endl;
        
        const MechPerformanceMetrics& metrics = mechFactory_->getPerformanceMetrics();
        
        std::cout << "Performance Metrics:" << std::endl;
        std::cout << "  Total generations: " << metrics.totalGenerations.load() << std::endl;
        std::cout << "  Cache hits: " << metrics.cacheHits.load() << std::endl;
        std::cout << "  Cache misses: " << metrics.cacheMisses.load() << std::endl;
        std::cout << "  Cache hit rate: " << (metrics.getCacheHitRate() * 100.0) << "%" << std::endl;
        std::cout << "  Average generation time: " << metrics.getAverageGenerationTime() << " ms" << std::endl;
        std::cout << "  Active instances: " << metrics.activeInstances.load() << std::endl;
        std::cout << "  Morphing instances: " << metrics.morphingInstances.load() << std::endl;
        std::cout << "  Peak memory usage: " << metrics.peakMemoryUsage.load() << " bytes" << std::endl;
    }
    
    // Demonstrate template system
    void demonstrateTemplateSystem() {
        std::cout << "\n=== Template System Demo ===" << std::endl;
        
        // Register custom templates
        MechParams customScout = createScoutTemplate();
        customScout.id = "custom_scout";
        customScout.style = "custom";
        customScout.colorPrimary = glm::vec3(0.8f, 0.2f, 0.8f); // Purple
        mechFactory_->registerTemplate("custom_scout", customScout);
        
        MechParams customHeavy = createHeavyTemplate();
        customHeavy.id = "custom_heavy";
        customHeavy.style = "custom";
        customHeavy.colorPrimary = glm::vec3(0.8f, 0.8f, 0.2f); // Yellow
        mechFactory_->registerTemplate("custom_heavy", customHeavy);
        
        // Get available templates
        std::vector<std::string> templates = mechFactory_->getAvailableTemplates();
        std::cout << "Available templates:" << std::endl;
        for (const auto& template_ : templates) {
            std::cout << "  - " << template_ << std::endl;
        }
        
        // Create from template
        MechParams fromTemplate = mechFactory_->createFromTemplate("custom_scout");
        fromTemplate.id = "template_instance";
        
        MechBundle bundle = mechFactory_->generateSync(fromTemplate);
        MechInstanceState instance = mechFactory_->createInstance(fromTemplate);
        instance.bundle = bundle;
        activeInstances_.push_back(instance);
        
        std::cout << "Created mech from template: " << fromTemplate.id << std::endl;
    }
    
    // Demonstrate hot reload
    void demonstrateHotReload() {
        std::cout << "\n=== Hot Reload Demo ===" << std::endl;
        
        // Watch for definition changes
        mechFactory_->watchDefinition("test_mech");
        
        std::cout << "Watching for definition changes..." << std::endl;
        std::cout << "Edit the mech definition file to see hot reload in action" << std::endl;
        
        // Process hot reloads for a few seconds
        for (int i = 0; i < 30; ++i) {
            mechFactory_->processHotReloads();
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        mechFactory_->unwatchDefinition("test_mech");
    }
    
    // Main demonstration
    void runFullDemonstration() {
        std::cout << "=== Hybrid C++23/26 + Lua Mech Generator Full Demo ===" << std::endl;
        
        // 1. Hybrid generation
        demonstrateHybridGeneration();
        
        // 2. Procedural generation
        demonstrateProceduralGeneration();
        
        // 3. Multi-form morphing
        demonstrateMultiFormMorphing();
        
        // 4. Performance monitoring
        demonstratePerformanceMonitoring();
        
        // 5. Template system
        demonstrateTemplateSystem();
        
        // 6. Hot reload
        demonstrateHotReload();
        
        std::cout << "\n=== Full demonstration completed! ===" << std::endl;
    }
    
private:
    // Template creation helpers
    MechParams createScoutTemplate() {
        MechParams params;
        params.style = "scout";
        params.forms = {"mobile", "stealth"};
        params.limbCount = 2;
        params.torsoSize = glm::vec3(1.0f, 1.2f, 0.6f);
        params.limbLength = 0.8f;
        params.armorPlates = true;
        params.weaponMounts = {"shoulder", "arm"};
        params.pattern = "hexCamouflage";
        params.detailLevel = 2;
        params.pulseEmission = true;
        params.maxSpeed = 15.0f;
        params.jumpHeight = 3.0f;
        params.canSwim = true;
        return params;
    }
    
    MechParams createHeavyTemplate() {
        MechParams params;
        params.style = "heavy";
        params.forms = {"drive", "tower", "siege"};
        params.limbCount = 0;
        params.torsoSize = glm::vec3(1.5f, 0.8f, 1.2f);
        params.armorPlates = true;
        params.weaponMounts = {"top", "sides"};
        params.pattern = "techDamaged";
        params.detailLevel = 2;
        params.pulseEmission = false;
        params.maxSpeed = 8.0f;
        params.jumpHeight = 1.0f;
        params.canFly = false;
        params.canSwim = false;
        return params;
    }
    
    MechParams createSupportTemplate() {
        MechParams params;
        params.style = "support";
        params.forms = {"mobile", "turret", "repair"};
        params.limbCount = 2;
        params.torsoSize = glm::vec3(1.2f, 1.0f, 0.8f);
        params.limbLength = 0.9f;
        params.armorPlates = true;
        params.weaponMounts = {"back", "arm"};
        params.pattern = "techClean";
        params.detailLevel = 2;
        params.pulseEmission = true;
        params.maxSpeed = 12.0f;
        params.jumpHeight = 2.0f;
        params.canFly = false;
        params.canSwim = true;
        return params;
    }
};

// Main function to run the demonstration
int main() {
    try {
        HybridMechGameSystem gameSystem;
        gameSystem.runFullDemonstration();
        
        std::cout << "\nHybrid mech generator demonstration completed successfully!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception in main: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
} 
