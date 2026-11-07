/* sealed_audio.h: the Sealed Audio core, a C ABI any game host can call.
 *
 * What it does: mounts sealed sound archives (MTSA1, made by audio_seal.py) and makes their entries appear to the
 * process as loose files under the game's data folder, by patching the Win32 file functions in the import tables of
 * the game executable and (optionally) of its script-extender plugins. Directory listings show the sealed folders and
 * files, attribute checks answer with their sizes, opening one for reading yields a memory-backed handle, and reads,
 * seeks, sizes and file mappings on that handle are answered from memory. A real loose file at the same path wins.
 *
 * How to wire it:
 *   - a script-extender plugin (SKSE, SKSEVR, SFSE, F4SE, ...): fill sa_config and call sa_init() in your Load; call
 *     sa_patch_new_modules() once all plugins are loaded and sa_mark_loaded() when the game's data is loaded;
 *   - any game without an extender: the version.dll proxy host (hosts/proxy) does the above from a sealed_audio.ini;
 *   - managed or scripted hosts: load SealedAudioCore.dll and call the same functions (bindings/python, bindings/csharp).
 *
 * Paths given to sa_has/sa_read are relative to the data folder, any case, either slash: "Sound\fx\mymod\hit.wav".
 * Thread safety: sa_init once, from the host's load; everything else may be called from any thread afterwards.
 */
#ifndef SEALED_AUDIO_H
#define SEALED_AUDIO_H

#include <stdint.h>
#include <wchar.h>

#if defined(SEALED_AUDIO_BUILD_DLL)
#	define SA_API __declspec(dllexport)
#elif defined(SEALED_AUDIO_USE_DLL)
#	define SA_API __declspec(dllimport)
#else
#	define SA_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef void (*sa_log_fn)(int level, const char* message, void* user);   /* level: 0 info, 1 warning, 2 error */

typedef struct sa_config {
	uint32_t       size;                 /* sizeof(sa_config): lets the ABI grow */
	const wchar_t* data_dir;             /* the folder the game reads loose files from, absolute, e.g. L"...\\Data"; NULL = <exe folder>\\Data */
	const wchar_t* data_folder_name;     /* the segment of a path that marks the data folder, L"Data" by default */
	const wchar_t* archive_dir;          /* folder with *.mtsa; NULL = <data_dir>\\SealedAudio */
	const wchar_t* log_file;             /* full path of the log; NULL = no file (use the callback) */
	sa_log_fn      log;                  /* optional callback for log lines */
	void*          log_user;
	const uint8_t* key32;                /* 32-byte archive key; NULL = the key compiled into the core (SealedKey.h) */
	int32_t        hook_listings;        /* 1 (default): sealed folders/files appear in directory listings */
	int32_t        hook_attributes;      /* 1: attribute checks of sealed paths are answered */
	int32_t        hook_serve;           /* 1: opening a sealed path yields a memory-backed handle */
	int32_t        hook_mappings;        /* 1: file mappings over such handles */
	int32_t        patch_modules;        /* 0: the executable only; 1 (default): also modules under data_dir and whose name starts with a module_prefixes entry; 2: every module under the game folder */
	const wchar_t* module_prefixes;      /* semicolon list, default L"skse;sfse;f4se;nvse;obse"; the script-extender runtime dlls */
	int32_t        log_probes;           /* 1: log the game's opens/attribute checks under sound\\ and music\\ */
	int32_t        max_probe_lines;      /* default 200 */
	int32_t        log_imports;          /* 1: list the file functions the executable imports */
} sa_config;

/* Fills a config with defaults (size set, hooks on, patch_modules 1); then set what differs. */
SA_API void sa_config_init(sa_config* config);

/* Mounts the archives and installs the hooks. Returns the number of file imports hooked in the executable (0 means
 * nothing is served), or a negative value: -1 bad config, -2 already initialized, -3 archive folder unreadable. */
SA_API int32_t sa_init(const sa_config* config);

/* Patches modules loaded since sa_init (script extenders load plugins in order). Returns imports hooked. */
SA_API int32_t sa_patch_new_modules(void);

/* Tell the core the game has finished loading its data (diagnostics stop treating exits as abnormal). */
SA_API void sa_mark_loaded(void);

/* Diagnostics, off by default: 1 = on. crash_log writes <log folder>\\SealedAudio-crash.log with a symbolized stack on
 * an unhandled exception; exit_hooks log who calls ExitProcess/TerminateProcess before sa_mark_loaded; first_chance
 * logs first-chance C++ exceptions and access violations during loading (noisy; slows start-up while it logs). */
SA_API void sa_diagnostics(int32_t crash_log, int32_t exit_hooks, int32_t first_chance);

/* Opens, sizes, seeks, reads, maps and closes a mounted sound through the hooked code paths; the entry must be
 * "Sound\\fx\\sealedaudio\\selftest.wav" (seal the test mod). Returns 0 when every step passes, -1 when the entry is not
 * mounted, else the number of failed steps. Steps are logged as SELFTEST lines. */
SA_API int32_t sa_self_test(void);

/* 1 when some archive holds the path (relative to the data folder). */
SA_API int32_t sa_has(const char* relative_path);

/* The unsealed bytes. With buffer NULL, only *size is set. Returns 1 on success, 0 when absent, -1 when the buffer is too small (size still set). */
SA_API int32_t sa_read(const char* relative_path, void* buffer, uint32_t capacity, uint32_t* size);

/* How many sounds are mounted, and from how many archives. */
SA_API void sa_mounted(uint32_t* archives, uint32_t* entries);

/* Counters since sa_init: served handles, reads from memory, probes seen, attribute checks answered, loose files that won. */
SA_API void sa_counters(uint64_t out[5]);

SA_API const char* sa_version(void);

#ifdef __cplusplus
}
#endif
#endif
