"""
File Safety Validator
Prevents scripts from modifying system files or sensitive directories.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

# System directories that should NEVER be modified
SYSTEM_DIRECTORIES = [
    # Windows system directories
    "C:\\Windows",
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    # User profile system directories
    os.path.expanduser("~\\AppData\\Local\\Microsoft"),
    os.path.expanduser("~\\AppData\\Roaming\\Microsoft"),
    # Registry (represented as paths)
    "HKLM",
    "HKCU",
    # Other sensitive locations
    "C:\\System Volume Information",
    "C:\\$Recycle.Bin",
]

# Allowed output directories (relative to script root)
ALLOWED_OUTPUT_PATTERNS = [
    "Output",
    "TestOutput",
    "AI_Generated_Assets",
    "Generated",
    "Temp",
    "Logs",
]


def is_system_path(file_path: str) -> bool:
    """
    Check if a path is in a system directory.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if path is in a system directory, False otherwise
    """
    try:
        abs_path = os.path.abspath(file_path)
        abs_path_lower = abs_path.lower()
        
        # Check against system directories
        for sys_dir in SYSTEM_DIRECTORIES:
            sys_dir_abs = os.path.abspath(sys_dir)
            sys_dir_lower = sys_dir_abs.lower()
            
            # Check if path starts with system directory
            if abs_path_lower.startswith(sys_dir_lower):
                return True
        
        # Check for system drive root modifications
        if abs_path_lower.startswith("c:\\") and len(abs_path.split(os.sep)) <= 3:
            # Too close to root - likely system file
            return True
            
        # Check for registry paths
        if abs_path.upper().startswith(("HKLM\\", "HKCU\\", "HKCR\\", "HKU\\")):
            return True
            
    except Exception:
        # If we can't validate, err on the side of caution
        return True
    
    return False


def validate_output_path(file_path: str, script_root: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that an output path is safe to write to.
    
    Args:
        file_path: Path to validate
        script_root: Root directory of the script (for relative path validation)
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if path is safe, False otherwise
        error_message: Error message if path is unsafe, None if safe
    """
    try:
        abs_path = os.path.abspath(file_path)
        
        # Check if it's a system path
        if is_system_path(abs_path):
            return False, f"ERROR: Cannot write to system directory: {abs_path}"
        
        # If script_root provided, prefer paths relative to it
        if script_root:
            script_root_abs = os.path.abspath(script_root)
            
            # Check if path is within script root or allowed output directories
            try:
                rel_path = os.path.relpath(abs_path, script_root_abs)
                
                # Check if it's in an allowed output pattern
                is_allowed = False
                for pattern in ALLOWED_OUTPUT_PATTERNS:
                    if rel_path.startswith(pattern + os.sep) or rel_path == pattern:
                        is_allowed = True
                        break
                
                # Also allow if it's in a subdirectory of script root (but not system)
                if not is_allowed and not rel_path.startswith(".."):
                    # Path is relative to script root - allow it
                    is_allowed = True
                
                if not is_allowed:
                    return False, f"ERROR: Output path must be in allowed directories: {abs_path}"
                    
            except ValueError:
                # Path is not relative to script root - check if it's safe
                if is_system_path(abs_path):
                    return False, f"ERROR: Cannot write outside script directory to: {abs_path}"
        
        # Additional safety: check parent directory
        parent_dir = os.path.dirname(abs_path)
        if is_system_path(parent_dir):
            return False, f"ERROR: Parent directory is a system directory: {parent_dir}"
        
        return True, None
        
    except Exception as e:
        return False, f"ERROR: Path validation failed: {e}"


def safe_write_file(file_path: str, content: str, script_root: Optional[str] = None, encoding: str = 'utf-8') -> Tuple[bool, Optional[str]]:
    """
    Safely write a file with validation.
    
    Args:
        file_path: Path to write to
        content: Content to write
        script_root: Root directory of the script
        encoding: File encoding (default: utf-8)
        
    Returns:
        Tuple of (success, error_message)
        success: True if file was written, False otherwise
        error_message: Error message if write failed, None if successful
    """
    # Validate path first
    is_valid, error_msg = validate_output_path(file_path, script_root)
    if not is_valid:
        return False, error_msg
    
    try:
        # Create parent directory if needed
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # Write file
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True, None
        
    except Exception as e:
        return False, f"ERROR: Failed to write file: {e}"


def get_script_root() -> str:
    """Get the root directory of the current script."""
    # Try to get from common environment variables
    script_root = os.environ.get('SCRIPT_ROOT')
    if script_root and os.path.exists(script_root):
        return script_root
    
    # Default to Tools directory
    current_file = os.path.abspath(__file__)
    tools_dir = os.path.dirname(current_file)
    return tools_dir

