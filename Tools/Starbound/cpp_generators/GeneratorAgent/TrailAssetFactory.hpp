#pragma once

#include "SegmentGen.hpp"
#include "BehaviorGen.hpp"
#include "RenderGen.hpp"
#include "ShaderGen.hpp"
#include "LODGen.hpp"
#include "core/utility/ConcurrentLRU.hpp"
#include "core/threading/UnifiedThreadingSystem.hpp"
#include <future>

struct TrailBundle {
  TrailHandle   handle;
  LODData       lodData;
};

class TrailAssetFactory {
  // TODO: Replace with actual implementation of ConcurrentLRU
  //ConcurrentLRU<uint64_t, TrailBundle> cache;
  
  // [[memory:4835707]]
  // TODO: Replace with actual implementation of MultithreadBus
  //MultithreadBus                           pool;

public:
  std::future<TrailBundle> generateAsync(
    const TrailParams&    tp,
    const SegmentParams&  sp,
    const BehaviorParams& bp,
    const RenderParams&   rp,
    const LODParams&      lp
  );
};
