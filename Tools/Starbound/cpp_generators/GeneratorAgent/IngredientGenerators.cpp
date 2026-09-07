#include "IngredientFactory.hpp"
#include "core/Log.hpp"

namespace MagiTech {
namespace Ingredients {
namespace Gen {

#define LOG_GEN(Type, Asset, Id) Log::info("Generating {} for {} ingredient: {}", #Asset, #Type, Id)

    // --- Herb Generators ---
    namespace Herb {
        MeshHandle buildMesh(const IngredientParams& p) { LOG_GEN(Herb, Mesh, p.id); return 1; }
        TextureHandle buildAlbedo(const IngredientParams& p) { LOG_GEN(Herb, Albedo, p.id); return 1; }
        ParticleHandle buildParticles(const IngredientParams& p) { LOG_GEN(Herb, Particles, p.id); return 1; }
    }

    // --- Crystal Generators ---
    namespace Crystal {
        MeshHandle buildMesh(const IngredientParams& p) { LOG_GEN(Crystal, Mesh, p.id); return 2; }
        TextureHandle buildAlbedo(const IngredientParams& p) { LOG_GEN(Crystal, Albedo, p.id); return 2; }
        ParticleHandle buildParticles(const IngredientParams& p) { LOG_GEN(Crystal, Particles, p.id); return 2; }
    }
    
    // --- Powder Generators (STUB) ---
    // namespace Powder { ... }

    // --- Liquid Generators (STUB) ---
    // namespace Liquid { ... }

    // --- Bone Generators (STUB) ---
    // namespace Bone { ... }

    // --- Runestone Generators (STUB) ---
    // namespace Runestone { ... }

} // namespace Gen
} // namespace Ingredients
} // namespace MagiTech
