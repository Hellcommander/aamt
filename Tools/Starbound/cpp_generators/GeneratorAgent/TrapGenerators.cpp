#include "TrapFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Traps {

namespace MeshGen {
    MeshHandle buildTrap(const TrapParams& t) {
        Log::info("Building trap mesh for: {} ({})", t.id, t.trapType);
        return 1;
    }
}
namespace TextureGen {
    TextureHandle buildTrap(const TrapParams& t) {
        Log::info("Building trap texture for: {}", t.id);
        return 1;
    }
}
namespace ShaderGen {
    ShaderHandle buildTrap(const TrapParams& t) {
        Log::info("Building trap shader for: {}", t.id);
        return 1;
    }
}
namespace PhysGen {
    PhysicsHandle buildTrap(const TrapParams& t, const BehaviorParams& b) {
        Log::info("Building trap physics for: {}", t.id);
        return 1;
    }
}
namespace ParticleGen {
    ParticleHandle buildTrapFX(const TrapParams& t) {
        Log::info("Building trap particle FX for: {}", t.id);
        return 1;
    }
}
namespace AudioGen {
    AudioHandle buildTrapSFX(const TrapParams& t) {
        Log::info("Building trap audio SFX for: {}", t.id);
        return 1;
    }
}
namespace IconGen {
    TextureHandle buildTrapIcon(const TrapParams& t, const BehaviorParams& b) {
        Log::info("Building trap icon for: {}", t.id);
        return 1;
    }
}

} // namespace Traps
} // namespace MagiTech
