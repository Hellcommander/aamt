// The C ABI over the core (see include/sealed_audio.h). Hosts link the core statically or load SealedAudioCore.dll.

#include "sealed_audio.h"

#include "Archives.h"
#include "CrashLog.h"
#include "FileHooks.h"
#include "Log.h"

#include <Windows.h>

#include <atomic>
#include <cstring>
#include <string>

namespace
{
	constexpr const char* kVersion = "SealedAudio core 1.1.0 (MTSA1)";
	std::atomic<bool>     g_initialized{ false };
	std::wstring          g_dataDir;
	SealedAudio::Hooks::Options g_hookOptions;

	std::wstring ExeDir()
	{
		wchar_t buf[MAX_PATH]{};
		::GetModuleFileNameW(nullptr, buf, MAX_PATH);
		std::wstring s(buf);
		const auto slash = s.find_last_of(L"\\/");
		return slash == std::wstring::npos ? L"." : s.substr(0, slash);
	}

	std::string Narrow(const std::wstring& w)
	{
		const int n = ::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
		std::string s((std::size_t)n, '\0');
		::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
		return s;
	}
}

extern "C"
{
	SA_API void sa_config_init(sa_config* c)
	{
		if (!c) {
			return;
		}
		std::memset(c, 0, sizeof(*c));
		c->size = sizeof(*c);
		c->hook_listings = c->hook_attributes = c->hook_serve = c->hook_mappings = 1;
		c->patch_modules = 1;
		c->max_probe_lines = 200;
	}

	SA_API int32_t sa_init(const sa_config* c)
	{
		using namespace SealedAudio;
		if (!c || c->size < sizeof(uint32_t) * 1) {
			return -1;
		}
		if (g_initialized.exchange(true)) {
			return -2;
		}
		// the struct may come from an older or newer header: read only what fits
		sa_config cfg;
		sa_config_init(&cfg);
		std::memcpy(&cfg, c, c->size < sizeof(cfg) ? c->size : sizeof(cfg));
		cfg.size = sizeof(cfg);

		Log::Open(cfg.log_file);
		if (cfg.log) {
			Log::SetCallback(cfg.log, cfg.log_user);
		}
		Log::Info("%s", kVersion);

		g_dataDir = cfg.data_dir && *cfg.data_dir ? std::wstring(cfg.data_dir) : ExeDir() + L"\\Data";
		const std::wstring archiveDir = cfg.archive_dir && *cfg.archive_dir ? std::wstring(cfg.archive_dir) : g_dataDir + L"\\SealedAudio";
		Log::Info("data folder %s, archives %s", Narrow(g_dataDir).c_str(), Narrow(archiveDir).c_str());

		const auto stats = Archives::Load(archiveDir, cfg.key32);
		Log::Info("%zu archive(s), %zu sealed sounds, %zu refused", stats.archives, stats.entries, stats.refused);

		g_hookOptions = Hooks::Options{};
		g_hookOptions.logProbes = cfg.log_probes != 0;
		g_hookOptions.maxProbeLogs = cfg.max_probe_lines > 0 ? cfg.max_probe_lines : 200;
		g_hookOptions.logImports = cfg.log_imports != 0;
		g_hookOptions.listings = cfg.hook_listings != 0;
		g_hookOptions.attributes = cfg.hook_attributes != 0;
		g_hookOptions.serve = cfg.hook_serve != 0;
		g_hookOptions.mappings = cfg.hook_mappings != 0;
		g_hookOptions.patchModules = cfg.patch_modules;
		g_hookOptions.dataDir = g_dataDir;
		if (cfg.data_folder_name && *cfg.data_folder_name) {
			g_hookOptions.dataFolderName = cfg.data_folder_name;
		}
		if (cfg.module_prefixes) {
			g_hookOptions.modulePrefixes = cfg.module_prefixes;
		}
		const int hooked = Hooks::Install(g_hookOptions);
		Log::Info("%d file imports hooked in the executable", hooked);
		if (hooked == 0) {
			Log::Error("the executable imports none of the file functions; sealed sounds cannot be served");
		}
		return hooked;
	}

	SA_API int32_t sa_patch_new_modules(void)
	{
		if (!g_initialized) {
			return 0;
		}
		const int n = SealedAudio::Hooks::PatchNewModules();
		if (n > 0) {
			SealedAudio::Log::Info("%d more file imports hooked in modules loaded later", n);
		}
		return n;
	}

	SA_API void sa_mark_loaded(void)
	{
		SealedAudio::CrashLog::MarkLoaded();
		SealedAudio::Hooks::LogCounters("at the host's data-loaded milestone");
	}

	SA_API void sa_diagnostics(int32_t crash_log, int32_t exit_hooks, int32_t first_chance)
	{
		using namespace SealedAudio;
		if (crash_log) {
			CrashLog::Install();
		}
		if (first_chance) {
			CrashLog::WatchFirstChance();
		}
		if (exit_hooks && g_initialized) {
			g_hookOptions.exitLog = true;
			Log::Info("exit hooks in %d import entries across all modules", Hooks::PatchExitHooksEverywhere());
		}
	}

	SA_API int32_t sa_self_test(void)
	{
		using namespace SealedAudio;
		if (!g_initialized) {
			return -1;
		}
		const std::wstring path = g_dataDir + L"\\Sound\\fx\\sealedaudio\\selftest.wav";
		if (!Archives::Has("Sound\\fx\\sealedaudio\\selftest.wav")) {
			Log::Info("SELFTEST skipped: no archive holds sound\\fx\\sealedaudio\\selftest.wav (seal the test mod)");
			return -1;
		}
		int fails = 0;
		auto check = [&](bool ok, const char* what) { if (!ok) fails++; Log::Info("SELFTEST %s %s", ok ? "PASS" : "FAIL", what); };
		check(Hooks::TestGetFileAttributesW(path.c_str()) != INVALID_FILE_ATTRIBUTES, "an attribute check sees the sealed file");
		HANDLE h = Hooks::TestCreateFileW(path.c_str());
		check(h != INVALID_HANDLE_VALUE, "opening the sealed path gives a handle");
		if (h == INVALID_HANDLE_VALUE) {
			return fails;
		}
		LARGE_INTEGER size{};
		check(Hooks::TestGetFileSizeEx(h, &size) && size.QuadPart > 44, "the handle reports the sound's size");
		char head[12]{};
		DWORD got = 0;
		check(Hooks::TestReadFile(h, head, 12, &got) && got == 12 && std::memcmp(head, "RIFF", 4) == 0 && std::memcmp(head + 8, "WAVE", 4) == 0, "the first bytes read are a RIFF WAVE header");
		LARGE_INTEGER back{};
		back.QuadPart = -4;
		LARGE_INTEGER np{};
		check(Hooks::TestSetFilePointerEx(h, back, &np, FILE_END) && np.QuadPart == size.QuadPart - 4, "seeking from the end lands 4 bytes before it");
		char tail[8]{};
		check(Hooks::TestReadFile(h, tail, 8, &got) && got == 4, "a read across the end returns the 4 bytes left");
		check(Hooks::TestReadFile(h, tail, 8, &got) && got == 0, "a read at the end returns 0 bytes, no error");
		HANDLE map = Hooks::TestCreateFileMapping(h);
		check(map != nullptr, "a file mapping of the handle can be made");
		if (map) {
			const void* view = ::MapViewOfFile(map, FILE_MAP_READ, 0, 0, 0);
			check(view && std::memcmp(view, "RIFF", 4) == 0, "the mapped view starts with the sound's bytes");
			if (view) ::UnmapViewOfFile(view);
			::CloseHandle(map);
		}
		check(Hooks::TestCloseHandle(h) == TRUE, "closing the handle works");
		std::uint32_t total = 0;
		auto bytes = Archives::Read("Sound\\fx\\sealedaudio\\selftest.wav", &total);
		check(bytes.size() == (std::size_t)size.QuadPart && total == bytes.size(), "the archive and the handle agree on the size");
		Log::Info(fails == 0 ? "SELFTEST ALL PASS" : "SELFTEST %d FAILED", fails);
		return fails;
	}

	SA_API int32_t sa_has(const char* relative_path)
	{
		return relative_path && g_initialized && SealedAudio::Archives::Has(relative_path) ? 1 : 0;
	}

	SA_API int32_t sa_read(const char* relative_path, void* buffer, uint32_t capacity, uint32_t* size)
	{
		if (!relative_path || !g_initialized) {
			return 0;
		}
		std::uint32_t n = 0;
		auto bytes = SealedAudio::Archives::Read(relative_path, &n);
		if (bytes.empty() && !SealedAudio::Archives::Has(relative_path)) {
			return 0;
		}
		if (size) {
			*size = (uint32_t)bytes.size();
		}
		if (!buffer) {
			return 1;
		}
		if (capacity < bytes.size()) {
			return -1;
		}
		std::memcpy(buffer, bytes.data(), bytes.size());
		return 1;
	}

	SA_API void sa_mounted(uint32_t* archives, uint32_t* entries)
	{
		const auto paths = SealedAudio::Archives::Paths();
		if (entries) *entries = (uint32_t)paths.size();
		if (archives) *archives = SealedAudio::Archives::ArchiveCount();
	}

	SA_API void sa_counters(uint64_t out[5])
	{
		if (!out) {
			return;
		}
		const auto c = SealedAudio::Hooks::Get();
		out[0] = c.served; out[1] = c.reads; out[2] = c.probesSeen; out[3] = c.probesAnswered; out[4] = c.looseWins;
	}

	SA_API const char* sa_version(void)
	{
		return kVersion;
	}
}
