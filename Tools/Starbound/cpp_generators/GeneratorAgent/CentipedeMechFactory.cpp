#include "CentipedeMechFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace CentipedeMechs {

void CentipedeMechFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized = true;
    Log::info("CentipedeMechFactory initialized with {} threads", num_threads);
}

void CentipedeMechFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.reset();
    m_initialized = false;
    Log::info("CentipedeMechFactory shutdown complete");
}

std::future<MechBundle> CentipedeMechFactory::generateAsync(
    const MechParams& m,
    const LegParams& l,
    const CockpitParams& c,
    const HardpointParams& h)
{
    if (!m_initialized || !m_pool) {
        throw std::runtime_error("CentipedeMechFactory not initialized");
    }
    
    return m_pool->enqueue([=]() {
        Log::info("Starting async mech generation for: {}", m.id);
        
        MechBundle bundle;
        
        // Generate all components in parallel where possible
        auto segmentsFuture = m_pool->enqueue([=]() { return SegmentGen::buildSegments(m, l); });
        auto jointsFuture = m_pool->enqueue([=]() { return JointGen::buildJoints(m.segmentCount, l.jointRadius); });
        auto legsFuture = m_pool->enqueue([=]() { return LegGen::buildAllLegs(m.segmentCount, l); });
        
        // Wait for parallel components
        bundle.segments = segmentsFuture.get();
        bundle.joints = jointsFuture.get();
        bundle.legs = legsFuture.get();
        
        // Generate cockpit if needed
        if (c.hasCockpit) {
            bundle.cockpit = CockpitGen::buildCockpit(c);
        }
        
        // Generate weapons and sensors
        bundle.weapons = WeaponGen::buildHardpoints(h);
        bundle.sensorArray = SensorGen::buildRadar(h.enableRadarArray, h.radarRange);
        
        // Generate materials and effects
        bundle.materials = MaterialGen::assignMechMaterials(m.baseColor);
        bundle.vfx = VFXGen::buildDamageAndThrusterFX(m.segmentCount);
        bundle.audio = AudioGen::buildMechSounds();
        bundle.collider = CollisionGen::buildMechCollider(m, l);
        
        Log::info("Completed async mech generation for: {}", m.id);
        return bundle;
    });
}

} // namespace CentipedeMechs
} // namespace MagiTech
