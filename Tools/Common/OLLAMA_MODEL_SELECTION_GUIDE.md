# Ollama Model Selection Guide for Space Whale Asset Generation

## Quick Answer

**For Space Whale asset generation, use:**
- **CodeLlama-34B** (best for Blender Python script generation and code correctness)
- **WizardLM-uncensored:latest** (13B, good for general orchestration and visual descriptions)
- **Auto-detection** (system will pick the best available model)

## Model Recommendations

### Primary Recommendation: CodeLlama-34B

**Best for:**
- Blender Python script generation
- Complex code refactoring
- High code correctness requirements

**Download via Ollama:**
```bash
ollama pull codellama:34b
```

**Usage:**
```bash
python space_whale_comprehensive_asset_generator.py --ollama-model codellama:34b
```

### Secondary Recommendation: WizardLM-uncensored:latest (13B)

**Best for:**
- General orchestration tasks
- Natural language prompts
- Visual description generation
- Lower resource requirements

**Already configured as default fallback**

### Auto-Detection

The system automatically detects and uses the best available model with this priority:
1. **CodeLlama-34B** (highest priority for code generation)
2. **CodeLlama-13B** (good code generation, lower resources)
3. **WizardLM-uncensored-13B** (good for instructions)
4. Other 34B models
5. Other 13B+ models
6. 7B models
7. 3B models

## Hardware Requirements

### CodeLlama-34B
- **Full model**: Requires multiple high-memory GPUs (A100/80GB class) or server
- **Quantized (GPTQ)**: Can run on single high-end consumer GPU (24GB+ VRAM)
- **Ollama quantized**: Optimized for consumer hardware, ~20-30GB RAM

### WizardLM-uncensored (13B)
- **Quantized**: Runs on consumer GPUs (8-16GB VRAM)
- **RAM**: ~8-16GB system RAM
- **Good for**: Most desktop systems

## Installation

### Option 1: Ollama (Recommended - Easiest)

```bash
# Install Ollama from https://ollama.ai
# Then pull the model:
ollama pull codellama:34b
# Or for smaller systems:
ollama pull codellama:13b
```

### Option 2: Hugging Face (Full Fidelity)

```bash
# Requires git-lfs
git lfs install
git clone https://huggingface.co/codellama/CodeLlama-34b-hf
# Use with transformers library
```

### Option 3: GPTQ Community Builds (Lower Memory)

Follow specific repo instructions for GPTQ quantized builds.

## Configuration

### Set Model in Batch Files

Edit `StartSpaceWhaleAssetGeneration.bat`:
```batch
set "OLLAMA_MODEL=codellama:34b"
```

### Set Model in PowerShell Scripts

```powershell
.\GenerateSpaceWhaleAssets.ps1 -OllamaModel "codellama:34b"
```

### Set Model in Python Scripts

```python
python space_whale_comprehensive_asset_generator.py --ollama-model codellama:34b
```

## Model Comparison

| Model | Code Quality | Instruction Following | Resource Usage | Best Use Case |
|-------|-------------|----------------------|----------------|---------------|
| **CodeLlama-34B** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | High | Blender Python scripts, complex code |
| **CodeLlama-13B** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Medium | Good balance of quality and speed |
| **WizardLM-uncensored-13B** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Medium | Visual descriptions, orchestration |
| **Llama 3.2** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Low | Quick iterations, lower quality |

## Safety & Best Practices

1. **Always validate generated code** before executing in Blender
2. **Use sandboxed execution** for generated scripts
3. **Check model outputs** for correctness, especially for destructive operations
4. **Prefer official sources** (Meta/Ollama) over community builds for production
5. **Verify checksums** when downloading models

## Troubleshooting

### Model Not Found
```bash
# Check available models
ollama list

# Pull missing model
ollama pull codellama:34b
```

### Out of Memory
- Use quantized models: `codellama:13b` instead of `34b`
- Reduce batch size in generation scripts
- Use `wizardlm-uncensored:latest` (smaller)

### Slow Generation
- Use smaller models for faster iterations
- Use CodeLlama-34B only for final production code
- Enable GPU acceleration in Ollama settings

## Current System Defaults

- **Dual-Model Support**: ✅ Enabled
  - **Code Generation**: CodeLlama-34B (auto-detected)
  - **Visual/Orchestration**: WizardLM-uncensored (auto-detected)
- **Auto-detection**: Enabled by default
- **Fallback**: `wizardlm-uncensored:latest` (if models not available)
- **Priority**: CodeLlama-34B > CodeLlama-13B > WizardLM-uncensored > others

## Dual-Model System

The system now uses **two models concurrently**:
- **CodeLlama-34B** for code generation tasks (Blender Python scripts)
- **WizardLM-uncensored** for visual/orchestration tasks (descriptions, palettes)

See `OLLAMA_DUAL_MODEL_GUIDE.md` for detailed information.

## References

- [Ollama Model Library](https://ollama.ai/library)
- [CodeLlama Official](https://github.com/facebookresearch/codellama)
- [WizardLM](https://github.com/nlpxucan/WizardLM)

