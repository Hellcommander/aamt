# Model Migration Guide: CodeLlama → StarCoder/Code Llama 7B

## Overview

The tools have been updated to prioritize **StarCoder 7B** and **Code Llama 7B (instruct)** over CodeLlama 34B for better code generation and to avoid indexing issues when referencing source code.

## Why the Change?

### CodeLlama 34B Issues
- **Indexing problems** when referencing source code
- Higher VRAM requirements (~15-20 GB)
- Slower inference time

### StarCoder 7B / Code Llama 7B Benefits
- **Better code generation** and completions
- **No indexing issues** when referencing source code
- Lower VRAM footprint (~4-10 GB with quantization)
- Faster inference
- Better suited for patch generation and code fixes

## Model Priority Order

The tools now use this priority order:

1. **StarCoder 7B** (`starcoder:7b`) - Best for raw code generation
2. **StarCoder 2 7B** (`starcoder2:7b`) - If available
3. **Code Llama 7B Instruct** (`codellama:7b-instruct`) - Best for patch suggestions
4. **Code Llama 7B** (`codellama:7b`) - Base variant
5. **Qwen2.5 Coder 7B** (`qwen2.5-coder:7b`) - Alternative
6. **DeepSeek Coder 6.7B** (`deepseek-coder:6.7b`) - Alternative
7. **CodeLlama 34B** (`codellama:34b`) - Fallback for complex reasoning
8. **CodeLlama 13B** (`codellama:13b`) - Fallback
9. **Llama 3.2 3B** (`llama3.2:3b`) - Lightweight fallback

## Installation

### Install StarCoder 7B
```bash
ollama pull starcoder:7b
```

### Install Code Llama 7B Instruct
```bash
ollama pull codellama:7b-instruct
```

### Install Code Llama 7B Base
```bash
ollama pull codellama:7b
```

## Updated Tools

### 1. Qud Mod Fixer (`Qud/qud_mod_fixer.py`)
- **Default**: Automatically selects best available model (StarCoder 7B preferred)
- **Fallback**: CodeLlama 34B if StarCoder/Code Llama 7B not available
- Shows which model is being used and its characteristics

### 2. Terraria Mod Fixer (`TerrariaMods/tmodloader_mod_fixer.py`)
- **Default**: `starcoder:7b`**
- Can be overridden with `--model` argument
- Example: `python tmodloader_mod_fixer.py --model codellama:7b-instruct`

### 3. Shared Ollama Integration (`Shared/ollama_integration.py`)
- Updated `preferred_models` to prioritize StarCoder 7B and Code Llama 7B
- CodeLlama 34B kept as fallback for complex reasoning tasks

## VRAM Requirements

### Quantized Models (Recommended)
- **StarCoder 7B (4-bit)**: ~4-6 GB VRAM
- **StarCoder 7B (8-bit)**: ~6-8 GB VRAM
- **Code Llama 7B (4-bit)**: ~4-6 GB VRAM
- **Code Llama 7B (8-bit)**: ~6-8 GB VRAM

### Full Precision (Not Recommended)
- **StarCoder 7B**: ~14 GB VRAM
- **Code Llama 7B**: ~14 GB VRAM

## When to Use CodeLlama 34B

CodeLlama 34B is still useful for:
- **Complex reasoning tasks** that require deeper understanding
- **Short answer generation** (as mentioned in your requirements)
- **Fallback** when 7B models don't produce good results

However, for most code fixing tasks, StarCoder 7B or Code Llama 7B will perform better and faster.

## Configuration

### Override Model Selection

#### Qud Mod Fixer
The model is auto-selected, but you can check which one is being used in the output:
```
Using model: starcoder:7b with 31 threads
(StarCoder 7B - optimized for code generation, ~4-10 GB VRAM)
```

#### Terraria Mod Fixer
```bash
# Use StarCoder 7B (default)
python tmodloader_mod_fixer.py --mod-source "path/to/mod"

# Use Code Llama 7B Instruct
python tmodloader_mod_fixer.py --mod-source "path/to/mod" --model codellama:7b-instruct

# Use CodeLlama 34B (fallback)
python tmodloader_mod_fixer.py --mod-source "path/to/mod" --model codellama:34b
```

## Performance Comparison

| Model | Code Generation | Source Code Reference | VRAM (quantized) | Speed |
|-------|----------------|----------------------|------------------|-------|
| StarCoder 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ~4-10 GB | Fast |
| Code Llama 7B Instruct | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ~4-10 GB | Fast |
| CodeLlama 34B | ⭐⭐⭐ | ⭐⭐ | ~15-20 GB | Slow |

## Troubleshooting

### Model Not Found
If you see "model not found" errors:
1. Install the model: `ollama pull starcoder:7b`
2. Check available models: `ollama list`
3. The tool will automatically fall back to available models

### Out of Memory
If you get OOM errors:
1. Use quantized models (4-bit or 8-bit)
2. Reduce context length in the tool
3. Use a smaller model like `llama3.2:3b`

### Poor Results
If the 7B models don't produce good results:
1. Try Code Llama 7B Instruct instead of StarCoder
2. Fall back to CodeLlama 34B for complex tasks
3. Check that the model is properly quantized

## Migration Checklist

- [x] Updated `ollama_integration.py` model preferences
- [x] Updated `tmodloader_mod_fixer.py` default model
- [x] Updated `qud_mod_fixer.py` model selection logic
- [x] Added informative output showing which model is used
- [ ] Install StarCoder 7B: `ollama pull starcoder:7b`
- [ ] Install Code Llama 7B Instruct: `ollama pull codellama:7b-instruct`
- [ ] Test tools with new models
- [ ] Verify VRAM usage is acceptable

## Notes

- CodeLlama 34B is still available as a fallback
- All tools maintain backward compatibility
- Model selection is automatic based on availability
- You can always override with command-line arguments where supported

