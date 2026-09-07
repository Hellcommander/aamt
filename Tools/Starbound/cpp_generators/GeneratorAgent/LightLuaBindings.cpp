#include "LightLuaBindings.hpp"
#include <memory>

namespace mt::light {

void LightLuaBindings::bind(sol::state& lua) {
    // -----------------------------------------------------------------------------------------------------------------
    // Enum & basic types
    // -----------------------------------------------------------------------------------------------------------------
    lua.new_enum("LightType",
        "Directional", static_cast<int>(LightType::Directional),
        "Point",        static_cast<int>(LightType::Point),
        "Spot",         static_cast<int>(LightType::Spot),
        "Area",         static_cast<int>(LightType::Area));

    // ------------------------------------------------ Parameter structs ---------------------------------------------
    lua.new_usertype<LightParams>("LightParams",
        sol::constructors<LightParams()>(),
        "id", &LightParams::id,
        "type", &LightParams::type,
        "color", &LightParams::color,
        "intensity", &LightParams::intensity,
        "range", &LightParams::range,
        "innerAngle", &LightParams::innerAngle,
        "outerAngle", &LightParams::outerAngle,
        "areaSize", &LightParams::areaSize,
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
        "uvScale", &CookieParams::uvScale,
        "uvOffset", &CookieParams::uvOffset);

    lua.new_usertype<VolumetricParams>("VolumetricParams",
        sol::constructors<VolumetricParams()>(),
        "density", &VolumetricParams::density,
        "scatterColor", &VolumetricParams::scatterColor,
        "anisotropy", &VolumetricParams::anisotropy);

    // Flicker pattern enum alias inside FlickerParams
    lua.new_enum("FlickerPattern",
        "Sine", static_cast<int>(FlickerParams::Pattern::Sine),
        "Perlin", static_cast<int>(FlickerParams::Pattern::Perlin),
        "Random", static_cast<int>(FlickerParams::Pattern::Random));

    lua.new_usertype<FlickerParams>("FlickerParams",
        sol::constructors<FlickerParams()>(),
        "enabled", &FlickerParams::enabled,
        "frequency", &FlickerParams::frequency,
        "amplitude", &FlickerParams::amplitude,
        "pattern", &FlickerParams::pattern);

    lua.new_usertype<LODParams>("LODParams",
        sol::constructors<LODParams()>(),
        "screenSizes", &LODParams::screenSizes,
        "shadowRes", &LODParams::shadowRes,
        "volumetricOn", &LODParams::volumetricOn,
        "cookieOn", &LODParams::cookieOn);

    // ------------------------------------------------ Bundle type -----------------------------------------------------
    lua.new_usertype<LightBundle>("LightBundle",
        "handle", &LightBundle::handle,
        "descSet", &LightBundle::descSet,
        "lightUBO", &LightBundle::lightUBO,
        "cullPipeline", &LightBundle::cullPipeline,
        "renderPipeline", &LightBundle::renderPipeline);

    // ------------------------------------------------ Factory bindings ------------------------------------------------
    lua["LightFactory"] = lua.create_table();
    lua["LightFactory"]["generate_sync"] = [](LightParams lp, ShadowParams sp, CookieParams cp,
                                                 VolumetricParams vp, FlickerParams fp, LODParams lodp) {
        return g_lightFactory.generateSync(lp, sp, cp, vp, fp, lodp);
    };

    lua["LightFactory"]["generate_async"] = [](LightParams lp, ShadowParams sp, CookieParams cp,
                                                  VolumetricParams vp, FlickerParams fp, LODParams lodp) {
        return g_lightFactory.generateAsync(lp, sp, cp, vp, fp, lodp);
    };

    lua["LightFactory"]["clear_cache"] = []() {
        g_lightFactory.clearCache();
    };
}

} // namespace mt::light
