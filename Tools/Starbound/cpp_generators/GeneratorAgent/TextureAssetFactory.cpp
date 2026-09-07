#include "TextureAssetFactory.hpp"
#include <stdexcept>

namespace MagiTech {
namespace TextureAssets {

std::future<TextureAssetBundle> TextureAssetFactory::generateAsync(
    const TextureParams& t,
    std::optional<NoiseParams> n,
    std::optional<MaskParams> m,
    std::optional<PBRParams> p,
    std::optional<AtlasParams> a,
    std::optional<CompressionParams> c)
{
    uint64_t key = t.hashKey();
    if (n) key = hashCombine(key, n->hashKey());
    if (m) key = hashCombine(key, m->hashKey());
    if (p) key = hashCombine(key, p->hashKey());
    if (a) key = hashCombine(key, a->hashKey());
    if (c) key = hashCombine(key, c->hashKey());

    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool.enqueue([=]() {
        TextureAssetBundle b;

        switch (t.type) {
            case TextureType::Noise:
                if (n) b.texture = NoiseGen::build(*n, t.resolution, t.seed, t.seamless);
                else throw std::runtime_error("NoiseParams required for Noise texture type.");
                break;
            case TextureType::Mask:
                if (m) b.texture = MaskGen::build(*m, t.resolution);
                else throw std::runtime_error("MaskParams required for Mask texture type.");
                break;
            case TextureType::PBR:
                if (p) b.texture = PBRGen::build(*p, t.resolution);
                else throw std::runtime_error("PBRParams required for PBR texture type.");
                break;
            case TextureType::Atlas:
                // Atlas is a post-process step, doesn't generate a base texture itself
                break;
            default:
                b.texture = 0; // Or some default/empty texture handle
        }

        if (a) {
            b.texture = AtlasGen::pack(*a);
        }

        if (c && b.texture != 0) {
            b.mipmaps = CompressGen::apply(*c, b.texture);
        }

        m_cache.insert(key, b);
        return b;
    });
}

} // namespace TextureAssets
} // namespace MagiTech
