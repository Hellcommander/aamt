#include "ClusterBombFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace ClusterBombs {

namespace MeshGen {
    MeshHandle buildBombCasing(const ClusterBombParams& p) {
        Log::info("Building bomb casing for: {}", p.id);
        return 1;
    }
    MeshHandle buildFragment(const ClusterBombParams& p) {
        Log::info("Building fragment mesh for: {}", p.id);
        return 2;
    }
}
namespace PhysicsGen {
    PhysicsHandle buildFuse(const ClusterBombParams& p) {
        Log::info("Building fuse physics for: {}", p.id);
        return 1;
    }
}
namespace FragmentGen {
    std::vector<FragmentAsset> generateFragments(const ClusterBombParams& p) {
        Log::info("Generating {} fragments for: {}", p.fragmentCount, p.id);
        std::vector<FragmentAsset> fragments;
        for(int i = 0; i < p.fragmentCount; ++i) {
            fragments.push_back({MeshGen::buildFragment(p), 1});
        }
        return fragments;
    }
}
namespace ParticleGen {
    ParticleHandle buildExplosionCore(const ClusterBombParams& p) {
        Log::info("Building explosion core FX for: {}", p.id);
        return 1;
    }
    ParticleHandle buildSmokeRing(const ClusterBombParams& p) {
        Log::info("Building smoke ring FX for: {}", p.id);
        return 2;
    }
    ParticleHandle buildDebris(const ClusterBombParams& p) {
        Log::info("Building debris FX for: {}", p.id);
        return 3;
    }
}
namespace ShaderGen {
    ShaderHandle buildCasingShader(const ClusterBombParams& p) {
        Log::info("Building casing shader for: {}", p.id);
        return 1;
    }
}

} // namespace ClusterBombs
} // namespace MagiTech
