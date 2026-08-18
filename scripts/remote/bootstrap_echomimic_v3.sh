#!/usr/bin/env bash
set -euo pipefail

A22_ROOT="${A22_ROOT:-/root/autodl-tmp/a22}"
ECHOMIMIC_V3_ROOT="${ECHOMIMIC_V3_ROOT:-$A22_ROOT/code/echomimic_v3}"
ECHOMIMIC_V3_ENV="${ECHOMIMIC_V3_ENV:-$A22_ROOT/.uv_envs/echomimic-v3}"
UV_BIN="${UV_BIN:-/root/.local/bin/uv}"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$A22_ROOT/tmp/uv-cache-echomimic-v3}"
export TMPDIR="${TMPDIR:-$A22_ROOT/tmp/tmpdir}"
mkdir -p "$UV_CACHE_DIR" "$TMPDIR"

if [ ! -d "$ECHOMIMIC_V3_ROOT/.git" ]; then
  git clone --depth 1 https://github.com/antgroup/echomimic_v3.git "$ECHOMIMIC_V3_ROOT"
fi

if [ ! -x "$ECHOMIMIC_V3_ENV/bin/python" ]; then
  "$UV_BIN" venv --python "$A22_ROOT/.uv_envs/avatar-service/bin/python" "$ECHOMIMIC_V3_ENV"
fi

"$UV_BIN" pip install --python "$ECHOMIMIC_V3_ENV/bin/python" \
  'torch==2.13.0' 'torchvision==0.28.0' 'diffusers==0.39.0' \
  'transformers==5.15.0' 'accelerate==1.14.0' 'mmgp==3.7.12' \
  Pillow einops safetensors timm tomesd torchdiffeq torchsde decord numpy \
  scikit-image opencv-python-headless omegaconf SentencePiece \
  'imageio[ffmpeg,pyav]' 'moviepy==2.2.1' librosa retina-face pyloudnorm

cd "$ECHOMIMIC_V3_ROOT"
"$ECHOMIMIC_V3_ENV/bin/python" infer_flash.py --help >/dev/null
echo "[ok] EchoMimicV3 environment: $ECHOMIMIC_V3_ENV"
