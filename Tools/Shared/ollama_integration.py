"""
Shared Ollama Integration Module for AI-Assisted Modding Tools (AAMT)

Provides high-performance Ollama integration with:
- Automatic Ollama startup
- Optimal thread usage (all available cores)
- Model-specific context limits
- Model auto-selection
- Connection testing and retry logic
- Thread-safe request handling
- Rate limiting for concurrent requests
"""

import os
import sys
import subprocess
import time
import requests
import threading
import re
import json
from typing import Optional, List, Dict, Any
from collections import defaultdict

# Cross-process GPU turn-taking (shared with SD): see Tools\Common\gpu_hub.py.
try:
    from gpu_hub import acquire_gpu
except Exception:  # hub is optional — never block generation on its absence
    import contextlib

    def acquire_gpu(label, timeout=None, poll=2.0, enabled=True):  # type: ignore
        return contextlib.nullcontext()

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_URL = f"{OLLAMA_URL}/api"

# Model-specific context limits
MODEL_CONTEXT_LIMITS = {
    "codellama": 16384,  # CodeLlama 7B/13B/34B
    "qwen2.5-coder": 32768,  # Qwen2.5 Coder (14B and 7B)
    "qwen2.5": 32768,  # Qwen2.5 general models
    "qwen2.5-math": 32768,  # Qwen2.5 Math
    "deepseek-coder": 16384,  # DeepSeek Coder
    "deepseek-r1": 16384,  # DeepSeek R1
    "llama3.1": 128000,  # Llama 3.1 (8B and 70B)
    "llama3.2": 128000,  # Llama 3.2
    "mistral": 32768,  # Mistral
    "gemma2": 8192,  # Gemma 2
    "wizardlm": 16384,  # WizardLM
    "default": 16384  # Default fallback
}

# High-performance AI configuration
# Optimized for asset generation pipeline: structured planning, creative concepting, hybrid tasks
# Modern stack: Removed outdated CodeLlama variants, optimized routing for mech asset generation
# Three-tier routing: Standard → Dark-tone → Escalation (for refusal handling)
AI_CONFIG = {
    "preferred_models": {
        "code": [
            "qwen2.5-coder:14b",               # Primary: Structured asset planning (JSON, atlas layouts, segment definitions)
            "qwen2.5-coder:7b",                # Fallback: Fast structured tasks
            "deepseek-coder:6.7b"              # Fallback: Code generation
        ],
        "analysis": [
            "qwen2.5-coder:14b",               # Primary: Structured planning (JSON, atlas layouts, deterministic schemas)
            "deepseek-r1:7b",                  # Hybrid: Physics modeling, mech stat balancing, multi-step reasoning
            "deepseek-coder:6.7b",             # Reasoning: Symbolic logic, physics modeling
            "qwen2.5-math:7b"                  # Math: Thrust-to-weight ratios, mass distributions, VRAM budgets
        ],
        "visual": [
            "wizardlm-uncensored:latest",      # Primary: Uncensored creative (biomutation / organic / dark biotech)
            "llama3.1:8b",                     # Fallback: Creative concepting
            "llama3.1:70b",                    # Higher quality if available
            "mistral:7b"                       # Fallback: General creative tasks
        ],
        "simple": [
            "qwen2.5-coder:7b",                # Fast structured tasks
            "qwen2.5:1.5b",                    # JSON repair, schema validation, formatting cleanup
            "llama3.2:1b",                     # Lightweight fallback
            "phi3:mini",                       # Safety fallback for malformed JSON
            "gemma2:2b"                        # Lightweight fallback
        ],
        # Tier 2: Dark-tone models (for horror, corrupted, eldritch content)
        "dark_tone": [
            "wizardlm-uncensored:latest",      # Primary: Uncensored dark / organic / body-horror tone
            "llama3.1:8b",                     # Fallback dark atmosphere
            "llama3.1:70b",                    # Higher quality dark tone
            "deepseek-r1:7b",                  # Corrupted logic, glitch horror
        ],
        # Tier 3: Escalation models (only when primary models refuse)
        "escalation": [
            "wizardlm-uncensored:latest",      # Last resort when models refuse
            "llama3.1:8b"                      # Alternative escalation
        ]
    },
    "selected_models": {
        "code": None,
        "analysis": None,
        "visual": None,
        "simple": None,
        "dark_tone": None,
        "escalation": None
    },
    "request_timeout_sec": 1800,  # 30 minutes (hybrid load + long prompt packs on 11GB)
    "request_timeout_simple_sec": 120,  # 2 minutes (for simple/short requests)
    "max_tokens_simple": 512,
    "max_tokens_standard": 2048,
    "max_tokens_detailed": 4096,
    "min_delay_between_requests": 0.2,  # seconds
    "max_concurrent_requests": 4,  # Limit concurrent requests to prevent overload
    "rate_limit_window": 1.0  # Rate limit window in seconds
}

# Thread-safe rate limiting
_rate_limit_lock = threading.Lock()
_rate_limit_times = defaultdict(list)
_request_lock = threading.Lock()
_connection_info_printed = False
_connection_info_lock = threading.Lock()

# Model management: track currently loaded model
_current_model_lock = threading.Lock()
_current_model: Optional[str] = None

# Cache for model context limits (to avoid repeated queries)
_model_context_cache: Dict[str, int] = {}
_model_context_cache_lock = threading.Lock()

def get_optimal_thread_count() -> int:
    """Gets optimal thread count for Ollama - uses all available threads."""
    try:
        import multiprocessing
        total_cores = multiprocessing.cpu_count()
        # Use all available threads (leave 1 for system)
        threads = max(4, total_cores - 1)
        return threads
    except:
        return 4

def _cuda_free_total_gb() -> tuple[float, float]:
    """Best-effort free/total VRAM in GB (torch or nvidia-smi)."""
    try:
        import torch
        if torch.cuda.is_available():
            free_b, total_b = torch.cuda.mem_get_info()
            return free_b / (1024 ** 3), total_b / (1024 ** 3)
    except Exception:
        pass
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            free_mb, total_mb = [float(x.strip()) for x in out.stdout.strip().splitlines()[0].split(",")]
            return free_mb / 1024.0, total_mb / 1024.0
    except Exception:
        pass
    return 0.0, 0.0


def _estimate_model_layers_and_gb(model_name: str = "") -> tuple[int, float]:
    """Rough layer count + resident size GB from model name / Ollama tags."""
    name = (model_name or "").lower()
    layers = 40
    size_gb = 7.0
    m = re.search(r"(\d+)\s*b", name)
    if m:
        params = int(m.group(1))
        if params <= 7:
            layers, size_gb = 32, 4.5
        elif params <= 8:
            layers, size_gb = 32, 5.0
        elif params <= 13:
            layers, size_gb = 40, 7.0
        elif params <= 14:
            layers, size_gb = 40, 8.0
        else:
            layers, size_gb = 60, min(14.0, params * 0.55)
    if "wizardlm" in name:
        layers, size_gb = 40, 7.0  # 13B Q4 ~7GB weights; runtime often ~10GB if all on GPU
    try:
        tags = requests.get(f"{OLLAMA_API_URL}/tags", timeout=3).json()
        for mod in tags.get("models", []) or []:
            if mod.get("name") == model_name or (model_name and model_name in str(mod.get("name", ""))):
                raw = mod.get("size") or 0
                if raw:
                    # Disk size is lower than VRAM residency; pad for KV/runtime.
                    size_gb = max(size_gb, (raw / (1024 ** 3)) * 1.35)
                break
    except Exception:
        pass
    return layers, size_gb


def get_num_gpu_layers(model_name: str = "") -> int:
    """
    Hybrid GPU+CPU layer split for Ollama.

    By design: put a *portion* of layers on VRAM and leave the rest on system RAM
    for CPU — not all-CPU (0) and not all-GPU (99) when hybrid is wanted.

    Override:
      AAMT_OLLAMA_NUM_GPU=auto   compute hybrid split (default)
      AAMT_OLLAMA_NUM_GPU=0      force full CPU/RAM
      AAMT_OLLAMA_NUM_GPU=28     exact GPU layer count
      AAMT_OLLAMA_NUM_GPU=99     force max GPU (no intentional CPU share)
      AAMT_OLLAMA_GPU_LAYER_FRACTION=0.65  fraction of layers on GPU when auto
      AAMT_OLLAMA_VRAM_HEADROOM_GB=1.0     keep this much VRAM free in auto mode
    """
    raw = os.environ.get("AAMT_OLLAMA_NUM_GPU", "auto").strip().lower()
    if raw not in ("", "auto", "hybrid", "split"):
        try:
            return int(raw)
        except ValueError:
            pass

    try:
        fraction = float(os.environ.get("AAMT_OLLAMA_GPU_LAYER_FRACTION", "0.65"))
    except ValueError:
        fraction = 0.65
    fraction = max(0.15, min(0.9, fraction))

    try:
        headroom = float(os.environ.get("AAMT_OLLAMA_VRAM_HEADROOM_GB", "1.0"))
    except ValueError:
        headroom = 1.0

    total_layers, model_gb = _estimate_model_layers_and_gb(model_name)
    free_gb, total_gb = _cuda_free_total_gb()
    usable = max(0.5, free_gb - headroom) if total_gb > 0 else model_gb * fraction

    # Cap GPU share by both VRAM budget and intentional CPU share fraction.
    vram_fraction = min(1.0, usable / max(model_gb, 0.1))
    use_fraction = min(fraction, vram_fraction)
    # Always leave at least ~15% of layers on CPU when model is mid/large (true hybrid).
    if total_layers >= 24 and use_fraction > 0.85:
        use_fraction = 0.85

    gpu_layers = int(round(total_layers * use_fraction))
    gpu_layers = max(1, min(total_layers - 1, gpu_layers))  # keep >=1 layer on CPU
    return gpu_layers


def start_ollama_if_needed() -> bool:
    """Attempts to start Ollama if it's not running."""
    # Check if ollama command is available
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, timeout=2, check=True)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        print("  Ollama command not found in PATH")
        return False
    
    # Check if Ollama is already running
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=1)
        if response.status_code == 200:
            return True
    except:
        pass
    
    # Ollama is not running, try to start it
    print("  Starting Ollama in background...")
    try:
        process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        print(f"  Ollama process started (PID: {process.pid})")
        
        # Wait for Ollama to become available (max 30 seconds)
        max_wait = 30
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            try:
                response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=1)
                if response.status_code == 200:
                    print("  Ollama is now available")
                    return True
            except:
                print(f"  Waiting for Ollama... ({waited}/{max_wait} seconds)")
        
        print(f"  Ollama did not become available within {max_wait} seconds")
        return False
    except Exception as e:
        print(f"  Failed to start Ollama: {e}")
        return False

def test_ollama_connection() -> bool:
    """Tests Ollama connection and auto-selects best available models.
    Connection info is only printed once, even when called from multiple threads."""
    global _connection_info_printed
    
    try:
        # Quick connection test with short timeout
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=3)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        data = response.json()
        if not data.get("models") or len(data["models"]) == 0:
            with _connection_info_lock:
                if not _connection_info_printed:
                    print("  No models found in Ollama")
                    print("  Please install at least one model: ollama pull llama3.2:3b")
                    _connection_info_printed = True
            return False
        
        available_models = [model["name"] for model in data["models"]]
        
        # Get available VRAM (total - in use) to prefer smaller models on low VRAM systems
        available_vram_gb = None
        try:
            # Get total VRAM from inference-compute endpoint
            total_vram_gb = None
            compute_response = requests.get(f"{OLLAMA_API_URL}/inference-compute", timeout=3)
            if compute_response.status_code == 200:
                compute_info = compute_response.text
                # Parse VRAM from string like "VRAM:11.0 GiB" or "available:8.6 GiB"
                import re
                # Try to get total VRAM
                vram_match = re.search(r"total[=:]\s*([\d.]+)\s*(GiB|GB)", compute_info, re.IGNORECASE)
                if not vram_match:
                    vram_match = re.search(r"VRAM:\s*([\d.]+)\s*(GiB|GB)", compute_info)
                if vram_match:
                    total_vram_gb = float(vram_match.group(1))
                
                # Try to get available VRAM directly
                available_match = re.search(r"available[=:]\s*([\d.]+)\s*(GiB|GB)", compute_info, re.IGNORECASE)
                if available_match:
                    available_vram_gb = float(available_match.group(1))
            
            # If we have total VRAM but not available, calculate it from loaded models
            if total_vram_gb and available_vram_gb is None:
                # Get VRAM in use from /api/ps endpoint
                ps_response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=3)
                if ps_response.status_code == 200:
                    ps_data = ps_response.json()
                    models_info = ps_data.get("models", [])
                    vram_in_use_gb = 0.0
                    for model in models_info:
                        size_vram = model.get("size_vram", 0)
                        if size_vram > 0:
                            # size_vram is in bytes, convert to GB
                            vram_in_use_gb += size_vram / (1024 ** 3)
                    
                    # Calculate available VRAM
                    available_vram_gb = total_vram_gb - vram_in_use_gb
                else:
                    # If we can't get ps info, use total VRAM (assume nothing loaded)
                    available_vram_gb = total_vram_gb
        except:
            pass  # If we can't get VRAM info, don't filter by size
        
        # Select best model for each task type (always do this, even if not printing)
        model_selections = []
        for task_type in AI_CONFIG["preferred_models"].keys():
            preferences = AI_CONFIG["preferred_models"][task_type]
            selected = select_best_available_model(preferences, available_models, max_vram_gb=available_vram_gb)
            
            if selected:
                AI_CONFIG["selected_models"][task_type] = selected
                tier_label = "Tier 1" if task_type in ["code", "analysis", "visual", "simple"] else ("Tier 2" if task_type == "dark_tone" else "Tier 3")
                model_selections.append(f"  {task_type} ({tier_label}): {selected}")
        
        # Only print connection info once, even if called from multiple threads
        with _connection_info_lock:
            if not _connection_info_printed:
                print(f"  Available models: {len(available_models)}")
                
                if model_selections:
                    print("  Model selection:")
                    for selection in model_selections:
                        print(selection)
                
                # Show resource settings
                threads = get_optimal_thread_count()
                print(f"  Threads: {threads} (of {os.cpu_count() or 4} cores)")
                print(f"  Max concurrent requests: {AI_CONFIG['max_concurrent_requests']}")
                
                # Show context limits for selected models
                context_info = []
                for task_type, model in AI_CONFIG["selected_models"].items():
                    if model:
                        ctx_limit = get_model_context_limit(model)
                        context_info.append(f"    {task_type}: {ctx_limit} tokens ({model})")
                if context_info:
                    print("  Context limits:")
                    for info in context_info:
                        print(info)
                
                _connection_info_printed = True
        
        return len([m for m in AI_CONFIG["selected_models"].values() if m]) > 0
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower() or "refused" in error_msg.lower():
            print("  Ollama is not running")
            
            # Try to start Ollama automatically
            if start_ollama_if_needed():
                # Retry connection after starting
                try:
                    response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("models") and len(data["models"]) > 0:
                            # Process models (same logic as successful connection above)
                            available_models = [model["name"] for model in data["models"]]
                            
                            # Get available VRAM (total - in use) to prefer smaller models on low VRAM systems
                            available_vram_gb = None
                            try:
                                # Get total VRAM from inference-compute endpoint
                                total_vram_gb = None
                                compute_response = requests.get(f"{OLLAMA_API_URL}/inference-compute", timeout=3)
                                if compute_response.status_code == 200:
                                    compute_info = compute_response.text
                                    # Parse VRAM from string like "VRAM:11.0 GiB" or "available:8.6 GiB"
                                    import re
                                    # Try to get total VRAM
                                    vram_match = re.search(r"total[=:]\s*([\d.]+)\s*(GiB|GB)", compute_info, re.IGNORECASE)
                                    if not vram_match:
                                        vram_match = re.search(r"VRAM:\s*([\d.]+)\s*(GiB|GB)", compute_info)
                                    if vram_match:
                                        total_vram_gb = float(vram_match.group(1))
                                    
                                    # Try to get available VRAM directly
                                    available_match = re.search(r"available[=:]\s*([\d.]+)\s*(GiB|GB)", compute_info, re.IGNORECASE)
                                    if available_match:
                                        available_vram_gb = float(available_match.group(1))
                                
                                # If we have total VRAM but not available, calculate it from loaded models
                                if total_vram_gb and available_vram_gb is None:
                                    # Get VRAM in use from /api/ps endpoint
                                    ps_response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=3)
                                    if ps_response.status_code == 200:
                                        ps_data = ps_response.json()
                                        models_info = ps_data.get("models", [])
                                        vram_in_use_gb = 0.0
                                        for model in models_info:
                                            size_vram = model.get("size_vram", 0)
                                            if size_vram > 0:
                                                # size_vram is in bytes, convert to GB
                                                vram_in_use_gb += size_vram / (1024 ** 3)
                                        
                                        # Calculate available VRAM
                                        available_vram_gb = total_vram_gb - vram_in_use_gb
                                    else:
                                        # If we can't get ps info, use total VRAM (assume nothing loaded)
                                        available_vram_gb = total_vram_gb
                            except:
                                pass  # If we can't get VRAM info, don't filter by size
                            
                            # Select best model for each task type (including dark_tone and escalation)
                            model_selections = []
                            for task_type in AI_CONFIG["preferred_models"].keys():
                                preferences = AI_CONFIG["preferred_models"][task_type]
                                selected = select_best_available_model(preferences, available_models, max_vram_gb=available_vram_gb)
                                
                                if selected:
                                    AI_CONFIG["selected_models"][task_type] = selected
                                    tier_label = "Tier 1" if task_type in ["code", "analysis", "visual", "simple"] else ("Tier 2" if task_type == "dark_tone" else "Tier 3")
                                    model_selections.append(f"  {task_type} ({tier_label}): {selected}")
                            
                            # Only print connection info once, even if called from multiple threads
                            with _connection_info_lock:
                                if not _connection_info_printed:
                                    if model_selections:
                                        print("  Model selection:")
                                        for selection in model_selections:
                                            print(selection)
                                    
                                    threads = get_optimal_thread_count()
                                    print(f"  Threads: {threads} (of {os.cpu_count() or 4} cores)")
                                    print(f"  Max concurrent requests: {AI_CONFIG['max_concurrent_requests']}")
                                    
                                    # Show context limits for selected models
                                    context_info = []
                                    for task_type, model in AI_CONFIG["selected_models"].items():
                                        if model:
                                            ctx_limit = get_model_context_limit(model)
                                            context_info.append(f"    {task_type}: {ctx_limit} tokens ({model})")
                                    if context_info:
                                        print("  Context limits:")
                                        for info in context_info:
                                            print(info)
                                    
                                    _connection_info_printed = True
                            
                            return len([m for m in AI_CONFIG["selected_models"].values() if m]) > 0
                except:
                    print("  Still cannot connect to Ollama after starting it")
                    return False
            else:
                print("\n❌ ERROR: Ollama is required")
                print("  To fix this:")
                print("  1. Install Ollama from https://ollama.com")
                print("  2. Start Ollama manually: ollama serve")
                print("  3. Install at least one model: ollama pull llama3.2:3b")
                print("")
                return False
        else:
            print(f"  Connection error: {error_msg}")
            return False
    except Exception as e:
        print(f"  Connection error: {e}")
        return False

def select_best_available_model(preferred_models: List[str], available_models: List[str], max_vram_gb: float = None) -> Optional[str]:
    """
    Selects the best available model from a preference list.
    Considers VRAM constraints - prefers smaller models when VRAM is limited.
    
    Args:
        preferred_models: List of preferred models in order of preference
        available_models: List of available models
        max_vram_gb: Maximum VRAM in GB (if None, doesn't filter by size)
    """
    # Model size estimates (approximate VRAM needed in GB for full precision)
    # These are rough estimates - actual usage depends on context length and quantization
    MODEL_SIZE_ESTIMATES = {
        "1b": 1.5,
        "1.5b": 2.0,
        "2b": 2.5,
        "3b": 4.0,
        "6.7b": 8.0,
        "7b": 8.5,
        "8b": 10.0,
        "13b": 16.0,
        "14b": 18.0,
        "70b": 40.0,
    }
    
    def estimate_model_vram(model_name: str) -> float:
        """Estimate VRAM needed for a model."""
        for size_key, vram_gb in MODEL_SIZE_ESTIMATES.items():
            if size_key in model_name.lower():
                return vram_gb
        # Default estimate for unknown models
        return 12.0
    
    # Filter models by available VRAM if constraint provided
    if max_vram_gb and max_vram_gb < 16.0:  # Low VRAM mode (< 16GB available)
        # For low VRAM, prefer smaller models (7B and below)
        # Filter preferred models to only include those that fit in available VRAM
        vram_safe_models = []
        for preferred in preferred_models:
            vram_needed = estimate_model_vram(preferred)
            # Allow some headroom (use 80% of available VRAM max)
            # This accounts for context/activations overhead
            if vram_needed <= (max_vram_gb * 0.8):
                vram_safe_models.append(preferred)
        
        # If we have VRAM-safe models, use those instead
        if vram_safe_models:
            preferred_models = vram_safe_models
        elif max_vram_gb < 8.0:
            # Very low VRAM (< 8GB available) - only use smallest models
            vram_safe_models = []
            for preferred in preferred_models:
                vram_needed = estimate_model_vram(preferred)
                if vram_needed <= 3.0:  # Only 1B-3B models
                    vram_safe_models.append(preferred)
            if vram_safe_models:
                preferred_models = vram_safe_models
    
    for preferred in preferred_models:
        # Check exact match
        if preferred in available_models:
            return preferred
        # Check partial match (e.g., "codellama:7b" matches "codellama:7b-instruct")
        base_name = preferred.split(":")[0]
        matching = [m for m in available_models if m.startswith(base_name)]
        if matching:
            return matching[0]
    
    # Fallback: return first available model
    if available_models:
        return available_models[0]
    
    return None

def get_available_models() -> List[str]:
    """Get list of available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
    except:
        pass
    return []


def get_model_context_limit(model_name: str, use_safe_margin: bool = True) -> int:
    """
    Get context limit for a specific model.
    
    First tries to query Ollama for the actual model's context size.
    Falls back to hardcoded limits if query fails.
    Uses a safety margin (85%) to avoid warnings about context size being too large.
    Results are cached to avoid repeated queries.
    
    Args:
        model_name: Model name (e.g., "llama3.1:8b")
        use_safe_margin: If True, use 85% of max context to avoid warnings
    
    Returns:
        Context limit in tokens
    """
    # Check cache first
    cache_key = f"{model_name}_{use_safe_margin}"
    with _model_context_cache_lock:
        if cache_key in _model_context_cache:
            return _model_context_cache[cache_key]
    
    # Try to query Ollama for actual model context size
    ctx_value = None
    try:
        # Use show API to get model details (with short timeout to avoid stalling)
        show_response = requests.get(
            f"{OLLAMA_API_URL}/show",
            json={"name": model_name},
            timeout=3  # Short timeout to avoid stalling
        )
        if show_response.status_code == 200:
            data = show_response.json()
            # Check for context size in model details
            if "modelfile" in data:
                # Parse modelfile for PARAMETER num_ctx
                modelfile = data.get("modelfile", "")
                for line in modelfile.split("\n"):
                    if "PARAMETER num_ctx" in line:
                        try:
                            ctx_value = int(line.split("PARAMETER num_ctx")[1].strip())
                            break
                        except (ValueError, IndexError):
                            pass
            
            # Check template parameters
            if ctx_value is None and "parameters" in data:
                params = data["parameters"]
                if "num_ctx" in params:
                    ctx_value = int(params["num_ctx"])
    except (requests.exceptions.RequestException, ValueError, KeyError):
        pass  # Fall back to hardcoded limits
    
    # If we got a value from Ollama, use it (with safety margin)
    if ctx_value is not None:
        if use_safe_margin:
            result = int(ctx_value * 0.85)  # 85% safety margin (more conservative)
        else:
            result = ctx_value
        # Cache the result
        with _model_context_cache_lock:
            _model_context_cache[cache_key] = result
        return result
    
    # Fallback to hardcoded limits with safety margin
    model_base = model_name.split(":")[0].lower()
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in model_base:
            if use_safe_margin:
                result = int(limit * 0.85)  # 85% safety margin
            else:
                result = limit
            # Cache the result
            with _model_context_cache_lock:
                _model_context_cache[cache_key] = result
            return result
    
    # Default with safety margin
    default_limit = MODEL_CONTEXT_LIMITS["default"]
    if use_safe_margin:
        result = int(default_limit * 0.85)
    else:
        result = default_limit
    # Cache the result
    with _model_context_cache_lock:
        _model_context_cache[cache_key] = result
    return result

def _wait_for_rate_limit():
    """Thread-safe rate limiting to prevent overwhelming Ollama."""
    with _rate_limit_lock:
        now = time.time()
        window_start = now - AI_CONFIG["rate_limit_window"]
        
        # Clean old entries
        _rate_limit_times["requests"] = [
            t for t in _rate_limit_times["requests"] if t > window_start
        ]
        
        # Check if we're at the limit
        if len(_rate_limit_times["requests"]) >= AI_CONFIG["max_concurrent_requests"]:
            # Wait until oldest request is outside the window
            oldest = min(_rate_limit_times["requests"])
            wait_time = (oldest + AI_CONFIG["rate_limit_window"]) - now
            if wait_time > 0:
                time.sleep(wait_time)
        
        # Record this request
        _rate_limit_times["requests"].append(time.time())

# Refusal detection patterns (model responses that indicate blocking)
REFUSAL_PATTERNS = [
    r"i cannot (describe|generate|create|process|continue)",
    r"i can't (describe|generate|create|process|continue)",
    r"this content is blocked",
    r"violates safety guidelines",
    r"i cannot help with",
    r"i'm not able to",
    r"i'm unable to",
    r"i cannot assist",
    r"this request cannot be",
    r"i cannot fulfill",
    r"content policy",
    r"safety policy",
    r"inappropriate content",
    r"cannot be generated",
    r"refuse to",
    r"decline to"
]

# Dark tone indicators (content that may need dark-tone routing)
# Organized by category for better detection and scoring
DARK_TONE_INDICATORS = {
    "horror": r"\b(horror|horrific|terror|dread|fear|nightmare|macabre|grisly|gruesome)\b",
    "eldritch": r"\b(eldritch|lovecraft|cosmic\s+horror|unknowable|incomprehensible|maddening)\b",
    "corrupted": r"\b(corrupt(ed|ion)?|taint(ed)?|blight(ed)?|decay(ed|ing)?|rotten|putrid|foul)\b",
    "void": r"\b(void|abyss|darkness|shadow|netherworldly|otherworldly|vacant|empty)\b",
    "gore": r"\b(blood|gore|gory|viscera|guts|entrails|innards|flesh|bone|skull)\b",
    "undead": r"\b(death|necrotic|undead|zombie|ghost|phantom|spirit|haunted|specter)\b",
    "demonic": r"\b(demon(ic)?|devil|hell|infernal|damned|cursed|unholy)\b",
    "monstrous": r"\b(abomination|monstrosity|grotesque|hideous|malformed|twisted|deformed|mutated|chimera)\b",
    "evil": r"\b(sinister|malicious|evil|wicked|malevolent|malignant|nefarious)\b",
    "glitch": r"\b(glitch(ed)?|corrupted\s+(data|code)|broken|malfunction|virus|infection|parasite|parasitic)\b",
    "organic_horror": r"\b(tentacle(d|s)?|tendril(s)?|writhing|pulsating|organic\s+(growth|mass))\b",
    "body_horror": r"\b(multiple\s+(arms|limbs|heads|eyes|faces)|extra\s+(arms|limbs|heads|eyes|faces)|deformity|deformities|disfigured|mutation|mutant|amalgamation|fused\s+(body|bodies|flesh)|conjoined)\b"
}

def detect_refusal(response: str) -> bool:
    """Detects if a model response indicates refusal/blocking."""
    if not response:
        return False
    
    response_lower = response.lower().strip()
    
    # Check for refusal patterns
    for pattern in REFUSAL_PATTERNS:
        if re.search(pattern, response_lower):
            return True
    
    # Check for very short responses that might be refusals
    if len(response_lower) < 50 and any(word in response_lower for word in ["cannot", "can't", "unable", "refuse", "decline"]):
        return True
    
    return False

def detect_dark_tone(prompt: str, verbose: bool = False) -> tuple:
    """
    Detects if a prompt contains dark/horror tone indicators.
    
    Returns:
        tuple: (should_route: bool, score: float, categories: list)
    """
    if not prompt:
        return (False, 0.0, [])
    
    prompt_lower = prompt.lower()
    
    # Score by category (weighted scoring)
    category_weights = {
        "eldritch": 3.0,      # Strong indicator
        "horror": 2.0,        # Strong indicator
        "gore": 2.0,          # Strong indicator
        "corrupted": 2.0,     # Strong indicator
        "monstrous": 2.0,     # Strong indicator
        "glitch": 2.0,        # Strong indicator (glitch horror)
        "organic_horror": 2.0,# Strong indicator
        "body_horror": 2.0,   # Strong indicator (mutations, extra limbs, deformities)
        "void": 1.5,          # Moderate indicator
        "undead": 1.5,        # Moderate indicator
        "demonic": 1.5,       # Moderate indicator
        "evil": 1.0,          # Weak indicator (common in fantasy)
    }
    
    score = 0.0
    matched_categories = []
    
    for category, pattern in DARK_TONE_INDICATORS.items():
        matches = len(re.findall(pattern, prompt_lower))
        if matches > 0:
            weight = category_weights.get(category, 1.0)
            # Diminishing returns for multiple matches in same category
            category_score = weight * (1 + (matches - 1) * 0.3)
            score += category_score
            matched_categories.append((category, matches, category_score))
    
    # Threshold: score of 3.0+ indicates dark tone content
    # This typically means: 2+ strong indicators OR 1 strong + 2 moderate
    should_route = score >= 3.0
    
    if verbose and should_route:
        print(f"  Dark tone score: {score:.1f} - Categories: {', '.join([c for c, _, _ in matched_categories])}")
    
    return (should_route, score, matched_categories)

def call_ollama(
    prompt: str,
    task_type: str = "analysis",
    response_length: str = "standard",
    system_prompt: str = "",
    model_name: str = "",
    use_chat_api: bool = False,
    auto_escalate: bool = True,
    verbose: bool = False
) -> Optional[str]:
    """Sends a high-performance, thread-safe request to Ollama API with optimal settings.

    Holds the cross-process GPU lock for the model load + generation so SD and
    Ollama never fight for VRAM (acquire_gpu is re-entrant per thread, so the
    internal escalation retry nests safely)."""
    with acquire_gpu(f"Ollama {model_name or task_type}"):
        return _call_ollama_impl(
            prompt=prompt,
            task_type=task_type,
            response_length=response_length,
            system_prompt=system_prompt,
            model_name=model_name,
            use_chat_api=use_chat_api,
            auto_escalate=auto_escalate,
            verbose=verbose,
        )


def _call_ollama_impl(
    prompt: str,
    task_type: str = "analysis",
    response_length: str = "standard",
    system_prompt: str = "",
    model_name: str = "",
    use_chat_api: bool = False,
    auto_escalate: bool = True,
    verbose: bool = False
) -> Optional[str]:
    import time
    
    start_time = time.time()
    
    # Thread-safe rate limiting
    _wait_for_rate_limit()
    
    if verbose:
        print(f"  [OLLAMA] Preparing request (task_type={task_type}, response_length={response_length})")
    
    # Determine routing tier based on content tone
    routing_tier = task_type
    if auto_escalate and task_type == "visual":
        # Check for dark tone indicators in prompt
        should_route, tone_score, categories = detect_dark_tone(prompt, verbose=True)
        if should_route:
            routing_tier = "dark_tone"
            print(f"  Dark tone detected (score: {tone_score:.1f}), routing to Tier 2")
    
    # Get the appropriate model (thread-safe read)
    with _request_lock:
        if not model_name:
            # Try primary task type first
            model = AI_CONFIG["selected_models"].get(routing_tier)
            if not model:
                # Fallback to original task type
                model = AI_CONFIG["selected_models"].get(task_type)
                if not model:
                    print(f"  No model available for task type: {task_type}")
                    return None
        else:
            model = model_name
        
        if verbose:
            print(f"  [OLLAMA] Using model: {model}")
        
        # Ensure the model is loaded (swap if needed)
        # Only swap if we're not already in an escalation (to avoid unnecessary swaps)
        global _current_model
        should_swap = True
        model_loading = False
        with _current_model_lock:
            # Check if model is already loaded in Ollama
            try:
                ps_response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=2)
                if ps_response.status_code == 200:
                    loaded_models = ps_response.json().get("models", [])
                    loaded_names = [m.get("name", "") for m in loaded_models]
                    if model in loaded_names:
                        # Model is already loaded, just update tracking
                        _current_model = model
                        should_swap = False
                        if verbose:
                            print(f"  [OLLAMA] Model {model} already loaded")
                    else:
                        # Check if any model is currently loading
                        for m in loaded_models:
                            if m.get("size_vram", 0) == 0:  # Model might be loading
                                model_loading = True
                                break
            except Exception as e:
                if verbose:
                    print(f"  [OLLAMA] Could not check loaded models: {e}")
                pass  # If check fails, proceed with swap
        
        if should_swap:
            with _current_model_lock:
                if _current_model != model:
                    # Model swap needed (only if different)
                    print(f"  [OLLAMA] Loading model {model} (this may take 30-120 seconds for large models)...")
                    print(f"  [OLLAMA] If this hangs, the model may still be loading into VRAM/RAM (not downloading if already in ollama list)")
                    try:
                        swap_model(_current_model, model, verbose=True)  # Always verbose for model loading
                        _current_model = model
                        print(f"  [OLLAMA] Model {model} loaded successfully")
                    except Exception as e:
                        print(f"  [OLLAMA ERROR] Failed to load model {model}: {e}")
                        print(f"  [OLLAMA ERROR] You may need to manually pull the model: ollama pull {model}")
                        raise
        elif model_loading:
            print(f"  [OLLAMA] Model is currently loading, waiting...")
    
    # Get model-specific context limit (with safety margin to avoid warnings)
    max_context = get_model_context_limit(model, use_safe_margin=True)
    
    # Determine max tokens based on response length
    max_tokens_map = {
        "short": AI_CONFIG["max_tokens_simple"],
        "standard": AI_CONFIG["max_tokens_standard"],
        "detailed": AI_CONFIG["max_tokens_detailed"]
    }
    max_tokens = max_tokens_map.get(response_length, AI_CONFIG["max_tokens_standard"])
    
    # Use shorter timeout for simple/short requests to avoid stalling
    request_timeout = AI_CONFIG["request_timeout_simple_sec"] if response_length == "short" else AI_CONFIG["request_timeout_sec"]
    
    # Get optimal thread count
    threads = get_optimal_thread_count()
    
    try:
        if use_chat_api:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            body = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_thread": threads,
                    "num_predict": max_tokens,
                    "num_ctx": max_context,
                    "num_gpu": get_num_gpu_layers(model),
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            print(f"  [OLLAMA] Sending HTTP POST to {OLLAMA_API_URL}/chat (model={model}, timeout={request_timeout}s, num_gpu={get_num_gpu_layers(model)})")
            if verbose:
                print(f"  [OLLAMA] Request body size: {len(json.dumps(body))} bytes")
            try:
                request_start = time.time()
                response = requests.post(
                    f"{OLLAMA_API_URL}/chat",
                    json=body,
                    timeout=request_timeout
                )
                request_elapsed = time.time() - request_start
                print(f"  [OLLAMA] HTTP response status: {response.status_code} (took {request_elapsed:.1f}s)")
            except requests.exceptions.ConnectionError as e:
                print(f"  [OLLAMA ERROR] Connection failed: {e}")
                print(f"  [OLLAMA ERROR] Is Ollama running? Check Process Explorer for 'ollama.exe'")
                raise
            except requests.exceptions.Timeout as e:
                print(f"  [OLLAMA ERROR] Request timed out after {request_timeout}s")
                raise
            
            if response.status_code == 200:
                data = response.json()
                if data.get("message") and data["message"].get("content"):
                    response_text = data["message"]["content"].strip()
                    
                    # Check for refusal and escalate if needed
                    if auto_escalate and detect_refusal(response_text):
                        print("  Model refusal detected, escalating to Tier 3...")
                        # Retry with escalation model
                        escalation_model = AI_CONFIG["selected_models"].get("escalation")
                        if escalation_model and escalation_model != model:
                            print(f"  Retrying with escalation model: {escalation_model}")
                            # Recursive call with escalation model (prevent infinite loop)
                            return call_ollama(
                                prompt=prompt,
                                task_type=task_type,
                                response_length=response_length,
                                system_prompt=system_prompt,
                                model_name=escalation_model,
                                use_chat_api=use_chat_api,
                                auto_escalate=False  # Prevent re-escalation
                            )
                        else:
                            # No escalation model available, return refusal
                            print("  No escalation model available")
                            return response_text
                    
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    print(f"  AI response received ({elapsed_ms}ms)")
                    return response_text
        else:
            # Use generate API (for backward compatibility)
            # If system_prompt is provided, prefer chat API for better handling
            if system_prompt:
                # Use chat API when system prompt is provided (better for system instructions)
                messages = []
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                body = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_thread": threads,
                        "num_predict": max_tokens,
                        "num_ctx": max_context,
                        "num_gpu": get_num_gpu_layers(model),
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
                
                print(f"  [OLLAMA] Sending HTTP POST to {OLLAMA_API_URL}/chat (model={model}, timeout={request_timeout}s, num_gpu={get_num_gpu_layers(model)})")
                try:
                    response = requests.post(
                        f"{OLLAMA_API_URL}/chat",
                        json=body,
                        timeout=request_timeout
                    )
                    print(f"  [OLLAMA] HTTP response status: {response.status_code}")
                except requests.exceptions.ConnectionError as e:
                    print(f"  [OLLAMA ERROR] Connection failed: {e}")
                    print(f"  [OLLAMA ERROR] Is Ollama running? Check Process Explorer for 'ollama.exe'")
                    raise
                except requests.exceptions.Timeout as e:
                    print(f"  [OLLAMA ERROR] Request timed out after {request_timeout}s")
                    raise
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("message") and data["message"].get("content"):
                        response_text = data["message"]["content"].strip()
                        
                        # Check for refusal and escalate if needed
                        if auto_escalate and detect_refusal(response_text):
                            print("  Model refusal detected, escalating to Tier 3...")
                            # Retry with escalation model
                            escalation_model = AI_CONFIG["selected_models"].get("escalation")
                            if escalation_model and escalation_model != model:
                                print(f"  Retrying with escalation model: {escalation_model}")
                                # Recursive call with escalation model (prevent infinite loop)
                                return call_ollama(
                                    prompt=prompt,
                                    task_type=task_type,
                                    response_length=response_length,
                                    system_prompt=system_prompt,
                                    model_name=escalation_model,
                                    use_chat_api=use_chat_api,
                                    auto_escalate=False  # Prevent re-escalation
                                )
                            else:
                                # No escalation model available, return refusal
                                print("  No escalation model available")
                                return response_text
                        
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        print(f"  AI response received ({elapsed_ms}ms)")
                        return response_text
            else:
                # Use generate API for simple prompts without system instructions
                body = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_thread": threads,
                        "num_predict": max_tokens,
                        "num_ctx": max_context,
                        "num_gpu": get_num_gpu_layers(model),
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
                # Note: num_gqa and rope_frequency_base are model-specific and handled by Ollama
                
                print(f"  [OLLAMA] Sending HTTP POST to {OLLAMA_API_URL}/generate (model={model}, timeout={request_timeout}s, num_gpu={get_num_gpu_layers(model)})")
                try:
                    response = requests.post(
                        f"{OLLAMA_API_URL}/generate",
                        json=body,
                        timeout=request_timeout
                    )
                    print(f"  [OLLAMA] HTTP response status: {response.status_code}")
                except requests.exceptions.ConnectionError as e:
                    print(f"  [OLLAMA ERROR] Connection failed: {e}")
                    print(f"  [OLLAMA ERROR] Is Ollama running? Check Process Explorer for 'ollama.exe'")
                    raise
                except requests.exceptions.Timeout as e:
                    print(f"  [OLLAMA ERROR] Request timed out after {request_timeout}s")
                    raise
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("response"):
                        response_text = data["response"].strip()
                        
                        # Check for refusal and escalate if needed
                        if auto_escalate and detect_refusal(response_text):
                            print("  Model refusal detected, escalating to Tier 3...")
                            # Retry with escalation model
                            escalation_model = AI_CONFIG["selected_models"].get("escalation")
                            if escalation_model and escalation_model != model:
                                print(f"  Retrying with escalation model: {escalation_model}")
                                # Recursive call with escalation model (prevent infinite loop)
                                return call_ollama(
                                    prompt=prompt,
                                    task_type=task_type,
                                    response_length=response_length,
                                    system_prompt=system_prompt,
                                    model_name=escalation_model,
                                    use_chat_api=use_chat_api,
                                    auto_escalate=False  # Prevent re-escalation
                                )
                            else:
                                # No escalation model available, return refusal
                                print("  No escalation model available")
                                return response_text
                        
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        print(f"  AI response received ({elapsed_ms}ms)")
                        return response_text
        
        print(f"  AI request failed: HTTP {response.status_code}")
        return None
    except requests.exceptions.Timeout:
        print("  AI request timed out")
        return None
    except Exception as e:
        print(f"  AI request failed: {e}")
        return None


def unload_model(model_name: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Unload a model from Ollama's memory to free VRAM.
    
    Uses Ollama's keep_alive parameter set to 0 to immediately unload the model.
    
    Args:
        model_name: Specific model to unload. If None, unloads currently loaded model.
        verbose: Print status messages.
    
    Returns:
        True if successful, False otherwise.
    """
    global _current_model
    
    with _current_model_lock:
        target_model = model_name or _current_model
        if not target_model:
            if verbose:
                print(f"  No model to unload")
            return True  # Nothing to unload is not an error
        
        try:
            # Check what's currently loaded first
            ps_response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=5)
            if ps_response.status_code == 200:
                loaded_models = ps_response.json().get("models", [])
                loaded_names = [m.get("name", "") for m in loaded_models]
                
                if target_model not in loaded_names:
                    if verbose:
                        print(f"  Model {target_model} is not currently loaded")
                    if _current_model == target_model:
                        _current_model = None
                    return True
            
            # Unload by making a minimal request with keep_alive=0
            # Ollama will unload the model immediately after this request
            unload_body = {
                "model": target_model,
                "prompt": "unload",  # Minimal prompt
                "stream": False,
                "keep_alive": 0  # 0 means unload immediately (can be int or string "0")
            }
            
            response = requests.post(
                f"{OLLAMA_API_URL}/generate",
                json=unload_body,
                timeout=10
            )
            
            if response.status_code == 200:
                if _current_model == target_model:
                    _current_model = None
                if verbose:
                    print(f"  Unloaded model: {target_model}")
                return True
            else:
                if verbose:
                    print(f"  Failed to unload model {target_model}: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"  Error unloading model {target_model}: {e}")
            return False
        except Exception as e:
            if verbose:
                print(f"  Unexpected error unloading model: {e}")
            return False


def ensure_model_loaded(model_name: str, verbose: bool = False) -> bool:
    """
    Ensure a specific model is loaded in Ollama's memory.
    Unloads current model if different, then loads the requested model.
    
    Args:
        model_name: Model to load (e.g., "llama3.1:8b")
        verbose: Print status messages.
    
    Returns:
        True if model is loaded (or was already loaded), False otherwise.
    """
    global _current_model
    
    with _current_model_lock:
        # Check if model is already loaded
        if _current_model == model_name:
            try:
                # Verify it's actually loaded in Ollama
                ps_response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=5)
                if ps_response.status_code == 200:
                    loaded_models = ps_response.json().get("models", [])
                    loaded_names = [m.get("name", "") for m in loaded_models]
                    if model_name in loaded_names:
                        if verbose:
                            print(f"  Model {model_name} already loaded")
                        return True
            except:
                pass  # Continue to load if check fails
        
        # Check if model exists first
        try:
            available_models = get_available_models()
            if model_name not in available_models:
                # Check for partial match (e.g., "llama3.1:8b" might match "llama3.1:8b-instruct")
                base_name = model_name.split(":")[0]
                matching = [m for m in available_models if m.startswith(base_name)]
                if not matching:
                    if verbose:
                        print(f"  [OLLAMA ERROR] Model {model_name} not found in Ollama")
                        print(f"  [OLLAMA ERROR] Install it with: ollama pull {model_name}")
                    return False
                else:
                    # Use the matching model
                    model_name = matching[0]
                    if verbose:
                        print(f"  [OLLAMA] Using available model: {model_name}")
        except Exception as e:
            if verbose:
                print(f"  [OLLAMA WARN] Could not check available models: {e}")
            # Continue anyway, Ollama will error if model doesn't exist
        
        # Unload current model if different
        if _current_model and _current_model != model_name:
            if verbose:
                print(f"  Unloading previous model: {_current_model}")
            unload_model(_current_model, verbose=verbose)
        
        # Load the requested model by making a minimal request
        # Ollama will load the model on first use
        try:
            if verbose:
                print(f"  [OLLAMA] Triggering local memory load for {model_name}...")
                print(f"  [OLLAMA] Note: already-installed models load from disk into VRAM/RAM (not a download)")
                print(f"  [OLLAMA] num_gpu={get_num_gpu_layers(model_name)} (hybrid: GPU layers + CPU/RAM spill)")
            
            # Minimal generate: load weights without a long completion.
            # Hybrid GPU+RAM loads can take several minutes on 11GB cards; not a download.
            load_body = {
                "model": model_name,
                "prompt": ".",
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "num_predict": 1,
                    "temperature": 0,
                    "num_gpu": get_num_gpu_layers(model_name),
                },
            }
            
            load_timeout = int(os.environ.get("OLLAMA_LOAD_TIMEOUT_SEC", "900"))
            
            if verbose:
                print(f"  [OLLAMA] Waiting for model to load into memory (timeout: {load_timeout}s)...")
            
            response = requests.post(
                f"{OLLAMA_API_URL}/generate",
                json=load_body,
                timeout=load_timeout
            )
            
            if response.status_code == 200:
                _current_model = model_name
                if verbose:
                    print(f"  [OLLAMA] Model {model_name} loaded successfully")
                return True
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except Exception:
                    pass
                if verbose:
                    print(f"  [OLLAMA ERROR] Failed to load model {model_name}: {error_msg}")
                    print(f"  [OLLAMA ERROR] If missing locally: ollama pull {model_name}")
                return False
                
        except requests.exceptions.Timeout:
            if verbose:
                print(f"  [OLLAMA WARN] Timeout loading model {model_name} after {load_timeout}s")
                print(f"  [OLLAMA WARN] Weights may still be mapping into VRAM/RAM in the background")
                print(f"  [OLLAMA WARN] Check: ollama ps  (installed models: ollama list — no pull if listed)")
            # Model might still be loading, but mark as current anyway
            # The next actual request will verify it's loaded
            _current_model = model_name
            return True
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"  [OLLAMA ERROR] Error loading model {model_name}: {e}")
                if "Connection" in str(e) or "refused" in str(e).lower():
                    print(f"  [OLLAMA ERROR] Is Ollama running? Check: ollama ps")
            return False
        except Exception as e:
            if verbose:
                print(f"  [OLLAMA ERROR] Unexpected error loading model: {e}")
            return False


def swap_model(old_model: Optional[str], new_model: str, verbose: bool = False) -> bool:
    """
    Swap from one model to another, unloading the old and loading the new.
    
    Args:
        old_model: Model to unload (can be None)
        new_model: Model to load
        verbose: Print status messages.
    
    Returns:
        True if swap successful, False otherwise.
    """
    if old_model:
        if verbose:
            print(f"  Swapping models: {old_model} -> {new_model}")
        unload_model(old_model, verbose=verbose)
    
    return ensure_model_loaded(new_model, verbose=verbose)


def get_loaded_models() -> List[str]:
    """
    Get list of models currently loaded in Ollama's memory.
    
    Returns:
        List of model names currently loaded.
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/ps", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
    except:
        pass
    return []


def unload_all_models(verbose: bool = False) -> int:
    """
    Unload all models currently loaded in Ollama's memory.
    Useful for freeing VRAM after asset generation is complete.
    
    Args:
        verbose: Print status messages.
    
    Returns:
        Number of models unloaded.
    """
    global _current_model
    
    loaded = get_loaded_models()
    if not loaded:
        if verbose:
            print("  No models to unload")
        return 0
    
    unloaded_count = 0
    for model_name in loaded:
        if unload_model(model_name, verbose=verbose):
            unloaded_count += 1
    
    with _current_model_lock:
        _current_model = None
    
    if verbose:
        print(f"  Unloaded {unloaded_count} model(s)")
    
    return unloaded_count


def get_current_model() -> Optional[str]:
    """
    Get the currently tracked model (may not match what's actually loaded in Ollama).
    
    Returns:
        Currently tracked model name, or None.
    """
    with _current_model_lock:
        return _current_model

