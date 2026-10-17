#pragma once

#include "LightTypes.hpp"
#include <algorithm>
#include <cstddef>
#include <vector>

namespace mt::light {

// One level of detail of a light: used while the light's projected screen size is >= screenSize.
struct LightLODLevel {
    float screenSize{0.0f}; // normalized projected size threshold (0..1)
    int   shadowRes{0};     // shadow map resolution at this level (0 = no shadows)
    bool  volumetric{true}; // volumetric shafts enabled at this level
    bool  cookie{true};     // cookie projection enabled at this level
};

struct LODData {
    std::vector<LightLODLevel> levels; // sorted by descending screenSize; levels[0] is the most detailed

    // Index of the level to use for a light covering `screenSize` of the screen.
    size_t selectLevel(float screenSize) const {
        for (size_t i = 0; i < levels.size(); ++i) {
            if (screenSize >= levels[i].screenSize) return i;
        }
        return levels.empty() ? 0 : levels.size() - 1;
    }
};

// Normalizes user LOD parameters into a consistent, sorted level table.
// Missing per-level values are derived from the previous level (shadow resolution halves per level,
// toggles inherit); with no thresholds at all a default 3-level chain is produced.
class LightLODGen {
public:
    static LODData compute(const LODParams& lp) {
        LODData out;
        std::vector<float> sizes = lp.screenSizes;
        sizes.erase(std::remove_if(sizes.begin(), sizes.end(), [](float s) { return !(s >= 0.0f); }), sizes.end());
        if (sizes.empty()) sizes = {0.25f, 0.05f, 0.0f};

        // Keep the per-level settings attached to their thresholds while sorting.
        std::vector<size_t> order(sizes.size());
        for (size_t i = 0; i < order.size(); ++i) order[i] = i;
        std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) { return sizes[a] > sizes[b]; });

        out.levels.reserve(order.size());
        // Unspecified top-level shadow resolution = unconstrained (ShadowGen's maximum); lower levels halve it.
        int prevShadow = 8192;
        bool prevVol = true, prevCookie = true;
        for (size_t rank = 0; rank < order.size(); ++rank) {
            const size_t src = order[rank];
            LightLODLevel level;
            level.screenSize = std::min(sizes[src], 1.0f);
            if (src < lp.shadowRes.size()) {
                level.shadowRes = std::max(lp.shadowRes[src], 0);
            } else {
                level.shadowRes = rank == 0 ? prevShadow : prevShadow / 2;
            }
            level.volumetric = src < lp.volumetricOn.size() ? static_cast<bool>(lp.volumetricOn[src]) : prevVol;
            level.cookie = src < lp.cookieOn.size() ? static_cast<bool>(lp.cookieOn[src]) : prevCookie;
            // Lower levels may never be more expensive than higher ones.
            if (rank > 0) {
                const LightLODLevel& prev = out.levels.back();
                level.shadowRes = std::min(level.shadowRes, prev.shadowRes);
                level.volumetric = level.volumetric && prev.volumetric;
                level.cookie = level.cookie && prev.cookie;
            }
            prevShadow = level.shadowRes;
            prevVol = level.volumetric;
            prevCookie = level.cookie;
            out.levels.push_back(level);
        }
        return out;
    }
};

} // namespace mt::light
