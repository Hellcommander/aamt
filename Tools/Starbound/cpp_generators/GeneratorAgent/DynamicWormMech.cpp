#include "WormMechTypes.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace WormMechs {

void DynamicWormMech::applyBundle(const MechAssetBundle& bundle) {
    Log::info("Applying new asset bundle to dynamic mech: {}", params->id);
    // In a real implementation, this would swap out mesh pointers,
    // texture handles, skeleton data, etc. on the live game object.
}

void DynamicWormMech::setSegmentCount(int n) {
    int currentCount = m_segments.size();
    if (n > currentCount) {
        for (int i = currentCount; i < n; ++i) {
            addSegment(i);
        }
    } else if (n < currentCount) {
        for (int i = currentCount - 1; i >= n; --i) {
            removeSegment(m_segments[i]);
        }
        m_segments.resize(n);
    }
    updateSpline();
}

void DynamicWormMech::updateLOD(const glm::vec3& cameraPos) {
    // Simplified distance check
    // float dist = glm::length(m_rootPosition - cameraPos);
    // int detail = (dist < 20) ? 3 : (dist < 50) ? 2 : 1;
    //
    // if (detail != m_currentDetailLevel) {
    //     Log::info("Updating LOD for {} to level {}", params->id, detail);
    //     m_currentDetailLevel = detail;
    //     
    //     // This triggers the regeneration through the Observable
    //     auto p = params.get();
    //     p.platingDetailLevel = detail;
    //     params.set(p);
    // }
}

void DynamicWormMech::addSegment(int index) {
    Log::info("Adding segment {} to dynamic mech: {}", index, params->id);
    // This would involve creating a new mesh/bone and attaching it.
    // For now, we just track the handle.
    m_segments.push_back(index + 1); // Placeholder handle
}

void DynamicWormMech::removeSegment(SegmentHandle handle) {
    Log::info("Removing segment {} from dynamic mech: {}", handle, params->id);
    // This would remove the corresponding game object and its resources.
}

void DynamicWormMech::updateSpline() {
    Log::info("Updating spline for dynamic mech: {}", params->id);
    // This would re-calculate joint positions, IK chains, etc.
}


} // namespace WormMechs
} // namespace MagiTech
