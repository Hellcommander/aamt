#!/usr/bin/env python3
"""
Caves of Qud Mod Fixer
Automatically fixes mods to work with newer API versions and corrects Harmony patch asset references.
Uses AI code models (StarCoder 7B or Code Llama 7B preferred) via Ollama for intelligent code fixes.
"""

import os
import sys
import re
import json
import shutil
import hashlib
import subprocess
import tempfile
import psutil
import time
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import difflib

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

# Add Shared directory to path for Ollama integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Shared"))
try:
    from ollama_integration import (
        test_ollama_connection,
        call_ollama,
        get_optimal_thread_count,
        AI_CONFIG
    )
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: Ollama integration not available")

# Import shared tool helpers
try:
    from tool_helpers import (
        SingleInstanceLock,
        WorkerScaler,
        FileComplexity,
        process_files_parallel,
        safe_print
    )
    TOOL_HELPERS_AVAILABLE = True
except ImportError:
    TOOL_HELPERS_AVAILABLE = False
    print("Info: Shared tool helpers not available, using local implementations")

# Try to import RAG system
try:
    from rag_system import RAGSystem, RetrievalResult
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Info: RAG system not available. Install with: python Shared/rag_setup.py")

# Try to import existing model router (enhanced with multimodel features)
try:
    import sys
    from pathlib import Path
    router_path = Path(__file__).parent.parent / "Common" / "ollama_model_router.py"
    if router_path.exists():
        sys.path.insert(0, str(router_path.parent))
        from ollama_model_router import OllamaModelRouter, RoutingDecision, TaskIntent
        MULTIMODEL_ROUTER_AVAILABLE = True
    else:
        MULTIMODEL_ROUTER_AVAILABLE = False
        print("Info: Model router not found")
except ImportError as e:
    MULTIMODEL_ROUTER_AVAILABLE = False
    print(f"Info: Model router not available: {e}")

# Try to import Unity asset generator
try:
    from unity_asset_generator import UnityAssetGenerator
    UNITY_ASSET_GENERATOR_AVAILABLE = True
except ImportError:
    UNITY_ASSET_GENERATOR_AVAILABLE = False
    print("Info: Unity asset generator not available")

# ANSI color codes for cross-platform terminal colors
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Status colors
    SUCCESS = '\033[92m'  # Green
    ERROR = '\033[91m'    # Red
    WARNING = '\033[93m'  # Yellow
    YELLOW = '\033[93m'   # Yellow (alias for WARNING)
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
    # Use ASCII-safe symbols for Windows compatibility
    import sys
    if sys.platform == 'win32':
        status_symbols = {
            "SUCCESS": "[OK]",
            "ERROR": "[X]",
            "WARNING": "[!]",
            "INFO": "[i]",
            "PROCESSING": "[...]"
        }
    else:
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
    try:
        print(f"  [{color_code}{symbol}{Colors.RESET}] {message}")
    except UnicodeEncodeError:
        # Fallback to ASCII-only if encoding fails
        print(f"  [{symbol}] {message}")


def get_ollama_models(ollama_url: str = "http://localhost:11434") -> Optional[List[Dict[str, Any]]]:
    """Get list of available Ollama models."""
    if not OLLAMA_AVAILABLE:
        return None
    
    try:
        import requests
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
                # Handle both int and str types for modified timestamp
                try:
                    modified_val = int(modified) if isinstance(modified, str) else modified
                    date = datetime.fromtimestamp(modified_val / 1000)
                    modified_str = f" - Modified: {date.strftime('%Y-%m-%d %H:%M')}"
                except (ValueError, TypeError):
                    modified_str = ""
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
                # Handle both int and str types for modified timestamp
                try:
                    modified_val = int(modified) if isinstance(modified, str) else modified
                    date = datetime.fromtimestamp(modified_val / 1000)
                    modified_str = f" - Modified: {date.strftime('%Y-%m-%d %H:%M')}"
                except (ValueError, TypeError):
                    modified_str = ""
            else:
                modified_str = ""
            print(f"    • {name}{size_gb}{modified_str}")
        print()
    
    print_status(f"Total models: {len(models)}", "INFO")


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
    if save_path is None:
        save_path = QUD_SAVE_PATH
    
    default_log_paths = [
        save_path / "Player.log",
        save_path / "Player-prev.log",
        save_path / "game_log.txt",
        save_path / "harmony.log.txt",
        save_path / "errors found.txt",
        save_path / "build_log.txt",
    ]
    
    # Add numbered game logs
    for i in range(30):
        default_log_paths.append(save_path / f"game_log.{i}.txt")
    
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
                        'could not', 'missing', 'not found', 'nullreference',
                        'invalid', 'broken', 'crash', 'stacktrace', 'stack trace'
                    ]):
                        # If mod_name is specified, filter for that mod
                        if mod_name and mod_name.lower() not in line_lower:
                            # Check if it's a general error that might affect the mod
                            if not any(general in line_lower for general in [
                                'system.', 'unity', 'mono', 'physics', 'graphics'
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

# Configuration
QUD_SOURCE_PATH = Path("G:/CavesofQud-decompiledsource/Assembly-CSharp")
QUD_STREAMING_ASSETS = Path("E:/SteamLibrary/steamapps/common/Caves of Qud/CoQ_Data/StreamingAssets")
QUD_MODS_PATH = Path("C:/Users/Arend/AppData/LocalLow/Freehold Games/CavesOfQud/Mods")
QUD_WORKSHOP_PATH = Path("E:/SteamLibrary/steamapps/workshop/content/333640")
QUD_SAVE_PATH = Path("C:/Users/Arend/AppData/LocalLow/Freehold Games/CavesOfQud")

# CPU Management
# Note: We leave 6% of cores free to prevent all cores from maxing at 100%
# CPUs run slower when all cores are maxed by design, so leaving some cores free
# ensures active cores have headroom and the CPU doesn't throttle
CPU_HEADROOM_PERCENT = 6.0  # Leave 6% of cores free (prevents cores from maxing at 100%)


@dataclass
class ModFile:
    """Represents a mod file to be analyzed."""
    path: Path
    content: str
    file_type: str  # 'cs', 'xml', 'json', etc.
    is_harmony_patch: bool
    asset_references: List[str]
    api_calls: List[str]


@dataclass
class FixResult:
    """Result of a fix operation."""
    file_path: str
    success: bool
    changes: List[str]
    original_content: str
    fixed_content: str
    errors: List[str]


@dataclass
class ModAnalysis:
    """Analysis results for a mod."""
    mod_path: Path
    files: List[ModFile]
    api_issues: List[Dict[str, Any]]
    asset_issues: List[Dict[str, Any]]
    harmony_patches: List[Dict[str, Any]]


class CPUManager:
    """Manages CPU usage to prevent burn-in test behavior.
    
    Leaves 6% of total cores free to ensure each core has headroom (not maxed at 100%).
    This prevents burn-in test detection by ensuring cores aren't fully saturated.
    """
    
    def __init__(self):
        self.cpu_count = psutil.cpu_count()
        # Leave 6% of cores free to provide headroom (prevents cores from being maxed at 100%)
        import math
        cores_to_leave = max(1, math.ceil(self.cpu_count * 0.06))
        self.available_cores = max(1, self.cpu_count - cores_to_leave)
        self.headroom_percent = CPU_HEADROOM_PERCENT
        
    def get_optimal_threads(self) -> int:
        """Get optimal thread count for Ollama (leaves 6% of cores free)."""
        return self.available_cores
    
    def monitor_cpu_usage(self, duration: float = 1.0):
        """Monitor CPU usage.
        
        Note: Idle cores are normal and expected. We leave 6% of cores free to prevent
        all cores from maxing at 100%, which causes CPUs to run slower by design.
        This function is kept for potential future diagnostics but doesn't warn about
        idle cores since that's expected behavior.
        """
        cpu_percent = psutil.cpu_percent(interval=duration, percpu=True)
        avg_percent = sum(cpu_percent) / len(cpu_percent) if cpu_percent else 0
        
        # Don't warn about idle cores - that's normal and expected
        # The 6% headroom (leaving cores free) prevents cores from maxing at 100%
        # which would cause the CPU to throttle and run slower
        
        return avg_percent


class SourceCodeIndex:
    """Indexes the decompiled source code for API comparison."""
    
    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.class_index: Dict[str, List[Path]] = {}
        self.method_index: Dict[str, List[Tuple[Path, int]]] = {}
        self.api_signatures: Dict[str, str] = {}
        self._build_index()
    
    def _build_index(self):
        """Build indexes of classes and methods from source code."""
        print(f"  Indexing source code from {self.source_path}...")
        
        if not self.source_path.exists():
            print(f"  Warning: Source path does not exist: {self.source_path}")
            return
        
        # Include both Assembly-CSharp and Unity audio modules for audio-based mods
        cs_files = list(self.source_path.rglob("*.cs"))
        
        # Also include Unity audio module if it exists at the parent level
        unity_audio_path = self.source_path.parent / "UnityEngine.AudioModule"
        if unity_audio_path.exists():
            cs_files.extend(list(unity_audio_path.rglob("*.cs")))
        print(f"  Found {len(cs_files)} C# files")
        
        for cs_file in cs_files:
            try:
                with open(cs_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    self._index_file(cs_file, content)
            except Exception as e:
                print(f"  Warning: Could not index {cs_file}: {e}")
        
        print(f"  Indexed {len(self.class_index)} classes, {len(self.method_index)} methods")
    
    def _index_file(self, file_path: Path, content: str):
        """Index a single C# file."""
        # Extract class names
        class_pattern = r'(?:public|private|internal|protected)?\s*(?:static\s+)?(?:sealed\s+)?(?:abstract\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            if class_name not in self.class_index:
                self.class_index[class_name] = []
            self.class_index[class_name].append(file_path)
        
        # Extract method signatures
        method_pattern = r'(?:public|private|internal|protected)?\s*(?:static\s+)?(?:virtual\s+)?(?:override\s+)?(?:async\s+)?(\w+)\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(method_pattern, content):
            return_type = match.group(1)
            method_name = match.group(2)
            method_key = f"{method_name}"
            
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            if method_key not in self.method_index:
                self.method_index[method_key] = []
            self.method_index[method_key].append((file_path, line_num))
            
            # Store full signature
            full_sig = match.group(0)
            self.api_signatures[method_key] = full_sig
    
    def find_class(self, class_name: str) -> List[Path]:
        """Find files containing a class."""
        return self.class_index.get(class_name, [])
    
    def find_method(self, method_name: str) -> List[Tuple[Path, int]]:
        """Find files and line numbers containing a method."""
        return self.method_index.get(method_name, [])
    
    def get_method_signature(self, method_name: str) -> Optional[str]:
        """Get the signature of a method."""
        return self.api_signatures.get(method_name)


class AssetReferenceChecker:
    """Checks and fixes asset references in Harmony patches."""
    
    def __init__(self, streaming_assets_path: Path, mods_path: Optional[Path] = None, workshop_path: Optional[Path] = None):
        self.streaming_assets_path = streaming_assets_path
        self.mods_path = mods_path
        self.workshop_path = workshop_path
        self.asset_cache: Dict[str, bool] = {}
        self._mod_asset_cache: Dict[str, Path] = {}  # Maps asset paths to mod directories
        self._build_asset_index()
    
    def _build_asset_index(self):
        """Build comprehensive asset index by parsing XML files in StreamingAssets."""
        print(f"  Indexing assets from XML files in {self.streaming_assets_path}...")
        
        if not self.streaming_assets_path.exists():
            print(f"  Warning: StreamingAssets path does not exist: {self.streaming_assets_path}")
            return
        
        # Initialize warning flags
        self._workshop_limit_warned = False
        self._workshop_error_warned = False
        
        xml_count = 0
        asset_refs_found = 0
        
        # Find all XML files in Base and DLC directories
        xml_files = []
        base_path = self.streaming_assets_path / "Base"
        dlc_path = self.streaming_assets_path / "DLC"
        
        if base_path.exists():
            xml_files.extend(base_path.rglob("*.xml"))
        if dlc_path.exists():
            xml_files.extend(dlc_path.rglob("*.xml"))
        
        print(f"    Found {len(xml_files)} XML files to parse...")
        
        # Parse XML files to extract asset references
        for xml_file in xml_files:
            try:
                xml_count += 1
                if xml_count % 100 == 0:
                    print(f"      Parsed {xml_count}/{len(xml_files)} XML files...")
                
                # Store XML file path itself
                rel_path = xml_file.relative_to(self.streaming_assets_path)
                xml_asset_path = str(rel_path).replace('\\', '/')
                self.asset_cache[xml_asset_path] = True
                
                # Parse XML to extract asset references
                try:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    # Extract asset references from XML
                    assets = self._extract_assets_from_xml(root, xml_file)
                    for asset_path in assets:
                        if asset_path and asset_path.strip():
                            normalized = asset_path.replace('\\', '/').strip()
                            # Store with and without extension
                            self.asset_cache[normalized] = True
                            if '.' in normalized:
                                normalized_no_ext = normalized.rsplit('.', 1)[0]
                                self.asset_cache[normalized_no_ext] = True
                            asset_refs_found += 1
                except ET.ParseError:
                    # Skip malformed XML files
                    continue
                except Exception as e:
                    # Skip files that can't be parsed
                    continue
                    
            except Exception as e:
                continue
        
        print(f"  Indexed {len(self.asset_cache)} asset paths from {xml_count} XML files:")
        print(f"    - {xml_count} XML files parsed")
        print(f"    - {asset_refs_found} asset references extracted")
        
        # Check for Base and DLC subdirectories
        if base_path.exists():
            print(f"    - Found Base directory")
        if dlc_path.exists():
            print(f"    - Found DLC directory")
        
        # Index mod directories (for cross-mod asset references)
        if self.mods_path and self.mods_path.exists():
            print(f"    - Found Mods directory: {self.mods_path}")
        if self.workshop_path and self.workshop_path.exists():
            try:
                workshop_count = len([d for d in self.workshop_path.iterdir() if d.is_dir()])
                print(f"    - Found Workshop directory: {self.workshop_path} ({workshop_count} mods)")
                if workshop_count > 100:
                    print(f"      Note: Workshop scanning is limited to prevent crashes on large directories")
            except Exception as e:
                print(f"    - Found Workshop directory: {self.workshop_path} (could not count: {e})")
    
    def _extract_assets_from_xml(self, element: ET.Element, xml_file: Path) -> Set[str]:
        """Recursively extract asset references from XML elements."""
        assets = set()
        
        # Common attributes that contain asset paths or IDs
        asset_attributes = [
            'Sound', 'Sounds', 'SoundFile', 'Audio', 'AudioFile',
            'Texture', 'TextureFile', 'Image', 'ImageFile', 'Sprite',
            'Tile', 'TileFile', 'Icon', 'IconFile',
            'Model', 'ModelFile', 'Mesh', 'MeshFile',
            'Prefab', 'PrefabFile', 'Asset', 'AssetPath',
            'MissileFireSound', 'DetonatedSound', 'AmbientIdleSound',
            'AttackSound', 'HitSound', 'DeathSound', 'SpawnSound',
            'FireSound', 'AmbientSound', 'IdleSound', 'WalkSound',
            'RunSound', 'JumpSound', 'LandSound', 'UseSound'
        ]
        
        # Check element attributes
        for attr_name, attr_value in element.attrib.items():
            if attr_value and isinstance(attr_value, str) and attr_value.strip():
                attr_value = attr_value.strip()
                
                # Check if attribute name suggests it's an asset
                if any(keyword.lower() in attr_name.lower() for keyword in asset_attributes):
                    # Add the value as-is (could be ID or path)
                    assets.add(attr_value)
                    
                    # If it looks like a sound ID (no path separators, no extension), 
                    # also try common sound path formats
                    if '/' not in attr_value and '\\' not in attr_value and '.' not in attr_value:
                        # Try Sounds/ prefix
                        assets.add(f"Sounds/{attr_value}")
                        # Try Base/Sounds/ prefix
                        assets.add(f"Base/Sounds/{attr_value}")
                
                # Also check if value looks like a path
                elif '/' in attr_value or '\\' in attr_value:
                    # Check if it looks like an asset path
                    if any(ext in attr_value.lower() for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac', '.png', '.jpg', '.jpeg', '.xml']):
                        assets.add(attr_value)
                    elif attr_value.startswith('Sounds/') or 'Sounds/' in attr_value:
                        assets.add(attr_value)
        
        # Check element text content
        if element.text and element.text.strip():
            text = element.text.strip()
            # Check if text looks like an asset path
            if '/' in text or '\\' in text:
                if any(ext in text.lower() for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac', '.png', '.jpg', '.jpeg', '.xml']):
                    assets.add(text)
                elif text.startswith('Sounds/') or 'Sounds/' in text:
                    assets.add(text)
        
        # Recursively process child elements
        for child in element:
            assets.update(self._extract_assets_from_xml(child, xml_file))
        
        return assets
    
    def check_asset_exists(self, asset_path: str) -> bool:
        """Check if an asset path exists in StreamingAssets (Base or DLC)."""
        if not asset_path or not asset_path.strip():
            return False
        
        # Normalize path
        normalized = asset_path.replace('\\', '/').strip()
        
        # Remove leading slashes
        if normalized.startswith('/'):
            normalized = normalized[1:]
        
        # Check cache first (fastest)
        if normalized in self.asset_cache:
            return True
        
        # Try direct path match
        full_path = self.streaming_assets_path / normalized
        if full_path.exists():
            self.asset_cache[normalized] = True
            return True
        
        # Try in Base subdirectory
        base_path = self.streaming_assets_path / "Base" / normalized
        if base_path.exists():
            base_normalized = f"Base/{normalized}"
            self.asset_cache[base_normalized] = True
            self.asset_cache[normalized] = True  # Also cache without Base prefix
            return True
        
        # Try in DLC subdirectories
        dlc_path = self.streaming_assets_path / "DLC"
        if dlc_path.exists():
            for dlc_dir in dlc_path.iterdir():
                if dlc_dir.is_dir():
                    dlc_asset_path = dlc_dir / normalized
                    if dlc_asset_path.exists():
                        dlc_normalized = f"DLC/{dlc_dir.name}/{normalized}"
                        self.asset_cache[dlc_normalized] = True
                        self.asset_cache[normalized] = True  # Also cache without DLC prefix
                        return True
        
        # For sound references, check Sounds directories on-demand (not pre-indexed to save tokens)
        # Check if this looks like a sound reference (no extension, or common sound extensions)
        is_sound_ref = (
            not '.' in normalized or 
            normalized.lower().endswith(('.wav', '.ogg', '.mp3', '.aac', '.flac')) or
            'sound' in normalized.lower()
        )
        
        if is_sound_ref:
            # Try without file extension first (sound IDs are often referenced without extension)
            normalized_no_ext = normalized.rsplit('.', 1)[0] if '.' in normalized else normalized
            
            # Check Base/Sounds directory
            sounds_base = self.streaming_assets_path / "Base" / "Sounds"
            if sounds_base.exists():
                for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac']:
                    sound_file = sounds_base / f"{normalized_no_ext}{ext}"
                    if sound_file.exists():
                        sound_path = f"Base/Sounds/{normalized_no_ext}{ext}"
                        self.asset_cache[sound_path] = True
                        self.asset_cache[normalized_no_ext] = True
                        self.asset_cache[normalized] = True
                        return True
                    # Also try with just the filename (in case it's in a subdirectory)
                    for sound_file in sounds_base.rglob(f"{normalized_no_ext}{ext}"):
                        rel_path = sound_file.relative_to(self.streaming_assets_path)
                        sound_path = str(rel_path).replace('\\', '/')
                        self.asset_cache[sound_path] = True
                        self.asset_cache[normalized_no_ext] = True
                        self.asset_cache[normalized] = True
                        return True
            
            # Check DLC/Sounds directories
            if dlc_path.exists():
                for dlc_dir in dlc_path.iterdir():
                    if dlc_dir.is_dir():
                        sounds_dlc = dlc_dir / "Sounds"
                        if sounds_dlc.exists():
                            for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac']:
                                sound_file = sounds_dlc / f"{normalized_no_ext}{ext}"
                                if sound_file.exists():
                                    sound_path = f"DLC/{dlc_dir.name}/Sounds/{normalized_no_ext}{ext}"
                                    self.asset_cache[sound_path] = True
                                    self.asset_cache[normalized_no_ext] = True
                                    self.asset_cache[normalized] = True
                                    return True
                                # Also try with just the filename
                                for sound_file in sounds_dlc.rglob(f"{normalized_no_ext}{ext}"):
                                    rel_path = sound_file.relative_to(self.streaming_assets_path)
                                    sound_path = str(rel_path).replace('\\', '/')
                                    self.asset_cache[sound_path] = True
                                    self.asset_cache[normalized_no_ext] = True
                                    self.asset_cache[normalized] = True
                                    return True
            
            # Check mod directories for cross-mod asset references
            if self.mods_path and self.mods_path.exists():
                for mod_dir in self.mods_path.iterdir():
                    if mod_dir.is_dir():
                        # Check mod's Sounds directory
                        mod_sounds = mod_dir / "Sounds"
                        if mod_sounds.exists():
                            for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac']:
                                for sound_file in mod_sounds.rglob(f"{normalized_no_ext}{ext}"):
                                    self.asset_cache[normalized] = True
                                    self.asset_cache[normalized_no_ext] = True
                                    self._mod_asset_cache[normalized] = mod_dir
                                    return True
                        # Also check root of mod directory
                        for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac']:
                            sound_file = mod_dir / f"{normalized_no_ext}{ext}"
                            if sound_file.exists():
                                self.asset_cache[normalized] = True
                                self.asset_cache[normalized_no_ext] = True
                                self._mod_asset_cache[normalized] = mod_dir
                                return True
            
            # Check workshop directories (with error handling and limits)
            # NOTE: Workshop scanning is done on-demand (lazy) to prevent initialization crashes
            # Only scan when actually looking for a specific asset
            if self.workshop_path and self.workshop_path.exists():
                try:
                    # Get workshop dirs (with limit to prevent crashes)
                    if not hasattr(self, '_workshop_dirs_cached'):
                        try:
                            all_dirs = list(self.workshop_path.iterdir())
                            # Limit to prevent crashes - even 318 mods can be slow with recursive searches
                            max_workshop_dirs = 200  # Reduced limit for better performance
                            if len(all_dirs) > max_workshop_dirs:
                                if not hasattr(self, '_workshop_limit_warned'):
                                    print(f"      Warning: {len(all_dirs)} workshop mods found, limiting scan to {max_workshop_dirs} to prevent crashes")
                                    self._workshop_limit_warned = True
                                all_dirs = all_dirs[:max_workshop_dirs]
                            self._workshop_dirs_cached = [d for d in all_dirs if d.is_dir()]
                        except Exception as e:
                            if not hasattr(self, '_workshop_error_warned'):
                                print(f"      Warning: Could not list workshop directory: {e}")
                                self._workshop_error_warned = True
                            self._workshop_dirs_cached = []
                    
                    # Only check first 50 mods per asset lookup to prevent slowdown
                    workshop_dirs_to_check = self._workshop_dirs_cached[:50]
                    
                    for workshop_mod_dir in workshop_dirs_to_check:
                        try:
                            # Check root first (fastest)
                            for ext in ['.wav', '.ogg', '.mp3', '.aac', '.flac']:
                                sound_file = workshop_mod_dir / f"{normalized_no_ext}{ext}"
                                if sound_file.exists():
                                    self.asset_cache[normalized] = True
                                    self.asset_cache[normalized_no_ext] = True
                                    self._mod_asset_cache[normalized] = workshop_mod_dir
                                    return True
                            
                            # Only check Sounds subdirectory if root check failed (slower)
                            workshop_sounds = workshop_mod_dir / "Sounds"
                            if workshop_sounds.exists():
                                try:
                                    # Very limited recursive search - only check first 3 matches
                                    for ext in ['.wav', '.ogg', '.mp3']:
                                        matches = list(workshop_sounds.rglob(f"{normalized_no_ext}{ext}"))[:3]
                                        for sound_file in matches:
                                            if sound_file.exists():
                                                self.asset_cache[normalized] = True
                                                self.asset_cache[normalized_no_ext] = True
                                                self._mod_asset_cache[normalized] = workshop_mod_dir
                                                return True
                                except (OSError, PermissionError):
                                    continue
                        except (OSError, PermissionError, Exception):
                            continue
                except Exception as e:
                    # Silently skip workshop if there's an error
                    pass
        
        # For non-sound assets, also check mod directories
        # Check mod directories
        if self.mods_path and self.mods_path.exists():
            for mod_dir in self.mods_path.iterdir():
                if mod_dir.is_dir():
                    asset_file = mod_dir / normalized
                    if asset_file.exists():
                        self.asset_cache[normalized] = True
                        self._mod_asset_cache[normalized] = mod_dir
                        return True
                    # Also check recursively
                    for asset_file in mod_dir.rglob(normalized):
                        self.asset_cache[normalized] = True
                        self._mod_asset_cache[normalized] = mod_dir
                        return True
        
        # Check workshop directories (with error handling and limits)
        # NOTE: Workshop scanning is done on-demand (lazy) to prevent initialization crashes
        if self.workshop_path and self.workshop_path.exists():
            try:
                # Get workshop dirs (with limit to prevent crashes)
                if not hasattr(self, '_workshop_dirs_cached'):
                    try:
                        all_dirs = list(self.workshop_path.iterdir())
                        # Limit to prevent crashes - even 318 mods can be slow with recursive searches
                        max_workshop_dirs = 200  # Reduced limit for better performance
                        if len(all_dirs) > max_workshop_dirs:
                            if not hasattr(self, '_workshop_limit_warned'):
                                print(f"      Warning: {len(all_dirs)} workshop mods found, limiting scan to {max_workshop_dirs} to prevent crashes")
                                self._workshop_limit_warned = True
                            all_dirs = all_dirs[:max_workshop_dirs]
                        self._workshop_dirs_cached = [d for d in all_dirs if d.is_dir()]
                    except Exception as e:
                        if not hasattr(self, '_workshop_error_warned'):
                            print(f"      Warning: Could not list workshop directory: {e}")
                            self._workshop_error_warned = True
                        self._workshop_dirs_cached = []
                
                # Only check first 50 mods per asset lookup to prevent slowdown
                workshop_dirs_to_check = self._workshop_dirs_cached[:50]
                
                for workshop_mod_dir in workshop_dirs_to_check:
                    try:
                        # Check root first (fastest)
                        asset_file = workshop_mod_dir / normalized
                        if asset_file.exists():
                            self.asset_cache[normalized] = True
                            self._mod_asset_cache[normalized] = workshop_mod_dir
                            return True
                        
                        # Only do recursive search if root check failed (much slower)
                        try:
                            # Very limited recursive search - only check first 5 matches
                            matches = list(workshop_mod_dir.rglob(normalized))[:5]
                            for asset_file in matches:
                                if asset_file.exists():
                                    self.asset_cache[normalized] = True
                                    self._mod_asset_cache[normalized] = workshop_mod_dir
                                    return True
                        except (OSError, PermissionError):
                            continue
                    except (OSError, PermissionError, Exception):
                        continue
            except Exception as e:
                # Silently skip workshop if there's an error
                pass
        
        return False
    
    def find_similar_asset(self, asset_path: str) -> Optional[str]:
        """Find a similar asset if the exact one doesn't exist."""
        # Extract key parts of the path
        parts = asset_path.lower().split('/')
        search_terms = [p for p in parts if p and p not in ['sounds', 'abilities', 'ui', 'melee']]
        
        # Search for similar assets
        for cached_path in self.asset_cache.keys():
            cached_lower = cached_path.lower()
            if any(term in cached_lower for term in search_terms if term):
                return cached_path
        
        return None


class ModAnalyzer:
    """Analyzes mod files for issues."""
    
    def __init__(self, source_index: SourceCodeIndex, asset_checker: AssetReferenceChecker):
        self.source_index = source_index
        self.asset_checker = asset_checker
    
    def analyze_mod(self, mod_path: Path) -> ModAnalysis:
        """Analyze a mod directory for issues."""
        print_section_header(f"ANALYZING MOD: {mod_path.name}", Colors.CYAN)
        
        files = []
        api_issues = []
        asset_issues = []
        harmony_patches = []
        
        # Find all C# files
        cs_files = list(mod_path.rglob("*.cs"))
        
        for cs_file in cs_files:
            try:
                with open(cs_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                mod_file = self._parse_file(cs_file, content, mod_path)
                files.append(mod_file)
                
                # Check for Harmony patches
                if mod_file.is_harmony_patch:
                    harmony_info = self._analyze_harmony_patch(mod_file)
                    harmony_patches.append(harmony_info)
                
                # Check API calls
                api_issues.extend(self._check_api_calls(mod_file))
                
                # Check asset references
                asset_issues.extend(self._check_asset_references(mod_file))
                
                # Check activated abilities for common issues
                api_issues.extend(self._check_activated_ability_issues(mod_file))
                
            except Exception as e:
                print(f"  Error analyzing {cs_file}: {e}")
        
        return ModAnalysis(
            mod_path=mod_path,
            files=files,
            api_issues=api_issues,
            asset_issues=asset_issues,
            harmony_patches=harmony_patches
        )
    
    def _parse_file(self, file_path: Path, content: str, mod_path: Path) -> ModFile:
        """Parse a file and extract information."""
        file_type = file_path.suffix[1:] if file_path.suffix else 'unknown'
        is_harmony = 'Harmony' in content or 'HarmonyPatch' in content or 'HarmonyLib' in content
        
        # Extract asset references (sound paths, etc.)
        # More comprehensive patterns to catch all asset references
        asset_patterns = [
            r'["\'](Sounds/[^"\']+)["\']',  # Sounds/Abilities/...
            r'["\']([^"\']+\.(wav|ogg|mp3|aac|flac))["\']',  # File with extension
            r'PlayWorldSound\s*\(\s*["\']([^"\']+)["\']',  # PlayWorldSound("...")
            r'PlayWorldSoundTag\s*\(\s*["\']([^"\']+)["\']',  # PlayWorldSoundTag("...")
            r'PlaySound\s*\(\s*["\']([^"\']+)["\']',  # PlaySound("...")
            r'SoundManager\.PlaySound\s*\(\s*["\']([^"\']+)["\']',  # SoundManager.PlaySound("...")
            r'Sound\s*[:=]\s*["\']([^"\']+)["\']',  # Sound = "..." or Sound: "..."
            r'["\'](Base/[^"\']+\.xml)["\']',  # Base/ObjectBlueprints.xml
            r'["\'](DLC/[^"\']+\.xml)["\']',  # DLC/.../ObjectBlueprints.xml
            r'Resources\.Load\s*<\w+>\s*\(\s*["\']([^"\']+)["\']',  # Resources.Load<...>("...")
            r'AssetDatabase\.LoadAssetAtPath\s*\(\s*["\']([^"\']+)["\']',  # AssetDatabase.LoadAssetAtPath("...")
        ]
        
        asset_refs = []
        for pattern in asset_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                asset_refs.append(match.group(1))
        
        # Extract API calls (method calls on game objects)
        api_patterns = [
            r'(\w+)\.(\w+)\s*\(',
            r'typeof\((\w+)\)',
        ]
        
        api_calls = []
        for pattern in api_patterns:
            for match in re.finditer(pattern, content):
                api_calls.append(match.group(0))
        
        return ModFile(
            path=file_path,
            content=content,
            file_type=file_type,
            is_harmony_patch=is_harmony,
            asset_references=asset_refs,
            api_calls=api_calls
        )
    
    def _analyze_harmony_patch(self, mod_file: ModFile) -> Dict[str, Any]:
        """Analyze a Harmony patch file."""
        return {
            'file': str(mod_file.path),
            'has_asset_refs': len(mod_file.asset_references) > 0,
            'asset_refs': mod_file.asset_references
        }
    
    def _check_api_calls(self, mod_file: ModFile) -> List[Dict[str, Any]]:
        """Check if API calls exist in source code."""
        issues = []
        
        for api_call in mod_file.api_calls:
            # Extract method/class name
            match = re.search(r'(\w+)\.(\w+)', api_call)
            if match:
                class_name = match.group(1)
                method_name = match.group(2)
                
                # Check if class exists
                class_files = self.source_index.find_class(class_name)
                if not class_files:
                    issues.append({
                        'file': str(mod_file.path),
                        'type': 'missing_class',
                        'class': class_name,
                        'api_call': api_call
                    })
                else:
                    # Check if method exists
                    method_locations = self.source_index.find_method(method_name)
                    if not method_locations:
                        issues.append({
                            'file': str(mod_file.path),
                            'type': 'missing_method',
                            'class': class_name,
                            'method': method_name,
                            'api_call': api_call
                        })
        
        return issues
    
    def _check_asset_references(self, mod_file: ModFile) -> List[Dict[str, Any]]:
        """Check if asset references are valid."""
        issues = []
        
        for asset_ref in mod_file.asset_references:
            if not self.asset_checker.check_asset_exists(asset_ref):
                similar = self.asset_checker.find_similar_asset(asset_ref)
                issues.append({
                    'file': str(mod_file.path),
                    'type': 'missing_asset',
                    'asset': asset_ref,
                    'similar': similar
                })
        
        return issues
    
    def _check_activated_ability_issues(self, mod_file: ModFile) -> List[Dict[str, Any]]:
        """Check for common activated ability issues."""
        issues = []
        content = mod_file.content
        
        # Pattern 1: Detect AddMyActivatedAbility calls
        ability_pattern = r'(\w+)\s*=\s*AddMyActivatedAbility\s*\(\s*["\']([^"\']+)["\']'
        ability_matches = list(re.finditer(ability_pattern, content, re.MULTILINE))
        
        for match in ability_matches:
            ability_var = match.group(1)
            ability_name = match.group(2)
            ability_line = match.start()
            
            # Count lines to get line number
            line_num = content[:ability_line].count('\n') + 1
            
            # Check if there's a corresponding cooldown application
            # Look for patterns like: ApplyCooldown, LinkCooldowns, SetCooldown
            cooldown_patterns = [
                rf'{ability_var}[^;]*Cooldown',
                r'ApplyCooldown\s*\([^)]*' + re.escape(ability_var),
                r'LinkCooldowns\s*\([^)]*' + re.escape(ability_var),
                r'SetCooldown\s*\([^)]*' + re.escape(ability_var),
            ]
            
            has_cooldown = False
            for cooldown_pattern in cooldown_patterns:
                if re.search(cooldown_pattern, content, re.IGNORECASE):
                    has_cooldown = True
                    break
            
            if not has_cooldown:
                issues.append({
                    'file': str(mod_file.path),
                    'type': 'activated_ability_no_cooldown',
                    'ability_name': ability_name,
                    'ability_var': ability_var,
                    'line': line_num,
                    'severity': 'high',
                    'description': f'Activated ability "{ability_name}" has no cooldown application, allowing infinite spam'
                })
        
        # Pattern 2: Check for command methods without proper returns or energy costs
        command_pattern = r'public\s+(?:virtual\s+|override\s+)?bool\s+(Command\w+)\s*\([^)]*GameObject\s+(\w+)[^)]*\)'
        for match in re.finditer(command_pattern, content, re.MULTILINE):
            method_name = match.group(1)
            param_name = match.group(2)
            method_start = match.end()
            
            # Find the method body (look for the closing brace)
            brace_count = 0
            method_end = method_start
            found_opening = False
            for i in range(method_start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                    found_opening = True
                elif content[i] == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        method_end = i
                        break
            
            if method_end > method_start:
                method_body = content[method_start:method_end]
                
                # Check for cooldown application in command method
                has_cooldown_call = any([
                    'ApplyCooldown' in method_body,
                    'LinkCooldowns' in method_body,
                    'SetCooldown' in method_body,
                    '.Cooldown' in method_body
                ])
                
                # Check for energy cost
                has_energy_cost = any([
                    'UseEnergy' in method_body,
                    'SubtractEnergy' in method_body,
                    'ChargeUse' in method_body,
                    'Energy' in method_body and '-=' in method_body
                ])
                
                line_num = content[:match.start()].count('\n') + 1
                
                if not has_cooldown_call:
                    issues.append({
                        'file': str(mod_file.path),
                        'type': 'command_method_no_cooldown',
                        'method_name': method_name,
                        'line': line_num,
                        'severity': 'medium',
                        'description': f'Command method "{method_name}" may lack cooldown management'
                    })
        
        # Pattern 3: Check for ActivatedAbilityID without RemoveMyActivatedAbility
        ability_id_pattern = r'private\s+(?:readonly\s+)?Guid\s+(\w*Ability(?:ID)?)\s*='
        remove_pattern = r'RemoveMyActivatedAbility\s*\(\s*ref\s+(\w+)'
        
        ability_ids = set(match.group(1) for match in re.finditer(ability_id_pattern, content))
        removed_ids = set(match.group(1) for match in re.finditer(remove_pattern, content))
        
        unremoved_ids = ability_ids - removed_ids
        if unremoved_ids and 'Unmutate' in content:
            for ability_id in unremoved_ids:
                # Check if there's an Unmutate method
                if re.search(r'public\s+override\s+bool\s+Unmutate\s*\(', content):
                    line_match = re.search(rf'(\w+\s+)?Guid\s+{re.escape(ability_id)}', content)
                    line_num = content[:line_match.start()].count('\n') + 1 if line_match else 0
                    
                    issues.append({
                        'file': str(mod_file.path),
                        'type': 'ability_not_removed_on_unmutate',
                        'ability_id': ability_id,
                        'line': line_num,
                        'severity': 'medium',
                        'description': f'Ability ID "{ability_id}" is never removed in Unmutate(), causing ability to persist'
                    })
        
        return issues


class NaturalLanguageIssueClassifier:
    """Classifies natural language issue descriptions into actionable fix types."""
    
    ISSUE_PATTERNS = {
        'cooldown': {
            'keywords': ['cooldown', 'spam', 'infinite use', 'no delay', 'use repeatedly', 'constant use'],
            'severity': 'high',
            'category': 'activated_ability_no_cooldown'
        },
        'crash': {
            'keywords': ['crash', 'null reference', 'nullreferenceexception', 'exception', 'error', 'breaks'],
            'severity': 'critical',
            'category': 'null_check_missing'
        },
        'placement_failure': {
            'keywords': ['not spawning', 'doesn\'t appear', 'not showing', 'invisible', 'not placed', 'doesn\'t create'],
            'severity': 'high',
            'category': 'object_placement_issue'
        },
        'persistence': {
            'keywords': ['stays after', 'doesn\'t remove', 'persists', 'won\'t go away', 'stuck'],
            'severity': 'medium',
            'category': 'cleanup_missing'
        },
        'energy_cost': {
            'keywords': ['energy', 'too cheap', 'free', 'no cost', 'mana'],
            'severity': 'medium',
            'category': 'energy_cost_missing'
        },
        'api_broken': {
            'keywords': ['doesn\'t work', 'api', 'method not found', 'class not found', 'outdated'],
            'severity': 'high',
            'category': 'api_compatibility'
        },
        'takeable': {
            'keywords': ['can\'t add to inventory', 'untakeable', 'inventory error', 'can\'t pick up'],
            'severity': 'medium',
            'category': 'takeable_flag_issue'
        },
        'message_no_object': {
            'keywords': ['message but no', 'shows message', 'says created but', 'announces but'],
            'severity': 'high',
            'category': 'object_creation_validation'
        }
    }
    
    @staticmethod
    def classify_issue(description: str) -> Dict[str, Any]:
        """Classify a natural language issue description."""
        description_lower = description.lower()
        
        matched_patterns = []
        for pattern_name, pattern_data in NaturalLanguageIssueClassifier.ISSUE_PATTERNS.items():
            score = 0
            for keyword in pattern_data['keywords']:
                if keyword in description_lower:
                    score += 1
            
            if score > 0:
                matched_patterns.append({
                    'name': pattern_name,
                    'score': score,
                    'severity': pattern_data['severity'],
                    'category': pattern_data['category'],
                    'keywords_matched': [kw for kw in pattern_data['keywords'] if kw in description_lower]
                })
        
        # Sort by score (highest first)
        matched_patterns.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'description': description,
            'matched_patterns': matched_patterns,
            'primary_category': matched_patterns[0]['category'] if matched_patterns else 'general',
            'severity': matched_patterns[0]['severity'] if matched_patterns else 'medium',
            'confidence': matched_patterns[0]['score'] if matched_patterns else 0
        }


class MutationArchitectureAnalyzer:
    """Analyzes mutation architecture from source code to understand correct patterns."""
    
    def __init__(self, rag_system: Optional[Any] = None):
        self.rag_system = rag_system
        self.mutation_patterns = {}
    
    def analyze_mutation_architecture(self, mod_file: ModFile) -> Dict[str, Any]:
        """Analyze a mutation file and retrieve correct patterns from source."""
        
        analysis = {
            'is_mutation': False,
            'base_class': None,
            'abilities': [],
            'lifecycle_methods': [],
            'cooldown_patterns': [],
            'source_examples': [],
            'issues': []
        }
        
        content = mod_file.content
        
        # Detect if this is a mutation
        if 'BaseMutation' in content or ': Mutation' in content:
            analysis['is_mutation'] = True
        
        # Extract base class
        base_match = re.search(r'class\s+\w+\s*:\s*(\w+)', content)
        if base_match:
            analysis['base_class'] = base_match.group(1)
        
        # Find activated abilities
        ability_pattern = r'(\w+)\s*=\s*AddMyActivatedAbility\s*\([^)]*["\']([^"\']+)["\']'
        for match in re.finditer(ability_pattern, content):
            analysis['abilities'].append({
                'var': match.group(1),
                'name': match.group(2),
                'has_cooldown': False,
                'cooldown_method': None
            })
        
        # Check lifecycle methods
        if 'override bool Mutate' in content:
            analysis['lifecycle_methods'].append('Mutate')
        if 'override bool Unmutate' in content:
            analysis['lifecycle_methods'].append('Unmutate')
        
        # Retrieve correct mutation patterns from source if RAG available
        if self.rag_system and analysis['is_mutation']:
            try:
                # Query for mutation examples with activated abilities
                query = "BaseMutation AddMyActivatedAbility ApplyCooldown Mutate Unmutate"
                retrieved = self.rag_system.retrieve(query, top_k=5)
                
                if retrieved and retrieved.chunks:
                    for chunk in retrieved.chunks:
                        # Extract cooldown patterns from source examples
                        chunk_content = chunk.content
                        
                        # Find cooldown application patterns
                        cooldown_matches = re.finditer(
                            r'(ApplyCooldown|LinkCooldowns)\s*\([^)]+\)',
                            chunk_content
                        )
                        for match in cooldown_matches:
                            pattern = match.group(0)
                            if pattern not in analysis['cooldown_patterns']:
                                analysis['cooldown_patterns'].append(pattern)
                        
                        # Store example for reference
                        analysis['source_examples'].append({
                            'file': chunk.metadata.get('file', 'unknown'),
                            'similarity': chunk.score,
                            'snippet': chunk_content[:500]
                        })
                
            except Exception as e:
                print(f"      [Mutation Analysis] RAG retrieval failed: {e}")
        
        # Analyze issues based on architecture
        analysis['issues'].extend(self._detect_architecture_issues(content, analysis))
        
        return analysis
    
    def _detect_architecture_issues(self, content: str, arch_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect issues by comparing to correct mutation architecture."""
        issues = []
        
        # Check each ability has cooldown
        for ability in arch_analysis['abilities']:
            ability_var = ability['var']
            
            # Check if cooldown is applied
            cooldown_patterns = [
                rf'ApplyCooldown\s*\([^,]*,\s*{re.escape(ability_var)}',
                rf'LinkCooldowns\s*\([^,]*,\s*{re.escape(ability_var)}',
                rf'{re.escape(ability_var)}[^;]*Cooldown\s*='
            ]
            
            has_cooldown = any(re.search(pattern, content, re.IGNORECASE) for pattern in cooldown_patterns)
            ability['has_cooldown'] = has_cooldown
            
            if not has_cooldown:
                issues.append({
                    'type': 'mutation_ability_no_cooldown',
                    'severity': 'critical',
                    'ability': ability['name'],
                    'ability_var': ability_var,
                    'fix_pattern': arch_analysis['cooldown_patterns'][0] if arch_analysis['cooldown_patterns'] else None
                })
        
        # Check lifecycle completeness
        if 'Mutate' in arch_analysis['lifecycle_methods']:
            if 'Unmutate' not in arch_analysis['lifecycle_methods']:
                issues.append({
                    'type': 'mutation_missing_unmutate',
                    'severity': 'high',
                    'message': 'Mutate() exists but Unmutate() is missing - abilities will persist'
                })
        
        # Check if abilities are removed in Unmutate
        if arch_analysis['abilities'] and 'Unmutate' in arch_analysis['lifecycle_methods']:
            for ability in arch_analysis['abilities']:
                ability_var = ability['var']
                remove_pattern = rf'RemoveMyActivatedAbility\s*\(\s*ref\s+{re.escape(ability_var)}'
                if not re.search(remove_pattern, content):
                    issues.append({
                        'type': 'mutation_ability_not_removed',
                        'severity': 'high',
                        'ability': ability['name'],
                        'ability_var': ability_var
                    })
        
        return issues
    
    def simulate_mutation_lifecycle(self, mod_file: ModFile, arch_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate mutation lifecycle to predict runtime behavior."""
        
        simulation = {
            'can_mutate': False,
            'can_unmutate': False,
            'abilities_added': [],
            'abilities_removed': [],
            'cooldowns_applied': [],
            'issues': []
        }
        
        content = mod_file.content
        
        # Simulate Mutate()
        if 'Mutate' in arch_analysis['lifecycle_methods']:
            simulation['can_mutate'] = True
            
            # Check what happens in Mutate
            for ability in arch_analysis['abilities']:
                if 'AddMyActivatedAbility' in content:
                    simulation['abilities_added'].append(ability['name'])
                    
                    # Check if cooldown is set up
                    if not ability['has_cooldown']:
                        simulation['issues'].append({
                            'phase': 'runtime',
                            'issue': f"Ability '{ability['name']}' can be spammed infinitely (no cooldown)",
                            'impact': 'game_breaking'
                        })
        
        # Simulate Unmutate()
        if 'Unmutate' in arch_analysis['lifecycle_methods']:
            simulation['can_unmutate'] = True
            
            # Check what gets cleaned up
            for ability in arch_analysis['abilities']:
                ability_var = ability['var']
                if re.search(rf'RemoveMyActivatedAbility.*{re.escape(ability_var)}', content):
                    simulation['abilities_removed'].append(ability['name'])
                else:
                    simulation['issues'].append({
                        'phase': 'cleanup',
                        'issue': f"Ability '{ability['name']}' persists after mutation removed",
                        'impact': 'ui_clutter_and_bugs'
                    })
        
        return simulation


class NaturalLanguageFixer:
    """Handles natural language issue descriptions and generates targeted fixes."""
    
    def __init__(self, mod_fixer: 'ModFixer'):
        self.mod_fixer = mod_fixer
        self.classifier = NaturalLanguageIssueClassifier()
        self.mutation_analyzer = MutationArchitectureAnalyzer(
            mod_fixer.rag_system if hasattr(mod_fixer, 'rag_system') else None
        )
    
    def fix_from_description(
        self,
        mod_path: Path,
        issue_description: str,
        target_file: Optional[str] = None,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """Fix issues based on natural language description."""
        
        print_section_header("NATURAL LANGUAGE ISSUE FIXING", Colors.CYAN)
        print()
        print(f"  Mod: {mod_path.name}")
        print(f"  Issue: {issue_description}")
        if target_file:
            print(f"  Target: {target_file}")
        print()
        
        # Classify the issue
        classification = self.classifier.classify_issue(issue_description)
        
        print_status("Issue Classification", "PROCESSING")
        print(f"    Primary Category: {classification['primary_category']}")
        print(f"    Severity: {classification['severity'].upper()}")
        print(f"    Confidence: {classification['confidence']}/5")
        
        if classification['matched_patterns']:
            print(f"    Matched Keywords: {', '.join(classification['matched_patterns'][0]['keywords_matched'])}")
        print()
        
        # Analyze mod to get file context
        analysis = self.mod_fixer.analyzer.analyze_mod(mod_path)
        
        # Find relevant files
        target_files = []
        if target_file:
            # Specific file provided
            target_files = [f for f in analysis.files if target_file in str(f.path)]
        else:
            # Use all C# files
            target_files = analysis.files
        
        if not target_files:
            print_status("No matching files found", "ERROR")
            return {
                'success': False,
                'error': 'No matching files found',
                'classification': classification
            }
        
        # Build specialized prompt based on classification
        prompt = self._build_natural_language_prompt(
            issue_description,
            classification,
            target_files,
            analysis
        )
        
        # Apply fixes
        results = []
        for file_obj in target_files:
            if create_backup:
                self.mod_fixer._create_file_backup(file_obj.path)
            
            print_status(f"Fixing {file_obj.path.name}", "PROCESSING")
            
            fixed_content = self.mod_fixer._get_ai_fix(
                file_obj.content,
                prompt,
                task_type="code"
            )
            
            if fixed_content and fixed_content != file_obj.content:
                # Apply the fix
                result = self.mod_fixer._apply_fix(
                    str(file_obj.path),
                    file_obj.content,
                    fixed_content
                )
                results.append(result)
                
                if result.success:
                    print_status(f"Fixed {file_obj.path.name}", "SUCCESS")
                else:
                    print_status(f"Failed to fix {file_obj.path.name}", "ERROR")
            else:
                print_status(f"No changes needed for {file_obj.path.name}", "INFO")
        
        return {
            'success': len([r for r in results if r.success]) > 0,
            'results': results,
            'classification': classification,
            'files_processed': len(target_files)
        }
    
    def _build_natural_language_prompt(
        self,
        issue_description: str,
        classification: Dict[str, Any],
        target_files: List[ModFile],
        analysis: ModAnalysis
    ) -> str:
        """Build a specialized prompt based on natural language description."""
        
        category = classification['primary_category']
        
        # Analyze mutation architecture if this is a mutation mod
        mutation_analysis = None
        mutation_simulation = None
        source_examples = []
        
        for file_obj in target_files:
            if 'BaseMutation' in file_obj.content or 'Mutation' in file_obj.content:
                mutation_analysis = self.mutation_analyzer.analyze_mutation_architecture(file_obj)
                if mutation_analysis['is_mutation']:
                    mutation_simulation = self.mutation_analyzer.simulate_mutation_lifecycle(
                        file_obj, mutation_analysis
                    )
                    source_examples = mutation_analysis.get('source_examples', [])
                    break
        
        # Build category-specific guidance
        guidance = self._get_category_guidance(category, issue_description)
        
        # Include error logs if available
        error_log_context = ""
        if self.mod_fixer.error_logs_cache:
            error_log_context = format_error_logs_for_context(self.mod_fixer.error_logs_cache, max_lines=20)
        
        # Build the prompt
        prompt = f"""# ISSUE FIXING REQUEST

## User Description
{issue_description}

## Issue Classification
- Category: {category}
- Severity: {classification['severity'].upper()}
- Confidence: {classification['confidence']}/5

"""
        
        # Add mutation architecture analysis if available
        if mutation_analysis and mutation_analysis['is_mutation']:
            prompt += f"""
## MUTATION ARCHITECTURE ANALYSIS

Base Class: {mutation_analysis['base_class']}
Lifecycle Methods: {', '.join(mutation_analysis['lifecycle_methods'])}

Detected Abilities:
"""
            for ability in mutation_analysis['abilities']:
                cooldown_status = "✓ Has cooldown" if ability['has_cooldown'] else "✗ MISSING COOLDOWN"
                prompt += f"  - {ability['name']} ({ability['var']}) - {cooldown_status}\n"
            
            # Add simulation results
            if mutation_simulation:
                prompt += f"""
## MUTATION LIFECYCLE SIMULATION

Runtime Behavior Prediction:
"""
                if mutation_simulation['abilities_added']:
                    prompt += f"  Abilities Added: {', '.join(mutation_simulation['abilities_added'])}\n"
                if mutation_simulation['abilities_removed']:
                    prompt += f"  Abilities Removed: {', '.join(mutation_simulation['abilities_removed'])}\n"
                
                if mutation_simulation['issues']:
                    prompt += f"\nPredicted Runtime Issues:\n"
                    for issue in mutation_simulation['issues']:
                        prompt += f"  [{'GAME-BREAKING' if issue['impact'] == 'game_breaking' else 'BUG'}] {issue['issue']}\n"
            
            # Add correct patterns from source code
            if source_examples:
                prompt += f"""
## CORRECT PATTERNS FROM GAME SOURCE CODE

Retrieved {len(source_examples)} similar mutations from source:
"""
                for idx, example in enumerate(source_examples[:2], 1):
                    prompt += f"""
### Example {idx} ({example['file']}) - Similarity: {example['similarity']:.2f}
```csharp
{example['snippet']}
```
"""
            
            if mutation_analysis['cooldown_patterns']:
                prompt += f"""
## CORRECT COOLDOWN PATTERNS (from source)
"""
                for pattern in mutation_analysis['cooldown_patterns'][:3]:
                    prompt += f"  {pattern}\n"
        
        prompt += f"\n{guidance}\n"
        
        prompt += """
## File Context
Files to fix:
"""
        
        for file_obj in target_files[:3]:  # Limit to 3 files for context
            prompt += f"\n### {file_obj.path.name}\n"
            prompt += f"```csharp\n{file_obj.content[:3000]}\n```\n"
            if len(file_obj.content) > 3000:
                prompt += f"\n... ({len(file_obj.content) - 3000} more characters)\n"
        
        if error_log_context:
            prompt += f"\n## Relevant Error Logs\n{error_log_context}\n"
        
        prompt += """

## Instructions
1. Study the mutation architecture analysis and source code examples
2. Understand how the game's mutation system actually works
3. Simulate the mutation lifecycle to predict behavior
4. Apply fixes that match the architectural patterns from source
5. Ensure cooldowns, lifecycle methods, and cleanup follow game conventions
6. Output ONLY the complete fixed code, no explanations

"""
        
        return prompt
    
    def _get_category_guidance(self, category: str, issue_description: str) -> str:
        """Get category-specific fixing guidance."""
        
        guidance_map = {
            'activated_ability_no_cooldown': """
## Fix Guidance: Missing Cooldown (FROM GAME SOURCE CODE)

PROBLEM: The ability can be used repeatedly without delay, breaking game balance.

SOLUTION PATTERN (from BaseMutation.cs and SpacetimeVortex.cs):
1. Add cooldown call after successful ability use in the command handler:
   ```csharp
   this.CooldownMyActivatedAbility(this.ActivatedAbilityID, cooldownTurns);
   ```

2. Example from SpacetimeVortex.cs (line 115):
   ```csharp
   this.CooldownMyActivatedAbility(this.ActivatedAbilityID, Math.Max(550 - 50 * this.Level, 5));
   ```

3. Also add energy cost (from SpacetimeVortex.cs line 114):
   ```csharp
   this.UseEnergy(1000, "Mental Mutation SpaceTimeVortex");
   ```

4. Place cooldown and energy calls AFTER ability succeeds but BEFORE return true

CRITICAL: 
- Use `this.CooldownMyActivatedAbility(this.ActivatedAbilityID, turns)` NOT `ApplyCooldown`
- Cooldown must be applied on EVERY successful use path
- Energy cost should also be applied (typically 1000 for mental mutations)
""",
            
            'null_check_missing': """
## Fix Guidance: Null Reference Protection

PROBLEM: Code crashes when objects are null or don't exist.

SOLUTION PATTERN:
1. Add null checks before accessing objects:
   ```csharp
   if (obj == null) return false;
   if (cell == null) { /* log error */ return; }
   ```

2. Use null-conditional operators:
   ```csharp
   cell?.AddObject(obj);
   var zone = cell?.ParentZone;
   ```

3. Validate GameObject creation:
   ```csharp
   GameObject newObj = GameObject.Create("Blueprint");
   if (newObj == null) {
       // Handle creation failure
       return false;
   }
   ```

4. Check references after delays (scheduled callbacks):
   - Cell references can become stale
   - Re-get cells from zone coordinates
   - Validate before use

CRITICAL: Add null checks at ALL access points, especially after delays!
""",
            
            'object_placement_issue': """
## Fix Guidance: Object Not Appearing

PROBLEM: Objects are created but don't appear in the game world.

COMMON CAUSES:
1. Cell reference is null
2. Object not added to cell (missing AddObject call)
3. Cell reference became stale (after delay/callback)
4. Object created but not placed

SOLUTION PATTERN:
1. Validate cell before placement:
   ```csharp
   Cell targetCell = GetPlacementCell();
   if (targetCell == null) {
       // Log error, notify user
       return false;
   }
   ```

2. Ensure AddObject is called:
   ```csharp
   GameObject obj = GameObject.Create("Blueprint");
   if (obj != null && targetCell != null) {
       targetCell.AddObject(obj);
   } else {
       // Handle failure - show message
   }
   ```

3. For delayed placement (scheduled callbacks):
   - Store zone and coordinates (not cell reference)
   - Re-get cell from coordinates after delay
   - Validate cell exists before placing

4. Add user feedback:
   ```csharp
   if (placement_failed) {
       MessageQueue.AddPlayerMessage("{{R|Failed to create object!}}");
   }
   ```

CRITICAL: Always validate placement succeeded and provide feedback!
""",
            
            'cleanup_missing': """
## Fix Guidance: Objects Persist After Removal

PROBLEM: Objects/abilities remain after they should be removed.

SOLUTION PATTERN:
1. Remove abilities in Unmutate():
   ```csharp
   public override bool Unmutate(GameObject GO)
   {
       RemoveMyActivatedAbility(ref AbilityID);
       // Clean up other resources
       return base.Unmutate(GO);
   }
   ```

2. Destroy created objects:
   ```csharp
   if (createdObject != null && !createdObject.IsInvalid()) {
       createdObject.Destroy();
   }
   ```

3. Clear tracked lists:
   ```csharp
   trackedObjects.Clear();
   activeEffects.Clear();
   ```

CRITICAL: Clean up ALL resources in reverse order of creation!
""",
            
            'takeable_flag_issue': """
## Fix Guidance: Inventory/Takeable Issues

PROBLEM: Object can't be added to inventory despite "Takeable" appearance.

SOLUTION:
1. Check Physics part Takeable flag:
   ```xml
   <part Name="Physics" Takeable="true" />
   ```

2. For permanent equipment, use protection tags instead:
   ```xml
   <part Name="Physics" Takeable="true" />
   <tag Name="CannotDrop" />
   <tag Name="CannotRemove" />
   ```

3. Verify no conflicting tags:
   - Remove "CantPickUp" property
   - Check for "NoTake" tags

CRITICAL: Takeable="false" prevents AddObject to inventory!
""",
            
            'object_creation_validation': """
## Fix Guidance: Messages Without Objects

PROBLEM: Success messages shown but objects don't actually appear.

SOLUTION:
1. Show message ONLY after successful placement:
   ```csharp
   GameObject obj = GameObject.Create("Blueprint");
   if (obj != null) {
       Cell target = GetTargetCell();
       if (target != null) {
           target.AddObject(obj);
           // ONLY NOW show success message
           MessageQueue.AddPlayerMessage("Success!");
       } else {
           MessageQueue.AddPlayerMessage("{{R|No room!}}");
       }
   } else {
       MessageQueue.AddPlayerMessage("{{R|Creation failed!}}");
   }
   ```

2. Wrap placement in try-catch with error messages:
   ```csharp
   try {
       targetCell.AddObject(obj);
       ShowSuccessMessage();
   } catch (Exception ex) {
       LogError(ex);
       ShowErrorMessage();
   }
   ```

CRITICAL: Validate success before showing positive feedback!
"""
        }
        
        return guidance_map.get(category, f"""
## Fix Guidance: {category.replace('_', ' ').title()}

{issue_description}

SOLUTION:
Analyze the code and user description to identify the root cause.
Apply appropriate fixes following Caves of Qud modding best practices.
""")


class ModFixer:
    """Main mod fixing class using AI code models (StarCoder 7B or Code Llama 7B preferred)."""
    
    # Thread lock for file writes (shared across all instances)
    _file_write_lock = threading.Lock()
    
    def __init__(
        self,
        source_path: Path = QUD_SOURCE_PATH,
        streaming_assets_path: Path = QUD_STREAMING_ASSETS,
        mods_path: Path = QUD_MODS_PATH,
        workshop_path: Optional[Path] = None,
        ollama_url: str = "http://localhost:11434",
        use_rag: bool = True,
        rag_index_path: Optional[Path] = None,
        preferred_model: Optional[str] = None,
        error_log_paths: Optional[List[Path]] = None,
        save_path: Optional[Path] = None
    ):
        self.source_path = source_path
        self.streaming_assets_path = streaming_assets_path
        self.mods_path = mods_path
        self.workshop_path = workshop_path or QUD_WORKSHOP_PATH
        self.ollama_url = ollama_url
        self.use_rag = use_rag and RAG_AVAILABLE
        self.preferred_model = preferred_model
        self.error_log_paths = error_log_paths
        self.save_path = save_path or QUD_SAVE_PATH
        self.error_logs_cache: Dict[str, List[str]] = {}
        
        self.cpu_manager = CPUManager()
        self.source_index = SourceCodeIndex(source_path)
        
        # Load error logs if available
        if self.error_log_paths or self.save_path:
            self._load_error_logs()
        self.asset_checker = AssetReferenceChecker(
            streaming_assets_path,
            mods_path=mods_path,
            workshop_path=self.workshop_path
        )
        self.analyzer = ModAnalyzer(self.source_index, self.asset_checker)
        
        # Initialize Unity asset generator if available
        self.unity_generator = None
        if UNITY_ASSET_GENERATOR_AVAILABLE:
            self.unity_generator = UnityAssetGenerator  # Store class, will instantiate per mod
        
        # Initialize model router if available (uses existing Common/ollama_model_router.py)
        self.router = None
        if MULTIMODEL_ROUTER_AVAILABLE and OLLAMA_AVAILABLE:
            try:
                # Determine shared index path (for multi-instance coordination)
                shared_index_path = None
                if rag_index_path:
                    shared_index_path = rag_index_path
                elif self.use_rag:
                    # Default shared index path
                    shared_index_path = self.mods_path.parent / "rag_index" / "qud_source_index.faiss"
                
                self.router = OllamaModelRouter(
                    use_verification=True,
                    enable_model_unloading=True,  # Unload unused models to save resources
                    shared_index_path=shared_index_path  # Share index across instances
                )
                print(f"  Model router initialized (verification enabled, model unloading enabled)")
                if self.router.code_model:
                    print(f"    Code model: {self.router.code_model}")
                if self.router.reasoning_model:
                    print(f"    Reasoning model: {self.router.reasoning_model}")
                if self.router.generation_model:
                    print(f"    Generation model: {self.router.generation_model}")
                if shared_index_path:
                    print(f"    Shared index: {shared_index_path}")
                    print(f"    Multi-instance coordination: Enabled")
            except Exception as e:
                print(f"  Warning: Model router initialization failed: {e}")
                self.router = None
        
        # Initialize RAG system if available
        self.rag_system = None
        if self.use_rag:
            try:
                if rag_index_path is None:
                    # Default index path in mods directory
                    rag_index_path = self.mods_path.parent / "rag_index"
                    rag_index_path.mkdir(exist_ok=True)
                    rag_index_path = rag_index_path / "qud_source_index.faiss"
                
                print(f"  Initializing RAG system...")
                print(f"    Source: {source_path}")
                
                # Check if Unity audio module exists and should be included
                unity_audio_path = source_path.parent / "UnityEngine.AudioModule"
                if unity_audio_path.exists():
                    print(f"    Unity Audio Module: {unity_audio_path} (will be indexed for audio-based mods)")
                
                print(f"    Index: {rag_index_path}")
                self.rag_system = RAGSystem(
                    source_path=source_path,
                    index_path=rag_index_path,
                    embedding_model="all-MiniLM-L6-v2",  # Small, fast, CPU-friendly
                    use_faiss=True,
                    device="cpu"  # Use CPU for air-gapped/low-VRAM
                )
                
                # Check if index exists and if it needs to be rebuilt
                needs_rebuild = False
                if not rag_index_path.exists():
                    needs_rebuild = True
                    print(f"    Index not found, building...")
                else:
                    # Check if source files are newer than the index
                    try:
                        index_mtime = rag_index_path.stat().st_mtime
                        source_mtime = self._get_newest_source_file_mtime(source_path)
                        
                        if source_mtime and source_mtime > index_mtime:
                            needs_rebuild = True
                            print(f"    Source files are newer than index, rebuilding...")
                        else:
                            print(f"    [OK] Using existing index (source unchanged)")
                    except (OSError, AttributeError) as e:
                        # If we can't check timestamps, assume rebuild needed for safety
                        print(f"    Warning: Could not check timestamps ({e}), rebuilding index...")
                        needs_rebuild = True
                
                if needs_rebuild:
                    print(f"    This may take a while (runs locally, no network calls)")
                    # Try to build index, but don't fail if lock can't be acquired
                    try:
                        # Index main source code
                        self.rag_system.index_source_code(file_patterns=['*.cs'])
                        
                        # Also index Unity audio module if it exists (for audio-based mods)
                        unity_audio_path = source_path.parent / "UnityEngine.AudioModule"
                        if unity_audio_path.exists():
                            print(f"    Also indexing Unity Audio Module for audio-based mods...")
                            try:
                                # Manually index Unity audio files since RAG system uses single source_path
                                unity_cs_files = list(unity_audio_path.rglob("*.cs"))
                                if unity_cs_files:
                                    print(f"    Found {len(unity_cs_files)} Unity Audio Module files")
                                    # Add Unity audio files to the index manually
                                    from Shared.rag_system import CodeChunker
                                    chunker = CodeChunker()
                                    unity_chunks = []
                                    for file_path in unity_cs_files:
                                        try:
                                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                                content = f.read()
                                            chunks = chunker.chunk_file(file_path, content)
                                            unity_chunks.extend(chunks)
                                        except Exception as e:
                                            print(f"    Warning: Failed to index {file_path.name}: {e}")
                                    
                                    if unity_chunks:
                                        print(f"    Adding {len(unity_chunks)} Unity Audio chunks to index...")
                                        # Get embeddings and add to vector store in batches
                                        batch_size = 32
                                        for i in range(0, len(unity_chunks), batch_size):
                                            batch = unity_chunks[i:i + batch_size]
                                            batch_texts = [chunk.content for chunk in batch]
                                            batch_embeddings = self.rag_system.embedder.embed(batch_texts)
                                            self.rag_system.vector_store.add_chunks(batch, batch_embeddings)
                                        
                                        # Save the updated index
                                        if self.rag_system.index_path:
                                            self.rag_system.vector_store.save()
                                        
                                        print(f"    [OK] Unity Audio Module indexed ({len(unity_chunks)} chunks)")
                            except Exception as e:
                                print(f"    Warning: Could not index Unity Audio Module: {e}")
                                # Continue without Unity audio - not critical
                        print(f"    [OK] Index built successfully")
                    except Exception as build_error:
                        if "lock" in str(build_error).lower() or "Lock" in str(build_error):
                            print(f"    Warning: RAG index is locked by another instance")
                            print(f"    Continuing without RAG (will use basic prompts)")
                            print(f"    You can try again later when the other instance finishes")
                        else:
                            print(f"    Warning: Could not build index: {build_error}")
                            print(f"    Continuing without RAG (will use basic prompts)")
                        self.rag_system = None
                        self.use_rag = False
                else:
                    # Try to load index, but continue even if lock fails
                    try:
                        self.rag_system.vector_store.load()
                        self.rag_system.indexed = True
                    except Exception as load_error:
                        if "lock" in str(load_error).lower() or "Lock" in str(load_error):
                            print(f"    Warning: RAG index is locked by another instance")
                            print(f"    Continuing without RAG (will use basic prompts)")
                            print(f"    You can try again later when the other instance finishes")
                        else:
                            print(f"    Warning: Could not load index: {load_error}")
                            print(f"    Continuing without RAG (will use basic prompts)")
                        self.rag_system = None
                        self.use_rag = False
                
            except Exception as e:
                print(f"    Warning: RAG system initialization failed: {e}")
                if "lock" in str(e).lower() or "Lock" in str(e):
                    print(f"    RAG index appears to be locked by another instance")
                    print(f"    Continuing without RAG (will use basic prompts)")
                else:
                    print(f"    Continuing without RAG (will use basic prompts)")
                self.rag_system = None
                self.use_rag = False
        
        # Configure Ollama for code models (StarCoder 7B or Code Llama 7B preferred)
        if OLLAMA_AVAILABLE:
            # Use optimal thread count (leaves 6% of cores free)
            optimal_threads = self.cpu_manager.get_optimal_threads()
            cores_left_free = self.cpu_manager.cpu_count - optimal_threads
            print(f"  Using {optimal_threads} threads (of {self.cpu_manager.cpu_count} cores, leaving {cores_left_free} cores free ~{cores_left_free/self.cpu_manager.cpu_count*100:.1f}%)")
    
    def _get_newest_source_file_mtime(self, source_path: Path) -> Optional[float]:
        """Get the modification time of the newest source file (including Unity audio module)."""
        if not source_path.exists():
            return None
        
        newest_mtime = 0.0
        try:
            # Check all .cs files recursively in main source
            for cs_file in source_path.rglob("*.cs"):
                try:
                    mtime = cs_file.stat().st_mtime
                    if mtime > newest_mtime:
                        newest_mtime = mtime
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
            
            # Also check Unity audio module if it exists
            unity_audio_path = source_path.parent / "UnityEngine.AudioModule"
            if unity_audio_path.exists():
                for cs_file in unity_audio_path.rglob("*.cs"):
                    try:
                        mtime = cs_file.stat().st_mtime
                        if mtime > newest_mtime:
                            newest_mtime = mtime
                    except (OSError, PermissionError):
                        continue
        except Exception:
            # If we can't traverse, return None to trigger rebuild
            return None
        
        return newest_mtime if newest_mtime > 0 else None
    
    def fix_mod(self, mod_path: Path, create_backup: bool = True) -> List[FixResult]:
        """Fix issues in a mod."""
        print_section_header(f"FIXING MOD: {mod_path.name}", Colors.YELLOW)
        
        # Create backup
        if create_backup:
            backup_path = mod_path.parent / f"{mod_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print_status(f"Creating backup: {backup_path}", "PROCESSING")
            shutil.copytree(mod_path, backup_path)
            print_status(f"Backup created: {backup_path}", "SUCCESS")
        
        # Analyze mod
        analysis = self.analyzer.analyze_mod(mod_path)
        
        if len(analysis.api_issues) > 0:
            print_status(f"Found {len(analysis.api_issues)} API issues", "WARNING")
        if len(analysis.asset_issues) > 0:
            print_status(f"Found {len(analysis.asset_issues)} asset issues", "WARNING")
        if len(analysis.harmony_patches) > 0:
            print_status(f"Found {len(analysis.harmony_patches)} Harmony patches", "INFO")
        
        # Check and create Unity assets if needed
        if UNITY_ASSET_GENERATOR_AVAILABLE and self.unity_generator:
            print(f"\n  Checking Unity assets...")
            try:
                unity_gen = self.unity_generator(mod_path)
                unity_results = unity_gen.check_and_fix_assets()
                
                if unity_results['meta_files_created'] > 0:
                    print(f"    [Unity] Created {unity_results['meta_files_created']} .meta files")
                if unity_results['springui_assets_created'] > 0:
                    print(f"    [Unity] Created {unity_results['springui_assets_created']} SpringUI assets")
                if unity_results['project_structure_created']:
                    print(f"    [Unity] Created Unity project structure")
                
                if (unity_results['meta_files_created'] == 0 and 
                    unity_results['springui_assets_created'] == 0 and 
                    not unity_results['project_structure_created']):
                    print(f"    [Unity] No Unity assets needed")
            except Exception as e:
                print(f"    [Unity] Warning: Unity asset generation failed: {e}")

        # Bridge Textures/ → Assets/Resources + .meta (Shared unity_meta; no Editor required)
        try:
            from export_textures_to_unity import export_textures
            textures_dir = Path(mod_path) / "Textures"
            if textures_dir.is_dir() and any(textures_dir.rglob("*.png")):
                print(f"\n  Bridging Textures/ into Assets/Resources...")
                n = export_textures(Path(mod_path), overwrite_meta=False)
                if n:
                    print(f"    [Unity] Exported {n} textures with .meta")
        except Exception as e:
            print(f"    [Unity] Texture bridge skipped: {e}")
        
        # Generate mutation/creature/equipment visual assets
        print(f"\n  Generating visual assets...")
        try:
            from mutation_asset_generator import MutationAssetGenerator
            from creature_asset_generator import CreatureAssetGenerator
            from equipment_asset_generator import EquipmentAssetGenerator
            
            # Mutation assets
            mutation_gen = MutationAssetGenerator(mod_path)
            mutation_results = mutation_gen.generate_all_mutation_assets()
            if mutation_results['icons_created'] > 0 or mutation_results['visuals_created'] > 0:
                print(f"    [Mutation Assets] Created {mutation_results['icons_created']} icons, {mutation_results['visuals_created']} visuals")
            
            # Creature assets
            creature_gen = CreatureAssetGenerator(mod_path)
            creature_results = creature_gen.generate_all_creature_assets()
            if creature_results['tiles_created'] > 0:
                print(f"    [Creature Assets] Created {creature_results['tiles_created']} creature tiles")
            
            # Equipment assets
            equipment_gen = EquipmentAssetGenerator(mod_path)
            equipment_results = equipment_gen.generate_all_equipment_assets()
            if equipment_results['tiles_created'] > 0 or equipment_results['icons_created'] > 0:
                print(f"    [Equipment Assets] Created {equipment_results['tiles_created']} tiles, {equipment_results['icons_created']} icons")
        except ImportError as e:
            print(f"    [Visual Assets] Warning: Asset generators not available: {e}")
            print(f"    [Visual Assets] Install Pillow: pip install Pillow")
        except Exception as e:
            print(f"    [Visual Assets] Warning: Asset generation failed: {e}")
        
        # Fix issues
        results = []
        
        # Fix asset references
        if analysis.asset_issues:
            print()
            print_status(f"FIXING ASSET REFERENCES", "PROCESSING")
            print("  Why: Asset paths may be broken or point to non-existent files", Colors.GRAY)
            print("  How: Using AI to locate correct asset paths in StreamingAssets", Colors.GRAY)
            print()
            asset_results = self._fix_asset_references(analysis)
            results.extend(asset_results)
        
        # Fix API issues
        if analysis.api_issues:
            print()
            print_status(f"FIXING API ISSUES", "PROCESSING")
            print("  Why: API calls may be outdated or incompatible with current game version", Colors.GRAY)
            print("  How: Using AI to update API calls to match decompiled source code", Colors.GRAY)
            print()
            api_results = self._fix_api_issues(analysis)
            results.extend(api_results)
        
        return results
    
    def _fix_single_file_asset(self, file_path: str, file_obj: ModFile, issues: List[Dict[str, Any]]) -> FixResult:
        """Thread-safe method to fix asset references in a single file."""
        print()
        print_status(f"FILE: {Path(file_path).name}", "INFO")
        print_status("TASK: Fixing asset references", "PROCESSING")
        print(f"  [WHY]  File contains references to assets that may not exist", Colors.GRAY)
        print(f"  [HOW]  Analyzing asset paths and correcting them using AI...", Colors.GRAY)
        
        # Build prompt for AI
        prompt = self._build_asset_fix_prompt(file_obj, issues)
        
        # Get AI fix
        if OLLAMA_AVAILABLE:
            try:
                fixed_content = self._get_ai_fix(
                    file_obj.content,
                    prompt,
                    task_type="code"
                )
                
                if fixed_content:
                    if fixed_content != file_obj.content:
                        print(f"      [FIX] AI generated fix for {Path(file_path).name}")
                        print(f"      [FIX] Original length: {len(file_obj.content)} chars")
                        print(f"      [FIX] Fixed length: {len(fixed_content)} chars")
                        # Apply fix (thread-safe file write)
                        result = self._apply_fix(file_path, file_obj.content, fixed_content, create_backup=True)
                        if result.success:
                            print(f"      [FIX] [OK] Successfully applied fix to {Path(file_path).name}")
                        else:
                            print(f"      [FIX] [FAIL] Failed to apply fix: {result.errors}")
                        return result
                    else:
                        print_status(f"No changes needed for {Path(file_path).name} (file is already correct)", "INFO")
                        return FixResult(
                            file_path=file_path,
                            success=True,
                            changes=[],
                            original_content=file_obj.content,
                            fixed_content=file_obj.content,
                            errors=[]
                        )
                else:
                    print_status(f"No changes suggested by AI for {Path(file_path).name}", "WARNING")
                    return FixResult(
                        file_path=file_path,
                        success=True,
                        changes=[],
                        original_content=file_obj.content,
                        fixed_content=file_obj.content,
                        errors=[]
                    )
            except Exception as e:
                print_status(f"Failed to fix {Path(file_path).name} : {e}", "ERROR")
                return FixResult(
                    file_path=file_path,
                    success=False,
                    changes=[],
                    original_content=file_obj.content,
                    fixed_content=file_obj.content,
                    errors=[str(e)]
                )
        else:
            return FixResult(
                file_path=file_path,
                success=False,
                changes=[],
                original_content=file_obj.content,
                fixed_content=file_obj.content,
                errors=["Ollama not available"]
            )
    
    def _calculate_optimal_workers(self, issues_by_file: Dict[str, List[Dict[str, Any]]], analysis: ModAnalysis) -> int:
        """
        Calculate optimal number of workers based on file complexity.
        
        Complexity factors:
        - File count (more files = more workers, up to a point)
        - Total file size (larger files = fewer concurrent workers to avoid memory issues)
        - Issue count per file (more issues = more processing time per file)
        - Available CPU cores
        
        Returns:
            Optimal number of workers (thread-safe, scales with complexity)
        """
        if not issues_by_file:
            return 1
        
        file_count = len(issues_by_file)
        available_cores = self.cpu_manager.available_cores
        
        # Calculate total complexity score
        total_size = 0
        total_issues = 0
        max_file_size = 0
        
        for file_path, issues in issues_by_file.items():
            file_obj = next((f for f in analysis.files if str(f.path) == file_path), None)
            if file_obj:
                file_size = len(file_obj.content)
                total_size += file_size
                max_file_size = max(max_file_size, file_size)
                total_issues += len(issues)
        
        # Base workers: scale with file count (up to available cores)
        base_workers = min(file_count, available_cores)
        
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
        # - For very simple tasks: can use more workers
        # - For complex tasks: use fewer workers to avoid overwhelming the system
        
        optimal_workers = min(optimal_workers, max(1, available_cores - 1))
        optimal_workers = max(1, optimal_workers)  # At least 1 worker
        
        return optimal_workers
    
    def _fix_asset_references(self, analysis: ModAnalysis) -> List[FixResult]:
        """Fix asset reference issues using AI with parallel processing."""
        results = []
        
        # Group issues by file
        issues_by_file: Dict[str, List[Dict[str, Any]]] = {}
        for issue in analysis.asset_issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        if not issues_by_file:
            return results
        
        # Calculate optimal workers based on complexity (thread-safe scaling)
        max_workers = self._calculate_optimal_workers(issues_by_file, analysis)
        print(f"    Processing {len(issues_by_file)} files with {max_workers} workers (scaled based on complexity)...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for file_path, issues in issues_by_file.items():
                file_obj = next((f for f in analysis.files if str(f.path) == file_path), None)
                if file_obj:
                    future = executor.submit(self._fix_single_file_asset, file_path, file_obj, issues)
                    future_to_file[future] = file_path
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print_status(f"Exception while processing {Path(file_path).name} : {e}", "ERROR")
                    file_obj = next((f for f in analysis.files if str(f.path) == file_path), None)
                    results.append(FixResult(
                        file_path=file_path,
                        success=False,
                        changes=[],
                        original_content=file_obj.content if file_obj else "",
                        fixed_content="",
                        errors=[str(e)]
                    ))
        
        return results
    
    def _fix_single_file_api(self, file_path: str, file_obj: ModFile, issues: List[Dict[str, Any]]) -> FixResult:
        """Thread-safe method to fix API issues in a single file."""
        print()
        print_status(f"FILE: {Path(file_path).name}", "INFO")
        print_status("TASK: Fixing API compatibility issues", "PROCESSING")
        print(f"  [WHY]  File uses API calls that may be outdated or incompatible", Colors.GRAY)
        print(f"  [HOW]  Updating API calls to match current game version using AI...", Colors.GRAY)
        
        # Build prompt for AI
        prompt = self._build_api_fix_prompt(file_obj, issues)
        
        # Get AI fix
        if OLLAMA_AVAILABLE:
            try:
                fixed_content = self._get_ai_fix(
                    file_obj.content,
                    prompt,
                    task_type="code"
                )
                
                if fixed_content:
                    if fixed_content != file_obj.content:
                        print(f"      [FIX] AI generated fix for {Path(file_path).name}")
                        print(f"      [FIX] Original length: {len(file_obj.content)} chars")
                        print(f"      [FIX] Fixed length: {len(fixed_content)} chars")
                        # Apply fix (thread-safe file write)
                        result = self._apply_fix(file_path, file_obj.content, fixed_content, create_backup=True)
                        if result.success:
                            print(f"      [FIX] [OK] Successfully applied fix to {Path(file_path).name}")
                        else:
                            print(f"      [FIX] [FAIL] Failed to apply fix: {result.errors}")
                        return result
                    else:
                        print_status(f"No changes needed for {Path(file_path).name} (file is already correct)", "INFO")
                        return FixResult(
                            file_path=file_path,
                            success=True,
                            changes=[],
                            original_content=file_obj.content,
                            fixed_content=file_obj.content,
                            errors=[]
                        )
                else:
                    print_status(f"No changes suggested by AI for {Path(file_path).name}", "WARNING")
                    return FixResult(
                        file_path=file_path,
                        success=True,
                        changes=[],
                        original_content=file_obj.content,
                        fixed_content=file_obj.content,
                        errors=[]
                    )
            except Exception as e:
                print_status(f"Failed to fix {Path(file_path).name} : {e}", "ERROR")
                return FixResult(
                    file_path=file_path,
                    success=False,
                    changes=[],
                    original_content=file_obj.content,
                    fixed_content=file_obj.content,
                    errors=[str(e)]
                )
        else:
            return FixResult(
                file_path=file_path,
                success=False,
                changes=[],
                original_content=file_obj.content,
                fixed_content=file_obj.content,
                errors=["Ollama not available"]
            )
    
    def _fix_api_issues(self, analysis: ModAnalysis) -> List[FixResult]:
        """Fix API issues using AI with parallel processing."""
        results = []
        
        # Group issues by file
        issues_by_file: Dict[str, List[Dict[str, Any]]] = {}
        for issue in analysis.api_issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        if not issues_by_file:
            return results
        
        # Calculate optimal workers based on complexity (thread-safe scaling)
        max_workers = self._calculate_optimal_workers(issues_by_file, analysis)
        print(f"    Processing {len(issues_by_file)} files with {max_workers} workers (scaled based on complexity)...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for file_path, issues in issues_by_file.items():
                file_obj = next((f for f in analysis.files if str(f.path) == file_path), None)
                if file_obj:
                    future = executor.submit(self._fix_single_file_api, file_path, file_obj, issues)
                    future_to_file[future] = file_path
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print_status(f"Exception while processing {Path(file_path).name} : {e}", "ERROR")
                    file_obj = next((f for f in analysis.files if str(f.path) == file_path), None)
                    results.append(FixResult(
                        file_path=file_path,
                        success=False,
                        changes=[],
                        original_content=file_obj.content if file_obj else "",
                        fixed_content="",
                        errors=[str(e)]
                    ))
        
        return results
    
    def _load_error_logs(self, mod_name: Optional[str] = None):
        """Load error logs from specified paths or auto-detect."""
        if self.error_logs_cache:
            return  # Already loaded
        
        try:
            self.error_logs_cache = read_error_logs(
                log_paths=self.error_log_paths,
                save_path=self.save_path,
                mod_name=mod_name
            )
            if self.error_logs_cache:
                print_status(f"Loaded error logs from {len(self.error_logs_cache)} log file(s)", "INFO")
        except Exception as e:
            print_status(f"Could not load error logs: {e}", "WARNING")
    
    def _build_asset_fix_prompt(self, mod_file: ModFile, issues: List[Dict[str, Any]]) -> str:
        """Build a prompt for fixing asset references, with RAG if available."""
        # Extract asset-related queries
        asset_queries = [issue['asset'] for issue in issues[:3]]
        
        # Use RAG to retrieve relevant code context for asset handling
        retrieved_chunks = None
        if self.use_rag and self.rag_system and asset_queries:
            try:
                # Search for asset loading/usage patterns
                query = "asset reference loading " + " ".join(asset_queries)
                print(f"      [RAG] Retrieving relevant asset handling code...")
                retrieved_chunks = self.rag_system.retrieve(query, top_k=3)
                if retrieved_chunks and retrieved_chunks.chunks:
                    print(f"      [RAG] [OK] Retrieved {len(retrieved_chunks.chunks)} relevant code chunks")
                else:
                    print(f"      [RAG] [SKIP] No chunks retrieved (lock may be held or index empty)")
                    retrieved_chunks = None
            except Exception as e:
                print(f"      [RAG] [FAIL] Retrieval failed: {e}")
                print(f"      [RAG] Continuing without RAG context")
                retrieved_chunks = None
        elif not self.use_rag:
            print(f"      [RAG] RAG disabled, using basic prompts")
        elif not self.rag_system:
            print(f"      [RAG] RAG system not available, using basic prompts")
        
        # Include error logs if available
        error_log_context = ""
        if self.error_logs_cache:
            error_log_context = format_error_logs_for_context(self.error_logs_cache, max_lines=30)
        
        # Build prompt
        if retrieved_chunks and retrieved_chunks.chunks:
            # Use RAG-augmented prompt
            task_description = f"""Fix asset reference issues in this Caves of Qud mod file.

The file contains references to assets that may not exist or have incorrect paths.
Use the retrieved code context to understand correct asset reference patterns."""
            
            if error_log_context:
                task_description += f"\n\n{error_log_context}"
            
            constraints = [
                "Use correct asset paths from StreamingAssets",
                "Follow asset loading patterns from retrieved code",
                "Maintain compatibility with game asset system"
            ]
            
            prompt = self.rag_system.build_rag_prompt(
                query=" ".join(asset_queries),
                retrieved_chunks=retrieved_chunks,
                task_description=task_description,
                constraints=constraints
            )
            
            # Add asset issues and mod file
            prompt += f"""

# Asset Issues
"""
            for issue in issues:
                prompt += f"- {issue['asset']} (missing)"
                if issue.get('similar'):
                    prompt += f" - similar: {issue['similar']}"
                prompt += "\n"
            
            prompt += f"""

# File to Fix
```csharp
{mod_file.content[:2000]}
```
"""
        else:
            # Fallback to basic prompt
            prompt = f"""Fix asset reference issues in this Caves of Qud mod file.

The file contains references to assets that may not exist or have incorrect paths.
Available assets are in: {self.streaming_assets_path}

Issues to fix:
"""
            for issue in issues:
                prompt += f"- {issue['asset']} (missing)"
                if issue.get('similar'):
                    prompt += f" - similar: {issue['similar']}"
                prompt += "\n"
            
            if error_log_context:
                prompt += f"\n{error_log_context}\n"
            
            prompt += f"""

Original file content:
```csharp
{mod_file.content[:3000]}
```

Please provide the fixed C# code with corrected asset paths. Only output the complete fixed code, no explanations.
"""
        
        return prompt
    
    def _build_api_fix_prompt(self, mod_file: ModFile, issues: List[Dict[str, Any]]) -> str:
        """Build a prompt for fixing API issues, with RAG if available."""
        # Separate ability issues from other API issues
        ability_issues = [i for i in issues if i.get('type', '').startswith('activated_ability_') or i.get('type', '').startswith('command_method_') or i.get('type', '') == 'ability_not_removed_on_unmutate']
        other_issues = [i for i in issues if i not in ability_issues]
        
        # Build prompt based on issue types
        prompt_parts = []
        
        # Handle activated ability issues with specialized guidance
        if ability_issues:
            prompt_parts.append("CRITICAL ACTIVATED ABILITY ISSUES DETECTED:\n")
            for issue in ability_issues:
                issue_type = issue.get('type', '')
                severity = issue.get('severity', 'medium').upper()
                line = issue.get('line', 'unknown')
                description = issue.get('description', '')
                
                prompt_parts.append(f"\n[{severity}] Line {line}: {description}")
                
                if issue_type == 'activated_ability_no_cooldown':
                    ability_name = issue.get('ability_name', 'Unknown')
                    ability_var = issue.get('ability_var', 'Unknown')
                    prompt_parts.append(f"""
ISSUE: Activated ability "{ability_name}" (variable: {ability_var}) has NO COOLDOWN.
This allows the player to spam the ability infinitely without any cost or delay.

REQUIRED FIX (from game source code - SpacetimeVortex.cs):
1. In the command method for this ability, add cooldown and energy calls:
   ```csharp
   this.UseEnergy(1000, "Mental Mutation {ability_name}");  // Energy cost
   this.CooldownMyActivatedAbility(this.{ability_var}, cooldownTurns);  // Cooldown
   ```

2. Example from SpacetimeVortex.cs (lines 114-115):
   ```csharp
   this.UseEnergy(1000, "Mental Mutation SpaceTimeVortex");
   this.CooldownMyActivatedAbility(this.ActivatedAbilityID, Math.Max(550 - 50 * this.Level, 5));
   ```

3. Define cooldown calculation if needed (from SpacetimeVortex.cs line 43-49):
   ```csharp
   public int GetCooldown(int Level)
   {{
       int cooldown = 550 - 50 * Level;
       if (cooldown < 5)
           cooldown = 5;
       return cooldown;
   }}
   ```

4. Place cooldown and energy calls AFTER ability succeeds but BEFORE return true.

EXAMPLE FIX:
```csharp
public bool Command{ability_name.replace(' ', '')}(GameObject GO)
{{
    // ... ability code ...
    
    // Apply energy cost and cooldown after successful use
    this.UseEnergy(1000, "Mental Mutation {ability_name}");
    this.CooldownMyActivatedAbility(this.{ability_var}, GetCooldown(this.Level));
    
    return true;
}}
```
""")
                
                elif issue_type == 'command_method_no_cooldown':
                    method_name = issue.get('method_name', 'Unknown')
                    prompt_parts.append(f"""
ISSUE: Command method "{method_name}" may lack cooldown management.
This could allow spamming of the ability if it's tied to an activated ability.

RECOMMENDED FIX (from game source code):
1. If this command is triggered by an activated ability, ensure cooldown is applied
2. Add energy cost: this.UseEnergy(1000, "Mental Mutation Name")
3. Add cooldown: this.CooldownMyActivatedAbility(this.ActivatedAbilityID, cooldownTurns)

EXAMPLE:
```csharp
public bool {method_name}(GameObject GO)
{{
    // Check if ability is ready (optional)
    // if (!IsMyActivatedAbilityReady(abilityID)) return false;
    
    // ... ability logic ...
    
    // Apply cooldown
    ApplyCooldown(GO, abilityID, GetCooldownForLevel(GO));
    
    return true;
}}
```
""")
                
                elif issue_type == 'ability_not_removed_on_unmutate':
                    ability_id = issue.get('ability_id', 'Unknown')
                    prompt_parts.append(f"""
ISSUE: Ability ID "{ability_id}" is NOT removed in Unmutate() method.
This causes the ability to persist even after the mutation is removed.

REQUIRED FIX:
Add this to the Unmutate() method:
```csharp
public override bool Unmutate(GameObject GO)
{{
    RemoveMyActivatedAbility(ref {ability_id});
    // ... other cleanup ...
    return base.Unmutate(GO);
}}
```
""")
        
        # Handle other API issues
        if other_issues:
            if ability_issues:
                prompt_parts.append("\n\nOTHER API ISSUES:\n")
            
            # Extract API calls/methods that need fixing
            api_queries = []
            for issue in other_issues:
                if issue.get('api_call'):
                    api_queries.append(issue['api_call'])
                elif issue.get('method'):
                    api_queries.append(issue['method'])
                elif issue.get('class'):
                    api_queries.append(issue['class'])
            
            # Use RAG to retrieve relevant code context
            retrieved_chunks = None
            if self.use_rag and self.rag_system and api_queries:
                try:
                    # Retrieve context for the API calls
                    query = " ".join(api_queries[:3])  # Use first 3 API calls as query
                    print(f"      [RAG] Retrieving relevant code context...")
                    retrieved_chunks = self.rag_system.retrieve(query, top_k=5)
                    if retrieved_chunks and retrieved_chunks.chunks:
                        print(f"      [RAG] [OK] Retrieved {len(retrieved_chunks.chunks)} relevant code chunks")
                    else:
                        print(f"      [RAG] [SKIP] No chunks retrieved (lock may be held or index empty)")
                        retrieved_chunks = None
                except Exception as e:
                    print(f"      [RAG] [FAIL] Retrieval failed: {e}")
                    print(f"      [RAG] Continuing without RAG context")
                    retrieved_chunks = None
            elif not self.use_rag:
                print(f"      [RAG] RAG disabled, using basic prompts")
            elif not self.rag_system:
                print(f"      [RAG] RAG system not available, using basic prompts")
            
            # Include error logs if available
            error_log_context = ""
            if self.error_logs_cache:
                error_log_context = format_error_logs_for_context(self.error_logs_cache, max_lines=30)
            
            # Build final prompt
            if ability_issues and not other_issues:
                # Only ability issues - use specialized prompt
                final_prompt = "".join(prompt_parts)
                final_prompt += f"\n\nOriginal file content:\n```csharp\n{mod_file.content}\n```\n"
                final_prompt += "\nPlease provide the fixed C# code with cooldown management properly implemented. Only output the complete fixed code, no explanations."
                return final_prompt
            
            # Continue with normal RAG/fallback logic for other issues
            prompt_parts.append("\n")
            
            # Build prompt
            if retrieved_chunks and retrieved_chunks.chunks:
                # Use RAG-augmented prompt
                task_description = "".join(prompt_parts) + f"""Fix API compatibility issues in this Caves of Qud mod file.

The file uses API calls that may be outdated or incompatible with the current game version.
Use the retrieved code context to understand the correct API patterns."""
            
            if error_log_context:
                task_description += f"\n\n{error_log_context}"
            
            constraints = [
                "Maintain compatibility with existing codebase",
                "Follow patterns from retrieved code context",
                "No external API calls",
                "Preserve all existing functionality"
            ]
            
            prompt = self.rag_system.build_rag_prompt(
                query=" ".join(api_queries),
                retrieved_chunks=retrieved_chunks,
                task_description=task_description,
                constraints=constraints
            )
            
            # Add issues list
            prompt += f"""

# Issues to Fix
"""
            for issue in issues:
                if issue.get('type', '').startswith('activated_ability_') or issue.get('type', '').startswith('command_method_') or issue.get('type', '') == 'ability_not_removed_on_unmutate':
                    # Already handled in prompt_parts
                    continue
                elif issue['type'] == 'missing_class':
                    prompt += f"- Class '{issue['class']}' not found\n"
                elif issue['type'] == 'missing_method':
                    prompt += f"- Method '{issue['method']}' in class '{issue['class']}' not found\n"
                else:
                    prompt += f"- {issue.get('type', 'unknown')}: {issue.get('api_call', issue.get('method', 'unknown'))}\n"
            
            # Add the mod file content
            prompt += f"""

# File to Fix
```csharp
{mod_file.content[:2000]}  # Limited for context
```
"""
        else:
            # Fallback to basic prompt (no RAG)
            prompt = "".join(prompt_parts) + f"""Fix API compatibility issues in this Caves of Qud mod file.

The file uses API calls that may have changed or been removed.
Source code reference: {self.source_path}

Issues to fix:
"""
            for issue in issues:
                if issue.get('type', '').startswith('activated_ability_') or issue.get('type', '').startswith('command_method_') or issue.get('type', '') == 'ability_not_removed_on_unmutate':
                    # Already handled in prompt_parts
                    continue
                elif issue['type'] == 'missing_class':
                    prompt += f"- Class '{issue['class']}' not found\n"
                elif issue['type'] == 'missing_method':
                    prompt += f"- Method '{issue['method']}' in class '{issue['class']}' not found\n"
            
            if error_log_context:
                prompt += f"\n{error_log_context}\n"
            
            prompt += f"""

Original file content:
```csharp
{mod_file.content[:3000]}
```

CRITICAL: Make TARGETED FIXES ONLY - do NOT rewrite the entire file.
- Preserve ALL existing code structure, classes, methods, and logic
- Only modify the specific API calls that need updating
- Keep all namespaces, using statements, and class declarations EXACTLY as they are
- Output ONLY the complete fixed code file (no markdown, no explanations)
"""
        
        return prompt
    
    def _get_ai_fix(self, original_content: str, prompt: str, task_type: str = "code") -> Optional[str]:
        """Get AI-generated fix using multimodel router (Code Llama 7B for reasoning, StarCoder 7B for generation)."""
        if not OLLAMA_AVAILABLE:
            print("      Ollama not available, skipping AI fix")
            return None
        
        # Test connection
        if not test_ollama_connection():
            print("      Ollama connection failed")
            return None
        
        # Monitor CPU usage
        self.cpu_manager.monitor_cpu_usage(0.5)
        
        # Get optimal thread count (all but 1 core)
        optimal_threads = self.cpu_manager.get_optimal_threads()
        
        # Prepare system prompt
        system_prompt = """You are an expert C# developer specializing in Caves of Qud modding.
You understand Harmony patches, XRL API, and game asset references.

CRITICAL RULES:
1. Make TARGETED FIXES only - do NOT rewrite the entire file
2. Preserve ALL existing code structure, classes, methods, and logic
3. Only modify the specific issues mentioned in the prompt
4. Keep all namespaces, using statements, and class declarations unchanged
5. Output ONLY the complete fixed code file (no markdown, no explanations)
6. Ensure the output is valid C# that compiles"""
        
        # Use multimodel router if available
        if self.router and MULTIMODEL_ROUTER_AVAILABLE:
            try:
                # Get available models (already have import from __init__)
                try:
                    from ollama_integration import get_available_models
                except ImportError:
                    # Fallback: get models from AI_CONFIG
                    available_models = []
                    for task_type in ['code', 'analysis']:
                        if AI_CONFIG.get('selected_models', {}).get(task_type):
                            available_models.append(AI_CONFIG['selected_models'][task_type])
                else:
                    available_models = get_available_models()
                
                # Route task to appropriate model (with complexity detection)
                # If preferred_model is specified, use it directly instead of routing
                if self.preferred_model:
                    print(f"      [MODEL] Using preferred model: {self.preferred_model} (bypassing router)")
                    # Create a simple routing decision for preferred model
                    from ollama_model_router import RoutingDecision, TaskIntent
                    routing = RoutingDecision(
                        intent=TaskIntent.GENERATION,
                        complexity="complex" if len(original_content) > 5000 else "standard",
                        primary_model=self.preferred_model,
                        verification_model=None,
                        confidence=1.0
                    )
                else:
                    task_description = "Fix code issues in Caves of Qud mod file"
                    code_length = len(original_content)  # For complexity detection
                    routing = self.router.route_with_intent(
                        prompt=prompt,
                        task_description=task_description,
                        task_type=task_type,
                        code_length=code_length
                    )
                
                print(f"      [MODEL ROUTING] Intent: {routing.intent.value}")
                print(f"      [MODEL ROUTING] Complexity: {routing.complexity}")
                print(f"      [MODEL ROUTING] Primary model: {routing.primary_model}")
                print(f"      [MODEL ROUTING] Confidence: {routing.confidence:.2f}")
                if routing.verification_model:
                    print(f"      [MODEL ROUTING] Verification model: {routing.verification_model}")
                if routing.complexity == "complex":
                    print(f"      [MODEL SWAP] Loading CodeLlama 34B (senior engineer model) for complex/high-risk task")
                    print(f"      [MODEL SWAP] Will unload after task completion to save resources")
                
                # Call primary model
                print(f"      [STEP 1] Generating fix with {routing.primary_model}...")
                primary_response = call_ollama(
                    prompt=prompt,
                    task_type=task_type,
                    response_length="detailed",
                    system_prompt=system_prompt,
                    model_name=routing.primary_model
                )
                
                if not primary_response:
                    print(f"      [STEP 1] [FAIL] Primary model failed")
                    return None
                
                # For complex tasks, unload CodeLlama 34B immediately after use (senior engineer model)
                if routing.complexity == "complex" and routing.primary_model == self.router.complex_model:
                    print(f"      [MODEL SWAP] Unloading CodeLlama 34B (senior engineer model) after task completion")
                    self.router.unload_model(routing.primary_model)
                    print(f"      [MODEL SWAP] CodeLlama 34B unloaded, returning to standard models")
                
                # Check confidence
                confidence_score, confidence_meta = self.router.score_output_confidence(
                    primary_response,
                    prompt,
                    min_length=50
                )
                
                print(f"      [STEP 1] [OK] Generated fix (confidence: {confidence_score:.2f})")
                
                # If using StarCoder for generation, verify with Code Llama
                # Skip verification if RAG is disabled (to avoid unnecessary model switches)
                if routing.verification_model and routing.intent == TaskIntent.GENERATION and self.use_rag:
                    print(f"      [MODEL SWAP] Switching to verification model: {routing.verification_model}")
                    print(f"      [STEP 2] Verifying with {routing.verification_model}...")
                    
                    verification_prompt = self.router.create_verification_prompt(
                        original_code=original_content[:1500],
                        generated_code=primary_response[:2000],
                        task_description=task_description
                    )
                    
                    verification_response = call_ollama(
                        prompt=verification_prompt,
                        task_type="analysis",
                        response_length="standard",
                        system_prompt="You are a code reviewer. Review code changes for correctness and safety.",
                        model_name=routing.verification_model
                    )
                    
                    if verification_response:
                        # Check verification verdict
                        verdict = verification_response.lower()
                        if 'approve' in verdict or 'correct' in verdict or 'safe' in verdict:
                            print(f"      [STEP 2] [OK] Verification passed")
                            return primary_response
                        elif 'reject' in verdict or 'error' in verdict or 'issue' in verdict:
                            print(f"      [STEP 2] [FAIL] Verification failed - issues detected")
                            print(f"      [STEP 2] Review: {verification_response[:200]}...")
                            # Still return the code but with warning
                            print(f"      [WARNING] Using unverified code - review manually")
                            return primary_response
                        else:
                            print(f"      [STEP 2] ? Verification inconclusive")
                            print(f"      [STEP 2] Review: {verification_response[:200]}...")
                            return primary_response
                    else:
                        print(f"      [STEP 2] [FAIL] Verification failed (no response)")
                        # Return primary response anyway if confidence is high
                        if confidence_score >= 0.7:
                            print(f"      [STEP 2] Using high-confidence output without verification")
                            return primary_response
                        return None
                else:
                    # No verification needed (reasoning task) or verification disabled or RAG disabled
                    if routing.verification_model and routing.intent == TaskIntent.GENERATION and not self.use_rag:
                        print(f"      [SKIP] Skipping verification (RAG disabled, avoiding model switches)")
                    # Validate the response before returning
                    validated_response = self._validate_ai_response(primary_response, original_content)
                    if validated_response:
                        return validated_response
                    else:
                        print(f"      [REJECT] AI response failed validation - too different from original")
                        return None
                    
            except Exception as e:
                print(f"      Warning: Multimodel routing failed: {e}")
                print(f"      Falling back to single-model approach...")
                # Fall through to single-model approach
        
        # Fallback: Single-model approach (original logic)
        try:
            # Use code model - prefer StarCoder 7B or Code Llama 7B instruct for better code generation
            # CodeLlama 34B kept as fallback (has indexing issues but good for complex reasoning)
            model = None
            
            # Check if a preferred model was specified
            if self.preferred_model:
                model = self.preferred_model
                print(f"      Using specified model: {model}")
            # Check available models and prefer StarCoder/Code Llama 7B
            elif hasattr(AI_CONFIG, 'selected_models') and AI_CONFIG.get('selected_models', {}).get('code'):
                model = AI_CONFIG['selected_models']['code']
            else:
                # Fallback: try to find best code model in preferred models
                available_models = AI_CONFIG.get("preferred_models", {}).get("code", [])
                # Prefer StarCoder 7B or Code Llama 7B instruct (better for code generation)
                # These models are better at referencing source code without indexing issues
                preferred_models = [m for m in available_models if any(x in m.lower() for x in ['starcoder', 'codellama:7b'])]
                if preferred_models:
                    model = preferred_models[0]
                elif available_models:
                    model = available_models[0]  # Use first available (should be StarCoder or Code Llama 7B)
                else:
                    model = "starcoder:7b"  # Default to StarCoder 7B
            
            print(f"      Using model: {model} with {optimal_threads} threads")
            if 'starcoder' in model.lower():
                print(f"      (StarCoder 7B - optimized for code generation, ~4-10 GB VRAM)")
            elif 'codellama:7b' in model.lower():
                print(f"      (Code Llama 7B - good for patches and code reasoning, ~4-10 GB VRAM)")
            elif 'codellama:34b' in model.lower():
                print(f"      (CodeLlama 34B - fallback for complex reasoning, may have indexing issues)")
            
            # Call Ollama - the integration module handles thread count automatically
            # but we can monitor CPU to ensure proper usage
            # Note: call_ollama uses generate API by default, works well with StarCoder and Code Llama
            response = call_ollama(
                prompt=prompt,
                task_type=task_type,
                response_length="detailed",
                system_prompt=system_prompt,
                model_name=model
            )
            
            # Monitor CPU after call to ensure it's being used properly
            cpu_usage = self.cpu_manager.monitor_cpu_usage(0.5)
            if cpu_usage < MIN_CPU_PERCENT_PER_CORE:
                print(f"      Warning: Low CPU usage detected ({cpu_usage:.1f}%), may indicate issues")
            
            if response:
                # Validate the response before returning
                validated_response = self._validate_ai_response(response, original_content)
                if not validated_response:
                    print(f"      [REJECT] AI response failed validation - too different from original")
                    return None
                
                # Check confidence even in fallback mode
                if MULTIMODEL_ROUTER_AVAILABLE and self.router:
                    confidence_score, confidence_meta = self.router.score_output_confidence(validated_response, prompt)
                    if confidence_score < 0.6:
                        print(f"      Warning: Low confidence output (score: {confidence_score:.2f})")
                        if confidence_meta.get('too_short'):
                            print(f"        Output may be too short")
                        if confidence_meta.get('incomplete'):
                            print(f"        Output appears incomplete")
                
                # Extract code from response (remove markdown code blocks if present)
                code = response.strip()
                if code.startswith("```"):
                    # Remove code block markers
                    lines = code.split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].strip() == "```":
                        lines = lines[:-1]
                    code = '\n'.join(lines)
                
                # Validate the response before returning
                validated_code = self._validate_ai_response(code, original_content)
                if validated_code:
                    return validated_code
                else:
                    print(f"      [REJECT] AI response failed validation - too different from original")
                    return None
            else:
                print("      No response from AI")
                return None
                
        except Exception as e:
            print(f"      AI call failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
    
    def _validate_ai_response(self, ai_response: str, original_content: str) -> Optional[str]:
        """Validate AI response to ensure it's a valid fix, not a complete rewrite.
        
        Returns the cleaned response if valid, None if invalid.
        """
        if not ai_response or len(ai_response.strip()) < 50:
            print(f"      [VALIDATION] Response too short ({len(ai_response)} chars)")
            return None
        
        cleaned_response = ai_response.strip()
        
        # Check for markdown code blocks and extract code
        if '```' in cleaned_response:
            import re
            code_blocks = re.findall(r'```(?:csharp|cs|c#)?\s*\n(.*?)```', cleaned_response, re.DOTALL)
            if code_blocks:
                cleaned_response = code_blocks[0].strip()
            else:
                code_blocks = re.findall(r'```\s*\n(.*?)```', cleaned_response, re.DOTALL)
                if code_blocks:
                    cleaned_response = code_blocks[0].strip()
        
        # Check if response is too different from original (likely a complete rewrite)
        original_lower = original_content.lower()
        response_lower = cleaned_response.lower()
        
        # Check for key structural elements that should be preserved
        key_elements = []
        import re
        
        # Extract namespace from original
        ns_match = re.search(r'namespace\s+(\S+)', original_content)
        if ns_match:
            key_elements.append(('namespace', ns_match.group(1).lower()))
        
        # Extract class name from original
        class_match = re.search(r'class\s+(\w+)', original_content)
        if class_match:
            key_elements.append(('class', class_match.group(1).lower()))
        
        # Check if key elements are preserved
        missing_elements = []
        for elem_type, elem_name in key_elements:
            if elem_name not in response_lower:
                missing_elements.append(f"{elem_type} '{elem_name}'")
        
        if missing_elements:
            print(f"      [VALIDATION] Missing key elements: {', '.join(missing_elements)}")
            return None
        
        # Check size similarity - response shouldn't be drastically different in size
        size_ratio = len(cleaned_response) / len(original_content) if len(original_content) > 0 else 0
        if size_ratio < 0.3 or size_ratio > 3.0:
            print(f"      [VALIDATION] Size ratio suspicious: {size_ratio:.2f} (original: {len(original_content)}, response: {len(cleaned_response)})")
            return None
        
        # Check for basic C# structure
        if 'using' not in response_lower and 'using' in original_lower:
            print(f"      [VALIDATION] Missing 'using' statements - may not be valid C#")
            return None
        
        # If we get here, the response seems valid
        return cleaned_response
    
    def _apply_fix(self, file_path: str, original_content: str, fixed_content: str, create_backup: bool = True) -> FixResult:
        """Apply a fix to a file (thread-safe)."""
        file_path_obj = Path(file_path)
        
        try:
            # Create backup before editing
            backup_path = None
            if create_backup and file_path_obj.exists():
                backup_path = self._create_file_backup(file_path_obj)
                if backup_path:
                    print_status(f"Backup created: {backup_path.name}", "SUCCESS")
                    print(f"  [BACKUP] {backup_path}")
            
            # Show current file being edited
            print()
            print_status(f"Editing file: {file_path_obj.name}", "PROCESSING")
            print(f"  [FILE]   {file_path_obj}")
            
            # Calculate changes and display diff
            original_lines = original_content.split('\n')
            fixed_lines = fixed_content.split('\n')
            diff = list(difflib.unified_diff(
                original_lines, 
                fixed_lines, 
                fromfile=f"{file_path_obj.name} (original)",
                tofile=f"{file_path_obj.name} (fixed)",
                lineterm='',
                n=3  # Show 3 lines of context
            ))
            
            changes = [line for line in diff if line.startswith('+') or line.startswith('-')]
            
            # Display the changes
            if diff:
                print()
                print_status("Code Changes:", "INFO")
                print("  " + "=" * 76)
                
                # Limit diff display to first 100 lines to avoid overwhelming output
                max_diff_lines = 100
                diff_to_show = diff[:max_diff_lines]
                if len(diff) > max_diff_lines:
                    print(f"  {Colors.WARNING}Showing first {max_diff_lines} of {len(diff)} diff lines...{Colors.RESET}")
                    print()
                
                # Show diff with color coding
                for line in diff_to_show:
                    if line.startswith('---') or line.startswith('+++'):
                        print(f"  {Colors.GRAY}{line}{Colors.RESET}")
                    elif line.startswith('@@'):
                        print(f"  {Colors.CYAN}{line}{Colors.RESET}")
                    elif line.startswith('+'):
                        # Added lines in green
                        print(f"  {Colors.SUCCESS}+{line[1:]}{Colors.RESET}")
                    elif line.startswith('-'):
                        # Removed lines in red
                        print(f"  {Colors.ERROR}-{line[1:]}{Colors.RESET}")
                    else:
                        # Context lines
                        print(f"  {line}")
                
                if len(diff) > max_diff_lines:
                    print(f"  {Colors.WARNING}... ({len(diff) - max_diff_lines} more lines){Colors.RESET}")
                
                print("  " + "=" * 76)
                print()
            
            # Thread-safe file write
            with self._file_write_lock:
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
            
            print_status(f"Applied {len(changes)} change(s) to {file_path_obj.name}", "SUCCESS")
            
            return FixResult(
                file_path=file_path,
                success=True,
                changes=changes[:10],  # Limit to first 10 changes
                original_content=original_content,
                fixed_content=fixed_content,
                errors=[]
            )
        except Exception as e:
            return FixResult(
                file_path=file_path,
                success=False,
                changes=[],
                original_content=original_content,
                fixed_content=fixed_content,
                errors=[str(e)]
            )


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


def main():
    """Main entry point."""
    import argparse
    
    # Single-instance lock to prevent multiple concurrent runs
    if TOOL_HELPERS_AVAILABLE:
        # Use shared SingleInstanceLock
        try:
            with SingleInstanceLock("qud_mod_fixer"):
                try:
                    _main_impl()
                except Exception as e:
                    print("\n" + "=" * 60)
                    print("ERROR: An error occurred during mod fixing:")
                    print("=" * 60)
                    print(f"{type(e).__name__}: {e}")
                    print("=" * 60)
                    import traceback
                    traceback.print_exc()
                    print("=" * 60)
                    print("")
                    try:
                        input("Press Enter to exit...")
                    except (EOFError, KeyboardInterrupt):
                        pass
                    raise
        except SystemExit:
            # Re-raise SystemExit (from lock failure)
            raise
        except Exception as e:
            print("\n" + "=" * 60)
            print("FATAL ERROR: Failed to start mod fixer:")
            print("=" * 60)
            print(f"{type(e).__name__}: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            print("=" * 60)
            print("")
            try:
                input("Press Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
            sys.exit(1)
    else:
        # Fallback to local implementation
        lock_file_path = Path(tempfile.gettempdir()) / "qud_mod_fixer.lock"
        lock_file = None
        lock_acquired = False
        
        try:
            # Try to acquire lock (platform-specific)
            if sys.platform == 'win32':
                if msvcrt is None:
                    print("Warning: msvcrt not available, cannot prevent concurrent instances")
                else:
                    try:
                        lock_file = open(lock_file_path, 'w')
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        lock_acquired = True
                        lock_file.write(str(os.getpid()))
                        lock_file.flush()
                    except IOError:
                        print("=" * 60)
                        print("ERROR: Another instance of QudModFixer is already running!")
                        print("=" * 60)
                        print("Please wait for the current instance to finish, or close it first.")
                        sys.exit(1)
            else:
                if fcntl is None:
                    print("Warning: fcntl not available, cannot prevent concurrent instances")
                else:
                    try:
                        lock_file = open(lock_file_path, 'w')
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_acquired = True
                        lock_file.write(str(os.getpid()))
                        lock_file.flush()
                    except IOError:
                        print("=" * 60)
                        print("ERROR: Another instance of QudModFixer is already running!")
                        print("=" * 60)
                        print("Please wait for the current instance to finish, or close it first.")
                        sys.exit(1)
        except Exception as e:
            print(f"Warning: Could not acquire lock file: {e}")
        
        try:
            try:
                _main_impl()
            except Exception as e:
                print("\n" + "=" * 60)
                print("ERROR: An error occurred during mod fixing:")
                print("=" * 60)
                print(f"{type(e).__name__}: {e}")
                print("=" * 60)
                import traceback
                traceback.print_exc()
                print("=" * 60)
                print("")
                try:
                    input("Press Enter to exit...")
                except (EOFError, KeyboardInterrupt):
                    pass
                raise
        except SystemExit:
            # Re-raise SystemExit
            raise
        except Exception as e:
            print("\n" + "=" * 60)
            print("FATAL ERROR: Failed to start mod fixer:")
            print("=" * 60)
            print(f"{type(e).__name__}: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            print("=" * 60)
            print("")
            try:
                input("Press Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
            sys.exit(1)
        finally:
            if lock_acquired and lock_file:
                try:
                    if sys.platform == 'win32' and msvcrt:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    elif fcntl:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                    if lock_file_path.exists():
                        lock_file_path.unlink()
                except Exception as e:
                    print(f"Warning: Could not release lock file: {e}")


def _main_impl():
    """Main implementation (separated for lock handling)."""
    import argparse
    
    try:
        parser = argparse.ArgumentParser(
            description="Fix Caves of Qud mods - now with natural language issue descriptions!",
            epilog="""
Examples:
  # Standard mode - auto-detects all issues
  python qud_mod_fixer.py "My Awesome Mod"
  
  # Natural language mode (Cursor-style!)
  python qud_mod_fixer.py "My Mod" --issue "ability has no cooldown, can spam it infinitely"
  python qud_mod_fixer.py "Space Time Vortex" --issue "says vortex created but nothing appears"
  python qud_mod_fixer.py "Broodmother" --issue "broodlings message shows but they dont spawn"
  
  # Natural language with specific file target
  python qud_mod_fixer.py "My Mod" --issue "crash on use" --file "MyAbility.cs"
  
  # Interactive natural language mode
  python qud_mod_fixer.py --interactive
""",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument("mod_name", nargs="*", help="Name of mod to fix (or 'all' for all mods). Can include spaces.")
        parser.add_argument("--issue", "-i", type=str, help="Natural language description of the issue (Cursor-style)")
        parser.add_argument("--file", "-f", type=str, help="Specific file to target (for natural language mode)")
        parser.add_argument("--source", default=str(QUD_SOURCE_PATH), help="Path to decompiled source")
        parser.add_argument("--assets", default=str(QUD_STREAMING_ASSETS), help="Path to StreamingAssets")
        parser.add_argument("--mods", default=str(QUD_MODS_PATH), help="Path to mods directory")
        parser.add_argument("--workshop", default=str(QUD_WORKSHOP_PATH), help="Path to Steam Workshop content directory")
        parser.add_argument("--no-backup", action="store_true", help="Don't create backups (ignored - backups always created)")
        parser.add_argument("--analyze-only", action="store_true", help="Only analyze, don't fix")
        parser.add_argument("--no-rag", action="store_true", help="Disable RAG (Retrieval-Augmented Generation) system")
        parser.add_argument("--rag-index", help="Path to RAG index file (default: auto-generated)")
        parser.add_argument("--model", help="Preferred AI model to use (e.g., codellama:7b, starcoder:7b)")
        parser.add_argument("--list-models", action="store_true", help="List available Ollama models and exit")
        parser.add_argument("--interactive", action="store_true", help="Show interactive model selection menu")
        parser.add_argument("--error-logs", nargs="+", help="Paths to error log files to include (auto-detects if not specified)")
        parser.add_argument("--save-path", help="Path to Caves of Qud save directory (for auto-detecting error logs)")
        
        args = parser.parse_args()
        
        # Join mod name parts if it was split by spaces
        mod_name = " ".join(args.mod_name) if args.mod_name else None
        
        # Handle list models
        if args.list_models:
            show_model_list()
            return
        
        # Show header
        print_status_header("Caves of Qud Mod Fixer", Colors.CYAN)
        
        # Natural language mode check
        if args.issue or (args.interactive and not mod_name):
            if not mod_name:
                print()
                print("=" * 60)
                print("NATURAL LANGUAGE MOD FIXER (Cursor-style!)")
                print("=" * 60)
                print()
                print("Describe issues in plain English:")
                print('  - "ability has no cooldown"')
                print('  - "broodlings dont spawn"')
                print('  - "vortex doesnt appear"')
                print('  - "cant add to inventory"')
                print()
                mod_name_input = input("Mod name: ").strip()
                if mod_name_input:
                    mod_name = mod_name_input
                else:
                    print_status("No mod name provided", "ERROR")
                    return
        
        # Handle interactive model selection
        selected_model = None
        if args.interactive:
            if args.issue or not mod_name:
                # Natural language interactive mode
                if not args.issue:
                    print()
                    print("Describe the issue:")
                    args.issue = input("Issue: ").strip()
                    if not args.issue:
                        print_status("No issue description provided", "ERROR")
                        return
            else:
                # Standard interactive mode with model selection
                selected_model = show_model_menu(current_model=args.model or "")
                if selected_model is not None:
                    args.model = selected_model
        
        # Initialize fixer
        print_status("Initializing Caves of Qud Mod Fixer...", "PROCESSING")
        
        # RAG options
        use_rag = not args.no_rag if hasattr(args, 'no_rag') else True
        rag_index_path = Path(args.rag_index) if hasattr(args, 'rag_index') and args.rag_index else None
        
        # Prepare error log paths
        error_log_paths = None
        if hasattr(args, 'error_logs') and args.error_logs:
            error_log_paths = [Path(p) for p in args.error_logs]
        
        fixer = ModFixer(
            source_path=Path(args.source),
            streaming_assets_path=Path(args.assets),
            mods_path=Path(args.mods),
            workshop_path=Path(args.workshop) if args.workshop else None,
            use_rag=use_rag,
            rag_index_path=rag_index_path,
            preferred_model=getattr(args, 'model', None),
            error_log_paths=error_log_paths,
            save_path=Path(args.save_path) if hasattr(args, 'save_path') and args.save_path else None
        )
        
        # Find mods to fix
        if mod_name:
            if mod_name.lower() == 'all':
                mod_dirs = [d for d in fixer.mods_path.iterdir() if d.is_dir()]
            else:
                mod_dirs = [fixer.mods_path / mod_name]
        else:
            # Interactive mode
            mod_dirs = [d for d in fixer.mods_path.iterdir() if d.is_dir()]
            print("\nAvailable mods:")
            for i, mod_dir in enumerate(mod_dirs, 1):
                print(f"  {i}. {mod_dir.name}")
            choice = input("\nEnter mod number or name (or 'all'): ").strip()
            
            if choice.lower() == 'all':
                mod_dirs = mod_dirs
            elif choice.isdigit():
                mod_dirs = [mod_dirs[int(choice) - 1]]
            else:
                # Try exact match first
                mod_path = fixer.mods_path / choice
                if mod_path.exists():
                    mod_dirs = [mod_path]
                else:
                    # Try to find partial match
                    matching = [d for d in mod_dirs if choice.lower() in d.name.lower()]
                    if matching:
                        mod_dirs = matching
                    else:
                        mod_dirs = [fixer.mods_path / choice]
        
        # Sort mods alphabetically
        mod_dirs = sorted([d for d in mod_dirs if d.exists()], key=lambda x: x.name.lower())
        
        if not mod_dirs:
            print("  No mods found to process.")
            return
        
        # Display selected mods at startup
        print_section_header(f"SELECTED MODS TO PROCESS: {len(mod_dirs)} mod(s)", Colors.CYAN)
        for idx, mod_dir in enumerate(mod_dirs, 1):
            print(f"  [{idx}/{len(mod_dirs)}] {mod_dir.name}")
        print()
        print_status("Processing in alphabetical order, one mod at a time", "INFO")
        
        # Process mods one at a time
        for idx, mod_dir in enumerate(mod_dirs, 1):
            if not mod_dir.exists():
                print_status(f"[{idx}/{len(mod_dirs)}] Mod not found: {mod_dir}", "ERROR")
                continue
            
            print_section_header(f"MOD {idx} of {len(mod_dirs)} : {mod_dir.name}", Colors.YELLOW)
            
            # Load error logs for this mod if not already loaded
            if not fixer.error_logs_cache:
                fixer._load_error_logs(mod_name=mod_dir.name)
            
            # Handle natural language issue fixing
            if hasattr(args, 'issue') and args.issue:
                # Initialize natural language fixer
                if not hasattr(fixer, 'natural_language_fixer'):
                    fixer.natural_language_fixer = NaturalLanguageFixer(fixer)
                
                # Get target file if specified
                target_file = getattr(args, 'file', None)
                
                # Create backup before fixing
                backup_path = mod_dir.parent / f"{mod_dir.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    shutil.copytree(mod_dir, backup_path)
                    print_status(f"Backup created: {backup_path.name}", "SUCCESS")
                except Exception as e:
                    print_status(f"Failed to create backup: {e}", "WARNING")
                
                # Fix using natural language description
                result = fixer.natural_language_fixer.fix_from_description(
                    mod_dir,
                    args.issue,
                    target_file=target_file,
                    create_backup=False  # Already created above
                )
                
                if result.get('success'):
                    print_status(f"Natural language fix completed for {mod_dir.name}", "SUCCESS")
                else:
                    print_status(f"Natural language fix failed: {result.get('error', 'Unknown error')}", "ERROR")
                
                continue  # Skip standard fixing for natural language mode
            
            # Always create backups before making changes (ignore --no-backup flag)
            # Backups are kept in case AI makes mistakes
            if args.analyze_only:
                # Just analyze - no backup needed
                analysis = fixer.analyzer.analyze_mod(mod_dir)
                print(f"\nAnalysis for {mod_dir.name}:")
                print(f"  API issues: {len(analysis.api_issues)}")
                print(f"  Asset issues: {len(analysis.asset_issues)}")
                print(f"  Harmony patches: {len(analysis.harmony_patches)}")
            else:
                # Check if mod has issues before prompting
                analysis = fixer.analyzer.analyze_mod(mod_dir)
                total_issues = len(analysis.api_issues) + len(analysis.asset_issues)
                
                if total_issues == 0:
                    print_status(f"No issues found in {mod_dir.name}. Skipping", "INFO")
                    continue
                
                # Prompt for confirmation (defaults to yes after timeout)
                prompt_msg = (
                    f"Fix {total_issues} issue(s) in '{mod_dir.name}'?\n"
                    f"  - {len(analysis.api_issues)} API issue(s)\n"
                    f"  - {len(analysis.asset_issues)} asset issue(s)\n"
                    f"  A backup will be created before making any changes."
                )
                
                if not prompt_with_timeout(prompt_msg, timeout=5.0, default="y"):
                    print_status(f"Skipping {mod_dir.name}", "WARNING")
                    continue
                
                # Always create backup before fixing (safety measure)
                print_status("Creating backup of mod before making changes...", "PROCESSING")
                print(f"  [WHY]    Backups are kept in case AI makes mistakes", Colors.GRAY)
                backup_path = mod_dir.parent / f"{mod_dir.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    shutil.copytree(mod_dir, backup_path)
                    print_status(f"Backup created: {backup_path.name}", "SUCCESS")
                except Exception as e:
                    print_status(f"Failed to create backup: {e}", "WARNING")
                    # Ask again if backup fails
                    if not prompt_with_timeout("  Continue without backup? (not recommended)", timeout=3.0, default="n"):
                        print_status(f"Skipping {mod_dir.name} (backup required)", "WARNING")
                        continue
                
                # Fix the mod (backup already created above)
                results = fixer.fix_mod(mod_dir, create_backup=False)
                
                print(f"\nFix results for {mod_dir.name}:")
                successful = sum(1 for r in results if r.success)
                print(f"  Fixed {successful}/{len(results)} files")
                
                if successful > 0:
                    print_status(f"Backup available at: {backup_path.name}", "SUCCESS")
                
                for result in results:
                    if result.success:
                        safe_print(f"    [OK] {Path(result.file_path).name}") if TOOL_HELPERS_AVAILABLE else print(f"    [OK] {Path(result.file_path).name}")
                    else:
                        safe_print(f"    [FAIL] {Path(result.file_path).name}: {', '.join(result.errors)}") if TOOL_HELPERS_AVAILABLE else print(f"    [FAIL] {Path(result.file_path).name}: {', '.join(result.errors)}")
    except Exception as e:
        print("\n" + "=" * 60)
        print("ERROR: An error occurred in _main_impl:")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        print("=" * 60)
        print("")
        try:
            input("Press Enter to exit...")
        except (EOFError, KeyboardInterrupt):
            pass
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("")
        try:
            input("Press Enter to exit...")
        except:
            pass
        sys.exit(1)

