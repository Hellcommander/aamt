#include "WormMechTypes.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace WormMechs {

void DynamicWormMech::applyBundle(const MechAssetBundle& bundle) {
    Log::info("WormMech", "Applying new asset bundle to dynamic mech: {} (mesh {}, skeleton {})",
              params->id, bundle.mesh, bundle.skeleton);
    // In a real implementation, this would swap out mesh pointers,
    // texture handles, skeleton data, etc. on the live game object.
}

void DynamicWormMech::setSegmentCount(int n) {
    int currentCount = static_cast<int>(m_segments.size());
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
    // Distance-based plating detail: close mechs get full detail.
    const float dist = glm::length(m_rootPosition - cameraPos);
    const int detail = (dist < 20.0f) ? 3 : (dist < 50.0f) ? 2 : 1;

    if (detail != m_currentDetailLevel) {
        Log::info("WormMech", "Updating LOD for {} to level {}", params->id, detail);
        m_currentDetailLevel = detail;

        // This triggers the regeneration through the Observable
        auto p = params.get();
        p.platingDetailLevel = detail;
        params.set(p);
    }
}

void DynamicWormMech::addSegment(int index) {
    Log::info("WormMech", "Adding segment {} to dynamic mech: {}", index, params->id);
    // This would involve creating a new mesh/bone and attaching it.
    // For now, we just track the handle.
    m_segments.push_back(static_cast<SegmentHandle>(index + 1));
}

void DynamicWormMech::removeSegment(SegmentHandle handle) {
    Log::info("WormMech", "Removing segment {} from dynamic mech: {}", handle, params->id);
    // This would remove the corresponding game object and its resources.
}

void DynamicWormMech::updateSpline() {
    Log::info("WormMech", "Updating spline for dynamic mech: {}", params->id);
    // This would re-calculate joint positions, IK chains, etc.
}


} // namespace WormMechs
} // namespace MagiTech
