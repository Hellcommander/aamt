#!/usr/bin/env python3
"""
Fix-TranscendenceForkGaps.py - the engine changes the other fixers do not cover, so a clean upstream
TranscendenceDev tree (integration/API59 or master) can be built with the user's features and no fork.

Groups (all idempotent; each patch is skipped when its result is already present):

  features        sealed sound archive (Resources\\sounds.mtsa, SealedArchive.h overlay + generated SealedKey.h)
                  isBound TLisp primitive  (isBound 'symbol) -> True/Nil
  upstream-fixes  OPTIONAL fixes for upstream bugs, kept until an official fix lands:
                    CCAtomTable GetEntry INT_PTR (x64 compile error C2664)
                    ICCItem refcount / free-list link pointer-sized (x64 truncation)
                    CCodeChain::Lookup public (needed by isBound)
                    WndProc signatures LRESULT/WPARAM/LPARAM (x64 truncation of lParam)
                    TLisp object refs pointer-sized (sysFindObject lists, gPlayerShip, gSource: x64 crashes)
                    nebula CTile child-section pointer (save format unchanged), smart-pointer NULL compares
  diagnostics     OPTIONAL: native crashes inside TLisp primitives are logged with function/file/line
  build-config    LibJPEGTurboUtil (no PCH, link turbojpeg.lib), zlibstat static debug CRT,
                  TSUI Hexarc stub excludes for x64, Transcendence.sln Debug For Contributors mapping

Usage:
  python Fix-TranscendenceForkGaps.py --api-root <tree> [--skip upstream-fixes] [--only features] [--dry-run]
         [--seal-key <audio_seal.key>] [--force]

SealedKey.h is generated from the key with Tools\\Shared\\audio_seal.py and is never stored in the toolkit.
When the key is missing the sealed-sound feature is skipped (a tree with the include but no key would not build).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
OVERLAYS = HERE / "fork_overlays"
DEFAULT_KEY = TOOLS / "Shared" / "audio_seal.key"
SEAL_TOOL = TOOLS / "Shared" / "audio_seal.py"

GROUPS = ("features", "upstream-fixes", "diagnostics", "build-config")


class Tree:
    def __init__(self, root: Path, dry: bool):
        self.root = root
        self.dry = dry
        self.stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backed: set[Path] = set()
        self.log: list[str] = []
        self.errors: list[str] = []

    # text files keep their BOM and line endings
    def read(self, rel: str):
        p = self.root / rel
        if not p.exists():
            return None
        raw = p.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw[3:].decode("utf-8", errors="surrogateescape") if bom else raw.decode("utf-8", errors="surrogateescape")
        crlf = "\r\n" in text
        return text.replace("\r\n", "\n"), bom, crlf

    def write(self, rel: str, text: str, bom: bool, crlf: bool):
        p = self.root / rel
        if self.dry:
            return
        if p not in self.backed and p.exists():
            b = self.root / "_forkgaps_backups" / self.stamp / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, b)
            self.backed.add(p)
        out = text.replace("\n", "\r\n") if crlf else text
        data = out.encode("utf-8", errors="surrogateescape")
        p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)

    def edit(self, rel: str, name: str, fn):
        """fn(text) -> (new_text, status) where status is 'applied', 'present' or an error string."""
        got = self.read(rel)
        if got is None:
            self.errors.append(f"{name}: {rel} not found")
            return
        text, bom, crlf = got
        new, status = fn(text)
        if status == "applied":
            self.write(rel, new, bom, crlf)
            self.log.append(f"  + {name}  ({rel})")
        elif status == "present":
            self.log.append(f"  = {name}  (already present)")
        else:
            self.errors.append(f"{name}: {status}  ({rel})")


def insert_after(anchor: str, addition: str, marker: str):
    """Insert `addition` right after the first `anchor`; `marker` proves it is already there."""
    def fn(text: str):
        if marker in text:
            return text, "present"
        i = text.find(anchor)
        if i < 0:
            return text, f"anchor not found: {anchor[:60]!r}"
        j = i + len(anchor)
        return text[:j] + addition + text[j:], "applied"
    return fn


def replace_once(old: str, new: str, marker: str | None = None, count: int = 1):
    def fn(text: str):
        if (marker or new) in text and old not in text:
            return text, "present"
        n = text.count(old)
        if n == 0:
            return text, f"pattern not found: {old[:60]!r}"
        return text.replace(old, new, count if count > 0 else n), "applied"
    return fn


def regex_sub(pattern: str, repl: str, marker: str, flags=0):
    def fn(text: str):
        if re.search(marker, text, flags):
            return text, "present"
        new, n = re.subn(pattern, repl, text, flags=flags)
        if n == 0:
            return text, f"pattern not found: {pattern[:60]!r}"
        return new, "applied"
    return fn


def chain(*fns):
    def fn(text: str):
        statuses = []
        for f in fns:
            text, st = f(text)
            if st not in ("applied", "present"):
                return text, st
            statuses.append(st)
        return text, "applied" if "applied" in statuses else "present"
    return fn


# ---------------------------------------------------------------- features

LOAD_SEALED_SOUND = r'''
ALERROR CResourceDb::LoadSealedSound (CSoundMgr &SoundMgr, const CString &sFilespec, int *retiChannel)

//	LoadSealedSound
//
//	Loads a sound from the extension's sealed archive (Resources\sounds.mtsa, see SealedArchive.h), when it has one.
//	The archive is read and indexed once per resource db; entries are unsealed in memory as they are asked for.

	{
	ALERROR error;

	if (!m_bSealedChecked)
		{
		m_bSealedChecked = true;

		CString sArchive;
		bool bFound = false;
		if (m_bResourcesInDb && m_pDb)
			bFound = (ReadEntry(SEALED_SOUNDS_FILE, &sArchive) == NOERROR);
		else
			{
			CString sPath = pathAddComponent(m_sRoot, SEALED_SOUNDS_FILE);
			if (pathExists(sPath))
				{
				CFileReadBlock File(sPath);
				if (File.Open() == NOERROR)
					{
					sArchive = CString(File.GetPointer(0, File.GetLength()), File.GetLength());
					bFound = true;
					}
				}
			}

		if (bFound)
			{
			//	The extension's own key file, when it has one (an extension sealed with a key of its own).
			CString sModKey;
			if (m_bResourcesInDb && m_pDb)
				ReadEntry(SEALED_SOUNDS_KEY_FILE, &sModKey);
			else
				{
				CString sKeyPath = pathAddComponent(m_sRoot, SEALED_SOUNDS_KEY_FILE);
				if (pathExists(sKeyPath))
					{
					CFileReadBlock KeyFile(sKeyPath);
					if (KeyFile.Open() == NOERROR)
						sModKey = CString(KeyFile.GetPointer(0, KeyFile.GetLength()), KeyFile.GetLength());
					}
				}

			SealedArchive::CArchive *pArchive = new SealedArchive::CArchive;
			std::vector<unsigned char> bytes((const unsigned char *)sArchive.GetASCIIZPointer(), (const unsigned char *)sArchive.GetASCIIZPointer() + sArchive.GetLength());
			std::string sError;
			if (pArchive->Open(std::move(bytes), &sError, std::string(sModKey.GetASCIIZPointer(), sModKey.GetLength())))
				{
				m_pSealed = pArchive;
				::kernelDebugLogPattern("Sealed sound archive in %s: %d sounds", m_sRoot, (int)pArchive->GetCount());
				}
			else
				{
				::kernelDebugLogPattern("Sealed sound archive in %s unusable: %s", m_sRoot, CString(sError.c_str()));
				delete pArchive;
				}
			}
		}

	if (m_pSealed == NULL)
		return ERR_NOTFOUND;

	std::string sData;
	if (!((SealedArchive::CArchive *)m_pSealed)->Read(std::string(sFilespec.GetASCIIZPointer(), sFilespec.GetLength()), &sData))
		return ERR_NOTFOUND;

	CString sWave(sData.data(), (int)sData.size());
	CBufferReadBlock Data(sWave);
	if (error = Data.Open())
		return error;

	if (error = SoundMgr.LoadWaveFromBuffer(Data, retiChannel))
		return error;

	return NOERROR;
	}'''.lstrip("\n")


def feature_sealed_sounds(t: Tree, key: Path) -> None:
    overlay = OVERLAYS / "Mammoth" / "Include" / "SealedArchive.h"
    if not key.exists():
        t.log.append(f"  ! sealed-sounds skipped: key {key} not found (SealedKey.h cannot be generated)")
        return
    if not overlay.exists():
        t.errors.append(f"sealed-sounds: overlay {overlay} missing")
        return

    inc = t.root / "Mammoth" / "Include"
    dst = inc / "SealedArchive.h"
    if not dst.exists() or dst.read_bytes() != overlay.read_bytes():
        if not t.dry:
            shutil.copy2(overlay, dst)
        t.log.append("  + SealedArchive.h overlay  (Mammoth/Include)")
    else:
        t.log.append("  = SealedArchive.h overlay  (already present)")

    hdr = inc / "SealedKey.h"
    if not t.dry:
        r = subprocess.run([sys.executable, str(SEAL_TOOL), "write-cpp-key", str(hdr), "--key", str(key),
                            "--namespace", "SealedKey"], capture_output=True, text=True)
        if r.returncode != 0 or not hdr.exists():
            t.errors.append(f"sealed-sounds: write-cpp-key failed: {r.stderr.strip() or r.stdout.strip()}")
            return
    t.log.append("  + SealedKey.h generated from the seal key  (never commit it)")
    gi = t.root / ".gitignore"
    if gi.exists() and "SealedKey.h" not in gi.read_text(encoding="utf-8", errors="ignore"):
        if not t.dry:
            with gi.open("a", encoding="utf-8") as f:
                f.write("\n# generated by Fix-TranscendenceForkGaps.py from the private seal key\nMammoth/Include/SealedKey.h\n")
        t.log.append("  + .gitignore: Mammoth/Include/SealedKey.h")

    t.edit("Mammoth/Include/TSEResourceDb.h", "sealed-sounds: CResourceDb declarations", chain(
        insert_after("ALERROR LoadSound (CSoundMgr &SoundMgr, const CString &sFolder, const CString &sFilename, int *retiChannel);\n",
                     "\t\tALERROR LoadSealedSound (CSoundMgr &SoundMgr, const CString &sFilespec, int *retiChannel);\n",
                     "LoadSealedSound"),
        insert_after("CDataFile *m_pDb;\n",
                     "\t\tvoid *m_pSealed = NULL;\t\t\t\t\t//\tSealedArchive::CArchive once looked for (Resources\\sounds.mtsa)\n"
                     "\t\tbool m_bSealedChecked = false;\n",
                     "m_pSealed"),
    ))

    t.edit("Mammoth/TSE/CResourceDb.cpp", "sealed-sounds: CResourceDb::LoadSealedSound", chain(
        insert_after('#include "Zip.h"\n',
                     '#include "SealedArchive.h"\n\n'
                     '#define SEALED_SOUNDS_FILE\t\t\t\tCONSTLIT("Resources\\\\sounds.mtsa")\n'
                     '#define SEALED_SOUNDS_KEY_FILE\t\t\tCONSTLIT("Resources\\\\sounds.key")\n',
                     '#include "SealedArchive.h"'),
        insert_after("\tdelete m_pDb;\n",
                     "\tdelete (SealedArchive::CArchive *)m_pSealed;\n",
                     "delete (SealedArchive::CArchive *)m_pSealed;"),
        regex_sub(r"(\t\tCString sData;\n\t\tif \(error = ReadEntry\(sFilespec, &sData\)\)\n)\t\t\treturn error;\n(\n\t\tCBufferReadBlock Data\(sData\);\n\t\tif \(error = Data\.Open\(\)\)\n\t\t\treturn error;\n\n\t\tif \(error = SoundMgr\.LoadWaveFromBuffer)",
                  r"\1\t\t\t//\tNot in the TDB itself: the extension may carry it sealed.\n\t\t\treturn LoadSealedSound(SoundMgr, sFilespec, retiChannel);\n\2",
                  r"Not in the TDB itself: the extension may carry it sealed"),
        regex_sub(r"(\t\tsFilespec = pathAddComponent\(sFilespec, sFilename\);\n\n)(\t\tif \(error = SoundMgr\.LoadWaveFile\(sFilespec, retiChannel\)\))",
                  r"\1\t\tif (!pathExists(sFilespec))\n\t\t\t//\tNo loose file: the extension may carry it sealed.\n\t\t\treturn LoadSealedSound(SoundMgr, pathAddComponent(sFolder, sFilename), retiChannel);\n\n\2",
                  r"No loose file: the extension may carry it sealed"),
        regex_sub(r"(ALERROR CResourceDb::LoadSound \(.*?\n\treturn NOERROR;\n\t\}\n)",
                  lambda m: m.group(1) + "\n" + LOAD_SEALED_SOUND + "\n",
                  r"ALERROR CResourceDb::LoadSealedSound", flags=re.S),
    ))


def feature_isbound(t: Tree) -> None:
    t.edit("Alchemy/CodeChain/Functions.h", "isBound: FN_ITEMINFO_ISBOUND id",
           regex_sub(r"(#define FN_EQUALITY_COMPARABLE[ \t]+128[^\n]*\n)",
                     r"\1#define FN_ITEMINFO_ISBOUND\t\t\t\t129\n", r"FN_ITEMINFO_ISBOUND"))
    t.edit("Alchemy/CodeChain/DefPrimitives.h", "isBound: primitive table entry",
           regex_sub(r'(\t\t\{\t"isAtom",[^\n]*\n)',
                     '\\1\t\t{\t"isBound",\t\t\tfnItemInfo,\t\tFN_ITEMINFO_ISBOUND,\t"(isBound \'symbol) -> True if symbol has a binding",\tNULL,\t0,\t},\n',
                     r'"isBound"'))
    t.edit("Alchemy/CodeChain/Functions.cpp", "isBound: fnItemInfo case", chain(
        insert_after("//\t(isatom item) -> True/Nil\n", "//\t(isBound 'symbol) -> True/Nil\n", "(isBound 'symbol)"),
        regex_sub(r"(\t\tcase FN_ITEMINFO_ISATOM:\n\t\t\t\{\n.*?\t\t\tbreak;\n\t\t\t\}\n)",
                  r"\1\n\t\tcase FN_ITEMINFO_ISBOUND:\n\t\t\t{\n\t\t\tICCItem *pName = pArgs->Head(pCC);\n\t\t\tICCItemPtr pBinding = pCC->Lookup(pCtx, *pName);\n\t\t\tpResult = pCC->CreateBool(!pBinding->IsError());\n\t\t\tbreak;\n\t\t\t}\n",
                  r"case FN_ITEMINFO_ISBOUND:", flags=re.S),
    ))
    lookup_public(t, "isBound: CCodeChain::Lookup public")


def lookup_public(t: Tree, name: str) -> None:
    decl = "\t\tICCItemPtr Lookup (CEvalContext *pCtx, ICCItem &Item);\n"

    def fn(text: str):
        anchor = "\t\tICCItem *Eval (CEvalContext *pEvalCtx, ICCItem *pItem);\n"
        a = text.find(anchor)
        if a < 0:
            return text, "anchor not found: CCodeChain::Eval"
        if text[a + len(anchor):].startswith(decl):
            return text, "present"
        i = text.find(decl, a)
        if i < 0:
            return text, "Lookup declaration not found"
        text = text[:i] + text[i + len(decl):]
        j = a + len(anchor)
        return text[:j] + decl + text[j:], "applied"
    t.edit("Alchemy/Include/CodeChain.h", name, fn)


# ---------------------------------------------------------------- optional upstream fixes

def upstream_fixes(t: Tree) -> None:
    t.edit("Alchemy/CodeChain/CCAtomTable.cpp", "fix: CCAtomTable GetEntry INT_PTR (x64 C2664)", chain(
        regex_sub(r"(\t\t\tICCItem \*pItem;\n\t\t\t)int iKey;\n\n(\t\t\t)m_Table\.GetEntry\(i, &iKey, NULL\);",
                  r"\1INT_PTR iKey, iValue;\n\n\2m_Table.GetEntry(i, &iKey, &iValue);",
                  r"\t\t\tICCItem \*pItem;\n\t\t\tINT_PTR iKey, iValue;\n\n\t\t\tm_Table\.GetEntry\(i, &iKey, &iValue\);"),
        regex_sub(r"pItem = pCC->CreateInteger\(iKey\);", r"pItem = pCC->CreateInteger((int)iKey);",
                  r"CreateInteger\(\(int\)iKey\)"),
    ))
    t.edit("Alchemy/Kernel/CArchiver.cpp", "fix: CUnarchiver::ResolveExternalReference iID INT_PTR (x64)",
           regex_sub(r"(CUnarchiver::ResolveExternalReference \(CString sTag, void \*pReference\)\n(?:.*\n)*?\tCObject \*pValue;\n\t)int iID;",
                     r"\1INT_PTR iID;",
                     r"CUnarchiver::ResolveExternalReference \(CString sTag, void \*pReference\)\n(?:.*\n)*?\tCObject \*pValue;\n\tINT_PTR iID;"))
    t.edit("Alchemy/Include/CodeChain.h", "fix: ICCItem refcount pointer-sized (x64)", chain(
        replace_once("DWORD GetRefCount () const { return m_dwRefCount; }",
                     "DWORD GetRefCount () const { return (DWORD)m_dwRefCount; }"),
        regex_sub(r"\n(\t\tICCItem \*GetNextFree\(\) \{ return \(ICCItem \*\)m_dwRefCount; \}\n\t\tvoid SetNextFree \(ICCItem \*pNext\) \{ m_dwRefCount = )\(DWORD\)pNext; \}",
                  r"\n\t\t// TX_X64_AUTOFIX: free-list link reuses refcount field — must be pointer-sized on x64\n\1(UINT_PTR)pNext; }",
                  r"m_dwRefCount = \(UINT_PTR\)pNext;"),
        regex_sub(r"mutable DWORD m_dwRefCount;[^\n]*",
                  "mutable UINT_PTR m_dwRefCount;\t\t\t//\tRefcount, or free-list link when unused",
                  r"mutable UINT_PTR m_dwRefCount;"),
    ))
    wnd = [("Mammoth/Include/Soundtrack.h", "ParentWndProc"),
           ("Mammoth/Include/TSUI.h", "MainWndProc"),
           ("Mammoth/TSUI/CMCIMixer.cpp", "CMCIMixer::ParentWndProc"),
           ("Mammoth/TSUI/Run.cpp", "CHumanInterface::MainWndProc")]
    objref_fix(t)
    for rel, fname in wnd:
        esc = re.escape(fname)
        t.edit(rel, f"fix: {fname} LRESULT/WPARAM/LPARAM (x64)",
               regex_sub(r"LONG APIENTRY " + esc + r" \(HWND hWnd, UINT message, UINT wParam, LONG lParam\)",
                         "LRESULT APIENTRY " + fname + " (HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)",
                         r"LRESULT APIENTRY " + esc + r" \("))


#   operands that are object pointers: pFoo, &Obj, this, and the two list builders the compiler flags (C4302)
_OBJ_OPERAND = r"(p\w+|&\w+|this|List\.GetMission\(i\)|Ctx\.DistSort\[i\])"
OBJREF_PATTERNS = [
    # list->AppendInteger((int)pObj)  -> pointer-sized integer item
    (re.compile(r"(\b[\w\.\->]+?)(->|\.)AppendInteger\(\(int\)" + _OBJ_OPERAND + r"\);"),
     r"{ ICCItem *pTxObjRef = CCodeChain::CreateInteger((INT_PTR)\3); \1\2Append(pTxObjRef); pTxObjRef->Discard(); }"),
    # CC.DefineGlobalInteger(var, (int)pObj)   (also TSETransLisp.h DefineSpaceObject = every gSource/gData)
    (re.compile(r"(\b[\w\.\->]+?)(->|\.)DefineGlobalInteger\(([^,;]+),\s*\(int\)" + _OBJ_OPERAND + r"\);"),
     r"{ ICCItem *pTxObjRef = CCodeChain::CreateInteger((INT_PTR)\4); \1\2DefineGlobal(\3, pTxObjRef); pTxObjRef->Discard(); }"),
    # return ICCItemPtr((int)pObj);
    (re.compile(r"\bICCItemPtr\(\(int\)(p\w+)\)"),
     r"ICCItemPtr(CCodeChain::CreateInteger((INT_PTR)\1))"),
    # pCC->CreateInteger((int) pObj)   (CreateInteger already takes INT_PTR)
    (re.compile(r"\bCreateInteger\(\(int\) ?(p\w+)\)"),
     r"CreateInteger((INT_PTR)\1)"),
]


def objref_fix(t: Tree) -> None:
    """Object pointers handed to TLisp as 32-bit ints (sysFindObject lists, gPlayerShip, dock gSource, CTLispConvert)
    are truncated on x64: an object above 4 GB comes back as a wild pointer and crashes the next call on it
    (e.g. objAddRandomItems while creating a system -> 'No adventure defined')."""
    hits = 0
    for sub in ("Mammoth", "Transcendence"):
        for p in sorted([*(t.root / sub).rglob("*.cpp"), *(t.root / sub).rglob("*.h")]):
            if any(part.startswith("_forkgaps") or "backup" in part.lower() for part in p.parts):
                continue
            rel = p.relative_to(t.root).as_posix()
            got = t.read(rel)
            if got is None:
                continue
            text, bom, crlf = got
            new, n = text, 0
            for pat, rep in OBJREF_PATTERNS:
                new, k = pat.subn(rep, new)
                n += k
            if n:
                t.write(rel, new, bom, crlf)
                t.log.append(f"  + fix: TLisp object refs pointer-sized x{n}  ({rel})")
                hits += n
    if not hits:
        t.log.append("  = fix: TLisp object refs pointer-sized  (already present)")

    # Nebula tile maps keep child-section pointers in a 32-bit tile word. Widen the word; leaf sections (the only
    # ones written raw to saves) are streamed per DWORD so the save format is unchanged.
    t.edit("Mammoth/Include/TSEUtil.h", "fix: CTile section pointer pointer-sized (x64 nebula maps)", chain(
        replace_once("DWORD GetTile (void) { return m_dwData; }\n\t\tDWORD *GetTilePointer (void) { return &m_dwData; }",
                     "DWORD GetTile (void) { return (DWORD)m_dwData; }\n\t\tDWORD *GetTilePointer (void) { return (DWORD *)&m_dwData; }\t//\tleaf tiles only (high half stays 0)"),
        replace_once("void SetTileMapSection (CTileMapSection *pMap) { m_dwData = (DWORD)pMap; }\n\n\tprivate:\n\t\tDWORD m_dwData;",
                     "void SetTileMapSection (CTileMapSection *pMap) { m_dwData = (UINT_PTR)pMap; }\n\n\tprivate:\n\t\tUINT_PTR m_dwData;\t\t//\tTX_X64: tile, or child section pointer"),
        replace_once("ALERROR ReadFromStream (int iCount, IReadStream *pStream) { return pStream->Read((char *)m_pMap, iCount * sizeof(CTile)); }",
                     "ALERROR ReadFromStream (int iCount, IReadStream *pStream) { for (int i = 0; i < iCount; i++) { DWORD dwTile; ALERROR error = pStream->Read((char *)&dwTile, sizeof(DWORD)); if (error) return error; m_pMap[i].SetTile(dwTile); } return NOERROR; }"),
        replace_once("void WriteToStream (int iCount, IWriteStream *pStream) const { pStream->Write((char *)m_pMap, iCount * sizeof(CTile)); }",
                     "void WriteToStream (int iCount, IWriteStream *pStream) const { for (int i = 0; i < iCount; i++) { DWORD dwTile = m_pMap[i].GetTile(); pStream->Write((char *)&dwTile, sizeof(DWORD)); } }"),
    ))
    # TSharedPtr/TUniquePtr == / != int (NULL tests) compared only the low 32 bits of the pointer
    t.edit("Alchemy/Include/TSmartPtr.h", "fix: smart-pointer NULL compares pointer-sized (x64)",
           replace_once("((int)(OBJ *)lhs", "((INT_PTR)(OBJ *)lhs", count=0))


# ---------------------------------------------------------------- diagnostics

SEH_LOGGER = r'''
//	TX_FORKGAPS_SEH_LOG: when a TLisp primitive crashes natively (access violation etc.) the engine only reports
//	"Exception in <fn>; arg = ...". This filter logs the exception code and the crashing frames (function, file,
//	line from the pdb) to Debug.log first, then lets the existing catch (...) handle it as before.
#include <dbghelp.h>
#pragma comment(lib, "dbghelp.lib")

static LONG TxLogPrimitiveCrash (EXCEPTION_POINTERS *pInfo, const char *pszName)
	{
	static bool bSymInit = false;
	HANDLE hProcess = ::GetCurrentProcess();
	if (!bSymInit)
		{
		::SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS);
		::SymInitialize(hProcess, NULL, TRUE);
		bSymInit = true;
		}

	::kernelDebugLogPattern("[crash] %s: exception 0x%08x at %x", CString(pszName),
			(DWORD)pInfo->ExceptionRecord->ExceptionCode, (DWORD)(UINT_PTR)pInfo->ExceptionRecord->ExceptionAddress);

#if defined(_M_X64)
	CONTEXT Context = *pInfo->ContextRecord;
	STACKFRAME64 Frame = { 0 };
	Frame.AddrPC.Offset = Context.Rip;		Frame.AddrPC.Mode = AddrModeFlat;
	Frame.AddrFrame.Offset = Context.Rbp;	Frame.AddrFrame.Mode = AddrModeFlat;
	Frame.AddrStack.Offset = Context.Rsp;	Frame.AddrStack.Mode = AddrModeFlat;
	for (int i = 0; i < 12; i++)
		{
		if (!::StackWalk64(IMAGE_FILE_MACHINE_AMD64, hProcess, ::GetCurrentThread(), &Frame, &Context, NULL,
				::SymFunctionTableAccess64, ::SymGetModuleBase64, NULL) || Frame.AddrPC.Offset == 0)
			break;

		char Buffer[sizeof(SYMBOL_INFO) + 256] = { 0 };
		SYMBOL_INFO *pSym = (SYMBOL_INFO *)Buffer;
		pSym->SizeOfStruct = sizeof(SYMBOL_INFO);
		pSym->MaxNameLen = 255;
		DWORD64 dwDisp = 0;
		const char *pszFn = (::SymFromAddr(hProcess, Frame.AddrPC.Offset, &dwDisp, pSym) ? pSym->Name : "?");

		IMAGEHLP_LINE64 Line = { sizeof(IMAGEHLP_LINE64) };
		DWORD dwLineDisp = 0;
		if (::SymGetLineFromAddr64(hProcess, Frame.AddrPC.Offset, &dwLineDisp, &Line))
			::kernelDebugLogPattern("[crash]   %d: %s  %s:%d", i, CString(pszFn), CString(Line.FileName), (int)Line.LineNumber);
		else
			::kernelDebugLogPattern("[crash]   %d: %s", i, CString(pszFn));
		}
#endif

	return EXCEPTION_CONTINUE_SEARCH;
	}

static ICCItem *TxInvokePrimitive (PRIMITIVEPROC pfFunction, CEvalContext *pCtx, ICCItem *pArgs, DWORD dwData, const char *pszName)
	{
	__try
		{
		return pfFunction(pCtx, pArgs, dwData);
		}
	__except (TxLogPrimitiveCrash(GetExceptionInformation(), pszName))
		{
		return NULL;
		}
	}
'''


def diagnostics(t: Tree) -> None:
    rel = "Alchemy/CodeChain/CCPrimitive.cpp"
    t.edit(rel, "diag: log native crashes in TLisp primitives (function/file/line)", chain(
        insert_after('#include "PreComp.h"\n', SEH_LOGGER, "TX_FORKGAPS_SEH_LOG"),
        replace_once("pResult = ((PRIMITIVEPROC)m_pfFunction)(pCtx, pEvalArgs, m_dwData);",
                     "pResult = TxInvokePrimitive((PRIMITIVEPROC)m_pfFunction, pCtx, pEvalArgs, m_dwData, m_sName.GetASCIIZPointer());"),
    ))


# ---------------------------------------------------------------- build config

def build_config(t: Tree) -> None:
    # LibJPEGTurboUtil: the two Debug x64 configs try to use a PCH that does not exist and never link turbojpeg.lib
    def jpeg(text: str):
        if "<AdditionalDependencies>turbojpeg.lib;" in text:
            return text, "present"
        n = 0
        out = []
        for block in re.split(r"(?=<ItemDefinitionGroup )", text):
            m = re.match(r"<ItemDefinitionGroup Condition=\"'\$\(Configuration\)\|\$\(Platform\)'=='(Debug|Debug For Contributors)\|x64'\">", block)
            if m and "<PrecompiledHeaderOutputFile>" in block and "<Lib>" in block:
                if "<PrecompiledHeader>" not in block:
                    block = re.sub(r"(\n(\s*)<PrecompiledHeaderOutputFile>)", r"\n\2<PrecompiledHeader>NotUsing</PrecompiledHeader>\1", block, count=1)
                block = re.sub(r"(\n(\s*)<OutputFile>\$\(OutDir\)\$\(TargetName\)\$\(TargetExt\)</OutputFile>\n)(\s*</Lib>)",
                               r"\1\2<AdditionalLibraryDirectories>$(MSBuildProjectDirectory);%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>\n"
                               r"\2<AdditionalDependencies>turbojpeg.lib;%(AdditionalDependencies)</AdditionalDependencies>\n\3", block, count=1)
                n += 1
            out.append(block)
        if n == 0:
            return text, "Debug|x64 item definitions not found"
        return "".join(out), "applied"
    t.edit("Alchemy/LibJPEGTurboUtil/LibJPEGTurboUtil.vcxproj", "build: LibJPEGTurboUtil no PCH + turbojpeg.lib", jpeg)

    t.edit("Alchemy/zlib-1.2.7/contrib/vstudio/vc10/zlibstat.vcxproj", "build: zlibstat static debug CRT (matches engine /MTd)",
           replace_once("<RuntimeLibrary>MultiThreadedDebugDLL</RuntimeLibrary>",
                        "<RuntimeLibrary>MultiThreadedDebug</RuntimeLibrary>", count=0))

    # TSUI: CHexarcService.cpp needs proprietary HexarcKeys.h; contributors builds use the stub (Win32 had it, x64 did not)
    def hexarc(text: str):
        if "'Debug For Contributors|x64'\">true</ExcludedFromBuild>" in text:
            return text, "present"
        cond = "<ExcludedFromBuild Condition=\"'$(Configuration)|$(Platform)'=='{c}'\">{v}</ExcludedFromBuild>"
        m = re.search(r'(\n(\s*)<ClCompile Include="CHexarcService\.cpp">\n(?:.*\n)*?)(\s*</ClCompile>)', text)
        s = re.search(r'(\n(\s*)<ClCompile Include="CHexarcServiceStub\.cpp">\n(?:.*\n)*?)(\s*</ClCompile>)', text)
        if not m or not s:
            return text, "CHexarcService ClCompile items not found"
        ind = m.group(2) + "  "
        svc = "".join(f"{ind}{cond.format(c=c, v='true')}\n" for c in ("Preview For Contributors|x64", "Debug For Contributors|x64"))
        stub_cfg = [("Debug|x64", "true"), ("SteamRelease|x64", "true"), ("Preview For Contributors|x64", "false"),
                    ("SteamDebug|x64", "true"), ("Debug with Address Sanitizer|x64", "true"), ("Release|x64", "true"),
                    ("Debug For Contributors|x64", "false"), ("Debug in Program Files|x64", "true")]
        stub = "".join(f"{ind}{cond.format(c=c, v=v)}\n" for c, v in stub_cfg)
        # insert at the later item first so the earlier offset stays valid
        for pos, add in sorted([(m.end(1), svc), (s.end(1), stub)], reverse=True):
            text = text[:pos] + add + text[pos:]
        return text, "applied"
    t.edit("Mammoth/TSUI/TSUI.vcxproj", "build: TSUI Hexarc stub for x64 contributor builds", hexarc)

    # TransData (headless test/report tool) still references the old IntelJPEGUtil, which has no x64 build;
    # the game links LibJPEGTurboUtil, so TransData does the same
    t.edit("Transcendence/TransData/TransData.vcxproj", "build: TransData uses LibJPEGTurboUtil (x64 link)",
           regex_sub(r'<ProjectReference Include="\.\.\\\.\.\\Alchemy\\IntelJPEGUtil\\IntelJPEGUtil\.vcxproj">(\s*)<Project>\{ecac7e19-acbc-4c3c-b89a-7bc7049b6f2e\}</Project>',
                     r'<ProjectReference Include="..\\..\\Alchemy\\LibJPEGTurboUtil\\LibJPEGTurboUtil.vcxproj">\1<Project>{c68a844b-f08b-4913-bcff-b607c7bc1f6d}</Project>',
                     r"LibJPEGTurboUtil\\LibJPEGTurboUtil\.vcxproj", flags=re.I))

    guid = "{C68A844B-F08B-4913-BCFF-B607C7BC1F6D}"

    def sln(text: str):
        good = f"{guid}.Debug For Contributors|x64.ActiveCfg = Debug For Contributors|x64"
        if good in text:
            return text, "present"
        pat = (re.escape(guid) + r"\.Debug For Contributors\|Win32\.ActiveCfg = Debug\|Win32\n(\s*)"
               + re.escape(guid) + r"\.Debug For Contributors\|x64\.ActiveCfg = Debug\|x64\n\s*"
               + re.escape(guid) + r"\.Debug For Contributors\|x64\.Build\.0 = Debug\|x64")
        rep = (f"{guid}.Debug For Contributors|Win32.ActiveCfg = Debug For Contributors|Win32\n\\1"
               f"{guid}.Debug For Contributors|Win32.Build.0 = Debug For Contributors|Win32\n\\1"
               f"{guid}.Debug For Contributors|x64.ActiveCfg = Debug For Contributors|x64\n\\1"
               f"{guid}.Debug For Contributors|x64.Build.0 = Debug For Contributors|x64")
        new, n = re.subn(pat, rep, text)
        if n == 0:
            return text, "Debug For Contributors mapping for the JPEG project not found"
        return new, "applied"
    t.edit("Transcendence/Transcendence.sln", "build: sln Debug For Contributors -> contributor config", sln)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-root", required=True, help="TranscendenceDev tree (official copy or _x64_workspace)")
    ap.add_argument("--skip", action="append", default=[], choices=GROUPS, help="group to leave out (repeatable)")
    ap.add_argument("--only", action="append", default=[], choices=GROUPS, help="run only these groups")
    ap.add_argument("--seal-key", default=str(DEFAULT_KEY), help="private seal key for SealedKey.h")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="accepted for switcher compatibility (patches are idempotent)")
    a = ap.parse_args()

    root = Path(a.api_root).resolve()
    if not (root / "Mammoth").is_dir() or not (root / "Alchemy").is_dir():
        print(f"[forkgaps] not a TranscendenceDev tree: {root}")
        return 2
    groups = [g for g in (a.only or GROUPS) if g not in a.skip]
    t = Tree(root, a.dry_run)
    print(f"[forkgaps] {root}  groups: {', '.join(groups)}{'  (dry run)' if a.dry_run else ''}")
    if "upstream-fixes" in groups:
        t.log.append("upstream-fixes (optional):")
        upstream_fixes(t)
    if "features" in groups:
        t.log.append("features:")
        feature_sealed_sounds(t, Path(a.seal_key))
        feature_isbound(t)
    if "diagnostics" in groups:
        t.log.append("diagnostics (optional):")
        diagnostics(t)
    if "build-config" in groups:
        t.log.append("build-config:")
        build_config(t)
    print("\n".join(t.log))
    if t.backed:
        print(f"[forkgaps] backups: {root / '_forkgaps_backups' / t.stamp}")
    if t.errors:
        print("[forkgaps] FAILED:")
        print("\n".join("  - " + e for e in t.errors))
        return 1
    print("[forkgaps] ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
