#!/usr/bin/env bash
# Serve one of the open models evaluated on DocAtlas-Bench with vLLM (OpenAI-compatible API).
#
#   ./serve_vllm.sh <model> [port] [extra `vllm serve` arguments ...]
#
#   CUDA_VISIBLE_DEVICES=0 ./serve_vllm.sh qwen3-vl-2b 8000
#
# The server answers on http://localhost:<port>/v1 and serves the model under the name <model>,
# which is the value to pass as --model to the inference clients. It runs in the foreground
# (Ctrl-C stops it). Requires vLLM (`pip install vllm`); the flags below were used with vLLM 0.30.0.
# Set HOST=0.0.0.0 to accept connections from other machines.
set -euo pipefail

MODELS="qwen3-vl-2b qwen2.5-vl-3b nanonets-ocr-s nanonets-ocr2-3b deepseek-ocr dots-ocr"

if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  echo "usage: $0 <model> [port] [extra vllm serve arguments ...]" >&2
  echo "models: $MODELS" >&2
  exit 2
fi

MODEL=$1
shift
PORT=8000
if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
  PORT=$1
  shift
fi

COMMON=(--host "${HOST:-127.0.0.1}" --port "$PORT" --served-model-name "$MODEL" --seed 0
        --limit-mm-per-prompt '{"image":1}')

case "$MODEL" in
  qwen3-vl-2b)
    exec vllm serve Qwen/Qwen3-VL-2B-Instruct "${COMMON[@]}" --max-model-len 32768 "$@" ;;
  # --generation-config vllm (next three models): decode with vLLM's defaults rather than the sampling
  # defaults in the checkpoint's generation_config.json, which add a repetition penalty of 1.05.
  qwen2.5-vl-3b)
    exec vllm serve Qwen/Qwen2.5-VL-3B-Instruct "${COMMON[@]}" --max-model-len 32768 \
      --generation-config vllm "$@" ;;
  nanonets-ocr-s)
    exec vllm serve nanonets/Nanonets-OCR-s "${COMMON[@]}" --max-model-len 32768 \
      --generation-config vllm "$@" ;;
  nanonets-ocr2-3b)
    exec vllm serve nanonets/Nanonets-OCR2-3B "${COMMON[@]}" --max-model-len 32768 \
      --generation-config vllm "$@" ;;
  deepseek-ocr)
    # Flags of the vLLM recipe for DeepSeek-OCR: the no-repeat n-gram logits processor that
    # run_inference_deepseek_ocr.py configures per request, and no prefix / multimodal caches.
    # TRITON_ALLOW_NON_CONSTEXPR_GLOBALS works around a Triton compile error in the model's SAM
    # attention kernel with vLLM 0.30.0 / Triton 3.7 (harmless with other versions).
    export TRITON_ALLOW_NON_CONSTEXPR_GLOBALS=1
    exec vllm serve deepseek-ai/DeepSeek-OCR "${COMMON[@]}" \
      --logits_processors vllm.model_executor.models.deepseek_ocr:NGramPerReqLogitsProcessor \
      --no-enable-prefix-caching --mm-processor-cache-gb 0 "$@" ;;
  dots-ocr)
    # Flags from the dots.ocr README.
    exec vllm serve rednote-hilab/dots.ocr "${COMMON[@]}" --trust-remote-code \
      --chat-template-content-format string "$@" ;;
  *)
    echo "unknown model: $MODEL (known: $MODELS)" >&2
    echo "any other model that vLLM supports can be served with plain \`vllm serve <hf id>\`." >&2
    exit 2 ;;
esac
