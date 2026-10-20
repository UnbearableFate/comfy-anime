#!/bin/bash
source "$(dirname -- "$0")/common.sh"
require_compute
mkdir -p "$COMFY_DATA_ROOT"/{logs,input,output,cache,config}
if [[ ! -x "$COMFY_DATA_ROOT/venv/bin/python" ]]; then
    timeout 180 uv venv --python 3.12 "$COMFY_DATA_ROOT/venv"
fi
timeout 300 uv pip install --python "$COMFY_DATA_ROOT/venv/bin/python" \
    --only-binary :all: "comfy-cli==$COMFY_CLI_VERSION"
comfy tracking disable
export UV_CONSTRAINT="$PROJECT_ROOT/config/constraints.txt"
export PIP_CONSTRAINT="$UV_CONSTRAINT"
comfy install --restore --version nightly --commit "$COMFY_COMMIT" \
    --nvidia --cuda-version 13.0 --fast-deps
# Pin the validated aarch64 CUDA stack; Manager also checks for torchaudio.
uv pip install --python "$PYTHON_BIN" --only-binary :all: \
    --index-url https://download.pytorch.org/whl/cu130 \
    'torch==2.11.0+cu130' 'torchvision==0.26.0+cu130' 'torchaudio==2.11.0+cu130'
# H3, LoRA loading and MP4 saving are core nodes. No third-party node pack needed.
comfy node simple-show installed --mode local > "$COMFY_DATA_ROOT/logs/custom-nodes.txt"
comfy node save-snapshot --output "$COMFY_DATA_ROOT/comfy-snapshot.json"
"$PYTHON_BIN" -c 'import platform, torch; assert platform.machine() == "aarch64"; assert torch.cuda.is_available(); print(torch.__version__, torch.cuda.get_device_name())'
uv pip freeze --python "$PYTHON_BIN" > "$COMFY_DATA_ROOT/installed-requirements.txt"
