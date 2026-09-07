#include "TextureAssetLuaBindings.hpp"
#include "TextureAssetFactory.hpp"
#include "core/plugins/MainPlugin.hpp"
#include <vector>

namespace MagiTech {
namespace TextureAssets {

static std::vector<std::pair<std::future<TextureAssetBundle>, std::string>> pendingAssets;

void TextureAssetLuaBindings::bind(sol::state& lua) {
    lua.new_enum("TextureType",
        "Noise", TextureType::Noise,
        "Mask", TextureType::Mask,
        "PBR", TextureType::PBR,
        "Atlas", TextureType::Atlas,
        "TrimSheet", TextureType::TrimSheet
    );

    lua.new_usertype<TextureParams>("TextureParams",
        sol::constructors<TextureParams()>(),
        "id", &TextureParams::id,
        "type", &TextureParams::type,
        "resolution", &TextureParams::resolution,
        "uvScale", &TextureParams::uvScale,
        "seed", &TextureParams::seed,
        "seamless", &TextureParams::seamless
    );

    lua.new_usertype<NoiseParams>("NoiseParams",
        sol::constructors<NoiseParams()>(),
        "noiseType", &NoiseParams::noiseType,
        "octaves", &NoiseParams::octaves,
        "frequency", &NoiseParams::frequency,
        "lacunarity", &NoiseParams::lacunarity,
        "gain", &NoiseParams::gain
    );

    lua.new_usertype<MaskParams>("MaskParams",
        sol::constructors<MaskParams()>(),
        "stops", &MaskParams::stops,
        "invert", &MaskParams::invert,
        "gaussianBlur", &MaskParams::gaussianBlur,
        "blurRadius", &MaskParams::blurRadius
    );
    
    lua.new_usertype<PBRParams>("PBRParams",
        sol::constructors<PBRParams()>(),
        "baseColorTint", &PBRParams::baseColorTint,
        "metallic", &PBRParams::metallic,
        "roughness", &PBRParams::roughness,
        "ambientOcclusion", &PBRParams::ambientOcclusion,
        "bakeHeight", &PBRParams::bakeHeight,
        "heightScale", &PBRParams::heightScale
    );

    lua.new_usertype<AtlasParams>("AtlasParams",
        sol::constructors<AtlasParams()>(),
        "sources", &AtlasParams::sources,
        "padding", &AtlasParams::padding,
        "maxWidth", &AtlasParams::maxWidth,
        "maxHeight", &AtlasParams::maxHeight,
        "generateUDIM", &AtlasParams::generateUDIM
    );

    lua.new_usertype<CompressionParams>("CompressionParams",
        sol::constructors<CompressionParams()>(),
        "format", &CompressionParams::format,
        "quality", &CompressionParams::quality,
        "generateMipmaps", &CompressionParams::generateMipmaps,
        "sRGB", &CompressionParams::sRGB
    );

    lua.new_usertype<TextureAssetBundle>("TextureAssetBundle",
        sol::no_constructor,
        "texture", &TextureAssetBundle::texture,
        "mipmaps", &TextureAssetBundle::mipmaps,
        "udim", &TextureAssetBundle::udim
    );

    lua.set_function("spawn_texture_asset",
        [&](const TextureParams& t, sol::optional<NoiseParams> n,
            sol::optional<MaskParams> m, sol::optional<PBRParams> p,
            sol::optional<AtlasParams> a, sol::optional<CompressionParams> c) {
            auto factory = MainPlugin::instance().getTextureFactory();
            pendingAssets.emplace_back(factory->generateAsync(t, n, m, p, a, c), t.id);
        }
    );
}

void TextureAssetLuaBindings::poll_assets(sol::state& lua) {
    for (auto it = pendingAssets.begin(); it != pendingAssets.end();) {
        if (it->first.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto b = it->first.get();
                lua["print"]("Texture asset ready: " + it->second);
            } catch (const std::exception& e) {
                // log error
            }
            it = pendingAssets.erase(it);
        } else {
            ++it;
        }
    }
}

} // namespace TextureAssets
} // namespace MagiTech
