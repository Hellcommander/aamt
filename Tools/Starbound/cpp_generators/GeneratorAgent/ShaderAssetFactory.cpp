#include "ShaderAssetFactory.hpp"

namespace MagiTech {
namespace ShaderAssets {

std::future<ShaderAssetBundle> ShaderAssetFactory::generateAsync(
    const ShaderParams& sp,
    std::optional<PipelineParams> pp,
    CompileTarget target)
{
    uint64_t key = sp.hashKey();
    if (pp) {
        key = hashCombine(key, pp->hashKey());
    }
    key = hashCombine(key, static_cast<uint64_t>(target));

    if (auto hit = m_cache.find(key)) {
        return std::async(std::launch::deferred, [=] { return *hit; });
    }

    return m_pool.enqueue([=]() {
        ShaderAssetBundle b;

        auto expandedSrc = TemplateGen::expand(sp.sourceTemplate, sp.defines, sp.includes);
        b.shader = CompileGen::compile(expandedSrc, sp.stage, sp.lang, target);
        b.reflection = ReflectionGen::inspect(b.shader);

        if (pp) {
            b.pipelineState = PipelineGen::create(*pp, *b.reflection);
        }

        m_cache.insert(key, b);
        return b;
    });
}

} // namespace ShaderAssets
} // namespace MagiTech
