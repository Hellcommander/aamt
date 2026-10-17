#include "LightLuaBindings.hpp"
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace mt::light {

namespace {

std::mutex& factoryMutex() {
    static std::mutex m;
    return m;
}

std::shared_ptr<LightAssetFactory>& factorySlot() {
    static std::shared_ptr<LightAssetFactory> f;
    return f;
}

// Reads a vector component from {x=..}/{r=..} style keys or from the array part ({1, 2, 3}).
float component(const sol::table& t, const char* name, const char* alias, int index, float fallback) {
    if (sol::optional<float> v = t[name]) return *v;
    if (alias) {
        if (sol::optional<float> v = t[alias]) return *v;
    }
    if (sol::optional<float> v = t[index]) return *v;
    return fallback;
}

Vec2 toVec2(const sol::table& t, const Vec2& fallback) {
    return Vec2(component(t, "x", nullptr, 1, fallback.x), component(t, "y", nullptr, 2, fallback.y));
}

Vec3 toVec3(const sol::table& t, const Vec3& fallback) {
    return Vec3(component(t, "x", "r", 1, fallback.x), component(t, "y", "g", 2, fallback.y),
                component(t, "z", "b", 3, fallback.z));
}

// glm members are exposed to Lua as plain tables ({x=, y=[, z=]}), so scripts need no glm usertypes.
template <typename T>
auto vec2Property(Vec2 T::*member) {
    return sol::property(
        [member](const T& self, sol::this_state s) {
            sol::state_view lua(s);
            const Vec2& v = self.*member;
            return lua.create_table_with("x", v.x, "y", v.y);
        },
        [member](T& self, sol::table t) { self.*member = toVec2(t, self.*member); });
}

template <typename T>
auto vec3Property(Vec3 T::*member) {
    return sol::property(
        [member](const T& self, sol::this_state s) {
            sol::state_view lua(s);
            const Vec3& v = self.*member;
            return lua.create_table_with("x", v.x, "y", v.y, "z", v.z);
        },
        [member](T& self, sol::table t) { self.*member = toVec3(t, self.*member); });
}

// std::vector members (incl. std::vector<bool>) as copied Lua arrays with a table setter.
template <typename T, typename E>
auto listProperty(std::vector<E> T::*member) {
    return sol::property(
        [member](const T& self, sol::this_state s) {
            sol::state_view lua(s);
            sol::table out = lua.create_table();
            const auto& list = self.*member;
            for (size_t i = 0; i < list.size(); ++i) out[i + 1] = static_cast<E>(list[i]);
            return out;
        },
        [member](T& self, sol::table t) {
            std::vector<E> values;
            const size_t n = t.size();
            values.reserve(n);
            for (size_t i = 1; i <= n; ++i) values.push_back(t.get<E>(i));
            self.*member = std::move(values);
        });
}

struct RequestArgs {
    ShadowParams     sp;
    CookieParams     cp;
    VolumetricParams vp;
    FlickerParams    fp;
    LODParams        lodp;
};

RequestArgs resolveArgs(const sol::optional<ShadowParams>& sp, const sol::optional<CookieParams>& cp,
                        const sol::optional<VolumetricParams>& vp, const sol::optional<FlickerParams>& fp,
                        const sol::optional<LODParams>& lodp) {
    RequestArgs args;
    if (sp) args.sp = *sp;
    if (cp) args.cp = *cp;
    if (vp) args.vp = *vp;
    if (fp) args.fp = *fp;
    if (lodp) args.lodp = *lodp;
    return args;
}

} // namespace

void LightLuaBindings::setFactory(std::shared_ptr<LightAssetFactory> factory) {
    std::lock_guard<std::mutex> lock(factoryMutex());
    factorySlot() = std::move(factory);
}

std::shared_ptr<LightAssetFactory> LightLuaBindings::factory() {
    std::lock_guard<std::mutex> lock(factoryMutex());
    auto& slot = factorySlot();
    if (!slot) {
        // No factory injected by the host: create a default one (starts its worker pool).
        slot = std::make_shared<LightAssetFactory>();
    }
    return slot;
}

void LightLuaBindings::bind(sol::state& lua) {
    // -----------------------------------------------------------------------------------------------------------------
    // Enums
    // -----------------------------------------------------------------------------------------------------------------
    lua.new_enum("LightType",
        "Directional", LightType::Directional,
        "Point",       LightType::Point,
        "Spot",        LightType::Spot,
        "Area",        LightType::Area);

    lua.new_enum("FlickerPattern",
        "Sine",   FlickerParams::Pattern::Sine,
        "Perlin", FlickerParams::Pattern::Perlin,
        "Random", FlickerParams::Pattern::Random);

    // ------------------------------------------------ Parameter structs ---------------------------------------------
    lua.new_usertype<LightParams>("LightParams",
        sol::constructors<LightParams()>(),
        "id", &LightParams::id,
        "type", &LightParams::type,
        "position", vec3Property(&LightParams::position),
        "direction", vec3Property(&LightParams::direction),
        "color", vec3Property(&LightParams::color),
        "intensity", &LightParams::intensity,
        "range", &LightParams::range,
        "innerAngle", &LightParams::innerAngle,
        "outerAngle", &LightParams::outerAngle,
        "areaSize", vec2Property(&LightParams::areaSize),
        "volumetric", &LightParams::volumetric,
        "dynamic", &LightParams::dynamic);

    lua.new_usertype<ShadowParams>("ShadowParams",
        sol::constructors<ShadowParams()>(),
        "castShadows", &ShadowParams::castShadows,
        "resolution", &ShadowParams::resolution,
        "cascades", &ShadowParams::cascades,
        "bias", &ShadowParams::bias,
        "normalBias", &ShadowParams::normalBias);

    lua.new_usertype<CookieParams>("CookieParams",
        sol::constructors<CookieParams()>(),
        "useCookie", &CookieParams::useCookie,
        "texturePath", &CookieParams::texturePath,
        "uvScale", vec2Property(&CookieParams::uvScale),
        "uvOffset", vec2Property(&CookieParams::uvOffset));

    lua.new_usertype<VolumetricParams>("VolumetricParams",
        sol::constructors<VolumetricParams()>(),
        "density", &VolumetricParams::density,
        "scatterColor", vec3Property(&VolumetricParams::scatterColor),
        "anisotropy", &VolumetricParams::anisotropy);

    lua.new_usertype<FlickerParams>("FlickerParams",
        sol::constructors<FlickerParams()>(),
        "enabled", &FlickerParams::enabled,
        "frequency", &FlickerParams::frequency,
        "amplitude", vec2Property(&FlickerParams::amplitude),
        "pattern", &FlickerParams::pattern);

    lua.new_usertype<LODParams>("LODParams",
        sol::constructors<LODParams()>(),
        "screenSizes", listProperty(&LODParams::screenSizes),
        "shadowRes", listProperty(&LODParams::shadowRes),
        "volumetricOn", listProperty(&LODParams::volumetricOn),
        "cookieOn", listProperty(&LODParams::cookieOn));

    // ------------------------------------------------ Bundle types ---------------------------------------------------
    lua.new_usertype<LightBundle>("LightBundle",
        "handle", sol::readonly(&LightBundle::handle),
        "type", sol::readonly(&LightBundle::type),
        "descSet", sol::readonly(&LightBundle::descSet),
        "lightUBO", sol::readonly(&LightBundle::lightUBO),
        "cullPipeline", sol::readonly(&LightBundle::cullPipeline),
        "renderPipeline", sol::readonly(&LightBundle::renderPipeline),
        "shadowsEnabled", sol::property([](const LightBundle& b) { return b.shadows.enabled; }),
        "shadowResolution", sol::property([](const LightBundle& b) { return b.shadows.resolution; }),
        "cookieEnabled", sol::property([](const LightBundle& b) { return b.cookie.enabled; }),
        "volumetricEnabled", sol::property([](const LightBundle& b) { return b.volume.enabled; }),
        "flickerEnabled", sol::property([](const LightBundle& b) { return b.flicker.enabled; }),
        "lodLevels", sol::property([](const LightBundle& b) { return b.lod.levels.size(); }),
        "selectLod", [](const LightBundle& b, float screenSize) { return b.lod.selectLevel(screenSize) + 1; },
        "flickerScale", [](const LightBundle& b, float timeSeconds) {
            return FlickerGen::evaluate(b.flicker, timeSeconds);
        });

    lua.new_usertype<LightBundleRequest>("LightBundleRequest",
        sol::no_constructor,
        "ready", &LightBundleRequest::ready,
        "get", &LightBundleRequest::get);

    // ------------------------------------------------ Factory bindings ------------------------------------------------
    sol::table factoryTable = lua.create_named_table("LightFactory");

    factoryTable.set_function("generate_sync",
        [](const LightParams& lp, sol::optional<ShadowParams> sp, sol::optional<CookieParams> cp,
           sol::optional<VolumetricParams> vp, sol::optional<FlickerParams> fp, sol::optional<LODParams> lodp) {
            const RequestArgs a = resolveArgs(sp, cp, vp, fp, lodp);
            return LightLuaBindings::factory()->generateSync(lp, a.sp, a.cp, a.vp, a.fp, a.lodp);
        });

    factoryTable.set_function("generate_async",
        [](const LightParams& lp, sol::optional<ShadowParams> sp, sol::optional<CookieParams> cp,
           sol::optional<VolumetricParams> vp, sol::optional<FlickerParams> fp, sol::optional<LODParams> lodp) {
            const RequestArgs a = resolveArgs(sp, cp, vp, fp, lodp);
            LightBundleRequest request;
            request.future = LightLuaBindings::factory()->generateAsync(lp, a.sp, a.cp, a.vp, a.fp, a.lodp).share();
            return request;
        });

    factoryTable.set_function("should_use_async", [](const LightParams& lp) {
        return LightLuaBindings::factory()->shouldUseAsync(lp);
    });

    factoryTable.set_function("release", [](const LightBundle& bundle) {
        return LightLuaBindings::factory()->releaseBundle(bundle);
    });

    factoryTable.set_function("clear_cache", []() {
        LightLuaBindings::factory()->clearCache();
    });

    factoryTable.set_function("cache_size", []() {
        return LightLuaBindings::factory()->getCacheSize();
    });

    factoryTable.set_function("cache_hit_rate", []() {
        return LightLuaBindings::factory()->getCacheHitRate();
    });

    factoryTable.set_function("warmup", []() {
        LightLuaBindings::factory()->warmupCache();
    });

    factoryTable.set_function("metrics", [](sol::this_state s) {
        sol::state_view view(s);
        const PerformanceSnapshot m = LightLuaBindings::factory()->getPerformanceMetrics();
        return view.create_table_with(
            "cacheHits", m.cacheHits,
            "cacheMisses", m.cacheMisses,
            "asyncGenerations", m.asyncGenerations,
            "syncGenerations", m.syncGenerations,
            "batchProcessings", m.batchProcessings,
            "cacheHitRate", m.cacheHitRate,
            "secondsSinceReset", m.secondsSinceReset);
    });

    factoryTable.set_function("set_asset_root", [](const std::string& root) {
        GPUDeviceInterface::getInstance().setAssetRoot(std::filesystem::path(std::u8string(root.begin(), root.end())));
    });
}

} // namespace mt::light
