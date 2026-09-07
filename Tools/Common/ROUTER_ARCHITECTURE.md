# Ollama Model Router Architecture

## Overview

The `OllamaModelRouter` supports **two routing systems** that can work independently or together:

1. **Dual-Model System** (Original - Default)
2. **Multimodel Pipeline** (Optional Enhancement)

## Dual-Model System (Original)

This is the **default behavior** and preserves backward compatibility.

### Purpose
Routes tasks based on **task type** (code vs visual).

### Models
- **Code Model**: CodeLlama-34B (or best available) for code/XML tasks
- **Visual Model**: WizardLM (or best available) for visual/orchestration tasks

### Usage
```python
from ollama_model_router import get_model_for_task, TASK_CODE, TASK_VISUAL

# Get model for code task
code_model = get_model_for_task(TASK_CODE)  # Returns CodeLlama-34B

# Get model for visual task
visual_model = get_model_for_task(TASK_VISUAL)  # Returns WizardLM
```

### When to Use
- Standard code generation/refactoring
- Visual descriptions, color palettes
- XML generation
- General orchestration tasks

## Multimodel Pipeline (Optional)

This is an **optional enhancement** for tasks that benefit from intent-based routing.

### Purpose
Routes tasks based on **intent** (reasoning vs generation) with verification.

### Models
- **Reasoning Model**: Code Llama 7B (instruct) for reasoning/refactoring tasks
- **Generation Model**: StarCoder 7B for code generation tasks
- **Verification**: Code Llama verifies StarCoder outputs

### Usage
```python
from ollama_model_router import OllamaModelRouter, TaskIntent

# Enable verification for multimodel pipeline
router = OllamaModelRouter(use_verification=True)

# Route with intent classification
routing = router.route_with_intent(
    prompt="Fix API compatibility issues",
    task_description="Update mod to newer API"
)

# routing.intent = TaskIntent.REASONING
# routing.primary_model = "codellama:7b-instruct"
# routing.verification_model = None (reasoning tasks don't need verification)
```

### When to Use
- Code fixes that need reasoning/analysis
- Code generation that needs verification
- Tasks where quality assurance is critical

## Key Differences

| Feature | Dual-Model System | Multimodel Pipeline |
|---------|------------------|---------------------|
| **Routing Basis** | Task type (code/visual) | Intent (reasoning/generation) |
| **Default Models** | CodeLlama-34B, WizardLM | Code Llama 7B, StarCoder 7B |
| **Verification** | None | Code Llama verifies StarCoder |
| **Confidence Scoring** | None | Yes (filters poor outputs) |
| **Enabled By** | Default (always on) | `use_verification=True` |
| **Backward Compatible** | Yes | Yes (optional) |

## Coexistence

Both systems can coexist:

1. **Dual-model system** is always active (default behavior)
2. **Multimodel pipeline** is optional (enabled with `use_verification=True`)
3. When multimodel is disabled, `route_with_intent()` falls back to dual-model system
4. Existing code using `get_model_for_task()` continues to work unchanged

## Example: Mod Fixer

The mod fixer uses the multimodel pipeline:

```python
# Initialize with verification enabled
router = OllamaModelRouter(use_verification=True)

# Route with intent
routing = router.route_with_intent(
    prompt=prompt,
    task_description="Fix code issues"
)

# Use primary model
response = call_ollama(prompt, model_name=routing.primary_model)

# If generation task, verify with Code Llama
if routing.verification_model:
    verification = call_ollama(
        router.create_verification_prompt(...),
        model_name=routing.verification_model
    )
```

## Migration Guide

### Existing Code (No Changes Needed)
```python
# This continues to work as before
from ollama_model_router import get_model_for_task, TASK_CODE
model = get_model_for_task(TASK_CODE)
```

### New Code (Using Multimodel Pipeline)
```python
# Enable multimodel pipeline
from ollama_model_router import OllamaModelRouter
router = OllamaModelRouter(use_verification=True)

# Use intent-based routing
routing = router.route_with_intent(prompt, task_description)
model = routing.primary_model
```

## Summary

- **Dual-Model System**: Original, always active, task-based routing
- **Multimodel Pipeline**: Optional enhancement, intent-based routing with verification
- **Both coexist**: No breaking changes, backward compatible
- **Choose based on needs**: Use dual-model for standard tasks, multimodel for quality-critical tasks

