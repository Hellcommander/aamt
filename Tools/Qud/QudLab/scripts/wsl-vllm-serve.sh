#!/usr/bin/env bash
# Turing (sm_75 / RTX 2080 Ti) vLLM 0.29 launcher.
# Default: Qwen2.5-Coder-7B-Instruct-AWQ @ 64k with CPU swap (leave ~2GB for Cursor).
# Usage: serve.sh [HF_REPO_OR_LOCAL_PATH] [extra vllm args...]
set -euo pipefail
export HOME="${HOME:-/home/arendeth}"
export USER="${USER:-arendeth}"
export PATH="/home/arendeth/.local/bin:$PATH"

VENV="/home/arendeth/vllm/.venv"
PY="$VENV/bin/python"
VLLM="$VENV/bin/vllm"

if [[ ! -x "$PY" ]]; then
  echo "vLLM venv missing at $VENV" >&2
  exit 1
fi

DEFAULT_MODEL="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
MODEL="${1:-${QUDLAB_VLLM_MODEL:-${QUDLAB_HF_MODEL:-$DEFAULT_MODEL}}}"
if [[ $# -gt 0 ]]; then
  shift
fi

PORT="${VLLM_PORT:-8000}"
HOST="${VLLM_HOST:-0.0.0.0}"
# ~0.72 of 11GB ≈ 8GB for vLLM; leaves ~2–3GB for Cursor / Windows.
UTIL="${VLLM_GPU_UTIL:-0.72}"
# 7B Coder natively supports 128k; 64k is the practical target with RAM spill.
MAXLEN="${VLLM_MAX_MODEL_LEN:-65536}"
MAXSEQ="${VLLM_MAX_NUM_SEQS:-1}"
# CPU RAM for KV blocks that do not fit in VRAM (GiB).
SWAP="${VLLM_SWAP_SPACE:-24}"
# Weight offload to system RAM if GPU is tight (GiB). 0 = keep weights on GPU.
CPU_OFFLOAD="${VLLM_CPU_OFFLOAD_GB:-0}"
PARSER="${VLLM_TOOL_PARSER:-hermes}"
# AWQ checkpoints: auto. FP16 dense 3B: float16.
DTYPE="${VLLM_DTYPE:-auto}"

if [[ -z "${HF_HOME:-}" ]]; then
  if [[ -d /mnt/d/hf-cache ]]; then
    export HF_HOME=/mnt/d/hf-cache
  elif [[ -d /mnt/c/Users/Arend/.cache/huggingface ]]; then
    export HF_HOME=/mnt/c/Users/Arend/.cache/huggingface
  fi
fi
if [[ -n "${HF_HOME:-}" && -z "${HUGGINGFACE_HUB_CACHE:-}" && -d "${HF_HOME}/hub" ]]; then
  export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
fi

if [[ -n "${HF_TOKEN:-}" ]]; then
  export HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-$HF_TOKEN}"
  echo "HF Hub: authenticated (token in environment)"
else
  echo "HF Hub: no HF_TOKEN in this process — Hub user will be unknown / unauthenticated"
fi

if [[ -z "${CC:-}" ]]; then
  if command -v gcc >/dev/null 2>&1; then
    export CC="$(command -v gcc)"
  fi
fi
if [[ -z "${CC:-}" ]]; then
  echo "Triton needs gcc. In WSL: sudo apt-get install -y build-essential" >&2
  exit 1
fi
export CXX="${CXX:-$(command -v g++ 2>/dev/null || echo "$CC")}"

ATTN="${VLLM_ATTENTION_BACKEND:-TRITON_ATTN}"
export VLLM_USE_V2_MODEL_RUNNER="${VLLM_USE_V2_MODEL_RUNNER:-0}"
export VLLM_WSL2_ENABLE_PIN_MEMORY="${VLLM_WSL2_ENABLE_PIN_MEMORY:-1}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"
unset VLLM_GPU_UTIL VLLM_ATTENTION_BACKEND 2>/dev/null || true

EXTRA=()
if [[ "$CPU_OFFLOAD" != "0" && -n "$CPU_OFFLOAD" ]]; then
  EXTRA+=(--cpu-offload-gb "$CPU_OFFLOAD")
fi

echo "vLLM 0.29.0  model=$MODEL  port=$PORT  dtype=$DTYPE  attn=$ATTN  cc=$CC"
echo "max_model_len=$MAXLEN  gpu_util=$UTIL  swap=${SWAP}GiB  cpu_offload=${CPU_OFFLOAD}GiB  max_seqs=$MAXSEQ"
echo "runner V2=$VLLM_USE_V2_MODEL_RUNNER  WSL pin_memory=$VLLM_WSL2_ENABLE_PIN_MEMORY  HF_HOME=${HF_HOME:-unset}"
echo "OpenAI API: http://127.0.0.1:${PORT}/v1   models: GET /v1/models"
echo "Slot another Hugging Face id:  vllm-serve.bat org/name"

exec "$VLLM" serve "$MODEL" \
  --served-model-name "$MODEL" vllm vllm-backend local-qwen-3b local-qwen-7b \
  --host "$HOST" \
  --port "$PORT" \
  --dtype "$DTYPE" \
  --enforce-eager \
  --attention-backend "$ATTN" \
  --gpu-memory-utilization "$UTIL" \
  --max-model-len "$MAXLEN" \
  --max-num-seqs "$MAXSEQ" \
  --swap-space "$SWAP" \
  --trust-remote-code \
  --enable-auto-tool-choice \
  --tool-call-parser "$PARSER" \
  --enable-prefix-caching \
  "${EXTRA[@]}" \
  "$@"
