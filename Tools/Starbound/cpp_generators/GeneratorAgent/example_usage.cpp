#include "MechAssetFactory.hpp"
#include "MechAssetLuaBindings.hpp"
#include <iostream>
#include <chrono>
#include <thread>

// Example: FormShiftMechGen Pipeline Integration
// This demonstrates how to use the FormShiftMechGen pipeline for creating
// and managing form-shifting Magitech mechs in your application.

class MechGameSystem {
private:
    MechAssetFactory mechFactory_;
    std::vector<MechInstanceState> activeInstances_;
    std::chrono::high_resolution_clock::time_point lastUpdate_;
    
public:
    MechGameSystem() {
        // Initialize the mech factory
        mechFactory_.setGPUAcceleration(true);
        lastUpdate_ = std::chrono::high_resolution_clock::now();
        
        std::cout << "MechGameSystem: Initialized FormShiftMechGen pipeline" << std::endl;
    }
    
    ~MechGameSystem() {
        // Clean up all instances
        for (auto& instance : activeInstances_) {
            mechFactory_.destroyInstance(instance);
        }
        activeInstances_.clear();
        
        std::cout << "MechGameSystem: Cleaned up all mech instances" << std::endl;
    }
    
    // Load a mech and create an instance
    MechInstanceState* createMechInstance(const std::string& mechName, 
                                        LODQuality quality = LODQuality::HIGH) {
        try {
            // Load the mech asset
            MechHandle mechHandle = mechFactory_.loadMech(mechName, quality);
            if (mechHandle == 0) {
                std::cerr << "Failed to load mech: " << mechName << std::endl;
                return nullptr;
            }
            
            // Create an instance
            MechInstanceState instance = mechFactory_.createInstance(mechHandle);
            if (!instance.isActive) {
                std::cerr << "Failed to create mech instance" << std::endl;
                return nullptr;
            }
            
            // Store the instance
            activeInstances_.push_back(instance);
            
            std::cout << "Created mech instance: " << mechName << std::endl;
            return &activeInstances_.back();
            
        } catch (const std::exception& e) {
            std::cerr << "Exception creating mech instance: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    // Start a morph transformation
    bool startMorph(MechInstanceState* instance, const std::string& profileName) {
        if (!instance) return false;
        
        bool success = mechFactory_.startMorph(*instance, profileName);
        if (success) {
            std::cout << "Started morph: " << profileName << std::endl;
        } else {
            std::cerr << "Failed to start morph: " << profileName << std::endl;
        }
        return success;
    }
    
    // Update all mech instances
    void update() {
        auto now = std::chrono::high_resolution_clock::now();
        auto deltaTime = std::chrono::duration_cast<std::chrono::milliseconds>(now - lastUpdate_).count() / 1000.0f;
        lastUpdate_ = now;
        
        // Update all instances
        for (auto& instance : activeInstances_) {
            if (instance.isActive) {
                mechFactory_.updateInstance(instance, deltaTime);
                
                // Log morph progress
                if (instance.isMorphing) {
                    std::cout << "Morph progress: " << (instance.morphProgress * 100.0f) << "%" << std::endl;
                }
            }
        }
        
        // Process hot reloads
        mechFactory_.processHotReloads();
    }
    
    // Get performance metrics
    void printPerformanceMetrics() {
        const MechPerformanceMetrics& metrics = mechFactory_.getPerformanceMetrics();
        
        std::cout << "\n=== Mech Performance Metrics ===" << std::endl;
        std::cout << "Total instances: " << metrics.totalInstances.load() << std::endl;
        std::cout << "Active instances: " << metrics.activeInstances.load() << std::endl;
        std::cout << "Morphing instances: " << metrics.morphingInstances.load() << std::endl;
        std::cout << "Cache hit rate: " << (metrics.getCacheHitRate() * 100.0) << "%" << std::endl;
        std::cout << "Average processing time: " << metrics.getAverageProcessingTime() << " ms" << std::endl;
        std::cout << "Cache size: " << mechFactory_.getCacheSize() << std::endl;
        std::cout << "================================\n" << std::endl;
    }
    
    // Enable hot reload for a mech
    void enableHotReload(const std::string& mechName) {
        if (mechFactory_.watchDefinition(mechName)) {
            std::cout << "Enabled hot reload for: " << mechName << std::endl;
        } else {
            std::cerr << "Failed to enable hot reload for: " << mechName << std::endl;
        }
    }
};

// Example: Lua Integration
void setupLuaIntegration(lua_State* L) {
    // Register the mech asset Lua bindings
    MagiTech::MechAssets::registerMechAssetLuaBindings(L);
    
    std::cout << "Lua integration: Registered mt_mech table" << std::endl;
}

// Example: Complete usage workflow
void demonstrateFormShiftMechGen() {
    std::cout << "=== FormShiftMechGen Pipeline Demo ===" << std::endl;
    
    // Create the game system
    MechGameSystem gameSystem;
    
    // Enable hot reload for development
    gameSystem.enableHotReload("phoenix_mk2");
    
    // Create a mech instance
    MechInstanceState* phoenix = gameSystem.createMechInstance("phoenix_mk2", LODQuality::HIGH);
    if (!phoenix) {
        std::cerr << "Failed to create Phoenix mech instance" << std::endl;
        return;
    }
    
    // Simulate game loop with morphing
    std::cout << "\nStarting mech morphing demonstration..." << std::endl;
    
    for (int frame = 0; frame < 300; ++frame) { // 5 seconds at 60fps
        // Update the game system
        gameSystem.update();
        
        // Trigger morphs at specific frames
        if (frame == 60) { // 1 second
            std::cout << "Triggering walker_to_flyer morph..." << std::endl;
            gameSystem.startMorph(phoenix, "walker_to_flyer");
        }
        else if (frame == 150) { // 2.5 seconds
            std::cout << "Triggering flyer_to_tank morph..." << std::endl;
            gameSystem.startMorph(phoenix, "flyer_to_tank");
        }
        else if (frame == 240) { // 4 seconds
            std::cout << "Triggering tank_to_walker morph..." << std::endl;
            gameSystem.startMorph(phoenix, "tank_to_walker");
        }
        
        // Print metrics every second
        if (frame % 60 == 0) {
            gameSystem.printPerformanceMetrics();
        }
        
        // Simulate 60fps
        std::this_thread::sleep_for(std::chrono::milliseconds(16));
    }
    
    std::cout << "\nFormShiftMechGen demonstration completed!" << std::endl;
}

// Example: Advanced usage with multiple mechs
void demonstrateAdvancedUsage() {
    std::cout << "\n=== Advanced FormShiftMechGen Usage ===" << std::endl;
    
    MechGameSystem gameSystem;
    
    // Create multiple mech instances
    MechInstanceState* mech1 = gameSystem.createMechInstance("phoenix_mk2", LODQuality::HIGH);
    MechInstanceState* mech2 = gameSystem.createMechInstance("phoenix_mk2", LODQuality::MEDIUM);
    
    if (mech1 && mech2) {
        std::cout << "Created two mech instances with different LOD qualities" << std::endl;
        
        // Start different morphs for each mech
        gameSystem.startMorph(mech1, "walker_to_flyer");
        gameSystem.startMorph(mech2, "flyer_to_tank");
        
        // Run for a few seconds
        for (int frame = 0; frame < 180; ++frame) {
            gameSystem.update();
            std::this_thread::sleep_for(std::chrono::milliseconds(16));
        }
        
        std::cout << "Advanced usage demonstration completed!" << std::endl;
    }
}

// Example: Performance testing
void demonstratePerformanceTesting() {
    std::cout << "\n=== FormShiftMechGen Performance Test ===" << std::endl;
    
    MechGameSystem gameSystem;
    
    // Create multiple instances to test performance
    std::vector<MechInstanceState*> instances;
    for (int i = 0; i < 10; ++i) {
        auto instance = gameSystem.createMechInstance("phoenix_mk2", LODQuality::MEDIUM);
        if (instance) {
            instances.push_back(instance);
        }
    }
    
    std::cout << "Created " << instances.size() << " mech instances" << std::endl;
    
    // Start morphing on all instances
    for (auto instance : instances) {
        gameSystem.startMorph(instance, "walker_to_flyer");
    }
    
    // Run performance test
    auto startTime = std::chrono::high_resolution_clock::now();
    
    for (int frame = 0; frame < 600; ++frame) { // 10 seconds
        gameSystem.update();
        
        if (frame % 60 == 0) {
            gameSystem.printPerformanceMetrics();
        }
        
        std::this_thread::sleep_for(std::chrono::milliseconds(16));
    }
    
    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    
    std::cout << "Performance test completed in " << duration.count() << "ms" << std::endl;
}

int main() {
    try {
        std::cout << "FormShiftMechGen Pipeline Examples" << std::endl;
        std::cout << "===================================" << std::endl;
        
        // Run basic demonstration
        demonstrateFormShiftMechGen();
        
        // Run advanced usage demonstration
        demonstrateAdvancedUsage();
        
        // Run performance testing
        demonstratePerformanceTesting();
        
        std::cout << "\nAll demonstrations completed successfully!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Exception in main: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}

// Example: Lua script integration
const char* luaMechScript = R"(
-- Example Lua script for FormShiftMechGen
print("Loading Phoenix mech...")

-- Load the mech
local mechHandle = mt_mech.load("phoenix_mk2", "HIGH")
if mechHandle == 0 then
    print("Failed to load mech!")
    return
end

-- Create instance
local instance = mt_mech.createInstance(mechHandle)
if not instance then
    print("Failed to create instance!")
    return
end

-- Enable hot reload
mt_mech.watchDefinition("phoenix_mk2")

-- Start morphing
print("Starting morph...")
mt_mech.startMorph(instance, "walker_to_flyer")

-- Game loop simulation
for i = 1, 300 do
    -- Update instance
    mt_mech.updateInstance(instance, 0.016) -- 60fps
    
    -- Check morph progress
    if instance.isMorphing then
        print("Morph progress: " .. (instance.morphProgress * 100) .. "%")
    end
    
    -- Process hot reloads
    mt_mech.processHotReloads()
    
    -- Simulate frame time
    -- (In real application, this would be handled by the game loop)
end

-- Clean up
mt_mech.destroyInstance(instance)
mt_mech.unload(mechHandle)
mt_mech.unwatchDefinition("phoenix_mk2")

print("Lua script completed!")
)";

// Example: How to run the Lua script
void runLuaScript(lua_State* L) {
    std::cout << "\n=== Running Lua Script ===" << std::endl;
    
    // Setup Lua integration
    setupLuaIntegration(L);
    
    // Run the script
    if (luaL_dostring(L, luaMechScript) != LUA_OK) {
        std::cerr << "Lua script error: " << lua_tostring(L, -1) << std::endl;
        lua_pop(L, 1);
    } else {
        std::cout << "Lua script executed successfully!" << std::endl;
    }
} 
