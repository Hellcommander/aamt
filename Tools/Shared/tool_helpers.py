#!/usr/bin/env python3
"""
Shared Tool Helpers
Common utilities for AI-powered code tools including:
- Dynamic worker scaling based on complexity
- Single-instance locking
- Unicode-safe output
- Thread-safe parallel processing
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Platform-specific imports for file locking
if sys.platform == 'win32':
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
else:
    try:
        import fcntl
    except ImportError:
        fcntl = None


@dataclass
class FileComplexity:
    """Represents complexity metrics for a file."""
    file_path: str
    file_size: int
    issue_count: int
    content: Optional[str] = None


class SingleInstanceLock:
    """
    Single-instance lock to prevent multiple concurrent runs of a tool.
    Thread-safe and cross-platform.
    """
    
    def __init__(self, lock_name: str = "tool_lock"):
        """
        Initialize single-instance lock.
        
        Args:
            lock_name: Name for the lock file (will be created in temp directory)
        """
        self.lock_file_path = Path(tempfile.gettempdir()) / f"{lock_name}.lock"
        self.lock_file = None
        self.lock_acquired = False
    
    def acquire(self) -> bool:
        """
        Acquire the lock. Returns False if another instance is running.
        
        Returns:
            True if lock acquired, False if another instance is running
        """
        try:
            if sys.platform == 'win32':
                if msvcrt is None:
                    print("Warning: msvcrt not available, cannot prevent concurrent instances")
                    return True  # Continue anyway
                try:
                    self.lock_file = open(self.lock_file_path, 'w')
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                    self.lock_acquired = True
                    # Write PID to lock file
                    self.lock_file.write(str(os.getpid()))
                    self.lock_file.flush()
                    return True
                except IOError:
                    # Another instance is running
                    return False
            else:
                if fcntl is None:
                    print("Warning: fcntl not available, cannot prevent concurrent instances")
                    return True  # Continue anyway
                try:
                    self.lock_file = open(self.lock_file_path, 'w')
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.lock_acquired = True
                    # Write PID to lock file
                    self.lock_file.write(str(os.getpid()))
                    self.lock_file.flush()
                    return True
                except IOError:
                    # Another instance is running
                    return False
        except Exception as e:
            print(f"Warning: Could not acquire lock file: {e}")
            print("Continuing anyway (may cause issues if another instance is running)")
            return True  # Continue anyway
    
    def release(self):
        """Release the lock."""
        if self.lock_acquired and self.lock_file:
            try:
                if sys.platform == 'win32' and msvcrt:
                    msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                elif fcntl:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                if self.lock_file_path.exists():
                    self.lock_file_path.unlink()
            except Exception as e:
                print(f"Warning: Could not release lock file: {e}")
    
    def get_running_pid(self) -> Optional[str]:
        """Get the PID of the running instance from the lock file."""
        try:
            if self.lock_file_path.exists():
                with open(self.lock_file_path, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        return None
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            pid = self.get_running_pid()
            print("=" * 60)
            print("ERROR: Another instance is already running!")
            print("=" * 60)
            print("Please wait for the current instance to finish, or close it first.")
            if pid:
                print(f"Lock file indicates process ID: {pid}")
            print("=" * 60)
            print("")
            input("Press Enter to exit...")  # Keep window open
            sys.exit(1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


class WorkerScaler:
    """
    Calculate optimal number of workers based on file complexity.
    Scales dynamically to maximize throughput while avoiding resource exhaustion.
    """
    
    def __init__(self, available_cores: int):
        """
        Initialize worker scaler.
        
        Args:
            available_cores: Number of available CPU cores
        """
        self.available_cores = available_cores
    
    def calculate_optimal_workers(
        self,
        file_complexities: List[FileComplexity],
        max_workers_override: Optional[int] = None
    ) -> int:
        """
        Calculate optimal number of workers based on file complexity.
        
        Complexity factors:
        - File count (more files = more workers, up to a point)
        - Total file size (larger files = fewer concurrent workers to avoid memory issues)
        - Issue count per file (more issues = more processing time per file)
        - Available CPU cores
        
        Args:
            file_complexities: List of FileComplexity objects
            max_workers_override: Optional maximum workers override
        
        Returns:
            Optimal number of workers (thread-safe, scales with complexity)
        """
        if not file_complexities:
            return 1
        
        if max_workers_override is not None:
            return min(max_workers_override, max(1, self.available_cores - 1))
        
        file_count = len(file_complexities)
        
        # Calculate total complexity score
        total_size = sum(fc.file_size for fc in file_complexities)
        total_issues = sum(fc.issue_count for fc in file_complexities)
        max_file_size = max((fc.file_size for fc in file_complexities), default=0)
        
        # Base workers: scale with file count (up to available cores)
        base_workers = min(file_count, self.available_cores)
        
        # Adjust based on file complexity:
        # - Small files (< 5KB): can process more concurrently
        # - Medium files (5-20KB): moderate concurrency
        # - Large files (> 20KB): fewer concurrent to avoid memory pressure
        
        avg_file_size = total_size / file_count if file_count > 0 else 0
        
        if avg_file_size < 5000:  # Small files
            # Can handle more concurrent requests
            complexity_factor = 1.5
        elif avg_file_size < 20000:  # Medium files
            complexity_factor = 1.0
        else:  # Large files
            # Reduce concurrency to avoid memory issues
            complexity_factor = 0.6
        
        # Adjust for very large individual files
        if max_file_size > 50000:  # Very large file
            complexity_factor *= 0.7
        
        # Adjust for high issue density (more processing per file)
        issues_per_file = total_issues / file_count if file_count > 0 else 0
        if issues_per_file > 50:  # High issue density
            complexity_factor *= 0.8
        
        # Calculate optimal workers
        optimal_workers = max(1, int(base_workers * complexity_factor))
        
        # Cap at reasonable limits:
        # - Minimum: 1 worker
        # - Maximum: available cores (but leave 1 core free for system)
        optimal_workers = min(optimal_workers, max(1, self.available_cores - 1))
        optimal_workers = max(1, optimal_workers)  # At least 1 worker
        
        return optimal_workers
    
    def calculate_from_files_and_issues(
        self,
        files: Dict[str, Any],  # Dict mapping file_path -> file_data
        issues_by_file: Dict[str, List[Any]],  # Dict mapping file_path -> list of issues
        get_file_size: Callable[[Any], int] = lambda x: len(str(x))
    ) -> int:
        """
        Calculate optimal workers from files and issues dicts.
        
        Args:
            files: Dictionary mapping file paths to file objects/data
            issues_by_file: Dictionary mapping file paths to lists of issues
            get_file_size: Function to extract file size from file object
        
        Returns:
            Optimal number of workers
        """
        complexities = []
        for file_path, issues in issues_by_file.items():
            file_data = files.get(file_path)
            if file_data:
                file_size = get_file_size(file_data)
                complexities.append(FileComplexity(
                    file_path=file_path,
                    file_size=file_size,
                    issue_count=len(issues),
                    content=None
                ))
        
        return self.calculate_optimal_workers(complexities)


def process_files_parallel(
    files_to_process: List[Tuple[str, Any]],  # List of (file_path, file_data) tuples
    process_func: Callable[[str, Any], Any],
    available_cores: int,
    max_workers: Optional[int] = None,
    show_progress: bool = True
) -> List[Any]:
    """
    Process files in parallel with dynamic worker scaling.
    Thread-safe and automatically scales based on complexity.
    
    Args:
        files_to_process: List of (file_path, file_data) tuples
        process_func: Function to process each file: process_func(file_path, file_data) -> result
        available_cores: Number of available CPU cores
        max_workers: Optional maximum workers override
        show_progress: Whether to show progress messages
    
    Returns:
        List of results from process_func
    """
    if not files_to_process:
        return []
    
    # Calculate file complexities
    complexities = []
    for file_path, file_data in files_to_process:
        if hasattr(file_data, 'content'):
            size = len(file_data.content)
        elif isinstance(file_data, str):
            size = len(file_data)
        elif hasattr(file_data, '__len__'):
            size = len(file_data)
        else:
            size = 1000  # Default estimate
        
        complexities.append(FileComplexity(
            file_path=file_path,
            file_size=size,
            issue_count=1,  # Default, can be overridden
            content=None
        ))
    
    # Calculate optimal workers
    scaler = WorkerScaler(available_cores)
    optimal_workers = scaler.calculate_optimal_workers(complexities, max_workers)
    
    if show_progress:
        print(f"    Processing {len(files_to_process)} files with {optimal_workers} workers (scaled based on complexity)...")
    
    results = []
    with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
        # Submit all tasks
        future_to_file = {}
        for file_path, file_data in files_to_process:
            future = executor.submit(process_func, file_path, file_data)
            future_to_file[future] = file_path
        
        # Collect results as they complete
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                if show_progress:
                    print(f"      Exception processing {Path(file_path).name}: {e}")
                results.append(None)  # Or create error result object
    
    return results


def safe_print(message: str, encoding: str = 'utf-8', errors: str = 'replace'):
    """
    Unicode-safe print function that handles encoding errors gracefully.
    
    Args:
        message: Message to print
        encoding: Encoding to use (default: utf-8)
        errors: Error handling strategy (default: 'replace')
    """
    try:
        # Try to print normally
        print(message)
    except UnicodeEncodeError:
        # If that fails, encode with error handling
        try:
            encoded = message.encode(encoding, errors=errors)
            print(encoded.decode(encoding))
        except Exception:
            # Last resort: ASCII only
            safe_message = message.encode('ascii', errors='replace').decode('ascii')
            print(safe_message)


# Example usage functions for common patterns

def create_file_complexity_from_dict(
    file_path: str,
    file_data: Any,
    issue_count: int = 0,
    get_size_func: Optional[Callable[[Any], int]] = None
) -> FileComplexity:
    """
    Create FileComplexity from file data.
    
    Args:
        file_path: Path to the file
        file_data: File data object
        issue_count: Number of issues in the file
        get_size_func: Optional function to extract size from file_data
    
    Returns:
        FileComplexity object
    """
    if get_size_func:
        size = get_size_func(file_data)
    elif hasattr(file_data, 'content'):
        size = len(file_data.content)
    elif isinstance(file_data, str):
        size = len(file_data)
    elif hasattr(file_data, '__len__'):
        size = len(file_data)
    else:
        size = 1000  # Default estimate
    
    return FileComplexity(
        file_path=file_path,
        file_size=size,
        issue_count=issue_count,
        content=None
    )

