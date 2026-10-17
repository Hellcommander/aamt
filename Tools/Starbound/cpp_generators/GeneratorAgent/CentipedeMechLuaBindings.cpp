#include "CentipedeMechLuaBindings.hpp"
#include "CentipedeMechFactory.hpp"
#include "core/Log.hpp"
#include <vector>
#include <chrono>
#include <memory>
#include <mutex>
#include <stdexcept>

namespace MagiTech {
namespace CentipedeMechs {

static std::vector<std::pair<std::future<MechBundle>, std::string>> pendingMechs;
static std::mutex pendingMechsMutex;

static std::mutex factoryMutex;
static std::shared_ptr<CentipedeMechFactory> g_mechFactory;

void CentipedeMechLuaBindings::setFactory(std::shared_ptr<CentipedeMechFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex);
    g_mechFactory = std::move(factory);
}

std::shared_ptr<CentipedeMechFactory> CentipedeMechLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex);
    if (!g_mechFactory) {
        g_mechFactory = std::make_shared<CentipedeMechFactory>();
        g_mechFactory->initialize(4); // 4 threads for generation
    }
    return g_mechFactory;
}

// Validation functions for parameters
bool validateMechParams(const MechParams& params) {
    if (params.id.empty()) {
        Log::error("MechParams: id cannot be empty");
        return false;
    }
    if (params.segmentCount < 3 || params.segmentCount > 20) {
        Log::error("CentipedeMech", "MechParams: segmentCount must be between 3 and 20, got {}", params.segmentCount);
        return false;
    }
    if (params.segmentLength <= 0.0f || params.segmentLength > 5.0f) {
        Log::error("CentipedeMech", "MechParams: segmentLength must be between 0.1 and 5.0, got {}", params.segmentLength);
        return false;
    }
    if (params.segmentRadius <= 0.0f || params.segmentRadius > 2.0f) {
        Log::error("CentipedeMech", "MechParams: segmentRadius must be between 0.1 and 2.0, got {}", params.segmentRadius);
        return false;
    }
    return true;
}

bool validateLegParams(const LegParams& params) {
    if (params.legsPerSegment < 1 || params.legsPerSegment > 8) {
        Log::error("CentipedeMech", "LegParams: legsPerSegment must be between 1 and 8, got {}", params.legsPerSegment);
        return false;
    }
    if (params.upperLegLength <= 0.0f || params.upperLegLength > 3.0f) {
        Log::error("CentipedeMech", "LegParams: upperLegLength must be between 0.1 and 3.0, got {}", params.upperLegLength);
        return false;
    }
    if (params.lowerLegLength <= 0.0f || params.lowerLegLength > 3.0f) {
        Log::error("CentipedeMech", "LegParams: lowerLegLength must be between 0.1 and 3.0, got {}", params.lowerLegLength);
        return false;
    }
    if (params.jointRadius <= 0.0f || params.jointRadius > 1.0f) {
        Log::error("CentipedeMech", "LegParams: jointRadius must be between 0.05 and 1.0, got {}", params.jointRadius);
        return false;
    }
    if (params.footType.empty()) {
        Log::error("LegParams: footType cannot be empty");
        return false;
    }
    return true;
}

bool validateCockpitParams(const CockpitParams& params) {
    if (params.width <= 0.0f || params.width > 5.0f) {
        Log::error("CentipedeMech", "CockpitParams: width must be between 0.5 and 5.0, got {}", params.width);
        return false;
    }
    if (params.height <= 0.0f || params.height > 3.0f) {
        Log::error("CentipedeMech", "CockpitParams: height must be between 0.5 and 3.0, got {}", params.height);
        return false;
    }
    if (params.depth <= 0.0f || params.depth > 5.0f) {
        Log::error("CentipedeMech", "CockpitParams: depth must be between 0.5 and 5.0, got {}", params.depth);
        return false;
    }
    if (params.displayCount < 0 || params.displayCount > 20) {
        Log::error("CentipedeMech", "CockpitParams: displayCount must be between 0 and 20, got {}", params.displayCount);
        return false;
    }
    return true;
}

bool validateHardpointParams(const HardpointParams& params) {
    if (params.missileTubes < 0 || params.missileTubes > 20) {
        Log::error("CentipedeMech", "HardpointParams: missileTubes must be between 0 and 20, got {}", params.missileTubes);
        return false;
    }
    if (params.autocannonSlots < 0 || params.autocannonSlots > 10) {
        Log::error("CentipedeMech", "HardpointParams: autocannonSlots must be between 0 and 10, got {}", params.autocannonSlots);
        return false;
    }
    if (params.radarRange < 0.0f || params.radarRange > 1000.0f) {
        Log::error("CentipedeMech", "HardpointParams: radarRange must be between 0 and 1000, got {}", params.radarRange);
        return false;
    }
    return true;
}

// Validates all parameter groups and queues an async generation; returns the mech ID for tracking.
static std::string spawnCentipedeMech(const MechParams& m, const LegParams& l, const CockpitParams& c, const HardpointParams& h) {
    // Validate all parameters
    if (!validateMechParams(m)) {
        throw std::runtime_error("Invalid MechParams");
    }
    if (!validateLegParams(l)) {
        throw std::runtime_error("Invalid LegParams");
    }
    if (!validateCockpitParams(c)) {
        throw std::runtime_error("Invalid CockpitParams");
    }
    if (!validateHardpointParams(h)) {
        throw std::runtime_error("Invalid HardpointParams");
    }

    Log::info("CentipedeMech", "Starting centipede mech generation: {}", m.id);
    auto startTime = std::chrono::high_resolution_clock::now();

    auto future = CentipedeMechLuaBindings::factory()->generateAsync(m, l, c, h);
    {
        std::lock_guard<std::mutex> lock(pendingMechsMutex);
        pendingMechs.emplace_back(std::move(future), m.id);
    }

    auto endTime = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    Log::info("CentipedeMech", "Queued mech generation for {} (took {}ms)", m.id, duration.count());

    return m.id; // Return the mech ID for tracking
}

void CentipedeMechLuaBindings::bind(sol::state& lua) {
    // Bind MechParams with validation
    lua.new_usertype<MechParams>("MechParams", 
        sol::constructors<MechParams()>(),
        "id", &MechParams::id,
        "segmentCount", &MechParams::segmentCount,
        "segmentLength", &MechParams::segmentLength,
        "segmentRadius", &MechParams::segmentRadius,
        "baseColor", &MechParams::baseColor,
        "seamlessJoints", &MechParams::seamlessJoints,
        "validate", [](const MechParams& p) { return validateMechParams(p); }
    );

    // Bind LegParams with validation
    lua.new_usertype<LegParams>("LegParams", 
        sol::constructors<LegParams()>(),
        "legsPerSegment", &LegParams::legsPerSegment,
        "upperLegLength", &LegParams::upperLegLength,
        "lowerLegLength", &LegParams::lowerLegLength,
        "jointRadius", &LegParams::jointRadius,
        "armorPlates", &LegParams::armorPlates,
        "footType", &LegParams::footType,
        "validate", [](const LegParams& p) { return validateLegParams(p); }
    );

    // Bind CockpitParams with validation
    lua.new_usertype<CockpitParams>("CockpitParams", 
        sol::constructors<CockpitParams()>(),
        "hasCockpit", &CockpitParams::hasCockpit,
        "cockpitPosition", &CockpitParams::cockpitPosition,
        "width", &CockpitParams::width,
        "height", &CockpitParams::height,
        "depth", &CockpitParams::depth,
        "enableDisplays", &CockpitParams::enableDisplays,
        "displayCount", &CockpitParams::displayCount,
        "seatMaterial", &CockpitParams::seatMaterial,
        "controlStyle", &CockpitParams::controlStyle,
        "validate", [](const CockpitParams& p) { return validateCockpitParams(p); }
    );

    // Bind HardpointParams with validation
    lua.new_usertype<HardpointParams>("HardpointParams", 
        sol::constructors<HardpointParams()>(),
        "missileTubes", &HardpointParams::missileTubes,
        "autocannonSlots", &HardpointParams::autocannonSlots,
        "enableTurret", &HardpointParams::enableTurret,
        "enableRadarArray", &HardpointParams::enableRadarArray,
        "radarRange", &HardpointParams::radarRange,
        "validate", [](const HardpointParams& p) { return validateHardpointParams(p); }
    );

    // Bind MechBundle with detailed information
    lua.new_usertype<MechBundle>("MechBundle", 
        sol::no_constructor,
        "segments", &MechBundle::segments,
        "joints", &MechBundle::joints,
        "legs", &MechBundle::legs,
        "cockpit", &MechBundle::cockpit,
        "weapons", &MechBundle::weapons,
        "sensorArray", &MechBundle::sensorArray,
        "materials", &MechBundle::materials,
        "vfx", &MechBundle::vfx,
        "audio", &MechBundle::audio,
        "collider", &MechBundle::collider,
        "getSegmentCount", [](const MechBundle& b) { return b.segments.size(); },
        "getJointCount", [](const MechBundle& b) { return b.joints.size(); },
        "getLegCount", [](const MechBundle& b) { return b.legs.size(); },
        "hasCockpit", [](const MechBundle& b) { return b.cockpit != 0; },
        "hasWeapons", [](const MechBundle& b) { return b.weapons != 0; },
        "hasSensors", [](const MechBundle& b) { return b.sensorArray != 0; }
    );

    // Initialize the factory (or pick up the one shared via setFactory)
    factory();

    // Main spawn function with comprehensive validation
    lua.set_function("spawn_centipede_mech", &spawnCentipedeMech);

    // Helper functions for creating common mech configurations
    lua.set_function("create_scout_mech", []() {
        MechParams m;
        m.id = "Scout_MK_I";
        m.segmentCount = 6;
        m.segmentLength = 0.8f;
        m.segmentRadius = 0.2f;
        m.baseColor = {0.2f, 0.8f, 0.2f, 1.0f};
        m.seamlessJoints = true;

        LegParams l;
        l.legsPerSegment = 2;
        l.upperLegLength = 0.6f;
        l.lowerLegLength = 0.4f;
        l.jointRadius = 0.08f;
        l.armorPlates = false;
        l.footType = "Pad";

        CockpitParams c;
        c.hasCockpit = true;
        c.cockpitPosition = {0, 0, 0};
        c.width = 0.8f;
        c.height = 0.6f;
        c.depth = 1.0f;
        c.enableDisplays = true;
        c.displayCount = 2;
        c.seatMaterial = "Light";
        c.controlStyle = "Joystick";

        HardpointParams h;
        h.missileTubes = 1;
        h.autocannonSlots = 0;
        h.enableTurret = false;
        h.enableRadarArray = true;
        h.radarRange = 200.0f;

        return spawnCentipedeMech(m, l, c, h);
    });

    lua.set_function("create_assault_mech", []() {
        MechParams m;
        m.id = "Assault_MK_I";
        m.segmentCount = 10;
        m.segmentLength = 1.4f;
        m.segmentRadius = 0.4f;
        m.baseColor = {0.8f, 0.2f, 0.2f, 1.0f};
        m.seamlessJoints = true;

        LegParams l;
        l.legsPerSegment = 4;
        l.upperLegLength = 1.0f;
        l.lowerLegLength = 0.8f;
        l.jointRadius = 0.12f;
        l.armorPlates = true;
        l.footType = "Claw";

        CockpitParams c;
        c.hasCockpit = true;
        c.cockpitPosition = {0, 0, 0};
        c.width = 1.2f;
        c.height = 1.0f;
        c.depth = 1.4f;
        c.enableDisplays = true;
        c.displayCount = 6;
        c.seatMaterial = "Heavy";
        c.controlStyle = "Holographic";

        HardpointParams h;
        h.missileTubes = 4;
        h.autocannonSlots = 2;
        h.enableTurret = true;
        h.enableRadarArray = true;
        h.radarRange = 500.0f;

        return spawnCentipedeMech(m, l, c, h);
    });

    lua.set_function("create_heavy_mech", []() {
        MechParams m;
        m.id = "Heavy_MK_I";
        m.segmentCount = 12;
        m.segmentLength = 1.6f;
        m.segmentRadius = 0.5f;
        m.baseColor = {0.3f, 0.3f, 0.8f, 1.0f};
        m.seamlessJoints = true;

        LegParams l;
        l.legsPerSegment = 6;
        l.upperLegLength = 1.2f;
        l.lowerLegLength = 1.0f;
        l.jointRadius = 0.15f;
        l.armorPlates = true;
        l.footType = "Tread";

        CockpitParams c;
        c.hasCockpit = true;
        c.cockpitPosition = {0, 0, 0};
        c.width = 1.5f;
        c.height = 1.2f;
        c.depth = 1.8f;
        c.enableDisplays = true;
        c.displayCount = 8;
        c.seatMaterial = "Command";
        c.controlStyle = "Levers";

        HardpointParams h;
        h.missileTubes = 8;
        h.autocannonSlots = 4;
        h.enableTurret = true;
        h.enableRadarArray = true;
        h.radarRange = 800.0f;

        return spawnCentipedeMech(m, l, c, h);
    });

    // Utility functions
    lua.set_function("get_pending_mech_count", []() {
        std::lock_guard<std::mutex> lock(pendingMechsMutex);
        return pendingMechs.size();
    });

    lua.set_function("clear_pending_mechs", []() {
        std::lock_guard<std::mutex> lock(pendingMechsMutex);
        pendingMechs.clear();
        Log::info("Cleared all pending mech generations");
    });

    lua.set_function("get_mech_factory_status", []() {
        std::lock_guard<std::mutex> lock(factoryMutex);
        return g_mechFactory && g_mechFactory->isInitialized();
    });

    Log::info("CentipedeMechLuaBindings initialized with comprehensive interface");
}

void CentipedeMechLuaBindings::poll_assets(sol::state& lua) {
    auto startTime = std::chrono::high_resolution_clock::now();
    int completedCount = 0;

    // Take the finished futures out under the lock, then run callbacks without
    // holding it (a Lua callback may queue another mech).
    std::vector<std::pair<std::future<MechBundle>, std::string>> ready;
    {
        std::lock_guard<std::mutex> lock(pendingMechsMutex);
        for (auto it = pendingMechs.begin(); it != pendingMechs.end();) {
            if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                ready.push_back(std::move(*it));
                it = pendingMechs.erase(it);
            } else {
                ++it;
            }
        }
    }

    for (auto& [future, mechId] : ready) {
        try {
            auto bundle = future.get();
            auto endTime = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);

            Log::info("CentipedeMech", "Centipede mech asset ready: {} ({} segments, {} legs, {} joints, polled in {}ms)",
                mechId,
                bundle.segments.size(),
                bundle.legs.size(),
                bundle.joints.size(),
                duration.count());

            // Call Lua callback if available
            sol::protected_function callback = lua["on_mech_generated"];
            if (callback.valid()) {
                auto result = callback(mechId, bundle);
                if (!result.valid()) {
                    sol::error err = result;
                    Log::error("CentipedeMech", "on_mech_generated failed for {}: {}", mechId, err.what());
                }
            }

            completedCount++;
        } catch (const std::exception& e) {
            Log::error("CentipedeMech", "Error generating mech {}: {}", mechId, e.what());
        }
    }

    if (completedCount > 0) {
        Log::info("CentipedeMech", "Completed {} mech generations", completedCount);
    }
}

void CentipedeMechLuaBindings::shutdown() {
    {
        std::lock_guard<std::mutex> lock(factoryMutex);
        if (g_mechFactory) {
            g_mechFactory->shutdown();
            g_mechFactory.reset();
        }
    }
    std::lock_guard<std::mutex> lock(pendingMechsMutex);
    pendingMechs.clear();
    Log::info("CentipedeMechLuaBindings shutdown complete");
}

} // namespace CentipedeMechs
} // namespace MagiTech
