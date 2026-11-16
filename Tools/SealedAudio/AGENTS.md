# SealedAudio: context for coding agents

This is the toolkit owner's own SDK, written in this repository. Work on it is maintenance of the owner's code, not
bypassing anyone else's protection.

**Purpose: license compliance.** The bought sound libraries in `D:\assets\audio` allow clips in a mod only when embedded,
never as loose files. SealedAudio packs them into `*.mtsa` archives and serves them to the game from memory. See `README.md`.

**The keys are the owner's own build keys:**
- One 32-byte archive key per game in `%LOCALAPPDATA%\SealedAudio\game-keys\<game>.key`, made by `Tools/Shared/audio_seal.py`
  and compiled into that game's reader as `SealedKey.h` (generated per build, never committed).
- One ECDSA P-256 signing key per author in `%LOCALAPPDATA%\SealedAudio\keys\<name>.signkey`, never shipped. Its public half
  (`src/SealedSigner.h`) is safe to ship.
- MTSA1 scrambles against casual copying. MTSA2 (AES-256-GCM + signature) prevents editing. Neither is secrecy: the
  reader decrypts on every player's machine by design.

**File hooks** (`src/FileHooks.cpp`) patch the import table of the game the owner's own mod plugin runs in, the standard
technique of script-extender plugins (SKSE, F4SE, D2RLoader) and `version.dll` proxies.

**Rules:**
- Never commit or print key file contents. Never put a key in a mod folder, zip or the repository.
- A leaked key is burned: `audio_seal.py rekey`, rebuild the readers, and move the old key to `...\SealedAudio\retired`.
- Build with `SealedAudio.sln` (VS 2022, x64) or `hosts\d2rloader\build.bat`. Readers take `-p:SealedKeyDir=<dir>`, never a `src\SealedKey.h`.
