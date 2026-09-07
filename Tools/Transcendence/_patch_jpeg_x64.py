#!/usr/bin/env python3
from pathlib import Path

vcx = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source"
    r"\TranscendenceDev-integration-API59\Transcendence\Transcendence\Transcendence.vcxproj"
)
t = vcx.read_text(encoding="utf-8")

# Drop IntelJPEG ProjectReference entirely from the game exe project; use turbo only.
import re

t2, n = re.subn(
    r"\s*<ProjectReference Include=\"\.\.\\\.\\Alchemy\\IntelJPEGUtil\\IntelJPEGUtil\.vcxproj\"[^>]*>[\s\S]*?</ProjectReference>\s*",
    "\n",
    t,
    count=1,
)
print("removed intel refs", n)

# Ensure LibJPEGTurbo reference exists without Condition
if "LibJPEGTurboUtil.vcxproj" not in t2:
    raise SystemExit("missing LibJPEGTurbo reference")

t2 = t2.replace(
    '<ProjectReference Include="..\\..\\Alchemy\\LibJPEGTurboUtil\\LibJPEGTurboUtil.vcxproj" Condition="\'$(Platform)\'==\'x64\'">',
    '<ProjectReference Include="..\\..\\Alchemy\\LibJPEGTurboUtil\\LibJPEGTurboUtil.vcxproj">',
)

# Patch Debug For Contributors|x64 Link deps
marker = "Condition=\"'$(Configuration)|$(Platform)'=='Debug For Contributors|x64'\""
i = t2.find(marker)
if i < 0:
    raise SystemExit("no x64 contributors group")
j = t2.find("<AdditionalDependencies>winhttp.lib;", i)
k = t2.find("</AdditionalDependencies>", j)
if j < 0 or k < 0 or j - i > 2500:
    # maybe already patched
    j = t2.find("<AdditionalDependencies>turbojpeg.lib;winhttp.lib;", i)
    print("deps already?", j > 0)
else:
    t2 = (
        t2[:j]
        + "<AdditionalDependencies>turbojpeg.lib;winhttp.lib;"
        + t2[j + len("<AdditionalDependencies>winhttp.lib;") :]
    )
    k = t2.find("</AdditionalDependencies>", j)
    insert = (
        "\n      <AdditionalLibraryDirectories>"
        "..\\..\\Alchemy\\LibJPEGTurboUtil;%(AdditionalLibraryDirectories)"
        "</AdditionalLibraryDirectories>"
    )
    if "LibJPEGTurboUtil;%(AdditionalLibraryDirectories)" not in t2[j : j + 600]:
        t2 = t2[: k + len("</AdditionalDependencies>")] + insert + t2[k + len("</AdditionalDependencies>") :]
    print("patched link deps")

vcx.write_text(t2, encoding="utf-8")

stale = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\game_and_dlc_source"
    r"\TranscendenceDev-integration-API59\Transcendence\x64\Debug For Contributors\IntelJPEGUtil.lib"
)
if stale.exists():
    stale.unlink()
    print("deleted stale", stale)
print("ok")
