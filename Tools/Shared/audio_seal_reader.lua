-- Sealed sound archive reader for OpenStarbound asset scripts (MTSA1, made by Tools/Shared/audio_seal.py).
--
-- Runs as a postLoad asset script (_metadata: "scripts": {"postLoad": ["/scripts/<mod>/audio_unseal.lua"]}). It reads
-- the archive with assets.bytes, unseals every entry in memory and hands it to the engine with assets.add under the
-- sound's own asset path, so every ".ogg" the mod names plays as usual while no sound file sits loose on disk.
-- Pure Lua 5.3: 64-bit integers, string.unpack / string.pack, bitwise operators. Nothing else.
--
-- The key below must match the archive's (the 8-byte key id in the header is checked first). This is scrambling against
-- copying and tools, not secrecy: anyone who reads this file has the key. Ship the C++ reader (the fork's
-- SealedAssetSource) instead where the key must stay hidden, and leave this script out.

local M = {}

local MAGIC = "MTSA1\0"
local WORDS_PER_CHUNK = 64                 -- 512 bytes per unpack/pack call: far fewer calls than byte by byte
local CHUNK_FMT = "<" .. string.rep("I8", WORDS_PER_CHUNK)

local function fnv1a64(s)
  local h = 0xCBF29CE484222325
  for i = 1, #s do
    h = (h ~ s:byte(i)) * 0x100000001B3
  end
  return h
end

local function splitmix(state)
  state = state + 0x9E3779B97F4A7C15
  local z = state
  z = (z ~ (z >> 30)) * 0xBF58476D1CE4E5B9
  z = (z ~ (z >> 27)) * 0x94D049BB133111EB
  return state, z ~ (z >> 31)
end

-- Unseal one entry: XOR with the keystream, 64 words at a time, then the tail word by word.
function M.unseal(data, key0, key1, nonce, name)
  local state = key0 ~ nonce ~ fnv1a64(name)
  local n = #data
  local out = {}
  local pos = 1
  local chunkBytes = WORDS_PER_CHUNK * 8
  local vals = {}
  while n - pos + 1 >= chunkBytes do
    local w = { string.unpack(CHUNK_FMT, data, pos) }
    for i = 1, WORDS_PER_CHUNK do
      local z
      state, z = splitmix(state)
      vals[i] = w[i] ~ z ~ key1
    end
    out[#out + 1] = string.pack(CHUNK_FMT, table.unpack(vals, 1, WORDS_PER_CHUNK))
    pos = pos + chunkBytes
  end
  while n - pos + 1 >= 8 do
    local w = string.unpack("<I8", data, pos)
    local z
    state, z = splitmix(state)
    out[#out + 1] = string.pack("<I8", w ~ z ~ key1)
    pos = pos + 8
  end
  if pos <= n then
    local z
    state, z = splitmix(state)
    local ks = string.pack("<I8", z ~ key1)
    local tail = {}
    for i = pos, n do
      tail[#tail + 1] = string.char(data:byte(i) ~ ks:byte(i - pos + 1))
    end
    out[#out + 1] = table.concat(tail)
  end
  return table.concat(out)
end

-- Parse the header and index. Returns { keyId = <8-byte string>, entries = { {name=, offset=, size=, nonce=}, ... } }.
function M.index(blob)
  if blob:sub(1, #MAGIC) ~= MAGIC then error("not an MTSA1 archive") end
  local keyId = blob:sub(#MAGIC + 1, #MAGIC + 8)
  local count, pos = string.unpack("<I4", blob, #MAGIC + 9)
  local entries = {}
  for _ = 1, count do
    local nameLen
    nameLen, pos = string.unpack("<I2", blob, pos)
    local name = blob:sub(pos, pos + nameLen - 1); pos = pos + nameLen
    local offset, size, nonce
    offset, size, nonce, pos = string.unpack("<I8I4I8", blob, pos)
    entries[#entries + 1] = { name = name, offset = offset, size = size, nonce = nonce }
  end
  return { keyId = keyId, entries = entries }
end

-- Unseal a whole archive into the engine. `key` = { id = <8-byte string>, k0 = <int>, k1 = <int> }.
-- `assetsApi` is the asset-script `assets` table (bytes / add); `log` optional.
function M.install(assetsApi, archivePath, key, log)
  log = log or function() end
  local ok, blob = pcall(assetsApi.bytes, archivePath)
  if not ok or not blob then log("sealed sounds: no archive at " .. archivePath); return 0 end
  local idx = M.index(blob)
  if idx.keyId ~= key.id then
    log("sealed sounds: " .. archivePath .. " was sealed with a different key; its sounds stay sealed")
    return 0
  end
  -- An engine with its own sealed-archive reader (the Magi-Tech fork) already serves these sounds: don't add them twice.
  if idx.entries[1] and assetsApi.exists and assetsApi.exists(idx.entries[1].name) then
    log("sealed sounds: the engine already serves the sounds in " .. archivePath .. "; the Lua reader stays idle")
    return 0
  end
  local n = 0
  for _, e in ipairs(idx.entries) do
    local data = blob:sub(e.offset + 1, e.offset + e.size)
    assetsApi.add(e.name, M.unseal(data, key.k0, key.k1, e.nonce, e.name))
    n = n + 1
  end
  log(string.format("sealed sounds: %d sounds unsealed from %s", n, archivePath))
  return n
end

return M
