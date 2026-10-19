#pragma once

// Batch helpers of the audio generator family. They drive the generator classes
// (SampleGen, SynthGen, EffectGen, MixerGen, ExportGen, LODGen) for whole track lists and
// are used by AudioAssetFactory's composite generation. (They used to be namespaces named
// after the classes, which collided with the class names.)

#include "AudioAssetTypes.hpp"
#include <string>
#include <vector>

namespace MagiTech {
namespace Audio {

class SampleGen;
class SynthGen;
class EffectGen;
class MixerGen;
class ExportGen;
class LODGen;

namespace AudioGenerators {

// Renders every sample request (interleaved stereo, 44.1 kHz).
std::vector<AudioBuffer> processSamples(SampleGen& generator, const std::vector<SampleParams>& params);

// Renders every synth request; duration > 0 overrides each request's note length (seconds).
std::vector<AudioBuffer> generateSynths(SynthGen& generator, const std::vector<SynthParams>& params, float duration);

// Runs the effect chain of ep over the input (input unchanged when the chain is empty).
AudioBuffer applyEffects(EffectGen& generator, const AudioBuffer& input, const EffectParams& ep);

// Mixes sample and synth tracks (samples first) with the mixer settings.
AudioBuffer mixTracks(MixerGen& generator, const std::vector<AudioBuffer>& samples,
                      const std::vector<AudioBuffer>& synths, const MixerParams& mp);

// Exports buf with xp and writes the first produced file to outPath. Returns false on failure.
bool exportAudio(ExportGen& generator, const AudioBuffer& buf, const ExportParams& xp, const std::string& outPath);

// Derives the LOD chain of lp from the master buffer (one buffer per LOD level).
std::vector<AudioBuffer> resampleLODs(LODGen& generator, const AudioBuffer& master, const LODParams& lp);

} // namespace AudioGenerators
} // namespace Audio
} // namespace MagiTech
