#pragma once
#include <memory>
#include <vector>
#include <string>
#include "core/spells/SpellNode.hpp"
#include "IMagiTechModule.hpp"

namespace MagiTech::GeneratorAgent {

struct SynthesisGoal {
    float targetPower = 0;
    std::vector<std::string> styleTags;
};

class GrammarEngine {
public:
    std::shared_ptr<SpellNode> expand(const SynthesisGoal& goal);
};

class GeneticSpellEvolver {
public:
    void evolve(int generations, std::vector<std::shared_ptr<SpellNode>>& population, const SynthesisGoal& goal);
};

class SpellSynthesisManager {
public:
    static SpellSynthesisManager& instance();
    std::string generateSpell(const SynthesisGoal& goal);
private:
    GrammarEngine _grammar;
    GeneticSpellEvolver _evolver;
}; 

} // namespace MagiTech::GeneratorAgent

