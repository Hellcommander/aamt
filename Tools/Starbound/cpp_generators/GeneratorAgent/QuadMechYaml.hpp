#pragma once
// Minimal YAML reader for QuadMech definition files (.quadmechdef).
//
// yaml-cpp is not vendored in the backend, so this parses the YAML subset the
// definition files use into an order-preserving nlohmann::ordered_json tree:
//   - block mappings ("key: value") and block sequences ("- item"), including
//     sequence items that start an inline mapping ("- id: walk")
//   - flow sequences / mappings ("[0, 1.5, 2]", "{min: 0.5, max: 2}"), which
//     may continue over several lines until the brackets balance
//   - plain, 'single' and "double" quoted scalars; true/false, null/~,
//     integers and floats are typed, everything else is a string
//   - "#" comments and blank lines
// Anchors, aliases, tags, multi-document streams and block scalars (| >) are
// not supported and raise QuadMechYamlError.
// Content whose first significant character is '{' is parsed as JSON instead.

#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

namespace MagiTech {
namespace QuadMech {

class QuadMechYamlError : public std::runtime_error {
public:
    QuadMechYamlError(const std::string& message, size_t line)
        : std::runtime_error("YAML line " + std::to_string(line) + ": " + message), m_line(line) {}
    size_t line() const { return m_line; }

private:
    size_t m_line;
};

// Parses a YAML (subset) or JSON document. Throws QuadMechYamlError on syntax errors.
nlohmann::ordered_json parseQuadMechYaml(const std::string& text);

} // namespace QuadMech
} // namespace MagiTech
