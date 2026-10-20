#!/bin/bash
# Official standing illustration: https://vrp.moe/talents/nanami
# Original asset: https://vrp.moe/talents/nanami/tachie.webp
# Download the original to the path below before submitting.
source "$(dirname -- "$0")/common.sh"
REFERENCE="$COMFY_DATA_ROOT/references/nana7mi/official-tachie.webp"
[[ -f "$REFERENCE" ]] || { echo "Missing reference: $REFERENCE" >&2; exit 2; }
PROMPT="$(cat "$PROJECT_ROOT/prompts/nana7mi-sakura-slope.txt")"
export PBS_QUEUE="${PBS_QUEUE:-debug-g}"
export PBS_WALLTIME="${PBS_WALLTIME:-00:15:00}"
exec bash "$PROJECT_ROOT/scripts/submit.sh" run \
    --image "$REFERENCE" --prompt "$PROMPT" \
    --width 832 --height 480 --frames 294 --fps 24 \
    --steps 20 --seed 715 --lora-strength 1.0
