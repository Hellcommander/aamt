// SealedArchive.h
//
// Sealed sound archives (MTSA1, made by the AI asset toolkit's audio_seal.py or this project's tools/sealed_audio_tool.py):
// one file per mod under Data\SealedAudio\ holding its sounds scrambled with a per-entry keystream, so no sound file sits
// loose in the mod and nothing can be lifted by copying a folder. The plugin serves an entry to the engine as if it were
// the loose file Data\<path> whenever no real loose file is there.
//
// Format, little-endian: "MTSA1\0", 8 bytes key id, u32 count, then per entry u16 nameLen, UTF-8 asset path
// ("/sound/fx/mymod/hit.wav", relative to Data), u64 offset, u32 size, u64 nonce. Data: entry bytes XOR a splitmix64
// keystream seeded with key0 ^ nonce ^ fnv1a64(path as stored), each 64-bit word also ^ key1 (key0, key1 = the key's
// first two words). The build key and its id come from SealedKey.h (generated, never committed); an archive sealed with
// another key opens when its 32-byte key sits beside it as <archive>.key (hex), so any mod author can seal with a key of
// their own. Scrambling against copying and tools, not secrecy: the key is in this build.
//
// MTSA2 (audio_seal.py seal --sign NAME): sealed against editing. "MTSA2\0", key id, u32 count, then per entry u16
// nameLen, path, u64 offset, u32 size (plaintext), 12 bytes nonce; data: AES-256-GCM ciphertext + 16-byte tag (associated
// data "MTSA2\0" + key id + path), with the same key lookup as MTSA1 (so every player's game decrypts it, in memory);
// trailer: the signer's ECDSA P-256 public key (X||Y) and a signature (r||s) over everything before the signature. The
// signing key never leaves the author's machine. An archive whose signature does not verify is refused, so an edited
// archive never plays; with SealedSigner.h (audio_seal.py write-cpp-signer) only the pinned signer is accepted.

#pragma once

#include <cstdint>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#include "SealedKey.h"

namespace SealedAudio
{
	// The key archives are expected to be sealed with: the compiled-in SealedKey.h unless the host supplied one.
	inline unsigned char g_buildKey[32]{};
	inline unsigned char g_buildKeyId[8]{};
	inline bool          g_buildKeySet{ false };

	void SetBuildKey(const unsigned char* key32);   // nullptr: the compiled-in key

	// AES-256-GCM decryption (Windows CNG, Archives.cpp). False when the tag does not verify.
	bool GcmDecrypt(const unsigned char* key32, const unsigned char* nonce12, const unsigned char* aad, std::size_t aadLen,
		const unsigned char* cipher, std::size_t len, const unsigned char* tag16, unsigned char* out);

	constexpr std::size_t kGcmTag = 16;
	constexpr std::size_t kSigTrailer = 128;  // public key 64 + signature 64

	// ECDSA P-256 / SHA-256 over `data` (Windows CNG, Archives.cpp): raw X||Y public key and r||s signature.
	bool EcdsaP256Verify(const unsigned char* pub64, const unsigned char* data, std::size_t len, const unsigned char* sig64);

	// The pinned signer, if this build has one (SealedSigner.h); null when any valid signature is accepted.
	const unsigned char* PinnedSigner();

	struct Entry
	{
		std::string   name;  // path exactly as stored (seeds the keystream)
		std::uint64_t offset{ 0 };
		std::uint32_t size{ 0 };
		std::uint64_t nonce{ 0 };
		unsigned char iv[12]{};      // MTSA2
		bool          gcm{ false };  // MTSA2: AES-256-GCM, size is the plaintext size, a 16-byte tag follows the data
	};

	inline std::uint64_t ReadU64(const unsigned char* p)
	{
		std::uint64_t v = 0;
		for (int i = 7; i >= 0; --i) {
			v = (v << 8) | p[i];
		}
		return v;
	}

	inline std::uint32_t ReadU32(const unsigned char* p)
	{
		return (std::uint32_t)p[0] | ((std::uint32_t)p[1] << 8) | ((std::uint32_t)p[2] << 16) | ((std::uint32_t)p[3] << 24);
	}

	inline std::uint64_t Fnv1a64(const std::string& s)
	{
		std::uint64_t h = 0xCBF29CE484222325ull;
		for (unsigned char c : s) {
			h = (h ^ c) * 0x100000001B3ull;
		}
		return h;
	}

	inline std::uint64_t SplitMix(std::uint64_t& state)
	{
		state += 0x9E3779B97F4A7C15ull;
		std::uint64_t z = state;
		z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
		z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
		return z ^ (z >> 31);
	}

	// Lower case, forward slashes, one leading slash: the engine asks for "Data\Sound\fx\x.wav" (or an absolute path
	// ending that way); the archive stores "/sound/fx/x.wav". Callers pass the part after Data\.
	inline std::string NormalizePath(std::string s)
	{
		for (char& c : s) {
			if (c == '\\') {
				c = '/';
			} else if (c >= 'A' && c <= 'Z') {
				c = (char)(c - 'A' + 'a');
			}
		}
		if (s.empty() || s[0] != '/') {
			s.insert(s.begin(), '/');
		}
		return s;
	}

	class Archive
	{
	public:
		// Parses the index from the whole archive's bytes. False (with a reason) when it is not an archive or was sealed
		// with a key this build does not carry and `modKeyHex` (the sibling .key file's text) does not match either.
		// `storeKeyHex`: the local key store's key with this archive's id, if any (used when no .key sits beside it).
		bool Open(std::vector<unsigned char> bytes, std::string* error, const std::string& modKeyHex = std::string(), const std::string& storeKeyHex = std::string())
		{
			_bytes = std::move(bytes);
			_entries.clear();
			if (!g_buildKeySet) SetBuildKey(nullptr);
			std::memcpy(_key, g_buildKey, 32);
			const bool v2 = _bytes.size() >= 18 && std::memcmp(_bytes.data(), "MTSA2\0", 6) == 0;
			if (!v2 && (_bytes.size() < 18 || std::memcmp(_bytes.data(), "MTSA1\0", 6) != 0)) {
				return Fail("not a sealed sound archive (MTSA1/MTSA2)", error);
			}
			const std::string& ownHex = modKeyHex.empty() ? storeKeyHex : modKeyHex;
			if (std::memcmp(_bytes.data() + 6, g_buildKeyId, 8) != 0) {
				unsigned char modKey[32];
				if (!ParseHexKey(ownHex, modKey) || !KeyIdMatches(modKey, _bytes.data() + 6)) {
					return Fail("sealed with a key this build does not carry, and no matching .key file beside it or in the key store", error);
				}
				std::memcpy(_key, modKey, 32);
				_ownKey = true;
			}
			if (v2) {
				return OpenSigned(error);
			}
			const unsigned char* p = _bytes.data();
			const std::size_t total = _bytes.size();
			std::size_t pos = 14;
			const std::uint32_t count = ReadU32(p + pos);
			pos += 4;
			for (std::uint32_t i = 0; i < count; i++) {
				if (pos + 2 > total) {
					return Fail("truncated archive", error);
				}
				const std::uint16_t nameLen = (std::uint16_t)(p[pos] | (p[pos + 1] << 8));
				pos += 2;
				if (pos + nameLen + 20 > total) {
					return Fail("truncated archive", error);
				}
				Entry e;
				e.name.assign((const char*)p + pos, nameLen);
				pos += nameLen;
				e.offset = ReadU64(p + pos);
				e.size = ReadU32(p + pos + 8);
				e.nonce = ReadU64(p + pos + 12);
				pos += 20;
				if (e.offset + e.size > total) {
					return Fail("entry past the end of the archive", error);
				}
				_entries[NormalizePath(e.name)] = e;
			}
			return true;
		}

		[[nodiscard]] bool        IsOpen() const { return !_entries.empty(); }
		[[nodiscard]] std::size_t Count() const { return _entries.size(); }
		[[nodiscard]] bool        UsesOwnKey() const { return _ownKey; }
		[[nodiscard]] bool        Signed() const { return _gcm; }
		// Signer id: first 8 bytes of SHA-256 of the signer's public key, as hex (MTSA2 only).
		[[nodiscard]] const std::string& SignerId() const { return _signerId; }
		[[nodiscard]] const std::unordered_map<std::string, Entry>& Entries() const { return _entries; }

		[[nodiscard]] const Entry* Find(const std::string& normalizedPath) const
		{
			auto it = _entries.find(normalizedPath);
			return it == _entries.end() ? nullptr : &it->second;
		}

		// The unsealed bytes of an entry; empty (for a non-empty entry) when an MTSA2 entry fails authentication.
		std::vector<unsigned char> Read(const Entry& e) const
		{
			if (e.gcm) {
				std::vector<unsigned char> out(e.size);
				std::vector<unsigned char> aad(_bytes.data(), _bytes.data() + 14);
				aad.insert(aad.end(), e.name.begin(), e.name.end());
				const unsigned char* c = _bytes.data() + e.offset;
				if (!GcmDecrypt(_key, e.iv, aad.data(), aad.size(), c, e.size, c + e.size, out.data())) {
					SecureZero(out);
					return {};
				}
				return out;
			}
			std::vector<unsigned char> out(_bytes.data() + e.offset, _bytes.data() + e.offset + e.size);
			const std::uint64_t key0 = ReadU64(_key);
			const std::uint64_t key1 = ReadU64(_key + 8);
			std::uint64_t state = key0 ^ e.nonce ^ Fnv1a64(e.name);
			const std::size_t n = out.size();
			std::size_t i = 0;
			for (; i + 8 <= n; i += 8) {
				const std::uint64_t ks = SplitMix(state) ^ key1;
				for (int b = 0; b < 8; b++) {
					out[i + b] ^= (unsigned char)((ks >> (8 * b)) & 0xFF);
				}
			}
			if (i < n) {
				const std::uint64_t ks = SplitMix(state) ^ key1;
				for (int b = 0; i + b < n; b++) {
					out[i + b] ^= (unsigned char)((ks >> (8 * b)) & 0xFF);
				}
			}
			return out;
		}

	public:
		// 64 hex characters (surrounding whitespace allowed) -> 32 bytes.
		static bool ParseHexKey(const std::string& hex, unsigned char* out32)
		{
			const std::size_t start = hex.find_first_not_of(" \t\r\n"), end = hex.find_last_not_of(" \t\r\n");
			if (start == std::string::npos || end - start + 1 != 64) {
				return false;
			}
			for (int i = 0; i < 32; i++) {
				int v = 0;
				for (int k = 0; k < 2; k++) {
					const char c = hex[start + 2 * i + k];
					const int d = (c >= '0' && c <= '9') ? c - '0' : (c >= 'a' && c <= 'f') ? c - 'a' + 10 : (c >= 'A' && c <= 'F') ? c - 'A' + 10 : -1;
					if (d < 0) {
						return false;
					}
					v = v * 16 + d;
				}
				out32[i] = (unsigned char)v;
			}
			return true;
		}

	public:
		// Key id = first 8 bytes of SHA-256(key). A small SHA-256 of one 32-byte block, so no library is needed.
		inline static void KeyIdImpl(const unsigned char* key32, unsigned char* out8)
		{
			static const std::uint32_t K[64] = {
				0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
				0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
				0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
				0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2 };
			std::uint32_t h[8] = { 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19 };
			unsigned char block[64] = { 0 };
			std::memcpy(block, key32, 32);
			block[32] = 0x80;
			block[62] = 0x01;  // bit length 256 = 0x0100, big-endian in the last 8 bytes
			std::uint32_t w[64];
			for (int i = 0; i < 16; i++) {
				w[i] = ((std::uint32_t)block[4 * i] << 24) | ((std::uint32_t)block[4 * i + 1] << 16) | ((std::uint32_t)block[4 * i + 2] << 8) | block[4 * i + 3];
			}
			auto rotr = [](std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };
			for (int i = 16; i < 64; i++) {
				const std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
				const std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
				w[i] = w[i - 16] + s0 + w[i - 7] + s1;
			}
			std::uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
			for (int i = 0; i < 64; i++) {
				const std::uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
				const std::uint32_t ch = (e & f) ^ (~e & g);
				const std::uint32_t t1 = hh + S1 + ch + K[i] + w[i];
				const std::uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
				const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
				const std::uint32_t t2 = S0 + maj;
				hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
			}
			h[0] += a;
			h[1] += b;
			const unsigned char id[8] = { (unsigned char)(h[0] >> 24), (unsigned char)(h[0] >> 16), (unsigned char)(h[0] >> 8), (unsigned char)h[0],
				(unsigned char)(h[1] >> 24), (unsigned char)(h[1] >> 16), (unsigned char)(h[1] >> 8), (unsigned char)h[1] };
			std::memcpy(out8, id, 8);
		}

		static bool KeyIdMatches(const unsigned char* key32, const unsigned char* id8)
		{
			unsigned char id[8];
			KeyIdImpl(key32, id);
			return std::memcmp(id, id8, 8) == 0;
		}

		static void SecureZero(std::vector<unsigned char>& v)
		{
			volatile unsigned char* p = v.data();
			for (std::size_t i = 0; i < v.size(); i++) p[i] = 0;
			v.clear();
		}

		static std::string SignerIdOf(const unsigned char* pub64);  // Archives.cpp (SHA-256 via CNG)

	private:
		bool OpenSigned(std::string* error)
		{
			if (_bytes.size() < 18 + kSigTrailer) {
				return Fail("truncated archive (no signature)", error);
			}
			const std::size_t total = _bytes.size() - kSigTrailer;  // the data ends where the signer's key begins
			const unsigned char* pub = _bytes.data() + total;
			const unsigned char* sig = pub + 64;
			if (!EcdsaP256Verify(pub, _bytes.data(), total + 64, sig)) {
				return Fail("signature does not verify: the archive was edited after it was sealed", error);
			}
			if (const unsigned char* pin = PinnedSigner(); pin && std::memcmp(pin, pub, 64) != 0) {
				return Fail("signed by someone other than the signer this plugin was built for (SealedSigner.h)", error);
			}
			_signerId = SignerIdOf(pub);
			_gcm = true;
			const unsigned char* p = _bytes.data();
			std::size_t pos = 14;
			const std::uint32_t count = ReadU32(p + pos);
			pos += 4;
			for (std::uint32_t i = 0; i < count; i++) {
				if (pos + 2 > total) {
					return Fail("truncated archive", error);
				}
				const std::uint16_t nameLen = (std::uint16_t)(p[pos] | (p[pos + 1] << 8));
				pos += 2;
				if (pos + nameLen + 24 > total) {
					return Fail("truncated archive", error);
				}
				Entry e;
				e.gcm = true;
				e.name.assign((const char*)p + pos, nameLen);
				pos += nameLen;
				e.offset = ReadU64(p + pos);
				e.size = ReadU32(p + pos + 8);
				std::memcpy(e.iv, p + pos + 12, 12);
				pos += 24;
				if (e.offset > total || (std::uint64_t)e.size + kGcmTag > total - e.offset) {
					return Fail("entry past the end of the archive", error);
				}
				_entries[NormalizePath(e.name)] = e;
			}
			return true;
		}

		bool Fail(const char* reason, std::string* error)
		{
			if (error) {
				*error = reason;
			}
			_entries.clear();
			return false;
		}

		unsigned char                           _key[32]{};
		bool                                    _ownKey{ false };
		bool                                    _gcm{ false };
		std::string                             _signerId;
		std::vector<unsigned char>              _bytes;
		std::unordered_map<std::string, Entry>  _entries;
	};
}

namespace SealedAudio
{
	inline void SetBuildKey(const unsigned char* key32)
	{
		if (key32) {
			std::memcpy(g_buildKey, key32, 32);
		} else {
			std::memcpy(g_buildKey, SealedKey::Key, 32);
		}
		Archive::KeyIdImpl(g_buildKey, g_buildKeyId);
		g_buildKeySet = true;
	}
}
