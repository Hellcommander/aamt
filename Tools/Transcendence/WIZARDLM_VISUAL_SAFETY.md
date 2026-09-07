# WizardLM for Visual Tasks - Safety Restrictions

## Summary

WizardLM-uncensored is now **exclusively used for visual-related tasks** and is **restricted from modifying system files**.

## Model Assignment

| Task Type | Model | Restrictions |
|-----------|-------|--------------|
| **Visual Descriptions** | WizardLM-uncensored-13B | ✅ Visual tasks only |
| **Color Palettes** | WizardLM-uncensored-13B | ✅ Visual tasks only |
| **FX Descriptions** | WizardLM-uncensored-13B | ✅ Visual tasks only |
| **Material Descriptions** | WizardLM-uncensored-13B | ✅ Visual tasks only |
| **Code Generation** | CodeLlama-34B | ❌ Not WizardLM |
| **XML Generation** | CodeLlama-34B | ❌ Not WizardLM |
| **System Files** | ❌ **BLOCKED** | ❌ Never modified |

## Safety Features

### 1. File Safety Validator (`file_safety_validator.py`)

**Protected System Directories:**
- `C:\Windows` and all subdirectories
- `C:\Windows\System32`
- `C:\Windows\SysWOW64`
- `C:\Program Files` and `C:\Program Files (x86)`
- `C:\ProgramData`
- User profile system directories (`AppData\Local\Microsoft`, etc.)
- Registry paths (`HKLM`, `HKCU`, etc.)
- System Volume Information
- Recycle Bin

**Allowed Output Directories:**
- `Output/` (relative to script root)
- `TestOutput/`
- `AI_Generated_Assets/`
- `Generated/`
- `Temp/`
- `Logs/`
- Any subdirectory of script root (but not system directories)

### 2. Visual Generator Protection

The `ollama_visual_variation_generator.py` now:
- ✅ Validates all output paths before writing
- ✅ Blocks writes to system directories
- ✅ Uses WizardLM-uncensored for visual tasks only
- ✅ Prevents accidental system file modifications

### 3. Model Router Restrictions

The `ollama_model_router.py`:
- ✅ Routes visual tasks to WizardLM-uncensored
- ✅ Routes code/XML tasks to CodeLlama-34B
- ✅ Never allows WizardLM to handle code generation
- ✅ Clear separation of concerns

## Usage

### Visual Tasks (WizardLM)
```python
from ollama_model_router import get_visual_model, TASK_VISUAL
model = get_visual_model()  # Returns WizardLM-uncensored-13B
```

### Code Tasks (CodeLlama)
```python
from ollama_model_router import get_code_model, TASK_CODE
model = get_code_model()  # Returns CodeLlama-34B
```

### Safe File Writing
```python
from file_safety_validator import safe_write_file, get_script_root

script_root = get_script_root()
success, error = safe_write_file(
    "Output/visual_palette.json",
    json_content,
    script_root=script_root
)

if not success:
    print(f"Error: {error}")
```

## Validation Examples

### ✅ Allowed Paths
```
Output/SpaceWhaleAssets/VisualLanguage/palette.json
TestOutput/visual_test.json
AI_Generated_Assets/color_scheme.json
```

### ❌ Blocked Paths
```
C:\Windows\System32\config.json
C:\Program Files\MyApp\data.json
HKLM\Software\MyApp\config.json
C:\Windows\palette.json
```

## Error Messages

If a script tries to write to a system directory:
```
ERROR: Cannot write to system directory: C:\Windows\config.json
ERROR: Parent directory is a system directory: C:\Program Files
ERROR: Output path must be in allowed directories: C:\System32\data.json
```

## Benefits

1. **Safety**: Prevents accidental system file corruption
2. **Security**: Blocks malicious or accidental system modifications
3. **Clarity**: Clear separation between visual and code tasks
4. **Reliability**: Ensures scripts only modify intended directories

## Implementation Status

- ✅ File safety validator created
- ✅ Visual generator protected
- ✅ Model router configured for WizardLM visual tasks
- ✅ System directory blocking active
- ✅ Output path validation implemented

---

**Last Updated:** Current session  
**Status:** ✅ WizardLM restricted to visual tasks, system files protected

