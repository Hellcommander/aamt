# Sealed Audio core

A game-agnostic library that makes sealed sound archives appear to a game as loose files. Any game or mod can use it
when wired in one of three ways: as part of a script-extender plugin, through the version.dll proxy for games without
an extender, or from managed or scripted code through `SealedAudioCore.dll`.

Why it exists: license compliance. Several sound libraries (the ones in `D:\assets\audio`: Dark Fantasy Studio /
Noise Alchemy, Tao and Sound, the Humble SFX bundle) allow their clips only *embedded* in a production, never as loose
files anyone can copy out. The archives made by `Tools/Shared/audio_seal.py` hold the sounds so that no loose audio
ever ships; the core serves them to the engine as if they sat loose in its data folder, so the mod's json, ESP, script
or `sounds.txt` references change nothing, and every player's game plays them.

- MTSA1: scrambled with the host's key. Against casual copying and tooling, not secrecy.
- MTSA2 (core 1.4, `seal --sign NAME`): encrypted (AES-256-GCM) and signed (ECDSA P-256). Sealing prevents *editing*,
  not use: the game decrypts the audio in memory on any machine, the archive is signed with a private key that never
  leaves the author's machine, and the core refuses an archive that is changed by even one byte.

## What the core does

At `sa_init` it mounts every `*.mtsa` in the archive folder (default `<data>\SealedAudio`), then patches the Win32 file
functions in the import table of the game executable and, by default, of the script extender's runtime dll and the
plugins under the data folder (plugins read their own sound files through the same functions). From then on:

- directory listings under the data folder show the sealed folders and files beside the real ones (engines index loose
  files by listing, so without this they never ask);
- attribute checks of sealed paths answer with their sizes, and sealed folders exist;
- opening a sealed path for reading, when no real file is there, gives a handle backed by the unsealed bytes; reads,
  seeks, sizes, type, information and file mappings on it are answered from memory;
- a real loose file at the same path always wins, so authors can test a sound by dropping it in.

Handled: CreateFileW/A/2, ReadFile/Ex, SetFilePointer/Ex, GetFileSize/Ex, GetFileType, GetFileInformationByHandle/Ex,
CloseHandle, GetFileAttributesW/A/ExW/ExA, FindFirstFileW/A/ExW/ExA, FindNextFileW/A, FindClose, CreateFileMappingA/W.
Verified so far on Skyrim SE 1.7.104 (SKSE host: 14 imports, self-test all pass, menu sounds played from an archive),
Skyrim VR 1.4.15 (SKSEVR, without a headset) and Starfield 1.16.244 (SFSE host: 21 imports, the engine indexed and
opened sealed entries). Fallout 4 1.11.240 (F4SE 0.7.9 host: loads, self-test all pass, the engine listed the sealed tree and opened its entries).
The New Vegas host (xNVSE 6.4.9, game 1.4.0.525, 32-bit) builds from a written-down NVSE header and is deployed but has
not been run yet; its host logs every NVSE message type it receives so a wrong constant would show. The proxy has been exercised in a process it was loaded into as version.dll (it loaded,
forwarded, mounted and passed the self-test there), but that process was SkyrimSELauncher.exe: starting SkyrimSE.exe
by hand bounces through Steam to the launcher, so a proxy test in a game's own process is still to do, on a game
that starts directly. The core dll has been driven from Python (bindings/python) with the self-test passing.

## Layout

```
include/sealed_audio.h          the C ABI (sa_config, sa_init, sa_patch_new_modules, sa_mark_loaded, sa_has, sa_read, ...)
src/                            the core: Archives (+ CNG: AES-GCM, ECDSA, SHA-256), FileHooks, SealedArchive (MTSA1/MTSA2 reader), Log, CrashLog (diagnostics), the API
src/SealedSigner.h              optional: pins the build to one signer (audio_seal.py write-cpp-signer; a public key, safe to ship)
SealedKey.h (not in src/)       the compiled-in key of one game, generated per build into that build's folder by audio_seal.py write-cpp-key --game NAME --namespace SealedKey
SealedAudioCore.vcxproj         static library  -> lib\Release\SealedAudioCore.lib
SealedAudioCoreDll.vcxproj      the same with the API exported -> bin\SealedAudioCore.dll (+ .lib)
hosts/skse/main.cpp             script-extender host: SKSE, SKSEVR and, with SEALED_SFSE / SEALED_F4SE / SEALED_NVSE, SFSE (Starfield) / F4SE (Fallout 4) / NVSE (New Vegas, 32-bit); headers in hosts/*/include
hosts/proxy/                    version.dll proxy host -> bin\proxy\version.dll + sealed_audio.ini
hosts/d2rloader/                D2RLoader plugin for Diablo II Resurrected (build.bat) -> bin\d2rloader\sealedaudio.dll;
                                Seal-LocalAudio.ps1 seals a mod's sounds as signed MTSA2 (signing key never shipped), from the
                                mod or straight from the library (-Map), and fails on loose audio or keys in the mod / zip;
                                New-D2rmmPackage.ps1 zips the dll with a mod's archives (no keys) for D2RMM's plugin manager
bindings/python/sealed_audio.py ctypes binding for the dll
bindings/csharp/SealedAudioNative.cs  P/Invoke binding for the dll
SealedAudio.sln                 builds the core, the dll and the proxy (Visual Studio 2022+, x64)
```

The Skyrim, Starfield, Fallout 4 and New Vegas plugins in `Skyrim Special Edition\src\SealedAudio` build from these sources (their project
files point at `$(SealedAudioCore)`, this folder) and keep only their tool, test mod and notes there.

## Wiring it

**Script-extender plugin.** Include `sealed_audio.h`, compile the five `src/*.cpp` files into your plugin (or link
`lib\Release\SealedAudioCore.lib`), and in your Load:

```cpp
sa_config cfg; sa_config_init(&cfg);
cfg.data_dir = L"...\\Data";            // where the game reads loose files
cfg.log_file = L"...\\SealedAudio.log";
sa_init(&cfg);                           // mounts archives, hooks the executable and the plugins loaded so far
// on the extender's "all plugins loaded" message:
sa_patch_new_modules();
// on its "data loaded" message:
sa_mark_loaded();
```

`hosts/skse/main.cpp` is exactly that for SKSE/SKSEVR/SFSE/F4SE/NVSE and reads a `SealedAudio.ini` beside the dll for the
switches. The core compiles for x64 and Win32 (the import-table and stack-walk code follow the build's bitness), so
32-bit games such as New Vegas work with a Win32 build of the host. For another extender (NVSE, OBSE, ...) add a branch the same way: the plugin API header, the version-data
export, and which message means "all plugins loaded" and "data loaded".

**Diablo II Resurrected: a D2RLoader plugin.** `hosts/d2rloader/build.bat [plugins folder]` builds `sealedaudio.dll`
against the D2RLoader PluginSDK (`D2RL_SDK`, else the toolkit's copy under the game's `mods\SkillTab4\sdk\include`)
and copies it into a mod's `d2rloader\plugins` (or the game's, for every mod). It mounts `<scope>\d2rloader\SealedAudio\*.mtsa`
(else `<scope>\d2rloader\plugins\SealedAudio\*.mtsa`, where a D2RMM package made by `hosts/d2rloader/New-D2rmmPackage.ps1`
deploys them),
whose entries are relative to the mod's `data` folder (`/hd/global/sfx/mymod/hit_hd.flac`), and reads
`<scope>\d2rloader\config\sealedaudio.toml` (written with defaults on first run). The packed game imports no file
functions, so this host turns on `patch_system`; it logs to `<game>\d2rloader\logs\SealedAudio.log`. Walkthrough in
`Tools/DiabloII/README.md` (Licensed sounds in a mod).

**Any game, no extender: the proxy.** Put `bin\proxy\version.dll` and `sealed_audio.ini` beside the game's executable.
Windows loads it in place of the system version.dll, it forwards every export to the real one, and on its own thread it
starts the core from the ini (`DataDir`, `DataFolderName`, `ArchiveDir`, `LogFile`, `PatchModules`, `StartDelayMs`,
`SelfTest`, diagnostics). Keep `PatchModules=1` unless the game has no extender-style plugins, then `0`; `2` hooks every
module in the game folder (renderer and runtime dlls included) and is for games whose own dlls load the sounds.
A game that already ships a `version.dll` mod needs a different proxy name; the forwarder list in `version_proxy.cpp`
is the only part tied to that dll.

**Managed, scripted or other-language hosts.** Load `bin\SealedAudioCore.dll` and call the same functions:
`bindings/csharp/SealedAudioNative.cs` (BepInEx, MelonLoader, Unity mods, launchers) and `bindings/python/sealed_audio.py`
(ctypes). The hooks act on the process they are loaded into, so this is for code that runs inside the game; `sa_read`
also works from tooling to pull an entry out.

**Sealing.** `python Tools/Shared/audio_seal.py seal <mod folder> <out.mtsa> --include sound music --game NAME`. Every
game has its own build key, `--game NAME`, in `%LOCALAPPDATA%\SealedAudio\game-keys\NAME.key` (made on first use, never in
the repository or a mod): `d2r` for Diablo II Resurrected, `transcendence`, `magitech` (OpenStarbound), `skyrim`,
`starfield`... A reader is built with its game's key only, so an archive of one game is refused by every other game's
reader, and a leak of one key opens only that game. There is no shared default key. `--key FILE` seals with any 32-byte
key instead (a mod sealed with its own key ships it as `<archive>.key` beside the archive). Entry paths are relative to
the data folder (`/sound/fx/mymod/hit.wav`).

**Building a host with its game's key.** `audio_seal.py write-cpp-key <dir>\SealedKey.h --game NAME --namespace SealedKey`,
then put `<dir>` on the include path (the MSBuild projects take `-p:SealedKeyDir=<dir>`; `hosts\d2rloader\build.bat` does it
itself with `--game d2r`). There is no `src\SealedKey.h`: a stray one would override the game's key, and build.bat refuses it.
**Moving an archive to another key:** `audio_seal.py rekey <archive> --from-key <old key file> --game NAME` re-encrypts it in
place in memory (no sound touches the disk) and verifies every entry before replacing the file. A key that was ever
committed or shipped is burned: rekey every archive it opened, rebuild the readers, and keep the old key file only in
`%LOCALAPPDATA%\SealedAudio\retired` until nothing uses it.

**Sealed against editing (core 1.4, MTSA2).** `seal ... --sign NAME` encrypts every entry with AES-256-GCM under the
reader's key (`--game NAME`, the key the plugin's `SealedKey.h` is generated from), so the plugin decrypts it in
memory on any player's machine, and signs the archive with `%LOCALAPPDATA%\SealedAudio\keys\NAME.signkey` (ECDSA P-256,
made on first use, never shipped). The core verifies the signature when it mounts the archive and refuses it if a single
byte was changed; each entry's GCM tag is checked again when the game opens it, and a failing entry is never served
(`ERROR_FILE_CORRUPT`). `audio_seal.py write-cpp-signer src\SealedSigner.h --sign NAME` before a build pins the plugin
to that signer, so an archive someone unpacked and re-signed with their own key is refused as well. `verify <archive>
[--signer NAME]` checks an archive; `unseal` of an MTSA2 archive needs `--recover`. `--map sources.json` (`{"/game/path":
"D:/assets/audio/..."}`) seals straight from the licensed library, so the files are never copied loose into the mod;
`--remove` never deletes anything under the library (`AAMT_AUDIO_LIBRARY`, default `D:\assets\audio`). `--sign`
refuses `--local-key` (that would make the sounds play only on this machine). Python needs `cryptography`; the core
uses Windows CNG (`bcrypt.lib`), no third-party code.

**A key that never ships (core 1.3, MTSA1).** `--local-key NAME` seals with `%LOCALAPPDATA%\SealedAudio\keys\NAME.key` (made on
first use). The core loads every `*.key` in its key store (`key_dirs`, default that folder) and opens an archive with
whichever one has the archive's key id, so the archive plays where the key is and is refused everywhere else. Neither
the mod nor the dll carries anything that opens it. `audio_seal.py keys [--archive f]` lists the store and says which key
opens an archive. `--local-key` refuses `--embed-key`, and `seal` refuses to make a key inside the mod or beside the
archive. For Diablo II Resurrected, `hosts/d2rloader/Seal-LocalAudio.ps1` does the sealing, the check that no key
file is in the mod and, with `-Package`, the D2RMM zip. Key lookup order: the compiled-in (or `key32`) key, then
`<archive>.key` beside it, then the key store. The Skyrim project's
`tools/sealed_audio_tool.py` wraps this for Bethesda games (`seal`, `check` with staleness manifests, `run`).

## Options worth knowing

- `data_folder_name`: the segment the engine puts in its paths for the loose-file folder ("Data" for Bethesda games;
  a Unity game might use "StreamingAssets").
- `patch_modules` 0/1/2 and `module_prefixes` (default `skse;sfse;f4se;nvse;obse`): which modules' imports get hooked.
- `key32`: a runtime key instead of the compiled-in one, for hosts that keep their key elsewhere.
- `patch_system` (1.2): also redirect kernel32's file export stubs (`jmp [slot]` into KernelBase) for the whole process.
  For executables that resolve the file functions at run time rather than importing them (packed games such as Diablo II
  Resurrected). Every patched slot is put back at exit (an atexit handler registered by `sa_init` runs before the core's
  statics are destroyed), so other modules' calls during shutdown never reach torn-down state.
- `key_dirs` (1.3): semicolon list of local key-store folders (`%VARS%` expand); NULL or empty means
  `%LOCALAPPDATA%\SealedAudio\keys`. The D2R plugin's TOML setting of the same name feeds it.
- `probe_prefixes` (1.2): which data-relative folders count as sound probes for `log_probes` (default `sound;music`;
  D2R uses `hd\global\sfx;global\sfx;...`).
- `sa_diagnostics(crash_log, exit_hooks, first_chance)`: off by default. Writes `SealedAudio-crash.log` with symbolized
  stacks on an unhandled exception, logs who calls ExitProcess before `sa_mark_loaded`, and logs first-chance C++
  exceptions and access violations during loading. Symbolizing is slow; use it to find a culprit, then turn it off.
- `sa_self_test()`: opens, sizes, seeks, reads, maps and closes `Sound\fx\sealedaudio\selftest.wav` through the hooked
  paths and logs SELFTEST lines; seal a test mod that holds that file.

## Formats and keys

MTSA2: `"MTSA2\0"`, 8-byte key id, u32 count, per entry u16 nameLen, UTF-8 path, u64 offset, u32 size (plaintext),
12-byte nonce; data AES-256-GCM ciphertext + 16-byte tag, associated data `"MTSA2\0"` + key id + path; trailer: the
signer's P-256 public key (X||Y, 64 bytes) and an ECDSA-SHA256 signature (r||s, 64 bytes) over everything before it.
Key lookup as for MTSA1. Signer id (in the log and `verify`): SHA-256 of the public key, first 8 bytes.

MTSA1: `"MTSA1\0"`, 8-byte key id (SHA-256 of the key, first 8), u32 count, per entry u16 nameLen, UTF-8 path, u64
offset, u32 size, u64 nonce; data XOR a splitmix64 keystream seeded with key0 ^ nonce ^ fnv1a64(path), each word ^ key1.
Readers also exist in Lua (Starbound) and C++ for two other engines in this toolkit; the Chimera loader uses its own
BWPK5 format (AES, HMAC tags, RSA-wrapped keys) and is not served by this core.
