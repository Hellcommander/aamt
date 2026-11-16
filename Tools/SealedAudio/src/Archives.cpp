#include "Archives.h"

#include "Log.h"
#include "SealedArchive.h"

#include <Windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <fstream>
#include <memory>
#include <mutex>
#include <unordered_map>

#pragma comment(lib, "bcrypt.lib")

#if __has_include("SealedSigner.h")
#include "SealedSigner.h"
#define SEALEDAUDIO_PINNED_SIGNER 1
#endif

namespace SealedAudio
{
	// ---- Windows CNG: AES-256-GCM, ECDSA P-256, SHA-256 (MTSA2) ------------------------------------------------------
	namespace
	{
		constexpr bool Ok(NTSTATUS s) { return s >= 0; }

		struct Provider
		{
			BCRYPT_ALG_HANDLE h{ nullptr };
			Provider(const wchar_t* alg, bool gcm)
			{
				if (!Ok(::BCryptOpenAlgorithmProvider(&h, alg, nullptr, 0))) {
					h = nullptr;
				} else if (gcm && !Ok(::BCryptSetProperty(h, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_GCM, sizeof(BCRYPT_CHAIN_MODE_GCM), 0))) {
					::BCryptCloseAlgorithmProvider(h, 0);
					h = nullptr;
				}
			}
			// left open for the life of the process: decryption can run during shutdown
		};

		BCRYPT_ALG_HANDLE Aes() { static Provider p(BCRYPT_AES_ALGORITHM, true); return p.h; }
		BCRYPT_ALG_HANDLE Ecdsa() { static Provider p(BCRYPT_ECDSA_P256_ALGORITHM, false); return p.h; }
		BCRYPT_ALG_HANDLE Sha256() { static Provider p(BCRYPT_SHA256_ALGORITHM, false); return p.h; }

		bool Sha256Of(const unsigned char* data, std::size_t len, unsigned char* out32)
		{
			BCRYPT_HASH_HANDLE hash = nullptr;
			if (!Sha256() || !Ok(::BCryptCreateHash(Sha256(), &hash, nullptr, 0, nullptr, 0, 0))) {
				return false;
			}
			bool ok = true;
			for (std::size_t done = 0; ok && done < len;) {  // ULONG-sized chunks
				const ULONG n = (ULONG)std::min<std::size_t>(len - done, 0x40000000);
				ok = Ok(::BCryptHashData(hash, (PUCHAR)data + done, n, 0));
				done += n;
			}
			ok = ok && Ok(::BCryptFinishHash(hash, out32, 32, 0));
			::BCryptDestroyHash(hash);
			return ok;
		}
	}

	bool GcmDecrypt(const unsigned char* key32, const unsigned char* nonce12, const unsigned char* aad, std::size_t aadLen,
		const unsigned char* cipher, std::size_t len, const unsigned char* tag16, unsigned char* out)
	{
		BCRYPT_KEY_HANDLE key = nullptr;
		if (!Aes() || len > 0xFFFFFFFFull || !Ok(::BCryptGenerateSymmetricKey(Aes(), &key, nullptr, 0, (PUCHAR)key32, 32, 0))) {
			return false;
		}
		BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO info;
		BCRYPT_INIT_AUTH_MODE_INFO(info);
		info.pbNonce = (PUCHAR)nonce12;
		info.cbNonce = 12;
		info.pbAuthData = (PUCHAR)aad;
		info.cbAuthData = (ULONG)aadLen;
		info.pbTag = (PUCHAR)tag16;
		info.cbTag = 16;
		ULONG got = 0;
		unsigned char dummy = 0;  // CNG wants a buffer even for an empty entry
		const NTSTATUS s = ::BCryptDecrypt(key, len ? (PUCHAR)cipher : &dummy, (ULONG)len, &info, nullptr, 0, len ? out : &dummy, (ULONG)len, &got, 0);
		::BCryptDestroyKey(key);
		return Ok(s) && got == len;
	}

	bool EcdsaP256Verify(const unsigned char* pub64, const unsigned char* data, std::size_t len, const unsigned char* sig64)
	{
		unsigned char digest[32];
		if (!Ecdsa() || !Sha256Of(data, len, digest)) {
			return false;
		}
		unsigned char blob[sizeof(BCRYPT_ECCKEY_BLOB) + 64];
		auto* head = (BCRYPT_ECCKEY_BLOB*)blob;
		head->dwMagic = BCRYPT_ECDSA_PUBLIC_P256_MAGIC;
		head->cbKey = 32;
		std::memcpy(blob + sizeof(BCRYPT_ECCKEY_BLOB), pub64, 64);
		BCRYPT_KEY_HANDLE key = nullptr;
		if (!Ok(::BCryptImportKeyPair(Ecdsa(), nullptr, BCRYPT_ECCPUBLIC_BLOB, &key, blob, sizeof(blob), 0))) {
			return false;
		}
		const NTSTATUS s = ::BCryptVerifySignature(key, nullptr, digest, 32, (PUCHAR)sig64, 64, 0);
		::BCryptDestroyKey(key);
		return Ok(s);
	}

	const unsigned char* PinnedSigner()
	{
#ifdef SEALEDAUDIO_PINNED_SIGNER
		return SealedSigner::PublicKey;
#else
		return nullptr;
#endif
	}

	std::string Archive::SignerIdOf(const unsigned char* pub64)
	{
		unsigned char d[32];
		if (!Sha256Of(pub64, 64, d)) {
			return "?";
		}
		static const char* hex = "0123456789abcdef";
		std::string s;
		for (int i = 0; i < 8; i++) {
			s += hex[d[i] >> 4];
			s += hex[d[i] & 15];
		}
		return s;
	}
}

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

	namespace
	{
		// Every *.key (64 hex characters) in the key-store folders, as hex text, with its source for the log. File names do
		// not matter: an archive picks the key whose id matches its header.
		struct StoreKey
		{
			std::string   hex;
			unsigned char id[8]{};
			std::wstring  file;
		};

		std::vector<StoreKey> LoadKeyStore(const std::vector<std::wstring>& dirs)
		{
			std::vector<StoreKey> keys;
			for (const std::wstring& dir : dirs) {
				WIN32_FIND_DATAW fd{};
				HANDLE h = ::FindFirstFileW((dir + L"\\*.key").c_str(), &fd);
				if (h == INVALID_HANDLE_VALUE) {
					continue;
				}
				do {
					if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
						continue;
					}
					StoreKey k;
					k.file = dir + L"\\" + fd.cFileName;
					auto bytes = Slurp(k.file);
					k.hex.assign(bytes.begin(), bytes.end());
					unsigned char raw[32];
					if (!Archive::ParseHexKey(k.hex, raw)) {
						Log::Warn("key store: %s is not 64 hex characters; skipped", Narrow(k.file).c_str());
						continue;
					}
					Archive::KeyIdImpl(raw, k.id);
					keys.push_back(std::move(k));
				} while (::FindNextFileW(h, &fd));
				::FindClose(h);
			}
			return keys;
		}
	}

	Stats Load(const std::wstring& folder, const unsigned char* key32, const std::vector<std::wstring>& keyDirs)
	{
		std::lock_guard lock(g_mutex);
		Stats stats;
		SetBuildKey(key32);
		const auto store = LoadKeyStore(keyDirs);
		for (const std::wstring& dir : keyDirs) {
			Log::Info("key store %s", Narrow(dir).c_str());
		}
		Log::Info("%zu key(s) in the key store", store.size());
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
			std::vector<unsigned char> bytes = Slurp(file);
			std::wstring keySource = modKey.empty() ? std::wstring() : L"the .key beside it";
			std::string storeKey;
			if (modKey.empty() && bytes.size() >= 14) {
				// no key beside it: the local key store (keys that never ship with the mod)
				for (const StoreKey& k : store) {
					if (std::memcmp(k.id, bytes.data() + 6, 8) == 0) {
						storeKey = k.hex;
						keySource = k.file;
						break;
					}
				}
			}
			if (!archive->Open(std::move(bytes), &error, modKey, storeKey)) {
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
			const std::string seal = archive->Signed() ? ", MTSA2 signature valid, signer " + archive->SignerId() + (PinnedSigner() ? " (pinned)" : "") : std::string();
			if (archive->UsesOwnKey() && !keySource.empty()) {
				Log::Info("mounted %s: %zu sounds (key from %s%s)", Narrow(file).c_str(), archive->Count(), Narrow(keySource).c_str(), seal.c_str());
			} else {
				Log::Info("mounted %s: %zu sounds%s", Narrow(file).c_str(), archive->Count(), seal.empty() ? "" : (" (" + seal.substr(2) + ")").c_str());
			}
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
