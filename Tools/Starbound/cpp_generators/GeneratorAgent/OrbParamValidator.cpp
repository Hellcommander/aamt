#include "OrbParamValidator.hpp"
#include <fstream>

namespace MagiTech {
namespace Orbs {

OrbParamValidator::OrbParamValidator(const std::string& schema_path) {
    std::ifstream schema_file(schema_path);
    if (schema_file) {
        nlohmann::json schema_json = nlohmann::json::parse(schema_file);
        m_validator.set_root_schema(schema_json);
    }
}

bool OrbParamValidator::validate(const OrbParams& params) const {
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
    
    try {
        m_validator.validate(params_json);
        return true;
    } catch (const std::exception& e) {
        // Log the validation error
        return false;
    }
}

} // namespace Orbs
} // namespace MagiTech
