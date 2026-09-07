#!/usr/bin/env python3
"""
Shared utilities for file processing tools.
Provides common functionality for:
- Processing items one at a time in alphabetical order
- Creating backups before changes
- Prompting with timeout (defaulting to yes)
- Enhanced output showing what's being worked on and why
"""

import os
import sys
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable, Any, Dict, Tuple, Union
from datetime import datetime


def prompt_with_timeout(prompt: str, timeout: float = 5.0, default: str = "y") -> bool:
    """
    Prompt user with timeout. Defaults to 'yes' if no input within timeout.
    
    Args:
        prompt: The prompt message
        timeout: Timeout in seconds (default: 5.0)
        default: Default answer if timeout ('y' or 'n', default: 'y')
    
    Returns:
        True if yes, False if no
    """
    print(f"\n{prompt}")
    print(f"  (Auto-{default.upper()} in {timeout:.1f} seconds if no response)")
    sys.stdout.flush()
    
    response = default  # Default response
    
    # Try to read input with timeout
    try:
        if sys.stdin.isatty():
            # We have a TTY, try to read with timeout
            def read_input():
                nonlocal response
                try:
                    user_input = input("  Enter [Y/n]: ").strip().lower()
                    if user_input:
                        response = user_input
                except (EOFError, KeyboardInterrupt):
                    pass  # Keep default
            
            input_thread = threading.Thread(target=read_input, daemon=True)
            input_thread.start()
            input_thread.join(timeout=timeout)
            
            if input_thread.is_alive():
                # Timeout occurred - input() is blocking, so we can't interrupt it cleanly
                # But the thread will finish eventually, we just proceed with default
                print(f"  (No response, defaulting to {default.upper()})")
        else:
            # Not a TTY (redirected input), use default immediately
            print(f"  (Non-interactive mode, defaulting to {default.upper()})")
    except Exception as e:
        # Fallback to default on any error
        print(f"  (Error reading input: {e}, defaulting to {default.upper()})")
    
    # Normalize response
    if not response or response == "":
        response = default
    
    return response in ('y', 'yes', '')


def create_backup(item_path: Path, backup_suffix: str = "_backup") -> Optional[Path]:
    """
    Create a backup of a file or directory.
    
    Args:
        item_path: Path to file or directory to backup
        backup_suffix: Suffix to add to backup name
    
    Returns:
        Path to backup if successful, None otherwise
    """
    if not item_path.exists():
        return None
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if item_path.is_file():
            backup_path = item_path.parent / f"{item_path.stem}{backup_suffix}_{timestamp}{item_path.suffix}"
            shutil.copy2(item_path, backup_path)
        else:
            backup_path = item_path.parent / f"{item_path.name}{backup_suffix}_{timestamp}"
            shutil.copytree(item_path, backup_path)
        
        return backup_path
    except Exception as e:
        print(f"  Warning: Failed to create backup: {e}")
        return None


def process_items_sequentially(
    items: List[Any],
    item_name: str = "item",
    process_func: Callable[[Any, int, int], Dict[str, Any]] = None,
    sort_key: Optional[Callable[[Any], str]] = None,
    create_backups: bool = True,
    prompt_before_processing: bool = True,
    analyze_func: Optional[Callable[[Any], Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Process items one at a time in alphabetical order with backups and prompts.
    
    Args:
        items: List of items to process (can be Path objects or any type)
        item_name: Name for items (e.g., "mod", "file", "asset")
        process_func: Function to process each item: func(item, index, total) -> result_dict
        sort_key: Function to extract sort key from item (default: str(item))
        create_backups: Whether to create backups before processing
        prompt_before_processing: Whether to prompt before processing each item
        analyze_func: Optional function to analyze item before processing: func(item) -> analysis_dict
    
    Returns:
        List of result dictionaries from process_func
    """
    if not items:
        print(f"  No {item_name}s found to process.")
        return []
    
    # Sort items alphabetically
    if sort_key is None:
        sort_key = lambda x: str(x).lower()
    
    sorted_items = sorted(items, key=sort_key)
    
    print(f"\n{'='*60}")
    print(f"Processing {len(sorted_items)} {item_name}(s) in alphabetical order")
    print(f"{'='*60}")
    sys.stdout.flush()
    
    results = []
    
    # Process items one at a time
    for idx, item in enumerate(sorted_items, 1):
        # Extract display name from item (could be Path, string, tuple, etc.)
        item_str = str(item)
        item_path = None
        
        if isinstance(item, Path):
            item_path = item
            if not item.exists():
                print(f"\n  [{idx}/{len(sorted_items)}] {item_name.capitalize()} not found: {item_str}")
                continue
            item_str = item.name
        elif isinstance(item, (tuple, list)) and len(item) > 0:
            # Handle tuples like (filepath, issues) or (filepath, ...)
            first_item = item[0]
            if isinstance(first_item, Path):
                item_path = first_item
                if not first_item.exists():
                    print(f"\n  [{idx}/{len(sorted_items)}] {item_name.capitalize()} not found: {first_item}")
                    continue
                item_str = first_item.name
            elif isinstance(first_item, str):
                item_path = Path(first_item)
                if not item_path.exists():
                    print(f"\n  [{idx}/{len(sorted_items)}] {item_name.capitalize()} not found: {first_item}")
                    continue
                item_str = os.path.basename(first_item)
            else:
                item_str = str(first_item)
        elif isinstance(item, str):
            item_path = Path(item)
            if not item_path.exists():
                print(f"\n  [{idx}/{len(sorted_items)}] {item_name.capitalize()} not found: {item_str}")
                continue
            item_str = os.path.basename(item)
        
        print(f"\n{'='*60}")
        print(f"  [{idx}/{len(sorted_items)}] Processing: {item_str}")
        print(f"{'='*60}")
        sys.stdout.flush()
        
        # Analyze item if analysis function provided
        analysis = None
        if analyze_func:
            try:
                analysis = analyze_func(item)
                if analysis:
                    total_issues = analysis.get('total_issues', 0)
                    if total_issues == 0:
                        print(f"\n  No issues found in {item_str}. Skipping.")
                        continue
            except Exception as e:
                print(f"  Warning: Error analyzing {item_str}: {e}")
        
        # Prompt for confirmation if needed
        if prompt_before_processing:
            if analysis:
                prompt_msg = (
                    f"Process {item_str}?\n"
                    f"  Issues found: {analysis.get('total_issues', 0)}\n"
                    f"  A backup will be created before making any changes."
                )
            else:
                prompt_msg = (
                    f"Process {item_str}?\n"
                    f"  A backup will be created before making any changes."
                )
            
            if not prompt_with_timeout(prompt_msg, timeout=5.0, default="y"):
                print(f"  Skipping {item_str}")
                continue
        
        # Create backup if needed
        backup_path = None
        if create_backups and item_path:
            # item_path was already extracted above
            if item_path.exists():
                print(f"\n  Creating backup before making changes...")
                backup_path = create_backup(item_path)
                if backup_path:
                    print(f"  Backup created: {backup_path.name}")
                else:
                    # Ask again if backup fails
                    if not prompt_with_timeout("  Continue without backup? (not recommended)", timeout=3.0, default="n"):
                        print(f"  Skipping {item_str} (backup required)")
                        continue
            else:
                # Path doesn't exist, but we'll continue (might be created during processing)
                print(f"  Note: {item_path} does not exist yet (will be created during processing)")
        
        # Process the item
        if process_func:
            try:
                result = process_func(item, idx, len(sorted_items))
                result['item'] = item_str
                result['backup_path'] = backup_path
                results.append(result)
                
                if result.get('success'):
                    print(f"\n  Successfully processed {item_str}")
                    if backup_path:
                        print(f"  Backup available at: {backup_path.name}")
                else:
                    print(f"\n  Failed to process {item_str}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"\n  Error processing {item_str}: {e}")
                results.append({
                    'item': item_str,
                    'success': False,
                    'error': str(e),
                    'backup_path': backup_path
                })
        else:
            # No processing function, just track the item
            results.append({
                'item': item_str,
                'success': True,
                'backup_path': backup_path
            })
    
    return results


def format_file_processing_output(
    file_path: str,
    task: str,
    why: str,
    how: str
) -> None:
    """
    Format output showing which file is being worked on and why.
    
    Args:
        file_path: Path to file being processed
        task: What task is being performed
        why: Why the file needs processing
        how: How it's being processed
    """
    file_name = Path(file_path).name if isinstance(file_path, (str, Path)) else str(file_path)
    print(f"\n  [FILE] {file_name}")
    print(f"  [TASK] {task}")
    print(f"  [WHY]  {why}")
    print(f"  [HOW]  {how}")

