#pragma once

#include <sol/sol.hpp>
#include <future>
#include <memory>
#include "LightAssetFactory.hpp"

namespace mt::light {

// Handle returned to Lua by LightFactory.generate_async: poll ready(), then get() the bundle.
struct LightBundleRequest {
    std::shared_future<LightBundle> future;

    bool ready() const {
        return future.valid() && future.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
    }
    LightBundle get() const { return future.get(); } // rethrows a failed build as a Lua error
};

class LightLuaBindings {
public:
    static void bind(sol::state& lua);

    // Factory used by the bindings; inject the host's instance with setFactory,
    // otherwise factory() lazily creates a default one.
    static void setFactory(std::shared_ptr<LightAssetFactory> factory);
    static std::shared_ptr<LightAssetFactory> factory();
};

} // namespace mt::light
