#pragma once

#include "OrbTypes.hpp"
#include "nlohmann/json.hpp"
#include "nlohmann/json-schema.hpp"

namespace MagiTech {
namespace Orbs {

class OrbParamValidator {
public:
    OrbParamValidator(const std::string& schema_path);

    bool validate(const OrbParams& params) const;
    
private:
    nlohmann::json_schema::json_validator m_validator;
};

} // namespace Orbs
} // namespace MagiTech
