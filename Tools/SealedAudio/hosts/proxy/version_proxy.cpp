// version.dll proxy host: the Sealed Audio core for any game that has no script extender.
//
// Drop version.dll beside the game's executable with a sealed_audio.ini. Windows loads this dll in place of the system
// version.dll (which nearly every game imports), it forwards every version.dll export to the real one in System32, and
// on a worker thread it starts the core with the settings from the ini. Nothing engine-specific is involved: the core
// patches the Win32 file imports, so sealed sounds appear wherever the game looks for loose files.
//
// sealed_audio.ini (beside this dll, or beside the executable):
//   [SealedAudio]
//   DataDir=Data                 ; the loose-file folder, relative to the executable or absolute
//   DataFolderName=Data          ; the path segment that marks it (what the engine puts in its paths)
//   ArchiveDir=                  ; where *.mtsa live; empty = <DataDir>\SealedAudio
//   LogFile=                     ; empty = <exe folder>\SealedAudio.log
//   PatchModules=1               ; 0 exe only, 1 + plugins under DataDir and extender dlls, 2 every module in the game folder
//   ModulePrefixes=skse;sfse;f4se;nvse;obse
//   SelfTest=0  LogProbes=0  LogImports=0  CrashLog=0
//   StartDelayMs=0               ; wait before hooking, for games that unpack themselves first

#include "sealed_audio.h"

#include <Windows.h>

#include <cstring>
#include <string>

namespace
{
	HMODULE g_real{ nullptr };

	std::wstring Dir(HMODULE m)
	{
		wchar_t buf[MAX_PATH]{};
		const DWORD n = ::GetModuleFileNameW(m, buf, MAX_PATH);
		std::wstring s(buf, n);
		const auto slash = s.find_last_of(L"\\/");
		return slash == std::wstring::npos ? L"." : s.substr(0, slash);
	}

	HMODULE Self()
	{
		HMODULE m{ nullptr };
		static int anchor = 0;
		::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, reinterpret_cast<LPCWSTR>(&anchor), &m);
		return m;
	}

	std::wstring IniPath()
	{
		std::wstring beside = Dir(Self()) + L"\\sealed_audio.ini";
		if (::GetFileAttributesW(beside.c_str()) != INVALID_FILE_ATTRIBUTES) {
			return beside;
		}
		return Dir(::GetModuleHandleW(nullptr)) + L"\\sealed_audio.ini";
	}

	std::wstring Str(const std::wstring& ini, const wchar_t* key, const wchar_t* def)
	{
		wchar_t buf[1024]{};
		::GetPrivateProfileStringW(L"SealedAudio", key, def, buf, 1024, ini.c_str());
		return buf;
	}

	std::wstring Absolute(const std::wstring& exeDir, const std::wstring& path)
	{
		if (path.empty()) {
			return path;
		}
		if (path.size() > 1 && (path[1] == L':' || (path[0] == L'\\' && path[1] == L'\\'))) {
			return path;
		}
		return exeDir + L"\\" + path;
	}

	// A dependency's DllMain runs before the loader has finished resolving the executable's own imports; hooking then
	// would record unresolved thunks as "originals" and be overwritten by the loader. So wait until the executable's
	// CreateFileW import points into a loaded module (kernel32/KernelBase), which happens before its entry point runs.
	bool ImportsResolved()
	{
		auto* base = reinterpret_cast<std::uint8_t*>(::GetModuleHandleW(nullptr));
		auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
		auto* nt = reinterpret_cast<IMAGE_NT_HEADERS64*>(base + dos->e_lfanew);
		const IMAGE_DATA_DIRECTORY& dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
		if (!dir.VirtualAddress) {
			return true;   // nothing to wait for
		}
		auto* desc = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(base + dir.VirtualAddress);
		for (; desc->Name; desc++) {
			if (!desc->OriginalFirstThunk) continue;
			auto* names = reinterpret_cast<IMAGE_THUNK_DATA64*>(base + desc->OriginalFirstThunk);
			auto* thunks = reinterpret_cast<IMAGE_THUNK_DATA64*>(base + desc->FirstThunk);
			for (; names->u1.AddressOfData; names++, thunks++) {
				if (IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal)) continue;
				auto* byName = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(base + names->u1.AddressOfData);
				if (std::strcmp(byName->Name, "CreateFileW") == 0 || std::strcmp(byName->Name, "CreateFileA") == 0 || std::strcmp(byName->Name, "CloseHandle") == 0) {
					HMODULE m{ nullptr };
					return ::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
						reinterpret_cast<LPCWSTR>(thunks->u1.Function), &m) && m != nullptr && m != ::GetModuleHandleW(nullptr);
				}
			}
		}
		return true;
	}

	DWORD WINAPI Start(LPVOID)
	{
		for (int i = 0; i < 500 && !ImportsResolved(); i++) {   // up to 10 s
			::Sleep(20);
		}
		const std::wstring ini = IniPath();
		const std::wstring exeDir = Dir(::GetModuleHandleW(nullptr));
		const int delay = (int)::GetPrivateProfileIntW(L"SealedAudio", L"StartDelayMs", 0, ini.c_str());
		if (delay > 0) {
			::Sleep((DWORD)delay);
		}
		const std::wstring data = Absolute(exeDir, Str(ini, L"DataDir", L"Data"));
		const std::wstring folderName = Str(ini, L"DataFolderName", L"Data");
		const std::wstring archives = Absolute(exeDir, Str(ini, L"ArchiveDir", L""));
		std::wstring log = Absolute(exeDir, Str(ini, L"LogFile", L""));
		if (log.empty()) {
			log = exeDir + L"\\SealedAudio.log";
		}
		const std::wstring prefixes = Str(ini, L"ModulePrefixes", L"skse;sfse;f4se;nvse;obse");

		sa_config cfg;
		sa_config_init(&cfg);
		cfg.data_dir = data.c_str();
		cfg.data_folder_name = folderName.c_str();
		cfg.archive_dir = archives.empty() ? nullptr : archives.c_str();
		cfg.log_file = log.c_str();
		cfg.module_prefixes = prefixes.c_str();
		cfg.patch_modules = (int)::GetPrivateProfileIntW(L"SealedAudio", L"PatchModules", 1, ini.c_str());
		cfg.log_probes = (int)::GetPrivateProfileIntW(L"SealedAudio", L"LogProbes", 0, ini.c_str());
		cfg.log_imports = (int)::GetPrivateProfileIntW(L"SealedAudio", L"LogImports", 0, ini.c_str());
		sa_init(&cfg);
		if (::GetPrivateProfileIntW(L"SealedAudio", L"CrashLog", 0, ini.c_str())) {
			sa_diagnostics(1, 1, 0);
		}
		if (::GetPrivateProfileIntW(L"SealedAudio", L"SelfTest", 0, ini.c_str())) {
			sa_self_test();
		}
		return 0;
	}

	void LoadReal()
	{
		if (g_real) {
			return;
		}
		wchar_t sys[MAX_PATH]{};
		::GetSystemDirectoryW(sys, MAX_PATH);
		std::wstring path = std::wstring(sys) + L"\\version.dll";
		g_real = ::LoadLibraryW(path.c_str());
	}

	template <class F>
	F Real(const char* name)
	{
		LoadReal();
		return g_real ? reinterpret_cast<F>(::GetProcAddress(g_real, name)) : nullptr;
	}
}

// ---- forwarded version.dll exports (the complete public surface) -------------------------------------------------
// Windows' winver.h already declares these names, so the bodies carry a prefix and the linker exports them under the
// real names.
#pragma comment(linker, "/export:GetFileVersionInfoA=Proxy_GetFileVersionInfoA")
#pragma comment(linker, "/export:GetFileVersionInfoW=Proxy_GetFileVersionInfoW")
#pragma comment(linker, "/export:GetFileVersionInfoExA=Proxy_GetFileVersionInfoExA")
#pragma comment(linker, "/export:GetFileVersionInfoExW=Proxy_GetFileVersionInfoExW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeA=Proxy_GetFileVersionInfoSizeA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeW=Proxy_GetFileVersionInfoSizeW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExA=Proxy_GetFileVersionInfoSizeExA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExW=Proxy_GetFileVersionInfoSizeExW")
#pragma comment(linker, "/export:GetFileVersionInfoByHandle=Proxy_GetFileVersionInfoByHandle")
#pragma comment(linker, "/export:VerFindFileA=Proxy_VerFindFileA")
#pragma comment(linker, "/export:VerFindFileW=Proxy_VerFindFileW")
#pragma comment(linker, "/export:VerInstallFileA=Proxy_VerInstallFileA")
#pragma comment(linker, "/export:VerInstallFileW=Proxy_VerInstallFileW")
#pragma comment(linker, "/export:VerLanguageNameA=Proxy_VerLanguageNameA")
#pragma comment(linker, "/export:VerLanguageNameW=Proxy_VerLanguageNameW")
#pragma comment(linker, "/export:VerQueryValueA=Proxy_VerQueryValueA")
#pragma comment(linker, "/export:VerQueryValueW=Proxy_VerQueryValueW")
extern "C"
{
	BOOL WINAPI Proxy_GetFileVersionInfoA(LPCSTR a, DWORD b, DWORD c, LPVOID d) { auto f = Real<BOOL(WINAPI*)(LPCSTR, DWORD, DWORD, LPVOID)>("GetFileVersionInfoA"); return f ? f(a, b, c, d) : FALSE; }
	BOOL WINAPI Proxy_GetFileVersionInfoW(LPCWSTR a, DWORD b, DWORD c, LPVOID d) { auto f = Real<BOOL(WINAPI*)(LPCWSTR, DWORD, DWORD, LPVOID)>("GetFileVersionInfoW"); return f ? f(a, b, c, d) : FALSE; }
	BOOL WINAPI Proxy_GetFileVersionInfoExA(DWORD a, LPCSTR b, DWORD c, DWORD d, LPVOID e) { auto f = Real<BOOL(WINAPI*)(DWORD, LPCSTR, DWORD, DWORD, LPVOID)>("GetFileVersionInfoExA"); return f ? f(a, b, c, d, e) : FALSE; }
	BOOL WINAPI Proxy_GetFileVersionInfoExW(DWORD a, LPCWSTR b, DWORD c, DWORD d, LPVOID e) { auto f = Real<BOOL(WINAPI*)(DWORD, LPCWSTR, DWORD, DWORD, LPVOID)>("GetFileVersionInfoExW"); return f ? f(a, b, c, d, e) : FALSE; }
	DWORD WINAPI Proxy_GetFileVersionInfoSizeA(LPCSTR a, LPDWORD b) { auto f = Real<DWORD(WINAPI*)(LPCSTR, LPDWORD)>("GetFileVersionInfoSizeA"); return f ? f(a, b) : 0; }
	DWORD WINAPI Proxy_GetFileVersionInfoSizeW(LPCWSTR a, LPDWORD b) { auto f = Real<DWORD(WINAPI*)(LPCWSTR, LPDWORD)>("GetFileVersionInfoSizeW"); return f ? f(a, b) : 0; }
	DWORD WINAPI Proxy_GetFileVersionInfoSizeExA(DWORD a, LPCSTR b, LPDWORD c) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCSTR, LPDWORD)>("GetFileVersionInfoSizeExA"); return f ? f(a, b, c) : 0; }
	DWORD WINAPI Proxy_GetFileVersionInfoSizeExW(DWORD a, LPCWSTR b, LPDWORD c) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCWSTR, LPDWORD)>("GetFileVersionInfoSizeExW"); return f ? f(a, b, c) : 0; }
	BOOL WINAPI Proxy_GetFileVersionInfoByHandle(DWORD a, HANDLE b, LPVOID* c, PUINT d) { auto f = Real<BOOL(WINAPI*)(DWORD, HANDLE, LPVOID*, PUINT)>("GetFileVersionInfoByHandle"); return f ? f(a, b, c, d) : FALSE; }
	DWORD WINAPI Proxy_VerFindFileA(DWORD a, LPCSTR b, LPCSTR c, LPCSTR d, LPSTR e, PUINT f2, LPSTR g, PUINT h) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCSTR, LPCSTR, LPCSTR, LPSTR, PUINT, LPSTR, PUINT)>("VerFindFileA"); return f ? f(a, b, c, d, e, f2, g, h) : 0; }
	DWORD WINAPI Proxy_VerFindFileW(DWORD a, LPCWSTR b, LPCWSTR c, LPCWSTR d, LPWSTR e, PUINT f2, LPWSTR g, PUINT h) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCWSTR, LPCWSTR, LPCWSTR, LPWSTR, PUINT, LPWSTR, PUINT)>("VerFindFileW"); return f ? f(a, b, c, d, e, f2, g, h) : 0; }
	DWORD WINAPI Proxy_VerInstallFileA(DWORD a, LPCSTR b, LPCSTR c, LPCSTR d, LPCSTR e, LPCSTR f2, LPSTR g, PUINT h) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCSTR, LPCSTR, LPCSTR, LPCSTR, LPCSTR, LPSTR, PUINT)>("VerInstallFileA"); return f ? f(a, b, c, d, e, f2, g, h) : 0; }
	DWORD WINAPI Proxy_VerInstallFileW(DWORD a, LPCWSTR b, LPCWSTR c, LPCWSTR d, LPCWSTR e, LPCWSTR f2, LPWSTR g, PUINT h) { auto f = Real<DWORD(WINAPI*)(DWORD, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, LPCWSTR, LPWSTR, PUINT)>("VerInstallFileW"); return f ? f(a, b, c, d, e, f2, g, h) : 0; }
	DWORD WINAPI Proxy_VerLanguageNameA(DWORD a, LPSTR b, DWORD c) { auto f = Real<DWORD(WINAPI*)(DWORD, LPSTR, DWORD)>("VerLanguageNameA"); return f ? f(a, b, c) : 0; }
	DWORD WINAPI Proxy_VerLanguageNameW(DWORD a, LPWSTR b, DWORD c) { auto f = Real<DWORD(WINAPI*)(DWORD, LPWSTR, DWORD)>("VerLanguageNameW"); return f ? f(a, b, c) : 0; }
	BOOL WINAPI Proxy_VerQueryValueA(LPCVOID a, LPCSTR b, LPVOID* c, PUINT d) { auto f = Real<BOOL(WINAPI*)(LPCVOID, LPCSTR, LPVOID*, PUINT)>("VerQueryValueA"); return f ? f(a, b, c, d) : FALSE; }
	BOOL WINAPI Proxy_VerQueryValueW(LPCVOID a, LPCWSTR b, LPVOID* c, PUINT d) { auto f = Real<BOOL(WINAPI*)(LPCVOID, LPCWSTR, LPVOID*, PUINT)>("VerQueryValueW"); return f ? f(a, b, c, d) : FALSE; }
}

BOOL WINAPI DllMain(HINSTANCE, DWORD reason, LPVOID)
{
	if (reason == DLL_PROCESS_ATTACH) {
		// nothing heavy under the loader lock: the real version.dll loads on first use, the core starts on its own thread
		HANDLE t = ::CreateThread(nullptr, 0, Start, nullptr, 0, nullptr);
		if (t) ::CloseHandle(t);
	}
	return TRUE;
}
