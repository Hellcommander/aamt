#!/usr/bin/env python3
"""
Fix-TranscendenceOptionalLibraries.py

Workspace overlay: optional <Library usage="optional"> entries must not disable
the parent extension when the library exists but is itself disabled.

Official Kronosaur trees stay clean. Idempotent via .optional_libraries_autofix_v1.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER_NAME = ".optional_libraries_autofix_v1"
TAG = "TX_OPTIONAL_LIB_AUTOFIX"

OLD_DISABLED = """\t\t//\tIf the library is disabled, then the extension is also disabled.

\t\telse if (pLibrary->IsDisabled())
\t\t\t{
\t\t\tpExtension->SetDisabled(strPatternSubst(CONSTLIT("Required library disabled: %s (%08x)"), pLibrary->GetName(), pLibrary->GetUNID()));
\t\t\tcontinue;
\t\t\t}
"""

NEW_DISABLED = """\t\t//\tIf the library is disabled, then the extension is also disabled.
\t\t//\tOptional libraries are skipped (same as missing) so EP-style bridge
\t\t//\taddons can load without Corporate Hierarchy / Near Stars.
\t\t//\t""" + TAG + """

\t\telse if (pLibrary->IsDisabled())
\t\t\t{
\t\t\tif (LibraryDesc.iUsage == CExtension::EUsage::optional)
\t\t\t\tcontinue;

\t\t\tpExtension->SetDisabled(strPatternSubst(CONSTLIT("Required library disabled: %s (%08x)"), pLibrary->GetName(), pLibrary->GetUNID()));
\t\t\tcontinue;
\t\t\t}
"""

OLD_DEPS = """\t\t//\tIf we have a dependency and the dependency is not found, then we do
\t\t//\tnot have all our dependencies.

\t\tif (LibraryDesc.iUsage == CExtension::EUsage::dependency
\t\t\t\t&& !FindBestExtension(LibraryDesc.dwUNID, LibraryDesc.dwRelease, dwFlags))
\t\t\treturn false;
"""

NEW_DEPS = """\t\t//\tIf we have a dependency and the dependency is not found, then we do
\t\t//\tnot have all our dependencies. A disabled library counts as missing
\t\t//\tso the extension is hidden instead of shown as an error.
\t\t//\t""" + TAG + """

\t\tif (LibraryDesc.iUsage == CExtension::EUsage::dependency)
\t\t\t{
\t\t\tCExtension *pLibrary;
\t\t\tif (!FindBestExtension(LibraryDesc.dwUNID, LibraryDesc.dwRelease, dwFlags, &pLibrary)
\t\t\t\t\t|| pLibrary->IsDisabled())
\t\t\t\treturn false;
\t\t\t}
"""


def patch_text(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    if TAG in text:
        notes.append("already patched")
        return text, notes
    if OLD_DISABLED not in text:
        notes.append("WARNING: disabled-library block not found")
    else:
        text = text.replace(OLD_DISABLED, NEW_DISABLED, 1)
        notes.append("skip disabled optional libraries")
    if OLD_DEPS not in text:
        notes.append("WARNING: HasDependencies block not found")
    else:
        text = text.replace(OLD_DEPS, NEW_DEPS, 1)
        notes.append("dependency treats disabled as missing")
    return text, notes


def main() -> None:
    ap = argparse.ArgumentParser(description="optional-library overlay (workspace)")
    ap.add_argument("api_root", nargs="?", default="")
    ap.add_argument("--api-root", dest="api_root_opt", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = Path(args.api_root_opt or args.api_root)
    if not root:
        raise SystemExit("api root required")
    marker = root / MARKER_NAME
    src = root / "Mammoth" / "TSE" / "CExtensionCollection.cpp"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    if marker.exists() and not args.force:
        print(f"optional-library autofix already applied ({marker.name}). Use --force to re-run.")
        return
    raw = src.read_text(encoding="utf-8", errors="replace")
    new, notes = patch_text(raw)
    print(f"{src}: {', '.join(notes)}")
    if args.dry_run or new == raw:
        return
    src.write_text(new, encoding="utf-8")
    marker.write_text("v1\n", encoding="utf-8")
    print(f"wrote {marker.name}")


if __name__ == "__main__":
    main()
