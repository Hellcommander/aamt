#include "Archives.h"

#include "Log.h"
#include "SealedArchive.h"

#include <Windows.h>

#include <algorithm>
#include <fstream>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace SealedAudio::Archives
{
	namespace
	{
		struct Mounted
		{
			std::wstring             file;
			std::shared_ptr<Archive> archive;
		};

		std::mutex                                                    g_mutex;
		std::vector<Mounted>                                          g_mounted;
		std::unordered_map<std::string, std::pair<std::size_t, Entry>> g_index;  // normalized path -> (archive index, entry)
		std::unordered_map<std::string, bool>                          g_dirs;   // normalized folder path (with trailing slash) -> present
		std::unordered_map<std::string, std::unordered_map<std::string, Child>> g_children;  // normalized folder -> child name (lower) -> child

		std::vector<unsigned char> Slurp(const std::wstring& path)
		{
			std::ifstream f(path, std::ios::binary);
			if (!f) {
				return {};
			}
			f.seekg(0, std::ios::end);
			const auto n = f.tellg();
			f.seekg(0, std::ios::beg);
			std::vector<unsigned char> out((std::size_t)n);
			if (n > 0) {
				f.read((char*)out.data(), n);
			}
			return out;
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
	}

	Stats Load(const std::wstring& folder, const unsigned char* key32)
	{
		std::lock_guard lock(g_mutex);
		Stats stats;
		SetBuildKey(key32);
		WIN32_FIND_DATAW fd{};
		HANDLE h = ::FindFirstFileW((folder + L"\\*.mtsa").c_str(), &fd);
		if (h == INVALID_HANDLE_VALUE) {
			Log::Info("no archives: %s has no *.mtsa", Narrow(folder).c_str());
			return stats;
		}
		std::vector<std::wstring> files;
		do {
			if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
				files.push_back(folder + L"\\" + fd.cFileName);
			}
		} while (::FindNextFileW(h, &fd));
		::FindClose(h);
		std::sort(files.begin(), files.end(), [](const std::wstring& a, const std::wstring& b) { return ::_wcsicmp(a.c_str(), b.c_str()) < 0; });

		for (const std::wstring& file : files) {
			auto archive = std::make_shared<Archive>();
			std::string error;
			std::string modKey;
			{
				// <archive>.key beside it: a mod author's own key, as 64 hex characters
				std::wstring keyPath = file.substr(0, file.size() - 5) + L".key";
				auto k = Slurp(keyPath);
				modKey.assign(k.begin(), k.end());
			}
			if (!archive->Open(Slurp(file), &error, modKey)) {
				Log::Warn("refused %s: %s", Narrow(file).c_str(), error.c_str());
				stats.refused++;
				continue;
			}
			const std::size_t idx = g_mounted.size();
			g_mounted.push_back({ file, archive });
			for (const auto& [path, entry] : archive->Entries()) {
				auto it = g_index.find(path);
				if (it != g_index.end()) {
					Log::Warn("%s is in both %s and %s; the later one wins", path.c_str(), Narrow(g_mounted[it->second.first].file).c_str(), Narrow(file).c_str());
				}
				g_index[path] = { idx, entry };
				// every parent folder exists, and every segment is a child of the folder above it
				std::string stored = entry.name;
				for (char& c : stored) {
					if (c == '\\') c = '/';
				}
				if (stored.empty() || stored[0] != '/') stored.insert(stored.begin(), '/');
				std::size_t prev = 1;
				for (std::size_t slash = path.find('/', 1); slash != std::string::npos; prev = slash + 1, slash = path.find('/', slash + 1)) {
					g_dirs[path.substr(0, slash + 1)] = true;
					Child c;
					c.name = stored.substr(prev, slash - prev);
					c.isDir = true;
					g_children[path.substr(0, prev)][path.substr(prev, slash - prev)] = c;
				}
				Child f;
				f.name = stored.substr(prev);
				f.size = entry.size;
				g_children[path.substr(0, prev)][path.substr(prev)] = f;
			}
			Log::Info("mounted %s: %zu sounds%s", Narrow(file).c_str(), archive->Count(), archive->UsesOwnKey() ? " (its own key)" : "");
			stats.archives++;
			stats.entries += archive->Count();
		}
		return stats;
	}

	bool Has(const std::string& rel)
	{
		std::lock_guard lock(g_mutex);
		return g_index.count(NormalizePath(rel)) != 0;
	}

	bool HasDirectory(const std::string& rel)
	{
		std::string n = NormalizePath(rel);
		if (n.empty() || n.back() != '/') {
			n += '/';
		}
		std::lock_guard lock(g_mutex);
		return g_dirs.count(n) != 0;
	}

	std::vector<Child> Children(const std::string& rel)
	{
		std::string n = NormalizePath(rel);
		if (n.empty() || n.back() != '/') {
			n += '/';
		}
		std::lock_guard lock(g_mutex);
		std::vector<Child> out;
		auto it = g_children.find(n);
		if (it != g_children.end()) {
			for (const auto& kv : it->second) {
				out.push_back(kv.second);
			}
		}
		return out;
	}

	bool SizeOf(const std::string& rel, std::uint64_t& size)
	{
		std::lock_guard lock(g_mutex);
		auto it = g_index.find(NormalizePath(rel));
		if (it == g_index.end()) {
			return false;
		}
		size = it->second.second.size;
		return true;
	}

	std::vector<unsigned char> Read(const std::string& rel, std::uint32_t* size)
	{
		std::shared_ptr<Archive> archive;
		Entry entry;
		{
			std::lock_guard lock(g_mutex);
			auto it = g_index.find(NormalizePath(rel));
			if (it == g_index.end()) {
				return {};
			}
			archive = g_mounted[it->second.first].archive;
			entry = it->second.second;
		}
		if (size) {
			*size = entry.size;
		}
		return archive->Read(entry);  // unsealing one entry, outside the lock: the archive bytes are immutable
	}

	std::uint32_t ArchiveCount()
	{
		std::lock_guard lock(g_mutex);
		return (std::uint32_t)g_mounted.size();
	}

	std::vector<std::string> Paths()
	{
		std::lock_guard lock(g_mutex);
		std::vector<std::string> out;
		for (const auto& kv : g_index) {
			out.push_back(kv.first);
		}
		std::sort(out.begin(), out.end());
		return out;
	}
}
