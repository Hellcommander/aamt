#pragma once

#include "TrailTypes.hpp"

namespace BehaviorGen {
  void configure(
    TrailHandle handle,
    const BehaviorParams& bp,
    bool gpu
  );
}
