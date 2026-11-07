#pragma once

// Optional ([Debug] bCrashLog=1): when the game dies of an unhandled exception, write what was executing, module by
// module with symbols where a PDB is beside the module, to <log folder>\SealedAudio-crash.log. For finding which plugin
// or engine function fell over on a machine without a crash logger. Off by default; it is diagnostics, not a feature.
namespace SealedAudio::CrashLog
{
	void Install();

	// Diagnostic: also log first-chance C++ exceptions and access violations raised from inside a plugin dll (noisy; only
	// while the game loads).
	void WatchFirstChance();

	// Writes "<why>" and the calling thread's stack to SealedAudio-crash.log (appending). Used by the exit hooks below.
	void WriteStack(const char* why);

	// True once the game has reached its data-loaded milestone; exits after that are normal quits and are not logged.
	void MarkLoaded();
	bool ShouldLogExit();
}
