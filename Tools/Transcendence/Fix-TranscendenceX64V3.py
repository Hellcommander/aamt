#!/usr/bin/env python3
"""
Fix-TranscendenceX64V3.py

Pointer-safety + capacity overlays for an API build *workspace* (not official trees).

Applies on top of v2 (INT_PTR containers / mathRound). Idempotent via .x64_autofix_v3.

Usage:
  python Fix-TranscendenceX64V3.py --api-root <workspace_or_tree> [--force] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER_NAME = ".x64_autofix_v3"
FIX_VERSION = 3
LEGACY_MARKERS = (".x64_autofix_v1", ".x64_autofix_v2")


def backup_file(path: Path, backup_root: Path, api_root: Path) -> None:
    rel = path.relative_to(api_root)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def apply_file(path: Path, patcher, api_root: Path, backup_root: Path, dry_run: bool) -> list[str]:
    if not path.is_file():
        return [f"skip missing: {path}"]
    text = path.read_text(encoding="utf-8", errors="ignore")
    new_text, notes = patcher(text)
    if new_text == text or not notes:
        return notes or [f"no change: {path.name}"]
    if not dry_run:
        backup_file(path, backup_root, api_root)
        nl = "\r\n" if "\r\n" in text else "\n"
        path.write_bytes(new_text.replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
    return notes


# ----- TLisp / CodeChain -----


def patch_codechain_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_CCINTEGER_INTPTR" in text and "GetIntPtrValue" in text:
        return text, ["CodeChain.h: already INT_PTR CCInteger + GetIntPtrValue"]

    # Prefer safer model: keep GetIntegerValue as int for math; add GetIntPtrValue for obj refs.
    if "GetIntPtrValue" not in text:
        text2, n = re.subn(
            r"virtual int GetIntegerValue \(void\) const \{ return 0; \}",
            "virtual int GetIntegerValue (void) const { return 0; }\n"
            "\t\tvirtual INT_PTR GetIntPtrValue (void) const { return (INT_PTR)GetIntegerValue(); } // TX_X64_CCINTEGER_INTPTR",
            text,
            count=1,
        )
        if n:
            text = text2
            notes.append("CodeChain.h: ICCItem::GetIntPtrValue added")

    old = """class CCInteger : public CCNumeral
	{
	public:
		CCInteger (void);

		int GetValue (void) { return m_iValue; }
		void SetValue (int iValue) { m_iValue = iValue; }

		//	ICCItem virtuals
		virtual ICCItem *Clone(CCodeChain *pCC) override;
		virtual bool IsInteger () const override { return true; }
		virtual bool IsDouble () const override { return false; }
		virtual int GetIntegerValue () const override { return m_iValue; }
		virtual double GetDoubleValue () const override { return double(m_iValue); }
		virtual CString GetStringValue () const override { return strFromInt(m_iValue); }
		virtual ValueTypes GetValueType () const override { return Integer;  }
		virtual CString Print (DWORD dwFlags = 0) const override;
		virtual void Reset () override;

	protected:
		virtual void DestroyItem () override;

	private:
		int m_iValue;							//	Value of 32-bit integer
	};"""

    new = """class CCInteger : public CCNumeral
	{
	public:
		CCInteger (void);

		INT_PTR GetValue (void) { return m_iValue; }
		void SetValue (INT_PTR iValue) { m_iValue = iValue; }

		//	ICCItem virtuals
		virtual ICCItem *Clone(CCodeChain *pCC) override;
		virtual bool IsInteger () const override { return true; }
		virtual bool IsDouble () const override { return false; }
		virtual int GetIntegerValue () const override { return (int)m_iValue; }
		virtual INT_PTR GetIntPtrValue () const override { return m_iValue; } // TX_X64_CCINTEGER_INTPTR
		virtual double GetDoubleValue () const override { return double(m_iValue); }
		virtual CString GetStringValue () const override { return strFromInt((int)m_iValue); }
		virtual ValueTypes GetValueType () const override { return Integer;  }
		virtual CString Print (DWORD dwFlags = 0) const override;
		virtual void Reset () override;

	protected:
		virtual void DestroyItem () override;

	private:
		INT_PTR m_iValue;						// TX_X64_CCINTEGER_INTPTR: pointer-sized int / obj ref
	};"""

    # If previous v3 pass widened GetIntegerValue to INT_PTR, roll that API surface back.
    text = text.replace(
        "virtual INT_PTR GetIntegerValue (void) const { return 0; } // TX_X64_CCINTEGER_INTPTR",
        "virtual int GetIntegerValue (void) const { return 0; }\n"
        "\t\tvirtual INT_PTR GetIntPtrValue (void) const { return (INT_PTR)GetIntegerValue(); } // TX_X64_CCINTEGER_INTPTR",
    )
    text = text.replace(
        "virtual INT_PTR GetIntegerValue () const override { return m_iValue; }",
        "virtual int GetIntegerValue () const override { return (int)m_iValue; }\n"
        "\t\tvirtual INT_PTR GetIntPtrValue () const override { return m_iValue; }",
    )
    text = text.replace(
        "virtual INT_PTR GetIntegerValue () const override { return (INT_PTR)m_dValue; }",
        "virtual int GetIntegerValue () const override { return int(m_dValue); }",
    )
    text = text.replace(
        "virtual INT_PTR GetIntegerValue (void) const override { return 0; }",
        "virtual int GetIntegerValue (void) const override { return 0; }",
    )
    text = text.replace(
        "virtual INT_PTR GetIntegerValue (void) const override { return 1; }",
        "virtual int GetIntegerValue (void) const override { return 1; }",
    )
    text = text.replace(
        "virtual INT_PTR GetIntegerValue (void) const override { return (INT_PTR)strToInt(m_sValue, 0); }",
        "virtual int GetIntegerValue (void) const override { return strToInt(m_sValue, 0); }",
    )

    if old in text:
        text = text.replace(old, new, 1)
        notes.append("CodeChain.h: CCInteger INT_PTR storage + GetIntPtrValue")
    elif "INT_PTR m_iValue" in text and "GetIntPtrValue () const override { return m_iValue; }" in text:
        notes.append("CodeChain.h: CCInteger already patched")
    else:
        # Fallback pieces
        if "INT_PTR m_iValue" not in text:
            text2, n = re.subn(
                r"\tint m_iValue;\s*//\s*Value of 32-bit integer",
                "\tINT_PTR m_iValue;\t\t\t\t\t\t// TX_X64_CCINTEGER_INTPTR",
                text,
                count=1,
            )
            if n:
                text = text2
                notes.append("CodeChain.h: m_iValue INT_PTR")
        if "void SetValue (INT_PTR" not in text:
            text = text.replace(
                "void SetValue (int iValue) { m_iValue = iValue; }",
                "void SetValue (INT_PTR iValue) { m_iValue = iValue; }",
                1,
            )
            text = text.replace(
                "int GetValue (void) { return m_iValue; }",
                "INT_PTR GetValue (void) { return m_iValue; }",
                1,
            )
        if "GetIntPtrValue () const override { return m_iValue; }" not in text and "class CCInteger" in text:
            text = text.replace(
                "virtual int GetIntegerValue () const override { return (int)m_iValue; }",
                "virtual int GetIntegerValue () const override { return (int)m_iValue; }\n"
                "\t\tvirtual INT_PTR GetIntPtrValue () const override { return m_iValue; }",
                1,
            )
            if "GetIntPtrValue () const override { return m_iValue; }" not in text:
                text = text.replace(
                    "virtual int GetIntegerValue () const override { return m_iValue; }",
                    "virtual int GetIntegerValue () const override { return (int)m_iValue; }\n"
                    "\t\tvirtual INT_PTR GetIntPtrValue () const override { return m_iValue; }",
                    1,
                )
            notes.append("CodeChain.h: GetIntPtrValue on CCInteger")

    text2, n = re.subn(
        r"static ICCItem \*CreateInteger \(int iValue\);",
        "static ICCItem *CreateInteger (INT_PTR iValue); // TX_X64_CCINTEGER_INTPTR",
        text,
        count=1,
    )
    if n:
        text = text2
        notes.append("CodeChain.h: CreateInteger(INT_PTR)")
    # already patched CreateInteger line
    if "CreateInteger (INT_PTR iValue)" in text and "CreateInteger(INT_PTR)" not in " ".join(notes):
        notes.append("CodeChain.h: CreateInteger(INT_PTR) present")

    text2, n = re.subn(
        r"void SetIntegerAt \(const CString &sKey, int iValue\);",
        "void SetIntegerAt (const CString &sKey, INT_PTR iValue); // TX_X64_V3: pointer-sized ints (obj refs)",
        text,
    )
    if n:
        text = text2
        notes.append("CodeChain.h: SetIntegerAt(INT_PTR)")
    elif "SetIntegerAt (const CString &sKey, INT_PTR iValue)" in text:
        notes.append("CodeChain.h: SetIntegerAt(INT_PTR) present")

    return text, notes


def patch_codechain_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"ICCItem \*CCodeChain::CreateInteger \(int iValue\)",
        "ICCItem *CCodeChain::CreateInteger (INT_PTR iValue)",
        text,
        count=1,
    )
    if n:
        text = text2
        notes.append("CodeChain.cpp: CreateInteger(INT_PTR)")
    elif "CreateInteger (INT_PTR iValue)" in text:
        notes.append("CodeChain.cpp: CreateInteger(INT_PTR) present")
    return text, notes


def patch_iccitem_set_integer_at(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"void ICCItem::SetIntegerAt \(const CString &sKey, int iValue\)",
        "void ICCItem::SetIntegerAt (const CString &sKey, INT_PTR iValue)",
        text,
    )
    if n:
        text = text2
        notes.append("ICCItem.cpp: SetIntegerAt(INT_PTR)")
    elif "SetIntegerAt (const CString &sKey, INT_PTR iValue)" in text:
        notes.append("ICCItem.cpp: SetIntegerAt(INT_PTR) present")
    return text, notes


def patch_set_integer_at_obj_casts(text: str) -> tuple[str, list[str]]:
    """SetIntegerAt(key, (int)<obj-ptr>) -> INT_PTR for object refs packed into structs."""
    notes = []
    pat = re.compile(
        r"SetIntegerAt\(([^,]+),\s*\(int\)(m_pAnchor|DamageCtx\.pObj|DamageCtx\.pCause|"
        r"pAttacker|pOrderGiver|pFound|Source\.GetObj\(\)|Source\.GetSecondaryObj\(\)|"
        r"pObj|pTarget|pCause|pAnchor|m_p[A-Z][A-Za-z0-9_]*)\)"
    )
    text2, n = pat.subn(r"SetIntegerAt(\1, (INT_PTR)\2)", text)
    if n:
        text = text2
        notes.append(f"SetIntegerAt((INT_PTR)obj) x{n}")
    return text, notes


def patch_ccutil_obj_pointers(text: str) -> tuple[str, list[str]]:
    notes = []
    old_from = """CSpaceObject *CreateObjFromItem (const ICCItem *pItem, DWORD dwFlags)
	{
	if (pItem == NULL)
		return NULL;

	int iArg = pItem->GetIntegerValue();
	if (iArg == 0)
		return NULL;

	CSpaceObject *pObj;
	try
		{
		pObj = reinterpret_cast<CSpaceObject *>(iArg);
		}"""

    new_from = """CSpaceObject *CreateObjFromItem (const ICCItem *pItem, DWORD dwFlags)
	{
	if (pItem == NULL)
		return NULL;

	INT_PTR iArg = pItem->GetIntPtrValue(); // TX_X64_OBJPTR
	if (iArg == 0)
		return NULL;

	CSpaceObject *pObj;
	try
		{
		pObj = reinterpret_cast<CSpaceObject *>(iArg);
		}"""

    if old_from in text:
        text = text.replace(old_from, new_from, 1)
        notes.append("CCUtil.cpp: CreateObjFromItem GetIntPtrValue")
    else:
        # Upgrade prior v3 INT_PTR GetIntegerValue variant
        text2, n = re.subn(
            r"INT_PTR iArg = pItem->GetIntegerValue\(\); // TX_X64_OBJPTR",
            "INT_PTR iArg = pItem->GetIntPtrValue(); // TX_X64_OBJPTR",
            text,
            count=1,
        )
        if n:
            text = text2
            notes.append("CCUtil.cpp: CreateObjFromItem use GetIntPtrValue")
        else:
            text2, n = re.subn(
                r"int iArg = pItem->GetIntegerValue\(\);",
                "INT_PTR iArg = pItem->GetIntPtrValue(); // TX_X64_OBJPTR",
                text,
                count=1,
            )
            if n:
                text = text2
                notes.append("CCUtil.cpp: CreateObjFromItem INT_PTR (fallback)")

    text2, n = re.subn(
        r"return CC\.CreateInteger\(\(int\)pObj\);",
        "return CC.CreateInteger((INT_PTR)pObj); // TX_X64_OBJPTR",
        text,
    )
    if n:
        text = text2
        notes.append(f"CCUtil.cpp: CreateObjPointer INT_PTR x{n}")
    text2, n = re.subn(
        r"return CC\.CreateInteger\(\(INT_PTR\)pObj\);(?! // TX_X64_OBJPTR)",
        "return CC.CreateInteger((INT_PTR)pObj); // TX_X64_OBJPTR",
        text,
    )

    return text, notes


def patch_create_integer_obj_casts(text: str) -> tuple[str, list[str]]:
    """Rewrite CreateInteger((int)<ptr-like>) -> CreateInteger((INT_PTR)...) for object refs."""
    notes = []
    # Common object pointer variable names packed into integers
    pat = re.compile(
        r"CreateInteger\(\(int\)(pObj|pTarget|pBestTarget|pGate|pOrderGiver|pRef|pHitObj|"
        r"pSource|pSender|pStation|pShip|pSectionObj|pTargetObj|pObj2|pEffect|"
        r"pSecondarySource|pBase|pDest|pAttacker|pDefender|pCenter|pOther)\)"
    )
    text2, n = pat.subn(r"CreateInteger((INT_PTR)\1)", text)
    if n:
        text = text2
        notes.append(f"CreateInteger((INT_PTR)obj) x{n}")

    # Generic: CreateInteger((int)pXxx) where Xxx looks like object (heuristic)
    pat2 = re.compile(r"CreateInteger\(\(int\)(p[A-Z][A-Za-z0-9_]*)\)")
    # Only rewrite if not already INT_PTR and name suggests pointer-to-object (not iValue etc.)
    def repl(m: re.Match) -> str:
        name = m.group(1)
        # Skip obvious non-object: pCC, pArgs, pList, pItem (ICCItem*), pCtx, pUNID-ish
        skip = {
            "pCC",
            "pArgs",
            "pList",
            "pItem",
            "pCtx",
            "pData",
            "pEntry",
            "pKey",
            "pValue",
            "pResult",
            "pError",
            "pString",
            "pVector",
            "pTable",
        }
        if name in skip:
            return m.group(0)
        return f"CreateInteger((INT_PTR){name})"

    text2, n2 = pat2.subn(repl, text)
    # Count only real changes
    if n2 and text2 != text:
        # recount actual INT_PTR introductions beyond first pass
        added = text2.count("CreateInteger((INT_PTR)") - text.count("CreateInteger((INT_PTR)")
        text = text2
        if added > 0:
            notes.append(f"CreateInteger heuristic INT_PTR x{added}")

    # this / m_pXxx / Ctx.pXxx packed as object refs
    for pat_extra, label in (
        (r"CreateInteger\(\(int\)this\)", "CreateInteger((INT_PTR)this)"),
        (r"CreateInteger\(\(int\)(m_p[A-Z][A-Za-z0-9_]*)\)", r"CreateInteger((INT_PTR)\1)"),
        (r"CreateInteger\(\(int\)(Ctx\.p[A-Z][A-Za-z0-9_]*)\)", r"CreateInteger((INT_PTR)\1)"),
        (
            r"CreateInteger\(\(int\)(m_pPlayer->GetShip\(\))\)",
            r"CreateInteger((INT_PTR)\1)",
        ),
    ):
        text2, n = re.subn(pat_extra, label, text)
        if n:
            text = text2
            notes.append(f"CreateInteger extra {label[:40]} x{n}")

    return text, notes


# ----- CObject / DXSparseMask -----


def patch_cobject_remaining(text: str) -> tuple[str, list[str]]:
    notes = []
    reps = [
        (
            r"\*\(\(DWORD \*\)pDest\) = \(DWORD\)pBlock;",
            "*((UINT_PTR *)pDest) = (UINT_PTR)pBlock; // TX_X64_V3",
        ),
        (
            r"\*\(\(DWORD \*\)pDest\) = \*\(\(DWORD \*\)pSource\);",
            "*((UINT_PTR *)pDest) = *((UINT_PTR *)pSource); // TX_X64_V3",
        ),
        (
            r"ASSERT\(\*\(\(DWORD \*\)pDest\) == 0\);",
            "ASSERT(*((UINT_PTR *)pDest) == 0); // TX_X64_V3",
        ),
    ]
    for pat, repl in reps:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"CObject.cpp: {pat[:40]}... x{n}")
    # EMBED_OBJ pointer advance: when copying vtable-ish via DWORD while advancing LPVOID
    # Fix pairs that still use DWORD for LPVOID-sized fields after v2
    text2, n = re.subn(
        r"\(\(DWORD \*\)pDest\)",
        "((UINT_PTR *)pDest)",
        text,
    )
    # Only if we introduced new ones beyond existing UINT_PTR - careful not to double-replace
    # Actually re.subn on already UINT_PTR would break. Only replace DWORD * forms.
    return text, notes


def patch_cobject_dword_ptr_slots(text: str) -> tuple[str, list[str]]:
    """Fix pointer-sized DATADESC slots only (not int/DWORD value copies)."""
    notes = []
    if "TX_X64_V3_COBJECT" in text:
        return text, ["CObject.cpp: already v3 marked"]

    original = text
    # Unarchive ALLOC_MEMORY stores a heap pointer
    text, n1 = re.subn(
        r"\*\(\(DWORD \*\)pDest\) = \(DWORD\)pBlock;",
        "*((UINT_PTR *)pDest) = (UINT_PTR)pBlock;",
        text,
    )
    # EMBED_OBJ / ALLOC copies of LPVOID-sized fields: only when advancing by sizeof(LPVOID)
    # Match blocks that already use UINT_PTR from v2 partially; finish remaining DWORD pointer stores
    # near sizeof(LPVOID) advances.
    lines = text.splitlines(keepends=True)
    out = []
    for i, line in enumerate(lines):
        stripped = line
        # If this line stores via DWORD* and nearby (+/- 3 lines) mentions sizeof(LPVOID) or MemAlloc pointer
        window = "".join(lines[max(0, i - 3) : min(len(lines), i + 4)])
        if "*((DWORD *)" in line and (
            "sizeof(LPVOID)" in window
            or "MemAlloc" in window
            or "pDestMem" in line
            or "pSourceMem" in line
            or "pCopy" in line
            or "pBlock" in line
        ):
            stripped = (
                line.replace("*((DWORD *)pDest)", "*((UINT_PTR *)pDest)")
                .replace("*((DWORD *)pSource)", "*((UINT_PTR *)pSource)")
                .replace("*((DWORD *)pPos)", "*((UINT_PTR *)pPos)")
                .replace("(DWORD)pBlock", "(UINT_PTR)pBlock")
                .replace("(DWORD)pDestMem", "(UINT_PTR)pDestMem")
                .replace("(DWORD)pCopy", "(UINT_PTR)pCopy")
                .replace("(BYTE *)*((DWORD *)", "(BYTE *)*((UINT_PTR *)")
            )
        out.append(stripped)
    text = "".join(out)

    if text != original:
        if "// TX_X64_V3_COBJECT" not in text:
            text = text.replace(
                "//\tCObject.cpp",
                "//\tCObject.cpp\n// TX_X64_V3_COBJECT: UINT_PTR for LPVOID-sized DATADESC slots only",
                1,
            )
        notes.append(f"CObject.cpp: LPVOID-sized slots -> UINT_PTR (n1={n1})")

    # CIntArray is the only ALLOC_SIZE32 user and stores INT_PTR elements on x64
    text2, n = re.subn(
        r"iAllocSize = sizeof\(DWORD\) \* \(\*\(\(int \*\)pSource\)\);",
        "iAllocSize = sizeof(INT_PTR) * (*((int *)pSource)); // TX_X64_V3_ALLOC_SIZE",
        text,
    )
    if n:
        text = text2
        notes.append(f"CObject.cpp: ALLOC_SIZE32 sizeof(INT_PTR) x{n}")
    text2, n = re.subn(
        r"iAllocSize = sizeof\(DWORD\) \* \(\*\(\(int \*\)pDest\)\);",
        "iAllocSize = sizeof(INT_PTR) * (*((int *)pDest)); // TX_X64_V3_ALLOC_SIZE",
        text,
    )
    if n:
        text = text2
        notes.append(f"CObject.cpp: ALLOC_SIZE32 unarchive sizeof(INT_PTR) x{n}")

    return text, notes


def patch_composite_image_selector(text: str) -> tuple[str, list[str]]:
    """CCompositeImageSelector stored CShipClass*/CItemType* in DWORD — truncates on x64."""
    notes = []
    if "TX_X64_V3_SELECTOR" in text and "UINT_PTR dwExtra" in text:
        return text, ["CCompositeImageSelector: already UINT_PTR dwExtra"]

    text2, n = re.subn(
        r"DWORD dwExtra;\s*//\s*Either 0 or a pointer to CItemType or CShipClass\.",
        "UINT_PTR dwExtra;					// TX_X64_V3_SELECTOR: pointer to CItemType or CShipClass (was DWORD)",
        text,
    )
    if n:
        text = text2
        notes.append("TSEImages.h: dwExtra UINT_PTR")

    reps = [
        (r"dwExtra = \(DWORD\)pItemType", "dwExtra = (UINT_PTR)pItemType"),
        (r"dwExtra = \(DWORD\)pWreckClass", "dwExtra = (UINT_PTR)pWreckClass"),
        (r"dwExtra = \(DWORD\)pShipClass", "dwExtra = (UINT_PTR)pShipClass"),
        (
            r"dwExtra = \(DWORD\)Ctx\.GetUniverse\(\)\.FindItemType",
            "dwExtra = (UINT_PTR)Ctx.GetUniverse().FindItemType",
        ),
        (
            r"dwExtra = \(DWORD\)Ctx\.GetUniverse\(\)\.FindShipClass",
            "dwExtra = (UINT_PTR)Ctx.GetUniverse().FindShipClass",
        ),
        (r"\(CItemType \*\)pEntry->dwExtra", "(CItemType *)(UINT_PTR)pEntry->dwExtra"),
        (r"\(CShipClass \*\)pEntry->dwExtra", "(CShipClass *)(UINT_PTR)pEntry->dwExtra"),
        (r"\(CItemType \*\)m_Sel\[i\]\.dwExtra", "(CItemType *)(UINT_PTR)m_Sel[i].dwExtra"),
        (r"\(CShipClass \*\)m_Sel\[i\]\.dwExtra", "(CShipClass *)(UINT_PTR)m_Sel[i].dwExtra"),
    ]
    for pat, repl in reps:
        text2, n = re.subn(pat, repl, text)
        if n:
            text = text2
            notes.append(f"selector cast {pat[:32]} x{n}")

    return text, notes


def patch_dxsparsemask(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_SPARSEMASK" in text:
        return text, ["DXSparseMask.h: already patched"]

    old = """		static void *EncodeByteArray (BYTE *pValue) { DWORD dwEncoded = ((DWORD)pValue) | typeByteArray; return (void *)dwEncoded; }
		static void *EncodeNodeArray (CNode *pValue) { DWORD dwEncoded = ((DWORD)pValue) | typeNodeArray; return (void *)dwEncoded; }
		static BYTE DecodeByte (void *pCode) { return (BYTE)((DWORD)pCode >> 24); }
		static BYTE *DecodeByteArray (void *pCode) { return (BYTE *)((DWORD)pCode & ~TYPE_MASK); }
		static CNode *DecodeNodeArray (void *pCode) { return (CNode *)((DWORD)pCode & ~TYPE_MASK); }
		static ETypes DecodeType (void *pCode) { return (ETypes)((DWORD)pCode & TYPE_MASK); }"""

    new = """		// TX_X64_V3_SPARSEMASK: tag pointers with UINT_PTR (low bits), not DWORD
		static void *EncodeByteArray (BYTE *pValue) { UINT_PTR uEncoded = ((UINT_PTR)pValue) | typeByteArray; return (void *)uEncoded; }
		static void *EncodeNodeArray (CNode *pValue) { UINT_PTR uEncoded = ((UINT_PTR)pValue) | typeNodeArray; return (void *)uEncoded; }
		static BYTE DecodeByte (void *pCode) { return (BYTE)((UINT_PTR)pCode >> 24); }
		static BYTE *DecodeByteArray (void *pCode) { return (BYTE *)((UINT_PTR)pCode & ~TYPE_MASK); }
		static CNode *DecodeNodeArray (void *pCode) { return (CNode *)((UINT_PTR)pCode & ~TYPE_MASK); }
		static ETypes DecodeType (void *pCode) { return (ETypes)((UINT_PTR)pCode & TYPE_MASK); }"""

    if old in text:
        text = text.replace(old, new, 1)
        notes.append("DXSparseMask.h: UINT_PTR tagging")
    else:
        text2 = text
        text2 = text2.replace("((DWORD)pValue)", "((UINT_PTR)pValue)")
        text2 = text2.replace("((DWORD)pCode)", "((UINT_PTR)pCode)")
        text2 = text2.replace("(DWORD)pCode", "(UINT_PTR)pCode")
        if text2 != text:
            text = text2
            if "TX_X64_V3_SPARSEMASK" not in text:
                text = text.replace(
                    "class DXSparseMask",
                    "// TX_X64_V3_SPARSEMASK\nclass DXSparseMask",
                    1,
                )
            notes.append("DXSparseMask.h: UINT_PTR tagging (fallback)")
    return text, notes


def patch_gwl_userdata(text: str) -> tuple[str, list[str]]:
    notes = []
    if "GWL_USERDATA" not in text and "SetWindowLong(" not in text:
        return text, []
    text2 = text
    text2 = text2.replace("GWL_USERDATA", "GWLP_USERDATA")
    text2 = re.sub(
        r"::SetWindowLong\(([^,]+),\s*GWLP_USERDATA,\s*\(LONG\)",
        r"::SetWindowLongPtr(\1, GWLP_USERDATA, (LONG_PTR)",
        text2,
    )
    text2 = re.sub(
        r"::GetWindowLong\(([^,]+),\s*GWLP_USERDATA\)",
        r"::GetWindowLongPtr(\1, GWLP_USERDATA)",
        text2,
    )
    if text2 != text:
        notes.append(f"{'file'}: GWLP_USERDATA / LongPtr")
        text = text2
    return text, notes


# ----- Capacity -----


def patch_cstring_store_max(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"#define STORE_ALLOC_MAX\s+\(64 \* 1024 \* 1024\)",
        "#define STORE_ALLOC_MAX\t\t(256 * 1024 * 1024)\t// TX_X64_V3 capacity",
        text,
    )
    if n:
        return text2, ["CString.cpp: STORE_ALLOC_MAX 64MB -> 256MB"]
    text2, n = re.subn(
        r"(STORE_ALLOC_MAX\s*=\s*)\(64 \* 1024 \* 1024\)",
        r"\1(256 * 1024 * 1024) /* TX_X64_V3 */",
        text,
    )
    if n:
        return text2, ["CString.cpp: STORE_ALLOC_MAX bumped"]
    # literal form variations
    text2, n = re.subn(
        r"64 \* 1024 \* 1024",
        "256 * 1024 * 1024 /* TX_X64_V3 STORE_ALLOC_MAX */",
        text,
        count=1,
    )
    if n and "STORE_ALLOC" in text:
        return text2, ["CString.cpp: STORE_ALLOC_MAX bumped (heuristic)"]
    return text, notes


def patch_codechain_pool(text: str) -> tuple[str, list[str]]:
    notes = []
    text2, n = re.subn(
        r"#define BACKBONE_SIZE\s+1024",
        "#define BACKBONE_SIZE\t\t\t4096\t\t// TX_X64_V3 capacity",
        text,
    )
    if n:
        text = text2
        notes.append("BACKBONE_SIZE 1024 -> 4096")
    return text, notes


# ----- Variadic / strPattern (x86 stack walk is invalid on x64) -----


def patch_strpattern_subst(text: str) -> tuple[str, list[str]]:
    """strPatternSubst must use va_start; x86 '&sLine + sizeof' breaks Debug.log on x64."""
    notes = []
    if "TX_X64_V3_VARARGS" in text:
        return text, ["Pattern.cpp: va_list already patched"]

    old = """CString Kernel::strPatternSubst (CString sLine, ...)

	{
	char *pArgs;
	CString sParsedLine;

	pArgs = (char *) &sLine + sizeof(sLine);
	sParsedLine = strPattern(sLine, (void **)pArgs);
	return sParsedLine;
	}"""

    new = """CString Kernel::strPatternSubst (CString sLine, ...)

	{
	// TX_X64_V3_VARARGS: x64 ABI does not place varargs after sLine on the stack
	va_list pArgs;
	CString sParsedLine;

	va_start(pArgs, sLine);
	sParsedLine = strPattern(sLine, (LPVOID *)pArgs);
	va_end(pArgs);
	return sParsedLine;
	}"""

    if old in text:
        text = text.replace(old, new, 1)
        notes.append("Pattern.cpp: strPatternSubst va_list")
    else:
        text2, n = re.subn(
            r"pArgs = \(char \*\) &sLine \+ sizeof\(sLine\);",
            "va_list pArgs;\n\tva_start(pArgs, sLine); // TX_X64_V3_VARARGS",
            text,
            count=1,
        )
        if n:
            text = text2.replace(
                "sParsedLine = strPattern(sLine, (void **)pArgs);\n\treturn sParsedLine;",
                "sParsedLine = strPattern(sLine, (LPVOID *)pArgs);\n\tva_end(pArgs);\n\treturn sParsedLine;",
                1,
            )
            text = text.replace("char *pArgs;\n\tCString sParsedLine;\n\n\tva_list", "CString sParsedLine;\n\n\tva_list", 1)
            notes.append("Pattern.cpp: strPatternSubst va_list (fallback)")

    # INT64 / double advance: on x64 each is one LPVOID slot, not two
    # Old code did pArgs++; pArgs++; for %lld and %r (x86 8-byte = 2x DWORD ptr)
    old_ll = """						//	Next

						pArgs++;
						pArgs++;
						}
					else
						{
						int *pInt = (int *)pArgs;"""
    new_ll = """						//	Next (TX_X64_V3_VARARGS: one LPVOID slot per 8-byte value)

						pArgs += AlignUp(sizeof(INT64), sizeof(LPVOID)) / sizeof(LPVOID);
						}
					else
						{
						int *pInt = (int *)pArgs;"""
    if old_ll in text:
        text = text.replace(old_ll, new_ll, 1)
        notes.append("Pattern.cpp: %lld arg advance AlignUp")

    old_r = """					//	Next

					pArgs++;
					pArgs++;

					pPos++;
					iLength--;
					}
				else if (*pPos == 'x' || *pPos == 'X')"""
    new_r = """					//	Next (TX_X64_V3_VARARGS)

					pArgs += AlignUp(sizeof(double), sizeof(LPVOID)) / sizeof(LPVOID);

					pPos++;
					iLength--;
					}
				else if (*pPos == 'x' || *pPos == 'X')"""
    if old_r in text:
        text = text.replace(old_r, new_r, 1)
        notes.append("Pattern.cpp: %r arg advance AlignUp")

    if "stdarg.h" not in text and notes:
        text = text.replace(
            '#include "PreComp.h"',
            '#include "PreComp.h"\n#include <stdarg.h> // TX_X64_V3_VARARGS',
            1,
        )
        notes.append("Pattern.cpp: include stdarg.h")

    return text, notes


def patch_kernel_varargs(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_VARARGS" in text and "va_start(pArgs, pszLine)" in text:
        return text, ["Kernel.cpp: kernelDebugLogPattern va_list already"]

    old = """		char *pArgs = (char *)&pszLine + sizeof(pszLine);
		sParsedLine = strPattern(CString(pszLine, (int)::strlen(pszLine), TRUE), (void **)pArgs);"""
    new = """		va_list pArgs; // TX_X64_V3_VARARGS
		va_start(pArgs, pszLine);
		sParsedLine = strPattern(CString(pszLine, (int)::strlen(pszLine), TRUE), (LPVOID *)pArgs);
		va_end(pArgs);"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("Kernel.cpp: kernelDebugLogPattern va_list")
    if "stdarg.h" not in text and notes:
        # Kernel.cpp likely has PreComp only
        if '#include "PreComp.h"' in text:
            text = text.replace(
                '#include "PreComp.h"',
                '#include "PreComp.h"\n#include <stdarg.h> // TX_X64_V3_VARARGS',
                1,
            )
    return text, notes


def patch_ilog_varargs(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_VARARGS" in text and "va_start(pArgs, pszLine)" in text:
        return text, ["ILog.cpp: LogOutput va_list already"]

    old = """	char *pArgs = (char *)&pszLine + sizeof(pszLine);
	sParsedLine = strPattern(CString(pszLine, ::strlen(pszLine), TRUE), (void **)pArgs);"""
    new = """	va_list pArgs; // TX_X64_V3_VARARGS
	va_start(pArgs, pszLine);
	sParsedLine = strPattern(CString(pszLine, ::strlen(pszLine), TRUE), (LPVOID *)pArgs);
	va_end(pArgs);"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("ILog.cpp: LogOutput va_list")
    if "stdarg.h" not in text and notes:
        text = text.replace(
            '#include "PreComp.h"',
            '#include "PreComp.h"\n#include <stdarg.h> // TX_X64_V3_VARARGS',
            1,
        )
    return text, notes


def patch_dib_getinfo(text: str) -> tuple[str, list[str]]:
    """bmBits cast through int truncates high half of pointers on x64 (font/DIB load crash)."""
    notes = []
    if "TX_X64_V3_DIBBITS" in text:
        return text, ["DIB.cpp: bmBits INT_PTR already"]

    old = "*retpBase = (void *) (((int) ds.dsBm.bmBits) + (ds.dsBm.bmWidthBytes * (ds.dsBm.bmHeight - 1)));"
    new = "*retpBase = (void *) (((BYTE *) ds.dsBm.bmBits) + (ds.dsBm.bmWidthBytes * (ds.dsBm.bmHeight - 1))); // TX_X64_V3_DIBBITS"
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("DIB.cpp: dibGetInfo bmBits via BYTE* (not int)")
    else:
        text2, n = re.subn(
            r"\*retpBase = \(void \*\) \(\(\(int\)\s*ds\.dsBm\.bmBits\)\s*\+",
            "*retpBase = (void *) (((BYTE *) ds.dsBm.bmBits) + // TX_X64_V3_DIBBITS\n\t\t\t\t",
            text,
            count=1,
        )
        # That might break paren balance - prefer simple replace of (int) cast only
        if n == 0:
            text2, n = re.subn(
                r"\(\(int\)\s*ds\.dsBm\.bmBits\)",
                "((BYTE *) ds.dsBm.bmBits) /* TX_X64_V3_DIBBITS */",
                text,
                count=1,
            )
        if n:
            text = text2
            notes.append("DIB.cpp: dibGetInfo bmBits via BYTE* (fallback)")
    return text, notes


def patch_assert_log(text: str) -> tuple[str, list[str]]:
    """Log ASSERT failures before DebugBreak so smoke runs leave a breadcrumb in AssertFail.log."""
    notes = []
    if "TX_X64_V3_ASSERT_LOG" in text:
        return text, ["Kernel.h: ASSERT log already"]

    old = (
        "#define ASSERT(exp)\t\t\t\t\t\t\\\n"
        "\t\t\t{\t\t\t\t\t\t\t\\\n"
        "\t\t\tif (!(exp))\t\t\t\t\t\\\n"
        "\t\t\t\tDebugBreak();\t\t\t\\\n"
        "\t\t\t}"
    )
    new = (
        "#define ASSERT(exp)\t\t\t\t\t\t\\\n"
        "\t\t\t{\t\t\t\t\t\t\t\\\n"
        "\t\t\tif (!(exp))\t\t\t\t\t\\\n"
        "\t\t\t\t{\t\t\t\t\t\t\\\n"
        "\t\t\t\t/* TX_X64_V3_ASSERT_LOG */ \\\n"
        "\t\t\t\tchar _txAssertBuf[768]; \\\n"
        "\t\t\t\twsprintfA(_txAssertBuf, \"ASSERT failed @ %s:%d\\r\\n\", __FILE__, __LINE__); \\\n"
        "\t\t\t\tOutputDebugStringA(_txAssertBuf); \\\n"
        "\t\t\t\t{ HANDLE _txH = ::CreateFileA(\"AssertFail.log\", FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL); \\\n"
        "\t\t\t\t  if (_txH != INVALID_HANDLE_VALUE) { DWORD _txW = 0; ::WriteFile(_txH, _txAssertBuf, (DWORD)lstrlenA(_txAssertBuf), &_txW, NULL); ::CloseHandle(_txH); } } \\\n"
        "\t\t\t\t}\t\t\t\t\t\t\\\n"
        "\t\t\t}"
    )
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("Kernel.h: ASSERT logs to AssertFail.log (no DebugBreak)")
    # Upgrade prior v3 that still DebugBreaks
    if "TX_X64_V3_ASSERT_LOG" in text and "DebugBreak();" in text:
        text2 = re.sub(
            r"(/\* TX_X64_V3_ASSERT_LOG[^*]*\*/[\s\S]*?)DebugBreak\(\);\s*\\",
            r"\1/* DebugBreak omitted */ \\",
            text,
            count=1,
        )
        # Simpler: remove DebugBreak line inside ASSERT block marked TX_X64
        text2, n = re.subn(
            r"(TX_X64_V3_ASSERT_LOG[\s\S]{0,400}?)(\t+DebugBreak\(\);\s*\\\n)",
            r"\1",
            text,
            count=1,
        )
        if n and text2 != text:
            text = text2
            notes.append("Kernel.h: removed DebugBreak from ASSERT")
    return text, notes


def patch_interaction_level_assert(text: str) -> tuple[str, list[str]]:
    """Replace CInteractionLevel ASSERT with clamp+log (DebugBreak blocked main menu)."""
    notes = []
    if "TX_X64_V3_INTERACTION" in text:
        return text, ["TSEWeaponFireDesc.h: interaction clamp already"]

    old = """		CInteractionLevel (int iInteraction) :
				m_iInteraction(iInteraction)
			{
			ASSERT(m_iInteraction == -1 || (m_iInteraction >= 0 && m_iInteraction <= 100));
			}"""

    new = """		CInteractionLevel (int iInteraction) :
				m_iInteraction(iInteraction)
			{
			// TX_X64_V3_INTERACTION: clamp out-of-range instead of DebugBreak in _DEBUG
			if (!(m_iInteraction == -1 || (m_iInteraction >= 0 && m_iInteraction <= 100)))
				{
				char _txBuf[256];
				wsprintfA(_txBuf, "CInteractionLevel clamp %d -> ", m_iInteraction);
				if (m_iInteraction < 0)
					m_iInteraction = 0;
				else
					m_iInteraction = 100;
				char _txBuf2[64];
				wsprintfA(_txBuf2, "%d\\r\\n", m_iInteraction);
				lstrcatA(_txBuf, _txBuf2);
				OutputDebugStringA(_txBuf);
				{ HANDLE _txH = ::CreateFileA("AssertFail.log", FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
				  if (_txH != INVALID_HANDLE_VALUE) { DWORD _txW = 0; ::WriteFile(_txH, _txBuf, (DWORD)lstrlenA(_txBuf), &_txW, NULL); ::CloseHandle(_txH); } }
				}
			}"""

    if old in text:
        text = text.replace(old, new, 1)
        notes.append("TSEWeaponFireDesc.h: CInteractionLevel clamp")
    return text, notes


# ----- Unbind sim/render from locked framerate -----


def patch_unbound_fps_tsui_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_bUncappedFrameRate" in text:
        return text, ["TSUI.h: uncappedFrameRate option already"]

    old_init = """			m_bUse60fps(false),
			m_iSoundVolume(DEFAULT_SOUND_VOLUME),
			m_bDebugVideo(false)
		{ }"""
    new_init = """			m_bUse60fps(false),
			m_bUncappedFrameRate(false),	// TX_X64_V3_UNBOUND_FPS
			m_iSoundVolume(DEFAULT_SOUND_VOLUME),
			m_bDebugVideo(false)
		{ }"""
    if old_init in text:
        text = text.replace(old_init, new_init, 1)
        notes.append("TSUI.h: SHIOptions m_bUncappedFrameRate init")

    old_field = """	bool m_bUse60fps;					//	If TRUE, run at 60 fps

	//	Sound options"""
    new_field = """	bool m_bUse60fps;					//	If TRUE, target 60 Hz sim steps (two frames per tick)
	bool m_bUncappedFrameRate;			// TX_X64_V3_UNBOUND_FPS: skip MainLoop Sleep

	//	Sound options"""
    if old_field in text:
        text = text.replace(old_field, new_field, 1)
        notes.append("TSUI.h: SHIOptions m_bUncappedFrameRate field")
    return text, notes


def patch_unbound_fps_run_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_bUncappedFrameRate" in text:
        return text, ["Run.cpp: uncapped MainLoop already"]

    old = """		//	Figure out how long until our next animation

#ifndef DEBUG_MAX_FRAME_RATE

		//	Wait

		DWORD dwNow = timeGetTime();
		if (dwNextFrame > dwNow)
			{
			::Sleep(dwNextFrame - dwNow);

			dwStartTime = dwNextFrame;
			}
		else
			dwStartTime = dwNow;
#endif
		}"""
    new = """		//	Figure out how long until our next animation

#if !defined(DEBUG_MAX_FRAME_RATE)
		// TX_X64_V3_UNBOUND_FPS: optional uncapped paint; sim uses CFixedSimClock
		if (!m_Options.m_bUncappedFrameRate)
			{
			DWORD dwNow = timeGetTime();
			if (dwNextFrame > dwNow)
				{
				::Sleep(dwNextFrame - dwNow);

				dwStartTime = dwNextFrame;
				}
			else
				dwStartTime = dwNow;
			}
		else
			{
			dwStartTime = timeGetTime();
			}
#endif
		}"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("Run.cpp: MainLoop respects m_bUncappedFrameRate")
    return text, notes


def patch_unbound_fps_game_settings_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "uncappedFrameRate" in text:
        return text, ["GameSettings.h: uncappedFrameRate already"]

    old = """			use60fps,						//	Run at 60 fps (two frames per tick)
			useMTSpritePaint,				//	Use multiple threads for painting sprites"""
    new = """			use60fps,						//	Run at 60 fps (two frames per tick)
			uncappedFrameRate,				// TX_X64_V3_UNBOUND_FPS: paint uncapped; sim fixed-step
			useMTSpritePaint,				//	Use multiple threads for painting sprites"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("GameSettings.h: uncappedFrameRate option")
    return text, notes


def patch_unbound_fps_game_settings_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "uncappedFrameRate" in text:
        return text, ["CGameSettings.cpp: uncappedFrameRate already"]

    old = """		{	"use60fps",					optionBoolean,	"true",		0	},
		{	"useMTSpritePaint",			optionBoolean,	"true",		0	},"""
    new = """		{	"use60fps",					optionBoolean,	"true",		0	},
		{	"uncappedFrameRate",		optionBoolean,	"true",		0	},	// TX_X64_V3_UNBOUND_FPS
		{	"useMTSpritePaint",			optionBoolean,	"true",		0	},"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("CGameSettings.cpp: uncappedFrameRate default true")
    return text, notes


def patch_unbound_fps_controller(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_bUncappedFrameRate" in text:
        return text, ["CTranscendenceController.cpp: uncapped wire already"]

    old = """	retOptions->m_bUse60fps = m_Settings.GetBoolean(CGameSettings::use60fps);
	retOptions->m_iSoundVolume = m_Settings.GetInteger(CGameSettings::soundVolume);"""
    new = """	retOptions->m_bUse60fps = m_Settings.GetBoolean(CGameSettings::use60fps);
	retOptions->m_bUncappedFrameRate = m_Settings.GetBoolean(CGameSettings::uncappedFrameRate);	// TX_X64_V3_UNBOUND_FPS
	retOptions->m_iSoundVolume = m_Settings.GetInteger(CGameSettings::soundVolume);"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("CTranscendenceController.cpp: wire uncappedFrameRate")
    return text, notes


def patch_unbound_fps_transcendence_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "class CFixedSimClock" in text:
        return text, ["Transcendence.h: CFixedSimClock already"]

    old = """const int g_iFramesPerSecond =				30;		//	Desired frames per second
const int FRAME_RATE_COUNT =				51;		//	number of statistics to keep (for debugging)

#define OBJID_CPLAYERSHIPCONTROLLER	MakeOBJCLASSID(100)"""
    new = """const int g_iFramesPerSecond =				30;		//	Desired frames per second
const int FRAME_RATE_COUNT =				51;		//	number of statistics to keep (for debugging)

// TX_X64_V3_UNBOUND_FPS: fixed-timestep clock (sim from real time, paint independent)
class CFixedSimClock
	{
	public:
		void Reset (void)
			{
			m_dwLastTime = 0;
			m_rAccumMs = 0.0;
			}

		int TakeUpdates (bool bUse60fps, CUniverse::EUpdateSpeeds iMode)
			{
			const Metric rMsPerUpdate = bUse60fps ? (1000.0 / 60.0) : (1000.0 / 30.0);
			const int iMaxUpdates = bUse60fps ? 12 : 6;

			DWORD dwNow = ::timeGetTime();
			if (m_dwLastTime == 0)
				{
				m_dwLastTime = dwNow;
				m_rAccumMs = 0.0;
				}

			if (iMode == CUniverse::updatePaused)
				{
				m_dwLastTime = dwNow;
				m_rAccumMs = 0.0;
				return 0;
				}

			if (iMode == CUniverse::updateSingleFrame)
				{
				m_dwLastTime = dwNow;
				m_rAccumMs = 0.0;
				return 1;
				}

			m_rAccumMs += (Metric)(dwNow - m_dwLastTime);
			m_dwLastTime = dwNow;

			if (m_rAccumMs > rMsPerUpdate * iMaxUpdates)
				m_rAccumMs = rMsPerUpdate * iMaxUpdates;

			int iUpdates = 0;
			while (m_rAccumMs >= rMsPerUpdate && iUpdates < iMaxUpdates)
				{
				m_rAccumMs -= rMsPerUpdate;
				iUpdates++;
				}

			return iUpdates;
			}

	private:
		DWORD m_dwLastTime = 0;
		Metric m_rAccumMs = 0.0;
	};

#define OBJID_CPLAYERSHIPCONTROLLER	MakeOBJCLASSID(100)"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("Transcendence.h: CFixedSimClock")
    return text, notes


def patch_unbound_fps_game_session_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_SimClock" in text:
        return text, ["GameSession.h: m_SimClock already"]

    old = """		CDockScreen m_CurrentDock;				//	Current dock screen
	};"""
    new = """		CDockScreen m_CurrentDock;				//	Current dock screen

		CFixedSimClock m_SimClock;				// TX_X64_V3_UNBOUND_FPS
	};"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("GameSession.h: m_SimClock")
    return text, notes


def patch_unbound_fps_intro_session_h(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_SimClock" in text:
        return text, ["IntroSession.h: m_SimClock already"]

    old = """		TSortMap<int, CShipClass *> m_ShipList;
		bool m_bShowAllShips = false;			//	If FALSE, we only show the lower half (by score)
	};"""
    new = """		TSortMap<int, CShipClass *> m_ShipList;
		bool m_bShowAllShips = false;			//	If FALSE, we only show the lower half (by score)

		CFixedSimClock m_SimClock;				// TX_X64_V3_UNBOUND_FPS
	};"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("IntroSession.h: m_SimClock")
    return text, notes


def patch_unbound_fps_game_session_animate(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_SimClock.TakeUpdates" in text:
        return text, ["GameSessionAnimate.cpp: fixed timestep already"]

    reps = [
        (
            """				//	Update the universe

				SetProgramState(psUpdating);
				bool bUpdated = g_pUniverse->Update(UpdateCtx, iUpdateMode);
				SetProgramState(psAnimating);

				if (iUpdateMode != CUniverse::updatePaused)
					{
					if (pPlayer)
						{
						pPlayer->Update(g_pUniverse->GetFrameTicks());

						if (pPlayer->GetSelectedTarget())
							m_HUD.Invalidate(hudTargeting);
						}
					}

				m_MessageDisplay.Update();

				//	Figure out how long it took to update

				if (m_Settings.GetBoolean(CGameSettings::debugVideo))
					{
					DWORD dwNow = ::GetTickCount();
					g_pTrans->m_iUpdateTime[g_pTrans->m_iFrameCount % FRAME_RATE_COUNT] = dwNow - dwStartTimer;
					dwStartTimer = dwNow;
					}

				//	Destroyed?

				if (g_pTrans->m_State == CTranscendenceWnd::gsDestroyed)
					{
					if (!g_pTrans->m_bPaused || g_pTrans->m_bPausedStep)
						{
						if (--g_pTrans->m_iCountdown == 0)
							g_pHI->HICommand(CONSTLIT("gameEndDestroyed"));
						g_pTrans->m_bPausedStep = false;
						}
					}

				break;
				}""",
            """				//	Update the universe (TX_X64_V3_UNBOUND_FPS: fixed timestep)

				SetProgramState(psUpdating);
				int iSimUpdates = m_SimClock.TakeUpdates(UpdateCtx.bUse60fps, iUpdateMode);
				for (int i = 0; i < iSimUpdates; i++)
					{
					g_pUniverse->Update(UpdateCtx, iUpdateMode);

					if (iUpdateMode != CUniverse::updatePaused)
						{
						if (pPlayer)
							{
							pPlayer->Update(g_pUniverse->GetFrameTicks());

							if (pPlayer->GetSelectedTarget())
								m_HUD.Invalidate(hudTargeting);
							}
						}

					if (g_pTrans->m_State == CTranscendenceWnd::gsDestroyed)
						{
						if (!g_pTrans->m_bPaused || g_pTrans->m_bPausedStep)
							{
							if (--g_pTrans->m_iCountdown == 0)
								g_pHI->HICommand(CONSTLIT("gameEndDestroyed"));
							g_pTrans->m_bPausedStep = false;
							}
						}
					}
				SetProgramState(psAnimating);

				m_MessageDisplay.Update();

				//	Figure out how long it took to update

				if (m_Settings.GetBoolean(CGameSettings::debugVideo))
					{
					DWORD dwNow = ::GetTickCount();
					g_pTrans->m_iUpdateTime[g_pTrans->m_iFrameCount % FRAME_RATE_COUNT] = dwNow - dwStartTimer;
					dwStartTimer = dwNow;
					}

				break;
				}""",
            "in-game Update loop",
        ),
        (
            """				//	Update the universe (at 1/4 rate)

				g_pUniverse->Update(UpdateCtx, CUniverse::updateSlowMotion);
				m_MessageDisplay.Update();
				m_CurrentDock.Update(g_pUniverse->GetFrameTicks());""",
            """				//	Update the universe (at 1/4 rate; TX_X64_V3_UNBOUND_FPS)

				int iDockUpdates = m_SimClock.TakeUpdates(UpdateCtx.bUse60fps, CUniverse::updateSlowMotion);
				for (int i = 0; i < iDockUpdates; i++)
					g_pUniverse->Update(UpdateCtx, CUniverse::updateSlowMotion);
				m_MessageDisplay.Update();
				m_CurrentDock.Update(g_pUniverse->GetFrameTicks());""",
            "docked Update loop",
        ),
        (
            """				//	Update the universe

				g_pUniverse->Update(UpdateCtx);
				m_MessageDisplay.Update();

				if (--g_pTrans->m_iCountdown == 0)
					{
					g_pHI->HICommand(CONSTLIT("gameInsideStargate"));
					g_pTrans->m_State = CTranscendenceWnd::gsWaitingForSystem;
					}

				break;
				}""",
            """				//	Update the universe (TX_X64_V3_UNBOUND_FPS)

				int iEnterUpdates = m_SimClock.TakeUpdates(UpdateCtx.bUse60fps, CUniverse::updateNormal);
				for (int i = 0; i < iEnterUpdates; i++)
					{
					g_pUniverse->Update(UpdateCtx);
					if (--g_pTrans->m_iCountdown == 0)
						{
						g_pHI->HICommand(CONSTLIT("gameInsideStargate"));
						g_pTrans->m_State = CTranscendenceWnd::gsWaitingForSystem;
						break;
						}
					}
				m_MessageDisplay.Update();

				break;
				}""",
            "entering-stargate Update",
        ),
        (
            """				//	Update the universe

				g_pUniverse->Update(UpdateCtx);
				m_MessageDisplay.Update();

				if (--g_pTrans->m_iCountdown == 0)
					{
					g_pHI->HICommand(CONSTLIT("gameLeaveStargate"));
					g_pTrans->m_State = CTranscendenceWnd::gsInGame;
					ExecuteCommandRefresh();
					}
				break;
				}""",
            """				//	Update the universe (TX_X64_V3_UNBOUND_FPS)

				int iLeaveUpdates = m_SimClock.TakeUpdates(UpdateCtx.bUse60fps, CUniverse::updateNormal);
				for (int i = 0; i < iLeaveUpdates; i++)
					{
					g_pUniverse->Update(UpdateCtx);
					if (--g_pTrans->m_iCountdown == 0)
						{
						g_pHI->HICommand(CONSTLIT("gameLeaveStargate"));
						g_pTrans->m_State = CTranscendenceWnd::gsInGame;
						ExecuteCommandRefresh();
						break;
						}
					}
				m_MessageDisplay.Update();
				break;
				}""",
            "leaving-stargate Update",
        ),
    ]

    for old, new, label in reps:
        if old in text:
            text = text.replace(old, new, 1)
            notes.append(f"GameSessionAnimate.cpp: {label}")
    return text, notes


def patch_unbound_fps_intro_session_cpp(text: str) -> tuple[str, list[str]]:
    notes = []
    if "TX_X64_V3_UNBOUND_FPS" in text and "m_SimClock.TakeUpdates" in text:
        return text, ["CIntroSession.cpp: fixed timestep already"]

    old = """	//	Update the universe

	SSystemUpdateCtx Ctx;
	Ctx.bUse60fps = m_Settings.GetBoolean(CGameSettings::use60fps);
	Ctx.bForceEventFiring = true;
	if (!g_pTrans->m_bPaused)
		{
		g_pUniverse->Update(Ctx);
		}"""
    new = """	//	Update the universe (TX_X64_V3_UNBOUND_FPS: fixed timestep)

	SSystemUpdateCtx Ctx;
	Ctx.bUse60fps = m_Settings.GetBoolean(CGameSettings::use60fps);
	Ctx.bForceEventFiring = true;
	if (g_pTrans->m_bPaused)
		{
		if (g_pTrans->m_bPausedStep)
			{
			int iUpdates = m_SimClock.TakeUpdates(Ctx.bUse60fps, CUniverse::updateSingleFrame);
			g_pTrans->m_bPausedStep = false;
			for (int i = 0; i < iUpdates; i++)
				g_pUniverse->Update(Ctx);
			}
		else
			m_SimClock.TakeUpdates(Ctx.bUse60fps, CUniverse::updatePaused);
		}
	else
		{
		int iUpdates = m_SimClock.TakeUpdates(Ctx.bUse60fps, CUniverse::updateNormal);
		for (int i = 0; i < iUpdates; i++)
			g_pUniverse->Update(Ctx);
		}"""
    if old in text:
        text = text.replace(old, new, 1)
        notes.append("CIntroSession.cpp: fixed timestep Update")
    return text, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="x64 v3 pointer-safety overlay (workspace)")
    ap.add_argument("--api-root", required=True, help="API tree or x64 build workspace root")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-capacity", action="store_true")
    args = ap.parse_args()

    api_root = Path(args.api_root).resolve()
    if not (api_root / "Transcendence" / "Transcendence.sln").is_file():
        print(f"ERROR: not an API tree: {api_root}", file=sys.stderr)
        return 2

    marker = api_root / MARKER_NAME
    if marker.is_file() and not args.force:
        print(f"x64 v3 already applied ({marker.name}). Use --force to re-run.")
        return 0

    game_root = api_root.parent.parent
    if not (game_root / "Tools" / "Transcendence").is_dir():
        game_root = api_root  # workspace may live under Tools
        backup_root = api_root / "_v3_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    else:
        backup_root = (
            game_root
            / "Tools"
            / "Transcendence"
            / "_ext_fix_backups"
            / f"x64_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    print(f"API/workspace: {api_root}")
    print(f"Backups:       {backup_root}")
    if args.dry_run:
        print("DRY RUN")

    jobs: list[tuple[Path, object]] = [
        (api_root / "Alchemy" / "Include" / "CodeChain.h", patch_codechain_h),
        (api_root / "Alchemy" / "CodeChain" / "CodeChain.cpp", patch_codechain_cpp),
        (api_root / "Alchemy" / "CodeChain" / "ICCItem.cpp", patch_iccitem_set_integer_at),
        (api_root / "Alchemy" / "Include" / "Kernel.h", patch_assert_log),
        (api_root / "Mammoth" / "Include" / "TSEWeaponFireDesc.h", patch_interaction_level_assert),
        (api_root / "Mammoth" / "TSE" / "CCUtil.cpp", patch_ccutil_obj_pointers),
        (api_root / "Mammoth" / "TSE" / "CCUtil.cpp", patch_set_integer_at_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CCExtensions.cpp", patch_create_integer_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CTLispConvert.cpp", patch_create_integer_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CSpaceObjectProperties.cpp", patch_create_integer_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CCreatePainterCtx.cpp", patch_set_integer_at_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CRangeTypeEvent.cpp", patch_set_integer_at_obj_casts),
        (api_root / "Mammoth" / "TSE" / "CUniverse.cpp", patch_create_integer_obj_casts),
        (api_root / "Mammoth" / "TSE" / "ShipProperties.cpp", patch_create_integer_obj_casts),
        (
            api_root / "Transcendence" / "Transcendence" / "CTranscendenceModel.cpp",
            patch_create_integer_obj_casts,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "Transcendence.h",
            patch_create_integer_obj_casts,
        ),
        (
            api_root / "Mammoth" / "Include" / "TSEImages.h",
            patch_composite_image_selector,
        ),
        (
            api_root / "Mammoth" / "TSE" / "CCompositeImageSelector.cpp",
            patch_composite_image_selector,
        ),
        (api_root / "Alchemy" / "Kernel" / "CObject.cpp", patch_cobject_dword_ptr_slots),
        (api_root / "Alchemy" / "Include" / "DXSparseMask.h", patch_dxsparsemask),
        (api_root / "Alchemy" / "Kernel" / "Pattern.cpp", patch_strpattern_subst),
        (api_root / "Alchemy" / "Kernel" / "Kernel.cpp", patch_kernel_varargs),
        (api_root / "Alchemy" / "Kernel" / "ILog.cpp", patch_ilog_varargs),
        (api_root / "Alchemy" / "Graphics" / "DIB.cpp", patch_dib_getinfo),
        (api_root / "Transcendence" / "TransData" / "CSimViewer.cpp", patch_gwl_userdata),
        (api_root / "Transcendence" / "TransData" / "Utilities.h", patch_gwl_userdata),
        (api_root / "Mammoth" / "TSUI" / "CMCIMixer.cpp", patch_gwl_userdata),
        # Unbind framerate (uncapped paint + fixed-timestep sim)
        (api_root / "Mammoth" / "Include" / "TSUI.h", patch_unbound_fps_tsui_h),
        (api_root / "Mammoth" / "TSUI" / "Run.cpp", patch_unbound_fps_run_cpp),
        (
            api_root / "Transcendence" / "Transcendence" / "GameSettings.h",
            patch_unbound_fps_game_settings_h,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "CGameSettings.cpp",
            patch_unbound_fps_game_settings_cpp,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "CTranscendenceController.cpp",
            patch_unbound_fps_controller,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "Transcendence.h",
            patch_unbound_fps_transcendence_h,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "GameSession.h",
            patch_unbound_fps_game_session_h,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "IntroSession.h",
            patch_unbound_fps_intro_session_h,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "GameSessionAnimate.cpp",
            patch_unbound_fps_game_session_animate,
        ),
        (
            api_root / "Transcendence" / "Transcendence" / "CIntroSession.cpp",
            patch_unbound_fps_intro_session_cpp,
        ),
    ]
    if not args.skip_capacity:
        jobs += [
            (api_root / "Alchemy" / "Kernel" / "CString.cpp", patch_cstring_store_max),
            (api_root / "Alchemy" / "CodeChain" / "CCItemPool.cpp", patch_codechain_pool),
            (api_root / "Alchemy" / "CodeChain" / "CConsPool.cpp", patch_codechain_pool),
        ]

    # Also scan Mammoth/Include headers for CreateInteger((int)pObj)
    for hdr in (api_root / "Mammoth" / "Include").glob("*.h"):
        jobs.append((hdr, patch_create_integer_obj_casts))

    all_notes: list[str] = []
    for path, patcher in jobs:
        for n in apply_file(path, patcher, api_root, backup_root, args.dry_run):
            print(f"  {n}")
            all_notes.append(n)

    if not args.dry_run:
        marker.write_text(
            f"version={FIX_VERSION}\napplied={datetime.now().isoformat()}\nnotes={len(all_notes)}\n"
            "note=overlay-workspace-ok-to-mix; official-trees-untouched-if-workspace\n",
            encoding="utf-8",
        )
        for legacy in LEGACY_MARKERS:
            # Keep v2 marker if present (v3 is additive); only remove v1
            if legacy.endswith("v1"):
                lp = api_root / legacy
                if lp.is_file():
                    lp.unlink()
        print(f"Wrote marker: {marker}")

    print(f"Done v3. {len(all_notes)} note(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
