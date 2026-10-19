#pragma once

#include <string>

// Runnable demonstration of the mesh-to-sprite pipeline (MeshToSpriteExample.cpp).
// It used to be a standalone program with main(); it is compiled into the backend,
// so it is exposed as a function instead.

namespace MagiTech {
namespace Animation {
namespace Examples {

// Builds a procedural mech mesh (.obj) and motion clips (.bvh) under
// `outputDirectory`/source, then runs the full workflow on them: camera presets,
// single / directional / batch animation capture, explicit sprite sheet packing and
// export, and Starbound .animation / .projectile export.
// Returns 0 on success and 1 if any step failed or threw.
int runMeshToSpriteExample(const std::string& outputDirectory = "./sprite_output");

} // namespace Examples
} // namespace Animation
} // namespace MagiTech
