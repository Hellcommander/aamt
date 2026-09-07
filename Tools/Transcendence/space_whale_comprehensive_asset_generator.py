#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Space Whale Comprehensive Asset Generator
Generates 150 variations of all asset types with detailed AI descriptions and quality checking.

Enhanced Features:
- CPU offload support for high VRAM models (KV cache in RAM)
- Two-stage pipeline (draft/polish models)
- Progress tracking with ETA
- Retry logic for failed tasks
- Performance metrics and timing
- Resume capability for interrupted generation
- Comprehensive error handling and recovery
- Resource monitoring
- Detailed logging
"""

import json
import os
import sys
import datetime
import requests
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
import threading
import subprocess
import time
import traceback

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Shared AI pipeline (SD3.5 / TRELLIS / audio QA)
_TX = Path(__file__).resolve().parent
_SHARED = _TX.parent / "Shared"
for _p in (_TX, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
try:
    import tx_ai_pipeline as tx  # type: ignore
except Exception:
    tx = None  # type: ignore

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class TaskResult:
    """Result of a generation task."""
    name: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: float = 0.0
    retry_count: int = 0
    error: Optional[str] = None
    output_files: List[Path] = field(default_factory=list)
    success: bool = False
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time if task is running."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0

# Load detailed AI description
DETAILED_DESCRIPTION = """
Create a space whale capital ship that combines organic whale anatomy with advanced crystalline technology. 

SILHOUETTE: Streamlined whale shape, 8.0 length × 3.5 width × 2.0 height. Bulbous head with wide mouth opening, elongated cylindrical mid-section with ventral belly bulge, tapering tail with horizontal fin, prominent dorsal crest running along the top.

MATERIALS: Living bioluminescent skin - smooth, slightly translucent organic membrane with dark navy base (#1a2a3a) and bright cyan vein network (#66ccff) that pulses with energy. Crystalline armor plates overlay key sections, semi-transparent with faceted appearance. Subsurface scattering creates soft internal glow.

COLORS: Dark navy base (70%), bright cyan veins (20%), intense white-cyan emissive core (5%), magenta-pink energy accents (5%). High saturation, smooth gradients, strong contrast between dark base and bright glows.

LIGHTING: Glows from within - central Bio-Core pulses rhythmically, energy flows through vein network in waves, six pairs of gill vents pulse with light, dorsal crest glows with bioluminescent patterns. All light uses additive blending for intensity. Emissive intensity 3.5.

DETAILS: Subtle organic wrinkles and folds, very faint scale-like texture, glowing energy runes, crystalline tech nodes at key points, visible energy conduits connecting systems. Procedural noise for organic variation.

STYLE: Nova Drift aesthetic - high-energy glows, smooth additive effects, procedural distortion, particle-driven motion, layered FX composition. Should feel alive, breathing, pulsing with energy.

ANIMATION: Subtle breathing (5% scale variation), tail sweeps horizontally, gill vents pulse rhythmically, vein energy flows in waves. All animations are organic and rhythmic.

SCALE: Massive capital ship presence, feels ancient and evolved, dominates the screen. Should inspire awe and respect.

Render with high detail, smooth surfaces, intense glows, and organic-meets-technological aesthetic. The ship should look like a living creature enhanced with advanced technology, glowing with bioluminescent energy.
"""

def load_detailed_description():
    """Load the detailed AI description from file."""
    desc_path = Path(__file__).parent / "SPACE_WHALE_AI_VISUAL_DESCRIPTION.md"
    if desc_path.exists():
        with open(desc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract the complete prompt section
            if "Complete AI Generation Prompt" in content:
                start = content.find("```", content.find("Complete AI Generation Prompt"))
                end = content.find("```", start + 3)
                if start >= 0 and end > start:
                    return content[start+3:end].strip()
    return DETAILED_DESCRIPTION

# Import model router for dual-model support with CPU offload
_model_router_path = os.path.join(os.path.dirname(__file__), "..", "Common", "ollama_model_router.py")
if os.path.exists(_model_router_path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Common"))
        from ollama_model_router import (
            get_router, get_code_model, get_visual_model,
            TASK_CODE, TASK_VISUAL, TASK_ORCHESTRATION, TASK_AUDIO
        )
        MODEL_ROUTER_AVAILABLE = True
    except ImportError:
        MODEL_ROUTER_AVAILABLE = False
        TASK_CODE = "code"
        TASK_VISUAL = "visual"
        TASK_ORCHESTRATION = "orchestration"
        TASK_AUDIO = "audio"
else:
    MODEL_ROUTER_AVAILABLE = False
    TASK_CODE = "code"
    TASK_VISUAL = "visual"
    TASK_ORCHESTRATION = "orchestration"
    TASK_AUDIO = "audio"

# Model context limits (in tokens, approximate: 1 token ≈ 4 characters)
# Updated for current model recommendations (34B disabled)
MODEL_CONTEXT_LIMITS = {
    # Code models
    'codellama:13b': 8000,   # CodeLlama limit: 8k tokens
    'codellama:7b': 8000,    # CodeLlama limit: 8k tokens
    'codellama:7b-instruct': 8000,
    'qwen2.5-coder:7b': 32768,  # Qwen2.5 supports 32k context
    'qwen2.5-coder:14b': 32768,
    'starcoder:7b': 8192,
    # Visual/General models
    'llama3.1:8b': 128000,   # Llama 3.1 supports 128k context
    'llama3.1:13b': 128000,
    'llama3.2': 128000,
    'llama3': 8192,
    'deepseek-r1:7b': 64000,  # DeepSeek-R1 supports 64k context
    'wizardlm-uncensored:latest': 8192,  # Conservative limit
    'wizardlm-uncensored:13b': 8192,
    'wizardlm-uncensored:7b': 8192,
    'llama2': 4096,  # Llama 2: 4k
}

def get_model_context_limit(model: str) -> int:
    """Get context limit for a model in tokens."""
    # Check exact match first
    if model.lower() in MODEL_CONTEXT_LIMITS:
        return MODEL_CONTEXT_LIMITS[model.lower()]
    
    # Check partial matches for model variants
    model_lower = model.lower()
    for key, value in MODEL_CONTEXT_LIMITS.items():
        if key in model_lower or model_lower in key:
            return value
    
    # Default to 8K for CodeLlama (most restrictive), but other models may be higher
    return 8000

def get_ollama_api_options(model_name: str, router=None, num_thread: int = None, num_predict: int = None, temperature: float = 0.7, top_p: float = 0.9):
    """
    Get Ollama API options with CPU offload configured.
    
    Args:
        model_name: Name of the model
        router: Model router instance (None = get new one)
        num_thread: Number of CPU threads
        num_predict: Max tokens to predict
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
    
    Returns:
        Dictionary with Ollama API options including CPU offload
    """
    if MODEL_ROUTER_AVAILABLE:
        if router is None:
            router = get_router()
        
        # Get options with CPU offload
        options = router.get_ollama_api_options(
            model_name=model_name,
            num_thread=num_thread,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p
        )
        return options
    
    # Fallback: basic options without CPU offload
    options = {
        'temperature': temperature,
        'top_p': top_p
    }
    if num_thread is not None:
        options['num_thread'] = num_thread
    if num_predict is not None:
        options['num_predict'] = num_predict
    
    return options

def detect_best_ollama_model(task_type: str = TASK_VISUAL, use_draft: bool = False, use_polish: bool = False):
    """
    Auto-detect the best available Ollama model for a specific task type.
    Supports draft/polish two-stage pipeline for better quality.
    
    Args:
        task_type: Task type (TASK_CODE, TASK_VISUAL, TASK_ORCHESTRATION, TASK_AUDIO)
        use_draft: Use draft model (7B, fast iterations)
        use_polish: Use polish model (8B+, final quality)
    
    Returns:
        Model name to use
    """
    if MODEL_ROUTER_AVAILABLE:
        router = get_router()
        
        # Use two-stage pipeline if requested
        if use_draft:
            task_str = "code" if task_type == TASK_CODE else "visual"
            model = router.get_draft_model(task_str)
            if model:
                return model
        elif use_polish:
            task_str = "code" if task_type == TASK_CODE else "visual"
            model = router.get_polish_model(task_str)
            if model:
                return model
        
        router.print_model_assignment()  # Show model assignments
        return router.get_model_for_task(task_type)
    
    # Fallback to old detection method
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            # Priority: 13-14B > 8B > 7B (34B disabled)
            for model in models:
                name = model.get('name', '').lower()
                if 'codellama' in name and ('13b' in name or '13' in name or '14b' in name or '14' in name):
                    return model.get('name')
                elif 'codellama' in name and ('8b' in name or '8' in name):
                    return model.get('name')
                elif 'codellama' in name and ('7b' in name or '7' in name):
                    return model.get('name')
                elif 'wizardlm' in name and 'uncensored' in name:
                    return model.get('name')
    except:
        pass
    return "codellama:7b"  # Fallback to 7B (34B disabled)

def check_resume_capability(output_dir: Path) -> Dict[str, bool]:
    """Check which tasks can be resumed (output files already exist)."""
    resume_status = {}
    
    # Check Visual Language
    visual_file = output_dir / "VisualLanguage" / "ollama_palette_variations.json"
    resume_status['visual'] = visual_file.exists()
    
    # Check FX Assets
    fx_best = output_dir.parent / "space_whale_fx_registry_best.json"
    fx_placeholders = output_dir.parent / "space_whale_fx_registry_placeholders.json"
    resume_status['fx'] = fx_best.exists() or fx_placeholders.exists()
    
    # Check Audio Assets
    audio_dir = output_dir / "Audio"
    resume_status['audio'] = audio_dir.exists() and any(audio_dir.rglob("*.wav"))
    
    # Check Textures
    texture_dir = output_dir / "Textures"
    resume_status['textures'] = texture_dir.exists() and any(texture_dir.rglob("*.png"))
    
    return resume_status

def generate_comprehensive_assets(ollama_model: str = None, ollama_code_model: str = None, output_dir: str = None, ship_id: str = None, variations: int = 150, max_workers: int = None, max_threads: int = None, resume: bool = False, skip_completed: bool = False):
    """
    Generate all comprehensive assets for Space Whale (multithreaded).
    Uses dual-model support with CPU offload for high VRAM models.
    
    Args:
        ollama_model: Ollama model for visual/orchestration tasks (None = auto-detect)
        ollama_code_model: Ollama model for code generation tasks (None = auto-detect)
        output_dir: Output directory path (None = use default)
        ship_id: Specific ship ID to generate assets for (None = all ships in registry)
        variations: Number of variations to generate per asset type (default: 150)
        max_workers: Maximum parallel tasks (None = auto-detect from CPU)
        max_threads: Maximum worker threads per task (None = auto-detect from CPU)
        resume: Resume interrupted generation (skip completed tasks)
        skip_completed: Skip tasks that already have output files
    """
    if tx:
        tx.print_probe()
        tx.prepare(image=True, mesh=True, keep_server=False)

    # Initialize model router with CPU offload support
    router = None
    if MODEL_ROUTER_AVAILABLE:
        router = get_router()
        router.print_model_assignment()
        
        # Show CPU offload status
        if router.enable_cpu_offload:
            print(f"\nCPU Offload: Enabled for high VRAM models (KV cache in RAM)")
            if ollama_model:
                offload = router.get_cpu_offload_settings(ollama_model)
                if offload:
                    print(f"  Visual model ({ollama_model}): {offload.get('num_gpu')} GPU layers (attention cache offloaded to RAM)")
            if ollama_code_model:
                offload = router.get_cpu_offload_settings(ollama_code_model)
                if offload:
                    print(f"  Code model ({ollama_code_model}): {offload.get('num_gpu')} GPU layers (attention cache offloaded to RAM)")
    
    # Auto-detect models if not specified (use polish models for better quality)
    if ollama_model is None:
        ollama_model = detect_best_ollama_model(TASK_VISUAL, use_polish=True)
        print(f"Auto-detected Visual/Orchestration model: {ollama_model}")
    else:
        print(f"Using specified Visual/Orchestration model: {ollama_model}")
    
    if ollama_code_model is None:
        ollama_code_model = detect_best_ollama_model(TASK_CODE, use_polish=True)
        print(f"Auto-detected Code Generation model: {ollama_code_model}")
    else:
        print(f"Using specified Code Generation model: {ollama_code_model}")
    
    detailed_desc = load_detailed_description()
    base_dir = Path(__file__).parent
    # Use provided output directory, or environment variable, or default
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir_env = os.environ.get("SPACE_WHALE_OUTPUT_DIR")
        if output_dir_env:
            output_dir = Path(output_dir_env)
        else:
            output_dir = base_dir / "Output" / "SpaceWhaleAssets"  # Match PowerShell script default
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check resume capability
    resume_status = check_resume_capability(output_dir)
    if resume or skip_completed:
        completed_tasks = [name for name, exists in resume_status.items() if exists]
        if completed_tasks:
            log_message(f"Resume mode: Found existing outputs for {len(completed_tasks)} tasks: {', '.join(completed_tasks)}", "INFO")
            if skip_completed:
                log_message("Skipping completed tasks", "INFO")
    
    # Determine optimal thread count (up to 32 cores)
    # Check environment variables first (set by PowerShell GUI for dynamic scaling)
    if max_workers is None:
        max_workers = int(os.environ.get("SPACE_WHALE_MAX_WORKERS", "4"))
    if max_threads is None:
        max_threads = int(os.environ.get("SPACE_WHALE_MAX_THREADS", str(min(32, cpu_count()))))
    
    # Ensure reasonable limits
    max_workers = max(1, min(max_workers, 8))  # Cap at 8 parallel tasks
    max_threads = max(1, min(max_threads, 32))  # Cap at 32 threads per task
    total_cores = min(max_threads, cpu_count())
    
    print("=" * 80)
    print("Space Whale Comprehensive Asset Generator (Multithreaded)")
    print("=" * 80)
    print(f"\nUsing detailed AI description ({len(detailed_desc)} characters)")
    print(f"Output directory: {output_dir}")
    print(f"Parallel generator tasks: {max_workers}")
    print(f"Available CPU cores: {total_cores}")
    print(f"Worker threads per task: {max_threads}")
    print(f"Total concurrent threads: {max_workers * max_threads}")
    print(f"\nGenerating {variations} variations of each asset type...")
    if ship_id:
        print(f"Ship ID filter: {ship_id}")
    
    # Display model context limits
    visual_limit = get_model_context_limit(ollama_model)
    code_limit = get_model_context_limit(ollama_code_model)
    print(f"\nModel Context Limits:")
    print(f"  Visual/Orchestration model ({ollama_model}): {visual_limit:,} tokens")
    print(f"  Code Generation model ({ollama_code_model}): {code_limit:,} tokens")
    print("=" * 80)
    
    # Performance tracking
    start_time = time.time()
    task_results: Dict[str, TaskResult] = {
        'visual': TaskResult(name='Visual Language'),
        'fx': TaskResult(name='FX Assets'),
        'audio': TaskResult(name='Audio Assets'),
        'textures': TaskResult(name='Textures'),
        'quality': TaskResult(name='Quality Check')
    }
    results_lock = threading.Lock()
    
    # Log file for detailed tracking
    log_file = output_dir / "generation_log.txt"
    log_lock = threading.Lock()
    
    def log_message(message: str, level: str = "INFO"):
        """Thread-safe logging to both console and file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Print to console
        print(message)
        
        # Write to log file
        with log_lock:
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass  # Don't fail if logging fails
    
    def run_task_with_retry(task_name: str, task_func, max_retries: int = 3, timeout: int = 3600):
        """Run a task with retry logic and progress tracking."""
        task_result = task_results[task_name]
        task_result.status = TaskStatus.RUNNING
        task_result.start_time = time.time()
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                task_result.status = TaskStatus.RETRYING
                task_result.retry_count = attempt
                log_message(f"  → Retrying {task_result.name} (attempt {attempt + 1}/{max_retries + 1})...", "RETRY")
                time.sleep(5 * attempt)  # Exponential backoff
            
            try:
                success = task_func()
                if success:
                    task_result.status = TaskStatus.COMPLETED
                    task_result.end_time = time.time()
                    task_result.duration = task_result.elapsed_time
                    task_result.success = True
                    log_message(f"  ✓ {task_result.name} completed in {task_result.duration:.1f}s", "SUCCESS")
                    return True
                else:
                    task_result.error = f"Task returned failure (attempt {attempt + 1})"
            except subprocess.TimeoutExpired:
                task_result.error = f"Task timed out after {timeout}s (attempt {attempt + 1})"
                log_message(f"  ✗ {task_result.name} timed out (attempt {attempt + 1})", "ERROR")
            except Exception as e:
                task_result.error = f"{type(e).__name__}: {str(e)} (attempt {attempt + 1})"
                log_message(f"  ✗ {task_result.name} error: {e} (attempt {attempt + 1})", "ERROR")
                if attempt < max_retries:
                    log_message(f"    Traceback: {traceback.format_exc()[:500]}", "DEBUG")
        
        # All retries failed
        task_result.status = TaskStatus.FAILED
        task_result.end_time = time.time()
        task_result.duration = task_result.elapsed_time
        log_message(f"  ✗ {task_result.name} failed after {max_retries + 1} attempts", "ERROR")
        return False
    
    def run_visual_language():
        """Generate Visual Language Assets using SpaceWhaleVisualLanguageGenerator."""
        # Skip if resume mode and already completed
        if skip_completed and resume_status.get('visual', False):
            log_message(f"  ⊘ Skipping Visual Language (already exists)", "INFO")
            task_results['visual'].status = TaskStatus.COMPLETED
            task_results['visual'].success = True
            task_results['visual'].start_time = time.time()
            task_results['visual'].end_time = time.time()
            return True
        
        # Use SpaceWhaleVisualLanguageGenerator.bat (or .ps1 if .bat not available)
        visual_bat = base_dir / "SpaceWhaleVisualLanguageGenerator.bat"
        visual_ps1 = base_dir / "SpaceWhaleVisualLanguageGenerator.ps1"
        
        if not visual_bat.exists() and not visual_ps1.exists():
            log_message(f"  ✗ Visual Language generator not found: {visual_bat} or {visual_ps1}", "ERROR")
            return False
        
        log_message(f"  → Starting Visual Language generator...", "INFO")
        log_message(f"     Variations: {variations}", "INFO")
        
        # Build registry and output paths
        registry_file = base_dir / "space_whale_visual_language_registry.json"
        output_path = output_dir / "VisualLanguage"
        
        if not registry_file.exists():
            log_message(f"  ✗ Visual Language registry not found: {registry_file}", "ERROR")
            return False
        
        try:
            # Use .bat file if available, otherwise use PowerShell directly
            if visual_bat.exists():
                visual_args = [
                    str(visual_bat),
                    "-RegistryPath", str(registry_file),
                    "-OutputDir", str(output_path)
                ]
                # Run batch file
                result = subprocess.run(visual_args, timeout=3600, 
                                      capture_output=False, text=True, shell=True)
            else:
                # Use PowerShell directly
                visual_args = [
                    "pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(visual_ps1),
                    "-RegistryPath", str(registry_file),
                    "-OutputDir", str(output_path)
                ]
                result = subprocess.run(visual_args, timeout=3600, 
                                      capture_output=False, text=True)
            
            # Check for output files
            if output_path.exists():
                # Check for any generated files (JSON, images, etc.)
                json_files = list(output_path.glob("*.json"))
                if json_files:
                    for json_file in json_files:
                        task_results['visual'].output_files.append(json_file)
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log_message(f"  ✗ Visual Language generator timed out", "ERROR")
            raise
        except Exception as e:
            log_message(f"  ✗ Visual Language generator error: {e}", "ERROR")
            raise
    
    def run_fx_assets():
        """Generate FX Assets (150 variations)."""
        # Skip if resume mode and already completed
        if skip_completed and resume_status.get('fx', False):
            log_message(f"  ⊘ Skipping FX Assets (already exists)", "INFO")
            task_results['fx'].status = TaskStatus.COMPLETED
            task_results['fx'].success = True
            task_results['fx'].start_time = time.time()
            task_results['fx'].end_time = time.time()
            return True
        
        fx_script = base_dir / "space_whale_fx_variation_generator.py"
        if not fx_script.exists():
            log_message(f"  ✗ FX Assets script not found: {fx_script}", "ERROR")
            return False
        
        log_message(f"  → Starting FX Assets generator...", "INFO")
        log_message(f"     Variations: {variations} per effect, 10 effects in parallel", "INFO")
        
        # Set environment variables for CPU offload
        env = os.environ.copy()
        if router:
            offload_opts = router.get_cpu_offload_settings(ollama_model)
            if offload_opts:
                env['OLLAMA_NUM_GPU'] = str(offload_opts.get('num_gpu'))
        
        fx_args = [
            sys.executable, str(fx_script),
            "space_whale_fx_registry.json", str(variations), "10"
        ]
        
        try:
            result = subprocess.run(fx_args, env=env, timeout=3600,
                                  capture_output=False, text=True)
            
            # Check for output files
            fx_best = base_dir / "space_whale_fx_registry_best.json"
            fx_placeholders = base_dir / "space_whale_fx_registry_placeholders.json"
            for fx_file in [fx_best, fx_placeholders]:
                if fx_file.exists():
                    task_results['fx'].output_files.append(fx_file)
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log_message(f"  ✗ FX Assets generator timed out", "ERROR")
            raise
        except Exception as e:
            log_message(f"  ✗ FX Assets generator error: {e}", "ERROR")
            raise
    
    def run_audio_assets():
        """Generate Audio Assets."""
        # Skip if resume mode and already completed
        if skip_completed and resume_status.get('audio', False):
            log_message(f"  ⊘ Skipping Audio Assets (already exists)", "INFO")
            task_results['audio'].status = TaskStatus.COMPLETED
            task_results['audio'].success = True
            task_results['audio'].start_time = time.time()
            task_results['audio'].end_time = time.time()
            return True
        
        audio_script = base_dir / "space_whale_audio_generator.py"
        if not audio_script.exists():
            log_message(f"  ✗ Audio Assets script not found: {audio_script}", "ERROR")
            return False
        
        log_message(f"  → Starting Audio Assets generator...", "INFO")
        log_message(f"     Variations: {variations} per sound", "INFO")
        
        # Set environment variables for CPU offload
        env = os.environ.copy()
        if router:
            offload_opts = router.get_cpu_offload_settings(ollama_model)
            if offload_opts:
                env['OLLAMA_NUM_GPU'] = str(offload_opts.get('num_gpu'))
        
        audio_args = [
            sys.executable, str(audio_script),
            "--registry", "space_whale_audio_registry.json",
            "--output", str(output_dir / "Audio"),
            "--variations", str(variations)
        ]
        
        try:
            result = subprocess.run(audio_args, env=env, timeout=1800,
                                  capture_output=False, text=True)
            
            # Check for output files
            audio_dir = output_dir / "Audio"
            if audio_dir.exists():
                for audio_file in audio_dir.rglob("*.wav"):
                    task_results['audio'].output_files.append(audio_file)
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log_message(f"  ✗ Audio Assets generator timed out", "ERROR")
            raise
        except Exception as e:
            log_message(f"  ✗ Audio Assets generator error: {e}", "ERROR")
            raise
    
    def run_textures():
        """Generate Textures for Rigging."""
        # Skip if resume mode and already completed
        if skip_completed and resume_status.get('textures', False):
            log_message(f"  ⊘ Skipping Textures (already exists)", "INFO")
            task_results['textures'].status = TaskStatus.COMPLETED
            task_results['textures'].success = True
            task_results['textures'].start_time = time.time()
            task_results['textures'].end_time = time.time()
            return True
        
        texture_script = base_dir / "space_whale_texture_generator.py"
        ship_registry = base_dir / "space_whale_ship_example.json"
        visual_registry = base_dir / "space_whale_visual_language_registry.json"
        skinning_registry = base_dir / "space_whale_skinning_registry.json"
        
        if not texture_script.exists():
            log_message(f"  ✗ Texture generator script not found: {texture_script}", "ERROR")
            return False
        
        missing_files = [f for f in [ship_registry, visual_registry, skinning_registry] if not f.exists()]
        if missing_files:
            log_message(f"  ✗ Texture generation skipped: Missing files: {[f.name for f in missing_files]}", "WARNING")
            return False
        
        log_message(f"  → Starting Texture generator...", "INFO")
        log_message(f"     Generating textures for rigging and spritesheet generation", "INFO")
        
        # Set environment variables for CPU offload
        env = os.environ.copy()
        if router:
            offload_opts = router.get_cpu_offload_settings(ollama_code_model)
            if offload_opts:
                env['OLLAMA_NUM_GPU'] = str(offload_opts.get('num_gpu'))
        
        texture_args = [
            sys.executable, str(texture_script),
            "--ship-registry", str(ship_registry),
            "--visual-registry", str(visual_registry),
            "--skinning-registry", str(skinning_registry),
            "--output", str(output_dir / "Textures")
        ]
        
        try:
            result = subprocess.run(texture_args, env=env, capture_output=True, text=True, timeout=600)
            
            # Check for output files
            texture_dir = output_dir / "Textures"
            if texture_dir.exists():
                for texture_file in texture_dir.rglob("*.png"):
                    task_results['textures'].output_files.append(texture_file)
            
            if result.returncode == 0:
                return True
            else:
                if result.stderr:
                    log_message(f"  ✗ Texture generation error: {result.stderr[:500]}", "ERROR")
                if result.stdout:
                    log_message(f"  Output: {result.stdout[:500]}", "DEBUG")
                return False
        except subprocess.TimeoutExpired:
            log_message(f"  ✗ Texture generator timed out", "ERROR")
            raise
        except Exception as e:
            log_message(f"  ✗ Texture generator error: {e}", "ERROR")
            raise
    
    # Initialize log file
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Space Whale Comprehensive Asset Generation Log\n")
        f.write(f"Started: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Models: Visual={ollama_model}, Code={ollama_code_model}\n")
        f.write(f"Variations: {variations}\n")
        f.write(f"Output: {output_dir}\n")
        f.write("=" * 80 + "\n\n")
    
    # Run tasks in parallel with retry logic
    log_message("\n[1-4/5] Running all generators in parallel...", "INFO")
    log_message(f"Using {max_workers} parallel tasks with up to {max_threads} threads each", "INFO")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            'visual': executor.submit(run_task_with_retry, 'visual', run_visual_language, max_retries=2),
            'fx': executor.submit(run_task_with_retry, 'fx', run_fx_assets, max_retries=2),
            'audio': executor.submit(run_task_with_retry, 'audio', run_audio_assets, max_retries=2),
            'textures': executor.submit(run_task_with_retry, 'textures', run_textures, max_retries=2, timeout=600)
        }
        
        # Monitor progress
        completed = 0
        total = len(futures)
        
        for name, future in futures.items():
            try:
                success = future.result()
                completed += 1
                task_result = task_results[name]
                status_icon = "✓" if success else "✗"
                log_message(f"  [{completed}/{total}] {status_icon} {task_result.name}: {task_result.status.value} ({task_result.duration:.1f}s)", 
                          "SUCCESS" if success else "ERROR")
            except Exception as e:
                completed += 1
                task_result = task_results[name]
                task_result.error = str(e)
                task_result.status = TaskStatus.FAILED
                log_message(f"  [{completed}/{total}] ✗ {task_result.name}: Exception - {e}", "ERROR")
    
    # Filter out low-quality assets (score < 17) before quality check
    log_message("\n[4.5/5] Filtering low-quality assets (score < 17)...", "INFO")
    filter_low_quality_assets(
        output_dir, 
        min_score=17, 
        log_message=log_message,
        ollama_url="http://localhost:11434",
        ollama_model=ollama_model  # Use visual model for audio assessment too
    )
    
    # 5. Quality Check and Report (sequential, needs all results)
    log_message("\n[5/5] Quality Checking and Reporting...", "INFO")
    task_results['quality'].status = TaskStatus.RUNNING
    task_results['quality'].start_time = time.time()
    
    # Use dedicated quality checker script if available
    quality_checker_script = base_dir / "space_whale_quality_checker.py"
    if quality_checker_script.exists():
        log_message(f"  → Running dedicated quality checker...", "INFO")
        try:
            quality_args = [
                sys.executable, str(quality_checker_script),
                "--output-dir", str(output_dir)
            ]
            result = subprocess.run(quality_args, timeout=600, capture_output=True, text=True)
            if result.returncode == 0:
                task_results['quality'].status = TaskStatus.COMPLETED
                task_results['quality'].success = True
                log_message(f"  ✓ Quality check complete", "SUCCESS")
                if result.stdout:
                    # Show summary from quality checker
                    lines = result.stdout.split('\n')
                    for line in lines[-10:]:  # Last 10 lines usually contain summary
                        if line.strip():
                            log_message(f"    {line}", "INFO")
            else:
                log_message(f"  ⚠ Quality checker had issues, using fallback...", "WARNING")
                if result.stderr:
                    log_message(f"    Error: {result.stderr[:200]}", "ERROR")
                quality_check_all_assets(output_dir)  # Fallback
        except Exception as e:
            log_message(f"  ⚠ Quality checker error: {e}, using fallback...", "WARNING")
            quality_check_all_assets(output_dir)  # Fallback
    else:
        # Fallback to built-in quality check
        quality_check_all_assets(output_dir)
    
    task_results['quality'].end_time = time.time()
    task_results['quality'].duration = task_results['quality'].elapsed_time
    
    # Generate summary report
    total_time = time.time() - start_time
    generate_summary_report(output_dir, task_results, total_time, variations, ollama_model, ollama_code_model)
    
    log_message("\n" + "=" * 80, "INFO")
    log_message("Comprehensive Asset Generation Complete!", "SUCCESS")
    log_message("=" * 80, "INFO")
    log_message(f"\nTotal generation time: {total_time:.1f}s ({total_time/60:.1f} minutes)", "INFO")
    log_message(f"All assets saved to: {output_dir}", "INFO")
    log_message(f"Detailed log: {log_file}", "INFO")
    log_message("\nNext steps:", "INFO")
    log_message("  1. Review quality reports in output directory", "INFO")
    log_message("  2. Review generation summary report", "INFO")
    log_message("  3. Select best variations for each asset type", "INFO")
    log_message("  4. Generate final spritesheets with Blender", "INFO")
    log_message("  5. Export to Transcendence XML format", "INFO")

def generate_summary_report(output_dir: Path, task_results: Dict[str, TaskResult], 
                           total_time: float, variations: int, visual_model: str, code_model: str):
    """Generate comprehensive summary report."""
    report_path = output_dir / "GENERATION_SUMMARY.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Space Whale Asset Generation Summary\n\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Configuration\n\n")
        f.write(f"- **Visual Model:** {visual_model}\n")
        f.write(f"- **Code Model:** {code_model}\n")
        f.write(f"- **Variations per asset:** {variations}\n")
        f.write(f"- **Total generation time:** {total_time:.1f}s ({total_time/60:.1f} minutes)\n\n")
        
        f.write("## Task Results\n\n")
        f.write("| Task | Status | Duration | Retries | Output Files |\n")
        f.write("|------|--------|----------|---------|-------------|\n")
        
        for task_name, result in task_results.items():
            status_icon = "✓" if result.success else "✗"
            status_text = result.status.value.upper()
            duration = f"{result.duration:.1f}s" if result.duration > 0 else "N/A"
            retries = str(result.retry_count) if result.retry_count > 0 else "0"
            file_count = len(result.output_files)
            
            f.write(f"| {result.name} | {status_icon} {status_text} | {duration} | {retries} | {file_count} |\n")
        
        f.write("\n## Performance Metrics\n\n")
        successful_tasks = [r for r in task_results.values() if r.success]
        failed_tasks = [r for r in task_results.values() if not r.success]
        
        f.write(f"- **Successful tasks:** {len(successful_tasks)}/{len(task_results)}\n")
        f.write(f"- **Failed tasks:** {len(failed_tasks)}/{len(task_results)}\n")
        
        if successful_tasks:
            avg_duration = sum(r.duration for r in successful_tasks) / len(successful_tasks)
            f.write(f"- **Average task duration:** {avg_duration:.1f}s\n")
        
        total_files = sum(len(r.output_files) for r in task_results.values())
        f.write(f"- **Total output files:** {total_files}\n")
        
        if failed_tasks:
            f.write("\n## Errors\n\n")
            for result in failed_tasks:
                f.write(f"### {result.name}\n\n")
                f.write(f"- **Error:** {result.error or 'Unknown error'}\n")
                f.write(f"- **Retries:** {result.retry_count}\n\n")
        
        f.write("\n## Output Files\n\n")
        for task_name, result in task_results.items():
            if result.output_files:
                f.write(f"### {result.name}\n\n")
                for file_path in result.output_files[:20]:  # Limit to first 20
                    f.write(f"- `{file_path.relative_to(output_dir) if file_path.is_relative_to(output_dir) else file_path}`\n")
                if len(result.output_files) > 20:
                    f.write(f"- ... and {len(result.output_files) - 20} more files\n")
                f.write("\n")
    
    log_message(f"  ✓ Summary report saved: {report_path}", "SUCCESS")

def filter_low_quality_assets(output_dir: Path, min_score: int = 17, log_message=None, 
                             ollama_url: str = "http://localhost:11434", ollama_model: str = None):
    """
    Filter out assets with quality scores below the minimum threshold.
    Only saves assets with scores >= min_score (default: 17).
    
    Args:
        output_dir: Output directory containing generated assets
        min_score: Minimum quality score to keep (default: 17)
        log_message: Optional logging function (default: print)
        ollama_url: Ollama API URL for audio assessment
        ollama_model: Ollama model name for audio assessment
    """
    if log_message is None:
        log_message = lambda msg, level="INFO": print(f"[{level}] {msg}")
    
    # Import audio quality assessment from Shared directory
    AUDIO_QA_AVAILABLE = False
    batch_assess_audio_quality = None
    filter_audio_by_quality = None
    try:
        # Try importing from Shared directory (parent/Shared)
        shared_path = os.path.join(os.path.dirname(__file__), "..", "Shared")
        if shared_path not in sys.path:
            sys.path.insert(0, shared_path)
        from audio_quality_assessment import (
            batch_assess_audio_quality, filter_audio_by_quality
        )
        AUDIO_QA_AVAILABLE = True
    except ImportError:
        # Fallback to local import (for backward compatibility)
        try:
            from space_whale_audio_quality_assessment import (
                batch_assess_audio_quality, filter_audio_by_quality
            )
            AUDIO_QA_AVAILABLE = True
        except ImportError:
            log_message("  Audio quality assessment not available (optional)", "INFO")
    # Import 20-level quality system
    try:
        from space_whale_quality_system import get_quality_threshold
        QUALITY_20_AVAILABLE = True
    except ImportError:
        QUALITY_20_AVAILABLE = False
    
    filtered_count = 0
    total_count = 0
    
    # Filter Visual Language
    visual_file = output_dir / "VisualLanguage" / "ollama_palette_variations.json"
    if visual_file.exists():
        with open(visual_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            variations = data.get('variations', [])
            visual_total = len(variations)
            total_count += visual_total
            
            filtered_variations = []
            visual_filtered = 0
            for v in variations:
                quality_data = v.get('quality', {})
                score = quality_data.get('overallScore', quality_data.get('score', 0))
                # Convert legacy 0-5 scale to 1-20 if needed
                if QUALITY_20_AVAILABLE and isinstance(score, float) and score <= 5.0:
                    score = int(score * 4 + 1)
                
                # Only keep items with score >= min_score
                if score >= min_score:
                    filtered_variations.append(v)
                else:
                    visual_filtered += 1
                    filtered_count += 1
            
            # Save filtered data
            data['variations'] = filtered_variations
            data['filtered_count'] = visual_filtered
            data['min_score_threshold'] = min_score
            
            with open(visual_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log_message(f"  Filtered Visual Language: {len(filtered_variations)}/{visual_total} kept (removed {visual_filtered} with score < {min_score})", "INFO")
    
    # Filter FX Assets
    fx_best = output_dir.parent / "space_whale_fx_registry_best.json"
    fx_placeholders = output_dir.parent / "space_whale_fx_registry_placeholders.json"
    
    for fx_file in [fx_best, fx_placeholders]:
        if fx_file.exists():
            with open(fx_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                effects = data.get('effects', [])
                
                fx_filtered = 0
                fx_total = 0
                
                for effect in effects:
                    variations = effect.get('variations', [])
                    fx_total += len(variations)
                    
                    filtered_vars = []
                    for var in variations:
                        quality_data = var.get('quality', {})
                        score = quality_data.get('overallScore', quality_data.get('score', 0))
                        # Convert legacy 0-5 scale to 1-20 if needed
                        if QUALITY_20_AVAILABLE and isinstance(score, float) and score <= 5.0:
                            score = int(score * 4 + 1)
                        
                        # Only keep items with score >= min_score
                        if score >= min_score:
                            filtered_vars.append(var)
                        else:
                            fx_filtered += 1
                    
                    effect['variations'] = filtered_vars
                
                total_count += fx_total
                filtered_count += fx_filtered
                
                # Save filtered data
                data['filtered_count'] = fx_filtered
                data['min_score_threshold'] = min_score
                
                with open(fx_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                log_message(f"  Filtered FX Assets ({fx_file.name}): {fx_total - fx_filtered}/{fx_total} kept (removed {fx_filtered} with score < {min_score})", "INFO")
    
    # Filter Audio Assets using hybrid quality assessment
    audio_dir = output_dir / "Audio"
    if audio_dir.exists() and AUDIO_QA_AVAILABLE:
        audio_files = list(audio_dir.rglob("*.wav")) + list(audio_dir.rglob("*.ogg"))
        if audio_files:
            log_message(f"  Assessing audio quality for {len(audio_files)} files...", "INFO")
            try:
                # Use provided model or default
                audio_model = ollama_model if ollama_model else "llama3.1:8b"
                
                assessments, audio_total, audio_filtered = batch_assess_audio_quality(
                    audio_dir,
                    min_score=min_score,
                    ollama_url=ollama_url,
                    ollama_model=audio_model,
                    log_message=log_message
                )
                
                if audio_filtered > 0:
                    removed = filter_audio_by_quality(audio_dir, assessments, min_score, log_message)
                    total_count += audio_total
                    filtered_count += removed
                    log_message(f"  Filtered Audio Assets: {audio_total - removed}/{audio_total} kept (removed {removed} with score < {min_score})", "INFO")
                else:
                    log_message(f"  Audio Assets: All {audio_total} files meet quality threshold", "SUCCESS")
            except Exception as e:
                log_message(f"  Error assessing audio quality: {e}", "ERROR")
                log_message(f"  Audio files will not be filtered", "WARNING")
    
    if total_count > 0:
        log_message(f"  Total filtered: {filtered_count}/{total_count} items removed (score < {min_score})", "INFO")
        log_message(f"  Kept: {total_count - filtered_count}/{total_count} items (score >= {min_score})", "SUCCESS")
    else:
        log_message(f"  No assets found to filter", "INFO")

def quality_check_all_assets(output_dir: Path):
    """Quality check all generated assets and report on scores below production threshold (17/20 = 85%)."""
    
    # Import 20-level quality system
    try:
        from space_whale_quality_system import get_quality_threshold
        PRODUCTION_THRESHOLD = get_quality_threshold("production")  # 17/20 (85% - EXCELLENT tier)
        QUALITY_20_AVAILABLE = True
    except ImportError:
        PRODUCTION_THRESHOLD = 8.0  # Legacy threshold
        QUALITY_20_AVAILABLE = False
    
    reports = []
    
    # Check Visual Language
    visual_file = output_dir / "VisualLanguage" / "ollama_palette_variations.json"
    if visual_file.exists():
        with open(visual_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            variations = data.get('variations', [])
            low_quality = []
            for v in variations:
                quality_data = v.get('quality', {})
                score = quality_data.get('overallScore', quality_data.get('score', 0))
                # Convert legacy 0-5 scale to 1-20 if needed
                if QUALITY_20_AVAILABLE and isinstance(score, float) and score <= 5.0:
                    score = int(score * 4 + 1)
                if score < PRODUCTION_THRESHOLD:
                    low_quality.append(v)
            reports.append({
                'type': 'Visual Language',
                'total': len(variations),
                'low_quality': len(low_quality),
                'details': low_quality[:20]  # First 20 for detail
            })
    
    # Check FX Assets
    fx_best = output_dir.parent / "space_whale_fx_registry_best.json"
    fx_placeholders = output_dir.parent / "space_whale_fx_registry_placeholders.json"
    for fx_file in [fx_best, fx_placeholders]:
        if fx_file.exists():
            with open(fx_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Process FX data structure
                effects = data.get('effects', [])
                total_vars = sum(len(e.get('variations', [])) for e in effects)
                low_quality_vars = []
                for effect in effects:
                    for var in effect.get('variations', []):
                        quality_data = var.get('quality', {})
                        score = quality_data.get('overallScore', quality_data.get('score', 0))
                        # Convert legacy 0-5 scale to 1-20 if needed
                        if QUALITY_20_AVAILABLE and isinstance(score, float) and score <= 5.0:
                            score = int(score * 4 + 1)
                        if score < PRODUCTION_THRESHOLD:
                            low_quality_vars.append({
                                'effect': effect.get('baseId', 'unknown'),
                                'variation': var.get('id', 'unknown'),
                                'score': score,
                                'score_max': 20 if QUALITY_20_AVAILABLE else 5
                            })
                if low_quality_vars:
                    reports.append({
                        'type': f'FX Assets ({fx_file.name})',
                        'total': total_vars,
                        'low_quality': len(low_quality_vars),
                        'details': low_quality_vars[:20]
                    })
    
    # Generate quality report
    threshold_text = f"{PRODUCTION_THRESHOLD}/20" if QUALITY_20_AVAILABLE else f"{PRODUCTION_THRESHOLD:.1f}"
    report_path = output_dir / "QUALITY_REPORT_LOW_SCORES.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Space Whale Asset Quality Report - Below Production Threshold (< {threshold_text})\n\n")
        f.write(f"This report details all generated assets with quality scores below {threshold_text}.\n")
        if QUALITY_20_AVAILABLE:
            f.write(f"**Quality System**: 20-level system (1-20 scale)\n")
            f.write(f"**Production Threshold**: {PRODUCTION_THRESHOLD}/20 (85% - EXCELLENT tier)\n")
        f.write("\n")
        f.write("=" * 80 + "\n\n")
        
        for report in reports:
            f.write(f"## {report['type']}\n\n")
            f.write(f"- **Total Variations**: {report['total']}\n")
            f.write(f"- **Low Quality (< 8.0)**: {report['low_quality']}\n")
            if report['total'] > 0:
                f.write(f"- **Percentage**: {report['low_quality'] / report['total'] * 100:.1f}%\n\n")
            else:
                f.write(f"- **Percentage**: N/A (no variations found)\n\n")
            
            if report['details']:
                f.write("### Detailed Low Quality Results\n\n")
                for i, item in enumerate(report['details'], 1):
                    f.write(f"{i}. ")
                    score_val = item.get('score', 0)
                    score_max = 20 if QUALITY_20_AVAILABLE else 5
                    if QUALITY_20_AVAILABLE:
                        f.write(f"Score: {score_val}/{score_max} - ")
                    else:
                        f.write(f"Score: {score_val:.2f} - ")
                    if 'baseColor' in item:
                        f.write(f"Colors: {item.get('baseColor')} / {item.get('veinColor')}\n")
                    elif 'effect' in item:
                        f.write(f"Effect: {item['effect']}, Variation: {item['variation']}\n")
                    else:
                        f.write(f"{json.dumps(item, indent=2)}\n")
                    f.write("\n")
            
            f.write("\n" + "-" * 80 + "\n\n")
        
        f.write("## Recommendations\n\n")
        if QUALITY_20_AVAILABLE:
            f.write(f"1. Review variations below threshold (< {PRODUCTION_THRESHOLD}/20) and consider regeneration\n")
            f.write(f"2. Focus on production-ready variations (>= {PRODUCTION_THRESHOLD}/20) for production use\n")
            f.write("3. Use filtered placeholders that exclude low-quality variations\n")
            f.write("4. Consider adjusting generation parameters for better results\n")
        else:
            f.write("1. Review low-quality variations and consider regeneration\n")
            f.write("2. Focus on variations with scores >= 8.0 for production use\n")
            f.write("3. Use filtered placeholders that exclude low-quality variations\n")
            f.write("4. Consider adjusting generation parameters for better results\n")
    
    # Use ASCII-safe checkmark for Windows compatibility
    checkmark = "[OK]" if sys.platform == 'win32' and not hasattr(sys.stdout, 'reconfigure') else "✅"
    try:
        print(f"  {checkmark} Quality report saved: {report_path}")
    except UnicodeEncodeError:
        print(f"  [OK] Quality report saved: {report_path}")
    
    # Summary
    total_low = sum(r['low_quality'] for r in reports)
    total_all = sum(r['total'] for r in reports)
    threshold_text = f"{PRODUCTION_THRESHOLD}/20" if QUALITY_20_AVAILABLE else f"{PRODUCTION_THRESHOLD:.1f}"
    
    print(f"\n  Quality Summary:")
    print(f"    Total variations: {total_all}")
    print(f"    Below threshold (< {threshold_text}): {total_low}")
    print(f"    Production ready (>= {threshold_text}): {total_all - total_low}")
    if total_all > 0:
        quality_rate = (total_all - total_low) / total_all * 100
        print(f"    Production ready rate: {quality_rate:.1f}%")
    else:
        print(f"    Production ready rate: N/A (no variations found)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Space Whale Comprehensive Asset Generator")
    parser.add_argument("--ollama-model", type=str, default=None,
                        help="Ollama model to use (None = auto-detect best available). "
                             "Recommended: 'codellama:13b' or 'llama3.1:8b' for visual tasks, 'qwen2.5-coder:7b' for code")
    parser.add_argument("--ollama-code-model", type=str, default=None,
                        help="Ollama model for code generation (None = auto-detect). "
                             "Recommended: 'qwen2.5-coder:7b' or 'codellama:7b-instruct'")
    parser.add_argument("--use-draft", action="store_true",
                        help="Use draft models (7B, fast iterations) instead of polish models")
    parser.add_argument("--use-polish", action="store_true", default=True,
                        help="Use polish models (8B+, final quality) - default")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for generated assets (default: Output/SpaceWhaleAssets)")
    parser.add_argument("--ship-id", type=str, default=None,
                        help="Specific ship ID to generate assets for (default: all ships in registry)")
    parser.add_argument("--variations", type=int, default=150,
                        help="Number of variations to generate per asset type (default: 150)")
    parser.add_argument("--max-workers", type=int, default=None,
                        help="Maximum parallel tasks (default: auto-detect from CPU)")
    parser.add_argument("--max-threads", type=int, default=None,
                        help="Maximum worker threads per task (default: auto-detect from CPU)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume interrupted generation (check for existing outputs)")
    parser.add_argument("--skip-completed", action="store_true",
                        help="Skip tasks that already have output files (use with --resume)")
    args = parser.parse_args()
    generate_comprehensive_assets(
        ollama_model=args.ollama_model,
        ollama_code_model=args.ollama_code_model,
        output_dir=args.output_dir,
        ship_id=args.ship_id,
        variations=args.variations,
        max_workers=args.max_workers,
        max_threads=args.max_threads,
        resume=args.resume,
        skip_completed=args.skip_completed
    )

