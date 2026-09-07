#include "MonsterGenerators.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Monsters {

MeshHandle MeshGen<MonsterParams>::build(const MonsterParams& p) {
    Log::info("Building monster mesh for: {}", p.id);
    // Placeholder implementation
    return 1;
}

TextureHandle TextureGen<MonsterParams>::build(const MonsterParams& p) {
    Log::info("Building monster texture for: {}", p.id);
    // Placeholder implementation
    return 1;
}

SkeletonHandle RigGen<MonsterParams>::build(const MonsterParams& p) {
    Log::info("Building monster skeleton for: {}", p.id);
    // Placeholder implementation
    return 1;
}

AnimationHandle AnimGen<MonsterParams>::build(const MonsterParams& p) {
    Log::info("Building monster animation for: {}", p.id);
    // Placeholder implementation
    return 1;
}

AIHandle AIGen<MonsterParams>::build(const MonsterParams& p) {
    Log::info("Building monster AI for: {}", p.id);
    // Placeholder implementation
    return 1;
}

} // namespace Monsters
} // namespace MagiTech
