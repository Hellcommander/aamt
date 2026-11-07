#pragma once

#include <string>

// Log lines go to a file the host names (sa_config.log_file) and/or to a callback the host gives; neither is required.
// Levels: 0 info, 1 warning, 2 error.
namespace SealedAudio::Log
{
	using Callback = void (*)(int level, const char* message, void* user);

	void Open(const wchar_t* filePath);           // nullptr or empty: no file
	void SetCallback(Callback callback, void* user);
	void Info(const char* fmt, ...);
	void Warn(const char* fmt, ...);
	void Error(const char* fmt, ...);
	// The folder of the log file, or the executable's folder when there is no log file (diagnostic files go there).
	[[nodiscard]] std::wstring Directory();
}
