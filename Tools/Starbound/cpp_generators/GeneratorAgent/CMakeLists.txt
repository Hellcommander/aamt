# Image Generator Module CMakeLists.txt
# Enhanced Image Generator GUI with Spritesheet Support

cmake_minimum_required(VERSION 3.16)

# Vendor headers still live in the mod's cpp_backend; this module lives in Tools.
if(NOT DEFINED MAGITECH_CPP_BACKEND)
    set(MAGITECH_CPP_BACKEND "F:/Games/OpenStarbound/mods/Magi-Tech Arcane Alchemy and Sorcery/cpp_backend")
endif()

# Set module name
set(MODULE_NAME "ImageGenerator")
set(MODULE_DESCRIPTION "Enhanced Image Generator GUI with Spritesheet Support")

# Create library target
add_library(MagiTech${MODULE_NAME} STATIC)

# Set target properties
set_target_properties(MagiTech${MODULE_NAME} PROPERTIES
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
    POSITION_INDEPENDENT_CODE ON
)

# Source files
set(SOURCES
    ImageGenerator.cpp
    ImageGeneratorLuaBindings.cpp
    ImageAssembler.cpp
    ImageWriter.cpp
    SpritesheetAssembler.cpp
    Utils.cpp
)

# Header files
set(HEADERS
    ImageTypes.hpp
    ImageGenerator.hpp
    ImageGeneratorLuaBindings.hpp
    ImageAssembler.hpp
    ImageWriter.hpp
    SpritesheetAssembler.hpp
    Utils.hpp
)

# Add source files to target
target_sources(MagiTech${MODULE_NAME} PRIVATE ${SOURCES})

# Include directories
target_include_directories(MagiTech${MODULE_NAME} PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${MAGITECH_CPP_BACKEND}
    ${MAGITECH_CPP_BACKEND}/vendor
    ${MAGITECH_CPP_BACKEND}/vendor/glm
    ${MAGITECH_CPP_BACKEND}/vendor/xxhash
    ${MAGITECH_CPP_BACKEND}/vendor/sol3
    ${MAGITECH_CPP_BACKEND}/vendor/imgui
    ${MAGITECH_CPP_BACKEND}/vendor/stb
)

# Compiler definitions
target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE
    MAGITECH_IMAGE_GENERATOR_MODULE
    IMGUI_DISABLE_OBSOLETE_FUNCTIONS
    STB_IMAGE_IMPLEMENTATION
    STB_IMAGE_WRITE_IMPLEMENTATION
    STB_IMAGE_RESIZE_IMPLEMENTATION
)

# Dependencies
if (WIN32 AND NOT PKG_CONFIG_EXECUTABLE)
    # Inherit autodetection from parent if available, otherwise attempt local
    file(TO_CMAKE_PATH "D:\\pkg-config" MAGITECH_PKGCFG_ROOT)
    if (EXISTS "${MAGITECH_PKGCFG_ROOT}")
        foreach(_MAGITECH_PKGCFG_EXE IN ITEMS
            "${MAGITECH_PKGCFG_ROOT}/pkg-config.exe"
            "${MAGITECH_PKGCFG_ROOT}/bin/pkg-config.exe")
            if (EXISTS "${_MAGITECH_PKGCFG_EXE}")
                set(PKG_CONFIG_EXECUTABLE "${_MAGITECH_PKGCFG_EXE}" CACHE FILEPATH "Path to pkg-config executable" FORCE)
                break()
            endif()
        endforeach()
    endif()
endif()
find_package(PkgConfig REQUIRED)

# Core dependencies
target_link_libraries(MagiTech${MODULE_NAME} PUBLIC
    MagiTechCore
    MagiTechMechs
    MagiTechAudio
    MagiTechUtils
)

# External dependencies
if(TARGET imgui)
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE imgui)
else()
    # Fallback for when ImGui is not available as a target
    target_include_directories(MagiTech${MODULE_NAME} PRIVATE
        ${MAGITECH_CPP_BACKEND}/vendor/imgui
    )
endif()

# STB Image (header-only)
target_include_directories(MagiTech${MODULE_NAME} PRIVATE
    ${MAGITECH_CPP_BACKEND}/vendor/stb
)

# GLM (header-only)
target_include_directories(MagiTech${MODULE_NAME} PRIVATE
    ${MAGITECH_CPP_BACKEND}/vendor/glm
)

# XXHash
if(TARGET xxhash)
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE xxhash)
else()
    # Include xxhash headers
    target_include_directories(MagiTech${MODULE_NAME} PRIVATE
        ${MAGITECH_CPP_BACKEND}/vendor/xxhash
    )
endif()

# Sol3 (Lua bindings)
if(TARGET sol3)
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE sol3)
else()
    # Include sol3 headers
    target_include_directories(MagiTech${MODULE_NAME} PRIVATE
        ${MAGITECH_CPP_BACKEND}/vendor/sol3
    )
endif()

# Platform-specific settings
if(WIN32)
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE
        WIN32_LEAN_AND_MEAN
        NOMINMAX
        _CRT_SECURE_NO_WARNINGS
    )
    
    # Windows-specific libraries
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE
        opengl32
        gdi32
        user32
        kernel32
    )
elseif(UNIX AND NOT APPLE)
    # Linux-specific libraries
    find_package(OpenGL REQUIRED)
    find_package(X11 REQUIRED)
    
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE
        OpenGL::GL
        X11
        Xrandr
        Xinerama
        Xcursor
        m
        dl
    )
elseif(APPLE)
    # macOS-specific libraries
    find_package(OpenGL REQUIRED)
    
    target_link_libraries(MagiTech${MODULE_NAME} PRIVATE
        OpenGL::GL
        "-framework Cocoa"
        "-framework IOKit"
        "-framework CoreVideo"
    )
endif()

# Compiler-specific settings
if(MSVC)
    target_compile_options(MagiTech${MODULE_NAME} PRIVATE
        /W4
        /wd4201  # nonstandard extension used: nameless struct/union
        /wd4100  # unreferenced formal parameter
        /wd4505  # unreferenced local function has been removed
    )
else()
    target_compile_options(MagiTech${MODULE_NAME} PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wno-unused-parameter
        -Wno-unused-variable
    )
endif()

# Installation
install(TARGETS MagiTech${MODULE_NAME}
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(FILES ${HEADERS}
    DESTINATION include/MagiTech/ImageGen
)

# Documentation
install(FILES README.md
    DESTINATION share/doc/MagiTech/ImageGen
)

# Module registration
set(MODULE_TARGET "MagiTech${MODULE_NAME}" PARENT_SCOPE)
set(MODULE_DESCRIPTION "${MODULE_DESCRIPTION}" PARENT_SCOPE)

# Export target for other modules
export(TARGETS MagiTech${MODULE_NAME} FILE MagiTech${MODULE_NAME}Targets.cmake)

# Create config file
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/MagiTech${MODULE_NAME}Config.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/MagiTech${MODULE_NAME}Config.cmake"
    @ONLY
)

# Install config files
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/MagiTech${MODULE_NAME}Config.cmake"
    DESTINATION lib/cmake/MagiTech${MODULE_NAME}
)

install(EXPORT MagiTech${MODULE_NAME}Targets
    FILE MagiTech${MODULE_NAME}Targets.cmake
    NAMESPACE MagiTech::
    DESTINATION lib/cmake/MagiTech${MODULE_NAME}
)

# Testing (if enabled)
if(BUILD_TESTING)
    enable_testing()
    
    # Add test executable
    add_executable(MagiTech${MODULE_NAME}Tests
        tests/ImageGeneratorTests.cpp
        tests/ImageAssemblerTests.cpp
        tests/ImageWriterTests.cpp
        tests/SpritesheetAssemblerTests.cpp
        tests/UtilsTests.cpp
    )
    
    target_link_libraries(MagiTech${MODULE_NAME}Tests PRIVATE
        MagiTech${MODULE_NAME}
        gtest
        gtest_main
    )
    
    # Add tests
    add_test(NAME ImageGeneratorTests COMMAND MagiTech${MODULE_NAME}Tests)
    add_test(NAME ImageAssemblerTests COMMAND MagiTech${MODULE_NAME}Tests --gtest_filter=ImageAssembler*)
    add_test(NAME ImageWriterTests COMMAND MagiTech${MODULE_NAME}Tests --gtest_filter=ImageWriter*)
    add_test(NAME SpritesheetAssemblerTests COMMAND MagiTech${MODULE_NAME}Tests --gtest_filter=SpritesheetAssembler*)
    add_test(NAME UtilsTests COMMAND MagiTech${MODULE_NAME}Tests --gtest_filter=Utils*)
endif()

# Print module info
message(STATUS "Configuring ${MODULE_NAME} module: ${MODULE_DESCRIPTION}")
message(STATUS "  - Sources: ${SOURCES}")
message(STATUS "  - Headers: ${HEADERS}")
message(STATUS "  - Target: MagiTech${MODULE_NAME}")

# Module-specific configuration
option(ENABLE_IMAGE_GENERATOR_GPU_ACCELERATION "Enable GPU acceleration for image generation" ON)
option(ENABLE_IMAGE_GENERATOR_ASYNC_PROCESSING "Enable async processing for image generation" ON)
option(ENABLE_IMAGE_GENERATOR_CACHING "Enable caching for image generation" ON)
option(ENABLE_IMAGE_GENERATOR_HOT_RELOAD "Enable hot reload for image generation" OFF)

if(ENABLE_IMAGE_GENERATOR_GPU_ACCELERATION)
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE MAGITECH_IMAGE_GENERATOR_GPU_ACCELERATION)
    message(STATUS "  - GPU acceleration: ENABLED")
else()
    message(STATUS "  - GPU acceleration: DISABLED")
endif()

if(ENABLE_IMAGE_GENERATOR_ASYNC_PROCESSING)
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE MAGITECH_IMAGE_GENERATOR_ASYNC_PROCESSING)
    message(STATUS "  - Async processing: ENABLED")
else()
    message(STATUS "  - Async processing: DISABLED")
endif()

if(ENABLE_IMAGE_GENERATOR_CACHING)
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE MAGITECH_IMAGE_GENERATOR_CACHING)
    message(STATUS "  - Caching: ENABLED")
else()
    message(STATUS "  - Caching: DISABLED")
endif()

if(ENABLE_IMAGE_GENERATOR_HOT_RELOAD)
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE MAGITECH_IMAGE_GENERATOR_HOT_RELOAD)
    message(STATUS "  - Hot reload: ENABLED")
else()
    message(STATUS "  - Hot reload: DISABLED")
endif()

# Performance optimization flags
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE
        MAGITECH_IMAGE_GENERATOR_RELEASE
        NDEBUG
    )
    
    if(MSVC)
        target_compile_options(MagiTech${MODULE_NAME} PRIVATE /O2)
    else()
        target_compile_options(MagiTech${MODULE_NAME} PRIVATE -O3)
    endif()
    
    message(STATUS "  - Release mode optimizations: ENABLED")
elseif(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_definitions(MagiTech${MODULE_NAME} PRIVATE
        MAGITECH_IMAGE_GENERATOR_DEBUG
        _DEBUG
    )
    
    message(STATUS "  - Debug mode: ENABLED")
endif()

# Module registration for parent scope
set(MAGITECH_IMAGE_GENERATOR_MODULE TRUE PARENT_SCOPE)
set(MAGITECH_IMAGE_GENERATOR_TARGET "MagiTech${MODULE_NAME}" PARENT_SCOPE) 