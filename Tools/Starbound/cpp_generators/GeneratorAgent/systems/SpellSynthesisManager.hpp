#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <mutex>
#include <random>
#include <string>
#include <vector>
#include "agents/CompositionAgent/nodes/SpellNode.hpp"
#include "IMagiTechModule.hpp"
#include "vendor/json/include/nlohmann/json.hpp"

namespace MagiTech::GeneratorAgent {

// The spell node tree is the CompositionAgent's (agents/CompositionAgent/nodes/SpellNode.hpp);
// its node methods are implemented in agents/CompositionAgent/CompositionAgent.cpp.
using CompositionAgent::SpellNode;
using CompositionAgent::SpellMetrics;
using CompositionAgent::ShapeNode;
using CompositionAgent::EffectNode;
using CompositionAgent::ModifierNode;
using CompositionAgent::TriggerNode;
using CompositionAgent::VFXNode;

struct SynthesisGoal {
    float targetPower = 0;
    std::vector<std::string> styleTags;
};

namespace synthesis_detail {

inline bool hasTag(const SynthesisGoal& goal, const std::string& tag) {
    return std::find(goal.styleTags.begin(), goal.styleTags.end(), tag) != goal.styleTags.end();
}

/** Serializes a node tree (SpellNode::toJson covers one node; children are added here). */
inline nlohmann::json treeToJson(const SpellNode& node) {
    nlohmann::json j = node.toJson();
    nlohmann::json kids = nlohmann::json::array();
    for (const auto& child : node.children) {
        if (child) kids.push_back(treeToJson(*child));
    }
    j["children"] = std::move(kids);
    return j;
}

/** Deep copy so evolved variants never share mutable children with their parents. */
inline std::shared_ptr<SpellNode> cloneTree(const std::shared_ptr<SpellNode>& node) {
    if (!node) return nullptr;
    std::shared_ptr<SpellNode> copy;
    if (auto p = std::dynamic_pointer_cast<ShapeNode>(node)) copy = std::make_shared<ShapeNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<EffectNode>(node)) copy = std::make_shared<EffectNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<ModifierNode>(node)) copy = std::make_shared<ModifierNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<TriggerNode>(node)) copy = std::make_shared<TriggerNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<VFXNode>(node)) copy = std::make_shared<VFXNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<CompositionAgent::ControlNode>(node)) copy = std::make_shared<CompositionAgent::ControlNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<CompositionAgent::SFXNode>(node)) copy = std::make_shared<CompositionAgent::SFXNode>(*p);
    else if (auto p = std::dynamic_pointer_cast<CompositionAgent::ChanceTriggerNode>(node)) copy = std::make_shared<CompositionAgent::ChanceTriggerNode>(*p);
    else return node; // unknown node kind: share it (immutable from the evolver's point of view)
    for (auto& child : copy->children) child = cloneTree(child);
    return copy;
}

/** Collects every node of the given kind in the tree. */
template <typename T>
void collect(const std::shared_ptr<SpellNode>& node, std::vector<std::shared_ptr<T>>& out) {
    if (!node) return;
    if (auto typed = std::dynamic_pointer_cast<T>(node)) out.push_back(typed);
    for (const auto& child : node->children) collect(child, out);
}

/** Higher is better: power close to the goal, plus a bonus per requested style tag present. */
inline double fitness(const SpellNode& node, const SynthesisGoal& goal) {
    const SpellMetrics m = node.evaluate();
    const double power = m.totalDamage + m.healAmount + m.crowdControlTime * 10.0 + m.areaCovered;
    double score = -std::abs(power - goal.targetPower);
    const auto tags = node.tags();
    for (const auto& wanted : goal.styleTags) {
        if (std::find(tags.begin(), tags.end(), wanted) != tags.end()) score += 5.0;
    }
    return score;
}

} // namespace synthesis_detail

/// Builds a spell tree from a goal: shape -> effect (+ modifiers, trigger, visuals).
class GrammarEngine {
public:
    /// Rewrite rule: a goal style tag matching `pattern` ('*' wildcard) also contributes `expansion`.
    void addRule(const std::string& pattern, const std::string& expansion) {
        _rules.emplace_back(pattern, expansion);
    }
    void clearRules() { _rules.clear(); }
    const std::vector<std::pair<std::string, std::string>>& rules() const { return _rules; }

    void setMaxDepth(int depth) { _maxDepth = std::max(1, depth); }

    std::shared_ptr<SpellNode> expand(const SynthesisGoal& rawGoal) {
        const SynthesisGoal goal = applyRules(rawGoal);
        using synthesis_detail::hasTag;
        auto shape = std::make_shared<ShapeNode>();
        shape->shapeType = hasTag(goal, "beam") ? "beam" : (hasTag(goal, "aoe") || hasTag(goal, "area")) ? "aoe" : "projectile";

        auto effect = std::make_shared<EffectNode>();
        if (hasTag(goal, "heal")) effect->effectType = "heal";
        else if (hasTag(goal, "frost") || hasTag(goal, "ice")) effect->effectType = "status.freeze";
        else if (hasTag(goal, "lightning")) effect->effectType = "damage.lightning";
        else if (hasTag(goal, "poison")) effect->effectType = "damage.poison";
        else effect->effectType = "damage.fire";
        effect->magnitude = std::max(goal.targetPower, 1.0f);
        shape->children.push_back(effect);

        for (const char* modifier : {"chain", "bounce", "repeat"}) {
            if (hasTag(goal, modifier)) {
                auto mod = std::make_shared<ModifierNode>();
                mod->modifierType = modifier;
                mod->value = 2;
                shape->children.push_back(mod);
            }
        }

        if (hasTag(goal, "explosive")) {
            auto trigger = std::make_shared<TriggerNode>();
            trigger->triggerType = "onImpact";
            auto burst = std::make_shared<EffectNode>();
            burst->effectType = effect->effectType;
            burst->magnitude = effect->magnitude * 0.5f;
            trigger->children.push_back(burst);
            shape->children.push_back(trigger);
        }

        auto vfx = std::make_shared<VFXNode>();
        vfx->vfxId = shape->shapeType + "_" + effect->effectType;
        shape->children.push_back(vfx);
        return shape;
    }

private:
    static bool wildcardMatch(const std::string& pattern, const std::string& text) {
        // '*' matches any sequence; everything else must match exactly
        size_t p = 0, t = 0, star = std::string::npos, mark = 0;
        while (t < text.size()) {
            if (p < pattern.size() && pattern[p] == text[t]) { ++p; ++t; }
            else if (p < pattern.size() && pattern[p] == '*') { star = p++; mark = t; }
            else if (star != std::string::npos) { p = star + 1; t = ++mark; }
            else return false;
        }
        while (p < pattern.size() && pattern[p] == '*') ++p;
        return p == pattern.size();
    }

    // Applies rewrite rules repeatedly (bounded by the max depth) until no new tag appears.
    SynthesisGoal applyRules(const SynthesisGoal& goal) const {
        SynthesisGoal out = goal;
        for (int pass = 0; pass < _maxDepth; ++pass) {
            bool added = false;
            const auto current = out.styleTags;
            for (const auto& tag : current) {
                for (const auto& [pattern, expansion] : _rules) {
                    if (wildcardMatch(pattern, tag) && !synthesis_detail::hasTag(out, expansion)) {
                        out.styleTags.push_back(expansion);
                        added = true;
                    }
                }
            }
            if (!added) break;
        }
        return out;
    }

    std::vector<std::pair<std::string, std::string>> _rules;
    int _maxDepth = 10;
};

/// Simple genetic search over spell trees (mutation of magnitudes/modifiers, elitist selection).
class GeneticSpellEvolver {
public:
    explicit GeneticSpellEvolver(uint64_t seed = std::random_device{}()) : m_rng(seed) {}

    void setMutationRate(float rate) { m_mutationRate = std::clamp(rate, 0.0f, 1.0f); }
    float mutationRate() const { return m_mutationRate; }

    void evolve(int generations, std::vector<std::shared_ptr<SpellNode>>& population, const SynthesisGoal& goal) {
        population.erase(std::remove(population.begin(), population.end(), nullptr), population.end());
        if (population.empty()) return;
        const size_t size = population.size();

        for (int gen = 0; gen < generations; ++gen) {
            // Rank by fitness (best first)
            std::vector<std::pair<double, std::shared_ptr<SpellNode>>> ranked;
            ranked.reserve(population.size());
            for (const auto& individual : population) {
                ranked.emplace_back(synthesis_detail::fitness(*individual, goal), individual);
            }
            std::sort(ranked.begin(), ranked.end(), [](const auto& a, const auto& b) { return a.first > b.first; });

            // Keep the best half, refill with mutated copies of survivors
            const size_t survivors = std::max<size_t>(1, size / 2);
            std::vector<std::shared_ptr<SpellNode>> next;
            next.reserve(size);
            for (size_t i = 0; i < survivors && i < ranked.size(); ++i) next.push_back(ranked[i].second);
            std::uniform_int_distribution<size_t> pick(0, next.size() - 1);
            while (next.size() < size) {
                auto child = synthesis_detail::cloneTree(next[pick(m_rng)]);
                mutate(child, goal);
                next.push_back(std::move(child));
            }
            population = std::move(next);
        }

        std::sort(population.begin(), population.end(), [&](const auto& a, const auto& b) {
            return synthesis_detail::fitness(*a, goal) > synthesis_detail::fitness(*b, goal);
        });
    }

private:
    void mutate(const std::shared_ptr<SpellNode>& root, const SynthesisGoal& goal) {
        std::uniform_real_distribution<float> unit(0.0f, 1.0f);
        std::normal_distribution<float> jitter(1.0f, 0.2f);

        std::vector<std::shared_ptr<EffectNode>> effects;
        synthesis_detail::collect(root, effects);
        for (auto& effect : effects) {
            if (unit(m_rng) < m_mutationRate || effects.size() == 1) {
                effect->magnitude = std::max(0.1f, effect->magnitude * jitter(m_rng));
            }
        }

        std::vector<std::shared_ptr<ModifierNode>> modifiers;
        synthesis_detail::collect(root, modifiers);
        for (auto& modifier : modifiers) {
            if (unit(m_rng) < m_mutationRate) {
                modifier->value = std::max(1, modifier->value + (unit(m_rng) < 0.5f ? -1 : 1));
            }
        }

        // Occasionally add a requested modifier the tree does not have yet
        if (unit(m_rng) < m_mutationRate && !goal.styleTags.empty()) {
            std::uniform_int_distribution<size_t> pickTag(0, goal.styleTags.size() - 1);
            const std::string& tag = goal.styleTags[pickTag(m_rng)];
            if (tag == "chain" || tag == "bounce" || tag == "repeat") {
                const bool present = std::any_of(modifiers.begin(), modifiers.end(),
                                                 [&](const auto& m) { return m->modifierType == tag; });
                if (!present) {
                    auto mod = std::make_shared<ModifierNode>();
                    mod->modifierType = tag;
                    mod->value = 1;
                    root->children.push_back(mod);
                }
            }
        }
    }

    std::mt19937_64 m_rng;
    float m_mutationRate = 0.1f;
};

/// Grammar expansion + genetic refinement; returns the best spell tree as JSON text.
class SpellSynthesisManager {
public:
    SpellSynthesisManager() = default;

    static SpellSynthesisManager& instance() {
        static SpellSynthesisManager manager;
        return manager;
    }

    std::string generateSpell(const SynthesisGoal& goal) {
        std::lock_guard<std::mutex> lock(_mutex);
        auto seed = _grammar.expand(goal);

        std::vector<std::shared_ptr<SpellNode>> population;
        population.reserve(_populationSize);
        population.push_back(seed);
        while (population.size() < _populationSize) {
            population.push_back(synthesis_detail::cloneTree(seed));
        }
        _evolver.evolve(_generations, population, goal);

        nlohmann::json out = synthesis_detail::treeToJson(*population.front());
        out["fitness"] = synthesis_detail::fitness(*population.front(), goal);
        return out.dump();
    }

    void addGrammarRule(const std::string& pattern, const std::string& expansion) {
        std::lock_guard<std::mutex> lock(_mutex);
        _grammar.addRule(pattern, expansion);
    }

    void clearGrammarRules() {
        std::lock_guard<std::mutex> lock(_mutex);
        _grammar.clearRules();
    }

    void setEvolutionParameters(size_t populationSize, int generations, float mutationRate) {
        std::lock_guard<std::mutex> lock(_mutex);
        _populationSize = std::max<size_t>(2, populationSize);
        _generations = std::max(0, generations);
        _evolver.setMutationRate(mutationRate);
    }

private:
    GrammarEngine _grammar;
    GeneticSpellEvolver _evolver;
    size_t _populationSize = 16;
    int _generations = 10;
    std::mutex _mutex;
};

} // namespace MagiTech::GeneratorAgent
