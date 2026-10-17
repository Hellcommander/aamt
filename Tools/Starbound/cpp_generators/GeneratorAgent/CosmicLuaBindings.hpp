#pragma once

#include <sol/sol.hpp>
#include <memory>

namespace MagiTech {
namespace Cosmic {

template<typename P> class CosmicFactory;
struct CosmicProjectileParams;
struct SpaceObjectParams;

using CosmicProjectileFactory = CosmicFactory<CosmicProjectileParams>;
using SpaceObjectFactory = CosmicFactory<SpaceObjectParams>;

class CosmicLuaBindings {
public:
    static void bind(sol::state& lua);
    static void poll_assets(sol::state& lua);

    // Factories used by the bindings; inject the host's instances (e.g. MainPlugin's) with the
    // setters, otherwise the getters lazily create and initialize default ones.
    static void setProjectileFactory(std::shared_ptr<CosmicProjectileFactory> factory);
    static std::shared_ptr<CosmicProjectileFactory> projectileFactory();
    static void setSpaceObjectFactory(std::shared_ptr<SpaceObjectFactory> factory);
    static std::shared_ptr<SpaceObjectFactory> spaceObjectFactory();
};

} // namespace Cosmic
} // namespace MagiTech
