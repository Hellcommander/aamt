# Ollama Dual Model Support Guide

## Overview

The Space Whale asset generation system now supports **dual-model usage**, intelligently routing different task types to the most appropriate model:

- **CodeLlama-34B** (or best available code model) → Code generation tasks
- **WizardLM-uncensored** (or best available instruction model) → Visual/orchestration tasks

## How It Works

### Model Router

The `ollama_model_router.py` module automatically:
1. Detects all available Ollama models
2. Assigns CodeLlama models to code generation tasks
3. Assigns WizardLM/instruction models to visual/orchestration tasks
4. Falls back gracefully if models aren't available

### Task Routing

| Task Type | Model Used | Examples |
|-----------|------------|----------|
| **Code Generation** | CodeLlama-34B | Blender Python scripts, code refactoring, script generation |
| **Visual Descriptions** | WizardLM-uncensored | Color palettes, visual language, FX descriptions |
| **Orchestration** | WizardLM-uncensored | High-level planning, task coordination |
| **Audio Descriptions** | WizardLM-uncensored | Audio generation prompts |

## Usage

### Automatic (Recommended)

The system automatically detects and uses the best models:

```bash
python space_whale_comprehensive_asset_generator.py
```

This will:
- Auto-detect CodeLlama-34B for code tasks
- Auto-detect WizardLM-uncensored for visual tasks
- Print model assignments on startup

### Manual Override

You can specify models explicitly:

```bash
python space_whale_comprehensive_asset_generator.py \
    --ollama-model wizardlm-uncensored:latest \
    --ollama-code-model codellama:34b
```

### In Python Code

```python
from ollama_model_router import get_code_model, get_visual_model, TASK_CODE, TASK_VISUAL

# Get models for specific tasks
code_model = get_code_model()  # Returns CodeLlama-34B if available
visual_model = get_visual_model()  # Returns WizardLM-uncensored if available

# Or use task-based routing
from ollama_model_router import get_model_for_task
model = get_model_for_task(TASK_CODE)  # Returns appropriate model for code tasks
```

## Model Detection Priority

### Code Models (Priority Order)
1. **CodeLlama-34B** (highest priority)
2. **CodeLlama-13B**
3. Other CodeLlama variants
4. Largest available model (fallback)

### Visual Models (Priority Order)
1. **WizardLM-uncensored-13B** (highest priority)
2. **WizardLM-uncensored** (any size)
3. **WizardLM** (any variant)
4. **Llama-13B+** models
5. Largest available model (fallback)

## Concurrent Model Usage

Ollama can run **two different models concurrently** if you have enough VRAM/RAM:

- **CodeLlama-34B** (~19GB) + **WizardLM-uncensored** (~7.4GB) = ~26.4GB total
- Both models can be loaded and serve requests simultaneously
- Tasks are automatically routed to the appropriate model

### Memory Requirements

| Configuration | VRAM/RAM Needed |
|---------------|-----------------|
| CodeLlama-34B + WizardLM-uncensored | ~26-30GB |
| CodeLlama-13B + WizardLM-uncensored | ~15-20GB |
| Quantized models | Lower (varies by quantization) |

## Benefits

1. **Better Code Quality**: CodeLlama-34B produces higher-quality Blender Python scripts
2. **Better Visual Descriptions**: WizardLM-uncensored excels at creative visual descriptions
3. **Optimal Resource Usage**: Each model handles tasks it's best at
4. **Automatic Routing**: No manual configuration needed
5. **Graceful Fallback**: Works even if only one model is available

## Troubleshooting

### Both Models Not Loading

If you get out-of-memory errors:
- Use quantized models (smaller memory footprint)
- Use CodeLlama-13B instead of 34B
- Run models sequentially instead of concurrently

### Wrong Model Used

Check model assignments:
```python
from ollama_model_router import get_router
router = get_router()
router.print_model_assignment()
```

### Model Not Detected

Ensure Ollama is running:
```bash
ollama list
```

If models aren't showing up, pull them:
```bash
ollama pull codellama:34b
ollama pull wizardlm-uncensored:latest
```

## Configuration

### Environment Variables

You can set Ollama concurrency:
```bash
export OLLAMA_NUM_PARALLEL=4  # Allow 4 parallel requests per model
```

### Model Override

In scripts, you can override model selection:
```python
# Force specific model for a task
from ollama_model_router import OllamaModelRouter
router = OllamaModelRouter()
router.code_model = "codellama:13b"  # Override code model
router.visual_model = "llama3.2"  # Override visual model
```

## Performance Tips

1. **Pre-load Models**: Models are loaded on first use; pre-loading can reduce latency
2. **Batch Requests**: Group similar tasks to maximize throughput
3. **Monitor Memory**: Watch VRAM/RAM usage to avoid OOM errors
4. **Use Quantized Models**: If memory is limited, use quantized variants

## Example Output

When running asset generation, you'll see:

```
============================================================
Ollama Model Router - Model Assignments
============================================================
Code Generation Model:     codellama:34b
Visual/Orchestration Model: wizardlm-uncensored:latest
Available Models: 2
  - codellama:34b
  - wizardlm-uncensored:latest
============================================================
Auto-detected Visual/Orchestration model: wizardlm-uncensored:latest
Auto-detected Code Generation model: codellama:34b
```

This confirms both models are detected and assigned correctly.

