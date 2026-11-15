"""Read-only access to the Diablo II: Resurrected game archive (CASC).

Uses CascLib.dll (Ladislav Zezula, MIT). D2RMM ships a copy in its `tools`
folder; pass its path, set D2R_CASCLIB, or let `find_casclib` look for it.
Nothing here writes to the game folder.
"""
import ctypes
import os
from ctypes import wintypes as w


def find_casclib(game_path, explicit=None):
    """Returns the path of a CascLib.dll: explicit > D2R_CASCLIB > search under the game folder."""
    for candidate in (explicit, os.environ.get('D2R_CASCLIB')):
        if candidate and os.path.isfile(candidate):
            return candidate
    for root, dirs, files in os.walk(game_path):
        # The archive itself (Data) is huge and never contains the DLL.
        dirs[:] = [d for d in dirs if d.lower() not in ('data', 'indices', 'ecache')]
        if root.count(os.sep) - game_path.count(os.sep) > 4:
            dirs[:] = []
        for name in files:
            if name.lower() == 'casclib.dll':
                return os.path.join(root, name)
    raise FileNotFoundError(
        'CascLib.dll not found. Pass --casclib, or set D2R_CASCLIB (D2RMM has one in its tools folder).')


class D2RArchive:
    """Opens the game archive at `game_path` (the folder that contains D2R.exe)."""

    def __init__(self, game_path, casclib=None):
        self.game_path = game_path
        self._dll = ctypes.WinDLL(find_casclib(game_path, casclib))
        d = self._dll
        d.CascOpenStorage.argtypes = [ctypes.c_char_p, w.DWORD, ctypes.POINTER(w.HANDLE)]
        d.CascOpenStorage.restype = ctypes.c_bool
        d.CascOpenFile.argtypes = [w.HANDLE, ctypes.c_char_p, w.DWORD, w.DWORD, ctypes.POINTER(w.HANDLE)]
        d.CascOpenFile.restype = ctypes.c_bool
        d.CascReadFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        d.CascReadFile.restype = ctypes.c_bool
        d.CascCloseFile.argtypes = [w.HANDLE]
        d.CascFindFirstFile.argtypes = [w.HANDLE, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_char_p]
        d.CascFindFirstFile.restype = w.HANDLE
        d.CascFindNextFile.argtypes = [w.HANDLE, ctypes.c_void_p]
        d.CascFindNextFile.restype = ctypes.c_bool
        d.CascFindClose.argtypes = [w.HANDLE]
        d.CascCloseStorage.argtypes = [w.HANDLE]
        self._h = w.HANDLE()
        if not d.CascOpenStorage(game_path.encode('mbcs'), 0, ctypes.byref(self._h)):
            raise OSError(f'Could not open the game archive at {game_path}')

    @staticmethod
    def _key(path):
        """`hd/missiles/arrow.json` or `data/hd/...` -> the archive's own name for the file."""
        p = path.replace('/', '\\')
        if p.lower().startswith('data\\'):
            p = p[5:]
        return ('data:data\\' + p).encode('latin1')

    def read(self, path):
        """Returns the file's bytes, or None when the archive has no such file."""
        f = w.HANDLE()
        if not self._dll.CascOpenFile(self._h, self._key(path), 0, 0, ctypes.byref(f)):
            return None
        out = bytearray()
        buf = ctypes.create_string_buffer(1 << 20)
        n = w.DWORD()
        while self._dll.CascReadFile(f, buf, len(buf), ctypes.byref(n)) and n.value:
            out += buf.raw[:n.value]
        self._dll.CascCloseFile(f)
        return bytes(out)

    def exists(self, path):
        f = w.HANDLE()
        if not self._dll.CascOpenFile(self._h, self._key(path), 0, 0, ctypes.byref(f)):
            return False
        self._dll.CascCloseFile(f)
        return True

    def list(self):
        """Every file name in the archive, lower-case, forward slashes, without the `data:data/` prefix."""
        buf = ctypes.create_string_buffer(4096)
        handle = self._dll.CascFindFirstFile(self._h, b'*', buf, None)
        names = []
        if handle and handle != w.HANDLE(-1).value:
            while True:
                name = buf.raw[:1024].split(b'\0', 1)[0].decode('latin1').lower()
                if name.startswith('data:data\\'):
                    names.append(name[10:].replace('\\', '/'))
                if not self._dll.CascFindNextFile(handle, buf):
                    break
            self._dll.CascFindClose(handle)
        return names

    def close(self):
        if self._h:
            self._dll.CascCloseStorage(self._h)
            self._h = w.HANDLE()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
