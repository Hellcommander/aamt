#pragma once

// Behaviour generation for segmented creatures. The behaviour tree itself is built
// by the canonical AIGen::build(BehaviorParams) (ProceduralFactory.hpp, which replaced
// the former AIGen<BehaviorParams> template specialisation); this layer derives
// parameters from behaviour archetypes and builds the multi-tree bundle.

#include "BehaviorTypes.hpp"
#include "ProceduralFactory.hpp"

namespace MagiTech {
namespace SegmentedCreatures {

/** Behaviour parameters for an archetype / movement pattern / combat style combination. */
BehaviorParams makeBehaviorParams(BehaviorType type,
                                  MovementPattern movement = MovementPattern::SLITHER,
                                  CombatStyle combat = CombatStyle::MELEE);

/**
 * Builds the main behaviour tree and the focused movement / combat / social /
 * environmental trees for `params` (all stored in CreatureAssets::AssetStore) and
 * fills the bundle statistics. Never throws; failures are reported in result.
 */
BehaviorAssetBundle buildBehaviorAssets(const BehaviorParams& params);

/** Releases every behaviour tree referenced by the bundle from the asset store. */
void releaseBehaviorAssets(const BehaviorAssetBundle& bundle);

} // namespace SegmentedCreatures
} // namespace MagiTech
