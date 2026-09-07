#!/usr/bin/env python3
"""Force JPEG backend to LibJPEGTurboUtil (x64-capable). Removes Intel IJL project refs."""
from __future__ import annotations

import re
import sys
from pathlib import Path

INTEL_GUID = "ECAC7E19-ACBC-4C3C-B89A-7BC7049B6F2E"
TURBO_GUID = "C68A844B-F08B-4913-BCFF-B607C7BC1F6D"


def fix_proj(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    orig = t
    t = re.sub(
        r"[ \t]*<ProjectReference Include=\"[^\"]*IntelJPEGUtil\.vcxproj\"[^>]*>\s*"
        r"<Project>\{ecac7e19-acbc-4c3c-b89a-7bc7049b6f2e\}</Project>\s*"
        r"</ProjectReference>\s*",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"[ \t]*<ProjectReference Include=\"[^\"]*LibJPEGTurboUtil\.vcxproj\"[^>]*>\s*"
        r"<Project>\{c68a844b-f08b-4913-bcff-b607c7bc1f6d\}</Project>\s*"
        r"</ProjectReference>\s*",
        "",
        t,
        flags=re.I,
    )
    turbo = (
        '    <ProjectReference Include="..\\..\\Alchemy\\LibJPEGTurboUtil\\LibJPEGTurboUtil.vcxproj">\n'
        "      <Project>{c68a844b-f08b-4913-bcff-b607c7bc1f6d}</Project>\n"
        "    </ProjectReference>\n"
    )
    if "LibJPEGTurboUtil.vcxproj" not in t:
        needle = 'Include="..\\..\\Alchemy\\Kernel\\Kernel.vcxproj"'
        alt = 'Include="..\\Kernel\\Kernel.vcxproj"'
        for n in (needle, alt):
            i = t.find(n)
            if i >= 0:
                line_start = t.rfind("\n", 0, i) + 1
                t = t[:line_start] + turbo + t[line_start:]
                break
        else:
            raise SystemExit(f"cannot insert LibJPEGTurboUtil into {path}")
    if t != orig:
        path.write_text(t, encoding="utf-8")
        print(f"updated {path}")


def fix_transcendence_link(path: Path) -> None:
    t = path.read_text(encoding="utf-8")
    pat = re.compile(
        r"(<ItemDefinitionGroup Condition=\"'\$\(Configuration\)\|\$\(Platform\)'=='Debug For Contributors\|x64'\">[\s\S]*?<Link>\s*)"
        r"<AdditionalDependencies>[^<]*</AdditionalDependencies>",
    )

    def repl(m: re.Match) -> str:
        deps = m.group(0)
        if "turbojpeg.lib" in deps:
            return deps
        return (
            m.group(1)
            + "<AdditionalDependencies>turbojpeg.lib;winhttp.lib; version.lib;vfw32.lib;"
            "winmm.lib;dsound.lib;odbc32.lib;odbccp32.lib;ws2_32.lib;%(AdditionalDependencies)"
            "</AdditionalDependencies>\n      <AdditionalLibraryDirectories>"
            r"..\..\Alchemy\LibJPEGTurboUtil;%(AdditionalLibraryDirectories)"
            "</AdditionalLibraryDirectories>"
        )

    t2, n = pat.subn(repl, t, count=1)
    if n and t2 != t:
        path.write_text(t2, encoding="utf-8")
        print("patched Transcendence x64 link deps")


def fix_sln(sln: Path) -> None:
    """Replace IntelJPEG solution deps with LibJPEGTurbo; do not build IntelJPEG on x64."""
    if not sln.is_file():
        return
    t = sln.read_text(encoding="utf-8")
    orig = t

    # Swap solution ProjectDependencies Intel -> Turbo
    t = t.replace(
        f"{{{INTEL_GUID}}} = {{{INTEL_GUID}}}",
        f"{{{TURBO_GUID}}} = {{{TURBO_GUID}}}",
    )
    # Also lowercase variants just in case
    t = re.sub(
        re.escape(f"{{{INTEL_GUID}}}"),
        f"{{{TURBO_GUID}}}",
        t,
        flags=re.I,
    )
    # Wait - that would also change the IntelJPEGUtil project definition GUID itself!
    # Restore the project definition line and config section carefully.
    # Re-read approach: only replace inside ProjectDependencies sections.

    t = orig  # reset
    def swap_deps(m: re.Match) -> str:
        body = m.group(0)
        body2 = re.sub(
            rf"\{{{INTEL_GUID}\}} = \{{{INTEL_GUID}\}}",
            f"{{{TURBO_GUID}}} = {{{TURBO_GUID}}}",
            body,
            flags=re.I,
        )
        # Avoid duplicate turbo lines
        lines = []
        seen = set()
        for line in body2.splitlines(keepends=True):
            key = line.strip().upper()
            if key in seen and TURBO_GUID.upper() in key:
                continue
            seen.add(key)
            lines.append(line)
        return "".join(lines)

    t = re.sub(
        r"ProjectSection\(ProjectDependencies\) = postProject.*?EndProjectSection",
        swap_deps,
        t,
        flags=re.S | re.I,
    )

    # Remove x64 Build.0 for IntelJPEGUtil so /t:Transcendence won't build/link it
    t2, n_build = re.subn(
        rf"\t\t\{{{INTEL_GUID}}}\.[^|\r\n]+\|x64\.Build\.0 = [^\r\n]+\r?\n",
        "",
        t,
        flags=re.I,
    )
    t = t2

    if t != orig:
        sln.write_text(t, encoding="utf-8")
        print(f"patched sln JPEG deps; removed {n_build} IntelJPEG x64 Build.0 lines")
    else:
        print("sln JPEG deps already ok")


def disable_intel_jpeg_x64(proj: Path) -> None:
    """Mark all x64 configs of IntelJPEGUtil as excluded from build via empty OutDir stay,
    but simpler: set ExcludeFromBuild for x64 ItemDefinitionGroups is awkward.
    Instead delete OutputFile targeting shared outdir by forcing a no-op — skip.
    Stale lib deletion + sln Build.0 removal is enough.
    """
    return


def main() -> int:
    api = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    if not api:
        print("usage: _force_jpeg_turbo_x64.py <api_root>", file=sys.stderr)
        return 2
    for rel in (
        "Transcendence/Transcendence/Transcendence.vcxproj",
        "Mammoth/TSE/TSE.vcxproj",
        "Mammoth/TSUI/TSUI.vcxproj",
    ):
        p = api / rel
        if p.is_file():
            fix_proj(p)
    tx = api / "Transcendence/Transcendence/Transcendence.vcxproj"
    if tx.is_file():
        fix_transcendence_link(tx)

    fix_sln(api / "Transcendence/Transcendence.sln")

    # Stale Intel IJL libs in shared x64 outdirs poison the link
    for stale in api.rglob("IntelJPEGUtil.lib"):
        try:
            stale.unlink()
            print(f"deleted stale {stale.relative_to(api)}")
        except OSError as e:
            print(f"warn: could not delete {stale}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
