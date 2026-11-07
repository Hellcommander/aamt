// Script-extender host for the Sealed Audio core: one source for SKSE (Skyrim SE), SKSEVR (Skyrim VR) and, with
// SEALED_SFSE, SEALED_F4SE or SEALED_NVSE defined, SFSE (Starfield), F4SE (Fallout 4) or NVSE (Fallout New Vegas, 32-bit). It reads SealedAudio.ini beside the dll, points the core at the game's Data
// folder and the extender's log folder, and forwards the extender's milestones (all plugins loaded; data loaded).
// Everything that serves sounds lives in the core (include/sealed_audio.h); this file only wires it.

#include "sealed_audio.h"

#if defined(SEALED_SFSE)
#	include "sfse/PluginAPI.h"
#	include "sfse/sfse_version.h"
#elif defined(SEALED_F4SE)
#	include "f4se/Types.h"
#	include "f4se/PluginAPI.h"
#	include "f4se/f4se_version.h"
#elif defined(SEALED_NVSE)
#	include "nvse/PluginAPI.h"
#else
#	include "skse/PluginAPI.h"
#	include "skse/skse_version.h"
#endif

#include <Windows.h>
#include <ShlObj.h>

#include <cstdio>
#include <string>

namespace
{
	constexpr std::uint32_t kVersion = MAKE_EXE_VERSION(1, 1, 0);

	std::wstring ModuleDir(HMODULE m)
	{
		wchar_t buf[MAX_PATH]{};
		const DWORD n = ::GetModuleFileNameW(m, buf, MAX_PATH);
		std::wstring s(buf, n);
		const auto slash = s.find_last_of(L"\\/");
		return slash == std::wstring::npos ? L"." : s.substr(0, slash);
	}

	HMODULE ThisModule()
	{
		HMODULE m{ nullptr };
		static int anchor = 0;
		::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, reinterpret_cast<LPCWSTR>(&anchor), &m);
		return m;
	}

	// Documents\My Games\<game>\<extender>[\Logs]\SealedAudio.log, where the extender and its plugins log.
	std::wstring LogPath()
	{
		PWSTR docs{ nullptr };
		std::wstring path = L".";
		if (SUCCEEDED(::SHGetKnownFolderPath(FOLDERID_Documents, 0, nullptr, &docs)) && docs) {
			path = docs;
			::CoTaskMemFree(docs);
#if defined(SEALED_SFSE)
			path += L"\\My Games\\Starfield\\SFSE";
			::CreateDirectoryW(path.c_str(), nullptr);
			path += L"\\Logs";
#elif defined(SEALED_F4SE)
			path += L"\\My Games\\Fallout4\\F4SE";
#elif defined(SEALED_NVSE)
			path += L"\\My Games\\FalloutNV\\NVSE";
#else
			path += ::GetModuleHandleW(L"SkyrimVR.exe") ? L"\\My Games\\Skyrim VR\\SKSE" : L"\\My Games\\Skyrim Special Edition\\SKSE";
#endif
			::CreateDirectoryW(path.c_str(), nullptr);
		}
		return path + L"\\SealedAudio.log";
	}

	bool Startup()
	{
		const std::wstring ini = ModuleDir(ThisModule()) + L"\\SealedAudio.ini";
		auto flag = [&](const wchar_t* section, const wchar_t* key, int def) { return (int)::GetPrivateProfileIntW(section, key, def, ini.c_str()); };

		const std::wstring log = LogPath();
		const std::wstring data = ModuleDir(::GetModuleHandleW(nullptr)) + L"\\Data";

		sa_config cfg;
		sa_config_init(&cfg);
		cfg.data_dir = data.c_str();
		cfg.log_file = log.c_str();
		cfg.hook_listings = flag(L"Hooks", L"bListings", 1);
		cfg.hook_attributes = flag(L"Hooks", L"bAttributes", 1);
		cfg.hook_serve = flag(L"Hooks", L"bServe", 1);
		cfg.hook_mappings = flag(L"Hooks", L"bMappings", 1);
		cfg.patch_modules = flag(L"Hooks", L"iPatchModules", 1);
		cfg.log_probes = flag(L"Log", L"bLogSoundProbes", 0);
		cfg.max_probe_lines = flag(L"Log", L"iMaxProbeLines", 200);
		cfg.log_imports = flag(L"Log", L"bLogImports", 0);

		const int hooked = sa_init(&cfg);
		if (flag(L"Debug", L"bCrashLog", 0)) {
			sa_diagnostics(1, 1, 1);
		}
		if (flag(L"Test", L"bSelfTest", 0)) {
			sa_self_test();
		}
		return hooked >= 0;
	}
}

#if defined(SEALED_NVSE)

namespace
{
	// NVSE's message numbers come from a header written down rather than shipped, so each type seen is logged once:
	// a mismatch would show up in the log instead of passing silently.
	void HandleMessage(NVSEMessagingInterface::Message* msg)
	{
		if (!msg) return;
		static bool seen[64]{};
		if (msg->type < 64 && !seen[msg->type]) {
			seen[msg->type] = true;
			char line[96];
			std::snprintf(line, sizeof(line), "NVSE message %u received", msg->type);
			::OutputDebugStringA(line);
		}
		switch (msg->type) {
		case NVSEMessagingInterface::kMessage_PostPostLoad: sa_patch_new_modules(); break;
		case NVSEMessagingInterface::kMessage_DeferredInit: sa_mark_loaded(); break;
		default: break;
		}
	}
}

extern "C"
{
	__declspec(dllexport) bool NVSEPlugin_Query(const NVSEInterface* nvse, PluginInfo* info)
	{
		if (info) {
			info->infoVersion = PluginInfo::kInfoVersion;
			info->name = "SealedAudio";
			info->version = kVersion;
		}
		return nvse && !nvse->isEditor;
	}

	__declspec(dllexport) bool NVSEPlugin_Load(NVSEInterface* nvse)
	{
		if (nvse->isEditor || !Startup()) return false;
		auto* messaging = static_cast<NVSEMessagingInterface*>(nvse->QueryInterface(kInterface_Messaging));
		if (messaging) messaging->RegisterListener(nvse->GetPluginHandle(), "NVSE", HandleMessage);
		return true;
	}
}

#elif defined(SEALED_F4SE)

namespace
{
	void HandleMessage(F4SEMessagingInterface::Message* msg)
	{
		if (!msg) return;
		switch (msg->type) {
		case F4SEMessagingInterface::kMessage_PostLoad: sa_patch_new_modules(); break;
		case F4SEMessagingInterface::kMessage_GameDataReady:
			if (msg->data) sa_mark_loaded();   // data is true once the data handler has finished loading
			break;
		default: break;
		}
	}
}

extern "C"
{
	__declspec(dllexport) F4SEPluginVersionData F4SEPlugin_Version = {
		F4SEPluginVersionData::kVersion, kVersion, "SealedAudio", "Arendeth",
		F4SEPluginVersionData::kAddressIndependence_Signatures, F4SEPluginVersionData::kStructureIndependence_NoStructs, { 0 }, 0, 0, 0
	};

	__declspec(dllexport) bool F4SEPlugin_Load(const F4SEInterface* f4se)
	{
		if (f4se->isEditor || !Startup()) return false;
		auto* messaging = static_cast<F4SEMessagingInterface*>(f4se->QueryInterface(kInterface_Messaging));
		if (messaging) messaging->RegisterListener(f4se->GetPluginHandle(), "F4SE", HandleMessage);
		return true;
	}
}

#elif defined(SEALED_SFSE)

namespace
{
	void HandleMessage(SFSEMessagingInterface::Message* msg)
	{
		if (!msg) return;
		switch (msg->type) {
		case SFSEMessagingInterface::kMessage_PostLoad: sa_patch_new_modules(); break;
		case SFSEMessagingInterface::kMessage_PostDataLoad: sa_mark_loaded(); break;
		default: break;
		}
	}
}

extern "C"
{
	__declspec(dllexport) SFSEPluginVersionData SFSEPlugin_Version = {
		SFSEPluginVersionData::kVersion, kVersion, "SealedAudio", "Arendeth",
		SFSEPluginVersionData::kAddressIndependence_Signatures, SFSEPluginVersionData::kStructureIndependence_NoStructs, { 0 }, 0, 0, 0
	};

	__declspec(dllexport) bool SFSEPlugin_Load(const SFSEInterface* sfse)
	{
		if (!Startup()) return false;
		auto* messaging = static_cast<SFSEMessagingInterface*>(sfse->QueryInterface(kInterface_Messaging));
		if (messaging) messaging->RegisterListener(sfse->GetPluginHandle(), "SFSE", HandleMessage);
		return true;
	}
}

#else

namespace
{
	void HandleMessage(SKSEMessagingInterface::Message* msg)
	{
		if (!msg) return;
		switch (msg->type) {
		case SKSEMessagingInterface::kMessage_PostLoad: sa_patch_new_modules(); break;
		case SKSEMessagingInterface::kMessage_DataLoaded: sa_mark_loaded(); break;
		default: break;
		}
	}
}

extern "C"
{
	__declspec(dllexport) SKSEPluginVersionData SKSEPlugin_Version = {
		SKSEPluginVersionData::kVersion, kVersion, "SealedAudio", "Arendeth", "",
		SKSEPluginVersionData::kVersionIndependentEx_NoStructUse, SKSEPluginVersionData::kVersionIndependent_Signatures, { 0 }, 0
	};

	__declspec(dllexport) bool SKSEPlugin_Query(const SKSEInterface* skse, PluginInfo* info)
	{
		if (info) {
			info->infoVersion = PluginInfo::kInfoVersion;
			info->name = "SealedAudio";
			info->version = kVersion;
		}
		return skse && !skse->isEditor;
	}

	__declspec(dllexport) bool SKSEPlugin_Load(const SKSEInterface* skse)
	{
		if (skse->isEditor || !Startup()) return false;
		auto* messaging = static_cast<SKSEMessagingInterface*>(skse->QueryInterface(kInterface_Messaging));
		if (messaging) messaging->RegisterListener(skse->GetPluginHandle(), "SKSE", HandleMessage);
		return true;
	}
}

#endif
