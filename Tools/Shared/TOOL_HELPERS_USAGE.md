# Tool Helpers Usage Guide

The `tool_helpers.py` module provides reusable utilities for AI-powered code tools. This guide shows how to use these helpers in your tools.

## Features

- **Dynamic Worker Scaling**: Automatically scales parallel processing based on file complexity
- **Single-Instance Locking**: Prevents multiple concurrent runs of the same tool
- **Unicode-Safe Output**: Handles encoding errors gracefully
- **Thread-Safe Processing**: Safe parallel file processing utilities

## Quick Start

```python
import sys
import os
from pathlib import Path

# Add Shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Shared"))

from tool_helpers import (
    SingleInstanceLock,
    WorkerScaler,
    FileComplexity,
    process_files_parallel,
    safe_print
)
```

## Single-Instance Locking

Prevent multiple concurrent runs of your tool:

```python
def main():
    # Use as context manager (recommended)
    with SingleInstanceLock("my_tool"):
        # Your tool code here
        process_files()
    
    # Or manually
    lock = SingleInstanceLock("my_tool")
    if not lock.acquire():
        print("Another instance is running!")
        sys.exit(1)
    try:
        # Your tool code here
        process_files()
    finally:
        lock.release()
```

## Dynamic Worker Scaling

Automatically calculate optimal number of workers:

```python
from tool_helpers import WorkerScaler, FileComplexity

# Get available cores (from your CPU manager or psutil)
available_cores = 63  # Example

# Create scaler
scaler = WorkerScaler(available_cores)

# Option 1: From FileComplexity objects
complexities = [
    FileComplexity(file_path="file1.cs", file_size=5000, issue_count=10),
    FileComplexity(file_path="file2.cs", file_size=15000, issue_count=5),
    FileComplexity(file_path="file3.cs", file_size=50000, issue_count=50),
]
optimal_workers = scaler.calculate_optimal_workers(complexities)
print(f"Using {optimal_workers} workers")

# Option 2: From files and issues dicts
files = {
    "file1.cs": file_obj1,
    "file2.cs": file_obj2,
}
issues_by_file = {
    "file1.cs": [issue1, issue2],
    "file2.cs": [issue3],
}
optimal_workers = scaler.calculate_from_files_and_issues(
    files,
    issues_by_file,
    get_file_size=lambda obj: len(obj.content)  # Custom size function
)
```

## Parallel File Processing

Process files in parallel with automatic scaling:

```python
from tool_helpers import process_files_parallel

def process_single_file(file_path: str, file_data: Any) -> Any:
    """Process a single file. This will run in parallel."""
    # Your processing logic here
    return result

# Files to process
files_to_process = [
    ("file1.cs", file_obj1),
    ("file2.cs", file_obj2),
    ("file3.cs", file_obj3),
]

# Process in parallel (automatically scales)
results = process_files_parallel(
    files_to_process=files_to_process,
    process_func=process_single_file,
    available_cores=63,
    show_progress=True
)

# Results is a list of return values from process_single_file
for result in results:
    if result:
        print(f"Success: {result}")
```

## Unicode-Safe Printing

Handle encoding errors gracefully:

```python
from tool_helpers import safe_print

# Use instead of print() for potentially problematic strings
safe_print("✓ Success!")  # Will handle Unicode encoding errors
safe_print("→ Processing...")  # Safe even on Windows console
```

## Complete Example

Here's a complete example combining all features:

```python
#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Shared"))
from tool_helpers import (
    SingleInstanceLock,
    WorkerScaler,
    FileComplexity,
    process_files_parallel,
    safe_print
)

def process_file(file_path: str, file_data: dict) -> dict:
    """Process a single file."""
    safe_print(f"  Processing {Path(file_path).name}...")
    # Your processing logic here
    return {"file": file_path, "status": "success"}

def main():
    # Prevent concurrent runs
    with SingleInstanceLock("my_code_fixer"):
        # Find files to process
        files_to_process = [
            ("file1.cs", {"content": "...", "issues": [...]}),
            ("file2.cs", {"content": "...", "issues": [...]}),
        ]
        
        # Process in parallel with automatic scaling
        results = process_files_parallel(
            files_to_process=files_to_process,
            process_func=process_file,
            available_cores=63,  # From your CPU manager
            show_progress=True
        )
        
        # Handle results
        for result in results:
            if result:
                safe_print(f"  [OK] {result['file']}")

if __name__ == "__main__":
    main()
```

## Integration with Existing Tools

### For tools using ThreadPoolExecutor:

Replace:
```python
max_workers = min(len(files), 4)  # Hardcoded limit
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    ...
```

With:
```python
from tool_helpers import WorkerScaler, FileComplexity

scaler = WorkerScaler(available_cores)
complexities = [FileComplexity(...) for file in files]
max_workers = scaler.calculate_optimal_workers(complexities)
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    ...
```

### For tools needing single-instance protection:

Wrap your main function:
```python
def main():
    with SingleInstanceLock("tool_name"):
        # Existing code
        ...
```

## Benefits

1. **Better Performance**: Dynamic scaling uses more workers for simple tasks, fewer for complex ones
2. **Resource Safety**: Prevents overwhelming system with too many concurrent operations
3. **User Experience**: Prevents accidental concurrent runs that could corrupt data
4. **Cross-Platform**: Works on Windows (msvcrt) and Unix (fcntl)
5. **Unicode Safety**: Handles encoding errors gracefully on all platforms

## Notes

- The helpers are designed to be optional - tools can work without them (with fallbacks)
- Worker scaling is conservative by default (leaves 1 core free for system)
- Lock files are created in the system temp directory
- All operations are thread-safe

