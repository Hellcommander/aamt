#pragma once

#include "OrbTypes.hpp"
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

namespace MagiTech {
namespace Orbs {

// Validates OrbParams against a JSON Schema (draft-07 subset) loaded from disk,
// e.g. OrbParams.schema.json. Uses the backend's nlohmann-based schema checker
// (core/JSON.hpp) plus array-size keywords it does not cover.
class OrbParamValidator {
public:
    explicit OrbParamValidator(const std::string& schema_path);

    bool validate(const OrbParams& params) const;

    bool hasSchema() const { return m_hasSchema; }

    // Errors reported by the most recent validate() call (not thread-safe).
    const std::vector<std::string>& lastErrors() const { return m_lastErrors; }

private:
    nlohmann::json m_schema;
    bool m_hasSchema = false;
    mutable std::vector<std::string> m_lastErrors;
};

} // namespace Orbs
} // namespace MagiTech
