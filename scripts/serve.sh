#!/bin/bash
source "$(dirname -- "$0")/common.sh"
require_compute
mkdir -p "$COMFY_DATA_ROOT"/{input,output,logs}
echo "ComfyUI on $(hostname):$COMFY_PORT (loopback); job $PBS_JOBID"
comfy launch -- --listen 127.0.0.1 --port "$COMFY_PORT" \
    --input-directory "$COMFY_DATA_ROOT/input" \
    --output-directory "$COMFY_DATA_ROOT/output" \
    --disable-auto-launch --disable-dynamic-vram --use-pytorch-cross-attention "$@"
