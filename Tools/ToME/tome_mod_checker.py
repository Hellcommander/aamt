#!/usr/bin/env python3
"""
ToME Mod Checker and Ollama-Guided Fixing Assistant
Validates ToME mods and uses Ollama to suggest fixes.
"""

import os
import sys
import json
import re
import ast
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# Import Ollama support
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import (
            get_router, get_code_model, get_visual_model,
            TASK_CODE, TASK_VISUAL
        )
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_CODE = "code"
        TASK_VISUAL = "visual"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_CODE = "code"
    TASK_VISUAL = "visual"

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Default ToME paths
TOME_GAME_PATH = Path("F:/SteamLibrary/steamapps/common/TalesMajEyal")
# Log file is in the game directory root
TOME_LOG_PATH = TOME_GAME_PATH / "te4_log.txt"
TOME_SOURCE_PATH = TOME_GAME_PATH / "game" / "source"
TOME_ENGINE_SOURCE = TOME_SOURCE_PATH / "t-engine4-src-1.7.6"
TOME_MOD_REFERENCES = TOME_SOURCE_PATH / "mod references"
TOME_ADDONS_PATH = TOME_GAME_PATH / "game" / "addons"

# ANSI color codes for cross-platform terminal colors
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Status colors
    SUCCESS = '\033[92m'  # Green
    ERROR = '\033[91m'    # Red
    WARNING = '\033[93m'  # Yellow
    INFO = '\033[94m'     # Blue
    CYAN = '\033[96m'     # Cyan
    MAGENTA = '\033[95m'  # Magenta
    GRAY = '\033[90m'     # Gray
    
    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'


# UI Helper Functions
def print_status_header(title: str, color: str = Colors.CYAN):
    """Print a formatted status header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def print_section_header(title: str, color: str = Colors.YELLOW):
    """Print a formatted section header."""
    print()
    print("-" * 60)
    print(f"  {title}")
    print("-" * 60)
    print()


def print_status(message: str, status: str = "INFO", color: str = Colors.RESET):
    """Print a status message with icon."""
    status_symbols = {
        "SUCCESS": "✓",
        "ERROR": "✗",
        "WARNING": "⚠",
        "INFO": "ℹ",
        "PROCESSING": "⟳"
    }
    
    status_colors = {
        "SUCCESS": Colors.SUCCESS,
        "ERROR": Colors.ERROR,
        "WARNING": Colors.WARNING,
        "INFO": Colors.INFO,
        "PROCESSING": Colors.MAGENTA
    }
    
    symbol = status_symbols.get(status, "•")
    color_code = status_colors.get(status, Colors.RESET)
    print(f"  [{color_code}{symbol}{Colors.RESET}] {message}")


def get_ollama_models(ollama_url: str = "http://localhost:11434") -> Optional[List[Dict[str, Any]]]:
    """Get list of available Ollama models."""
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get('models', [])
    except:
        pass
    return None


def show_model_list(ollama_url: str = "http://localhost:11434"):
    """Display list of available Ollama models."""
    print_status_header("Available Ollama Models", Colors.CYAN)
    
    models = get_ollama_models(ollama_url)
    if not models:
        print_status("Ollama is not running or no models are available", "ERROR")
        print()
        print("  Install Ollama from: https://ollama.com")
        print("  Then run: ollama pull codellama:7b")
        print()
        return
    
    # Categorize models
    code_models = []
    other_models = []
    
    for model in models:
        name = model.get('name', '')
        if any(x in name.lower() for x in ['codellama', 'starcoder', 'deepseek', 'qwen', 'wizardcoder']):
            code_models.append(model)
        else:
            other_models.append(model)
    
    if code_models:
        print("  Code Models (Recommended):")
        print()
        for model in code_models:
            name = model.get('name', '')
            size = model.get('size', 0)
            size_gb = f" - {size / (1024**3):.2f} GB" if size else ""
            modified = model.get('modified_at', 0)
            if modified:
                from datetime import datetime
                date = datetime.fromtimestamp(modified / 1000)
                modified_str = f" - Modified: {date.strftime('%Y-%m-%d %H:%M')}"
            else:
                modified_str = ""
            print(f"    • {name}{size_gb}{modified_str}")
        print()
    
    if other_models:
        print("  Other Models:")
        print()
        for model in other_models:
            name = model.get('name', '')
            size = model.get('size', 0)
            size_gb = f" - {size / (1024**3):.2f} GB" if size else ""
            modified = model.get('modified_at', 0)
            if modified:
                from datetime import datetime
                date = datetime.fromtimestamp(modified / 1000)
                modified_str = f" - Modified: {date.strftime('%Y-%m-%d %H:%M')}"
            else:
                modified_str = ""
            print(f"    • {name}{size_gb}{modified_str}")
        print()
    
    print_status(f"Total models: {len(models)}", "INFO")


def show_model_menu(ollama_url: str = "http://localhost:11434", current_model: str = "") -> Optional[str]:
    """Show interactive model selection menu."""
    print_status_header("AI Model Selection", Colors.CYAN)
    
    models = get_ollama_models(ollama_url)
    if not models:
        print_status("Ollama is not running or no models are available", "ERROR")
        print()
        print("  To install models, run:")
        print("    ollama pull codellama:7b")
        print("    ollama pull starcoder:7b")
        print()
        return None
    
    # Categorize models
    code_models = []
    other_models = []
    
    for model in models:
        name = model.get('name', '')
        if any(x in name.lower() for x in ['codellama', 'starcoder', 'deepseek', 'qwen', 'wizardcoder']):
            code_models.append(model)
        else:
            other_models.append(model)
    
    print("  Available Code Models:")
    print()
    
    index = 1
    menu_items = []
    
    # Show code models first
    for model in code_models:
        name = model.get('name', '')
        size = model.get('size', 0)
        size_str = f" ({size / (1024**3):.2f} GB)" if size else ""
        selected = " ← CURRENT" if name == current_model else ""
        color = Colors.SUCCESS if name == current_model else Colors.RESET
        print(f"    [{index}] {color}{name}{size_str}{selected}{Colors.RESET}")
        menu_items.append(name)
        index += 1
    
    # Show other models
    if other_models:
        print()
        print("  Other Models:")
        print()
        for model in other_models:
            name = model.get('name', '')
            size = model.get('size', 0)
            size_str = f" ({size / (1024**3):.2f} GB)" if size else ""
            selected = " ← CURRENT" if name == current_model else ""
            color = Colors.SUCCESS if name == current_model else Colors.GRAY
            print(f"    [{index}] {color}{name}{size_str}{selected}{Colors.RESET}")
            menu_items.append(name)
            index += 1
    
    print()
    print(f"    [0] Use default (auto-select)")
    print()
    
    try:
        selection = input("  Select model (0-{}): ".format(len(menu_items)))
        selection_num = int(selection)
        
        if selection_num == 0:
            return ""
        elif 1 <= selection_num <= len(menu_items):
            return menu_items[selection_num - 1]
        else:
            print_status("Invalid selection, using default", "WARNING")
            return ""
    except (ValueError, KeyboardInterrupt):
        print_status("Invalid selection, using default", "WARNING")
        return ""


def read_error_logs(
    log_paths: Optional[List[Path]] = None,
    save_path: Optional[Path] = None,
    mod_name: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    Read error logs from common locations and extract relevant errors.
    
    Returns:
        Dictionary with log file names as keys and lists of error lines as values
    """
    error_logs = {}
    
    # Default log locations
    default_log_paths = []
    
    # Primary ToME log location
    if TOME_LOG_PATH.exists():
        default_log_paths.append(TOME_LOG_PATH)
    
    # If save_path is provided, check there
    if save_path:
        default_log_paths.extend([
            save_path / "te4_log.txt",
            save_path / "tome.log",
            save_path / "error.log",
            save_path / "game.log",
        ])
    
    # Common ToME log locations (fallback)
    common_paths = [
        Path.home() / ".t-engine" / "4.0" / "te4_log.txt",
        Path.home() / ".t-engine" / "4.0" / "tome.log",
        Path.home() / ".t-engine" / "4.0" / "error.log",
    ]
    default_log_paths.extend(common_paths)
    
    # Use provided paths or defaults
    if log_paths:
        paths_to_check = log_paths
    else:
        paths_to_check = default_log_paths
    
    for log_path in paths_to_check:
        if not log_path.exists():
            continue
        
        try:
            errors = []
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                for line in lines:
                    line_lower = line.lower()
                    # Filter for error-related lines
                    if any(keyword in line_lower for keyword in [
                        'error', 'exception', 'failed', 'fail', 'cannot', 
                        'could not', 'missing', 'not found', 'nil',
                        'invalid', 'broken', 'crash', 'stacktrace', 'stack trace',
                        'lua error', 'syntax error'
                    ]):
                        # If mod_name is specified, filter for that mod
                        if mod_name and mod_name.lower() not in line_lower:
                            # Check if it's a general error that might affect the mod
                            if not any(general in line_lower for general in [
                                'system.', 'lua', 'tome', 'mod'
                            ]):
                                continue
                        
                        errors.append(line.strip())
            
            if errors:
                error_logs[log_path.name] = errors[:100]  # Limit to first 100 errors per log
                
        except Exception as e:
            print_status(f"Could not read log {log_path.name}: {e}", "WARNING")
    
    return error_logs


def format_error_logs_for_context(error_logs: Dict[str, List[str]], max_lines: int = 50) -> str:
    """Format error logs for inclusion in AI context."""
    if not error_logs:
        return ""
    
    formatted = ["Error Logs from Previous Sessions:"]
    formatted.append("")
    
    total_lines = 0
    for log_name, errors in error_logs.items():
        if total_lines >= max_lines:
            formatted.append(f"... (truncated, showing first {max_lines} error lines)")
            break
        
        formatted.append(f"=== {log_name} ===")
        remaining = max_lines - total_lines
        formatted.extend(errors[:remaining])
        total_lines += len(errors[:remaining])
        formatted.append("")
    
    return "\n".join(formatted)


class IssueSeverity(Enum):
    """Issue severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ModIssue:
    """Represents a mod validation issue."""
    severity: IssueSeverity
    file: str
    line: Optional[int]
    message: str
    code: Optional[str] = None
    suggestion: Optional[str] = None
    fixable: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'severity': self.severity.value,
            'file': self.file,
            'line': self.line,
            'message': self.message,
            'code': self.code,
            'suggestion': self.suggestion,
            'fixable': self.fixable
        }


class ToMEModChecker:
    """Validates ToME mods and checks for common issues."""
    
    def __init__(self, tome_source_path: Optional[str] = None):
        # Use default source path if not provided
        if tome_source_path:
            self.tome_source_path = Path(tome_source_path)
        else:
            # Try engine source first, then fallback to source
            if TOME_ENGINE_SOURCE.exists():
                self.tome_source_path = TOME_ENGINE_SOURCE
            elif TOME_SOURCE_PATH.exists():
                self.tome_source_path = TOME_SOURCE_PATH
            else:
                self.tome_source_path = None
        
        self.tome_mod_references = TOME_MOD_REFERENCES if TOME_MOD_REFERENCES.exists() else None
        self.tome_addons_path = TOME_ADDONS_PATH if TOME_ADDONS_PATH.exists() else None
        
        self.issues: List[ModIssue] = []
        self.mod_path: Optional[Path] = None
        
        # Required mod structure
        self.required_files = ['init.lua']
        self.optional_dirs = [
            'data', 'hooks', 'overload', 'superload'
        ]
        self.required_data_dirs = [
            'gfx', 'lua', 'locale'
        ]
    
    def check_mod(self, mod_path: str) -> List[ModIssue]:
        """Check a mod directory for issues."""
        self.mod_path = Path(mod_path)
        self.issues = []
        
        if not self.mod_path.exists():
            self.issues.append(ModIssue(
                IssueSeverity.ERROR,
                str(mod_path),
                None,
                f"Mod directory does not exist: {mod_path}"
            ))
            return self.issues
        
        # Check mod structure
        self._check_mod_structure()
        
        # Check init.lua
        self._check_init_lua()
        
        # Check data directory
        self._check_data_directory()
        
        # Check Lua files
        self._check_lua_files()
        
        # Check graphics
        self._check_graphics()
        
        # Check localization
        self._check_localization()
        
        return self.issues
    
    def _check_mod_structure(self):
        """Check mod directory structure."""
        # Check for init.lua
        init_file = self.mod_path / "init.lua"
        if not init_file.exists():
            self.issues.append(ModIssue(
                IssueSeverity.ERROR,
                str(init_file),
                None,
                "Missing required file: init.lua"
            ))
        
        # Check for data directory
        data_dir = self.mod_path / "data"
        if not data_dir.exists():
            self.issues.append(ModIssue(
                IssueSeverity.WARNING,
                str(data_dir),
                None,
                "Missing data directory (mod may have no content)"
            ))
    
    def _check_init_lua(self):
        """Check init.lua file."""
        init_file = self.mod_path / "init.lua"
        if not init_file.exists():
            return
        
        try:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required fields
            required_fields = ['long_name', 'short_name', 'for_module']
            for field in required_fields:
                if field not in content:
                    self.issues.append(ModIssue(
                        IssueSeverity.ERROR,
                        str(init_file),
                        None,
                        f"Missing required field in init.lua: {field}"
                    ))
            
            # Check for valid Lua syntax (basic check)
            try:
                # Try to parse as Lua (simplified check)
                if 'function' in content and '(' in content:
                    # Basic syntax validation
                    if content.count('{') != content.count('}'):
                        self.issues.append(ModIssue(
                            IssueSeverity.ERROR,
                            str(init_file),
                            None,
                            "Mismatched braces in init.lua"
                        ))
            except Exception as e:
                self.issues.append(ModIssue(
                    IssueSeverity.WARNING,
                    str(init_file),
                    None,
                    f"Could not validate Lua syntax: {e}"
                ))
            
            # Check for common issues
            if 'loadPrevious' not in content and 'data' in content:
                self.issues.append(ModIssue(
                    IssueSeverity.WARNING,
                    str(init_file),
                    None,
                    "Consider using loadPrevious(...) for mod compatibility"
                ))
        
        except Exception as e:
            self.issues.append(ModIssue(
                IssueSeverity.ERROR,
                str(init_file),
                None,
                f"Error reading init.lua: {e}"
            ))
    
    def _check_data_directory(self):
        """Check data directory structure."""
        data_dir = self.mod_path / "data"
        if not data_dir.exists():
            return
        
        # Check for common subdirectories
        expected_dirs = ['gfx', 'lua', 'locale', 'talents', 'zones', 'quests']
        found_dirs = [d.name for d in data_dir.iterdir() if d.is_dir()]
        
        for expected in expected_dirs:
            expected_path = data_dir / expected
            if expected_path.exists():
                # Check if directory has content
                if not any(expected_path.rglob('*')):
                    self.issues.append(ModIssue(
                        IssueSeverity.WARNING,
                        str(expected_path),
                        None,
                        f"Empty directory: {expected}"
                    ))
    
    def _check_single_lua_file(self, lua_file: Path) -> List[ModIssue]:
        """Check a single Lua file for issues (thread-safe)."""
        issues = []
        try:
            with open(lua_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for loadPrevious
            if 'newTalent' in content or 'newEntity' in content or 'newLore' in content:
                if 'loadPrevious' not in content:
                    issues.append(ModIssue(
                        IssueSeverity.WARNING,
                        str(lua_file.relative_to(self.mod_path)),
                        None,
                        "Consider using loadPrevious(...) for mod compatibility",
                        fixable=True
                    ))
            
            # Check for common syntax issues
            for i, line in enumerate(lines, 1):
                # Check for unclosed strings
                if line.count("'") % 2 != 0 and line.count('"') % 2 != 0:
                    if '--' not in line or line.find('--') > line.find("'"):
                        issues.append(ModIssue(
                            IssueSeverity.ERROR,
                            str(lua_file.relative_to(self.mod_path)),
                            i,
                            "Possible unclosed string literal",
                            code=line.strip()
                        ))
                
                # Check for undefined functions (common mistakes)
                if re.search(r'\bnewTalent\s*\(', line) and 'local _M = loadPrevious' not in content[:content.find(line)]:
                    issues.append(ModIssue(
                        IssueSeverity.WARNING,
                        str(lua_file.relative_to(self.mod_path)),
                        i,
                        "newTalent should be used with loadPrevious(...)",
                        code=line.strip(),
                        fixable=True
                    ))
        
        except Exception as e:
            issues.append(ModIssue(
                IssueSeverity.ERROR,
                str(lua_file.relative_to(self.mod_path)),
                None,
                f"Error reading Lua file: {e}"
            ))
        
        return issues
    
    def _check_lua_files(self):
        """Check Lua files for common issues using multithreading."""
        lua_files = list(self.mod_path.rglob('*.lua'))
        
        if not lua_files:
            return
        
        # Use multithreading for file checking
        max_workers = min(len(lua_files), os.cpu_count() or 4, 8)  # Limit to 8 workers max
        print_status(f"Checking {len(lua_files)} Lua file(s) with {max_workers} worker(s)...", "PROCESSING")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file checks
            future_to_file = {executor.submit(self._check_single_lua_file, lua_file): lua_file for lua_file in lua_files}
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                lua_file = future_to_file[future]
                completed += 1
                try:
                    file_issues = future.result()
                    self.issues.extend(file_issues)
                except Exception as e:
                    self.issues.append(ModIssue(
                        IssueSeverity.ERROR,
                        str(lua_file.relative_to(self.mod_path)),
                        None,
                        f"Error checking Lua file: {e}"
                    ))
                
                # Show progress
                if completed % 10 == 0 or completed == len(lua_files):
                    print_status(f"Checked {completed}/{len(lua_files)} files", "INFO")
    
    def _check_single_sprite(self, sprite: Path) -> Optional[ModIssue]:
        """Check a single sprite file (thread-safe)."""
        meta_file = sprite.with_suffix('.meta.json')
        if not meta_file.exists():
            return ModIssue(
                IssueSeverity.INFO,
                str(sprite.relative_to(self.mod_path)),
                None,
                "Sprite missing metadata file (.meta.json)"
            )
        return None
    
    def _check_graphics(self):
        """Check graphics files using multithreading."""
        gfx_dir = self.mod_path / "data" / "gfx"
        if not gfx_dir.exists():
            return
        
        # Check for sprites
        sprite_files = list(gfx_dir.rglob('*.png'))
        if not sprite_files:
            return
        
        # Use multithreading for sprite checking
        max_workers = min(len(sprite_files), os.cpu_count() or 4, 8)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all sprite checks
            future_to_sprite = {executor.submit(self._check_single_sprite, sprite): sprite for sprite in sprite_files}
            
            # Collect results
            for future in as_completed(future_to_sprite):
                try:
                    issue = future.result()
                    if issue:
                        self.issues.append(issue)
                except Exception:
                    pass  # Ignore individual sprite check errors
    
    def _check_localization(self):
        """Check localization files."""
        locale_dir = self.mod_path / "data" / "locale"
        if not locale_dir.exists():
            return
        
        # Check for English locale
        en_dir = locale_dir / "en"
        if not en_dir.exists():
            self.issues.append(ModIssue(
                IssueSeverity.WARNING,
                str(locale_dir),
                None,
                "Missing English locale directory (locale/en/)"
            ))


class OllamaModFixer:
    """Uses Ollama to suggest and apply fixes for mod issues."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", preferred_model: Optional[str] = None):
        self.ollama_url = ollama_url
        self.code_model = None
        self.visual_model = None
        self.preferred_model = preferred_model
        self.current_file: Optional[Path] = None
        self.backup_files: Dict[Path, Path] = {}  # original -> backup
        
        if MODEL_ROUTER_AVAILABLE:
            try:
                router = get_router()
                self.code_model = router.get_code_model()
                self.visual_model = router.get_visual_model()
            except:
                pass
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _call_ollama(self, prompt: str, model: Optional[str] = None, task_type: str = TASK_CODE) -> Optional[str]:
        """Call Ollama API."""
        if not self._check_ollama_available():
            return None
        
        if model is None:
            # Use preferred model if specified
            if self.preferred_model:
                model = self.preferred_model
            else:
                model = self.code_model if task_type == TASK_CODE else self.visual_model
        
        if not model:
            return None
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '').strip()
        except Exception as e:
            print(f"Ollama call failed: {e}")
        
        return None
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file before editing."""
        if not file_path.exists():
            return None
        
        try:
            backup_path = file_path.parent / f"{file_path.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)
            self.backup_files[file_path] = backup_path
            return backup_path
        except Exception as e:
            print_status(f"Failed to create backup for {file_path.name}: {e}", "WARNING")
            return None
    
    def restore_backup(self, file_path: Path) -> bool:
        """Restore a file from backup."""
        if file_path not in self.backup_files:
            return False
        
        backup_path = self.backup_files[file_path]
        if not backup_path.exists():
            return False
        
        try:
            shutil.copy2(backup_path, file_path)
            return True
        except Exception as e:
            print_status(f"Failed to restore backup for {file_path.name}: {e}", "ERROR")
            return False
    
    def apply_fix(self, file_path: Path, fixed_content: str, create_backup: bool = True) -> Tuple[bool, Optional[Path]]:
        """Apply a fix to a file with optional backup."""
        self.current_file = file_path
        
        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = self.create_backup(file_path)
            if backup_path:
                print_status(f"Backup created: {backup_path.name}", "SUCCESS")
        
        # Apply fix
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print_status(f"Applied fix to {file_path.name}", "SUCCESS")
            self.current_file = None
            return True, backup_path
        except Exception as e:
            print_status(f"Failed to apply fix to {file_path.name}: {e}", "ERROR")
            self.current_file = None
            return False, backup_path
    
    def suggest_fix(self, issue: ModIssue, file_content: Optional[str] = None, error_logs: Optional[Dict[str, List[str]]] = None) -> Optional[str]:
        """Suggest a fix for an issue using Ollama."""
        if not issue.fixable:
            return None
        
        # Include error logs if available
        error_log_context = ""
        if error_logs:
            error_log_context = format_error_logs_for_context(error_logs, max_lines=30)
        
        prompt = f"""You are a ToME (Tales of Maj'Eyal) modding expert. Fix this Lua code issue:

Issue: {issue.message}
File: {issue.file}
Line: {issue.line}
Code: {issue.code if issue.code else 'N/A'}

Context:
{file_content[:1000] if file_content else 'No context available'}
"""
        if error_log_context:
            prompt += f"\n{error_log_context}\n"
        
        prompt += "\nProvide a fixed version of the code. Return ONLY the fixed code, no explanations."
        
        result = self._call_ollama(prompt, task_type=TASK_CODE)
        return result
    
    def explain_issue(self, issue: ModIssue) -> Optional[str]:
        """Explain an issue using Ollama."""
        prompt = f"""Explain this ToME mod issue in simple terms:

Issue: {issue.message}
File: {issue.file}
Line: {issue.line}
Severity: {issue.severity.value}

Provide a clear explanation of what's wrong and why it matters."""
        
        result = self._call_ollama(prompt, task_type=TASK_VISUAL)
        return result


class ModCheckResult:
    """Result of mod checking."""
    
    def __init__(self, mod_path: str):
        self.mod_path = mod_path
        self.issues: List[ModIssue] = []
        self.summary: Dict[str, int] = {
            'errors': 0,
            'warnings': 0,
            'info': 0
        }
    
    def add_issue(self, issue: ModIssue):
        """Add an issue to the result."""
        self.issues.append(issue)
        key = issue.severity.value + 's'
        if key not in self.summary:
            self.summary[key] = 0
        self.summary[key] += 1
    
    def to_dict(self) -> Dict:
        return {
            'mod_path': self.mod_path,
            'summary': self.summary,
            'issues': [issue.to_dict() for issue in self.issues]
        }
    
    def to_json(self) -> str:
        """Export to JSON."""
        return json.dumps(self.to_dict(), indent=2)


def check_mod(mod_path: str, tome_source: Optional[str] = None) -> ModCheckResult:
    """Check a mod and return results."""
    checker = ToMEModChecker(tome_source)
    issues = checker.check_mod(mod_path)
    
    result = ModCheckResult(mod_path)
    for issue in issues:
        result.add_issue(issue)
    
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ToME Mod Checker')
    parser.add_argument('mod_path', nargs='?', help='Path to mod directory')
    parser.add_argument('--tome-source', default=str(TOME_ENGINE_SOURCE) if TOME_ENGINE_SOURCE.exists() else str(TOME_SOURCE_PATH), help=f'Path to ToME source directory (default: {TOME_ENGINE_SOURCE})')
    parser.add_argument('--tome-game', default=str(TOME_GAME_PATH), help=f'Path to ToME game directory (default: {TOME_GAME_PATH})')
    parser.add_argument('--tome-addons', default=str(TOME_ADDONS_PATH), help=f'Path to ToME addons directory (default: {TOME_ADDONS_PATH})')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--model', help='AI model to use (e.g., codellama:7b, starcoder:7b)')
    parser.add_argument('--list-models', action='store_true', help='List available Ollama models and exit')
    parser.add_argument('--interactive', action='store_true', help='Show interactive model selection menu')
    parser.add_argument('--error-logs', nargs="+", help='Paths to error log files to include (default: auto-detect from game directory)')
    parser.add_argument('--save-path', help='Path to ToME save directory (for auto-detecting error logs)')
    parser.add_argument('--get-fixes', action='store_true', help='Get AI suggestions for fixable issues')
    
    args = parser.parse_args()
    
    # Handle list models
    if args.list_models:
        show_model_list()
        sys.exit(0)
    
    # Show header
    print_status_header("ToME Mod Checker", Colors.CYAN)
    
    # Handle interactive model selection
    selected_model = None
    if args.interactive:
        selected_model = show_model_menu(current_model=args.model or "")
        if selected_model is not None:
            args.model = selected_model
    
    # Check if mod_path is provided
    if not args.mod_path:
        print_status("No mod path provided. Use --help for usage information.", "ERROR")
        parser.print_help()
        sys.exit(1)
    
    # Load error logs if available (auto-detect from game directory if not specified)
    error_logs = {}
    if args.error_logs or args.save_path or not args.error_logs:
        # Auto-detect from game directory if no logs specified
        game_path = Path(args.tome_game)
        log_paths = None
        if args.error_logs:
            log_paths = [Path(p) for p in args.error_logs]
        elif game_path.exists():
            # Try to find te4_log.txt in game directory
            default_log = game_path / "te4_log.txt"
            if default_log.exists():
                log_paths = [default_log]
        
        error_logs = read_error_logs(
            log_paths=log_paths,
            save_path=Path(args.save_path) if args.save_path else None,
            mod_name=Path(args.mod_path).name if args.mod_path else None
        )
        if error_logs:
            print_status(f"Loaded error logs from {len(error_logs)} log file(s)", "INFO")
    
    # Check mod
    print_status(f"Checking mod: {args.mod_path}", "PROCESSING")
    print_status(f"Using ToME source: {args.tome_source}", "INFO")
    if TOME_ADDONS_PATH.exists():
        print_status(f"ToME addons path: {args.tome_addons}", "INFO")
    result = check_mod(args.mod_path, args.tome_source)
    
    if args.json:
        print(result.to_json())
    else:
        print_section_header("Mod Check Results", Colors.CYAN)
        print_status(f"Mod: {args.mod_path}", "INFO")
        print_status(f"Errors: {result.summary['errors']}", "ERROR" if result.summary['errors'] > 0 else "INFO")
        print_status(f"Warnings: {result.summary['warnings']}", "WARNING" if result.summary['warnings'] > 0 else "INFO")
        print_status(f"Info: {result.summary['info']}", "INFO")
        print()
        
        if result.issues:
            print_section_header("Issues Found", Colors.YELLOW)
            for issue in result.issues:
                severity_status = issue.severity.value.upper()
                status_type = "ERROR" if issue.severity == IssueSeverity.ERROR else "WARNING" if issue.severity == IssueSeverity.WARNING else "INFO"
                print_status(f"{severity_status}: {issue.file}:{issue.line or '?'}", status_type)
                print(f"    {issue.message}")
                if issue.code:
                    print(f"    Code: {issue.code}")
                if issue.fixable:
                    print(f"    {Colors.SUCCESS}[Fixable]{Colors.RESET}")
                print()
        else:
            print_status("No issues found!", "SUCCESS")
        
        # Get AI fixes if requested
        if args.get_fixes:
            fixable_issues = [i for i in result.issues if i.fixable]
            if fixable_issues:
                print_section_header("AI-Generated Fixes", Colors.CYAN)
                fixer = OllamaModFixer(preferred_model=args.model)
                
                for issue in fixable_issues[:10]:  # Limit to 10 issues
                    print_status(f"Getting fix for: {issue.file}:{issue.line or '?'}", "PROCESSING")
                    
                    # Read file content
                    file_path = Path(args.mod_path) / issue.file
                    file_content = None
                    if file_path.exists():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                        except:
                            pass
                    
                    suggestion = fixer.suggest_fix(issue, file_content, error_logs)
                    if suggestion:
                        print_status(f"Fix generated for {issue.file}", "SUCCESS")
                        print(f"  Issue: {issue.message}")
                        print(f"  Suggested Fix:")
                        print(f"  {'-'*60}")
                        print(f"  {suggestion}")
                        print(f"  {'-'*60}")
                        print()
                    else:
                        print_status(f"Could not generate fix for {issue.file}", "WARNING")
            else:
                print_status("No fixable issues found", "INFO")

