# CPU Key/Value Offload for Ollama Models

## Overview

CPU offload enables attention key/value (KV) caches to live in RAM instead of VRAM for high VRAM models. This allows larger models (13-14B, 8B) to run on 11GB GPUs by offloading some computation to CPU while keeping attention caches in system RAM.

## How It Works

- **num_gpu**: Controls how many transformer layers run on GPU
- **Remaining layers**: Run on CPU with attention KV cache in RAM
- **Result**: Lower VRAM usage, higher RAM usage, slightly slower but fits in 11GB VRAM

## Configuration

The router automatically configures CPU offload based on model size:

| Model Size | GPU Layers | CPU Layers | KV Cache Location |
|------------|-----------|------------|-------------------|
| 7B         | All       | None       | VRAM (no offload) |
| 8B         | 20        | Rest       | RAM               |
| 13-14B     | 15        | Rest       | RAM               |

## Usage

### Python

```python
from ollama_model_router import get_router

router = get_router()

# Get options with CPU offload for a model
options = router.get_ollama_api_options(
    model_name="codellama:13b",
    num_thread=8,
    num_predict=2048,
    temperature=0.7,
    top_p=0.9
)

# options will include: {'num_gpu': 15, 'num_thread': 8, ...}
# Use in Ollama API request
```

### PowerShell

```powershell
# Import the module
Import-Module ".\Tools\Common\OllamaCpuOffload.psm1"

# Get options with CPU offload
$options = Get-OllamaCpuOffloadOptions -ModelName "codellama:13b" -NumThread 8

# $options will include num_gpu if offload is needed
# Use in Ollama API request body
```

### Direct API Call

```powershell
$body = @{
    model = "codellama:13b"
    prompt = "Your prompt here"
    options = Get-OllamaCpuOffloadOptions -ModelName "codellama:13b" -NumThread 8 -NumPredict 2048
}

$response = Invoke-RestMethod -Uri "http://localhost:11434/api/generate" `
    -Method Post `
    -Body ($body | ConvertTo-Json -Depth 10) `
    -ContentType "application/json"
```

## Benefits

1. **Fits in 11GB VRAM**: 13-14B models can run without OOM errors
2. **Uses abundant RAM**: Attention caches stored in system RAM
3. **Automatic**: Router detects model size and applies appropriate settings
4. **Configurable**: Can adjust num_gpu layers per model size

## Adjusting Settings

Edit `ollama_model_router.py` to change offload settings:

```python
self.cpu_offload_config = {
    '7b': None,      # No offload
    '8b': 20,       # 20 GPU layers
    '13b': 15,      # 15 GPU layers (more offload)
    '14b': 15,      # 15 GPU layers
    'default': 20   # Default for unknown large models
}
```

**Lower num_gpu = More CPU offload = Less VRAM usage, More RAM usage, Slightly slower**

## Verification

Check if CPU offload is enabled:

```python
router = get_router()
router.print_model_assignment()  # Shows CPU offload status
```

Or check for a specific model:

```python
offload = router.get_cpu_offload_settings("codellama:13b")
# Returns: {'num_gpu': 15} if offload is enabled
```

## Notes

- CPU offload is automatically enabled for models 8B and larger
- 7B models don't need offload (fit easily in 11GB VRAM)
- Performance impact is minimal (attention cache access is still fast in RAM)
- Works best with models that have good CPU inference support
