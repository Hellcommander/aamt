#include "CrashLog.h"

#include "Log.h"

#include <Windows.h>
#include <DbgHelp.h>
#include <Psapi.h>

#include <cstdio>
#include <exception>
#include <cstring>
#include <string>

#pragma comment(lib, "dbghelp.lib")

namespace SealedAudio::CrashLog
{
	namespace
	{
#ifdef _WIN64
		constexpr DWORD kMachine = IMAGE_FILE_MACHINE_AMD64;
#else
		constexpr DWORD kMachine = IMAGE_FILE_MACHINE_I386;
#endif
		LPTOP_LEVEL_EXCEPTION_FILTER g_previous{ nullptr };
		volatile LONG                 g_entered{ 0 };
		volatile LONG                 g_loaded{ 0 };

		std::string ModuleOf(void* address, std::uintptr_t* offset)
		{
			HMODULE m{ nullptr };
			if (!::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, reinterpret_cast<LPCWSTR>(address), &m) || !m) {
				*offset = 0;
				return "?";
			}
			*offset = reinterpret_cast<std::uintptr_t>(address) - reinterpret_cast<std::uintptr_t>(m);
			char path[MAX_PATH]{};
			::GetModuleFileNameA(m, path, MAX_PATH);
			const char* slash = std::strrchr(path, '\\');
			return slash ? slash + 1 : path;
		}

		void Symbol(HANDLE process, DWORD64 address, char* out, std::size_t size)
		{
			alignas(SYMBOL_INFO) char buffer[sizeof(SYMBOL_INFO) + 256]{};
			auto* sym = reinterpret_cast<SYMBOL_INFO*>(buffer);
			sym->SizeOfStruct = sizeof(SYMBOL_INFO);
			sym->MaxNameLen = 255;
			DWORD64 disp = 0;
			if (::SymFromAddr(process, address, &disp, sym)) {
				IMAGEHLP_LINE64 line{};
				line.SizeOfStruct = sizeof(line);
				DWORD lineDisp = 0;
				if (::SymGetLineFromAddr64(process, address, &lineDisp, &line)) {
					std::snprintf(out, size, "%s+0x%llx  (%s:%lu)", sym->Name, disp, line.FileName, line.LineNumber);
				} else {
					std::snprintf(out, size, "%s+0x%llx", sym->Name, disp);
				}
			} else {
				out[0] = '\0';
			}
		}

		LONG WINAPI Filter(EXCEPTION_POINTERS* info)
		{
			if (::InterlockedCompareExchange(&g_entered, 1, 0) != 0) {
				return g_previous ? g_previous(info) : EXCEPTION_CONTINUE_SEARCH;
			}
			const std::wstring path = Log::Directory() + L"\\SealedAudio-crash.log";
			FILE* f = nullptr;
			::_wfopen_s(&f, path.c_str(), L"w");
			if (f && info && info->ExceptionRecord) {
				auto* rec = info->ExceptionRecord;
				std::uintptr_t off = 0;
				const std::string mod = ModuleOf(rec->ExceptionAddress, &off);
				std::fprintf(f, "Unhandled exception 0x%08lX at %s+0x%llx (%p)\n", rec->ExceptionCode, mod.c_str(), (unsigned long long)off, rec->ExceptionAddress);
				if (rec->ExceptionCode == EXCEPTION_ACCESS_VIOLATION && rec->NumberParameters >= 2) {
					std::fprintf(f, "  %s address %p\n", rec->ExceptionInformation[0] == 0 ? "reading" : rec->ExceptionInformation[0] == 1 ? "writing" : "executing", (void*)rec->ExceptionInformation[1]);
				}
				HANDLE process = ::GetCurrentProcess();
				::SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_LOAD_LINES);
				::SymInitialize(process, nullptr, TRUE);
				CONTEXT ctx = *info->ContextRecord;
				STACKFRAME64 frame{};
#ifdef _WIN64
				frame.AddrPC.Offset = ctx.Rip;
				frame.AddrFrame.Offset = ctx.Rbp;
				frame.AddrStack.Offset = ctx.Rsp;
#else
				frame.AddrPC.Offset = ctx.Eip;
				frame.AddrFrame.Offset = ctx.Ebp;
				frame.AddrStack.Offset = ctx.Esp;
#endif
				frame.AddrPC.Mode = AddrModeFlat;
				frame.AddrFrame.Mode = AddrModeFlat;
				frame.AddrStack.Mode = AddrModeFlat;
				std::fprintf(f, "Stack (thread %lu):\n", ::GetCurrentThreadId());
				for (int i = 0; i < 48; i++) {
					if (!::StackWalk64(kMachine, process, ::GetCurrentThread(), &frame, &ctx, nullptr, ::SymFunctionTableAccess64, ::SymGetModuleBase64, nullptr) || frame.AddrPC.Offset == 0) {
						break;
					}
					std::uintptr_t o = 0;
					const std::string m = ModuleOf(reinterpret_cast<void*>(frame.AddrPC.Offset), &o);
					char sym[400]{};
					Symbol(process, frame.AddrPC.Offset, sym, sizeof(sym));
					std::fprintf(f, "  [%2d] %s+0x%llx %s\n", i, m.c_str(), (unsigned long long)o, sym);
				}
				std::fprintf(f, "Modules from the game folder:\n");
				HMODULE mods[512];
				DWORD needed = 0;
				if (::EnumProcessModules(process, mods, sizeof(mods), &needed)) {
					for (DWORD i = 0; i < needed / sizeof(HMODULE) && i < 512; i++) {
						char p[MAX_PATH]{};
						::GetModuleFileNameA(mods[i], p, MAX_PATH);
						char exe[MAX_PATH]{};
						::GetModuleFileNameA(nullptr, exe, MAX_PATH);
						char* slash = std::strrchr(exe, '\\');
						if (slash) slash[1] = 0;
						if (_strnicmp(p, exe, std::strlen(exe)) == 0) {   // everything loaded from the game's folder tree
							std::fprintf(f, "  %p %s\n", (void*)mods[i], p);
						}
					}
				}
				std::fflush(f);
				std::fclose(f);
			} else if (f) {
				std::fclose(f);
			}
			return g_previous ? g_previous(info) : EXCEPTION_CONTINUE_SEARCH;
		}
	}

	void MarkLoaded() { ::InterlockedExchange(&g_loaded, 1); }
	bool ShouldLogExit() { return g_loaded == 0; }

	void WriteStack(const char* why)
	{
		const std::wstring path = Log::Directory() + L"\\SealedAudio-crash.log";
		FILE* f = nullptr;
		::_wfopen_s(&f, path.c_str(), L"a");
		if (!f) {
			return;
		}
		HANDLE process = ::GetCurrentProcess();
		::SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_LOAD_LINES);
		::SymInitialize(process, nullptr, TRUE);
		CONTEXT ctx{};
		::RtlCaptureContext(&ctx);
		STACKFRAME64 frame{};
#ifdef _WIN64
		frame.AddrPC.Offset = ctx.Rip;
		frame.AddrFrame.Offset = ctx.Rbp;
		frame.AddrStack.Offset = ctx.Rsp;
#else
		frame.AddrPC.Offset = ctx.Eip;
		frame.AddrFrame.Offset = ctx.Ebp;
		frame.AddrStack.Offset = ctx.Esp;
#endif
		frame.AddrPC.Mode = AddrModeFlat;
		frame.AddrFrame.Mode = AddrModeFlat;
		frame.AddrStack.Mode = AddrModeFlat;
		std::fprintf(f, "%s (thread %lu):\n", why, ::GetCurrentThreadId());
		for (int i = 0; i < 48; i++) {
			if (!::StackWalk64(kMachine, process, ::GetCurrentThread(), &frame, &ctx, nullptr, ::SymFunctionTableAccess64, ::SymGetModuleBase64, nullptr) || frame.AddrPC.Offset == 0) {
				break;
			}
			std::uintptr_t o = 0;
			const std::string m = ModuleOf(reinterpret_cast<void*>(frame.AddrPC.Offset), &o);
			char sym[400]{};
			Symbol(process, frame.AddrPC.Offset, sym, sizeof(sym));
			std::fprintf(f, "  [%2d] %s+0x%llx %s\n", i, m.c_str(), (unsigned long long)o, sym);
		}
		std::fflush(f);
		std::fclose(f);
	}

	namespace
	{
		volatile LONG g_firstChanceLogged{ 0 };

		// Plain C function body (no objects to unwind), so a structured exception block is allowed here.
		static bool SafeWhat(void* object, char* out, std::size_t size)
		{
			__try {
				auto* e = reinterpret_cast<std::exception*>(object);
				const char* w = e ? e->what() : nullptr;
				if (!w) return false;
				std::size_t i = 0;
				for (; i + 1 < size && w[i]; i++) out[i] = w[i];
				out[i] = 0;
				return true;
			} __except (EXCEPTION_EXECUTE_HANDLER) {
				return false;
			}
		}

		LONG CALLBACK Vectored(EXCEPTION_POINTERS* info)
		{
			if (!info || !info->ExceptionRecord || g_loaded != 0) {
				return EXCEPTION_CONTINUE_SEARCH;
			}
			const DWORD code = info->ExceptionRecord->ExceptionCode;
			if (code != 0xE06D7363 && code != EXCEPTION_ACCESS_VIOLATION && code != EXCEPTION_ILLEGAL_INSTRUCTION && code != EXCEPTION_STACK_OVERFLOW) {
				return EXCEPTION_CONTINUE_SEARCH;
			}
			if (::InterlockedIncrement(&g_firstChanceLogged) > 40) {
				return EXCEPTION_CONTINUE_SEARCH;   // enough
			}
			std::uintptr_t off = 0;
			const std::string mod = ModuleOf(info->ExceptionRecord->ExceptionAddress, &off);
			// a C++ throw: the exception object may be a std::exception; read its message defensively
			std::string what;
			if (code == 0xE06D7363 && info->ExceptionRecord->NumberParameters >= 3) {
				char buf[256]{};
				what = SafeWhat(reinterpret_cast<void*>(info->ExceptionRecord->ExceptionInformation[1]), buf, sizeof(buf)) ? buf : "(not a std::exception)";
			}
			char why[640];
			std::snprintf(why, sizeof(why), "first-chance %s at %s+0x%llx%s%s", code == 0xE06D7363 ? "C++ exception" : code == EXCEPTION_ACCESS_VIOLATION ? "access violation" : "exception",
				mod.c_str(), (unsigned long long)off, what.empty() ? "" : ": ", what.c_str());
			WriteStack(why);
			return EXCEPTION_CONTINUE_SEARCH;
		}
	}

	void WatchFirstChance()
	{
		::AddVectoredExceptionHandler(1, Vectored);
		Log::Info("first-chance exception watcher armed (C++ throws and access violations until the game has loaded)");
	}

	void Install()
	{
		g_previous = ::SetUnhandledExceptionFilter(Filter);
		Log::Info("crash log armed: an unhandled exception writes SealedAudio-crash.log beside this log");
	}
}
