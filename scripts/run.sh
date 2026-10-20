#!/bin/bash
source "$(dirname -- "$0")/common.sh"
require_compute
RUN_DIR="$("$PYTHON_BIN" "$PROJECT_ROOT/scripts/prepare_run.py" "$@")"
echo "$RUN_DIR"
export RUN_DIR
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/audit_lora.py"
# Own a process group so cleanup terminates both comfy-cli and its server child.
setsid bash "$PROJECT_ROOT/scripts/serve.sh" > "$RUN_DIR/server.log" 2>&1 &
SERVER_PID=$!
cleanup() {
    kill -- "-$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
export SERVER_PID COMFY_PORT
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/wait_server.py"
comfy run --workflow "$RUN_DIR/workflow.api.json" --host 127.0.0.1 \
    --port "$COMFY_PORT" --wait --timeout 1800 --json > "$RUN_DIR/events.jsonl"
"$PYTHON_BIN" "$PROJECT_ROOT/scripts/verify_output.py" "$RUN_DIR"
echo "Outputs and validation: $RUN_DIR/result.json"
