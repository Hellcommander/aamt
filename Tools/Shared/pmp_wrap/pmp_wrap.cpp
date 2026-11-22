// pmpwrap: a plain C interface to the Polygon Mesh Processing Library, for Python (ctypes).
//
// pmp-library (https://github.com/pmp-library/pmp-library, MIT) is C++ with no Python binding.
// This file is the toolkit's own code; pmp-library itself is not in this repository: the build
// (Build-PmpWrap.ps1) compiles it from the clone in Tools/Shared/third_party/pmp-library and
// links it statically into pmpwrap.dll, which also stays outside the repository.
//
// Written against pmp-library 3.0.0 (clone at 3.0.0-310-gfc0bfd7a, Eigen 5.0.1 bundled), built
// with MSVC 19.5x (Build Tools 18) and CMake 4.5, scalar type double (PMP_SCALAR_TYPE_64).
//
// Every function that can fail returns 0 on success and 1 on failure; pw_last_error() then
// gives the reason. A mesh lives behind a handle from pw_create and is edited in place.

#include <pmp/surface_mesh.h>
#include <pmp/algorithms/decimation.h>
#include <pmp/algorithms/hole_filling.h>
#include <pmp/algorithms/parameterization.h>
#include <pmp/algorithms/remeshing.h>
#include <pmp/algorithms/smoothing.h>
#include <pmp/algorithms/subdivision.h>
#include <pmp/algorithms/triangulation.h>
#include <pmp/algorithms/utilities.h>

#include <exception>
#include <string>
#include <vector>

using namespace pmp;

#define API extern "C" __declspec(dllexport)

static thread_local std::string g_error;

template <class F>
static int guard(F&& f)
{
    try
    {
        f();
        return 0;
    }
    catch (const std::exception& e)
    {
        g_error = e.what();
    }
    catch (...)
    {
        g_error = "unknown error";
    }
    return 1;
}

static SurfaceMesh& mesh_of(void* handle)
{
    return *static_cast<SurfaceMesh*>(handle);
}

API const char* pw_version()
{
    return "pmpwrap 1 (pmp-library 3.0.0, double precision)";
}

API const char* pw_last_error()
{
    return g_error.c_str();
}

// vertices: nv x 3 doubles; triangles: nt x 3 vertex numbers. Returns null when the triangles do
// not form a manifold surface (an edge with three faces, a vertex touched by two fans).
API void* pw_create(const double* vertices, int nv, const int* triangles, int nt)
{
    auto* mesh = new SurfaceMesh();
    int failed = guard([&] {
        std::vector<Vertex> made;
        made.reserve(nv);
        for (int i = 0; i < nv; ++i)
            made.push_back(mesh->add_vertex(Point(vertices[3 * i], vertices[3 * i + 1], vertices[3 * i + 2])));
        for (int j = 0; j < nt; ++j)
            mesh->add_triangle(made[triangles[3 * j]], made[triangles[3 * j + 1]], made[triangles[3 * j + 2]]);
    });
    if (failed)
    {
        delete mesh;
        return nullptr;
    }
    return mesh;
}

API void pw_free(void* handle)
{
    delete static_cast<SurfaceMesh*>(handle);
}

// Removes deleted elements (so numbers run 0..n-1) and reports the sizes.
API int pw_counts(void* handle, int* nv, int* nf)
{
    return guard([&] {
        auto& mesh = mesh_of(handle);
        mesh.garbage_collection();
        *nv = static_cast<int>(mesh.n_vertices());
        *nf = static_cast<int>(mesh.n_faces());
    });
}

// Call pw_counts first. vertices: nv x 3, triangles: nf x 3. Fails on a face that is not a triangle.
API int pw_get(void* handle, double* vertices, int* triangles)
{
    return guard([&] {
        auto& mesh = mesh_of(handle);
        for (auto v : mesh.vertices())
        {
            const Point& p = mesh.position(v);
            vertices[3 * v.idx()] = p[0];
            vertices[3 * v.idx() + 1] = p[1];
            vertices[3 * v.idx() + 2] = p[2];
        }
        for (auto f : mesh.faces())
        {
            int corner = 0;
            for (auto v : mesh.vertices(f))
            {
                if (corner >= 3)
                    throw std::runtime_error("a face is not a triangle; call pw_triangulate first");
                triangles[3 * f.idx() + corner++] = static_cast<int>(v.idx());
            }
        }
    });
}

// uv: nv x 2, after pw_lscm or pw_harmonic.
API int pw_get_uv(void* handle, double* uv)
{
    return guard([&] {
        auto& mesh = mesh_of(handle);
        auto tex = mesh.get_vertex_property<TexCoord>("v:tex");
        if (!tex)
            throw std::runtime_error("the mesh has no texture coordinates; run a parameterization first");
        for (auto v : mesh.vertices())
        {
            uv[2 * v.idx()] = tex[v][0];
            uv[2 * v.idx() + 1] = tex[v][1];
        }
    });
}

// Least squares conformal map: angles kept as well as possible. Needs an open edge.
API int pw_lscm(void* handle)
{
    return guard([&] { lscm_parameterization(mesh_of(handle)); });
}

// Harmonic map onto a disc: the open edge is laid on a circle. Needs exactly one open edge loop.
API int pw_harmonic(void* handle, int uniform_weights)
{
    return guard([&] { harmonic_parameterization(mesh_of(handle), uniform_weights != 0); });
}

API int pw_decimate(void* handle, unsigned int target_vertices, double aspect_ratio, double edge_length,
                    unsigned int max_valence, double normal_deviation, double hausdorff_error)
{
    return guard([&] {
        decimate(mesh_of(handle), target_vertices, aspect_ratio, edge_length, max_valence, normal_deviation,
                 hausdorff_error);
    });
}

API int pw_remesh_uniform(void* handle, double edge_length, unsigned int iterations, int use_projection)
{
    return guard([&] { uniform_remeshing(mesh_of(handle), edge_length, iterations, use_projection != 0); });
}

API int pw_remesh_adaptive(void* handle, double min_edge, double max_edge, double approx_error,
                           unsigned int iterations, int use_projection)
{
    return guard([&] {
        adaptive_remeshing(mesh_of(handle), min_edge, max_edge, approx_error, iterations, use_projection != 0);
    });
}

// Closes open edge loops of at most max_edges edges (0: every loop). filled / skipped: how many
// loops were closed, and how many were left (too long, or pmp could not fill them).
API int pw_fill_holes(void* handle, int max_edges, int* filled, int* skipped)
{
    return guard([&] {
        auto& mesh = mesh_of(handle);
        *filled = 0;
        *skipped = 0;
        std::vector<Halfedge> loops;
        std::vector<int> sizes;
        std::vector<char> seen(mesh.halfedges_size(), 0);
        for (auto h : mesh.halfedges())
        {
            if (!mesh.is_boundary(h) || seen[h.idx()])
                continue;
            int count = 0;
            Halfedge at = h;
            do
            {
                seen[at.idx()] = 1;
                at = mesh.next_halfedge(at);
                ++count;
            } while (at != h && count < 10000000);
            loops.push_back(h);
            sizes.push_back(count);
        }
        for (size_t i = 0; i < loops.size(); ++i)
        {
            if (max_edges > 0 && sizes[i] > max_edges)
            {
                ++*skipped;
                continue;
            }
            try
            {
                fill_hole(mesh, loops[i]);
                ++*filled;
            }
            catch (const std::exception&)
            {
                ++*skipped;
            }
        }
    });
}

API int pw_smooth(void* handle, unsigned int iterations, int uniform_laplace)
{
    return guard([&] { explicit_smoothing(mesh_of(handle), iterations, uniform_laplace != 0); });
}

API int pw_smooth_implicit(void* handle, double timestep, unsigned int iterations, int uniform_laplace, int rescale)
{
    return guard([&] {
        implicit_smoothing(mesh_of(handle), timestep, iterations, uniform_laplace != 0, rescale != 0);
    });
}

// kind 0: Loop (triangles), 1: Catmull-Clark (gives quads; pw_triangulate after), 2: linear.
API int pw_subdivide(void* handle, int kind)
{
    return guard([&] {
        auto& mesh = mesh_of(handle);
        if (kind == 0)
            loop_subdivision(mesh);
        else if (kind == 1)
            catmull_clark_subdivision(mesh);
        else if (kind == 2)
            linear_subdivision(mesh);
        else
            throw std::runtime_error("unknown subdivision kind");
    });
}

API int pw_triangulate(void* handle)
{
    return guard([&] { triangulate(mesh_of(handle)); });
}

API int pw_components(void* handle, int* count)
{
    return guard([&] { *count = connected_components(mesh_of(handle)); });
}
