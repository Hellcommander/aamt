#!/usr/bin/env python3
"""Patch LibJPEGTurboUtil + CSimViewer + Transcendence.sln for Contributors builds.

Also syncs Steamworks SDK (headers + steam_api64) and enables Steam Multiverse
fallback for contributor builds that lack HexarcKeys.h.

Does not touch an 'official' tree unless you point --api-root at it.
Prefer running against an x64 build workspace.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

DEFAULT_API = Path(
    r"D:\games\Steam\steamapps\common\Transcendence"
    r"\game_and_dlc_source\TranscendenceDev-integration-API59"
)

API: Path = DEFAULT_API


def patch_jpeg() -> None:
    p = API / "Alchemy" / "LibJPEGTurboUtil" / "LibJPEGTurboUtil.vcxproj"
    text = p.read_text(encoding="utf-8")
    if "Debug For Contributors|x64" in text:
        print("LibJPEGTurboUtil: Contributors configs already present")
        return

    # Add project configurations
    old_cfgs = """  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Debug|Win32">
      <Configuration>Debug</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|Win32">
      <Configuration>Release</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Debug|x64">
      <Configuration>Debug</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>"""

    new_cfgs = """  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Debug|Win32">
      <Configuration>Debug</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Debug For Contributors|Win32">
      <Configuration>Debug For Contributors</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|Win32">
      <Configuration>Release</Configuration>
      <Platform>Win32</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Debug|x64">
      <Configuration>Debug</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Debug For Contributors|x64">
      <Configuration>Debug For Contributors</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>"""
    if old_cfgs not in text:
        raise SystemExit("LibJPEGTurboUtil: ProjectConfigurations block mismatch")
    text = text.replace(old_cfgs, new_cfgs, 1)

    # After Debug|Win32 Configuration PropertyGroup, clone Contributors
    win32_debug_cfg = """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>"""
    win32_contrib_cfg = """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|Win32'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>"""
    text = text.replace(win32_debug_cfg, win32_contrib_cfg, 1)

    x64_debug_cfg = """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>"""
    x64_contrib_cfg = """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|x64'" Label="Configuration">
    <ConfigurationType>StaticLibrary</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>NotSet</CharacterSet>
  </PropertyGroup>"""
    text = text.replace(x64_debug_cfg, x64_contrib_cfg, 1)

    # Property sheets
    text = text.replace(
        """  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>""",
        """  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|Win32'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>""",
        1,
    )
    text = text.replace(
        """  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>""",
        """  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|x64'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>""",
        1,
    )

    # Fix x64 OutDir collision + Contributors dirs: put libs in project root so
    # Transcendence AdditionalLibraryDirectories (..\\..\\Alchemy\\LibJPEGTurboUtil) works.
    text = text.replace(
        """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <LinkIncremental>true</LinkIncremental>
    <OutDir>.\\Debug\\</OutDir>
    <IntDir>.\\Debug\\</IntDir>
  </PropertyGroup>""",
        """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'">
    <LinkIncremental>true</LinkIncremental>
    <OutDir>.\\</OutDir>
    <IntDir>.\\Debug\\</IntDir>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|Win32'">
    <LinkIncremental>true</LinkIncremental>
    <OutDir>.\\</OutDir>
    <IntDir>.\\Debug\\</IntDir>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'">
    <LinkIncremental>true</LinkIncremental>
    <OutDir>.\\</OutDir>
    <IntDir>.\\x64\\Debug\\</IntDir>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug For Contributors|x64'">
    <LinkIncremental>true</LinkIncremental>
    <OutDir>.\\</OutDir>
    <IntDir>.\\x64\\Debug\\</IntDir>
  </PropertyGroup>""",
        1,
    )
    # Remove duplicate Debug|Win32 LinkIncremental-only group if still present later
    text = text.replace(
        """  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|Win32'">
    <LinkIncremental>true</LinkIncremental>
  </PropertyGroup>
""",
        "",
        1,
    )

    # Clone ItemDefinitionGroups for Contributors from Debug
    for plat in ("Win32", "x64"):
        needle = f"Condition=\"'$(Configuration)|$(Platform)'=='Debug|{plat}'\""
        contrib = f"Condition=\"'$(Configuration)|$(Platform)'=='Debug For Contributors|{plat}'\""
        # Find ItemDefinitionGroup for Debug|plat and duplicate
        start = text.find(f"<ItemDefinitionGroup {needle}>")
        if start < 0:
            raise SystemExit(f"missing ItemDefinitionGroup Debug|{plat}")
        end = text.find("</ItemDefinitionGroup>", start)
        end = end + len("</ItemDefinitionGroup>")
        block = text[start:end]
        if contrib in text:
            continue
        clone = block.replace(needle, contrib)
        text = text[:end] + "\n" + clone + text[end:]

    p.write_text(text, encoding="utf-8")
    print(f"patched {p}")


def patch_sln() -> None:
    p = API / "Transcendence" / "Transcendence.sln"
    text = p.read_text(encoding="utf-8")
    changed = False

    # JPEG Contributors must map to Contributors configs, not Debug
    if "Debug For Contributors|Win32.Build.0" in text and "Debug For Contributors|Win32.ActiveCfg = Debug For Contributors|Win32" in text:
        print("sln: Contributors Build.0 already OK")
    else:
        text2 = text.replace(
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|Win32.ActiveCfg = Debug|Win32\n",
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|Win32.ActiveCfg = Debug For Contributors|Win32\n"
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|Win32.Build.0 = Debug For Contributors|Win32\n",
            1,
        )
        text2 = text2.replace(
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|x64.ActiveCfg = Debug|x64\n"
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|x64.Build.0 = Debug|x64\n",
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|x64.ActiveCfg = Debug For Contributors|x64\n"
            "\t\t{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}.Debug For Contributors|x64.Build.0 = Debug For Contributors|x64\n",
            1,
        )
        if text2 != text:
            text = text2
            changed = True
            print("sln: JPEG Contributors ActiveCfg fixed")

    # zlib Steam*|x64 wrongly maps to Address Sanitizer (breaks asm link)
    for guid, rel, dbg in (
        ("{910B3EA2-DB1B-4F5D-B3C5-9AB1B600936B}", "Release|x64", "Debug|x64"),
        ("{674CF44A-E652-48D2-8D5A-52BC1F280534}", "Release|x64", "Debug|x64"),
    ):
        pairs = (
            (
                f"\t\t{guid}.SteamRelease|x64.ActiveCfg = Debug with Address Sanitizer|x64\n",
                f"\t\t{guid}.SteamRelease|x64.ActiveCfg = {rel}\n"
                f"\t\t{guid}.SteamRelease|x64.Build.0 = {rel}\n",
            ),
            (
                f"\t\t{guid}.SteamDebug|x64.ActiveCfg = Debug with Address Sanitizer|x64\n",
                f"\t\t{guid}.SteamDebug|x64.ActiveCfg = {dbg}\n"
                f"\t\t{guid}.SteamDebug|x64.Build.0 = {dbg}\n",
            ),
        )
        for old, new in pairs:
            if old in text:
                text = text.replace(old, new, 1)
                changed = True
                print(f"sln: fixed zlib Steam mapping {guid[:9]}...")

    if changed:
        p.write_text(text, encoding="utf-8", newline="\r\n")
        print(f"patched {p}")
    else:
        print("sln: no further changes")


MARKER_STEAM_FALLBACK = "TX_MULTIVERSE_STEAM_FALLBACK"
MARKER_STEAM_SDK165 = "TX_STEAMWORKS_SDK_165"
DEFAULT_STEAMWORKS_SDK = Path(r"E:\sdks\steamworks_sdk_165\sdk")


def _resolve_steamworks_sdk(cli_path: str | None) -> Path | None:
    candidates = []
    if cli_path:
        candidates.append(Path(cli_path))
    env = os.environ.get("TX_STEAMWORKS_SDK", "").strip()
    if env:
        candidates.append(Path(env))
    candidates.append(DEFAULT_STEAMWORKS_SDK)
    for p in candidates:
        root = p.resolve()
        if (root / "public" / "steam" / "steam_api.h").is_file() and (
            root / "redistributable_bin" / "win64" / "steam_api64.lib"
        ).is_file():
            return root
    return None


def patch_steamworks_sdk_x64(sdk_root: Path | None) -> None:
    """Sync Steamworks SDK 1.65+ headers/libs into SteamUtil for x64 Multiverse."""
    if sdk_root is None:
        print("Steamworks SDK: not found (set --steamworks-sdk or TX_STEAMWORKS_SDK)")
        print("  expected: <sdk>/public/steam/steam_api.h and redistributable_bin/win64/steam_api64.lib")
        return

    dest_steam = API / "Mammoth" / "SteamUtil" / "steam"
    dest_win64 = dest_steam / "lib" / "win64"
    dest_win32 = dest_steam / "lib" / "win32"
    marker = API / ".steamworks_sdk_synced"
    stamp = f"{MARKER_STEAM_SDK165}|{sdk_root}"
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == stamp:
        # Still refresh libs if missing (deploy path)
        if (dest_win64 / "steam_api64.lib").is_file() and (dest_steam / "steam_api_common.h").is_file():
            print(f"Steamworks SDK: already synced from {sdk_root}")
            patch_steam_api_compat()
            return

    hdr_src = sdk_root / "public" / "steam"
    dest_steam.mkdir(parents=True, exist_ok=True)
    copied_h = 0
    for src in hdr_src.glob("*.h"):
        shutil.copy2(src, dest_steam / src.name)
        copied_h += 1
    # Optional companion files used by some tooling
    for name in ("steam_api.json",):
        s = hdr_src / name
        if s.is_file():
            shutil.copy2(s, dest_steam / name)

    dest_win64.mkdir(parents=True, exist_ok=True)
    for name in ("steam_api64.dll", "steam_api64.lib"):
        s = sdk_root / "redistributable_bin" / "win64" / name
        if not s.is_file():
            raise SystemExit(f"Steamworks SDK missing {s}")
        shutil.copy2(s, dest_win64 / name)

    dest_win32.mkdir(parents=True, exist_ok=True)
    for name in ("steam_api.dll", "steam_api.lib"):
        s = sdk_root / "redistributable_bin" / name
        if s.is_file():
            shutil.copy2(s, dest_win32 / name)

    marker.write_text(stamp + "\n", encoding="utf-8")
    print(f"Steamworks SDK: synced {copied_h} headers + win64 redistributables from {sdk_root}")
    patch_steam_api_compat()


def patch_steam_api_compat() -> None:
    """Adapt SteamUtil helpers to SDK 1.65+ (RequestCurrentStats removed)."""
    impl = API / "Mammoth" / "SteamUtil" / "SteamUtilImpl.h"
    text = impl.read_text(encoding="utf-8", errors="replace")
    if MARKER_STEAM_SDK165 in text:
        print("SteamUtilImpl.h: SDK 1.65 compat already")
        return

    old = """		bool Call ()
			{
			if (!SteamUserStats()->RequestCurrentStats())
				return false;

			while (!m_bComplete)
				{
				::Sleep(50);
				SteamAPI_RunCallbacks();
				}

			return true;
			}"""
    new = f"""		bool Call ()
			{{
			// {MARKER_STEAM_SDK165}: RequestCurrentStats removed in Steamworks 1.57+;
			// Steam syncs stats/achievements before process start.
			m_bComplete = true;
			return true;
			}}"""
    if old not in text:
        raise SystemExit("SteamUtilImpl.h: CRequestCurrentStats::Call block not found")
    impl.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("SteamUtilImpl.h: RequestCurrentStats -> no-op (SDK 1.65)")


def patch_steam_multiverse_fallback() -> None:
    """Contributor builds lack HexarcKeys.h, so Hexarc Create() is NULL and
    Multiverse login is disabled. Fall back to CSteamService + steam_api64.
    """
    ctrl = API / "Transcendence" / "Transcendence" / "CTranscendenceController.cpp"
    text = ctrl.read_text(encoding="utf-8", errors="replace")
    if MARKER_STEAM_FALLBACK in text:
        print("CTranscendenceController: Steam Multiverse fallback already")
    else:
        old_inc = """#ifdef STEAM_BUILD
#include "SteamUtil.h"
#endif
"""
        new_inc = f"""#include "SteamUtil.h" // {MARKER_STEAM_FALLBACK}
"""
        if old_inc not in text:
            raise SystemExit("CTranscendenceController: SteamUtil include block not found")
        text = text.replace(old_inc, new_inc, 1)

        old_svc = """#ifdef STEAM_BUILD
	m_Service.AddService(new CSteamService(m_HI));
#else
	CHexarcServiceFactory HexarcService;
	m_Service.AddService(HexarcService.Create(m_HI));
#endif
"""
        new_svc = f"""#ifdef STEAM_BUILD
	m_Service.AddService(new CSteamService(m_HI));
#else
	// {MARKER_STEAM_FALLBACK}: Hexarc stub returns NULL without HexarcKeys.h
	CHexarcServiceFactory HexarcService;
	ICIService *pHexarc = HexarcService.Create(m_HI);
	if (pHexarc)
		m_Service.AddService(pHexarc);
	else
		m_Service.AddService(new CSteamService(m_HI));
#endif
"""
        if old_svc not in text:
            raise SystemExit("CTranscendenceController: service boot block not found")
        text = text.replace(old_svc, new_svc, 1)
        ctrl.write_text(text, encoding="utf-8")
        print(f"patched {ctrl.name}: Steam Multiverse fallback")

    # Link steam_api64 into SteamUtil for Contributors|x64 (and Preview|x64)
    su = API / "Mammoth" / "SteamUtil" / "SteamUtil.vcxproj"
    su_text = su.read_text(encoding="utf-8")
    # Only flip the steam_api64.lib block's Contributors|x64 exclusion
    marker = "steam\\lib\\win64\\steam_api64.lib"
    idx = su_text.find(marker)
    if idx < 0:
        raise SystemExit("SteamUtil.vcxproj: steam_api64.lib block missing")
    # Find Contributors|x64 exclusion after this Library Include
    block_end = su_text.find("</Library>", idx)
    block = su_text[idx:block_end]
    if "Debug For Contributors|x64\">false</ExcludedFromBuild>" in block:
        print("SteamUtil: steam_api64 already enabled for Contributors|x64")
    else:
        target = (
            "<ExcludedFromBuild Condition=\"'$(Configuration)|$(Platform)'=="
            "'Debug For Contributors|x64'\">true</ExcludedFromBuild>"
        )
        repl = (
            "<ExcludedFromBuild Condition=\"'$(Configuration)|$(Platform)'=="
            "'Debug For Contributors|x64'\">false</ExcludedFromBuild>"
        )
        if target not in block:
            # Already flipped or format differs — treat as done if false present
            if "false</ExcludedFromBuild>" in block and "Debug For Contributors|x64" in block:
                print("SteamUtil: steam_api64 Contributors|x64 looks enabled")
            else:
                raise SystemExit("SteamUtil.vcxproj: Contributors|x64 exclusion not in steam_api64 block")
        else:
            new_block = block.replace(target, repl, 1)
            su_text = su_text[:idx] + new_block + su_text[block_end:]
            su.write_text(su_text, encoding="utf-8")
            print("SteamUtil: enabled steam_api64.lib for Contributors|x64")

    # Ensure final exe also links steam_api64 (static-lib Library items don't always propagate)
    tx = API / "Transcendence" / "Transcendence" / "Transcendence.vcxproj"
    tx_text = tx.read_text(encoding="utf-8")
    steam_dep = r"..\..\Mammoth\SteamUtil\steam\lib\win64\steam_api64.lib"
    needle = (
        "<ItemDefinitionGroup Condition=\"'$(Configuration)|$(Platform)'=="
        "'Debug For Contributors|x64'\">"
    )
    if needle not in tx_text:
        raise SystemExit("Transcendence.vcxproj: Contributors|x64 group missing")
    start = tx_text.find(needle)
    end = tx_text.find("</ItemDefinitionGroup>", start)
    group = tx_text[start:end]
    if steam_dep in group:
        print("Transcendence.vcxproj: steam_api64 already in Contributors|x64 link")
    else:
        old_link = (
            "<AdditionalDependencies>turbojpeg.lib;winhttp.lib; version.lib;"
            "vfw32.lib;winmm.lib;dsound.lib;odbc32.lib;odbccp32.lib;ws2_32.lib;"
            "%(AdditionalDependencies)</AdditionalDependencies>"
        )
        if old_link not in group:
            old_link = (
                "<AdditionalDependencies>winhttp.lib; version.lib;vfw32.lib;"
                "winmm.lib;dsound.lib;odbc32.lib;odbccp32.lib;ws2_32.lib;"
                "%(AdditionalDependencies)</AdditionalDependencies>"
            )
            if old_link not in group:
                raise SystemExit("Transcendence.vcxproj: Contributors|x64 AdditionalDependencies not found")
            new_link = (
                f"<AdditionalDependencies>{steam_dep};winhttp.lib; version.lib;"
                "vfw32.lib;winmm.lib;dsound.lib;odbc32.lib;odbccp32.lib;ws2_32.lib;"
                f"%(AdditionalDependencies)</AdditionalDependencies><!-- {MARKER_STEAM_FALLBACK} -->"
            )
        else:
            new_link = (
                f"<AdditionalDependencies>{steam_dep};turbojpeg.lib;winhttp.lib; version.lib;"
                "vfw32.lib;winmm.lib;dsound.lib;odbc32.lib;odbccp32.lib;ws2_32.lib;"
                f"%(AdditionalDependencies)</AdditionalDependencies><!-- {MARKER_STEAM_FALLBACK} -->"
            )
        new_group = group.replace(old_link, new_link, 1)
        tx_text = tx_text[:start] + new_group + tx_text[end:]
        tx.write_text(tx_text, encoding="utf-8")
        print("Transcendence.vcxproj: linked steam_api64 for Contributors|x64")

def patch_csimviewer() -> None:
    cpp = API / "Transcendence" / "TransData" / "CSimViewer.cpp"
    hdr = API / "Transcendence" / "TransData" / "Utilities.h"
    for p in (cpp, hdr):
        t = p.read_text(encoding="utf-8", errors="replace")
        if "GWLP_USERDATA" in t and "LRESULT APIENTRY" in t:
            print(f"already fixed: {p.name}")
            continue
        t = t.replace(
            "static LONG APIENTRY WndProc (HWND hWnd, UINT message, UINT wParam, LONG lParam);",
            "static LRESULT APIENTRY WndProc (HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam);",
        )
        t = t.replace(
            "LONG APIENTRY CSimViewer::WndProc (HWND hWnd, UINT message, UINT wParam, LONG lParam)",
            "LRESULT APIENTRY CSimViewer::WndProc (HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)",
        )
        t = t.replace(
            "::SetWindowLong(hWnd, GWL_USERDATA, (LONG)pViewer);",
            "::SetWindowLongPtr(hWnd, GWLP_USERDATA, (LONG_PTR)pViewer);",
        )
        t = t.replace(
            "CSimViewer *pViewer = (CSimViewer *)::GetWindowLong(hWnd, GWL_USERDATA);",
            "CSimViewer *pViewer = (CSimViewer *)::GetWindowLongPtr(hWnd, GWLP_USERDATA);",
        )
        # cast of lParam for CREATESTRUCT is fine with LPARAM
        p.write_text(t, encoding="utf-8")
        print(f"patched {p}")


def main() -> None:
    global API
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-root", default=str(DEFAULT_API))
    ap.add_argument("--steamworks-sdk", default="", help="Path to Steamworks SDK root (…/sdk)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args, _ = ap.parse_known_args()
    API = Path(args.api_root).resolve()
    if args.dry_run:
        print(f"[DryRun] would patch projects under {API}")
        return
    print(f"api-root: {API}")
    patch_jpeg()
    patch_sln()
    patch_csimviewer()
    sdk = _resolve_steamworks_sdk(args.steamworks_sdk or None)
    patch_steamworks_sdk_x64(sdk)
    patch_steam_multiverse_fallback()
    print("OK")
    print("NOTE: Hexarc Multiverse needs proprietary HexarcKeys.h (not in source).")
    print("      Contributors builds fall back to Steam Multiverse (steam_api64.dll + launch via Steam).")


if __name__ == "__main__":
    main()
