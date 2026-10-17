#include "OrbParamValidator.hpp"
#include "core/JSON.hpp"
#include "core/Log.hpp"
#include <fstream>

namespace MagiTech {
namespace Orbs {

namespace {

// core/JSON.hpp's validator handles type/required/enum/const/minimum/maximum/
// properties/items; this adds the array-size and exclusive-bound keywords the
// orb schema relies on (minItems/maxItems on the colour arrays).
void checkExtraKeywords(const nlohmann::json& value, const nlohmann::json& schema,
                        const std::string& path, std::vector<std::string>& errors) {
    if (!schema.is_object()) return;

    if (value.is_array()) {
        if (auto it = schema.find("minItems"); it != schema.end() && it->is_number_unsigned()
            && value.size() < it->get<size_t>())
            errors.push_back(path + ": array has fewer than " + std::to_string(it->get<size_t>()) + " items");
        if (auto it = schema.find("maxItems"); it != schema.end() && it->is_number_unsigned()
            && value.size() > it->get<size_t>())
            errors.push_back(path + ": array has more than " + std::to_string(it->get<size_t>()) + " items");
        if (auto it = schema.find("items"); it != schema.end() && it->is_object()) {
            for (size_t i = 0; i < value.size(); ++i)
                checkExtraKeywords(value[i], *it, path + "[" + std::to_string(i) + "]", errors);
        }
    }

    if (value.is_number()) {
        const double v = value.get<double>();
        if (auto it = schema.find("exclusiveMinimum"); it != schema.end() && it->is_number() && v <= it->get<double>())
            errors.push_back(path + ": value not above exclusiveMinimum");
        if (auto it = schema.find("exclusiveMaximum"); it != schema.end() && it->is_number() && v >= it->get<double>())
            errors.push_back(path + ": value not below exclusiveMaximum");
    }

    if (value.is_object()) {
        if (auto props = schema.find("properties"); props != schema.end() && props->is_object()) {
            for (auto it = props->begin(); it != props->end(); ++it) {
                if (auto field = value.find(it.key()); field != value.end())
                    checkExtraKeywords(*field, it.value(), path.empty() ? it.key() : path + "." + it.key(), errors);
            }
        }
    }
}

} // namespace

OrbParamValidator::OrbParamValidator(const std::string& schema_path) {
    std::ifstream schema_file(schema_path);
    if (!schema_file) {
        Log::warn("Orbs", "OrbParamValidator: cannot open schema '{}'", schema_path);
        return;
    }
    nlohmann::json schema_json = nlohmann::json::parse(schema_file, nullptr, false);
    if (schema_json.is_discarded() || !JSONSchema::isValidSchema(schema_json)) {
        Log::warn("Orbs", "OrbParamValidator: schema '{}' is not a valid JSON schema", schema_path);
        return;
    }
    m_schema = std::move(schema_json);
    m_hasSchema = true;
}

bool OrbParamValidator::validate(const OrbParams& params) const {
    m_lastErrors.clear();
    if (!m_hasSchema) {
        m_lastErrors.push_back("no root schema has been loaded");
        Log::warn("Orbs", "OrbParamValidator: cannot validate '{}' without a schema", params.id);
        return false;
    }

    nlohmann::json params_json = {
        {"id", params.id},
        {"orbType", params.orbType},
        {"radius", params.radius},
        {"coreColor", {params.coreColor.r, params.coreColor.g, params.coreColor.b}},
        {"shellColor", {params.shellColor.r, params.shellColor.g, params.shellColor.b}},
        {"runePattern", params.runePattern},
        {"runeDensity", params.runeDensity},
        {"auraIntensity", params.auraIntensity},
        {"trailEffect", params.trailEffect},
        {"gravitationalPull", params.gravitationalPull},
        {"spellAffinity", params.spellAffinity},
        {"detailLevel", params.detailLevel}
    };

    JSON::ValidationResult result = JSONSchema::validate(params_json, m_schema);
    m_lastErrors = result.errors;
    checkExtraKeywords(params_json, m_schema, "", m_lastErrors);

    if (!m_lastErrors.empty()) {
        std::string summary;
        for (const auto& e : m_lastErrors) {
            if (!summary.empty()) summary += "; ";
            summary += e;
        }
        Log::warn("Orbs", "OrbParams '{}' failed schema validation: {}", params.id, summary);
        return false;
    }
    return true;
}

} // namespace Orbs
} // namespace MagiTech
