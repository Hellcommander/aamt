#pragma once

#include <string>
#include <vector>

// Core trail settings
struct TrailParams {
  std::string  id;                   // unique asset name
  float        lifeTime;             // seconds before segment fades
  bool         loop;                 // continuous vs. one-shot
  int          maxSegments;          // maximum segment count
  bool         gpuDriven;            // CPU vs. GPU update
};

// Segment sampling along emitter path
struct SegmentParams {
  enum Type { Ribbon, Tube, Decal } type;
  // TODO: Replace with proper Vector class
  // Vec3        offset;                // local position offset
  float       widthStart;            // start width
  float       widthEnd;              // end width
  int          radialSubdiv;         // for Tube type
  bool         capEnds;              // close caps for Tube
};

// Behavioral modifiers over trail
struct BehaviorParams {
  float        jitter;               // random offset magnitude
  float        drag;                 // damp positional changes
  // TODO: Replace with proper Vector class
  // Vec2         speedRange;           // per-segment speed variance
  // Vec2         twistRange;           // random rotation per segment
};

// Styling: color, UV, blending
struct RenderParams {
  std::string  texture;              // path to trail atlas
  bool         animateUV;            // scroll UV over time
  // TODO: Replace with proper Vector class
  // Vec4         colorStart;           // RGBA at segment birth
  // Vec4         colorEnd;             // RGBA at segment death
  bool         additive;             // additive vs. alpha blend
};

// LOD thresholds and scales
struct LODParams {
  std::vector<float> screenSizes;    // [high, mid, low] thresholds
  std::vector<int>   segmentCounts;  // maxSegments per LOD tier
  std::vector<float> widthScales;    // width multiplier per LOD
};
