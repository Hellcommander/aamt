#!/usr/bin/env python3
"""
Clean up stale RAG index lock files.
"""

import sys
import os
from pathlib import Path

# Add Shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Shared"))

try:
    from rag_system import RAGSystem
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("RAG system not available")

def clean_rag_lock(rag_index_path: Path):
    """Clean up stale RAG lock file."""
    # Try both possible lock file names
    lock_file1 = rag_index_path / "qud_source_index.faiss.lock"
    lock_file2 = rag_index_path / "qud_source_index.lock"
    
    # Use whichever exists
    if lock_file2.exists():
        lock_file = lock_file2
    elif lock_file1.exists():
        lock_file = lock_file1
    else:
        lock_file = None
    
    if lock_file is None or not lock_file.exists():
        print(f"  [RAG] No lock file found")
        return True
    
    print(f"  [RAG] Found lock file: {lock_file}")
    
    # Check if lock is stale
    try:
        with open(lock_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 1:
                pid_str = lines[0].strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    # Check if process is still running
                    try:
                        import psutil
                        if psutil.pid_exists(pid):
                            print(f"  [RAG] Lock file is held by running process (PID: {pid})")
                            print(f"  [RAG] Cannot remove lock - process is still active")
                            return False
                        else:
                            print(f"  [RAG] Lock file is stale (PID: {pid} no longer exists)")
                    except ImportError:
                        # psutil not available, try alternative method
                        if sys.platform == 'win32':
                            import subprocess
                            try:
                                result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                      capture_output=True, timeout=2)
                                if pid_str in result.stdout.decode('utf-8', errors='ignore'):
                                    print(f"  [RAG] Lock file is held by running process (PID: {pid})")
                                    print(f"  [RAG] Cannot remove lock - process is still active")
                                    return False
                                else:
                                    print(f"  [RAG] Lock file is stale (PID: {pid} no longer exists)")
                            except:
                                print(f"  [RAG] Could not verify process status, assuming stale")
                        else:
                            # Unix: try to send signal 0 (doesn't kill, just checks)
                            try:
                                os.kill(pid, 0)
                                print(f"  [RAG] Lock file is held by running process (PID: {pid})")
                                print(f"  [RAG] Cannot remove lock - process is still active")
                                return False
                            except OSError:
                                print(f"  [RAG] Lock file is stale (PID: {pid} no longer exists)")
    except Exception as e:
        print(f"  [RAG] Warning: Could not read lock file: {e}")
        print(f"  [RAG] Assuming stale and removing...")
    
    # Remove stale lock file
    try:
        lock_file.unlink()
        print(f"  [RAG] [OK] Removed stale lock file")
        return True
    except Exception as e:
        print(f"  [RAG] [FAIL] Could not remove lock file: {e}")
        return False

if __name__ == "__main__":
    rag_index_path = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\rag_index")
    
    print("=" * 60)
    print("RAG Index Lock Cleanup")
    print("=" * 60)
    print(f"RAG index path: {rag_index_path}")
    
    if not rag_index_path.exists():
        print(f"  [RAG] Index directory does not exist, creating...")
        rag_index_path.mkdir(parents=True, exist_ok=True)
    
    if clean_rag_lock(rag_index_path):
        print(f"\n  [RAG] Lock cleanup complete")
        print(f"  [RAG] You can now build the RAG index")
    else:
        print(f"\n  [RAG] Lock cleanup failed - another process may be using the index")
        print(f"  [RAG] Wait for the other process to finish, or close it manually")

