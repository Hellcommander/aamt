#pragma once

#include <Windows.h>

#include <cstdint>
#include <string>

// The game reaches loose files through the Win32 file API it imports from kernel32 (CreateFileW, ReadFile, ...). These
// hooks sit in the game executable's import table, so they need no engine address and survive game updates: when the engine
// opens Data\<path> for reading, no real file is there, and a sealed archive holds that path, it gets a virtual handle
// backed by the unsealed bytes, and every later call on that handle (read, seek, size, type, close) is answered from
// memory. A loose file at the same path always wins, so authors can test a sound by dropping it in.
namespace SealedAudio::Hooks
{
	struct Options
	{
		bool logProbes{ false };      // log the engine's opens/attribute checks under sound\ and music\ (what it asks for, and how)
		int  maxProbeLogs{ 200 };
		bool logImports{ false };     // list the file APIs the game imports, once
		// Each hook family can be switched off ([Hooks] in the ini) to narrow a problem down without a rebuild.
		bool listings{ true };        // sealed folders and files appear in directory listings
		bool attributes{ true };      // attribute checks of sealed paths and folders are answered
		bool serve{ true };           // opening a sealed path gives a virtual handle
		bool mappings{ true };        // file mappings over virtual handles
		bool exitLog{ false };        // log the stack of whoever ends the process before the game has loaded (diagnostics)
		std::wstring dataFolderName{ L"Data" };        // the path segment that marks the game's data folder
		std::wstring dataDir;                           // absolute data folder (lower-cased inside); modules under it are plugins
		int          patchModules{ 1 };                 // 0 executable only; 1 + extender/plugins; 2 every module under the game folder
		std::wstring modulePrefixes{ L"skse;sfse;f4se;nvse;obse" };   // script-extender runtime dlls, by name prefix
	};

	struct Counters
	{
		std::uint64_t served{ 0 };          // virtual handles handed out
		std::uint64_t reads{ 0 };           // ReadFile calls answered from memory
		std::uint64_t probesSeen{ 0 };      // sound/music paths the engine asked about
		std::uint64_t probesAnswered{ 0 };  // attribute checks answered for sealed paths
		std::uint64_t looseWins{ 0 };       // sealed paths a real loose file shadowed
	};

	// Patches the import tables of the game executable and of every other module loaded from the game's folder (script
	// extender plugins read their own sound files through the same Win32 functions, so sealed sounds must reach them too).
	// Returns how many imports were hooked in the executable (0 means nothing works).
	int Install(const Options& options);

	// Patches modules loaded since Install (the script extender loads plugins in order; this runs again once all are in).
	int PatchNewModules();

	// Diagnostic: puts the ExitProcess/TerminateProcess hooks into every module in the process, system ones included.
	int PatchExitHooksEverywhere();

	[[nodiscard]] Counters Get();
	void LogCounters(const char* when);

	// For the self-test: the same code paths the engine's calls take.
	HANDLE  TestCreateFileW(const wchar_t* path);
	BOOL    TestReadFile(HANDLE h, void* buffer, DWORD toRead, DWORD* read);
	BOOL    TestGetFileSizeEx(HANDLE h, LARGE_INTEGER* size);
	BOOL    TestSetFilePointerEx(HANDLE h, LARGE_INTEGER distance, LARGE_INTEGER* newPos, DWORD method);
	BOOL    TestCloseHandle(HANDLE h);
	DWORD   TestGetFileAttributesW(const wchar_t* path);
	HANDLE  TestCreateFileMapping(HANDLE h);
}
