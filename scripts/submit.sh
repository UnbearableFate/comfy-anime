#!/bin/bash
source "$(dirname -- "$0")/common.sh"
ACTION="${1:-}"
case "$ACTION" in
    install|download|run|serve|check) shift ;;
    *) echo "Usage: $0 {install|download|run|serve|check} [arguments...]" >&2; exit 2 ;;
esac
/usr/bin/python3 -I "$MIYABI_PBS_CMD_ROOT/scripts/context.py" --target-system Miyabi-G >&2
mkdir -p "$COMFY_DATA_ROOT"/{requests,logs}
REQUEST="$(mktemp "$COMFY_DATA_ROOT/requests/request-XXXXXXXX.json")"
# This is a small stdlib-only control-plane operation.
/usr/bin/python3 - "$REQUEST" "$ACTION" "$@" <<'PY'
import json, os, sys
args = sys.argv[3:]
for index, value in enumerate(args):
    if value == "--image" and index + 1 < len(args):
        args[index + 1] = os.path.abspath(args[index + 1])
    elif value.startswith("--image="):
        args[index] = "--image=" + os.path.abspath(value.split("=", 1)[1])
with open(sys.argv[1], "w") as stream:
    json.dump({"action": sys.argv[2], "args": args}, stream)
PY
export ANIME_PROJECT_ROOT="$PROJECT_ROOT" ANIME_REQUEST="$REQUEST"
# PBS's -v syntax cannot represent commas in paths.
[[ "$PROJECT_ROOT$REQUEST$COMFY_DATA_ROOT$MIYABI_PBS_CMD_ROOT" != *,* ]] || {
    echo "PBS paths must not contain commas" >&2; exit 2;
}
export MIYABI_PBS_CMD_ROOT COMFY_PORT
bash -n "$PROJECT_ROOT/pbs/comfy.pbs"
qsub -q "${PBS_QUEUE:-short-g}" -W "group_list=$PBS_GROUP" \
    -l "walltime=${PBS_WALLTIME:-00:55:00}" \
    -o "$COMFY_DATA_ROOT/logs/$(basename "$REQUEST" .json).pbs.log" \
    -v ANIME_PROJECT_ROOT,ANIME_REQUEST,COMFY_DATA_ROOT,MIYABI_PBS_CMD_ROOT,COMFY_PORT \
    "$PROJECT_ROOT/pbs/comfy.pbs"
