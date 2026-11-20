// Offline test of the D2R host's file hooks against the way D2R's aio library reads files: open with
// FILE_FLAG_OVERLAPPED, attach the handle to an I/O completion port, issue overlapped reads, collect one completion
// packet per read with GetQueuedCompletionStatusEx. Built by iocp_test.bat with the core sources and the d2r key.
//
//   iocp_test.exe <data dir> <archive dir> <sealed path relative to data> <loose file relative to data>
//
// Exit 0 when every check passes. Before core 1.4.1 the sealed half failed: the stand-in handle could not be attached
// to a port, and an overlapped read on it posted no packet, so a completion-port engine waited for it forever (in D2R
// every sound effect went silent from the first sealed sound on, 2026-11-18).
#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>

#include "sealed_audio.h"

static int g_fails = 0;

static void Check(bool ok, const char* what)
{
	std::printf("%s  %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok) g_fails++;
}

// What aio does for one file: open overlapped, attach to the port, read the first `want` bytes, wait for the packet.
static bool ReadThroughPort(const std::wstring& path, HANDLE port, ULONG_PTR key, char* out, DWORD want, DWORD* got, const char* label)
{
	char line[256];
	HANDLE h = ::CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, nullptr);
	std::snprintf(line, sizeof(line), "%s: opens with FILE_FLAG_OVERLAPPED", label);
	Check(h != INVALID_HANDLE_VALUE, line);
	if (h == INVALID_HANDLE_VALUE) return false;
	HANDLE attached = ::CreateIoCompletionPort(h, port, key, 0);
	std::snprintf(line, sizeof(line), "%s: attaches to the completion port (CreateIoCompletionPort returns that port)", label);
	Check(attached == port, line);
	OVERLAPPED ov{};
	DWORD n = 0;
	const BOOL done = ::ReadFile(h, out, want, &n, &ov);
	const DWORD err = ::GetLastError();
	std::snprintf(line, sizeof(line), "%s: ReadFile succeeds or is pending (err %lu)", label, done ? 0ul : err);
	Check(done || err == ERROR_IO_PENDING, line);
	OVERLAPPED_ENTRY entry{};
	ULONG removed = 0;
	const BOOL packet = ::GetQueuedCompletionStatusEx(port, &entry, 1, &removed, 2000, FALSE);
	std::snprintf(line, sizeof(line), "%s: the port delivers the read's packet within 2 s", label);
	Check(packet && removed == 1 && entry.lpOverlapped == &ov && entry.lpCompletionKey == key, line);
	*got = packet ? entry.dwNumberOfBytesTransferred : 0;
	ULONG removed2 = 0;
	const BOOL extra = ::GetQueuedCompletionStatusEx(port, &entry, 1, &removed2, 100, FALSE);
	std::snprintf(line, sizeof(line), "%s: no second packet for the same read", label);
	Check(!extra, line);
	DWORD viaResult = 0;
	std::snprintf(line, sizeof(line), "%s: GetOverlappedResult agrees on the byte count", label);
	Check(::GetOverlappedResult(h, &ov, &viaResult, FALSE) && viaResult == *got, line);
	std::snprintf(line, sizeof(line), "%s: CancelIoEx afterwards finds nothing to cancel", label);
	Check(!::CancelIoEx(h, nullptr) && ::GetLastError() == ERROR_NOT_FOUND, line);
	::CloseHandle(h);
	return true;
}

int wmain(int argc, wchar_t** argv)
{
	if (argc < 5) {
		std::printf("usage: iocp_test <data dir> <archive dir> <sealed relative path> <loose relative path>\n");
		return 2;
	}
	const std::wstring data = argv[1], archives = argv[2];
	sa_config cfg;
	sa_config_init(&cfg);
	cfg.data_dir = data.c_str();
	cfg.data_folder_name = L"data";
	cfg.archive_dir = archives.c_str();
	const std::wstring logFile = archives + L"\\iocp_test.log";
	cfg.log_file = logFile.c_str();
	cfg.patch_modules = 0;
	cfg.patch_system = 1;       // as in D2R: kernel32's stubs, process-wide
	const int hooked = sa_init(&cfg);
	uint32_t count = 0, entries = 0;
	sa_mounted(&count, &entries);
	std::printf("core %s: %d functions hooked, %u archive(s), %u sealed files\n", sa_version(), hooked, count, entries);
	Check(hooked > 0 && entries > 0, "the core hooks file functions and mounts the archive");

	HANDLE port = ::CreateIoCompletionPort(INVALID_HANDLE_VALUE, nullptr, 0, 1);
	Check(port != nullptr, "a completion port is made");

	char buf[64]{};
	DWORD got = 0;
	// 1) an ordinary file through the same port: must keep working with the hooks in place
	if (ReadThroughPort(data + L"\\" + argv[4], port, 0x11, buf, 16, &got, "loose file")) {
		Check(got == 16, "loose file: 16 bytes arrive");
	}
	// 2) a sealed sound: served from memory, the way the game's loader asks for it
	std::memset(buf, 0, sizeof(buf));
	if (ReadThroughPort(data + L"\\" + argv[3], port, 0x22, buf, 16, &got, "sealed sound")) {
		Check(got == 16 && std::memcmp(buf, "fLaC", 4) == 0, "sealed sound: 16 bytes arrive and start with the FLAC signature");
	}
	::CloseHandle(port);
	std::printf(g_fails ? "%d check(s) FAILED\n" : "all checks passed\n", g_fails);
	return g_fails ? 1 : 0;
}
