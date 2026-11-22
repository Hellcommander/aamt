# pmpwrap.dll: pmp-library (MIT, not in this repository) behind a plain C interface.
# Configure with -DPMP_ROOT=<clone of pmp-library>; see Build-PmpWrap.ps1.
cmake_minimum_required(VERSION 3.20)
project(pmpwrap LANGUAGES C CXX)

set(PMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/pmp-library" CACHE PATH "pmp-library clone")
if(NOT EXISTS "${PMP_ROOT}/src/pmp/surface_mesh.h")
  message(FATAL_ERROR "pmp-library not found in ${PMP_ROOT}; clone https://github.com/pmp-library/pmp-library there")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "")

# Only the library: no viewers (GLFW, ImGui), examples or tests; static, so the DLL stands alone.
set(PMP_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(PMP_BUILD_VIEWERS OFF CACHE BOOL "" FORCE)
set(PMP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PMP_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(PMP_STRICT_COMPILATION OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
# pmp's install rules do not work for a static build (its object library is in no export set),
# and they are also where it adds its include paths, so those are given here instead.
set(PMP_INSTALL OFF CACHE BOOL "" FORCE)
include_directories(SYSTEM "${PMP_ROOT}/external/eigen-5.0.1" "${PMP_ROOT}/src")
add_compile_definitions(PMP_SCALAR_TYPE_64 _USE_MATH_DEFINES NOMINMAX)

add_subdirectory("${PMP_ROOT}" pmp-library EXCLUDE_FROM_ALL)

add_library(pmpwrap SHARED pmp_wrap.cpp)
target_include_directories(pmpwrap PRIVATE "${PMP_ROOT}/src" "${PMP_ROOT}/external/eigen-5.0.1")
target_link_libraries(pmpwrap PRIVATE pmp)
