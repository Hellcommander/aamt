#include "FileHooks.h"

#include "Archives.h"
#include "CrashLog.h"
#include "Log.h"

#include <Psapi.h>

#include <atomic>
#include <set>
#include <cstdio>
#include <cwctype>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <vector>

namespace SealedAudio::Hooks
{
	namespace
	{
		Options g_options;
		std::atomic<int> g_probeLogs{ 0 };
		std::atomic<std::uint64_t> g_served{ 0 }, g_reads{ 0 }, g_probesSeen{ 0 }, g_probesAnswered{ 0 }, g_looseWins{ 0 };

		// ---- virtual files -------------------------------------------------------------------------------------------

		struct VFile
		{
			std::vector<unsigned char> data;
			std::string                path;
			std::mutex                 lock;
			std::int64_t               pos{ 0 };
			std::uint64_t              bytesRead{ 0 };
			bool                       overlapped{ false };
		};

		std::shared_mutex                                         g_filesLock;
		std::unordered_map<HANDLE, std::shared_ptr<VFile>>        g_files;

		std::shared_ptr<VFile> Lookup(HANDLE h)
		{
			if (h == nullptr || h == INVALID_HANDLE_VALUE) {
				return nullptr;
			}
			std::shared_lock lock(g_filesLock);
			auto it = g_files.find(h);
			return it == g_files.end() ? nullptr : it->second;
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

		std::wstring Widen(const char* a)
		{
			if (!a || !*a) {
				return {};
			}
			const int n = ::MultiByteToWideChar(CP_ACP, 0, a, -1, nullptr, 0);
			std::wstring w((std::size_t)(n > 0 ? n - 1 : 0), L'\0');
			if (n > 1) {
				::MultiByteToWideChar(CP_ACP, 0, a, -1, w.data(), n);
			}
			return w;
		}

		// The part of a path after its data folder ("Sound\fx\x.wav"), or empty when the path has no such folder. The
		// folder name (Data by default) is matched as a whole path segment anywhere, case-insensitively, so relative
		// ("Data\Sound\...") and absolute paths both work.
		std::string RelativeToData(const wchar_t* path)
		{
			if (!path) {
				return {};
			}
			const std::wstring& name = g_options.dataFolderName;
			const std::size_t n = name.size();
			if (n == 0) {
				return {};
			}
			std::wstring p(path);
			for (std::size_t i = 0; i + n + 1 <= p.size(); i++) {
				const bool atStart = i == 0 || p[i - 1] == L'\\' || p[i - 1] == L'/';
				if (!atStart || (p[i + n] != L'\\' && p[i + n] != L'/')) {
					continue;
				}
				bool same = true;
				for (std::size_t k = 0; k < n && same; k++) {
					same = ::towlower(p[i + k]) == ::towlower(name[k]);
				}
				if (same) {
					return Narrow(p.substr(i + n + 1));
				}
			}
			return {};
		}

		bool IsSoundish(const std::string& rel)
		{
			std::string s = rel;
			for (char& c : s) {
				if (c == '/') c = '\\';
				else if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
			}
			return s.rfind("sound\\", 0) == 0 || s.rfind("music\\", 0) == 0;
		}

		void Probe(const char* api, const std::string& rel, const char* result)
		{
			g_probesSeen++;
			if (g_options.logProbes && g_probeLogs.fetch_add(1) < g_options.maxProbeLogs) {
				Log::Info("probe %s Data\\%s -> %s", api, rel.c_str(), result);
			}
		}

		// ---- originals -----------------------------------------------------------------------------------------------

		using CreateFileW_t = HANDLE(WINAPI*)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
		using CreateFileA_t = HANDLE(WINAPI*)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
		using CreateFile2_t = HANDLE(WINAPI*)(LPCWSTR, DWORD, DWORD, DWORD, LPCREATEFILE2_EXTENDED_PARAMETERS);
		using CreateFileMappingA_t = HANDLE(WINAPI*)(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCSTR);
		using CreateFileMappingW_t = HANDLE(WINAPI*)(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCWSTR);
		using ReadFile_t = BOOL(WINAPI*)(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);
		using ReadFileEx_t = BOOL(WINAPI*)(HANDLE, LPVOID, DWORD, LPOVERLAPPED, LPOVERLAPPED_COMPLETION_ROUTINE);
		using SetFilePointer_t = DWORD(WINAPI*)(HANDLE, LONG, PLONG, DWORD);
		using SetFilePointerEx_t = BOOL(WINAPI*)(HANDLE, LARGE_INTEGER, PLARGE_INTEGER, DWORD);
		using GetFileSize_t = DWORD(WINAPI*)(HANDLE, LPDWORD);
		using GetFileSizeEx_t = BOOL(WINAPI*)(HANDLE, PLARGE_INTEGER);
		using GetFileType_t = DWORD(WINAPI*)(HANDLE);
		using GetFileInformationByHandle_t = BOOL(WINAPI*)(HANDLE, LPBY_HANDLE_FILE_INFORMATION);
		using GetFileInformationByHandleEx_t = BOOL(WINAPI*)(HANDLE, FILE_INFO_BY_HANDLE_CLASS, LPVOID, DWORD);
		using CloseHandle_t = BOOL(WINAPI*)(HANDLE);
		using GetFileAttributesW_t = DWORD(WINAPI*)(LPCWSTR);
		using GetFileAttributesA_t = DWORD(WINAPI*)(LPCSTR);
		using GetFileAttributesExW_t = BOOL(WINAPI*)(LPCWSTR, GET_FILEEX_INFO_LEVELS, LPVOID);
		using GetFileAttributesExA_t = BOOL(WINAPI*)(LPCSTR, GET_FILEEX_INFO_LEVELS, LPVOID);
		using FindFirstFileA_t = HANDLE(WINAPI*)(LPCSTR, LPWIN32_FIND_DATAA);
		using FindFirstFileExA_t = HANDLE(WINAPI*)(LPCSTR, FINDEX_INFO_LEVELS, LPVOID, FINDEX_SEARCH_OPS, LPVOID, DWORD);
		using FindNextFileA_t = BOOL(WINAPI*)(HANDLE, LPWIN32_FIND_DATAA);
		using FindNextFileW_t = BOOL(WINAPI*)(HANDLE, LPWIN32_FIND_DATAW);
		using FindClose_t = BOOL(WINAPI*)(HANDLE);
		using ExitProcess_t = void(WINAPI*)(UINT);
		using TerminateProcess_t = BOOL(WINAPI*)(HANDLE, UINT);
		using FindFirstFileW_t = HANDLE(WINAPI*)(LPCWSTR, LPWIN32_FIND_DATAW);
		using FindFirstFileExW_t = HANDLE(WINAPI*)(LPCWSTR, FINDEX_INFO_LEVELS, LPVOID, FINDEX_SEARCH_OPS, LPVOID, DWORD);

		CreateFileW_t                  o_CreateFileW{ nullptr };
		CreateFileA_t                  o_CreateFileA{ nullptr };
		CreateFile2_t                  o_CreateFile2{ nullptr };
		CreateFileMappingA_t           o_CreateFileMappingA{ nullptr };
		CreateFileMappingW_t           o_CreateFileMappingW{ nullptr };
		ReadFile_t                     o_ReadFile{ nullptr };
		ReadFileEx_t                   o_ReadFileEx{ nullptr };
		SetFilePointer_t               o_SetFilePointer{ nullptr };
		SetFilePointerEx_t             o_SetFilePointerEx{ nullptr };
		GetFileSize_t                  o_GetFileSize{ nullptr };
		GetFileSizeEx_t                o_GetFileSizeEx{ nullptr };
		GetFileType_t                  o_GetFileType{ nullptr };
		GetFileInformationByHandle_t   o_GetFileInformationByHandle{ nullptr };
		GetFileInformationByHandleEx_t o_GetFileInformationByHandleEx{ nullptr };
		CloseHandle_t                  o_CloseHandle{ nullptr };
		GetFileAttributesW_t           o_GetFileAttributesW{ nullptr };
		GetFileAttributesA_t           o_GetFileAttributesA{ nullptr };
		GetFileAttributesExW_t         o_GetFileAttributesExW{ nullptr };
		GetFileAttributesExA_t         o_GetFileAttributesExA{ nullptr };
		FindFirstFileA_t               o_FindFirstFileA{ nullptr };
		FindFirstFileExA_t             o_FindFirstFileExA{ nullptr };
		FindNextFileA_t                o_FindNextFileA{ nullptr };
		FindNextFileW_t                o_FindNextFileW{ nullptr };
		FindClose_t                    o_FindClose{ nullptr };
		ExitProcess_t                  o_ExitProcess{ nullptr };
		TerminateProcess_t             o_TerminateProcess{ nullptr };
		FindFirstFileW_t               o_FindFirstFileW{ nullptr };
		FindFirstFileExW_t             o_FindFirstFileExW{ nullptr };

		// ---- the hooks -----------------------------------------------------------------------------------------------

		template <class Real>
		HANDLE OpenSealedWith(const wchar_t* path, DWORD access, DWORD disposition, DWORD flags, Real real)
		{
			const std::string rel = RelativeToData(path);
			const bool readOnly = disposition == OPEN_EXISTING && !(access & (GENERIC_WRITE | FILE_WRITE_DATA | FILE_APPEND_DATA | DELETE));
			const bool soundish = !rel.empty() && IsSoundish(rel);
			if (rel.empty() || !readOnly || !g_options.serve || !Archives::Has(rel)) {
				HANDLE h = real();
				if (soundish) {
					const DWORD err = ::GetLastError();
					Probe("CreateFileW", rel, h == INVALID_HANDLE_VALUE ? (err == ERROR_FILE_NOT_FOUND || err == ERROR_PATH_NOT_FOUND ? "not found" : "failed") : "loose file");
					::SetLastError(err);
				}
				return h;
			}
			// a sealed path: the real file first (a loose file wins), then the archive
			HANDLE h = real();
			if (h != INVALID_HANDLE_VALUE) {
				g_looseWins++;
				Probe("CreateFileW", rel, "loose file shadows the sealed one");
				return h;
			}
			const DWORD err = ::GetLastError();
			if (err != ERROR_FILE_NOT_FOUND && err != ERROR_PATH_NOT_FOUND) {
				Probe("CreateFileW", rel, "open failed for another reason; not served");
				::SetLastError(err);
				return INVALID_HANDLE_VALUE;
			}
			auto vf = std::make_shared<VFile>();
			vf->data = Archives::Read(rel);
			vf->path = rel;
			vf->overlapped = (flags & FILE_FLAG_OVERLAPPED) != 0;
			// A real kernel object stands in for the file: unique, closeable by CloseHandle, harmless to any API we do not
			// answer ourselves, and signalled, so an overlapped wait on it returns at once.
			HANDLE fake = ::CreateEventW(nullptr, TRUE, TRUE, nullptr);
			if (!fake) {
				::SetLastError(ERROR_FILE_NOT_FOUND);
				return INVALID_HANDLE_VALUE;
			}
			{
				std::unique_lock lock(g_filesLock);
				g_files[fake] = vf;
			}
			g_served++;
			Probe("CreateFileW", rel, vf->overlapped ? "served from a sealed archive (overlapped)" : "served from a sealed archive");
			::SetLastError(ERROR_SUCCESS);
			return fake;
		}

		HANDLE OpenSealed(const wchar_t* path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disposition, DWORD flags, HANDLE tmpl, CreateFileW_t real)
		{
			return OpenSealedWith(path, access, disposition, flags, [&]() { return real(path, access, share, sa, disposition, flags, tmpl); });
		}

		HANDLE WINAPI h_CreateFileW(LPCWSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disposition, DWORD flags, HANDLE tmpl)
		{
			return OpenSealed(path, access, share, sa, disposition, flags, tmpl, o_CreateFileW);
		}

		// Some engines (Starfield) open files with CreateFile2; the extended parameters carry the flags.
		HANDLE WINAPI h_CreateFile2(LPCWSTR path, DWORD access, DWORD share, DWORD disposition, LPCREATEFILE2_EXTENDED_PARAMETERS params)
		{
			const DWORD flags = params ? (params->dwFileFlags | params->dwFileAttributes) : 0;
			return OpenSealedWith(path, access, disposition, flags, [&]() { return o_CreateFile2(path, access, share, disposition, params); });
		}

		// A mapping of a virtual file: an anonymous, pagefile-backed section filled with the unsealed bytes. Read-only
		// views of it behave like views of the file; the engine never sees a difference.
		HANDLE MapVirtual(const std::shared_ptr<VFile>& vf, LPSECURITY_ATTRIBUTES sa, DWORD protect, DWORD maxHigh, DWORD maxLow)
		{
			std::uint64_t size = ((std::uint64_t)maxHigh << 32) | maxLow;
			if (size == 0 || size > vf->data.size()) {
				size = vf->data.size();
			}
			if (size == 0) {
				::SetLastError(ERROR_FILE_INVALID);
				return nullptr;
			}
			const DWORD create = (protect == PAGE_READONLY || protect == PAGE_WRITECOPY || protect == PAGE_READWRITE) ? PAGE_READWRITE : protect;
			HANDLE map = (o_CreateFileMappingW ? o_CreateFileMappingW : ::CreateFileMappingW)(INVALID_HANDLE_VALUE, sa, create, (DWORD)(size >> 32), (DWORD)(size & 0xFFFFFFFFull), nullptr);
			if (!map) {
				return nullptr;
			}
			void* view = ::MapViewOfFile(map, FILE_MAP_WRITE, 0, 0, (SIZE_T)size);
			if (!view) {
				::CloseHandle(map);
				::SetLastError(ERROR_NOT_ENOUGH_MEMORY);
				return nullptr;
			}
			std::memcpy(view, vf->data.data(), (std::size_t)size);
			::UnmapViewOfFile(view);
			Probe("CreateFileMapping", vf->path, "mapped from a sealed archive");
			::SetLastError(ERROR_SUCCESS);
			return map;
		}

		HANDLE WINAPI h_CreateFileMappingA(HANDLE h, LPSECURITY_ATTRIBUTES sa, DWORD protect, DWORD maxHigh, DWORD maxLow, LPCSTR name)
		{
			auto vf = g_options.mappings ? Lookup(h) : nullptr;
			if (!vf) {
				return o_CreateFileMappingA(h, sa, protect, maxHigh, maxLow, name);
			}
			return MapVirtual(vf, sa, protect, maxHigh, maxLow);
		}

		HANDLE WINAPI h_CreateFileMappingW(HANDLE h, LPSECURITY_ATTRIBUTES sa, DWORD protect, DWORD maxHigh, DWORD maxLow, LPCWSTR name)
		{
			auto vf = g_options.mappings ? Lookup(h) : nullptr;
			if (!vf) {
				return o_CreateFileMappingW(h, sa, protect, maxHigh, maxLow, name);
			}
			return MapVirtual(vf, sa, protect, maxHigh, maxLow);
		}

		HANDLE WINAPI h_CreateFileA(LPCSTR path, DWORD access, DWORD share, LPSECURITY_ATTRIBUTES sa, DWORD disposition, DWORD flags, HANDLE tmpl)
		{
			const std::string rel = RelativeToData(Widen(path).c_str());
			if (rel.empty() || !Archives::Has(rel)) {
				return o_CreateFileA(path, access, share, sa, disposition, flags, tmpl);
			}
			// route through the wide path so the sealed logic lives in one place
			const std::wstring w = Widen(path);
			return OpenSealed(w.c_str(), access, share, sa, disposition, flags, tmpl, o_CreateFileW ? o_CreateFileW : ::CreateFileW);
		}

		BOOL WINAPI h_ReadFile(HANDLE h, LPVOID buffer, DWORD toRead, LPDWORD read, LPOVERLAPPED ov)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_ReadFile(h, buffer, toRead, read, ov);
			}
			std::lock_guard lock(vf->lock);
			std::int64_t at = vf->pos;
			if (ov) {
				at = (std::int64_t)(((std::uint64_t)ov->OffsetHigh << 32) | ov->Offset);
			}
			const std::int64_t size = (std::int64_t)vf->data.size();
			DWORD n = 0;
			if (at < size) {
				n = (DWORD)std::min<std::int64_t>(toRead, size - at);
				if (n && buffer) {
					std::memcpy(buffer, vf->data.data() + at, n);
				}
			}
			if (!ov) {
				vf->pos = at + n;
			}
			g_reads++;
			vf->bytesRead += n;
			if (read) {
				*read = n;
			}
			if (ov) {
				ov->Internal = 0;        // STATUS_SUCCESS: GetOverlappedResult reads these
				ov->InternalHigh = n;
				if (ov->hEvent) {
					::SetEvent(ov->hEvent);
				}
				if (n == 0 && toRead > 0) {
					::SetLastError(ERROR_HANDLE_EOF);
					return FALSE;
				}
			}
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		struct ApcCompletion
		{
			LPOVERLAPPED_COMPLETION_ROUTINE routine;
			DWORD                           bytes;
			LPOVERLAPPED                    ov;
		};

		void NTAPI ApcThunk(ULONG_PTR p)
		{
			auto* c = reinterpret_cast<ApcCompletion*>(p);
			c->routine(0, c->bytes, c->ov);
			delete c;
		}

		BOOL WINAPI h_ReadFileEx(HANDLE h, LPVOID buffer, DWORD toRead, LPOVERLAPPED ov, LPOVERLAPPED_COMPLETION_ROUTINE routine)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_ReadFileEx(h, buffer, toRead, ov, routine);
			}
			DWORD n = 0;
			{
				std::lock_guard lock(vf->lock);
				const std::int64_t at = ov ? (std::int64_t)(((std::uint64_t)ov->OffsetHigh << 32) | ov->Offset) : vf->pos;
				const std::int64_t size = (std::int64_t)vf->data.size();
				if (at < size) {
					n = (DWORD)std::min<std::int64_t>(toRead, size - at);
					if (n && buffer) {
						std::memcpy(buffer, vf->data.data() + at, n);
					}
				}
				if (!ov) {
					vf->pos = at + n;
				}
			}
			g_reads++;
			if (ov) {
				ov->Internal = 0;
				ov->InternalHigh = n;
			}
			if (routine) {
				// the completion runs as an APC on this thread, the way the kernel would deliver it
				::QueueUserAPC(ApcThunk, ::GetCurrentThread(), (ULONG_PTR) new ApcCompletion{ routine, n, ov });
			}
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		BOOL WINAPI h_SetFilePointerEx(HANDLE h, LARGE_INTEGER distance, PLARGE_INTEGER newPos, DWORD method)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_SetFilePointerEx(h, distance, newPos, method);
			}
			std::lock_guard lock(vf->lock);
			std::int64_t base = method == FILE_BEGIN ? 0 : method == FILE_CURRENT ? vf->pos : (std::int64_t)vf->data.size();
			const std::int64_t target = base + distance.QuadPart;
			if (target < 0) {
				::SetLastError(ERROR_NEGATIVE_SEEK);
				return FALSE;
			}
			vf->pos = target;
			if (newPos) {
				newPos->QuadPart = target;
			}
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		DWORD WINAPI h_SetFilePointer(HANDLE h, LONG distance, PLONG distanceHigh, DWORD method)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_SetFilePointer(h, distance, distanceHigh, method);
			}
			LARGE_INTEGER d;
			d.LowPart = (DWORD)distance;
			d.HighPart = distanceHigh ? *distanceHigh : (distance < 0 ? -1 : 0);
			LARGE_INTEGER np{};
			if (!h_SetFilePointerEx(h, d, &np, method)) {
				return INVALID_SET_FILE_POINTER;
			}
			if (distanceHigh) {
				*distanceHigh = np.HighPart;
			}
			::SetLastError(ERROR_SUCCESS);
			return np.LowPart;
		}

		BOOL WINAPI h_GetFileSizeEx(HANDLE h, PLARGE_INTEGER size)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_GetFileSizeEx(h, size);
			}
			if (size) {
				size->QuadPart = (LONGLONG)vf->data.size();
			}
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		DWORD WINAPI h_GetFileSize(HANDLE h, LPDWORD high)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_GetFileSize(h, high);
			}
			if (high) {
				*high = (DWORD)((std::uint64_t)vf->data.size() >> 32);
			}
			::SetLastError(ERROR_SUCCESS);
			return (DWORD)(vf->data.size() & 0xFFFFFFFFull);
		}

		DWORD WINAPI h_GetFileType(HANDLE h)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_GetFileType(h);
			}
			::SetLastError(ERROR_SUCCESS);
			return FILE_TYPE_DISK;
		}

		void FillTimes(FILETIME& ft)
		{
			::GetSystemTimeAsFileTime(&ft);
		}

		BOOL WINAPI h_GetFileInformationByHandle(HANDLE h, LPBY_HANDLE_FILE_INFORMATION info)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_GetFileInformationByHandle(h, info);
			}
			if (info) {
				std::memset(info, 0, sizeof(*info));
				info->dwFileAttributes = FILE_ATTRIBUTE_NORMAL | FILE_ATTRIBUTE_READONLY;
				FillTimes(info->ftCreationTime);
				info->ftLastAccessTime = info->ftLastWriteTime = info->ftCreationTime;
				info->nFileSizeLow = (DWORD)(vf->data.size() & 0xFFFFFFFFull);
				info->nFileSizeHigh = (DWORD)((std::uint64_t)vf->data.size() >> 32);
				info->nNumberOfLinks = 1;
				info->nFileIndexLow = (DWORD)(std::uintptr_t)h;
			}
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		BOOL WINAPI h_GetFileInformationByHandleEx(HANDLE h, FILE_INFO_BY_HANDLE_CLASS cls, LPVOID info, DWORD size)
		{
			auto vf = Lookup(h);
			if (!vf) {
				return o_GetFileInformationByHandleEx(h, cls, info, size);
			}
			if (cls == FileStandardInfo && info && size >= sizeof(FILE_STANDARD_INFO)) {
				auto* s = static_cast<FILE_STANDARD_INFO*>(info);
				std::memset(s, 0, sizeof(*s));
				s->AllocationSize.QuadPart = s->EndOfFile.QuadPart = (LONGLONG)vf->data.size();
				s->NumberOfLinks = 1;
				::SetLastError(ERROR_SUCCESS);
				return TRUE;
			}
			if (cls == FileBasicInfo && info && size >= sizeof(FILE_BASIC_INFO)) {
				auto* b = static_cast<FILE_BASIC_INFO*>(info);
				std::memset(b, 0, sizeof(*b));
				FILETIME ft;
				FillTimes(ft);
				b->CreationTime.LowPart = b->LastAccessTime.LowPart = b->LastWriteTime.LowPart = b->ChangeTime.LowPart = ft.dwLowDateTime;
				b->CreationTime.HighPart = b->LastAccessTime.HighPart = b->LastWriteTime.HighPart = b->ChangeTime.HighPart = (LONG)ft.dwHighDateTime;
				b->FileAttributes = FILE_ATTRIBUTE_NORMAL | FILE_ATTRIBUTE_READONLY;
				::SetLastError(ERROR_SUCCESS);
				return TRUE;
			}
			::SetLastError(ERROR_INVALID_PARAMETER);
			return FALSE;
		}

		BOOL WINAPI h_CloseHandle(HANDLE h)
		{
			std::shared_ptr<VFile> vf;
			{
				std::unique_lock lock(g_filesLock);
				auto it = g_files.find(h);
				if (it != g_files.end()) {
					vf = it->second;
					g_files.erase(it);
				}
			}
			if (vf) {
				char what[96];
				std::snprintf(what, sizeof(what), "closed after the engine read %llu of %zu bytes", (unsigned long long)vf->bytesRead, vf->data.size());
				Probe("CloseHandle", vf->path, what);
			}
			return o_CloseHandle(h);
		}

		DWORD WINAPI h_GetFileAttributesW(LPCWSTR path)
		{
			const DWORD attrs = o_GetFileAttributesW(path);
			const std::string rel = RelativeToData(path);
			if (rel.empty()) {
				return attrs;
			}
			const DWORD err = ::GetLastError();
			if (attrs == INVALID_FILE_ATTRIBUTES && g_options.attributes && Archives::Has(rel)) {
				g_probesAnswered++;
				Probe("GetFileAttributesW", rel, "answered: sealed");
				::SetLastError(ERROR_SUCCESS);
				return FILE_ATTRIBUTE_NORMAL | FILE_ATTRIBUTE_READONLY;
			}
			if (attrs == INVALID_FILE_ATTRIBUTES && g_options.attributes && Archives::HasDirectory(rel)) {
				g_probesAnswered++;
				Probe("GetFileAttributesW", rel, "answered: folder of sealed sounds");
				::SetLastError(ERROR_SUCCESS);
				return FILE_ATTRIBUTE_DIRECTORY;
			}
			if (IsSoundish(rel)) {
				Probe("GetFileAttributesW", rel, attrs == INVALID_FILE_ATTRIBUTES ? "not found" : "loose file");
			}
			::SetLastError(err);
			return attrs;
		}

		DWORD WINAPI h_GetFileAttributesA(LPCSTR path)
		{
			const std::wstring w = Widen(path);
			const std::string rel = RelativeToData(w.c_str());
			if (rel.empty() || !Archives::Has(rel)) {
				return o_GetFileAttributesA(path);
			}
			return h_GetFileAttributesW(w.c_str());
		}

		BOOL WINAPI h_GetFileAttributesExW(LPCWSTR path, GET_FILEEX_INFO_LEVELS level, LPVOID info)
		{
			const BOOL ok = o_GetFileAttributesExW(path, level, info);
			const std::string rel = RelativeToData(path);
			if (rel.empty()) {
				return ok;
			}
			const DWORD err = ::GetLastError();
			std::uint64_t size = 0;
			if (!ok && level == GetFileExInfoStandard && info && g_options.attributes && Archives::SizeOf(rel, size)) {
				auto* d = static_cast<WIN32_FILE_ATTRIBUTE_DATA*>(info);
				std::memset(d, 0, sizeof(*d));
				d->dwFileAttributes = FILE_ATTRIBUTE_NORMAL | FILE_ATTRIBUTE_READONLY;
				FillTimes(d->ftCreationTime);
				d->ftLastAccessTime = d->ftLastWriteTime = d->ftCreationTime;
				d->nFileSizeLow = (DWORD)(size & 0xFFFFFFFFull);
				d->nFileSizeHigh = (DWORD)(size >> 32);
				g_probesAnswered++;
				Probe("GetFileAttributesExW", rel, "answered: sealed");
				::SetLastError(ERROR_SUCCESS);
				return TRUE;
			}
			if (!ok && level == GetFileExInfoStandard && info && g_options.attributes && Archives::HasDirectory(rel)) {
				auto* d = static_cast<WIN32_FILE_ATTRIBUTE_DATA*>(info);
				std::memset(d, 0, sizeof(*d));
				d->dwFileAttributes = FILE_ATTRIBUTE_DIRECTORY;
				FillTimes(d->ftCreationTime);
				d->ftLastAccessTime = d->ftLastWriteTime = d->ftCreationTime;
				g_probesAnswered++;
				Probe("GetFileAttributesExW", rel, "answered: folder of sealed sounds");
				::SetLastError(ERROR_SUCCESS);
				return TRUE;
			}
			if (IsSoundish(rel)) {
				Probe("GetFileAttributesExW", rel, ok ? "loose file" : "not found");
			}
			::SetLastError(err);
			return ok;
		}

		BOOL WINAPI h_GetFileAttributesExA(LPCSTR path, GET_FILEEX_INFO_LEVELS level, LPVOID info)
		{
			const std::wstring w = Widen(path);
			const std::string rel = RelativeToData(w.c_str());
			if (rel.empty()) {
				return o_GetFileAttributesExA(path, level, info);
			}
			// the wide hook answers sealed paths and logs sound probes; the structure is the same for A and W
			return h_GetFileAttributesExW(w.c_str(), level, info);
		}

		// ---- directory listings ------------------------------------------------------------------------------------
		//
		// The engine indexes loose files by listing Data\Sound (and every folder below) once, so sealed sounds must
		// appear in those listings. A listing of a folder the archives cover is a virtual one: the real folder's entries
		// first (when it exists), then the sealed subfolders and files that have no real counterpart, filtered by the
		// search pattern. The handle is a real event object, as for virtual files, so FindClose and foreign APIs behave.

		struct VFind
		{
			std::vector<WIN32_FIND_DATAW> entries;
			std::size_t                   next{ 0 };
		};

		std::unordered_map<HANDLE, std::shared_ptr<VFind>> g_finds;   // under g_filesLock

		bool WildMatch(const wchar_t* pat, const wchar_t* s)
		{
			if (!*pat) return !*s;
			if (*pat == L'*') return WildMatch(pat + 1, s) || (*s && WildMatch(pat, s + 1));
			if (!*s) return false;
			if (*pat == L'?' || ::towlower(*pat) == ::towlower(*s)) return WildMatch(pat + 1, s + 1);
			return false;
		}

		bool MatchesPattern(const std::wstring& pattern, const wchar_t* name)
		{
			if (pattern == L"*" || pattern == L"*.*") return true;
			return WildMatch(pattern.c_str(), name);
		}

		void ToAnsi(const WIN32_FIND_DATAW& w, WIN32_FIND_DATAA& a)
		{
			std::memset(&a, 0, sizeof(a));
			a.dwFileAttributes = w.dwFileAttributes;
			a.ftCreationTime = w.ftCreationTime;
			a.ftLastAccessTime = w.ftLastAccessTime;
			a.ftLastWriteTime = w.ftLastWriteTime;
			a.nFileSizeHigh = w.nFileSizeHigh;
			a.nFileSizeLow = w.nFileSizeLow;
			::WideCharToMultiByte(CP_ACP, 0, w.cFileName, -1, a.cFileName, MAX_PATH, nullptr, nullptr);
			::WideCharToMultiByte(CP_ACP, 0, w.cAlternateFileName, -1, a.cAlternateFileName, 14, nullptr, nullptr);
		}

		// Builds the merged listing for "<folder>\<pattern>" when the sealed tree covers <folder>; nullptr otherwise.
		std::shared_ptr<VFind> BuildListing(const std::wstring& search, const std::string& relSearch)
		{
			if (!g_options.listings) {
				return nullptr;
			}
			const std::size_t cut = relSearch.find_last_of("\\/");
			const std::string relFolder = cut == std::string::npos ? std::string() : relSearch.substr(0, cut);
			const std::string patternA = cut == std::string::npos ? relSearch : relSearch.substr(cut + 1);
			if (patternA.empty() || patternA.find('*') == std::string::npos && patternA.find('?') == std::string::npos) {
				return nullptr;   // a single name: CreateFile/GetFileAttributes answer those
			}
			const auto children = Archives::Children(relFolder);
			if (children.empty()) {
				return nullptr;
			}
			auto vf = std::make_shared<VFind>();
			std::vector<std::wstring> seen;
			// the real folder's entries, if it exists
			WIN32_FIND_DATAW fd{};
			HANDLE real = o_FindFirstFileW(search.c_str(), &fd);
			if (real != INVALID_HANDLE_VALUE) {
				do {
					vf->entries.push_back(fd);
					seen.push_back(fd.cFileName);
				} while (::FindNextFileW(real, &fd));
				::FindClose(real);
			} else {
				const std::size_t wcut = search.find_last_of(L"\\/");
				const std::wstring pattern = wcut == std::wstring::npos ? search : search.substr(wcut + 1);
				for (const wchar_t* dot : { L".", L".." }) {
					if (MatchesPattern(pattern, dot)) {
						WIN32_FIND_DATAW d{};
						d.dwFileAttributes = FILE_ATTRIBUTE_DIRECTORY;
						::GetSystemTimeAsFileTime(&d.ftCreationTime);
						d.ftLastAccessTime = d.ftLastWriteTime = d.ftCreationTime;
						::wcscpy_s(d.cFileName, dot);
						vf->entries.push_back(d);
					}
				}
			}
			const std::size_t wcut = search.find_last_of(L"\\/");
			const std::wstring pattern = wcut == std::wstring::npos ? search : search.substr(wcut + 1);
			int added = 0;
			for (const Archives::Child& c : children) {
				const int n = ::MultiByteToWideChar(CP_UTF8, 0, c.name.c_str(), -1, nullptr, 0);
				std::wstring wname((std::size_t)(n > 0 ? n - 1 : 0), L'\0');
				if (n > 1) ::MultiByteToWideChar(CP_UTF8, 0, c.name.c_str(), -1, wname.data(), n);
				bool dup = false;
				for (const std::wstring& s : seen) {
					if (::_wcsicmp(s.c_str(), wname.c_str()) == 0) { dup = true; break; }
				}
				if (dup || !MatchesPattern(pattern, wname.c_str())) {
					continue;
				}
				WIN32_FIND_DATAW d{};
				d.dwFileAttributes = c.isDir ? FILE_ATTRIBUTE_DIRECTORY : (FILE_ATTRIBUTE_NORMAL | FILE_ATTRIBUTE_READONLY);
				::GetSystemTimeAsFileTime(&d.ftCreationTime);
				d.ftLastAccessTime = d.ftLastWriteTime = d.ftCreationTime;
				d.nFileSizeLow = (DWORD)(c.size & 0xFFFFFFFFull);
				d.nFileSizeHigh = (DWORD)(c.size >> 32);
				::wcsncpy_s(d.cFileName, wname.c_str(), MAX_PATH - 1);
				vf->entries.push_back(d);
				added++;
			}
			if (added == 0 && real == INVALID_HANDLE_VALUE) {
				return nullptr;
			}
			Probe("FindFirstFile", relSearch, added ? "listed with sealed entries" : "listed (real entries only)");
			return vf;
		}

		HANDLE OpenListing(const std::wstring& search, const std::string& rel, LPWIN32_FIND_DATAW out)
		{
			auto vf = BuildListing(search, rel);
			if (!vf || vf->entries.empty()) {
				return nullptr;
			}
			HANDLE fake = ::CreateEventW(nullptr, TRUE, TRUE, nullptr);
			if (!fake) {
				return nullptr;
			}
			*out = vf->entries[0];
			vf->next = 1;
			std::unique_lock lock(g_filesLock);
			g_finds[fake] = vf;
			return fake;
		}

		std::shared_ptr<VFind> LookupFind(HANDLE h)
		{
			if (h == nullptr || h == INVALID_HANDLE_VALUE) return nullptr;
			std::shared_lock lock(g_filesLock);
			auto it = g_finds.find(h);
			return it == g_finds.end() ? nullptr : it->second;
		}

		HANDLE WINAPI h_FindFirstFileW(LPCWSTR path, LPWIN32_FIND_DATAW fd)
		{
			const std::string rel = RelativeToData(path);
			if (!rel.empty() && fd) {
				if (HANDLE v = OpenListing(path, rel, fd)) {
					::SetLastError(ERROR_SUCCESS);
					return v;
				}
			}
			HANDLE h = o_FindFirstFileW(path, fd);
			if (!rel.empty() && IsSoundish(rel)) {
				const DWORD err = ::GetLastError();
				Probe("FindFirstFileW", rel, h == INVALID_HANDLE_VALUE ? "nothing" : "found");
				::SetLastError(err);
			}
			return h;
		}

		HANDLE WINAPI h_FindFirstFileExW(LPCWSTR path, FINDEX_INFO_LEVELS level, LPVOID fd, FINDEX_SEARCH_OPS op, LPVOID filter, DWORD flags)
		{
			const std::string rel = RelativeToData(path);
			if (!rel.empty() && fd && (level == FindExInfoStandard || level == FindExInfoBasic)) {
				if (HANDLE v = OpenListing(path, rel, static_cast<LPWIN32_FIND_DATAW>(fd))) {
					::SetLastError(ERROR_SUCCESS);
					return v;
				}
			}
			HANDLE h = o_FindFirstFileExW(path, level, fd, op, filter, flags);
			if (!rel.empty() && IsSoundish(rel)) {
				const DWORD err = ::GetLastError();
				Probe("FindFirstFileExW", rel, h == INVALID_HANDLE_VALUE ? "nothing" : "found");
				::SetLastError(err);
			}
			return h;
		}

		HANDLE WINAPI h_FindFirstFileA(LPCSTR path, LPWIN32_FIND_DATAA fd)
		{
			const std::wstring w = Widen(path);
			const std::string rel = RelativeToData(w.c_str());
			if (!rel.empty() && fd) {
				WIN32_FIND_DATAW wfd{};
				if (HANDLE v = OpenListing(w, rel, &wfd)) {
					ToAnsi(wfd, *fd);
					::SetLastError(ERROR_SUCCESS);
					return v;
				}
			}
			HANDLE h = o_FindFirstFileA(path, fd);
			if (!rel.empty() && IsSoundish(rel)) {
				const DWORD err = ::GetLastError();
				Probe("FindFirstFileA", rel, h == INVALID_HANDLE_VALUE ? "nothing" : "found");
				::SetLastError(err);
			}
			return h;
		}

		HANDLE WINAPI h_FindFirstFileExA(LPCSTR path, FINDEX_INFO_LEVELS level, LPVOID fd, FINDEX_SEARCH_OPS op, LPVOID filter, DWORD flags)
		{
			const std::wstring w = Widen(path);
			const std::string rel = RelativeToData(w.c_str());
			if (!rel.empty() && fd && (level == FindExInfoStandard || level == FindExInfoBasic)) {
				WIN32_FIND_DATAW wfd{};
				if (HANDLE v = OpenListing(w, rel, &wfd)) {
					ToAnsi(wfd, *static_cast<LPWIN32_FIND_DATAA>(fd));
					::SetLastError(ERROR_SUCCESS);
					return v;
				}
			}
			return o_FindFirstFileExA(path, level, fd, op, filter, flags);
		}

		BOOL WINAPI h_FindNextFileW(HANDLE h, LPWIN32_FIND_DATAW fd)
		{
			auto vf = LookupFind(h);
			if (!vf) {
				return o_FindNextFileW(h, fd);
			}
			if (vf->next >= vf->entries.size()) {
				::SetLastError(ERROR_NO_MORE_FILES);
				return FALSE;
			}
			if (fd) *fd = vf->entries[vf->next];
			vf->next++;
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		BOOL WINAPI h_FindNextFileA(HANDLE h, LPWIN32_FIND_DATAA fd)
		{
			auto vf = LookupFind(h);
			if (!vf) {
				return o_FindNextFileA(h, fd);
			}
			if (vf->next >= vf->entries.size()) {
				::SetLastError(ERROR_NO_MORE_FILES);
				return FALSE;
			}
			if (fd) ToAnsi(vf->entries[vf->next], *fd);
			vf->next++;
			::SetLastError(ERROR_SUCCESS);
			return TRUE;
		}

		BOOL WINAPI h_FindClose(HANDLE h)
		{
			bool ours = false;
			{
				std::unique_lock lock(g_filesLock);
				ours = g_finds.erase(h) != 0;
			}
			if (ours) {
				o_CloseHandle ? o_CloseHandle(h) : ::CloseHandle(h);
				::SetLastError(ERROR_SUCCESS);
				return TRUE;
			}
			return o_FindClose(h);
		}

		// ---- who ends the process? (diagnostic) --------------------------------------------------------------------
		// An uncaught C++ exception or an abort() ends the game through ExitProcess with no crash record anywhere; the
		// caller's stack says which module did it.

		void WINAPI h_ExitProcess(UINT code)
		{
			if (CrashLog::ShouldLogExit()) {
				char why[96];
				std::snprintf(why, sizeof(why), "ExitProcess(%u) before the game finished loading", code);
				CrashLog::WriteStack(why);
			}
			o_ExitProcess(code);
		}

		BOOL WINAPI h_TerminateProcess(HANDLE process, UINT code)
		{
			if (CrashLog::ShouldLogExit() && (process == ::GetCurrentProcess() || ::GetProcessId(process) == ::GetCurrentProcessId())) {
				char why[96];
				std::snprintf(why, sizeof(why), "TerminateProcess(self, %u) before the game finished loading", code);
				CrashLog::WriteStack(why);
			}
			return o_TerminateProcess(process, code);
		}

		// ---- import table --------------------------------------------------------------------------------------------

		struct Patch
		{
			const char* name;
			void*       hook;
			void**      original;
		};

		std::set<HMODULE>   g_patchedModules;
		std::vector<Patch>  g_patches;
		std::wstring        g_gameDir;    // lower-case, with trailing slash

		std::wstring Lower(std::wstring s)
		{
			for (wchar_t& c : s) c = (wchar_t)::towlower(c);
			return s;
		}

		int PatchImports(HMODULE module, const std::vector<Patch>& patches)
		{
			auto* base = reinterpret_cast<std::uint8_t*>(module);
			auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
			if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
				return 0;
			}
			auto* nt = reinterpret_cast<IMAGE_NT_HEADERS*>(base + dos->e_lfanew);   // 64- or 32-bit layout, by build
			if (nt->Signature != IMAGE_NT_SIGNATURE) {
				return 0;
			}
			const IMAGE_DATA_DIRECTORY& dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
			if (!dir.VirtualAddress) {
				return 0;
			}
			int patched = 0;
			auto* desc = reinterpret_cast<IMAGE_IMPORT_DESCRIPTOR*>(base + dir.VirtualAddress);
			for (; desc->Name; desc++) {
				const char* dll = reinterpret_cast<const char*>(base + desc->Name);
				if (!desc->OriginalFirstThunk) {
					continue;
				}
				auto* names = reinterpret_cast<IMAGE_THUNK_DATA*>(base + desc->OriginalFirstThunk);   // IMAGE_THUNK_DATA follows the build's bitness
				auto* thunks = reinterpret_cast<IMAGE_THUNK_DATA*>(base + desc->FirstThunk);
				for (; names->u1.AddressOfData; names++, thunks++) {
					if (IMAGE_SNAP_BY_ORDINAL(names->u1.Ordinal)) {
						continue;
					}
					auto* byName = reinterpret_cast<IMAGE_IMPORT_BY_NAME*>(base + names->u1.AddressOfData);
					const char* fn = byName->Name;
					if (g_options.logImports && (std::strstr(fn, "File") || std::strstr(fn, "Find") || std::strstr(fn, "Handle"))) {
						Log::Info("import %s!%s", dll, fn);
					}
					for (const Patch& p : patches) {
						if (std::strcmp(fn, p.name) != 0) {
							continue;
						}
						DWORD old = 0;
						if (!::VirtualProtect(&thunks->u1.Function, sizeof(void*), PAGE_READWRITE, &old)) {
							Log::Warn("could not unprotect the import entry of %s", fn);
							break;
						}
						if (!*p.original) {
							*p.original = reinterpret_cast<void*>(static_cast<std::uintptr_t>(thunks->u1.Function));
						}
						thunks->u1.Function = static_cast<decltype(thunks->u1.Function)>(reinterpret_cast<std::uintptr_t>(p.hook));
						::VirtualProtect(&thunks->u1.Function, sizeof(void*), old, &old);
						patched++;
						if (g_patchedModules.empty()) {
							Log::Info("hooked %s!%s", dll, fn);   // the executable's own list; other modules get one summary line
						}
					}
				}
			}
			return patched;
		}
	}

	int Install(const Options& options)
	{
		g_options = options;
		HMODULE game = ::GetModuleHandleW(nullptr);
		const std::vector<Patch> patches = {
			{ "CreateFileW", (void*)&h_CreateFileW, (void**)&o_CreateFileW },
			{ "CreateFileA", (void*)&h_CreateFileA, (void**)&o_CreateFileA },
			{ "CreateFile2", (void*)&h_CreateFile2, (void**)&o_CreateFile2 },
			{ "CreateFileMappingA", (void*)&h_CreateFileMappingA, (void**)&o_CreateFileMappingA },
			{ "CreateFileMappingW", (void*)&h_CreateFileMappingW, (void**)&o_CreateFileMappingW },
			{ "ReadFile", (void*)&h_ReadFile, (void**)&o_ReadFile },
			{ "ReadFileEx", (void*)&h_ReadFileEx, (void**)&o_ReadFileEx },
			{ "SetFilePointer", (void*)&h_SetFilePointer, (void**)&o_SetFilePointer },
			{ "SetFilePointerEx", (void*)&h_SetFilePointerEx, (void**)&o_SetFilePointerEx },
			{ "GetFileSize", (void*)&h_GetFileSize, (void**)&o_GetFileSize },
			{ "GetFileSizeEx", (void*)&h_GetFileSizeEx, (void**)&o_GetFileSizeEx },
			{ "GetFileType", (void*)&h_GetFileType, (void**)&o_GetFileType },
			{ "GetFileInformationByHandle", (void*)&h_GetFileInformationByHandle, (void**)&o_GetFileInformationByHandle },
			{ "GetFileInformationByHandleEx", (void*)&h_GetFileInformationByHandleEx, (void**)&o_GetFileInformationByHandleEx },
			{ "CloseHandle", (void*)&h_CloseHandle, (void**)&o_CloseHandle },
			{ "GetFileAttributesW", (void*)&h_GetFileAttributesW, (void**)&o_GetFileAttributesW },
			{ "GetFileAttributesA", (void*)&h_GetFileAttributesA, (void**)&o_GetFileAttributesA },
			{ "GetFileAttributesExW", (void*)&h_GetFileAttributesExW, (void**)&o_GetFileAttributesExW },
			{ "GetFileAttributesExA", (void*)&h_GetFileAttributesExA, (void**)&o_GetFileAttributesExA },
			{ "FindFirstFileA", (void*)&h_FindFirstFileA, (void**)&o_FindFirstFileA },
			{ "FindFirstFileExA", (void*)&h_FindFirstFileExA, (void**)&o_FindFirstFileExA },
			{ "FindNextFileA", (void*)&h_FindNextFileA, (void**)&o_FindNextFileA },
			{ "FindNextFileW", (void*)&h_FindNextFileW, (void**)&o_FindNextFileW },
			{ "FindClose", (void*)&h_FindClose, (void**)&o_FindClose },
			{ "FindFirstFileW", (void*)&h_FindFirstFileW, (void**)&o_FindFirstFileW },
			{ "FindFirstFileExW", (void*)&h_FindFirstFileExW, (void**)&o_FindFirstFileExW },
		};
		{
			wchar_t buf[MAX_PATH]{};
			::GetModuleFileNameW(game, buf, MAX_PATH);
			std::wstring exe = Lower(buf);
			const auto slash = exe.find_last_of(L"\\/");
			g_gameDir = slash == std::wstring::npos ? L"" : exe.substr(0, slash + 1);
		}
		std::vector<Patch> all = patches;
		if (options.exitLog) {
			all.push_back({ "ExitProcess", (void*)&h_ExitProcess, (void**)&o_ExitProcess });
			all.push_back({ "TerminateProcess", (void*)&h_TerminateProcess, (void**)&o_TerminateProcess });
		}
		g_patches = all;
		const int n = PatchImports(game, all);
		g_patchedModules.insert(game);
		const bool savedLog = g_options.logImports;
		g_options.logImports = false;           // the executable's import list is enough
		PatchNewModules();
		g_options.logImports = savedLog;
		// anything the game does not import still needs a real function behind our test entry points
		if (!o_CreateFileW) o_CreateFileW = ::CreateFileW;
		if (!o_CreateFileA) o_CreateFileA = ::CreateFileA;
		if (!o_CreateFile2) o_CreateFile2 = ::CreateFile2;
		if (!o_CreateFileMappingA) o_CreateFileMappingA = ::CreateFileMappingA;
		if (!o_CreateFileMappingW) o_CreateFileMappingW = ::CreateFileMappingW;
		if (!o_ReadFile) o_ReadFile = ::ReadFile;
		if (!o_ReadFileEx) o_ReadFileEx = ::ReadFileEx;
		if (!o_SetFilePointer) o_SetFilePointer = ::SetFilePointer;
		if (!o_SetFilePointerEx) o_SetFilePointerEx = ::SetFilePointerEx;
		if (!o_GetFileSize) o_GetFileSize = ::GetFileSize;
		if (!o_GetFileSizeEx) o_GetFileSizeEx = ::GetFileSizeEx;
		if (!o_GetFileType) o_GetFileType = ::GetFileType;
		if (!o_GetFileInformationByHandle) o_GetFileInformationByHandle = ::GetFileInformationByHandle;
		if (!o_GetFileInformationByHandleEx) o_GetFileInformationByHandleEx = ::GetFileInformationByHandleEx;
		if (!o_CloseHandle) o_CloseHandle = ::CloseHandle;
		if (!o_GetFileAttributesW) o_GetFileAttributesW = ::GetFileAttributesW;
		if (!o_GetFileAttributesA) o_GetFileAttributesA = ::GetFileAttributesA;
		if (!o_GetFileAttributesExW) o_GetFileAttributesExW = ::GetFileAttributesExW;
		if (!o_GetFileAttributesExA) o_GetFileAttributesExA = ::GetFileAttributesExA;
		if (!o_FindFirstFileA) o_FindFirstFileA = ::FindFirstFileA;
		if (!o_FindFirstFileExA) o_FindFirstFileExA = ::FindFirstFileExA;
		if (!o_FindNextFileA) o_FindNextFileA = ::FindNextFileA;
		if (!o_FindNextFileW) o_FindNextFileW = ::FindNextFileW;
		if (!o_FindClose) o_FindClose = ::FindClose;
		if (!o_ExitProcess) o_ExitProcess = ::ExitProcess;
		if (!o_TerminateProcess) o_TerminateProcess = ::TerminateProcess;
		if (!o_FindFirstFileW) o_FindFirstFileW = ::FindFirstFileW;
		if (!o_FindFirstFileExW) o_FindFirstFileExW = ::FindFirstFileExW;
		return n;
	}

	int PatchExitHooksEverywhere()
	{
		std::vector<Patch> exits = {
			{ "ExitProcess", (void*)&h_ExitProcess, (void**)&o_ExitProcess },
			{ "TerminateProcess", (void*)&h_TerminateProcess, (void**)&o_TerminateProcess },
		};
		HMODULE mods[1024];
		DWORD needed = 0;
		if (!::EnumProcessModules(::GetCurrentProcess(), mods, sizeof(mods), &needed)) {
			return 0;
		}
		HMODULE self{ nullptr };
		static int anchor = 0;
		::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, reinterpret_cast<LPCWSTR>(&anchor), &self);
		int total = 0;
		const DWORD count = std::min<DWORD>(needed / sizeof(HMODULE), 1024);
		const bool savedLog = g_options.logImports;
		g_options.logImports = false;
		for (DWORD i = 0; i < count; i++) {
			if (mods[i] == self) continue;
			wchar_t buf[MAX_PATH]{};
			::GetModuleFileNameW(mods[i], buf, MAX_PATH);
			const std::wstring path = Lower(buf);
			if (path.find(L"\\kernel32.dll") != std::wstring::npos || path.find(L"\\kernelbase.dll") != std::wstring::npos || path.find(L"\\ntdll.dll") != std::wstring::npos) {
				continue;   // the implementations themselves
			}
			total += PatchImports(mods[i], exits);
		}
		g_options.logImports = savedLog;
		return total;
	}

	int PatchNewModules()
	{
		if (g_patches.empty()) {
			return 0;
		}
		HMODULE mods[1024];
		DWORD needed = 0;
		if (!::EnumProcessModules(::GetCurrentProcess(), mods, sizeof(mods), &needed)) {
			return 0;
		}
		HMODULE self{ nullptr };
		static int anchor = 0;
		::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, reinterpret_cast<LPCWSTR>(&anchor), &self);
		int total = 0;
		const DWORD count = std::min<DWORD>(needed / sizeof(HMODULE), 1024);
		for (DWORD i = 0; i < count; i++) {
			HMODULE m = mods[i];
			if (m == self || g_patchedModules.count(m)) {
				continue;
			}
			wchar_t buf[MAX_PATH]{};
			if (!::GetModuleFileNameW(m, buf, MAX_PATH)) {
				continue;
			}
			const std::wstring path = Lower(buf);
			if (g_gameDir.empty() || path.rfind(g_gameDir, 0) != 0) {
				continue;
			}
			// patchModules 1: the script extender's runtime dll (by name prefix) and the plugins under the data folder, which
			// read game files the way the engine does; the renderer, video, Steam and runtime dlls beside the executable are
			// left alone. 2: every module under the game folder. 0: never reached (the executable only).
			if (g_options.patchModules <= 0) {
				continue;
			}
			if (g_options.patchModules == 1) {
				const std::wstring rest = path.substr(g_gameDir.size());
				bool extender = false;
				std::size_t start = 0;
				const std::wstring& prefixes = g_options.modulePrefixes;
				while (start < prefixes.size()) {
					std::size_t end = prefixes.find(L';', start);
					if (end == std::wstring::npos) end = prefixes.size();
					std::wstring pre = Lower(prefixes.substr(start, end - start));
					if (!pre.empty() && rest.rfind(pre, 0) == 0) {
						extender = true;
					}
					start = end + 1;
				}
				const std::wstring dataLower = Lower(g_options.dataDir);
				const bool plugin = !dataLower.empty() && path.rfind(dataLower, 0) == 0;
				if (!extender && !plugin) {
					continue;
				}
			}
			g_patchedModules.insert(m);
			const int n = PatchImports(m, g_patches);
			if (n > 0) {
				const auto slash = path.find_last_of(L"\\/");
				std::string name;
				{
					const std::wstring w = path.substr(slash == std::wstring::npos ? 0 : slash + 1);
					const int len = ::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
					name.resize((std::size_t)len);
					::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), name.data(), len, nullptr, nullptr);
				}
				Log::Info("also hooked %d file imports of %s", n, name.c_str());
				total += n;
			}
		}
		return total;
	}

	Counters Get()
	{
		return Counters{ g_served.load(), g_reads.load(), g_probesSeen.load(), g_probesAnswered.load(), g_looseWins.load() };
	}

	void LogCounters(const char* when)
	{
		const Counters c = Get();
		Log::Info("%s: served %llu sealed sounds, %llu reads from memory, %llu sound/music probes seen, %llu attribute checks answered, %llu loose files shadowing sealed ones",
			when, c.served, c.reads, c.probesSeen, c.probesAnswered, c.looseWins);
	}

	HANDLE TestCreateFileW(const wchar_t* path) { return h_CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr); }
	BOOL   TestReadFile(HANDLE h, void* buffer, DWORD toRead, DWORD* read) { return h_ReadFile(h, buffer, toRead, read, nullptr); }
	BOOL   TestGetFileSizeEx(HANDLE h, LARGE_INTEGER* size) { return h_GetFileSizeEx(h, size); }
	BOOL   TestSetFilePointerEx(HANDLE h, LARGE_INTEGER distance, LARGE_INTEGER* newPos, DWORD method) { return h_SetFilePointerEx(h, distance, newPos, method); }
	BOOL   TestCloseHandle(HANDLE h) { return h_CloseHandle(h); }
	DWORD  TestGetFileAttributesW(const wchar_t* path) { return h_GetFileAttributesW(path); }
	HANDLE TestCreateFileMapping(HANDLE h) { return h_CreateFileMappingW(h, nullptr, PAGE_READONLY, 0, 0, nullptr); }
}
