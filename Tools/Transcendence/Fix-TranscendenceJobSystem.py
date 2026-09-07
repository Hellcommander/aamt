#!/usr/bin/env python3
"""
Fix-TranscendenceJobSystem.py

In-engine job system overlay (Qud ModJob-style: capture → worker compute → main Apply).

- CJobSystem / IJob in Alchemy Kernel (persistent workers)
- DrainApplies from CHumanInterface::OnAnimate
- Boot/Shutdown around MainLoop in Run.cpp
- Consumer: async wreck-image rotation prefetch after sync GetWreckImage miss

Idempotent via .x64_jobsystem marker and TX_X64_JOBSYSTEM tags.

Usage:
  python Fix-TranscendenceJobSystem.py --api-root <workspace> [--force] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

MARKER_NAME = ".x64_jobsystem"
FIX_VERSION = 1

CJOBSYSTEM_CPP = r'''//	CJobSystem.cpp
//
//	Persistent worker pool + main-thread apply drain (TX_X64_JOBSYSTEM).
//	Applied by Fix-TranscendenceJobSystem.py — official trees stay untouched.

#include "PreComp.h"

static CJobSystem g_JobSystem;

CJobSystem &CJobSystem::Get (void)
	{
	return g_JobSystem;
	}

bool CJobSystem::Boot (int iThreadCount)

//	Boot
//
//	Start persistent workers. iThreadCount <= 0 picks a conservative default.

	{
	CSmartLock Lock(m_cs);

	if (m_bBooted)
		return true;

	m_dwOwnerThread = ::GetCurrentThreadId();

	if (iThreadCount <= 0)
		{
		SYSTEM_INFO SI;
		::GetSystemInfo(&SI);
		int iCores = (int)SI.dwNumberOfProcessors;
		iThreadCount = Max(1, Min(8, iCores - 1));
		}

	m_WorkAvail.Create();
	m_Quit.Create();

	m_Threads.InsertEmpty(iThreadCount);
	for (int i = 0; i < m_Threads.GetCount(); i++)
		m_Threads[i].hThread = ::kernelCreateThread(WorkerThreadStub, this);

	m_bBooted = true;
	::kernelDebugLogPattern("CJobSystem: booted %d worker(s)", iThreadCount);
	return true;
	}

void CJobSystem::Shutdown (void)

//	Shutdown
//
//	Stop workers and discard unfinished jobs (main-thread only).

	{
	AssertMainThread();

	m_cs.Lock();
	if (!m_bBooted)
		{
		m_cs.Unlock();
		return;
		}

	m_bBooted = false;
	m_Quit.Set();
	m_WorkAvail.Set();
	m_cs.Unlock();

	if (m_Threads.GetCount() > 0)
		{
		HANDLE *pThreads = new HANDLE [m_Threads.GetCount()];
		for (int i = 0; i < m_Threads.GetCount(); i++)
			pThreads[i] = m_Threads[i].hThread;

		::WaitForMultipleObjects(m_Threads.GetCount(), pThreads, TRUE, 5000);
		delete [] pThreads;

		for (int i = 0; i < m_Threads.GetCount(); i++)
			::CloseHandle(m_Threads[i].hThread);
		m_Threads.DeleteAll();
		}

	m_cs.Lock();
	while (m_ComputeQueue.GetCount() > 0)
		{
		delete m_ComputeQueue.Head();
		m_ComputeQueue.Dequeue();
		}
	for (int i = 0; i < m_ApplyQueue.GetCount(); i++)
		delete m_ApplyQueue[i];
	m_ApplyQueue.DeleteAll();
	m_iComputePending = 0;
	m_iApplyPending = 0;
	m_cs.Unlock();

	::kernelDebugLogPattern("CJobSystem: shutdown");
	}

DWORD CJobSystem::Submit (IJob *pJob)

//	Submit
//
//	Capture on caller (main), then queue Compute for workers.

	{
	if (pJob == NULL)
		return 0;

	AssertMainThread();

	if (!m_bBooted)
		{
		delete pJob;
		return 0;
		}

	try
		{
		pJob->Capture();
		}
	catch (...)
		{
		::kernelDebugLogPattern("CJobSystem: Capture exception");
		delete pJob;
		return 0;
		}

	m_cs.Lock();
	DWORD dwID = ++m_dwNextID;
	pJob->SetJobID(dwID);
	m_ComputeQueue.Enqueue(pJob);
	m_iComputePending++;
	m_cs.Unlock();

	m_WorkAvail.Set();
	return dwID;
	}

int CJobSystem::DrainApplies (int iMaxCount)

//	DrainApplies
//
//	Run Apply callbacks on the main thread.

	{
	AssertMainThread();

	if (iMaxCount <= 0)
		return 0;

	int iRan = 0;
	while (iRan < iMaxCount)
		{
		IJob *pJob = NULL;

		m_cs.Lock();
		if (m_ApplyQueue.GetCount() == 0)
			{
			m_cs.Unlock();
			break;
			}

		pJob = m_ApplyQueue[0];
		m_ApplyQueue.Delete(0);
		m_iApplyPending = Max(0, m_iApplyPending - 1);
		m_cs.Unlock();

		try
			{
			pJob->Apply();
			}
		catch (...)
			{
			::kernelDebugLogPattern("CJobSystem: Apply exception (job %d)", pJob->GetJobID());
			}

		delete pJob;
		iRan++;
		}

	return iRan;
	}

int CJobSystem::GetPendingComputeCount (void) const
	{
	return m_iComputePending;
	}

int CJobSystem::GetPendingApplyCount (void) const
	{
	return m_iApplyPending;
	}

void CJobSystem::AssertMainThread (void) const
	{
	ASSERT(m_dwOwnerThread == 0 || m_dwOwnerThread == ::GetCurrentThreadId());
	}

IJob *CJobSystem::TakeComputeJob (void)
	{
	CSmartLock Lock(m_cs);
	if (m_ComputeQueue.GetCount() == 0)
		return NULL;

	IJob *pJob = m_ComputeQueue.Head();
	m_ComputeQueue.Dequeue();
	m_iComputePending = Max(0, m_iComputePending - 1);
	return pJob;
	}

void CJobSystem::EnqueueApply (IJob *pJob)
	{
	CSmartLock Lock(m_cs);
	m_ApplyQueue.Insert(pJob);
	m_iApplyPending++;
	}

void CJobSystem::WorkerThread (void)
	{
	HANDLE Events[2];
	Events[0] = m_WorkAvail.GetWaitObject();
	Events[1] = m_Quit.GetWaitObject();

	while (true)
		{
		DWORD dwWait = ::WaitForMultipleObjects(2, Events, FALSE, INFINITE);
		if (dwWait == WAIT_OBJECT_0 + 1)
			return;

		while (true)
			{
			if (m_Quit.IsSet())
				return;

			IJob *pJob = TakeComputeJob();
			if (pJob == NULL)
				{
				m_cs.Lock();
				if (m_ComputeQueue.GetCount() == 0)
					m_WorkAvail.Reset();
				m_cs.Unlock();
				break;
				}

			try
				{
				pJob->Compute();
				}
			catch (...)
				{
				::kernelDebugLogPattern("CJobSystem: Compute exception (job %d)", pJob->GetJobID());
				}

			EnqueueApply(pJob);
			}
		}
	}
'''

WRECK_JOB_APPEND = r'''

// TX_X64_JOBSYSTEM ----------------------------------------------------------------

class CWreckImagePrefetchJob : public IJob
	{
	public:
		CWreckImagePrefetchJob (const CShipwreckDesc *pDesc,
				CShipClass *pClass,
				DWORD dwGen,
				const TArray<int> &Frames) :
				m_pDesc(pDesc),
				m_pClass(pClass),
				m_dwGen(dwGen),
				m_Frames(Frames)
			{ }

		virtual ~CWreckImagePrefetchJob (void)
			{
			for (int i = 0; i < m_Results.GetCount(); i++)
				delete m_Results[i];
			ClearPending();
			}

		virtual void Compute (void) override
			{
			for (int i = 0; i < m_Frames.GetCount(); i++)
				{
				CObjectImageArray *pImage = new CObjectImageArray;
				if (m_pDesc->CreateWreckImage(m_pClass, m_Frames[i], *pImage))
					m_Results.Insert(pImage);
				else
					delete pImage;
				}
			}

		virtual void Apply (void) override
			{
			if (m_pDesc == NULL || m_pClass == NULL)
				{
				ClearPending();
				return;
				}

			if (m_dwGen != m_pDesc->m_dwAsyncGen)
				{
				ClearPending();
				return;
				}

			for (int i = 0; i < m_Frames.GetCount(); i++)
				{
				if (i >= m_Results.GetCount() || m_Results[i] == NULL)
					continue;

				bool bInserted = false;
				CObjectImageArray *pSlot = m_pDesc->m_WreckImages.SetAt(m_Frames[i], &bInserted);
				if (bInserted && pSlot)
					*pSlot = *m_Results[i];
				}

			ClearPending();
			}

	private:
		void ClearPending (void)
			{
			if (m_pClass == NULL || m_bClearedPending)
				return;
			m_bClearedPending = true;

			DWORD dwUNID = m_pClass->GetUNID();
			CSmartLock Lock(CShipwreckDesc::g_csWreckPrefetchPending);
			for (int i = 0; i < m_Frames.GetCount(); i++)
				CShipwreckDesc::g_WreckPrefetchPending.DeleteAt(
						CShipwreckDesc::MakeWreckPrefetchKey(dwUNID, m_Frames[i]));
			}

		const CShipwreckDesc *m_pDesc;
		CShipClass *m_pClass;
		DWORD m_dwGen;
		TArray<int> m_Frames;
		TArray<CObjectImageArray *> m_Results;
		bool m_bClearedPending = false;
	};

CCriticalSection CShipwreckDesc::g_csWreckPrefetchPending;
TSortMap<DWORD, bool> CShipwreckDesc::g_WreckPrefetchPending;

DWORD CShipwreckDesc::MakeWreckPrefetchKey (DWORD dwUNID, int iFrame)
	{
	return (dwUNID << 8) | (DWORD)(iFrame & 0xff);
	}

void CShipwreckDesc::ScheduleWreckImagePrefetch (const CShipClass *pClass, int iFrameCount, int iHaveFrame) const

//	ScheduleWreckImagePrefetch
//
//	Queue worker jobs to build other rotation wreck images (TX_X64_JOBSYSTEM).

	{
	if (pClass == NULL || iFrameCount <= 1)
		return;
	if (!CJobSystem::Get().IsBooted())
		return;

	TArray<int> Frames;
	DWORD dwUNID = pClass->GetUNID();

		{
		CSmartLock Lock(g_csWreckPrefetchPending);
		const int iMaxPrefetch = 8;
		for (int i = 0; i < iFrameCount && Frames.GetCount() < iMaxPrefetch; i++)
			{
			if (i == iHaveFrame)
				continue;
			if (m_WreckImages.GetAt(i) != NULL)
				continue;

			DWORD dwKey = MakeWreckPrefetchKey(dwUNID, i);
			if (g_WreckPrefetchPending.GetAt(dwKey) != NULL)
				continue;

			g_WreckPrefetchPending.SetAt(dwKey, true);
			Frames.Insert(i);
			}
		}

	if (Frames.GetCount() == 0)
		return;

	CJobSystem::Get().Submit(
			new CWreckImagePrefetchJob(this, const_cast<CShipClass *>(pClass), m_dwAsyncGen, Frames));
	}
'''


def backup_file(path: Path, backup_root: Path, api_root: Path) -> None:
    rel = path.relative_to(api_root)
    dest = backup_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, dest)


def write_text(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def patch_replace(
    path: Path,
    old: str,
    new: str,
    note: str,
    notes: list[str],
    dry_run: bool,
    backup_root: Path,
    api_root: Path,
    already_token: str | None = "TX_X64_JOBSYSTEM",
) -> bool:
    if not path.is_file():
        notes.append(f"missing: {path.name} ({note})")
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    if already_token and already_token in text and (
        "DrainApplies" in note
        or "Boot CJobSystem" in note
        or "Shutdown CJobSystem" in note
        or "m_SimClock" in note
        or "prefetch" in note.lower()
    ):
        # Force re-run after Sync may leave prior overlays; treat as OK.
        if "CJobSystem" in text or "ScheduleWreckImagePrefetch" in text or "DrainApplies" in text:
            notes.append(f"already: {note}")
            return True
    if old not in text:
        notes.append(f"NO MATCH: {note}")
        return False
    if not dry_run:
        backup_file(path, backup_root, api_root)
        nl = "\r\n" if "\r\n" in text else "\n"
        path.write_bytes(text.replace(old, new, 1).replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
    notes.append(note)
    return True


def patch_kernel_h(api_root: Path, notes: list[str], dry_run: bool, backup_root: Path) -> None:
    path = api_root / "Alchemy" / "Include" / "Kernel.h"
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "class CJobSystem" in text and "TX_X64_JOBSYSTEM" in text:
        notes.append("Kernel.h: CJobSystem already")
        return

    anchor = """		CManualEvent m_WorkAvail;
		CManualEvent m_WorkCompleted;
		CManualEvent m_Quit;
	};

//	Initialization functions (Kernel.cpp)"""

    insert = """		CManualEvent m_WorkAvail;
		CManualEvent m_WorkCompleted;
		CManualEvent m_Quit;
	};

//	TX_X64_JOBSYSTEM: persistent jobs (capture → compute → main Apply)

class IJob
	{
	public:
		virtual ~IJob (void) { }
		virtual void Capture (void) { }
		virtual void Compute (void) = 0;
		virtual void Apply (void) = 0;

		DWORD GetJobID (void) const { return m_dwJobID; }
		void SetJobID (DWORD dwID) { m_dwJobID = dwID; }

	private:
		DWORD m_dwJobID = 0;
	};

class CJobSystem
	{
	public:
		static CJobSystem &Get (void);

		bool Boot (int iThreadCount = 0);
		void Shutdown (void);
		bool IsBooted (void) const { return m_bBooted; }

		DWORD Submit (IJob *pJob);
		int DrainApplies (int iMaxCount = 64);

		int GetPendingComputeCount (void) const;
		int GetPendingApplyCount (void) const;

	private:
		struct SThreadDesc
			{
			HANDLE hThread;
			};

		void AssertMainThread (void) const;
		IJob *TakeComputeJob (void);
		void EnqueueApply (IJob *pJob);
		void WorkerThread (void);

		static DWORD WINAPI WorkerThreadStub (LPVOID pData)
			{ ((CJobSystem *)pData)->WorkerThread(); return 0; }

		bool m_bBooted = false;
		DWORD m_dwOwnerThread = 0;
		DWORD m_dwNextID = 0;
		mutable CCriticalSection m_cs = CCriticalSection();
		int m_iComputePending = 0;
		int m_iApplyPending = 0;

		TArray<SThreadDesc> m_Threads;
		TQueue<IJob *> m_ComputeQueue;
		TArray<IJob *> m_ApplyQueue;
		CManualEvent m_WorkAvail;
		CManualEvent m_Quit;
	};

//	Initialization functions (Kernel.cpp)"""

    if anchor not in text:
        notes.append("NO MATCH: Kernel.h CThreadPool trailer")
        return
    if not dry_run:
        backup_file(path, backup_root, api_root)
        nl = "\r\n" if "\r\n" in text else "\n"
        path.write_bytes(text.replace(anchor, insert, 1).replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
    notes.append("Kernel.h: IJob + CJobSystem")


def patch_kernel_vcxproj(api_root: Path, notes: list[str], dry_run: bool, backup_root: Path) -> None:
    path = api_root / "Alchemy" / "Kernel" / "Kernel.vcxproj"
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "CJobSystem.cpp" in text:
        notes.append("Kernel.vcxproj: CJobSystem.cpp already")
        return
    old = '    <ClCompile Include="CThreadPool.cpp" />\n'
    new = '    <ClCompile Include="CThreadPool.cpp" />\n    <ClCompile Include="CJobSystem.cpp" />\n'
    if old not in text:
        notes.append("NO MATCH: Kernel.vcxproj CThreadPool.cpp")
        return
    if not dry_run:
        backup_file(path, backup_root, api_root)
        nl = "\r\n" if "\r\n" in text else "\n"
        path.write_bytes(text.replace(old, new, 1).replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
    notes.append("Kernel.vcxproj: add CJobSystem.cpp")


def write_jobsystem_cpp(api_root: Path, notes: list[str], dry_run: bool, backup_root: Path) -> None:
    path = api_root / "Alchemy" / "Kernel" / "CJobSystem.cpp"
    if path.is_file() and "TX_X64_JOBSYSTEM" in path.read_text(encoding="utf-8", errors="ignore"):
        notes.append("CJobSystem.cpp: already present")
        return
    if path.is_file() and not dry_run:
        backup_file(path, backup_root, api_root)
    write_text(path, CJOBSYSTEM_CPP, dry_run)
    notes.append("CJobSystem.cpp: written")


def patch_hi_and_run(api_root: Path, notes: list[str], dry_run: bool, backup_root: Path) -> None:
    hi = api_root / "Mammoth" / "TSUI" / "CHumanInterface.cpp"
    hi_text = hi.read_text(encoding="utf-8", errors="ignore") if hi.is_file() else ""
    if "TX_X64_JOBSYSTEM" in hi_text and "DrainApplies" in hi_text:
        notes.append("CHumanInterface.cpp: DrainApplies already")
    else:
        patch_replace(
            hi,
            """void CHumanInterface::OnAnimate (void)

//	OnAnimate
//
//	Paint an animation frame

	{
	int i;

	//	If minimized, bail out

	if (m_ScreenMgr.IsMinimized())
		return;""",
            """void CHumanInterface::OnAnimate (void)

//	OnAnimate
//
//	Paint an animation frame

	{
	int i;

	// TX_X64_JOBSYSTEM: main-thread Apply drain (before paint/sim)
	if (CJobSystem::Get().IsBooted())
		CJobSystem::Get().DrainApplies();

	//	If minimized, bail out

	if (m_ScreenMgr.IsMinimized())
		return;""",
            "CHumanInterface.cpp: DrainApplies",
            notes,
            dry_run,
            backup_root,
            api_root,
        )

    path = api_root / "Mammoth" / "TSUI" / "Run.cpp"
    run_text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    if "TX_X64_JOBSYSTEM" in run_text and "CJobSystem::Get().Boot" in run_text:
        notes.append("Run.cpp: Boot/Shutdown CJobSystem already")
        return

    patch_replace(
        path,
        """	if (g_pHI->m_pController->HIInit(&sError) != NOERROR)
		{
		::MessageBox(g_pHI->m_hWnd, sError.GetASCIIZPointer(), g_pHI->m_Options.sAppName.GetASCIIZPointer(), MB_OK);
		::DestroyWindow(g_pHI->m_hWnd);
		return;
		}

	//	Event loop until we quit.

	g_pHI->MainLoop();""",
        """	if (g_pHI->m_pController->HIInit(&sError) != NOERROR)
		{
		::MessageBox(g_pHI->m_hWnd, sError.GetASCIIZPointer(), g_pHI->m_Options.sAppName.GetASCIIZPointer(), MB_OK);
		::DestroyWindow(g_pHI->m_hWnd);
		return;
		}

	// TX_X64_JOBSYSTEM: persistent worker pool for capture/compute/apply jobs
	CJobSystem::Get().Boot();

	//	Event loop until we quit.

	g_pHI->MainLoop();""",
        "Run.cpp: Boot CJobSystem",
        notes,
        dry_run,
        backup_root,
        api_root,
    )

    patch_replace(
        path,
        """	g_pHI->MainLoop();

	//	Done

	Destroy();
	}""",
        """	g_pHI->MainLoop();

	// TX_X64_JOBSYSTEM
	CJobSystem::Get().Shutdown();

	//	Done

	Destroy();
	}""",
        "Run.cpp: Shutdown CJobSystem",
        notes,
        dry_run,
        backup_root,
        api_root,
    )


def patch_shipwreck(api_root: Path, notes: list[str], dry_run: bool, backup_root: Path) -> None:
    hdr = api_root / "Mammoth" / "Include" / "TSEShipClass.h"
    cpp = api_root / "Mammoth" / "TSE" / "CShipwreckDesc.cpp"

    text = hdr.read_text(encoding="utf-8", errors="ignore")
    if "ScheduleWreckImagePrefetch" in text and "TX_X64_JOBSYSTEM" in text:
        notes.append("TSEShipClass.h: wreck prefetch already")
    else:
        patch_replace(
            hdr,
            """//	Wreck Descriptor -----------------------------------------------------------

class CShipwreckDesc
	{
	public:""",
            """//	Wreck Descriptor -----------------------------------------------------------

class CWreckImagePrefetchJob;	// TX_X64_JOBSYSTEM

class CShipwreckDesc
	{
	public:
		friend class CWreckImagePrefetchJob;	// TX_X64_JOBSYSTEM
""",
            "TSEShipClass.h: friend prefetch job",
            notes,
            dry_run,
            backup_root,
            api_root,
        )

        patch_replace(
            hdr,
            """		bool CreateWreckImage (const CShipClass *pClass, int iRotationFrame, CObjectImageArray &Result) const;
		void InitDamageImage (void) const;
		bool IsWreckChanceSet (int *retiChance) const;
		void LoadXMLBool (const CXMLElement &Desc, const CString &sAttrib, bool &retbValue);

		static constexpr int DAMAGE_IMAGE_COUNT =		10;""",
            """		bool CreateWreckImage (const CShipClass *pClass, int iRotationFrame, CObjectImageArray &Result) const;
		void InitDamageImage (void) const;
		bool IsWreckChanceSet (int *retiChance) const;
		void LoadXMLBool (const CXMLElement &Desc, const CString &sAttrib, bool &retbValue);
		void ScheduleWreckImagePrefetch (const CShipClass *pClass, int iFrameCount, int iHaveFrame) const;	// TX_X64_JOBSYSTEM

		static DWORD MakeWreckPrefetchKey (DWORD dwUNID, int iFrame);	// TX_X64_JOBSYSTEM

		static constexpr int DAMAGE_IMAGE_COUNT =		10;""",
            "TSEShipClass.h: ScheduleWreckImagePrefetch",
            notes,
            dry_run,
            backup_root,
            api_root,
        )

        patch_replace(
            hdr,
            """		mutable TSortMap<int, CObjectImageArray> m_WreckImages;	//	Wreck image for each rotation frame index""",
            """		mutable TSortMap<int, CObjectImageArray> m_WreckImages;	//	Wreck image for each rotation frame index
		mutable DWORD m_dwAsyncGen = 0;							// TX_X64_JOBSYSTEM

		static CCriticalSection g_csWreckPrefetchPending;		// TX_X64_JOBSYSTEM
		static TSortMap<DWORD, bool> g_WreckPrefetchPending;	// TX_X64_JOBSYSTEM""",
            "TSEShipClass.h: async gen + pending map",
            notes,
            dry_run,
            backup_root,
            api_root,
        )

    cpp_text = cpp.read_text(encoding="utf-8", errors="ignore")
    if "ScheduleWreckImagePrefetch" in cpp_text and "CWreckImagePrefetchJob" in cpp_text:
        notes.append("CShipwreckDesc.cpp: prefetch consumer already")
        return

    patch_replace(
        cpp,
        """void CShipwreckDesc::CleanUp (void)

//	CleanUp
//
//	Clean up images to free up space.

	{
	m_pInherited = NULL;
	m_WreckImages.DeleteAll();
	}""",
        """void CShipwreckDesc::CleanUp (void)

//	CleanUp
//
//	Clean up images to free up space.

	{
	m_pInherited = NULL;
	m_dwAsyncGen++;	// TX_X64_JOBSYSTEM
	m_WreckImages.DeleteAll();
	}""",
        "CShipwreckDesc.cpp: CleanUp bump gen",
        notes,
        dry_run,
        backup_root,
        api_root,
    )

    patch_replace(
        cpp,
        """bool CShipwreckDesc::CreateWreckImage (const CShipClass *pClass, int iRotationFrame, CObjectImageArray &Result) const

//	CreateWreckImage
//
//	Initializes Result. Returns FALSE if we failed.

	{
	int i;

	//	Get the original ship class image""",
        """bool CShipwreckDesc::CreateWreckImage (const CShipClass *pClass, int iRotationFrame, CObjectImageArray &Result) const

//	CreateWreckImage
//
//	Initializes Result. Returns FALSE if we failed.

	{
	// TX_X64_JOBSYSTEM: mathRandom / damage bitmap are process-global
	static CCriticalSection s_csWreckImageGen;
	CSmartLock Lock(s_csWreckImageGen);

	int i;

	//	Get the original ship class image""",
        "CShipwreckDesc.cpp: CreateWreckImage CS",
        notes,
        dry_run,
        backup_root,
        api_root,
    )

    patch_replace(
        cpp,
        """	if (bNotInCache)
		{
		if (!CreateWreckImage(pClass, iRotationFrame, *pImage))
			{
			//	This should never happen. But if it does, we're ready for it.
			m_WreckImages.DeleteAt(iRotationFrame);
			return NULL;
			}
		}

	//	Mark to indicate in use

	pImage->MarkImage();""",
        """	if (bNotInCache)
		{
		if (!CreateWreckImage(pClass, iRotationFrame, *pImage))
			{
			//	This should never happen. But if it does, we're ready for it.
			m_WreckImages.DeleteAt(iRotationFrame);
			return NULL;
			}

		// TX_X64_JOBSYSTEM: prefetch other rotations off the main thread
		ScheduleWreckImagePrefetch(pClass, iFrameCount, iRotationFrame);
		}

	//	Mark to indicate in use

	pImage->MarkImage();""",
        "CShipwreckDesc.cpp: prefetch after miss",
        notes,
        dry_run,
        backup_root,
        api_root,
    )

    # Append job + Schedule implementation
    if not dry_run:
        backup_file(cpp, backup_root, api_root)
        text2 = cpp.read_text(encoding="utf-8", errors="ignore")
        if "CWreckImagePrefetchJob" not in text2:
            nl = "\r\n" if "\r\n" in text2 else "\n"
            text2 = text2.rstrip() + "\n" + WRECK_JOB_APPEND
            cpp.write_bytes(text2.replace("\r\n", "\n").replace("\n", nl).encode("utf-8"))
            notes.append("CShipwreckDesc.cpp: append prefetch job")
    else:
        notes.append("CShipwreckDesc.cpp: append prefetch job (dry-run)")


def main() -> int:
    ap = argparse.ArgumentParser(description="x64 job system overlay (workspace)")
    ap.add_argument("--api-root", required=True)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_root = Path(args.api_root).resolve()
    if not (api_root / "Transcendence" / "Transcendence.sln").is_file():
        print(f"ERROR: not an API tree: {api_root}", file=sys.stderr)
        return 2

    marker = api_root / MARKER_NAME
    if marker.is_file() and not args.force:
        print(f"job system already applied ({marker.name}). Use --force to re-run.")
        return 0

    backup_root = api_root / "_jobsystem_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"API/workspace: {api_root}")
    print(f"Backups:       {backup_root}")
    if args.dry_run:
        print("DRY RUN")

    notes: list[str] = []
    patch_kernel_h(api_root, notes, args.dry_run, backup_root)
    write_jobsystem_cpp(api_root, notes, args.dry_run, backup_root)
    patch_kernel_vcxproj(api_root, notes, args.dry_run, backup_root)
    patch_hi_and_run(api_root, notes, args.dry_run, backup_root)
    patch_shipwreck(api_root, notes, args.dry_run, backup_root)

    for n in notes:
        print(f"  {n}")

    fails = [n for n in notes if n.startswith("NO MATCH") or n.startswith("missing")]
    if fails and not args.dry_run:
        print(f"ERROR: {len(fails)} patch failure(s)", file=sys.stderr)
        return 1

    if not args.dry_run:
        marker.write_text(
            f"version={FIX_VERSION}\napplied={datetime.now().isoformat()}\nnotes={len(notes)}\n",
            encoding="utf-8",
        )
        print(f"Wrote marker: {marker}")

    print(f"Done job system. {len(notes)} note(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
