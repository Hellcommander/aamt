#include "SnakeSpellFactory.hpp"
#include <stdexcept>

namespace MagiTech {
namespace SnakeSpells {

void SnakeSpellFactory::initialize(size_t num_threads) {
    if (m_initialized) return;
    m_pool = std::make_unique<MultithreadBusPlugin>(num_threads);
    m_initialized = true;
}

void SnakeSpellFactory::shutdown() {
    if (!m_initialized) return;
    m_pool.reset();
    m_initialized = false;
}

std::future<SnakeBundle> SnakeSpellFactory::generateAsync(
    const SnakeBodyParams& b,
    const MotionParams& m,
    const ScaleVFXParams& v,
    const ParticleParams& p,
    const AudioParams& a,
    const CollisionParams& c)
{
    return m_pool->enqueue([=]() {
        SnakeBundle sb;
        
        // Generate spline-based segmented mesh
        sb.mesh = SnakeMeshGen::buildSplineMesh(b);
        
        // Setup serpentine motion simulation
        sb.motionSim = MotionSim::setupSnake(b, m);
        
        // Setup scale VFX with glow and pulsation
        sb.vfx = ScaleVFXGen::setup(b.segmentCount, v);
        
        // Generate venom drip and smoke trail particles
        sb.particles = ParticleGen::buildVenomAndSmoke(p);
        
        // Load snake audio (hiss and rattle)
        sb.audio = AudioGen::loadSnakeAudio(a);
        
        // Build capsule chain collision
        float segmentLength = b.totalLength / b.segmentCount;
        sb.collider = CollisionGen::buildCapsuleChain(b.segmentCount, c, segmentLength);
        
        return sb;
    });
}

} // namespace SnakeSpells
} // namespace MagiTech
