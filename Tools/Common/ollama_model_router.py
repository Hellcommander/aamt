"""
Ollama Model Router
Intelligently routes tasks to the best available model based on task type.

TWO-STAGE PIPELINE (Optimized for 11GB GPU):
- Draft Stage (fast iterations): 7B models for quick A/B testing
  * Qwen2.5-Coder 7B or CodeLlama 7B-instruct for structured outputs (JSON/SVG)
  * DeepSeek-R1 7B or WizardLM-uncensored 7B for creative drafts
- Polish Stage (final quality): 8B+ or quantized 14B for final copy
  * Llama 3.1 8B for balanced instruction following, longer context
  * Quantized 14B models for complex reasoning (if available)

DUAL-MODEL SYSTEM (Original - Default):
- Code/Structured: Qwen2.5-Coder 7B (preferred) or CodeLlama 7B-instruct
- Visual/Creative: Llama 3.1 8B (polish) or DeepSeek-R1 7B (draft)
- WizardLM reserved for sensitive content only (low priority for general use)

MULTIMODEL PIPELINE (Optional Enhancement):
- Reasoning: CodeLlama 7B-instruct or Qwen2.5-Coder 7B
- Generation: Qwen2.5-Coder 7B (preferred) or StarCoder 7B
- Verification: CodeLlama verifies generation outputs

The router supports both systems:
- Use get_model_for_task() for dual-model routing (original behavior)
- Use route_with_intent() for multimodel pipeline (when use_verification=True)
- Use get_draft_model() / get_polish_model() for two-stage pipeline

Note: WizardLM is kept available but with low priority, as it's primarily needed
for sensitive/uncensored content generation, which is rarely needed for Transcendence.
"""

import requests
import re
import time
import threading
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Set
from enum import Enum
from dataclasses import dataclass

# File locking for multi-instance coordination
try:
    if sys.platform == 'win32':
        import msvcrt
        HAS_FILE_LOCKING = True
    else:
        import fcntl
        HAS_FILE_LOCKING = True
except ImportError:
    HAS_FILE_LOCKING = False

# Task type constants
TASK_CODE = "code"  # Blender Python, code generation, refactoring, XML generation
TASK_XML = "xml"  # XML generation, export, configuration (uses code model)
TASK_VISUAL = "visual"  # Visual descriptions, color palettes, FX descriptions
TASK_ORCHESTRATION = "orchestration"  # General orchestration, planning
TASK_AUDIO = "audio"  # Audio descriptions (can use either)

# Intent classification for multimodel pipeline
class TaskIntent(Enum):
    """Task intent classification for routing."""
    REASONING = "reasoning"      # Explain, diagnose, refactoring, analysis
    GENERATION = "generation"    # Generate, complete, implement, scaffold
    UNKNOWN = "unknown"          # Default/fallback

@dataclass
class RoutingDecision:
    """Decision from the router with intent and verification info."""
    intent: TaskIntent
    primary_model: str
    verification_model: Optional[str] = None
    confidence: float = 1.0
    reasoning: str = ""
    complexity: str = "standard"  # "simple", "standard", "complex"

class OllamaModelRouter:
    """Routes tasks to appropriate Ollama models based on task type."""
    
    # Reasoning keywords (route to Code Llama for reasoning tasks)
    REASONING_KEYWORDS = [
        'explain', 'why', 'reason', 'analyze', 'diagnose', 'debug',
        'refactor', 'improve', 'optimize', 'fix', 'correct', 'update',
        'compatibility', 'compatible', 'outdated', 'deprecated', 'missing',
        'error', 'bug', 'issue', 'problem', 'wrong', 'incorrect'
    ]
    
    # Generation keywords (route to StarCoder for generation tasks)
    GENERATION_KEYWORDS = [
        'generate', 'create', 'implement', 'write', 'complete', 'scaffold',
        'build', 'make', 'add', 'new', 'missing', 'implement', 'code'
    ]
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        use_verification: bool = False,
        enable_model_unloading: bool = True,
        shared_index_path: Optional[Path] = None
    ):
        """
        Initialize router with resource management.
        
        Args:
            ollama_url: Ollama API URL
            use_verification: Enable verification for generation tasks (multimodel pipeline)
            enable_model_unloading: Automatically unload unused models to save resources
            shared_index_path: Path to shared RAG index (for multi-instance coordination)
        """
        self.ollama_url = ollama_url
        self.available_models: List[Dict] = []
        # Original dual-model assignments (code/visual)
        self.code_model: Optional[str] = None
        self.visual_model: Optional[str] = None
        # Multimodel pipeline assignments (reasoning/generation) - optional
        self.reasoning_model: Optional[str] = None  # Code Llama 7B instruct for reasoning
        self.generation_model: Optional[str] = None  # StarCoder 7B for generation
        self.complex_model: Optional[str] = None  # 13-14B or 8B for complex tasks (34B disabled)
        self.use_verification = use_verification
        self.enable_model_unloading = enable_model_unloading
        
        # CPU offload settings for high VRAM models
        # num_gpu controls how many layers run on GPU (rest go to CPU with KV cache in RAM)
        # Lower num_gpu = more CPU offload = less VRAM usage, more RAM usage
        self.enable_cpu_offload = True  # Enable CPU offload for high VRAM models
        self.cpu_offload_config = {
            # Model size -> num_gpu layers (None = use all GPU layers, no offload)
            '7b': None,      # 7B models: no offload needed (fits easily)
            '8b': 20,       # 8B models: offload some layers (20 GPU layers, rest CPU)
            '13b': 15,      # 13B models: more offload (15 GPU layers)
            '14b': 15,      # 14B models: more offload (15 GPU layers)
            'default': 20   # Default for unknown large models
        }
        
        # Resource management
        self.loaded_models: Set[str] = set()  # Track which models are currently loaded
        self.model_last_used: Dict[str, float] = {}  # Track last usage time
        self.model_unload_timeout = 300  # Unload models after 5 minutes of inactivity
        self._resource_lock = threading.Lock()  # Thread-safe resource access
        
        # Shared index coordination
        self.shared_index_path = shared_index_path
        self.index_lock_file: Optional[Path] = None
        self.index_lock_handle = None
        if shared_index_path:
            self._setup_shared_index()
        
        self._detect_models()
    
    def _setup_shared_index(self):
        """Setup shared index with file locking for multi-instance coordination."""
        if not self.shared_index_path:
            return
        
        # Create lock file path
        lock_file = self.shared_index_path.parent / f"{self.shared_index_path.stem}.lock"
        self.index_lock_file = lock_file
        
        # Create lock file if it doesn't exist
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        if not lock_file.exists():
            lock_file.touch()
        
        # Acquire lock (non-blocking, will wait if another instance is using it)
        self._acquire_index_lock()
    
    def _acquire_index_lock(self):
        """Acquire file lock for shared index access (waits if another instance is using it)."""
        if not self.index_lock_file or not HAS_FILE_LOCKING:
            return
        
        timeout = 30.0  # Wait up to 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if sys.platform == 'win32':
                    # Windows file locking (non-blocking)
                    self.index_lock_handle = open(self.index_lock_file, 'r+')
                    msvcrt.locking(self.index_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    # Unix file locking (non-blocking)
                    self.index_lock_handle = open(self.index_lock_file, 'r+')
                    fcntl.flock(self.index_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Write PID to lock file for debugging
                self.index_lock_handle.seek(0)
                self.index_lock_handle.write(f"{os.getpid()}\n{time.time()}\n")
                self.index_lock_handle.flush()
                return
            except (IOError, OSError):
                # Lock is held by another instance, wait and retry
                if self.index_lock_handle:
                    try:
                        self.index_lock_handle.close()
                    except:
                        pass
                    self.index_lock_handle = None
                time.sleep(0.5)  # Wait before retry
        
        print(f"Warning: Could not acquire index lock after {timeout}s. Another instance may be using it.")
    
    def _release_index_lock(self):
        """Release file lock for shared index."""
        if self.index_lock_handle and HAS_FILE_LOCKING:
            try:
                if sys.platform == 'win32':
                    msvcrt.locking(self.index_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(self.index_lock_handle.fileno(), fcntl.LOCK_UN)
                self.index_lock_handle.close()
            except:
                pass
            self.index_lock_handle = None
    
    def _detect_models(self):
        """Detect available models and assign them to task types."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.available_models = response.json().get('models', [])
                self._assign_models()
        except Exception as e:
            print(f"Warning: Could not detect Ollama models: {e}")
            self._set_fallbacks()
    
    def _assign_models(self):
        """Assign best models for code and visual tasks."""
        # Find best code model (CodeLlama preferred)
        code_candidates = []
        visual_candidates = []
        
        for model in self.available_models:
            name = model.get('name', '').lower()
            details = model.get('details', {})
            param_size = details.get('parameter_size', '')
            model_name = model.get('name')  # Preserve original case
            
            # Helper to check model size patterns (handles :7b, :7, -7b, etc.)
            def has_size(size_str):
                return (size_str in name or 
                       f':{size_str}' in name or 
                       f'-{size_str}' in name or
                       size_str in param_size.lower())
            
            # Qwen2.5-Coder - Excellent for code generation and structured outputs (JSON/SVG)
            if 'qwen' in name and 'coder' in name:
                if has_size('14b') or has_size('14'):
                    # 14B quantized only for 11GB GPU
                    priority = 95   # Very high priority for code (if quantized)
                    code_candidates.append((priority, model_name))
                elif has_size('7b') or has_size('7'):
                    priority = 97   # Highest priority for code - excellent for structured outputs
                    code_candidates.append((priority, model_name))
                    if not self.generation_model:  # Use for generation tasks
                        self.generation_model = model_name
                else:
                    priority = 90   # Other Qwen coder variants
                    code_candidates.append((priority, model_name))
            
            # Code model candidates (34B disabled - too slow for 11GB VRAM)
            elif 'codellama' in name:
                # Skip 34B models - too slow for available VRAM
                if has_size('34b') or has_size('34'):
                    # Don't use 34B - prefer 13-14B or 8B models instead
                    continue
                elif has_size('13b') or has_size('13') or has_size('14b') or has_size('14'):
                    # 13-14B models are excellent for complex tasks (fits in 11GB VRAM)
                    priority = 96   # Very high priority - best for complex code tasks
                    code_candidates.append((priority, model_name))
                    # Use as complex model replacement (instead of 34B)
                    if not self.complex_model:
                        self.complex_model = model_name
                elif has_size('8b') or has_size('8'):
                    # 8B models good for standard tasks
                    priority = 93   # High priority for standard code tasks
                    code_candidates.append((priority, model_name))
                    if not self.complex_model:
                        self.complex_model = model_name  # Use 8B as complex model if no 13-14B
                elif has_size('7b') or has_size('7'):
                    # CodeLlama-7B-instruct: deterministic code/assets, templates
                    if 'instruct' in name:
                        priority = 94   # High priority for structured/code tasks
                        code_candidates.append((priority, model_name))
                        self.reasoning_model = model_name  # Prefer instruct for reasoning
                    else:
                        priority = 88   # CodeLlama-7B - good balance of speed/quality
                        code_candidates.append((priority, model_name))
                    if not self.reasoning_model:  # Use as reasoning model fallback
                        self.reasoning_model = model_name
                else:
                    priority = 80   # Other CodeLlama variants
                    code_candidates.append((priority, model_name))
            
            # StarCoder for generation tasks (multimodel pipeline)
            elif 'starcoder' in name:
                if has_size('7b') or has_size('7'):
                    if not self.generation_model:
                        self.generation_model = model_name
                    # Also add to code candidates (StarCoder is excellent for code generation)
                    code_candidates.append((96, model_name))  # Very high priority for code
                else:
                    code_candidates.append((94, model_name))  # High priority even if not 7B
            elif 'code' in name and 'llama' not in name and 'starcoder' not in name and 'qwen' not in name:
                # Other code models (not CodeLlama, StarCoder, or Qwen)
                priority = 70
                code_candidates.append((priority, model_name))
            
            # Visual/orchestration model candidates
            # Two-stage pipeline: Draft (7B fast) -> Polish (8B+ or quantized 14B)
            
            # Llama 3.1 (8B) - Polish stage: balanced instruction following, longer context
            if 'llama' in name and ('3.1' in name or '3.1' in param_size):
                if has_size('8b') or has_size('8'):
                    priority = 90  # High priority for polish stage - excellent for final copy
                    visual_candidates.append((priority, model_name))
                elif has_size('13b') or has_size('13') or has_size('14b') or has_size('14'):
                    # Quantized 14B for polish if available
                    priority = 88  # High priority if quantized
                    visual_candidates.append((priority, model_name))
                else:
                    priority = 85  # Other Llama 3.1 variants
                    visual_candidates.append((priority, model_name))
            
            # DeepSeek-R1 (7B) - Draft stage: creative drafts, exploration, strong conversational
            elif 'deepseek' in name and ('r1' in name or 'r-1' in name):
                if has_size('7b') or has_size('7'):
                    priority = 85  # High priority for draft stage - creative exploration
                    visual_candidates.append((priority, model_name))
                else:
                    priority = 80  # Other DeepSeek-R1 variants
                    visual_candidates.append((priority, model_name))
            
            # CodeLlama can also handle visual/orchestration tasks well (general-purpose)
            elif 'codellama' in name:
                # CodeLlama models are good for visual tasks too (not just code)
                if has_size('13b') or has_size('13'):
                    priority = 75  # CodeLlama-13B for visual tasks
                elif has_size('7b') or has_size('7'):
                    priority = 70  # CodeLlama-7B for visual tasks
                else:
                    priority = 65  # Other CodeLlama variants for visual
                visual_candidates.append((priority, model_name))
            
            # Regular Llama models (not CodeLlama, not 3.1) - good for visual tasks
            elif 'llama' in name and 'codellama' not in name:
                if has_size('13b') or has_size('13'):
                    priority = 80  # Regular Llama-13B - good for visual
                elif has_size('8b') or has_size('8'):
                    priority = 82  # Llama 8B - good balance
                else:
                    priority = 70  # Regular Llama models - good for visual
                visual_candidates.append((priority, model_name))
            
            # WizardLM-uncensored (7B) - Draft stage: creative outputs, instruction following
            # Note: Reserved for sensitive content, but can be used for creative drafts
            elif 'wizardlm' in name and 'uncensored' in name:
                if has_size('7b') or has_size('7'):
                    priority = 75  # Medium priority - good for creative drafts
                    visual_candidates.append((priority, model_name))
                elif has_size('13b') or has_size('13'):
                    priority = 40  # Low priority - only use when needed for sensitive content
                    visual_candidates.append((priority, model_name))
                elif ':latest' in name or name.endswith(':latest'):
                    priority = 70  # Medium-low priority - reserved for sensitive content
                    visual_candidates.append((priority, model_name))
                else:
                    priority = 30  # Very low priority - reserved for sensitive content
                    visual_candidates.append((priority, model_name))
            elif 'wizardlm' in name:
                priority = 25  # Very low priority - reserved for sensitive content
                visual_candidates.append((priority, model_name))
        
        # Select best code model
        if code_candidates:
            code_candidates.sort(reverse=True, key=lambda x: x[0])
            self.code_model = code_candidates[0][1]
        else:
            # Fallback: try to find any code-related model, then use largest available
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'codellama' in name or 'starcoder' in name or 'code' in name:
                    self.code_model = model.get('name')
                    break
            if not self.code_model:
                # Fallback: use largest available model for code
                largest = self._find_largest_model()
                self.code_model = largest
        
        # Select best visual model
        if visual_candidates:
            visual_candidates.sort(reverse=True, key=lambda x: x[0])
            self.visual_model = visual_candidates[0][1]
        else:
            # Fallback: prefer CodeLlama or regular Llama over WizardLM for visual tasks
            for model in self.available_models:
                name = model.get('name', '').lower()
                # Prefer CodeLlama for visual tasks (general-purpose, good quality)
                if 'codellama' in name:
                    self.visual_model = model.get('name')
                    break
            if not self.visual_model:
                # Next prefer regular Llama models
                for model in self.available_models:
                    name = model.get('name', '').lower()
                    if 'llama' in name and 'codellama' not in name:
                        self.visual_model = model.get('name')
                        break
            if not self.visual_model:
                # Last resort: use largest available model (may include WizardLM)
                largest = self._find_largest_model()
                self.visual_model = largest
        
        # Final fallback: if still no models assigned, use any available model
        if not self.code_model and self.available_models:
            self.code_model = self.available_models[0].get('name')
        if not self.visual_model and self.available_models:
            # Prefer a different model for visual if available
            for model in self.available_models:
                if model.get('name') != self.code_model:
                    self.visual_model = model.get('name')
                    break
            if not self.visual_model:
                self.visual_model = self.code_model
        
        # Set complex model (13-14B or 8B) - 34B disabled (too slow for 11GB VRAM)
        if not self.complex_model:
            # Look for 13-14B or 8B models (fits in 11GB VRAM, faster than 34B)
            for model in self.available_models:
                name = model.get('name', '').lower()
                # Prefer CodeLlama or Qwen coder 13-14B
                if ('codellama' in name or ('qwen' in name and 'coder' in name)):
                    if (('13b' in name or ':13' in name or '-13' in name) or
                        ('14b' in name or ':14' in name or '-14' in name)):
                        self.complex_model = model.get('name')
                        break
            # If no 13-14B found, look for 8B models
            if not self.complex_model:
                for model in self.available_models:
                    name = model.get('name', '').lower()
                    if ('codellama' in name or ('qwen' in name and 'coder' in name) or
                        ('llama' in name and '3.1' in name)):
                        if ('8b' in name or ':8' in name or '-8' in name):
                            self.complex_model = model.get('name')
                            break
        
        # Set reasoning/generation models for multimodel pipeline
        # These are separate from the dual-model system (code/visual)
        # Also set reasoning model even if verification is disabled (for potential future use)
        
        # Helper to check 7B models
        def is_7b_model(name):
            return (':7b' in name or ':7' in name or '-7b' in name or '-7' in name or
                   name.endswith(':7b') or name.endswith(':7') or
                   '7b' in name.split(':')[-1] or '7' in name.split(':')[-1])
        
        if not self.reasoning_model:
            # Prefer CodeLlama 7B instruct, then Qwen2.5-coder, then CodeLlama 7B
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'codellama' in name and is_7b_model(name) and 'instruct' in name:
                    self.reasoning_model = model.get('name')
                    break
            # If no instruct variant found, try Qwen2.5-coder 7B
            if not self.reasoning_model:
                for model in self.available_models:
                    name = model.get('name', '').lower()
                    if 'qwen' in name and 'coder' in name and is_7b_model(name):
                        self.reasoning_model = model.get('name')
                        break
            # If still not found, use any CodeLlama 7B
            if not self.reasoning_model:
                for model in self.available_models:
                    name = model.get('name', '').lower()
                    if 'codellama' in name and is_7b_model(name):
                        self.reasoning_model = model.get('name')
                        break
            # Final fallback to code model (if it's a CodeLlama or Qwen variant)
            if not self.reasoning_model and self.code_model:
                code_name = self.code_model.lower()
                if ('codellama' in code_name or 'qwen' in code_name) and is_7b_model(code_name):
                    self.reasoning_model = self.code_model
        
        if not self.generation_model:
            # Prefer Qwen2.5-coder 7B, then StarCoder 7B, then code model
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'qwen' in name and 'coder' in name and is_7b_model(name):
                    self.generation_model = model.get('name')
                    break
            # If no Qwen found, try StarCoder 7B
            if not self.generation_model:
                for model in self.available_models:
                    name = model.get('name', '').lower()
                    if 'starcoder' in name:
                        if is_7b_model(name):
                            self.generation_model = model.get('name')
                            break
                        else:
                            # Use any StarCoder if 7B not found
                            self.generation_model = model.get('name')
                            break
            # Fallback to code model if no specialized generation model found
            if not self.generation_model:
                self.generation_model = self.code_model
    
    def _find_largest_model(self) -> str:
        """Find the largest available model as fallback."""
        if not self.available_models:
            # Prefer CodeLlama as fallback (WizardLM only if nothing else available)
            return "codellama:7b"
        
        def model_size_score(m):
            details = m.get('details', {})
            param_size = details.get('parameter_size', '').lower()
            name = m.get('name', '').lower()
            
            # Helper to check model size patterns
            def has_size(size_str):
                return (size_str in name or 
                       f':{size_str}' in name or 
                       f'-{size_str}' in name or
                       size_str in param_size or
                       name.endswith(f':{size_str}') or
                       size_str in name.split(':')[-1])
            
            # Skip 34B models (too slow for 11GB VRAM)
            if has_size('34b') or has_size('34'):
                return 0  # Skip 34B models
            
            # Prioritize 13-14B models (fits in 11GB VRAM, faster than 34B)
            if 'codellama' in name and (has_size('13b') or has_size('13') or has_size('14b') or has_size('14')):
                return 100  # Highest priority - best for complex tasks
            elif ('qwen' in name and 'coder' in name) and (has_size('13b') or has_size('13') or has_size('14b') or has_size('14')):
                return 98  # Very high priority
            elif has_size('13b') or has_size('13') or has_size('14b') or has_size('14'):
                return 95
            # Prioritize 8B models (good balance)
            elif 'codellama' in name and (has_size('8b') or has_size('8')):
                return 92
            elif ('llama' in name and '3.1' in name) and (has_size('8b') or has_size('8')):
                return 90
            elif has_size('8b') or has_size('8'):
                return 85
            elif has_size('7b') or has_size('7'):
                return 60
            elif has_size('3b') or has_size('3'):
                return 40
            # Prefer models with :latest tag (often means best available)
            elif ':latest' in name or name.endswith(':latest'):
                return 50
            return 20
        
        largest = max(self.available_models, key=model_size_score)
        # Prefer CodeLlama as fallback (WizardLM only if nothing else available)
        return largest.get('name', 'codellama:7b')
    
    def _set_fallbacks(self):
        """Set fallback models if detection fails."""
        # Prefer CodeLlama as fallback (WizardLM only if nothing else available)
        self.code_model = "codellama:7b"
        self.visual_model = "codellama:7b"
    
    def get_model_for_task(self, task_type: str) -> str:
        """
        Get the appropriate model for a given task type.
        
        Args:
            task_type: One of TASK_CODE, TASK_XML, TASK_VISUAL, TASK_ORCHESTRATION, TASK_AUDIO
        
        Returns:
            Model name to use (CodeLlama for code/XML, CodeLlama/Llama for visual/orchestration)
        """
        # Code and XML tasks use CodeLlama (code model)
        if task_type in (TASK_CODE, TASK_XML):
            return self.code_model or self.visual_model or "codellama:7b"
        elif task_type in (TASK_VISUAL, TASK_ORCHESTRATION, TASK_AUDIO):
            # Visual/orchestration tasks prefer CodeLlama or regular Llama (WizardLM reserved for sensitive content)
            return self.visual_model or self.code_model or "codellama:7b"
        else:
            # Default to visual model (which prefers CodeLlama) for unknown task types
            return self.visual_model or self.code_model or "codellama:7b"
    
    def get_code_model(self) -> str:
        """Get the model for code generation tasks."""
        return self.code_model or self.visual_model or "codellama:7b"
    
    def get_visual_model(self) -> str:
        """Get the model for visual/orchestration tasks."""
        return self.visual_model or self.code_model or "codellama:7b"
    
    def get_draft_model(self, task_type: str = "visual") -> str:
        """
        Get model for draft stage (fast iterations, 7B models).
        
        Args:
            task_type: "code" for structured outputs, "visual" for creative drafts
        
        Returns:
            Model name for draft stage (7B model for fast iterations)
        """
        if task_type == "code":
            # For structured outputs: prefer Qwen2.5-Coder 7B or CodeLlama 7B-instruct
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'qwen' in name and 'coder' in name and (':7b' in name or ':7' in name):
                    return model.get('name')
            # Fallback to CodeLlama 7B-instruct
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'codellama' in name and 'instruct' in name and (':7b' in name or ':7' in name):
                    return model.get('name')
            # Final fallback
            return self.code_model or "codellama:7b"
        else:
            # For creative drafts: prefer DeepSeek-R1 7B or WizardLM-uncensored 7B
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'deepseek' in name and ('r1' in name or 'r-1' in name) and (':7b' in name or ':7' in name):
                    return model.get('name')
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'wizardlm' in name and 'uncensored' in name and (':7b' in name or ':7' in name):
                    return model.get('name')
            # Fallback to visual model or code model
            return self.visual_model or self.code_model or "codellama:7b"
    
    def get_polish_model(self, task_type: str = "visual") -> str:
        """
        Get model for polish stage (final quality, 8B+ or quantized 14B).
        
        Args:
            task_type: "code" for code polish, "visual" for creative polish
        
        Returns:
            Model name for polish stage (8B+ or quantized 14B for final quality)
        """
        if task_type == "code":
            # For code polish: prefer larger CodeLlama or Qwen2.5-Coder
            for model in self.available_models:
                name = model.get('name', '').lower()
                if ('codellama' in name or ('qwen' in name and 'coder' in name)):
                    # Prefer 13B+ or quantized 14B
                    if ':13' in name or ':14' in name or '13b' in name or '14b' in name:
                        return model.get('name')
            # Fallback to code model
            return self.code_model or "codellama:7b"
        else:
            # For creative polish: prefer Llama 3.1 8B or quantized 14B
            for model in self.available_models:
                name = model.get('name', '').lower()
                if 'llama' in name and ('3.1' in name or '3.1' in model.get('details', {}).get('parameter_size', '')):
                    if ':8' in name or ':13' in name or ':14' in name or '8b' in name or '13b' in name or '14b' in name:
                        return model.get('name')
                    elif ':7' in name or '7b' in name:
                        return model.get('name')  # Still better than draft models
            # Fallback to visual model
            return self.visual_model or self.code_model or "codellama:7b"
    
    def classify_complexity(self, prompt: str, task_description: str = "", code_length: int = 0) -> str:
        """
        Classify task complexity to determine if a larger model (13-14B or 8B) is needed.
        
        Complex tasks use 13-14B or 8B models (34B disabled - too slow for 11GB VRAM):
        - Large-codebase reasoning and cross-file refactors
        - High-quality code generation and infilling
        - Complex bug diagnosis across modules
        - Production-grade generation
        - High-risk tasks (design changes, security-sensitive fixes)
        
        Args:
            prompt: The full prompt
            task_description: Task description
            code_length: Length of code being processed (in characters)
        
        Returns:
            "simple", "standard", or "complex"
        """
        text = (prompt + " " + task_description).lower()
        
        complexity_score = 0
        
        # High-risk/complex indicators (require CodeLlama 34B - senior engineer model)
        # These indicate tasks requiring deep reasoning, cross-file understanding, or high accuracy
        high_risk_keywords = [
            # Cross-file and architecture
            'cross-file', 'cross file', 'multiple files', 'across files', 'entire',
            'architecture', 'design pattern', 'refactor', 'restructure',
            'dependency', 'dependencies', 'module', 'modules',
            
            # Complex reasoning
            'complex', 'complicated', 'extensive', 'comprehensive', 'large-scale',
            'multi-step', 'multi step', 'tracing', 'diagnosis', 'debugging',
            
            # High-stakes tasks
            'security', 'sensitive', 'critical', 'production', 'production-grade',
            'high-risk', 'high risk', 'important', 'crucial',
            
            # Advanced patterns
            'harmony', 'patch', 'intercept', 'hook', 'reflection', 'dynamic',
            'async', 'await', 'threading', 'concurrent', 'parallel',
            'inheritance', 'polymorphism', 'interface', 'abstract', 'generic',
            'delegate', 'event', 'callback', 'observer',
            
            # Code quality indicators
            'infill', 'fill-in-the-middle', 'completion', 'scaffold',
            'generate', 'implement', 'feature'
        ]
        
        # Medium complexity indicators
        medium_keywords = [
            'update', 'fix', 'correct', 'modify', 'change',
            'improve', 'optimize', 'enhance'
        ]
        
        # Simple indicators (can use 7B models - quick completions)
        simple_keywords = [
            'simple', 'basic', 'small', 'quick', 'minor', 'small fix',
            'typo', 'syntax', 'format', 'style', 'rename', 'comment'
        ]
        
        # Count high-risk indicators (weighted heavily)
        for keyword in high_risk_keywords:
            if keyword in text:
                complexity_score += 3  # High weight for senior engineer tasks
        
        # Count medium indicators
        for keyword in medium_keywords:
            if keyword in text:
                complexity_score += 1
        
        # Count simple indicators (negative)
        for keyword in simple_keywords:
            if keyword in text:
                complexity_score -= 2  # Strong negative weight
        
        # Code length factor (longer code = more complex, requires better reasoning)
        if code_length > 5000:
            complexity_score += 4  # Large codebase = complex
        elif code_length > 2000:
            complexity_score += 2  # Medium-large = moderate complexity
        elif code_length > 1000:
            complexity_score += 1
        
        # Cross-file or multi-module indicators
        if any(phrase in text for phrase in ['multiple files', 'across', 'entire', 'cross-file', 'cross file']):
            complexity_score += 3  # Cross-file work requires larger model (13-14B or 8B)
        
        # Security or production indicators (always complex)
        if any(phrase in text for phrase in ['security', 'sensitive', 'critical', 'production']):
            complexity_score += 4  # High-stakes = always use larger model (13-14B or 8B)
        
        # Decision thresholds (adjusted for better routing)
        if complexity_score >= 5:
            return "complex"  # Use 13-14B or 8B model (fits in 11GB VRAM, faster than 34B)
        elif complexity_score <= -1:
            return "simple"  # Use 7B models (quick completions)
        else:
            return "standard"  # Use default code model (7B or 8B)
    
    def classify_intent(self, prompt: str, task_description: str = "") -> TaskIntent:
        """
        Classify task intent using heuristic rules.
        
        Args:
            prompt: The full prompt
            task_description: Optional task description
        
        Returns:
            TaskIntent classification
        """
        text = (prompt + " " + task_description).lower()
        
        # Count keyword matches
        reasoning_score = sum(1 for keyword in self.REASONING_KEYWORDS if keyword in text)
        generation_score = sum(1 for keyword in self.GENERATION_KEYWORDS if keyword in text)
        
        # Check for explicit patterns
        if any(pattern in text for pattern in ['fix', 'correct', 'update', 'compatibility', 'deprecated']):
            reasoning_score += 2
        
        if any(pattern in text for pattern in ['generate', 'create', 'implement', 'complete', 'scaffold']):
            generation_score += 2
        
        # Decision logic
        if reasoning_score > generation_score:
            return TaskIntent.REASONING
        elif generation_score > reasoning_score:
            return TaskIntent.GENERATION
        else:
            # Default to reasoning for safety (more conservative)
            return TaskIntent.REASONING
    
    def route_with_intent(
        self,
        prompt: str,
        task_description: str = "",
        task_type: str = "code",
        code_length: int = 0
    ) -> RoutingDecision:
        """
        Route a task with intent classification (multimodel pipeline).
        This is an OPTIONAL enhancement that works alongside the dual-model system.
        
        Use this for tasks that benefit from intent-based routing (reasoning vs generation).
        For standard task-based routing, use get_model_for_task() instead.
        
        Args:
            prompt: The full prompt
            task_description: Task description
            task_type: Type of task (for fallback to dual-model system)
            code_length: Length of code being processed (for complexity detection)
        
        Returns:
            RoutingDecision with model selection and verification plan
        """
        # Classify complexity first (determines if we need larger model: 13-14B or 8B)
        complexity = self.classify_complexity(prompt, task_description, code_length)
        
        # Classify intent
        intent = self.classify_intent(prompt, task_description)
        
        # Determine primary model based on complexity
        # Complex tasks -> 13-14B or 8B models (fits in 11GB VRAM, faster than 34B)
        # Standard/Simple tasks -> 7B models (stay loaded for quick completions)
        if complexity == "complex" and self.complex_model:
            # Use 13-14B or 8B model for complex/high-risk tasks (fits in 11GB VRAM)
            primary_model = self.complex_model
            model_size = "13-14B or 8B"
            if '13' in self.complex_model.lower() or '14' in self.complex_model.lower():
                model_size = "13-14B"
            elif '8' in self.complex_model.lower():
                model_size = "8B"
            print(f"  [COMPLEXITY] Task classified as complex/high-risk -> Using {self.complex_model} ({model_size} model)")
            print(f"  [RESOURCE] {model_size} model fits in 11GB VRAM and is faster than 34B")
        elif intent == TaskIntent.REASONING:
            # Reasoning tasks use Code Llama 7B instruct
            primary_model = self.reasoning_model if self.use_verification else None
            if not primary_model:
                # Fall back to dual-model system (code model for reasoning tasks)
                primary_model = self.code_model
        else:  # GENERATION or standard
            # Generation tasks use StarCoder 7B or default code model
            primary_model = self.generation_model if self.use_verification else None
            if not primary_model:
                # Fall back to dual-model system (code model for generation tasks)
                primary_model = self.code_model
        
        # Verification model (only for generation tasks, not complex)
        if complexity != "complex" and intent == TaskIntent.GENERATION:
            verification_model = (
                self.reasoning_model or self.code_model
                if self.use_verification
                else None
            )
        else:
            verification_model = None  # No verification for complex tasks or reasoning
        
        # Ensure models are loaded (resource management)
        if self.enable_model_unloading:
            self._ensure_model_loaded(primary_model)
            if verification_model:
                self._ensure_model_loaded(verification_model)
            
            # For complex tasks, larger models (13-14B or 8B) can stay loaded longer than 34B would
            if complexity == "complex" and primary_model == self.complex_model:
                # Larger models fit in VRAM better than 34B, can stay loaded for reasonable time
                # The model will be unloaded by the timeout mechanism if not used
                pass
        
        # Calculate confidence (simple heuristic)
        confidence = self._calculate_confidence(prompt, task_description, intent)
        
        # Generate reasoning
        reasoning = f"Intent: {intent.value}, Complexity: {complexity}, Primary: {primary_model}"
        if verification_model:
            reasoning += f", Verification: {verification_model}"
        if complexity == "complex":
            model_size = "13-14B or 8B"
            if '13' in str(primary_model).lower() or '14' in str(primary_model).lower():
                model_size = "13-14B"
            elif '8' in str(primary_model).lower():
                model_size = "8B"
            reasoning += f" ({model_size} model for complex/high-risk tasks - faster than 34B, fits in 11GB VRAM)"
        if not self.use_verification:
            reasoning += " (using dual-model fallback)"
        
        return RoutingDecision(
            intent=intent,
            primary_model=primary_model,
            verification_model=verification_model,
            confidence=confidence,
            reasoning=reasoning,
            complexity=complexity
        )
    
    def _calculate_confidence(
        self,
        prompt: str,
        task_description: str,
        intent: TaskIntent
    ) -> float:
        """Calculate confidence in routing decision (0.0 to 1.0)."""
        text = (prompt + " " + task_description).lower()
        
        # Count strong indicators
        strong_indicators = 0
        
        if intent == TaskIntent.REASONING:
            strong_patterns = ['fix', 'correct', 'update', 'compatibility', 'deprecated', 'missing']
            strong_indicators = sum(1 for pattern in strong_patterns if pattern in text)
        else:  # GENERATION
            strong_patterns = ['generate', 'create', 'implement', 'complete', 'scaffold']
            strong_indicators = sum(1 for pattern in strong_patterns if pattern in text)
        
        # Confidence based on strong indicators
        if strong_indicators >= 2:
            return 0.9
        elif strong_indicators >= 1:
            return 0.7
        else:
            return 0.5  # Lower confidence, may need verification
    
    def create_verification_prompt(
        self,
        original_code: str,
        generated_code: str,
        task_description: str
    ) -> str:
        """
        Create a verification prompt for Code Llama to check StarCoder output.
        
        Args:
            original_code: Original code that was being fixed
            generated_code: Code generated by StarCoder
            task_description: What the task was trying to accomplish
        
        Returns:
            Verification prompt
        """
        return f"""You are a code reviewer. Review this code change for correctness and safety.

## Task
{task_description}

## Original Code
```csharp
{original_code[:1500]}
```

## Generated Code (to review)
```csharp
{generated_code[:2000]}
```

## Review Criteria
1. Does the generated code correctly address the task?
2. Are there any logic errors or regressions?
3. Does it maintain compatibility with the existing codebase?
4. Are there any security issues or unsafe patterns?
5. Does it follow the same coding style and patterns?

## Your Review
Provide a brief review (1-2 sentences) and a verdict:
- APPROVE: Code is correct and safe
- REJECT: Code has issues that need fixing
- REVISE: Code is mostly correct but needs minor changes

Verdict:"""
    
    def score_output_confidence(
        self,
        output: str,
        prompt: str,
        min_length: int = 50,
        max_length: int = 10000
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score output confidence.
        
        Args:
            output: Generated output
            prompt: Original prompt
            min_length: Minimum expected output length
            max_length: Maximum expected output length
        
        Returns:
            (confidence_score, metadata)
        """
        metadata = {}
        score = 1.0
        
        # Length check
        length = len(output)
        if length < min_length:
            score *= 0.5
            metadata['too_short'] = True
        elif length > max_length:
            score *= 0.7
            metadata['too_long'] = True
        
        # Code block check (for code generation)
        if '```' in prompt:
            if '```' not in output:
                score *= 0.6
                metadata['missing_code_block'] = True
            else:
                # Check if code block is complete
                code_blocks = output.count('```')
                if code_blocks % 2 != 0:
                    score *= 0.8
                    metadata['incomplete_code_block'] = True
        
        # Syntax indicators
        if 'error' in output.lower() or 'cannot' in output.lower():
            score *= 0.5
            metadata['error_indicators'] = True
        
        # Completeness indicators
        if output.strip().endswith('...') or output.strip().endswith('// ...'):
            score *= 0.7
            metadata['incomplete'] = True
        
        metadata['length'] = length
        metadata['score'] = score
        
        return score, metadata
    
    def _ensure_model_loaded(self, model_name: Optional[str]):
        """
        Ensure a model is marked as loaded and update its last used time.
        This tracks which models are currently in memory (Ollama loads models on-demand).
        
        Args:
            model_name: Name of the model to mark as loaded
        """
        if not model_name or not self.enable_model_unloading:
            return
        
        with self._resource_lock:
            current_time = time.time()
            self.loaded_models.add(model_name)
            self.model_last_used[model_name] = current_time
            
            # Clean up expired models (models that haven't been used in timeout period)
            self._cleanup_expired_models()
    
    def _cleanup_expired_models(self):
        """Remove models from loaded set if they've exceeded the timeout."""
        if not self.enable_model_unloading:
            return
        
        current_time = time.time()
        expired_models = [
            model for model, last_used in self.model_last_used.items()
            if current_time - last_used > self.model_unload_timeout
        ]
        
        for model in expired_models:
            self.loaded_models.discard(model)
            self.model_last_used.pop(model, None)
    
    def get_loaded_models(self) -> List[str]:
        """
        Get list of currently loaded models (within timeout period).
        
        Returns:
            List of model names that are currently loaded
        """
        if not self.enable_model_unloading:
            return []
        
        with self._resource_lock:
            # Clean up expired models first
            self._cleanup_expired_models()
            # Return list of currently loaded models
            return sorted(list(self.loaded_models))
    
    def get_model_size(self, model_name: str) -> Optional[str]:
        """
        Detect model size from model name.
        
        Args:
            model_name: Name of the model
        
        Returns:
            Model size string ('7b', '8b', '13b', '14b') or None if unknown
        """
        name_lower = model_name.lower()
        
        # Check for size patterns
        if '14b' in name_lower or ':14' in name_lower or '-14' in name_lower:
            return '14b'
        elif '13b' in name_lower or ':13' in name_lower or '-13' in name_lower:
            return '13b'
        elif '8b' in name_lower or ':8' in name_lower or '-8' in name_lower:
            return '8b'
        elif '7b' in name_lower or ':7' in name_lower or '-7' in name_lower:
            return '7b'
        
        return None
    
    def get_cpu_offload_settings(self, model_name: str) -> Dict[str, Any]:
        """
        Get CPU offload settings for a model.
        Returns Ollama API options with num_gpu configured for CPU offload.
        
        Args:
            model_name: Name of the model to get settings for
        
        Returns:
            Dictionary with Ollama API options including num_gpu for CPU offload
            Returns empty dict if CPU offload is disabled or not needed
        """
        if not self.enable_cpu_offload:
            return {}
        
        model_size = self.get_model_size(model_name)
        if not model_size:
            # Unknown model size - check if it's a high VRAM model by checking if it's complex model
            if model_name == self.complex_model:
                # Use default offload for complex models
                num_gpu = self.cpu_offload_config.get('default')
            else:
                # Assume 7B or smaller - no offload needed
                return {}
        else:
            num_gpu = self.cpu_offload_config.get(model_size)
        
        if num_gpu is None:
            # No offload needed for this model size
            return {}
        
        # Return Ollama API options with CPU offload configured
        # num_gpu: number of layers to keep on GPU (rest go to CPU with KV cache in RAM)
        return {
            'num_gpu': num_gpu
        }
    
    def get_ollama_api_options(
        self,
        model_name: str,
        num_thread: Optional[int] = None,
        num_predict: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_ctx: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get complete Ollama API options dictionary with CPU offload configured.
        
        Args:
            model_name: Name of the model
            num_thread: Number of CPU threads (None = auto)
            num_predict: Max tokens to predict (None = default)
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            num_ctx: Context window size (None = default)
        
        Returns:
            Dictionary with all Ollama API options including CPU offload
        """
        options = {}
        
        # Add CPU offload settings for high VRAM models
        offload_settings = self.get_cpu_offload_settings(model_name)
        options.update(offload_settings)
        
        # Add other options
        if num_thread is not None:
            options['num_thread'] = num_thread
        if num_predict is not None:
            options['num_predict'] = num_predict
        if num_ctx is not None:
            options['num_ctx'] = num_ctx
        options['temperature'] = temperature
        options['top_p'] = top_p
        
        return options
    
    def print_model_assignment(self):
        """Print current model assignments for debugging."""
        print("=" * 60)
        print("Ollama Model Router - Model Assignments")
        print("=" * 60)
        print("Dual-Model System (Original):")
        print(f"  Code Generation Model:     {self.code_model}")
        print(f"  Visual/Orchestration Model: {self.visual_model}")
        if self.complex_model:
            model_size = "13-14B or 8B"
            if '13' in self.complex_model.lower() or '14' in self.complex_model.lower():
                model_size = "13-14B"
            elif '8' in self.complex_model.lower():
                model_size = "8B"
            print(f"  Complex Task Model:         {self.complex_model} ({model_size} - faster than 34B, fits in 11GB VRAM)")
        if self.use_verification:
            print("\nMultimodel Pipeline (Enhanced):")
            if self.reasoning_model:
                print(f"  Reasoning Model:            {self.reasoning_model}")
            if self.generation_model:
                print(f"  Generation Model:           {self.generation_model}")
            print(f"  Verification Enabled:        {self.use_verification}")
        else:
            print("\nMultimodel Pipeline: Disabled (use_verification=False)")
        if self.enable_model_unloading:
            print(f"\nResource Management:")
            print(f"  Model Unloading:            Enabled (5 min timeout)")
            loaded = self.get_loaded_models()
            if loaded:
                print(f"  Currently Loaded:            {', '.join(loaded)}")
            else:
                print(f"  Currently Loaded:            None")
        
        if self.enable_cpu_offload:
            print(f"\nCPU Offload (KV Cache in RAM):")
            print(f"  CPU Offload:                 Enabled for high VRAM models")
            print(f"  7B models:                  No offload (fits in VRAM)")
            print(f"  8B models:                  {self.cpu_offload_config.get('8b', 'N/A')} GPU layers (attention cache in RAM)")
            print(f"  13-14B models:              {self.cpu_offload_config.get('13b', 'N/A')} GPU layers (attention cache in RAM)")
            
            # Show offload settings for assigned models
            if self.complex_model:
                offload = self.get_cpu_offload_settings(self.complex_model)
                if offload:
                    print(f"  {self.complex_model}:         {offload.get('num_gpu')} GPU layers (KV cache offloaded to RAM)")
                else:
                    print(f"  {self.complex_model}:         No offload needed")
        
        print(f"\nAvailable Models: {len(self.available_models)}")
        for model in self.available_models:
            model_name = model.get('name')
            offload = self.get_cpu_offload_settings(model_name) if self.enable_cpu_offload else {}
            if offload:
                print(f"  - {model_name} (CPU offload: {offload.get('num_gpu')} GPU layers)")
            else:
                print(f"  - {model_name}")
        print("=" * 60)

# Global router instance
_router: Optional[OllamaModelRouter] = None

def get_router() -> OllamaModelRouter:
    """Get or create the global model router."""
    global _router
    if _router is None:
        _router = OllamaModelRouter()
    return _router

def get_model_for_task(task_type: str) -> str:
    """Convenience function to get model for a task type."""
    return get_router().get_model_for_task(task_type)

def get_code_model() -> str:
    """Convenience function to get code model (CodeLlama-34B preferred)."""
    return get_router().get_code_model()

def get_xml_model() -> str:
    """Convenience function to get model for XML generation (uses code model - CodeLlama-34B)."""
    return get_router().get_model_for_task(TASK_XML)

def get_visual_model() -> str:
    """Convenience function to get visual model."""
    return get_router().get_visual_model()

