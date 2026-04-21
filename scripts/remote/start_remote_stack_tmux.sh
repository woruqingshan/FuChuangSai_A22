#!/usr/bin/env bash
set -euo pipefail

if [ -f /root/autodl-tmp/a22/env.sh ]; then
  # shellcheck disable=SC1091
  source /root/autodl-tmp/a22/env.sh
fi

export A22_CODE="${A22_CODE:-/root/autodl-tmp/a22/code/FuChuangSai_A22}"
export A22_MODEL_ROOT="${A22_MODEL_ROOT:-/root/autodl-tmp/a22/models}"
export A22_ENV_ROOT="${A22_ENV_ROOT:-/root/autodl-tmp/a22/.uv_envs}"
export A22_TMP_ROOT="${A22_TMP_ROOT:-/root/autodl-tmp/a22/tmp}"
export A22_LOG_ROOT="${A22_LOG_ROOT:-/root/autodl-tmp/a22/logs}"
export AVATAR_ENV_NAME="${AVATAR_ENV_NAME:-avatar-service}"
export AVATAR_RENDERER_BACKEND="${AVATAR_RENDERER_BACKEND:-soulxflashhead}"

export QWEN_CUDA_VISIBLE_DEVICES="${QWEN_CUDA_VISIBLE_DEVICES:-0}"
export SPEECH_CUDA_VISIBLE_DEVICES="${SPEECH_CUDA_VISIBLE_DEVICES:-0}"
export VISION_CUDA_VISIBLE_DEVICES="${VISION_CUDA_VISIBLE_DEVICES:-0}"
export AVATAR_CUDA_VISIBLE_DEVICES="${AVATAR_CUDA_VISIBLE_DEVICES:-0}"

export QWEN_MODEL_PATH="${QWEN_MODEL_PATH:-$A22_MODEL_ROOT/Qwen2.5-7B-Instruct}"
export QWEN_MODEL_NAME="${QWEN_MODEL_NAME:-Qwen2.5-7B-Instruct}"
export QWEN_GPU_MEMORY_UTILIZATION="${QWEN_GPU_MEMORY_UTILIZATION:-0.28}"
export QWEN_MAX_MODEL_LEN="${QWEN_MAX_MODEL_LEN:-4096}"
export QWEN_MAX_NUM_SEQS="${QWEN_MAX_NUM_SEQS:-2}"

export ASR_MODEL_PATH="${ASR_MODEL_PATH:-$A22_MODEL_ROOT/Qwen3-ASR-1.7B}"
export VISION_MODEL_PATH="${VISION_MODEL_PATH:-$A22_MODEL_ROOT/Qwen2.5-VL-7B-Instruct}"
export TTS_MODE="${TTS_MODE:-cosyvoice_300m_instruct}"
export TTS_MODEL_PATH="${TTS_MODEL_PATH:-$A22_MODEL_ROOT/CosyVoice-300M-Instruct}"
export TTS_REPO_PATH="${TTS_REPO_PATH:-$A22_MODEL_ROOT/CosyVoice}"

if [ -z "${SOULX_ROOT:-}" ]; then
  if [ -d "$A22_MODEL_ROOT/SoulX-FlashHead" ]; then
    SOULX_ROOT="$A22_MODEL_ROOT/SoulX-FlashHead"
  else
    SOULX_ROOT="$A22_MODEL_ROOT/SoulXFlashHead"
  fi
fi
export SOULX_ROOT
export SOULX_PYTHON="${SOULX_PYTHON:-/root/autodl-tmp/a22/.uv_envs/soulx-full/bin/python}"
export SOULX_CKPT_DIR="${SOULX_CKPT_DIR:-$A22_MODEL_ROOT/SoulX-FlashHead-1_3B}"
export SOULX_WAV2VEC_DIR="${SOULX_WAV2VEC_DIR:-$A22_MODEL_ROOT/wav2vec2-base-960h}"
export SOULX_INFER_SCRIPT="${SOULX_INFER_SCRIPT:-generate_video.py}"
export SOULX_CHUNK_SECONDS="${SOULX_CHUNK_SECONDS:-2.0}"
export SOULX_FPS="${SOULX_FPS:-25}"
export SOULX_COMMAND_TEMPLATE="${SOULX_COMMAND_TEMPLATE:-$SOULX_PYTHON {infer_script} --ckpt_dir $SOULX_CKPT_DIR --wav2vec_dir $SOULX_WAV2VEC_DIR --model_type lite --cond_image {ref_image_path} --audio_path {audio_path} --audio_encode_mode stream --save_file {output_path}}"

if [ -z "${SOULX_REF_IMAGE_PATH:-}" ]; then
  if [ -f "$SOULX_ROOT/examples/girl.png" ]; then
    SOULX_REF_IMAGE_PATH="$SOULX_ROOT/examples/girl.png"
  elif [ -f "$SOULX_ROOT/examples/your_new_person.png" ]; then
    SOULX_REF_IMAGE_PATH="$SOULX_ROOT/examples/your_new_person.png"
  else
    SOULX_REF_IMAGE_PATH=""
  fi
fi
export SOULX_REF_IMAGE_PATH

for env_name in qwen-server speech-service vision-service "$AVATAR_ENV_NAME" orchestrator; do
  if [ ! -x "$A22_ENV_ROOT/$env_name/bin/python" ]; then
    echo "[error] missing uv environment: $A22_ENV_ROOT/$env_name" >&2
    exit 1
  fi
done

if [ ! -x "$SOULX_PYTHON" ]; then
  echo "[error] missing soulx python: $SOULX_PYTHON" >&2
  exit 1
fi

mkdir -p "$A22_TMP_ROOT/speech" "$A22_TMP_ROOT/vision" "$A22_TMP_ROOT/avatar" "$A22_LOG_ROOT"

for session_name in qwen speech vision avatar orchestrator; do
  tmux kill-session -t "$session_name" 2>/dev/null || true
done

tmux new-session -d -s qwen "bash -lc '
set -euo pipefail
source /root/autodl-tmp/a22/env.sh
source \"$A22_ENV_ROOT/qwen-server/bin/activate\"
cd \"$A22_CODE/remote/qwen-server\"
export CUDA_VISIBLE_DEVICES=\"$QWEN_CUDA_VISIBLE_DEVICES\"
exec python -m vllm.entrypoints.openai.api_server \
  --host 127.0.0.1 --port 8000 \
  --model \"$QWEN_MODEL_PATH\" \
  --served-model-name \"$QWEN_MODEL_NAME\" \
  --dtype auto --gpu-memory-utilization \"$QWEN_GPU_MEMORY_UTILIZATION\" \
  --max-model-len \"$QWEN_MAX_MODEL_LEN\" --max-num-seqs \"$QWEN_MAX_NUM_SEQS\" --trust-remote-code
'"

tmux new-session -d -s speech "bash -lc '
set -euo pipefail
source /root/autodl-tmp/a22/env.sh
source \"$A22_ENV_ROOT/speech-service/bin/activate\"
cd \"$A22_CODE/remote/speech-service\"
export CUDA_VISIBLE_DEVICES=\"$SPEECH_CUDA_VISIBLE_DEVICES\"
export TMP_DIR=\"$A22_TMP_ROOT/speech\"
export ASR_PROVIDER=qwen3_asr
export ASR_MODEL=\"$ASR_MODEL_PATH\"
export ASR_LANGUAGE=Chinese
export ASR_DEVICE=cuda:0
export ASR_WARMUP_ENABLED=false
export QWEN_ASR_USE_FLASH_ATTN=true
export QWEN_ASR_USE_ITN=false
exec python -m uvicorn app:app --host 127.0.0.1 --port 19100
'"

tmux new-session -d -s vision "bash -lc '
set -euo pipefail
source /root/autodl-tmp/a22/env.sh
source \"$A22_ENV_ROOT/vision-service/bin/activate\"
cd \"$A22_CODE/remote/vision-service\"
export CUDA_VISIBLE_DEVICES=\"$VISION_CUDA_VISIBLE_DEVICES\"
export TMP_DIR=\"$A22_TMP_ROOT/vision\"
export VISION_EXTRACTOR_MODE=qwen2_5_vl
export VISION_MODEL=\"$VISION_MODEL_PATH\"
export VISION_DEVICE=cuda:0
export VISION_DTYPE=float16
export VISION_WARMUP_ENABLED=false
exec python -m uvicorn app:app --host 127.0.0.1 --port 19200
'"

tmux new-session -d -s avatar "bash -lc '
set -euo pipefail
source /root/autodl-tmp/a22/env.sh
source \"$A22_ENV_ROOT/$AVATAR_ENV_NAME/bin/activate\"
cd \"$A22_CODE/remote/avatar-service\"
export CUDA_VISIBLE_DEVICES=\"$AVATAR_CUDA_VISIBLE_DEVICES\"
export TMP_DIR=\"$A22_TMP_ROOT/avatar\"
export AVATAR_RENDERER_BACKEND=\"$AVATAR_RENDERER_BACKEND\"
export SOULX_ROOT=\"$SOULX_ROOT\"
export SOULX_INFER_SCRIPT=\"$SOULX_INFER_SCRIPT\"
export SOULX_REF_IMAGE_PATH=\"$SOULX_REF_IMAGE_PATH\"
export SOULX_COMMAND_TEMPLATE=\"$SOULX_COMMAND_TEMPLATE\"
export SOULX_CHUNK_SECONDS=\"$SOULX_CHUNK_SECONDS\"
export SOULX_FPS=\"$SOULX_FPS\"
export TTS_MODE=\"$TTS_MODE\"
export TTS_MODEL=\"$TTS_MODEL_PATH\"
export TTS_REPO_PATH=\"$TTS_REPO_PATH\"
export TTS_DEVICE=cuda:0
export TTS_WARMUP_ENABLED=false
export PYTHONPATH=\"$TTS_REPO_PATH:$TTS_REPO_PATH/third_party/Matcha-TTS\"
exec python -m uvicorn app:app --host 127.0.0.1 --port 19300
'"

tmux new-session -d -s orchestrator "bash -lc '
set -euo pipefail
source /root/autodl-tmp/a22/env.sh
source \"$A22_ENV_ROOT/orchestrator/bin/activate\"
cd \"$A22_CODE/remote/orchestrator\"
export LLM_PROVIDER=qwen
export LLM_MODEL=\"$QWEN_MODEL_NAME\"
export LLM_API_BASE=http://127.0.0.1:8000/v1
export LLM_API_KEY=EMPTY
export SPEECH_SERVICE_ENABLED=true
export SPEECH_SERVICE_BASE=http://127.0.0.1:19100
export VISION_SERVICE_ENABLED=true
export VISION_SERVICE_BASE=http://127.0.0.1:19200
export AVATAR_SERVICE_ENABLED=true
export AVATAR_SERVICE_BASE=http://127.0.0.1:19300
export EMOTION_SERVICE_ENABLED=false
exec python -m uvicorn app:app --host 127.0.0.1 --port 19000
'"

echo "[ok] tmux sessions started:"
tmux ls | grep -E '^(qwen|speech|vision|avatar|orchestrator):'
echo "[hint] check health: curl -s http://127.0.0.1:19000/health | python -m json.tool"
