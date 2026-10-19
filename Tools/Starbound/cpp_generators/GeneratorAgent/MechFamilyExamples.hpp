#pragma once

// Runnable demonstrations of the Mechs pipeline (hybrid_example.cpp and
// segmented_example.cpp). They used to be standalone programs with main();
// they are compiled into the backend, so they are exposed as functions instead.
// Each returns 0 on success and 1 if the demonstration threw.

namespace MagiTech {
namespace Mechs {
namespace Examples {

int runHybridMechExample();
int runSegmentedMechExample();

} // namespace Examples
} // namespace Mechs
} // namespace MagiTech
