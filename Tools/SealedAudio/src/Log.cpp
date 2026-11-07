#include "Log.h"

#include <Windows.h>

#include <cstdarg>
#include <cstdio>
#include <mutex>
#include <share.h>

namespace SealedAudio::Log
{
	namespace
	{
		std::mutex   g_mutex;
		FILE*        g_file{ nullptr };
		std::wstring g_dir;
		Callback     g_callback{ nullptr };
		void*        g_user{ nullptr };

		void Write(int level, const char* levelName, const char* fmt, va_list args)
		{
			char line[2048];
			std::vsnprintf(line, sizeof(line), fmt, args);
			std::lock_guard lock(g_mutex);
			if (g_file) {
				SYSTEMTIME st{};
				::GetLocalTime(&st);
				std::fprintf(g_file, "[%02u:%02u:%02u.%03u] [%s] %s\n", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, levelName, line);
				std::fflush(g_file);
			}
			if (g_callback) {
				g_callback(level, line, g_user);
			}
		}
	}

	void Open(const wchar_t* filePath)
	{
		std::lock_guard lock(g_mutex);
		if (g_file) {
			std::fclose(g_file);
			g_file = nullptr;
		}
		if (!filePath || !*filePath) {
			return;
		}
		std::wstring path(filePath);
		const auto slash = path.find_last_of(L"\\/");
		if (slash != std::wstring::npos) {
			g_dir = path.substr(0, slash);
			::CreateDirectoryW(g_dir.c_str(), nullptr);   // one level; the usual <game docs>\<extender>\Logs layouts exist already
		}
		g_file = ::_wfsopen(path.c_str(), L"w", _SH_DENYWR);   // others may read it while the game runs
	}

	void SetCallback(Callback callback, void* user)
	{
		std::lock_guard lock(g_mutex);
		g_callback = callback;
		g_user = user;
	}

	std::wstring Directory()
	{
		std::lock_guard lock(g_mutex);
		if (!g_dir.empty()) {
			return g_dir;
		}
		wchar_t buf[MAX_PATH]{};
		::GetModuleFileNameW(nullptr, buf, MAX_PATH);
		std::wstring exe(buf);
		const auto slash = exe.find_last_of(L"\\/");
		return slash == std::wstring::npos ? L"." : exe.substr(0, slash);
	}

	void Info(const char* fmt, ...) { va_list a; va_start(a, fmt); Write(0, "info", fmt, a); va_end(a); }
	void Warn(const char* fmt, ...) { va_list a; va_start(a, fmt); Write(1, "warn", fmt, a); va_end(a); }
	void Error(const char* fmt, ...) { va_list a; va_start(a, fmt); Write(2, "error", fmt, a); va_end(a); }
}
