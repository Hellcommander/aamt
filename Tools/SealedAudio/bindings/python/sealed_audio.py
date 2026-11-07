"""ctypes binding for SealedAudioCore.dll: mount sealed sound archives and serve them as loose files from Python.

    from sealed_audio import SealedAudio
    sa = SealedAudio(r"...\\bin\\SealedAudioCore.dll")
    sa.init(data_dir=r"D:\\Game\\Data", log_file=r"D:\\Game\\SealedAudio.log")
    sa.has("Sound/fx/mymod/hit.wav"), sa.read("Sound/fx/mymod/hit.wav"), sa.counters()

Note that the hooks patch the import tables of the current process: the useful host is a Python embedded in a game, or a
launcher that injects the dll. Reading entries (sa.read) works anywhere, for tooling."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from typing import Callable, Optional

LOG_FN = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)


class SaConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("data_dir", ctypes.c_wchar_p),
        ("data_folder_name", ctypes.c_wchar_p),
        ("archive_dir", ctypes.c_wchar_p),
        ("log_file", ctypes.c_wchar_p),
        ("log", LOG_FN),
        ("log_user", ctypes.c_void_p),
        ("key32", ctypes.POINTER(ctypes.c_uint8)),
        ("hook_listings", ctypes.c_int32),
        ("hook_attributes", ctypes.c_int32),
        ("hook_serve", ctypes.c_int32),
        ("hook_mappings", ctypes.c_int32),
        ("patch_modules", ctypes.c_int32),
        ("module_prefixes", ctypes.c_wchar_p),
        ("log_probes", ctypes.c_int32),
        ("max_probe_lines", ctypes.c_int32),
        ("log_imports", ctypes.c_int32),
    ]


class SealedAudio:
    def __init__(self, dll_path: str):
        self._dll = ctypes.WinDLL(dll_path)
        d = self._dll
        d.sa_config_init.argtypes = [ctypes.POINTER(SaConfig)]
        d.sa_init.argtypes = [ctypes.POINTER(SaConfig)]
        d.sa_init.restype = ctypes.c_int32
        d.sa_patch_new_modules.restype = ctypes.c_int32
        d.sa_self_test.restype = ctypes.c_int32
        d.sa_has.argtypes = [ctypes.c_char_p]
        d.sa_has.restype = ctypes.c_int32
        d.sa_read.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
        d.sa_read.restype = ctypes.c_int32
        d.sa_mounted.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]
        d.sa_counters.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
        d.sa_diagnostics.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]
        d.sa_version.restype = ctypes.c_char_p
        self._log_cb = None
        self._key = None
        self._strings = []

    def init(self, data_dir: str, archive_dir: Optional[str] = None, log_file: Optional[str] = None, key32: Optional[bytes] = None,
             log: Optional[Callable[[int, str], None]] = None, patch_modules: int = 1, data_folder_name: str = "Data", **flags) -> int:
        cfg = SaConfig()
        self._dll.sa_config_init(ctypes.byref(cfg))
        cfg.data_dir = data_dir
        cfg.data_folder_name = data_folder_name
        cfg.archive_dir = archive_dir
        cfg.log_file = log_file
        cfg.patch_modules = patch_modules
        if key32 is not None:
            if len(key32) != 32:
                raise ValueError("key32 must be 32 bytes")
            self._key = (ctypes.c_uint8 * 32)(*key32)
            cfg.key32 = ctypes.cast(self._key, ctypes.POINTER(ctypes.c_uint8))
        if log is not None:
            self._log_cb = LOG_FN(lambda level, msg, _user: log(level, msg.decode("utf-8", "replace") if msg else ""))
            cfg.log = self._log_cb
        for name in ("hook_listings", "hook_attributes", "hook_serve", "hook_mappings", "log_probes", "max_probe_lines", "log_imports"):
            if name in flags:
                setattr(cfg, name, int(flags[name]))
        return int(self._dll.sa_init(ctypes.byref(cfg)))

    def patch_new_modules(self) -> int:
        return int(self._dll.sa_patch_new_modules())

    def mark_loaded(self) -> None:
        self._dll.sa_mark_loaded()

    def self_test(self) -> int:
        return int(self._dll.sa_self_test())

    def diagnostics(self, crash_log=True, exit_hooks=True, first_chance=False) -> None:
        self._dll.sa_diagnostics(int(crash_log), int(exit_hooks), int(first_chance))

    def has(self, relative_path: str) -> bool:
        return bool(self._dll.sa_has(relative_path.encode("utf-8")))

    def read(self, relative_path: str) -> Optional[bytes]:
        size = ctypes.c_uint32()
        rc = self._dll.sa_read(relative_path.encode("utf-8"), None, 0, ctypes.byref(size))
        if rc == 0:
            return None
        buf = ctypes.create_string_buffer(size.value)
        rc = self._dll.sa_read(relative_path.encode("utf-8"), buf, size.value, ctypes.byref(size))
        return buf.raw[: size.value] if rc == 1 else None

    def mounted(self):
        a, e = ctypes.c_uint32(), ctypes.c_uint32()
        self._dll.sa_mounted(ctypes.byref(a), ctypes.byref(e))
        return a.value, e.value

    def counters(self) -> dict:
        out = (ctypes.c_uint64 * 5)()
        self._dll.sa_counters(out)
        return dict(zip(("served", "reads", "probes_seen", "attributes_answered", "loose_wins"), out))

    def version(self) -> str:
        return self._dll.sa_version().decode("ascii")
