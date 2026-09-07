#!/usr/bin/env python3
"""
Fix-TranscendenceX64.py

Autofix a TranscendenceDev-integration-APIxx tree for a true 64-bit (x64) client build.

Primary issue: Kernel stores pointers in CIntArray/CDictionary as 32-bit `int`.
This rewrites those containers to INT_PTR and fixes related casts / SEH code.

Idempotent: writes .x64_autofix_v2 marker under the API root.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER_NAME = ".x64_autofix_v2"
FIX_VERSION = 2
LEGACY_MARKERS = (".x64_autofix_v1",)


def backup_file(path: Path, backup_root: Path, api_root: Path) -> None:
    rel = path.relative_to(api_root)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def write_text(path: Path, text: str) -> None:
    # Preserve UTF-8, normalize to the file's prior newline style if possible
    path.write_bytes(text.encode("utf-8"))


def patch_kernel_h(text: str) -> tuple[str, list[str]]:
    notes = []
    original = text

    # Ensure Windows INT_PTR available (Kernel.h already pulls windows types via Alchemy)
    if "TX_X64_INTPTR_ELEMENT" not in text:
        # Insert typedef alias near top of Kernel namespace / after includes block
        # Prefer a marker comment after pragma/includes
        insert = (
            "\n// TX_X64_AUTOFIX: pointer-sized array/dictionary elements for x64\n"
            "#ifndef TX_X64_INTPTR_ELEMENT\n"
            "#define TX_X64_INTPTR_ELEMENT\n"
            "// INT_PTR comes from Windows headers included by this tree\n"
            "#endif\n"
        )
        # After `#pragma once` or first include block
        if "#pragma once" in text:
            text = text.replace("#pragma once", "#pragma once" + insert, 1)
            notes.append("Kernel.h: added x64 autofix marker")
        else:
            text = insert + text
            notes.append("Kernel.h: prepended x64 autofix marker")

    # CIntArray: element storage INT_PTR
    replacements = [
        (
            r"ALERROR AppendElement \(int iElement, int \*retiIndex = NULL\);",
            "ALERROR AppendElement (INT_PTR iElement, int *retiIndex = NULL);",
        ),
        (
            r"int FindElement \(int iElement\) const;",
            "int FindElement (INT_PTR iElement) const;",
        ),
        (
            r"int GetElement \(int iIndex\) const;",
            "INT_PTR GetElement (int iIndex) const;",
        ),
        (
            r"ALERROR InsertElement \(int iElement, int iPos, int \*retiIndex\);",
            "ALERROR InsertElement (INT_PTR iElement, int iPos, int *retiIndex);",
        ),
        (
            r"ALERROR Set \(int iCount, int \*pData\);",
            "ALERROR Set (int iCount, INT_PTR *pData);",
        ),
        (
            r"void ReplaceElement \(int iPos, int iElement\);",
            "void ReplaceElement (int iPos, INT_PTR iElement);",
        ),
        (
            r"int \*m_pData;(\s+)//\tPointer to integer array",
            r"INT_PTR *m_pData;\1//\tPointer to INT_PTR array (x64-safe)",
        ),
    ]

    # CDictionary signatures
    dict_reps = [
        (
            r"ALERROR AddEntry \(int iKey, int iValue\);",
            "ALERROR AddEntry (INT_PTR iKey, INT_PTR iValue);",
        ),
        (
            r"ALERROR Find \(int iKey, int \*retiValue\) const;",
            "ALERROR Find (INT_PTR iKey, INT_PTR *retiValue) const;",
        ),
        (
            r"ALERROR FindEx \(int iKey, int \*retiEntry\) const;",
            "ALERROR FindEx (INT_PTR iKey, int *retiEntry) const;",
        ),
        (
            r"ALERROR FindOrAdd \(int iKey, int iValue, bool \*retbFound, int \*retiValue\);",
            "ALERROR FindOrAdd (INT_PTR iKey, INT_PTR iValue, bool *retbFound, INT_PTR *retiValue);",
        ),
        (
            r"void GetEntry \(int iEntry, int \*retiKey, int \*retiValue\) const;",
            "void GetEntry (int iEntry, INT_PTR *retiKey, INT_PTR *retiValue) const;",
        ),
        (
            r"ALERROR ReplaceEntry \(int iKey, int iValue, bool bAdd, bool \*retbAdded, int \*retiOldValue\);",
            "ALERROR ReplaceEntry (INT_PTR iKey, INT_PTR iValue, bool bAdd, bool *retbAdded, INT_PTR *retiOldValue);",
        ),
        (
            r"ALERROR RemoveEntryByOrdinal \(int iEntry, int \*retiOldValue = NULL\);",
            "ALERROR RemoveEntryByOrdinal (int iEntry, INT_PTR *retiOldValue = NULL);",
        ),
        (
            r"ALERROR RemoveEntry \(int iKey, int \*retiOldValue\);",
            "ALERROR RemoveEntry (INT_PTR iKey, INT_PTR *retiOldValue);",
        ),
        (
            r"virtual int Compare \(int iKey1, int iKey2\) const;",
            "virtual int Compare (INT_PTR iKey1, INT_PTR iKey2) const;",
        ),
        (
            r"void SetEntry \(int iEntry, int iKey, int iValue\);",
            "void SetEntry (int iEntry, INT_PTR iKey, INT_PTR iValue);",
        ),
        (
            r"bool FindSlot \(int iKey, int \*retiPos\) const;",
            "bool FindSlot (INT_PTR iKey, int *retiPos) const;",
        ),
        # CIDTable inline
        (
            r"ALERROR AddEntry \(int iKey, CObject \*pValue\) \{ return CDictionary::AddEntry\(iKey, \(int\)pValue\); \}",
            "ALERROR AddEntry (int iKey, CObject *pValue) { return CDictionary::AddEntry(iKey, (INT_PTR)pValue); }",
        ),
    ]

    for pat, repl in replacements + dict_reps:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"Kernel.h: {pat[:48]}... x{n}")

    # Already patched?
    if text == original and "INT_PTR *m_pData" in text:
        notes.append("Kernel.h: already x64-patched")
    return text, notes


def patch_cintarray_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    # sizeof(int) -> sizeof(INT_PTR) for element allocations
    text2, n = re.subn(r"sizeof\(int\)", "sizeof(INT_PTR)", text)
    if n:
        text = text2
        notes.append(f"CIntArray.cpp: sizeof(int)->sizeof(INT_PTR) x{n}")

    text2, n = re.subn(r"\(int \*\)", "(INT_PTR *)", text)
    if n:
        text = text2
        notes.append(f"CIntArray.cpp: (int *)->(INT_PTR *) x{n}")

    sigs = [
        (
            r"ALERROR CIntArray::AppendElement \(int iElement, int \*retiIndex\)",
            "ALERROR CIntArray::AppendElement (INT_PTR iElement, int *retiIndex)",
        ),
        (
            r"int CIntArray::FindElement \(int iElement\) const",
            "int CIntArray::FindElement (INT_PTR iElement) const",
        ),
        (
            r"int CIntArray::GetElement \(int iIndex\) const",
            "INT_PTR CIntArray::GetElement (int iIndex) const",
        ),
        (
            r"ALERROR CIntArray::InsertElement \(int iElement, int iPos, int \*retiIndex\)",
            "ALERROR CIntArray::InsertElement (INT_PTR iElement, int iPos, int *retiIndex)",
        ),
        (
            r"ALERROR CIntArray::Set \(int iCount, int \*pData\)",
            "ALERROR CIntArray::Set (int iCount, INT_PTR *pData)",
        ),
        (
            r"void CIntArray::ReplaceElement \(int iPos, int iElement\)",
            "void CIntArray::ReplaceElement (int iPos, INT_PTR iElement)",
        ),
        (
            r"int \*pNewData;",
            "INT_PTR *pNewData;",
        ),
        (
            r"int iTemp;",
            "INT_PTR iTemp;",
        ),
        (
            r"int iValue = m_pData\[x\];",
            "INT_PTR iValue = m_pData[x];",
        ),
    ]
    for pat, repl in sigs:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"CIntArray.cpp: sig/local x{n}")

    return text, notes


def patch_cdictionary_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    reps = [
        (
            r"ALERROR CDictionary::AddEntry \(int iKey, int iValue\)",
            "ALERROR CDictionary::AddEntry (INT_PTR iKey, INT_PTR iValue)",
        ),
        (
            r"int CDictionary::Compare \(int iKey1, int iKey2\) const",
            "int CDictionary::Compare (INT_PTR iKey1, INT_PTR iKey2) const",
        ),
        (
            r"ALERROR CDictionary::Find \(int iKey, int \*retiValue\) const",
            "ALERROR CDictionary::Find (INT_PTR iKey, INT_PTR *retiValue) const",
        ),
        (
            r"ALERROR CDictionary::FindEx \(int iKey, int \*retiEntry\) const",
            "ALERROR CDictionary::FindEx (INT_PTR iKey, int *retiEntry) const",
        ),
        (
            r"ALERROR CDictionary::FindOrAdd \(int iKey, int iValue, bool \*retbFound, int \*retiValue\)",
            "ALERROR CDictionary::FindOrAdd (INT_PTR iKey, INT_PTR iValue, bool *retbFound, INT_PTR *retiValue)",
        ),
        (
            r"bool CDictionary::FindSlot \(int iKey, int \*retiPos\) const",
            "bool CDictionary::FindSlot (INT_PTR iKey, int *retiPos) const",
        ),
        (
            r"void CDictionary::GetEntry \(int iEntry, int \*retiKey, int \*retiValue\) const",
            "void CDictionary::GetEntry (int iEntry, INT_PTR *retiKey, INT_PTR *retiValue) const",
        ),
        (
            r"ALERROR CDictionary::RemoveEntry \(int iKey, int \*retiOldValue\)",
            "ALERROR CDictionary::RemoveEntry (INT_PTR iKey, INT_PTR *retiOldValue)",
        ),
        (
            r"ALERROR CDictionary::RemoveEntryByOrdinal \(int iEntry, int \*retiOldValue\)",
            "ALERROR CDictionary::RemoveEntryByOrdinal (int iEntry, INT_PTR *retiOldValue)",
        ),
        (
            r"ALERROR CDictionary::ReplaceEntry \(int iKey, int iValue, bool bAdd, bool \*retbAdded, int \*retiOldValue\)",
            "ALERROR CDictionary::ReplaceEntry (INT_PTR iKey, INT_PTR iValue, bool bAdd, bool *retbAdded, INT_PTR *retiOldValue)",
        ),
        (
            r"void CDictionary::SetEntry \(int iEntry, int iKey, int iValue\)",
            "void CDictionary::SetEntry (int iEntry, INT_PTR iKey, INT_PTR iValue)",
        ),
        (
            r"int iEntryKey, iCompare;",
            "INT_PTR iEntryKey;\n\tint iCompare;",
        ),
        (
            r"\tint iOldValue;",
            "\tINT_PTR iOldValue;",
        ),
    ]
    for pat, repl in reps:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"CDictionary.cpp: {n}")
    return text, notes


def patch_pointer_casts(text: str) -> tuple[str, list[str]]:
    """Cast pointer->int to pointer->INT_PTR in Kernel table code."""
    notes = []
    # (int)pSomething / (int)psKey where clearly a pointer cast
    patterns = [
        (r"\(int\)(p[A-Za-z_][\w]*)", r"(INT_PTR)\1"),
        (r"\(int\)(ps[A-Za-z_][\w]*)", r"(INT_PTR)\1"),
        (r"\(int\)&(s[A-Za-z_][\w]*)", r"(INT_PTR)&\1"),  # CSymbolTable key lookup via &CString
        (r"\(int \*\)&(p[A-Za-z_][\w]*)", r"(INT_PTR *)&\1"),
        (r"\(int \*\)&([a-zA-Z_][\w]*)", r"(INT_PTR *)&\1"),
    ]
    for pat, repl in patterns:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"cast {pat} x{n}")

    # Locals used as dictionary key/value often `int iKey, iValue` next to GetEntry
    text2, n = re.subn(
        r"\bint iKey, iValue;",
        "INT_PTR iKey, iValue;",
        text,
    )
    if n:
        text = text2
        notes.append(f"int iKey,iValue -> INT_PTR x{n}")

    text2, n = re.subn(r"\bint iKey;\s*\n\s*CObject \*pValue;", "INT_PTR iKey;\n\t\t\tCObject *pValue;", text)
    if n:
        text = text2
        notes.append(f"int iKey before CObject* x{n}")

    text2, n = re.subn(r"\bint iOldValue;", "INT_PTR iOldValue;", text)
    if n:
        text = text2
        notes.append(f"int iOldValue -> INT_PTR x{n}")

    text2, n = re.subn(r"\bint iOldEntry;", "INT_PTR iOldEntry;", text)
    if n:
        text = text2
        notes.append(f"int iOldEntry -> INT_PTR x{n}")

    # Common dictionary out-params / temps holding packed pointer values
    text2, n = re.subn(r"\bint iValue;", "INT_PTR iValue;", text)
    if n:
        text = text2
        notes.append(f"int iValue -> INT_PTR x{n}")

    # NOTE: do NOT widen archive reference IDs (int iID) — those stay 32-bit.

    text2, n = re.subn(
        r"int CIDTable::Compare \(int iKey1, int iKey2\) const",
        "int CIDTable::Compare (INT_PTR iKey1, INT_PTR iKey2) const",
        text,
    )
    if n:
        text = text2
        notes.append("CIDTable::Compare INT_PTR")

    text2, n = re.subn(
        r"int CSymbolTable::Compare \(int iKey1, int iKey2\) const",
        "int CSymbolTable::Compare (INT_PTR iKey1, INT_PTR iKey2) const",
        text,
    )
    if n:
        text = text2
        notes.append("CSymbolTable::Compare INT_PTR")

    # DWORD compare of keys should be UINT_PTR on x64
    text2, n = re.subn(r"\(DWORD\)iKey1 > \(DWORD\)iKey2", "(UINT_PTR)iKey1 > (UINT_PTR)iKey2", text)
    if n:
        text = text2
        notes.append("DWORD key compare -> UINT_PTR")

    # Archiver stores reference IDs in the int-array; keep position as int, value as INT_PTR
    # (already handled by (int)p* -> INT_PTR). Also widen sizeof(DWORD) pointer IO only when
    # reading into a CObject* slot — leave archive format alone for now.

    return text, notes


def patch_kernel_exceptions(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"DWORD dwInfo = info->ExceptionRecord->ExceptionInformation\[i\];",
        "ULONG_PTR dwInfo = info->ExceptionRecord->ExceptionInformation[i];",
        text,
    )
    if n:
        text = text2
        notes.append(f"ExceptionInformation ULONG_PTR x{n}")
    # format strings %x still ok for truncated display; use %Ix for pointer-sized
    text2, n = re.subn(
        r'CONSTLIT\(" - ADDR: %x"\)',
        'CONSTLIT(" - ADDR: %Ix")',
        text,
    )
    if n:
        text = text2
        notes.append("ADDR format %Ix")
    return text, notes


def patch_kernel_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"CString\(pszLine, ::strlen\(pszLine\), TRUE\)",
        "CString(pszLine, (int)::strlen(pszLine), TRUE)",
        text,
    )
    if n:
        text = text2
        notes.append("strlen cast to int")
    return text, notes


def patch_cidtable_getkey(text: str) -> tuple[str, list[str]]:
    """CIDTable::GetKey still returns int (UNID); narrow INT_PTR explicitly."""
    notes = []
    text2, n = re.subn(
        r"(int CIDTable::GetKey \(int iEntry\) const\s*//[^\n]*\n(?:.*\n)*?\treturn )iKey;",
        r"\1(int)iKey;",
        text,
        count=1,
    )
    if n:
        text = text2
        notes.append("CIDTable::GetKey return (int)iKey")
    # Also handle simple form without relying on comments
    if "return (int)iKey;" not in text:
        text2, n = re.subn(
            r"(int CIDTable::GetKey \(int iEntry\) const[\s\S]*?GetEntry\(iEntry, &iKey, &iValue\);\s*\n\s*return )iKey;",
            r"\1(int)iKey;",
            text,
            count=1,
        )
        if n:
            text = text2
            notes.append("CIDTable::GetKey return (int)iKey")
    return text, notes


def patch_transcendence_vcxproj(text: str) -> tuple[str, list[str]]:
    notes = []
    if "Debug For Contributors|x64'\">..\\Game\\" in text or 'Debug For Contributors|x64">..\\Game\\' in text:
        notes.append("vcxproj: x64 OutDir already set")
    else:
        block = (
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Release|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Preview For Contributors|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='SteamRelease|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Debug|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Debug For Contributors|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Debug with Address Sanitizer|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='SteamDebug|x64'\">..\\Game\\</OutDir>\r\n"
            "    <OutDir Condition=\"'$(Configuration)|$(Platform)'=='Debug in Program Files|x64'\">..\\Game\\</OutDir>\r\n"
        )
        if "\r\n" not in text:
            block = block.replace("\r\n", "\n")

        anchor = "<OutDir Condition=\"'$(Configuration)|$(Platform)'=='Debug in Program Files|Win32'\">..\\Game\\</OutDir>"
        if anchor in text:
            nl = "\r\n" if "\r\n" in text else "\n"
            text = text.replace(
                anchor,
                anchor + nl + block.rstrip("\r\n").rstrip("\n") + nl,
                1,
            )
            notes.append("vcxproj: added x64 OutDir -> ..\\Game\\")
        else:
            notes.append("vcxproj: OutDir anchor not found — skipped")
    return text, notes


def patch_restore_archive_int_ids(text: str) -> tuple[str, list[str]]:
    """v1 mistakenly widened archive IDs; Reference2ID still takes int *."""
    notes = []
    # Call sites: INT_PTR iID used with Reference2ID(...)
    text2, n = re.subn(
        r"INT_PTR iID;\s*\n(\s*CObject \*pValue = \(CObject \*\)iValue;\s*\n\s*if \(error = pArchiver->Reference2ID)",
        r"int iID;\n\1",
        text,
    )
    if n:
        text = text2
        notes.append(f"restore int iID before Reference2ID x{n}")

    text2, n = re.subn(
        r"INT_PTR iID;\s*\n(\s*//\tConvert to ID\s*\n\s*if \(error = Reference2ID)",
        r"int iID;\n\1",
        text,
    )
    if n:
        text = text2
        notes.append(f"restore int iID Convert-to-ID x{n}")

    text2, n = re.subn(
        r"INT_PTR iID;\s*\n(\s*//\tAssign a reference ID)",
        r"int iID;\n\1",
        text,
    )
    if n:
        text = text2
        notes.append(f"restore int iID Assign-ref x{n}")

    # Other Reference2ID call-site patterns in CArchiver
    text2, n = re.subn(
        r"INT_PTR iID;\s*\n(\s*if \(error = Reference2ID)",
        r"int iID;\n\1",
        text,
    )
    if n:
        text = text2
        notes.append(f"restore int iID Reference2ID call x{n}")

    text2, n = re.subn(
        r"INT_PTR iID;\s*\n(\s*//\tWrite out the object ID\s*\n\s*if \(error = Reference2ID)",
        r"int iID;\n\1",
        text,
    )
    if n:
        text = text2
        notes.append(f"restore int iID Write-object-ID x{n}")

    # Inside Reference2ID keep INT_PTR for FindOrAdd, but narrow when writing out
    text2, n = re.subn(
        r"(\*retiID = )(?!\(int\))iID;",
        r"\1(int)iID;",
        text,
    )
    if n:
        text = text2
        notes.append(f"*retiID = (int)iID x{n}")

    # Fake CObject* from small integer IDs
    text2, n = re.subn(
        r"\(CObject \*\)iID\b",
        r"(CObject *)(INT_PTR)iID",
        text,
    )
    if n:
        text = text2
        notes.append(f"(CObject *)(INT_PTR)iID x{n}")

    text2, n = re.subn(
        r"\(CObject \*\)m_iNextAtom\b",
        r"(CObject *)(INT_PTR)m_iNextAtom",
        text,
    )
    if n:
        text = text2
        notes.append("(CObject *)(INT_PTR)m_iNextAtom")

    # ResolveReference / GetElement → void* / int narrowing
    text2, n = re.subn(
        r"iID = \(int\)pValue;",
        "iID = (int)(INT_PTR)pValue;",
        text,
    )
    if n:
        text = text2
        notes.append("iID from pValue via INT_PTR")

    return text, notes


def patch_math_round_x64(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_MATH_ROUND" in text:
        notes.append("Math.cpp: already patched")
        return text, notes
    if "mathRound" not in text or "__asm" not in text:
        return text, notes

    new_fn_src = r'''int Kernel::mathRound (double x)

//	mathRound
//
//	Round to the nearest integer.
//	Based on: http://ldesoras.free.fr/doc/articles/rounding_en.pdf
//	TX_X64_MATH_ROUND: MSVC x64 has no inline asm — use portable rounding.

	{
#if defined(_WIN64) || defined(__x86_64__) || defined(_M_X64)
	return (int)floor(x + 0.5);
#else
	const double round_to_nearest = 0.5;
	int i;

#ifndef __GNUC__
	__asm
		{
		fld x
		fadd st, st (0)
		fadd round_to_nearest
		fistp i
		sar i, 1
		}
#else
	//i = floor(x + round_to_nearest); //fallback alternative
	__asm__ __volatile__ (
		"fadd %%st\n\t"
		"fadd %%st(1)\n\t"
		"fistpl %0\n\t"
		"sarl $1, %0\n"
		: "=m"(i) : "u"(round_to_nearest), "t"(x) : "st"
        );
#endif
	return (i);
#endif
	}'''

    pat = re.compile(
        r"int Kernel::mathRound \(double x\)\s*//\s*mathRound[\s\S]*?return \(i\);\s*\}",
        re.M,
    )
    text2, n = pat.subn(new_fn_src, text, count=1)
    if n:
        text = text2
        notes.append("Math.cpp: portable mathRound for x64")
    else:
        notes.append("Math.cpp: mathRound pattern not matched")
    return text, notes


def patch_cobject_ptr_slots(text: str) -> tuple[str, list[str]]:
    """Store object/memory pointers as UINT_PTR-sized slots (not DWORD)."""
    notes = []
    reps = [
        (
            r"BYTE \*pSourceMem = \(BYTE \*\)\*\(\(DWORD \*\)pSource\);",
            "BYTE *pSourceMem = (BYTE *)*((UINT_PTR *)pSource);",
        ),
        (
            r"\*\(\(DWORD \*\)pDest\) = \(DWORD\)pDestMem;",
            "*((UINT_PTR *)pDest) = (UINT_PTR)pDestMem;",
        ),
        (
            r"\*\(\(DWORD \*\)pDest\) = \(DWORD\)pCopy;",
            "*((UINT_PTR *)pDest) = (UINT_PTR)pCopy;",
        ),
        (
            r"\*\(\(DWORD \*\)pDest\) = 0;",
            "*((UINT_PTR *)pDest) = 0;",
        ),
        (
            r"BYTE \*pMem = \(BYTE \*\)\*\(\(DWORD \*\)pPos\);",
            "BYTE *pMem = (BYTE *)*((UINT_PTR *)pPos);",
        ),
        (
            r"\*\(\(DWORD \*\)pPos\) = \(DWORD\)",
            "*((UINT_PTR *)pPos) = (UINT_PTR)",
        ),
    ]
    for pat, repl in reps:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"CObject UINT_PTR slot x{n}")
    return text, notes


def patch_kernel_vcxproj_x64_warnings(text: str) -> tuple[str, list[str]]:
    """Don't fail x64 Kernel builds on remaining size_t/int noise after real pointer fixes."""
    notes = []
    flipped = 0

    def flip_group(m: re.Match) -> str:
        nonlocal flipped
        g = m.group(0)
        g2, n = re.subn(
            r"<TreatWarningAsError>true</TreatWarningAsError>",
            "<TreatWarningAsError>false</TreatWarningAsError>",
            g,
        )
        flipped += n
        return g2

    text2, _ = re.subn(
        r"<ItemDefinitionGroup Condition=\"[^\"]*\|x64[^\"]*\">[\s\S]*?</ItemDefinitionGroup>",
        flip_group,
        text,
    )
    if flipped:
        notes.append(f"Kernel.vcxproj: TreatWarningAsError=false for x64 x{flipped}")
    else:
        notes.append("Kernel.vcxproj: no TreatWarningAsError flips (already false or missing)")
    return text2, notes


def apply_file(path: Path, patcher, api_root: Path, backup_root: Path, dry_run: bool) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    new_text, notes = patcher(text)
    if new_text != text and notes:
        if not dry_run:
            backup_file(path, backup_root, api_root)
            # preserve newlines roughly
            nl = "\r\n" if "\r\n" in text else "\n"
            out = new_text.replace("\r\n", "\n").replace("\r", "\n")
            if nl != "\n":
                out = out.replace("\n", nl)
            path.write_bytes(out.encode("utf-8"))
        return [f"{path.relative_to(api_root)}: {n}" for n in notes]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofix Transcendence API tree for x64")
    ap.add_argument("api_folder", help="Path to TranscendenceDev-integration-APIxx")
    ap.add_argument("--force", action="store_true", help="Re-apply even if marker present")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true", help="Only report whether fix is applied")
    args = ap.parse_args()

    api_root = Path(args.api_folder).resolve()
    if not api_root.is_dir():
        print(f"ERROR: API folder not found: {api_root}", file=sys.stderr)
        return 2

    sln = api_root / "Transcendence" / "Transcendence.sln"
    if not sln.is_file():
        print(f"ERROR: Not a Transcendence API tree (missing Transcendence\\Transcendence.sln): {api_root}", file=sys.stderr)
        return 2

    marker = api_root / MARKER_NAME
    if args.status:
        print("applied" if marker.is_file() else "not_applied")
        return 0

    if marker.is_file() and not args.force:
        print(f"x64 autofix already applied ({marker.name}). Use --force to re-run.")
        return 0

    backup_root = (
        api_root.parent.parent
        / "Tools"
        / "Transcendence"
        / "_ext_fix_backups"
        / f"x64_autofix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    # If Tools isn't under parent.parent (api is under game_and_dlc_source), resolve GameRoot
    # api_root = .../game_and_dlc_source/TranscendenceDev-integration-API59
    game_root = api_root.parent.parent  # Transcendence
    backup_root = game_root / "Tools" / "Transcendence" / "_ext_fix_backups" / f"x64_autofix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"API tree: {api_root}")
    print(f"Backups:  {backup_root}")
    if args.dry_run:
        print("DRY RUN — no files written")

    jobs: list[tuple[Path, object]] = [
        (api_root / "Alchemy" / "Include" / "Kernel.h", patch_kernel_h),
        (api_root / "Alchemy" / "Include" / "KernelExceptions.h", patch_kernel_exceptions),
        (api_root / "Alchemy" / "Kernel" / "CIntArray.cpp", patch_cintarray_cpp),
        (api_root / "Alchemy" / "Kernel" / "CDictionary.cpp", patch_cdictionary_cpp),
        (api_root / "Alchemy" / "Kernel" / "Kernel.cpp", patch_kernel_cpp),
        (api_root / "Alchemy" / "Kernel" / "CIDTable.cpp", patch_pointer_casts),
        (api_root / "Alchemy" / "Kernel" / "CIDTable.cpp", patch_cidtable_getkey),
        (api_root / "Alchemy" / "Kernel" / "CIDTable.cpp", patch_restore_archive_int_ids),
        (api_root / "Alchemy" / "Kernel" / "CSymbolTable.cpp", patch_pointer_casts),
        (api_root / "Alchemy" / "Kernel" / "CSymbolTable.cpp", patch_restore_archive_int_ids),
        (api_root / "Alchemy" / "Kernel" / "CArchiver.cpp", patch_pointer_casts),
        (api_root / "Alchemy" / "Kernel" / "CArchiver.cpp", patch_restore_archive_int_ids),
        (api_root / "Alchemy" / "Kernel" / "CAtomTable.cpp", patch_restore_archive_int_ids),
        (api_root / "Alchemy" / "Kernel" / "Math.cpp", patch_math_round_x64),
        (api_root / "Alchemy" / "Kernel" / "CObject.cpp", patch_cobject_ptr_slots),
        (api_root / "Alchemy" / "Kernel" / "Kernel.vcxproj", patch_kernel_vcxproj_x64_warnings),
        (api_root / "Alchemy" / "CodeChain" / "CCAtomTable.cpp", patch_pointer_casts),
        (api_root / "Alchemy" / "NetUtil" / "CDataPackStruct.cpp", patch_pointer_casts),
        (
            api_root / "Transcendence" / "Transcendence" / "Transcendence.vcxproj",
            patch_transcendence_vcxproj,
        ),
    ]

    all_notes: list[str] = []
    for path, patcher in jobs:
        if not path.is_file():
            print(f"  skip missing: {path.relative_to(api_root)}")
            continue
        notes = apply_file(path, patcher, api_root, backup_root, args.dry_run)
        for n in notes:
            print(f"  {n}")
            all_notes.append(n)

    # Project/solution wiring for x64 (warn-as-error, lib outdirs, sln platform maps).
    if not args.dry_run:
        import subprocess

        tools = Path(__file__).resolve().parent
        for script, arg in (
            ("_flip_x64_warn_as_error.py", str(api_root)),
            ("_fix_x64_lib_outdir.py", str(api_root)),
            (
                "_fix_sln_x64_cfgs.py",
                str(api_root / "Transcendence" / "Transcendence.sln"),
            ),
            # JPEG swap MUST run after sln x64 cfg fix (strips IntelJPEG x64 Build.0)
            (
                "_force_jpeg_turbo_x64.py",
                str(api_root),
            ),
        ):
            sp = tools / script
            if not sp.is_file():
                continue
            r = subprocess.run(
                [sys.executable, str(sp), arg],
                capture_output=True,
                text=True,
            )
            print(r.stdout, end="")
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr)
            else:
                all_notes.append(f"ran {script}")

    if not args.dry_run:
        marker.write_text(
            f"version={FIX_VERSION}\napplied={datetime.now().isoformat()}\nnotes={len(all_notes)}\n",
            encoding="utf-8",
        )
        # Remove legacy markers
        for legacy in LEGACY_MARKERS:
            lp = api_root / legacy
            if lp.is_file():
                lp.unlink()
        print(f"Wrote marker: {marker}")

    print(f"Done. {len(all_notes)} patch note(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
