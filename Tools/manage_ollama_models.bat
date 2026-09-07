@echo off
REM Ollama Model Management Script
REM Install recommended models and uninstall 34B model

echo ========================================
echo Ollama Model Management
echo ========================================
echo.

REM Uninstall 34B models (too slow for 11GB VRAM)
echo Uninstalling 34B models (too slow for 11GB VRAM)...
ollama rm codellama:34b 2>nul
ollama rm codellama:34b-instruct 2>nul
ollama rm codellama:34b-python 2>nul
echo 34B models removed (if they existed)
echo.

REM Install recommended distilled/smaller models
echo Installing recommended models for 11GB VRAM...
echo.

REM Option 1: Qwen2.5-Coder 7B (excellent for structured outputs)
echo [1/5] Installing Qwen2.5-Coder 7B...
ollama pull qwen2.5-coder:7b
echo.

REM Option 2: CodeLlama 13B (good for complex tasks, fits in 11GB)
echo [2/5] Installing CodeLlama 13B...
ollama pull codellama:13b
echo.

REM Option 3: Llama 3.1 8B (balanced, good for polish stage)
echo [3/5] Installing Llama 3.1 8B...
ollama pull llama3.1:8b
echo.

REM Option 4: CodeLlama 7B-instruct (deterministic code/assets)
echo [4/5] Installing CodeLlama 7B-instruct...
ollama pull codellama:7b-instruct
echo.

REM Option 5: DeepSeek-R1 7B (creative drafts) - optional
echo [5/5] Installing DeepSeek-R1 7B (optional, for creative drafts)...
ollama pull deepseek-r1:7b
echo.

echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Installed models:
ollama list
echo.
echo Note: 34B models have been removed. Use 13-14B or 8B models for complex tasks.
echo These models fit in 11GB VRAM and are faster than 34B.
echo.
echo CPU Offload: Enabled for 8B+ models (KV cache in RAM)
echo - 7B models: No offload needed (fits in VRAM)
echo - 8B models: 20 GPU layers (attention cache in RAM)
echo - 13-14B models: 15 GPU layers (attention cache in RAM)
echo.
echo See Tools\Common\CPU_OFFLOAD_README.md for details.
pause
