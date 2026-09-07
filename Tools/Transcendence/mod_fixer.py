#!/usr/bin/env python3
"""
Mod Fixer - Ollama-Assisted Mod Fixing System
Uses per-game profiles to safely fix mod issues with AI assistance.
"""

import os
import sys
import json
import yaml
import shutil
import hashlib
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib
import re

# Import API checker
_api_checker_path = os.path.join(os.path.dirname(__file__), "mod_fixer_api_checker.py")
if os.path.exists(_api_checker_path):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from mod_fixer_api_checker import ApiChecker
        API_CHECKER_AVAILABLE = True
    except ImportError:
        API_CHECKER_AVAILABLE = False
else:
    API_CHECKER_AVAILABLE = False

# Import Ollama support
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import (
            get_router, get_code_model, get_visual_model,
            TASK_CODE, TASK_XML
        )
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_CODE = "code"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_CODE = "code"

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests library not available. Ollama features disabled.")

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


class SandboxMode(Enum):
    """Sandbox execution modes."""
    DIRECTORY = "directory"  # Copy to temp directory
    CONTAINER = "container"   # Docker container (not implemented)
    RUNSPACE = "runspace"    # PowerShell runspace (Windows)


@dataclass
class FixReport:
    """Report metadata for a fix operation."""
    profile: str
    prompt: str
    model_version: str
    patch_hash: str
    rollback_hash: Optional[str]
    validation_results: Dict[str, Any]
    reviewer: Optional[str]
    timestamp: str
    applied: bool
    files_changed: List[str]
    lines_changed: int


class ModFixerProfile:
    """Loads and manages a game-specific mod fixer profile."""
    
    def __init__(self, profile_path: Path):
        self.profile_path = profile_path
        self.data: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Load profile from YAML file."""
        with open(self.profile_path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)
    
    @property
    def game(self) -> str:
        return self.data.get('game', 'unknown')
    
    @property
    def engine(self) -> str:
        return self.data.get('engine', 'unknown')
    
    @property
    def system_prompt(self) -> str:
        return self.data.get('system_prompt', '')
    
    @property
    def allowed_files(self) -> List[str]:
        return self.data.get('allowed_files', [])
    
    @property
    def validation_commands(self) -> List[Dict[str, Any]]:
        return self.data.get('validation', [])
    
    @property
    def safety_config(self) -> Dict[str, Any]:
        return self.data.get('safety', {})
    
    @property
    def prompts(self) -> Dict[str, str]:
        return self.data.get('prompts', {})
    
    @property
    def max_changes(self) -> int:
        return self.safety_config.get('max_changes', 100)
    
    @property
    def timeout_seconds(self) -> int:
        return self.safety_config.get('timeout_seconds', 60)
    
    @property
    def sandbox_mode(self) -> str:
        return self.safety_config.get('sandbox', 'directory')
    
    def get_prompt_template(self, template_name: str) -> Optional[str]:
        """Get a prompt template by name."""
        return self.prompts.get(template_name)


class ModFixer:
    """Main mod fixer class with Ollama integration."""
    
    def __init__(
        self,
        profile_path: str,
        ollama_url: str = "http://localhost:11434",
        sandbox_dir: Optional[str] = None,
        api_rules_path: Optional[str] = None,
        preferred_model: Optional[str] = None
    ):
        self.profile = ModFixerProfile(Path(profile_path))
        self.ollama_url = ollama_url
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else None
        self.model_router = None
        self.api_checker = None
        self.preferred_model = preferred_model
        
        if MODEL_ROUTER_AVAILABLE:
            try:
                self.model_router = get_router()
            except Exception as e:
                print_status(f"Could not initialize model router: {e}", "WARNING")
        
        # Initialize API checker for Transcendence mods
        if API_CHECKER_AVAILABLE and self.profile.game == "transcendence":
            try:
                self.api_checker = ApiChecker(api_rules_path)
            except Exception as e:
                print_status(f"Could not initialize API checker: {e}", "WARNING")
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        format: str = "json"
    ) -> Optional[str]:
        """Call Ollama API for text generation."""
        if not self._check_ollama_available():
            raise RuntimeError("Ollama is not available")
        
        if system_prompt is None:
            system_prompt = self.profile.system_prompt
        
        if model is None:
            # Use preferred model if specified
            if self.preferred_model:
                model = self.preferred_model
                print_status(f"Using specified model: {model}", "INFO")
            elif self.model_router:
                model = self.model_router.get_code_model()
            else:
                model = "codellama:latest"
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            request_data = {
                "model": model,
                "messages": messages,
                "stream": False
            }
            
            if format == "json":
                request_data["format"] = "json"
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=request_data,
                timeout=self.profile.timeout_seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '').strip()
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code}")
        except Exception as e:
            raise RuntimeError(f"Ollama call failed: {e}")
    
    def _create_sandbox(self, mod_path: Path) -> Path:
        """Create a sandbox copy of the mod for safe testing."""
        if self.sandbox_dir:
            sandbox = self.sandbox_dir / f"mod_sandbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            sandbox = Path(tempfile.mkdtemp(prefix="mod_fixer_sandbox_"))
        
        # Copy mod to sandbox
        shutil.copytree(mod_path, sandbox, dirs_exist_ok=True)
        return sandbox
    
    def _apply_patch(self, target_dir: Path, patch_content: str, create_backup: bool = True) -> Tuple[List[str], int]:
        """Apply a unified diff patch to target directory with multithreading."""
        # Parse unified diff to collect all file patches
        lines = patch_content.split('\n')
        file_patches = []  # List of (file_path, patch_lines) tuples
        current_file = None
        current_lines = []
        in_hunk = False
        
        for line in lines:
            if line.startswith('---'):
                # Save previous file
                if current_file and current_lines:
                    file_patches.append((current_file, current_lines))
                
                # Start new file
                file_path = line[4:].strip().split('\t')[0]
                if file_path.startswith('a/') or file_path.startswith('b/'):
                    file_path = file_path[2:]
                current_file = target_dir / file_path
                current_lines = []
                in_hunk = False
            elif line.startswith('+++'):
                continue
            elif line.startswith('@@'):
                in_hunk = True
            elif in_hunk and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                current_lines.append(line)
        
        # Save last file
        if current_file and current_lines:
            file_patches.append((current_file, current_lines))
        
        if not file_patches:
            return [], 0
        
        # Apply patches in parallel
        files_changed = []
        lines_changed = 0
        max_workers = min(len(file_patches), os.cpu_count() or 4, 8)
        
        print_status(f"Applying patches to {len(file_patches)} file(s) with {max_workers} worker(s)...", "PROCESSING")
        
        def apply_single_patch(file_path: Path, patch_lines: List[str]) -> Tuple[str, int]:
            """Apply patch to a single file (thread-safe)."""
            self._apply_file_patch(file_path, patch_lines, create_backup=create_backup)
            file_rel = str(file_path.relative_to(target_dir))
            lines_count = len([l for l in patch_lines if l.startswith('+') or l.startswith('-')])
            return file_rel, lines_count
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(apply_single_patch, file_path, patch_lines): file_path
                for file_path, patch_lines in file_patches
            }
            
            completed = 0
            for future in as_completed(future_to_file):
                completed += 1
                try:
                    file_rel, lines_count = future.result()
                    files_changed.append(file_rel)
                    lines_changed += lines_count
                except Exception as e:
                    file_path = future_to_file[future]
                    print_status(f"Failed to apply patch to {file_path.name}: {e}", "ERROR")
                
                # Show progress
                if completed % 5 == 0 or completed == len(file_patches):
                    print_status(f"Applied patches to {completed}/{len(file_patches)} files", "INFO")
        
        return files_changed, lines_changed
    
    def _create_file_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file before editing."""
        if not file_path.exists():
            return None
        
        try:
            backup_path = file_path.parent / f"{file_path.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            print_status(f"Failed to create backup for {file_path.name}: {e}", "WARNING")
            return None
    
    def _apply_file_patch(self, file_path: Path, patch_lines: List[str], create_backup: bool = True):
        """Apply patch lines to a single file."""
        # Create backup before editing
        backup_path = None
        if create_backup and file_path.exists():
            backup_path = self._create_file_backup(file_path)
            if backup_path:
                print_status(f"Backup created: {backup_path.name}", "SUCCESS")
        
        # Show current file being edited
        print_status(f"Editing file: {file_path.name}", "PROCESSING")
        print(f"  [FILE]   {file_path}")
        if backup_path:
            print(f"  [BACKUP] {backup_path}")
        
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            original_content = []
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.readlines()
        
        # Simple patch application (context-based)
        result = []
        i = 0
        for patch_line in patch_lines:
            if patch_line.startswith(' '):
                # Context line - match with original
                if i < len(original_content):
                    result.append(original_content[i])
                    i += 1
            elif patch_line.startswith('+'):
                # Add line
                result.append(patch_line[1:] + '\n')
            elif patch_line.startswith('-'):
                # Remove line
                if i < len(original_content):
                    i += 1
        
        # Add remaining original lines
        result.extend(original_content[i:])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(result)
        
        print_status(f"Applied changes to {file_path.name}", "SUCCESS")
    
    def _run_validation(self, mod_path: Path) -> Dict[str, Any]:
        """Run validation commands on the mod."""
        results = {}
        
        for validation in self.profile.validation_commands:
            command = validation.get('command', '')
            description = validation.get('description', '')
            required = validation.get('required', False)
            
            if not command:
                continue
            
            try:
                # Replace placeholders with actual paths
                script_dir = Path(__file__).parent
                command = command.replace('%SCRIPT_DIR%', str(script_dir))
                command = command.replace('%MOD_PATH%', str(mod_path))
                command = command.replace('./mod', str(mod_path))
                
                # Run command
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=mod_path.parent,
                    capture_output=True,
                    text=True,
                    timeout=self.profile.timeout_seconds
                )
                
                results[description or command] = {
                    'success': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode,
                    'required': required
                }
            except subprocess.TimeoutExpired:
                results[description or command] = {
                    'success': False,
                    'error': 'Timeout',
                    'required': required
                }
            except Exception as e:
                results[description or command] = {
                    'success': False,
                    'error': str(e),
                    'required': required
                }
        
        return results
    
    def _calculate_patch_hash(self, patch_content: str) -> str:
        """Calculate SHA256 hash of patch content."""
        return hashlib.sha256(patch_content.encode('utf-8')).hexdigest()[:16]
    
    def generate_fix(
        self,
        mod_path: str,
        issue_description: str,
        prompt_template: Optional[str] = None,
        context_files: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a fix for a mod issue.
        
        Returns:
            Dictionary with 'diff', 'rollback_diff', 'validation_commands', 'notes'
        """
        mod_path = Path(mod_path)
        if not mod_path.exists():
            raise ValueError(f"Mod path does not exist: {mod_path}")
        
        # Build context
        context_parts = [f"[PROFILE: {self.profile.game}]"]
        context_parts.append("CONTEXT:")
        
        if context_files:
            context_parts.append(f"- file list: {', '.join(context_files)}")
        
        # Read relevant files for context (multithreaded)
        file_contents = {}
        if context_files:
            # Collect all matching files first
            all_files = []
            for file_pattern in context_files:
                all_files.extend(list(mod_path.rglob(file_pattern)))
            
            if all_files:
                # Use multithreading to read files
                max_workers = min(len(all_files), os.cpu_count() or 4, 8)
                
                def read_file(file_path: Path) -> Tuple[str, str]:
                    """Read a single file (thread-safe)."""
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:2000]  # Limit size
                        return str(file_path.relative_to(mod_path)), content
                    except:
                        return None, None
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(read_file, file_path): file_path for file_path in all_files}
                    
                    for future in as_completed(future_to_file):
                        file_name, content = future.result()
                        if file_name and content:
                            file_contents[file_name] = content
        
        if file_contents:
            context_parts.append("- file contents:")
            for file_name, content in file_contents.items():
                context_parts.append(f"  {file_name}:\n{content[:500]}...")  # Truncate for prompt
        
        context_parts.append(f"- errors: {issue_description}")
        
        # Add API compatibility check results if available
        if self.api_checker and self.profile.game == "transcendence":
            try:
                api_report = self.api_checker.generate_api_check_report(mod_path)
                if api_report['total_issues'] > 0:
                    context_parts.append("")
                    context_parts.append("- API compatibility check:")
                    context_parts.append(f"  Current API version: {api_report['api_version']}")
                    context_parts.append(f"  Total issues found: {api_report['total_issues']} (errors: {api_report['errors']}, warnings: {api_report['warnings']})")
                    
                    # Add sample issues
                    sample_issues = []
                    for file_path, issues in list(api_report['issues_by_file'].items())[:5]:
                        for issue in issues[:3]:
                            sample_issues.append(f"    - {file_path}:{issue.get('line', '?')} [{issue['code']}] {issue['message']}")
                    if sample_issues:
                        context_parts.append("  Sample issues:")
                        context_parts.extend(sample_issues)
            except Exception as e:
                # Non-fatal - continue without API check info
                pass
        
        context_parts.append("")
        context_parts.append("TASK:")
        
        # Use template or default
        if prompt_template and prompt_template in self.profile.prompts:
            task = self.profile.prompts[prompt_template]
        else:
            task = f"Fix the following issue: {issue_description}"
            task += "\n1) Produce a unified diff that fixes the issue."
            task += "\n2) Provide a rollback diff."
            task += "\n3) Output validation commands to run."
        
        context_parts.append(task)
        context_parts.append("")
        context_parts.append("FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes.")
        
        full_prompt = "\n".join(context_parts)
        
        # Call Ollama
        response = self._call_ollama(full_prompt, format="json")
        
        if not response:
            raise RuntimeError("Ollama returned empty response")
        
        # Parse JSON response
        try:
            # Try to extract JSON from response (in case it's wrapped in markdown)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                fix_data = json.loads(json_match.group())
            else:
                fix_data = json.loads(response)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Ollama response as JSON: {e}\nResponse: {response[:500]}")
        
        return fix_data
    
    def apply_fix(
        self,
        mod_path: str,
        fix_data: Dict[str, Any],
        dry_run: bool = True
    ) -> FixReport:
        """
        Apply a fix to a mod (with sandboxing if dry_run=True).
        
        Returns:
            FixReport with metadata about the fix
        """
        mod_path = Path(mod_path)
        patch_content = fix_data.get('diff', '')
        rollback_content = fix_data.get('rollback_diff', '')
        
        if not patch_content:
            raise ValueError("No patch content provided")
        
        # Create sandbox for dry run
        if dry_run:
            sandbox = self._create_sandbox(mod_path)
            target_path = sandbox
        else:
            target_path = mod_path
        
        # Apply patch (with backups)
        print_status("Applying patch to files...", "PROCESSING")
        files_changed, lines_changed = self._apply_patch(target_path, patch_content, create_backup=not dry_run)
        
        # Check limits
        if lines_changed > self.profile.max_changes:
            raise ValueError(f"Patch exceeds max_changes limit ({self.profile.max_changes})")
        
        # Run validation
        validation_results = self._run_validation(target_path)
        
        # Calculate hashes
        patch_hash = self._calculate_patch_hash(patch_content)
        rollback_hash = self._calculate_patch_hash(rollback_content) if rollback_content else None
        
        # Create report
        report = FixReport(
            profile=self.profile.game,
            prompt=fix_data.get('notes', ''),
            model_version=self.model_router.get_code_model() if self.model_router else "unknown",
            patch_hash=patch_hash,
            rollback_hash=rollback_hash,
            validation_results=validation_results,
            reviewer=None,
            timestamp=datetime.now().isoformat(),
            applied=not dry_run,
            files_changed=files_changed,
            lines_changed=lines_changed
        )
        
        return report
    
    def save_report(self, report: FixReport, output_path: str):
        """Save fix report to JSON file."""
        report_dict = asdict(report)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mod Fixer - AI-assisted mod fixing")
    parser.add_argument('mod_path', help='Path to mod directory')
    parser.add_argument('--profile', required=True, help='Profile name (tome, unity, minecraft_fabric, transcendence)')
    parser.add_argument('--issue', required=True, help='Issue description')
    parser.add_argument('--template', help='Prompt template name')
    parser.add_argument('--context-files', nargs='+', help='Context files to include')
    parser.add_argument('--apply', action='store_true', help='Apply fix (default: dry-run)')
    parser.add_argument('--ollama-url', default='http://localhost:11434', help='Ollama URL')
    parser.add_argument('--sandbox-dir', help='Sandbox directory (default: temp)')
    parser.add_argument('--output-report', help='Save fix report to file')
    parser.add_argument('--api-rules', help='Path to api_rules.json (auto-detects for Transcendence)')
    parser.add_argument('--check-api', action='store_true', help='Run API compatibility check before fixing')
    parser.add_argument('--model', help='AI model to use (e.g., codellama:7b, starcoder:7b)')
    parser.add_argument('--list-models', action='store_true', help='List available Ollama models and exit')
    parser.add_argument('--interactive', action='store_true', help='Show interactive model selection menu')
    
    args = parser.parse_args()
    
    # Load profile
    profile_path = Path(__file__).parent / 'mod_fixer_profiles' / f'{args.profile}.yaml'
    if not profile_path.exists():
        print_status(f"Profile not found: {profile_path}", "ERROR")
        return 1
    
    # Show header
    print_status_header("Mod Fixer - AI-Assisted Mod Fixing", Colors.CYAN)
    
    # Initialize fixer
    fixer = ModFixer(
        str(profile_path),
        ollama_url=args.ollama_url,
        sandbox_dir=args.sandbox_dir,
        api_rules_path=args.api_rules,
        preferred_model=getattr(args, 'model', None)
    )
    
    # Handle list models
    if args.list_models:
        show_model_list(args.ollama_url)
        return 0
    
    # Handle interactive model selection
    selected_model = None
    if args.interactive:
        selected_model = show_model_menu(args.ollama_url, args.model or "")
        if selected_model is not None:
            args.model = selected_model
    
    # Run API check if requested
    if args.check_api and fixer.api_checker:
        print_status("Running API compatibility check...", "PROCESSING")
        api_report = fixer.api_checker.generate_api_check_report(Path(args.mod_path))
        print_section_header("API Check Results", Colors.CYAN)
        print_status(f"API Version: {api_report['api_version']}", "INFO")
        print_status(f"Total Issues: {api_report['total_issues']}", 
                    "ERROR" if api_report['errors'] > 0 else "WARNING" if api_report['warnings'] > 0 else "INFO")
        print_status(f"  Errors: {api_report['errors']}", "ERROR" if api_report['errors'] > 0 else "INFO")
        print_status(f"  Warnings: {api_report['warnings']}", "WARNING" if api_report['warnings'] > 0 else "INFO")
        print_status(f"  Info: {api_report['infos']}", "INFO")
        
        if api_report['total_issues'] > 0:
            print()
            print_status(f"Issues found in {len(api_report['issues_by_file'])} files", "WARNING")
            if not args.issue or "api" in args.issue.lower() or "compatibility" in args.issue.lower():
                print_status("Consider using --template fix_api_compatibility to fix these issues", "INFO")
        print()
    
    # Generate fix
    print_status(f"Generating fix for {args.profile} mod...", "PROCESSING")
    try:
        fix_data = fixer.generate_fix(
            args.mod_path,
            args.issue,
            prompt_template=args.template,
            context_files=args.context_files
        )
        
        print_section_header("FIX GENERATED", Colors.SUCCESS)
        files_count = len(fix_data.get('diff', '').split('---')) - 1
        print_status(f"Files to change: {files_count}", "INFO")
        print_status(f"Notes: {fix_data.get('notes', 'N/A')}", "INFO")
        
        # Apply fix (dry-run by default)
        mode = "DRY-RUN" if not args.apply else "LIVE"
        mode_color = Colors.WARNING if not args.apply else Colors.ERROR
        print()
        print_status(f"Applying fix ({mode})...", "PROCESSING")
        report = fixer.apply_fix(args.mod_path, fix_data, dry_run=not args.apply)
        
        print_section_header("FIX REPORT", Colors.CYAN)
        print_status(f"Profile: {report.profile}", "INFO")
        print_status(f"Files changed: {len(report.files_changed)}", "INFO")
        print_status(f"Lines changed: {report.lines_changed}", "INFO")
        print_status(f"Applied: {report.applied}", "SUCCESS" if report.applied else "WARNING")
        print_status(f"Patch hash: {report.patch_hash}", "INFO")
        
        print()
        print_status("Validation Results:", "INFO")
        for name, result in report.validation_results.items():
            status_type = "SUCCESS" if result.get('success') else "ERROR"
            print_status(f"{name}", status_type)
            if not result.get('success') and result.get('stderr'):
                print(f"    {Colors.ERROR}Error: {result['stderr'][:200]}{Colors.RESET}")
        
        # Save report
        if args.output_report:
            fixer.save_report(report, args.output_report)
            print()
            print_status(f"Report saved to: {args.output_report}", "SUCCESS")
        
        if not args.apply:
            print()
            print_status("This was a DRY-RUN. Use --apply to apply the fix.", "WARNING")
        
        return 0
        
    except Exception as e:
        print()
        print_status_header("ERROR", Colors.ERROR)
        print_status(str(e), "ERROR")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

