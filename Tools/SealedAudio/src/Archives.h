#pragma once

#include <cstdint>
#include <string>
#include <vector>

// Every Data\SealedAudio\*.mtsa, read once at plugin load. Lookups take the engine's path below Data\ (any case, either
// slash) and answer with the unsealed bytes. Two archives holding the same path: the one loaded later (alphabetical) wins,
// and the clash is logged once.
namespace SealedAudio::Archives
{
	struct Stats
	{
		std::size_t archives{ 0 };
		std::size_t entries{ 0 };
		std::size_t refused{ 0 };
	};

	// `archiveDir` holds the *.mtsa files. `key32` overrides the compiled-in key (nullptr keeps it). Returns what was mounted.
	Stats Load(const std::wstring& archiveDir, const unsigned char* key32);

	// True when an archive holds that path (relative to Data, e.g. "Sound\fx\mymod\hit.wav").
	[[nodiscard]] bool Has(const std::string& relativeToData);

	// The unsealed bytes, or an empty vector when no archive holds the path.
	[[nodiscard]] std::vector<unsigned char> Read(const std::string& relativeToData, std::uint32_t* size = nullptr);

	// True when some archive holds a path under this folder (relative to Data, e.g. "Sound" or "Soundx\mymod"). The
	// engine only looks for loose files under folders that exist, so these folders must exist for it.
	[[nodiscard]] bool HasDirectory(const std::string& relativeToData);

	struct Child
	{
		std::string   name;       // as stored (one path segment)
		bool          isDir{ false };
		std::uint64_t size{ 0 };
	};

	// What the sealed tree holds directly under a folder (relative to Data, e.g. "Sound\fx"): subfolders and files.
	// Empty when no archive covers the folder. The engine indexes loose files by listing folders, so these are what it
	// must see.
	[[nodiscard]] std::vector<Child> Children(const std::string& relativeToData);

	// The size an archive reports for the path, without unsealing; false when absent.
	[[nodiscard]] bool SizeOf(const std::string& relativeToData, std::uint64_t& size);

	// How many archives were mounted.
	[[nodiscard]] std::uint32_t ArchiveCount();

	// For the self-test: every path mounted, normalized.
	[[nodiscard]] std::vector<std::string> Paths();
}
