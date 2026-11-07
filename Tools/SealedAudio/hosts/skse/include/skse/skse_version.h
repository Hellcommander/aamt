#pragma once

#define SKSE_VERSION_INTEGER 2
#define SKSE_VERSION_INTEGER_MINOR 3
#define SKSE_VERSION_INTEGER_BETA 1

#define MAKE_EXE_VERSION_EX(major, minor, build, sub) \
	((((major) & 0xFF) << 24) | (((minor) & 0xFF) << 16) | (((build) & 0xFFF) << 4) | ((sub) & 0xF))
#define MAKE_EXE_VERSION(major, minor, build) MAKE_EXE_VERSION_EX(major, minor, build, 0)
#define MAKE_EXE_VR_VERSION(major, minor, build) MAKE_EXE_VERSION_EX(major, minor, build, 1)

#define GET_EXE_VERSION_MAJOR(a) (((a) & 0xFF000000) >> 24)
#define GET_EXE_VERSION_MINOR(a) (((a) & 0x00FF0000) >> 16)
#define GET_EXE_VERSION_BUILD(a) (((a) & 0x0000FFF0) >> 4)
#define GET_EXE_VERSION_SUB(a) (((a) & 0x0000000F) >> 0)

#define RUNTIME_VERSION_1_7_104 MAKE_EXE_VERSION(1, 7, 104)
#define RUNTIME_VR_VERSION_1_4_15 MAKE_EXE_VR_VERSION(1, 4, 15)
#define PACKED_SKSE_VERSION MAKE_EXE_VERSION(SKSE_VERSION_INTEGER, SKSE_VERSION_INTEGER_MINOR, SKSE_VERSION_INTEGER_BETA)
#define CURRENT_RELEASE_RUNTIME RUNTIME_VERSION_1_7_104
