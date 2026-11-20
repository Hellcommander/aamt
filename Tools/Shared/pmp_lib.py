"""pmp-library (Polygon Mesh Processing Library, MIT, C++) from Python, through pmpwrap.dll.

    import pmp_lib
    with pmp_lib.Mesh(vertices, triangles) as m:        # N x 3 floats, M x 3 ints; must be manifold
        m.fill_holes()
        m.remesh_uniform(edge_length=0.1)
        m.decimate(target_vertices=2000)
        vertices, triangles = m.arrays()
        uv = m.lscm()                                   # N x 2, for a mesh with an open edge

The DLL is built from the clone in Tools/Shared/third_party/pmp-library by
Tools/Shared/pmp_wrap/Build-PmpWrap.ps1 (source: pmp_wrap/pmp_wrap.cpp, the toolkit's own code).
Neither the clone nor the DLL is in the repository. `available()` says whether the DLL is there;
PMPWRAP_DLL names another path.

Written against pmpwrap 1 = pmp-library 3.0.0 (clone 3.0.0-310-gfc0bfd7a), double precision.

pmp works on manifold surfaces: an edge with three faces, or a vertex where two separate fans of
faces touch, makes Mesh() raise. Vertices doubled along a UV seam are separate vertices to it,
so weld a mesh by position first when the surface should be whole (`weld`). Editing calls
(decimate, remesh, subdivide, fill_holes) change the vertex list: per-vertex data such as UVs
or skin does not come back from them and has to be carried over by position.
"""
import ctypes
import os

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT = os.path.join(_HERE, 'third_party', 'pmp-build', 'pmpwrap.dll')
_lib = None


def dll_path():
    return os.environ.get('PMPWRAP_DLL') or _DEFAULT


def available():
    return os.path.isfile(dll_path())


def _load():
    global _lib
    if _lib is None:
        if not available():
            raise FileNotFoundError(f'{dll_path()} not found; build it with Tools\\Shared\\pmp_wrap\\Build-PmpWrap.ps1')
        lib = ctypes.CDLL(dll_path())
        lib.pw_version.restype = ctypes.c_char_p
        lib.pw_last_error.restype = ctypes.c_char_p
        lib.pw_create.restype = ctypes.c_void_p
        lib.pw_create.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        lib.pw_free.argtypes = [ctypes.c_void_p]
        for name, extra in (('pw_counts', [ctypes.c_void_p, ctypes.c_void_p]), ('pw_get', [ctypes.c_void_p, ctypes.c_void_p]),
                            ('pw_get_uv', [ctypes.c_void_p]), ('pw_lscm', []), ('pw_harmonic', [ctypes.c_int]),
                            ('pw_decimate', [ctypes.c_uint, ctypes.c_double, ctypes.c_double, ctypes.c_uint, ctypes.c_double, ctypes.c_double]),
                            ('pw_remesh_uniform', [ctypes.c_double, ctypes.c_uint, ctypes.c_int]),
                            ('pw_remesh_adaptive', [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_uint, ctypes.c_int]),
                            ('pw_fill_holes', [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]),
                            ('pw_smooth', [ctypes.c_uint, ctypes.c_int]),
                            ('pw_smooth_implicit', [ctypes.c_double, ctypes.c_uint, ctypes.c_int, ctypes.c_int]),
                            ('pw_subdivide', [ctypes.c_int]), ('pw_triangulate', []), ('pw_components', [ctypes.c_void_p])):
            function = getattr(lib, name)
            function.restype = ctypes.c_int
            function.argtypes = [ctypes.c_void_p] + extra
        _lib = lib
    return _lib


def version():
    return _load().pw_version().decode()


def weld(vertices, triangles, decimals=6):
    """Vertices at one place become one. Returns (vertices, triangles, index of each old vertex in
    the new list); triangles that collapse are dropped."""
    vertices = np.asarray(vertices, dtype=np.float64)
    unique, inverse = np.unique(np.round(vertices, decimals), axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    merged = inverse[np.asarray(triangles, dtype=np.int64)]
    keep = (merged[:, 0] != merged[:, 1]) & (merged[:, 1] != merged[:, 2]) & (merged[:, 0] != merged[:, 2])
    return unique, merged[keep], inverse


class Mesh:
    def __init__(self, vertices, triangles):
        lib = _load()
        v = np.ascontiguousarray(vertices, dtype=np.float64)
        t = np.ascontiguousarray(triangles, dtype=np.int32)
        self._lib = lib
        self._handle = lib.pw_create(v.ctypes.data, len(v), t.ctypes.data, len(t))
        if not self._handle:
            raise ValueError('pmp: ' + lib.pw_last_error().decode())

    def close(self):
        if self._handle:
            self._lib.pw_free(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        self.close()

    def _call(self, name, *args):
        if getattr(self._lib, name)(self._handle, *args):
            raise RuntimeError(f'pmp {name[3:]}: ' + self._lib.pw_last_error().decode())

    def counts(self):
        nv, nf = ctypes.c_int(), ctypes.c_int()
        self._call('pw_counts', ctypes.byref(nv), ctypes.byref(nf))
        return nv.value, nf.value

    def arrays(self):
        """(vertices N x 3, triangles M x 3) as they are now."""
        nv, nf = self.counts()
        v, t = np.zeros((nv, 3)), np.zeros((nf, 3), dtype=np.int32)
        self._call('pw_get', v.ctypes.data, t.ctypes.data)
        return v, t.astype(np.int64)

    def _uv(self):
        uv = np.zeros((self.counts()[0], 2))
        self._call('pw_get_uv', uv.ctypes.data)
        return uv

    def lscm(self):
        """Least squares conformal map (keeps angles); N x 2. The mesh needs an open edge."""
        self._call('pw_lscm')
        return self._uv()

    def harmonic(self, uniform_weights=False):
        """Harmonic map onto a disc; N x 2. The mesh needs exactly one open edge loop."""
        self._call('pw_harmonic', int(uniform_weights))
        return self._uv()

    def decimate(self, target_vertices, aspect_ratio=0.0, edge_length=0.0, max_valence=0, normal_deviation=0.0, hausdorff_error=0.0):
        self._call('pw_decimate', int(target_vertices), aspect_ratio, edge_length, int(max_valence), normal_deviation, hausdorff_error)

    def remesh_uniform(self, edge_length, iterations=10, use_projection=True):
        self._call('pw_remesh_uniform', edge_length, int(iterations), int(use_projection))

    def remesh_adaptive(self, min_edge, max_edge, approx_error, iterations=10, use_projection=True):
        self._call('pw_remesh_adaptive', min_edge, max_edge, approx_error, int(iterations), int(use_projection))

    def fill_holes(self, max_edges=0):
        """Closes open edge loops (of at most max_edges edges; 0 = all). Returns (filled, left)."""
        filled, skipped = ctypes.c_int(), ctypes.c_int()
        self._call('pw_fill_holes', int(max_edges), ctypes.byref(filled), ctypes.byref(skipped))
        return filled.value, skipped.value

    def smooth(self, iterations=10, uniform_laplace=False):
        self._call('pw_smooth', int(iterations), int(uniform_laplace))

    def smooth_implicit(self, timestep=0.001, iterations=1, uniform_laplace=False, rescale=True):
        self._call('pw_smooth_implicit', timestep, int(iterations), int(uniform_laplace), int(rescale))

    def subdivide(self, kind='loop'):
        self._call('pw_subdivide', {'loop': 0, 'catmull-clark': 1, 'linear': 2}[kind])
        if kind != 'loop':
            self._call('pw_triangulate')

    def components(self):
        count = ctypes.c_int()
        self._call('pw_components', ctypes.byref(count))
        return count.value
