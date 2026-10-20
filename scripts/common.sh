#!/bin/bash
# Source this file; it performs no application imports.
set -eEuo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/config/runtime.env"
[[ "$COMFY_DATA_ROOT" = /* ]] || { echo "COMFY_DATA_ROOT must be absolute" >&2; exit 2; }
case "$(realpath -m "$COMFY_DATA_ROOT")/" in
    "$(realpath "$PROJECT_ROOT")/"*) echo "Runtime data must be outside the git checkout" >&2; exit 2 ;;
esac
export COMFY_DATA_ROOT
export COMFY_WHERE=local
export XDG_CONFIG_HOME="$COMFY_DATA_ROOT/config"
export HF_HOME="$COMFY_DATA_ROOT/cache/huggingface"
export UV_CACHE_DIR="$COMFY_DATA_ROOT/cache/uv"
export TORCH_HOME="$COMFY_DATA_ROOT/cache/torch"
export TRITON_CACHE_DIR="$COMFY_DATA_ROOT/cache/triton"
export OMP_NUM_THREADS=8
COMFY_DIR="$COMFY_DATA_ROOT/ComfyUI"
CLI="$COMFY_DATA_ROOT/venv/bin/comfy"
PYTHON_BIN="$COMFY_DIR/.venv/bin/python"
export PYTHON_BIN
export PATH="$COMFY_DIR/.venv/bin:$COMFY_DATA_ROOT/venv/bin:$PATH"
# Prevent an unrelated activated environment from overriding comfy's interpreter.
unset VIRTUAL_ENV CONDA_PREFIX

require_compute() {
    /usr/bin/python3 -I "$MIYABI_PBS_CMD_ROOT/scripts/context.py" \
        --target-system Miyabi-G --require-compute
    local status_json
    status_json="$(/usr/bin/python3 -I "$MIYABI_PBS_CMD_ROOT/scripts/qstat_json.py" \
        "${PBS_JOBID:?}" --summary)"
    echo "$status_json"
    /usr/bin/python3 -c 'import json,sys; x=json.load(sys.stdin); sys.exit(0 if x.get("ok") and x.get("status_counts")=={"RUNNING":1} else 1)' <<< "$status_json"
    export PAGER=cat MODULES_PAGER=cat LMOD_PAGER=cat
    module load cuda/13.2
}

comfy() {
    "$CLI" --skip-prompt --workspace "$COMFY_DIR" --where local "$@"
}
