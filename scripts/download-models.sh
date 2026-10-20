#!/bin/bash
source "$(dirname -- "$0")/common.sh"
require_compute
"$COMFY_DATA_ROOT/venv/bin/python" "$PROJECT_ROOT/scripts/download_models.py"
