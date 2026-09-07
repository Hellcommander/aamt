#include "AtlasAssetFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace AtlasAssets {

#define LOG_ATLAS_GEN(Action, Id) Log::info("AtlasAssetGen - {}: {}", #Action, Id)

// Hash function implementations
uint64_t SpriteParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(SpriteParams) - 2 * sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    XXH64_update(&s, path.c_str(), path.length());
    return XXH64_digest(&s);
}
uint64_t AtlasParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(AtlasParams) - sizeof(std::string));
    XXH64_update(&s, id.c_str(), id.length());
    return XXH64_digest(&s);
}
uint64_t MaterialParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, this, sizeof(MaterialParams) - sizeof(std::string));
    XXH64_update(&s, shader.c_str(), shader.length());
    return XXH64_digest(&s);
}
uint64_t LODParams::hashKey() const {
    XXH64_state_t s; XXH64_reset(&s, 0);
    XXH64_update(&s, screenSizes.data(), screenSizes.size() * sizeof(float));
    XXH64_update(&s, atlasResolutions.data(), atlasResolutions.size() * sizeof(int));
    return XXH64_digest(&s);
}

// Generator stubs
namespace SpriteImportGen {
    std::vector<ImportedSprite> import(const std::vector<SpriteParams>& sprites) {
        LOG_ATLAS_GEN(ImportingSprites, sprites.size());
        std::vector<ImportedSprite> imported;
        for(const auto& p : sprites) {
            imported.push_back({p.id, {}, 128, 128});
        }
        return imported;
    }
}
namespace LayoutGen {
    AtlasLayout createLayout(const std::vector<ImportedSprite>& sprites, const AtlasParams& ap) {
        LOG_ATLAS_GEN(CreatingLayout, ap.id);
        AtlasLayout layout;
        layout.atlasWidth = ap.maxWidth;
        layout.atlasHeight = ap.maxHeight;
        int x=0, y=0;
        for(const auto& s : sprites) {
            layout.uvMap[s.id] = UVRect(x, y, 128, 128);
            x += 128 + ap.padding;
            if (x > ap.maxWidth) { x = 0; y += 128 + ap.padding; }
        }
        return layout;
    }
}
namespace PackingGen {
    TextureHandle packSprites(const std::vector<ImportedSprite>& sprites, const AtlasLayout& layout, const AtlasParams& ap) {
        LOG_ATLAS_GEN(PackingSprites, ap.id);
        static uint32_t nextHandle = 1; return nextHandle++;
    }
}
namespace MipGen {
    void generate(const TextureHandle& atlas, int levels) {
        LOG_ATLAS_GEN(GeneratingMips, atlas);
    }
}
namespace MaterialGen {
    MaterialHandle buildMaterial(const MaterialParams& mp, const TextureHandle& atlas) {
        LOG_ATLAS_GEN(BuildingMaterial, mp.shader);
        static uint32_t nextHandle = 100; return nextHandle++;
    }
}
namespace LODGen {
    LODData compute(const LODParams& lp, const TextureHandle& base) {
        LOG_ATLAS_GEN(ComputingLODs, lp.screenSizes.size());
        LODData data;
        data.screenSizes = lp.screenSizes;
        return data;
    }
}

} // namespace AtlasAssets
} // namespace MagiTech
