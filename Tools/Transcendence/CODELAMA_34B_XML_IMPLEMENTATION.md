# CodeLlama-34B for Code & XML Tasks

## Summary

The dual-model router now ensures **CodeLlama-34B** is used for all code-related tasks, including XML generation.

## Changes Made

### 1. Enhanced Model Router (`ollama_model_router.py`)

**Improved CodeLlama-34B Detection:**
- ✅ More robust pattern matching for CodeLlama-34B variants
- ✅ Handles formats: `codellama:34b`, `codellama-34b`, `codellama:34b-instruct`, etc.
- ✅ Priority system: CodeLlama-34B (100) > CodeLlama-13B (90) > CodeLlama-7B (85)

**Added XML Task Type:**
- ✅ `TASK_XML` constant added
- ✅ XML tasks route to code model (CodeLlama-34B)
- ✅ `get_xml_model()` convenience function

### 2. Updated AssetMakerAI.ps1

**XML Generation Uses Code Model:**
- ✅ `Generate-AssetXML` function now uses `Get-CodeModel()`
- ✅ Automatically detects CodeLlama-34B for XML tasks
- ✅ Falls back gracefully if CodeLlama not available

**New Function:**
- ✅ `Get-CodeModel()` - Gets CodeLlama-34B from router or detects directly

## Model Assignment

| Task Type | Model | Priority |
|-----------|-------|----------|
| **Code Generation** | CodeLlama-34B | 100 |
| **XML Generation** | CodeLlama-34B | 100 |
| **Blender Python** | CodeLlama-34B | 100 |
| **Visual Descriptions** | WizardLM-uncensored | 100 |
| **Color Palettes** | WizardLM-uncensored | 100 |

## Usage

### XML Generation (Automatic)
```powershell
.\AssetMakerAI.ps1 -Action CreateXML -AssetType Ship -InputData "MyShip"
# Automatically uses CodeLlama-34B
```

### Code Generation (Automatic)
```python
from ollama_model_router import get_code_model, TASK_CODE
model = get_code_model()  # Returns CodeLlama-34B if available
```

### XML Generation (Explicit)
```python
from ollama_model_router import get_xml_model, TASK_XML
model = get_xml_model()  # Returns CodeLlama-34B (same as code model)
```

## Detection Priority

1. **CodeLlama-34B** (highest priority)
   - Pattern: `*codellama*34*`, `*codellama:34*`, `*codellama-34*`
   - Priority: 100

2. **CodeLlama-13B** (fallback)
   - Pattern: `*codellama*13*`, `*codellama:13*`, `*codellama-13*`
   - Priority: 90

3. **CodeLlama-7B** (smaller fallback)
   - Pattern: `*codellama*7*`, `*codellama:7*`, `*codellama-7*`
   - Priority: 85

4. **Other Code Models** (last resort)
   - Priority: 70

5. **WizardLM-uncensored** (final fallback)
   - Used only if no CodeLlama models available

## Benefits

1. **Better XML Quality**: CodeLlama-34B produces more accurate XML syntax
2. **Better Code Quality**: CodeLlama-34B excels at code generation
3. **Automatic Routing**: No manual model selection needed
4. **Graceful Fallback**: Works even if CodeLlama-34B not installed

## Verification

Test the router:
```powershell
python test_dual_model_system.py
```

Check model assignment:
```python
from ollama_model_router import get_router
router = get_router()
router.print_model_assignment()
```

Expected output:
```
Code Generation Model:     codellama:34b
Visual/Orchestration Model: wizardlm-uncensored:latest
```

---

**Last Updated:** Current session  
**Status:** ✅ CodeLlama-34B now used for all code and XML tasks

