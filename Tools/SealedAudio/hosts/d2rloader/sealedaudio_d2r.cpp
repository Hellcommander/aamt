// D2RLoader host for the Sealed Audio core: a Diablo II Resurrected plugin (d2rloader.net PluginSDK, ABI 2-4) that serves
// sealed sound archives (*.mtsa) to the game as if their .flac/.wav files sat loose in the mod's data folder, so a mod's
// sounds.txt rows and file paths stay exactly as they are while licensed clips never ship as copyable files.
//
// D2R differs from the extender hosts in one way: the game code is packed, so the executable imports none of the Win32
// file functions (it resolves them at run time). The core's patch_system option therefore redirects kernel32's own export
// stubs, which reaches every caller in the process; D2RLoader's core dll (which also reads mod files) is import-patched
// as usual through module_prefixes. Everything that serves sounds lives in the core (include/sealed_audio.h).
//
// Layout in a mod:   mods\<Mod>\d2rloader\plugins\sealedaudio.dll
//                    mods\<Mod>\d2rloader\SealedAudio\*.mtsa        entries relative to data\: hd/global/sfx/<mod>/x.flac
//                    (or mods\<Mod>\d2rloader\plugins\SealedAudio\*.mtsa, where a D2RMM D2RLoader package deploys them)
//                    mods\<Mod>\d2rloader\config\sealedaudio.toml   created with the defaults below on first run
// (or the same under <game>\d2rloader\ for a global install).

#include "sealed_audio.h"

#include <D2RLPlugin/api.h>

#include <Windows.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace
{
	constexpr const char* kDefaultToml =
		"# SealedAudio: serves sealed sound archives (*.mtsa) to Diablo II Resurrected as loose files.\n"
		"# Archives: <this scope>\\d2rloader\\SealedAudio\\*.mtsa (else d2rloader\\plugins\\SealedAudio) unless archive_dir\n"
		"# says otherwise (absolute, or relative to the scope's d2rloader folder, then its plugins folder).\n"
		"archive_dir = \"SealedAudio\"\n"
		"\n"
		"# Local key store: archives sealed with Seal-LocalAudio.ps1 (audio_seal.py --local-key) open with a key that stays on\n"
		"# this machine and never ships with the mod. Semicolon list of folders; empty = %LOCALAPPDATA%\\SealedAudio\\keys.\n"
		"key_dirs = \"\"\n"
		"\n"
		"# Redirect kernel32's file stubs process-wide. Needed for D2R: the packed game imports no file functions.\n"
		"patch_system = true\n"
		"# 0: executable only; 1: also modules named by module_prefixes (D2RLoader's core); 2: every dll in the game folder\n"
		"patch_modules = 1\n"
		"module_prefixes = \"d2rcore;d2r_loader\"\n"
		"\n"
		"# Hook families, for narrowing a problem down.\n"
		"listings = true\n"
		"attributes = true\n"
		"serve = true\n"
		"mappings = true\n"
		"\n"
		"# Diagnostics. log_probes lists what the game opens under probe_prefixes (and whether it was sealed, loose or missing).\n"
		"log_probes = false\n"
		"max_probe_lines = 200\n"
		"probe_prefixes = \"hd\\\\global\\\\sfx;hd\\\\global\\\\music;hd\\\\local;global\\\\sfx;global\\\\music\"\n"
		"log_imports = false\n"
		"self_test = false\n"
		"crash_log = false\n";

	const D2RL::PluginContext* g_context{ nullptr };

	// The few settings this plugin has, read from the loader's TOML config. Flat "key = value" lines only: strings in
	// double quotes (with \\ and \" escapes), true/false, integers; # starts a comment outside quotes.
	struct Settings
	{
		std::wstring archiveDir{ L"SealedAudio" };
		std::wstring keyDirs;
		bool         patchSystem{ true };
		int          patchModules{ 1 };
		std::wstring modulePrefixes{ L"d2rcore;d2r_loader" };
		bool         listings{ true }, attributes{ true }, serve{ true }, mappings{ true };
		bool         logProbes{ false };
		int          maxProbeLines{ 200 };
		std::wstring probePrefixes{ L"hd\\global\\sfx;hd\\global\\music;hd\\local;global\\sfx;global\\music" };
		bool         logImports{ false }, selfTest{ false }, crashLog{ false };
	};

	std::wstring Widen(const std::string& s)
	{
		if (s.empty()) {
			return {};
		}
		const int n = ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
		std::wstring w((std::size_t)n, L'\0');
		::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), n);
		return w;
	}

	std::string Narrow(const std::wstring& w)
	{
		if (w.empty()) {
			return {};
		}
		const int n = ::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
		std::string s((std::size_t)n, '\0');
		::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
		return s;
	}

	std::string Trim(const std::string& s)
	{
		const auto a = s.find_first_not_of(" \t\r\n");
		if (a == std::string::npos) {
			return {};
		}
		const auto b = s.find_last_not_of(" \t\r\n");
		return s.substr(a, b - a + 1);
	}

	void Apply(Settings& st, const std::string& key, const std::string& raw, bool quoted)
	{
		const bool b = raw == "true" || raw == "1";
		const int i = std::atoi(raw.c_str());
		if (key == "archive_dir" && quoted) st.archiveDir = Widen(raw);
		else if (key == "key_dirs" && quoted) st.keyDirs = Widen(raw);
		else if (key == "patch_system") st.patchSystem = b;
		else if (key == "patch_modules") st.patchModules = i;
		else if (key == "module_prefixes" && quoted) st.modulePrefixes = Widen(raw);
		else if (key == "listings") st.listings = b;
		else if (key == "attributes") st.attributes = b;
		else if (key == "serve") st.serve = b;
		else if (key == "mappings") st.mappings = b;
		else if (key == "log_probes") st.logProbes = b;
		else if (key == "max_probe_lines") st.maxProbeLines = i;
		else if (key == "probe_prefixes" && quoted) st.probePrefixes = Widen(raw);
		else if (key == "log_imports") st.logImports = b;
		else if (key == "self_test") st.selfTest = b;
		else if (key == "crash_log") st.crashLog = b;
	}

	void Parse(Settings& st, const std::string& toml)
	{
		std::size_t start = 0;
		while (start < toml.size()) {
			std::size_t end = toml.find('\n', start);
			if (end == std::string::npos) end = toml.size();
			const std::string line = toml.substr(start, end - start);
			start = end + 1;
			const auto eq = line.find('=');
			if (eq == std::string::npos) {
				continue;
			}
			const std::string key = Trim(line.substr(0, eq));
			if (key.empty() || key[0] == '#' || key[0] == '[') {
				continue;
			}
			std::string rest = Trim(line.substr(eq + 1));
			if (!rest.empty() && rest[0] == '"') {
				std::string value;
				for (std::size_t k = 1; k < rest.size() && rest[k] != '"'; k++) {
					if (rest[k] == '\\' && k + 1 < rest.size()) {
						k++;
					}
					value.push_back(rest[k]);
				}
				Apply(st, key, value, true);
			} else {
				const auto hash = rest.find('#');
				Apply(st, key, Trim(hash == std::string::npos ? rest : rest.substr(0, hash)), false);
			}
		}
	}

	Settings LoadSettings(const D2RL::PluginContext* ctx)
	{
		Settings st;
		if (!ctx->EnsureConfig(kDefaultToml)) {
			ctx->LogWarn("SealedAudio: could not create the default config; using built-in defaults");
		}
		const auto read = D2RL::ApiReadConfig(ctx->GetApi());
		if (!read) {
			return st;
		}
		std::uint32_t need = 0;
		read(ctx, nullptr, 0, &need);
		if (need == 0) {
			return st;
		}
		std::string text(need + 1, '\0');
		if (read(ctx, text.data(), (std::uint32_t)text.size(), &need)) {
			text.resize(std::strlen(text.c_str()));
			Parse(st, text);
		}
		return st;
	}

	std::wstring Parent(const std::wstring& path)
	{
		std::wstring p = path;
		while (!p.empty() && (p.back() == L'\\' || p.back() == L'/')) p.pop_back();
		const auto slash = p.find_last_of(L"\\/");
		return slash == std::wstring::npos ? std::wstring{} : p.substr(0, slash);
	}

	bool IsDir(const std::wstring& path)
	{
		const DWORD a = ::GetFileAttributesW(path.c_str());
		return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_DIRECTORY);
	}

	bool IsAbsolute(const std::wstring& p)
	{
		return (p.size() > 1 && p[1] == L':') || (p.size() > 1 && p[0] == L'\\' && p[1] == L'\\');
	}

	std::wstring ExeDir()
	{
		wchar_t buf[MAX_PATH]{};
		::GetModuleFileNameW(nullptr, buf, MAX_PATH);
		return Parent(buf);
	}

	// The folder D2R reads this mod's loose files from: mods\<Mod>\<Mod>.mpq\data, else mods\<Mod>\data, else <game>\data.
	// Only used for logging, the self-test path and module selection; sealed paths match on the "data" segment anywhere.
	std::wstring DataDir(const D2RL::PluginContext* ctx)
	{
		if (ctx->modDirectory && *ctx->modDirectory) {
			const std::wstring mod = ctx->modDirectory;
			if (ctx->activeMod && *ctx->activeMod) {
				const std::wstring mpq = mod + L"\\" + Widen(ctx->activeMod) + L".mpq\\data";
				if (IsDir(mpq)) return mpq;
			}
			WIN32_FIND_DATAW fd{};
			HANDLE h = ::FindFirstFileW((mod + L"\\*.mpq").c_str(), &fd);
			if (h != INVALID_HANDLE_VALUE) {
				std::wstring found;
				do {
					if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && IsDir(mod + L"\\" + fd.cFileName + L"\\data")) {
						found = mod + L"\\" + fd.cFileName + L"\\data";
						break;
					}
				} while (::FindNextFileW(h, &fd));
				::FindClose(h);
				if (!found.empty()) return found;
			}
			if (IsDir(mod + L"\\data")) return mod + L"\\data";
		}
		return ExeDir() + L"\\data";
	}

	void Log(const char* fmt, const char* a = "", const char* b = "")
	{
		if (!g_context) return;
		char line[1024];
		std::snprintf(line, sizeof(line), fmt, a, b);
		g_context->LogInfo(line);
	}

	// D2RLoader has no "all plugins loaded" or "data loaded" notification for plugins, so a worker picks up dlls loaded
	// after this one and tells the core when start-up is over.
	DWORD WINAPI Milestones(void*)
	{
		::Sleep(15000);
		sa_patch_new_modules();
		::Sleep(45000);
		sa_patch_new_modules();
		sa_mark_loaded();
		std::uint64_t c[5]{};
		sa_counters(c);
		char line[256];
		std::snprintf(line, sizeof(line), "SealedAudio: after start-up %llu sealed sounds served, %llu reads from memory, %llu probes seen, %llu loose files won",
			(unsigned long long)c[0], (unsigned long long)c[1], (unsigned long long)c[2], (unsigned long long)c[4]);
		if (g_context) g_context->LogInfo(line);
		return 0;
	}

	bool Startup(const D2RL::PluginContext* ctx)
	{
		const Settings st = LoadSettings(ctx);

		// mods\<Mod>\d2rloader\plugins -> mods\<Mod>\d2rloader
		const std::wstring pluginDir = ctx->pluginDirectory && *ctx->pluginDirectory ? std::wstring(ctx->pluginDirectory) : ExeDir() + L"\\d2rloader\\plugins";
		const std::wstring loaderDir = Parent(pluginDir);
		// A relative archive_dir is looked up under d2rloader\ first, then under d2rloader\plugins\ (the only folder a D2RMM
		// D2RLoader package deploys arbitrary files into).
		std::wstring archives = IsAbsolute(st.archiveDir) ? st.archiveDir : loaderDir + L"\\" + st.archiveDir;
		if (!IsAbsolute(st.archiveDir) && !IsDir(archives) && IsDir(pluginDir + L"\\" + st.archiveDir))
			archives = pluginDir + L"\\" + st.archiveDir;
		const std::wstring data = DataDir(ctx);
		const std::wstring logDir = ExeDir() + L"\\d2rloader\\logs";
		::CreateDirectoryW(Parent(logDir).c_str(), nullptr);
		::CreateDirectoryW(logDir.c_str(), nullptr);
		const std::wstring log = logDir + L"\\SealedAudio.log";

		if (!IsDir(archives)) {
			Log("SealedAudio: no archive folder at %s; nothing to serve", Narrow(archives).c_str());
			return true;   // loaded, idle: a mod may ship the plugin before its archives
		}

		sa_config cfg;
		sa_config_init(&cfg);
		cfg.data_dir = data.c_str();
		cfg.data_folder_name = L"data";
		cfg.archive_dir = archives.c_str();
		cfg.log_file = log.c_str();
		cfg.hook_listings = st.listings;
		cfg.hook_attributes = st.attributes;
		cfg.hook_serve = st.serve;
		cfg.hook_mappings = st.mappings;
		cfg.patch_modules = st.patchModules;
		cfg.module_prefixes = st.modulePrefixes.c_str();
		cfg.log_probes = st.logProbes;
		cfg.max_probe_lines = st.maxProbeLines;
		cfg.log_imports = st.logImports;
		cfg.patch_system = st.patchSystem;
		cfg.probe_prefixes = st.probePrefixes.c_str();
		cfg.key_dirs = st.keyDirs.empty() ? nullptr : st.keyDirs.c_str();

		// The hooks point into this dll for the rest of the process; it must never be unloaded.
		HMODULE self{ nullptr };
		::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN, reinterpret_cast<LPCWSTR>(&Startup), &self);

		const int hooked = sa_init(&cfg);
		std::uint32_t archiveCount = 0, entries = 0;
		sa_mounted(&archiveCount, &entries);
		char line[512];
		std::snprintf(line, sizeof(line), "SealedAudio: %u archive(s), %u sealed sounds, %d file functions hooked; data %s; log %s",
			archiveCount, entries, hooked, Narrow(data).c_str(), Narrow(log).c_str());
		ctx->LogInfo(line);
		if (hooked <= 0) {
			ctx->LogError("SealedAudio: no file function hooked; sealed sounds will not play (see SealedAudio.log)");
			return hooked == 0;   // 0: loaded but idle; negative: a configuration error
		}
		if (st.crashLog) {
			sa_diagnostics(1, 1, 1);
		}
		if (st.selfTest) {
			const int fails = sa_self_test();
			ctx->LogInfo(fails == 0 ? "SealedAudio: self-test passed" : "SealedAudio: self-test failed or skipped (see SealedAudio.log)");
		}
		HANDLE t = ::CreateThread(nullptr, 0, &Milestones, nullptr, 0, nullptr);
		if (t) ::CloseHandle(t);
		return true;
	}

	constexpr D2RL::PluginInfo kInfo {
		.infoSize    = D2RL::PluginInfoSize,
		.abiVersion  = D2RL_PLUGIN_ABI_VERSION,
		.id          = "sealedaudio",
		.name        = "SealedAudio",
		.version     = "1.4.0",
		.author      = "Arendeth",
		.description = "Serves sealed sound archives (*.mtsa) to the game as loose files, for licensed sounds that may not ship as files.",
		.flags       = D2RL::PluginFlags::Client,
	};
}

D2RL_PLUGIN_EXPORT auto D2RLoaderGetPluginInfo() noexcept -> const D2RL::PluginInfo* {
	return &kInfo;
}

D2RL_PLUGIN_EXPORT auto D2RLoaderLoadPlugin(const D2RL::PluginContext* context) noexcept -> bool {
	if (context == nullptr || context->GetApi() == nullptr) {
		return false;
	}
	g_context = context;
	return Startup(context);
}
