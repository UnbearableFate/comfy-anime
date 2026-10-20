#!/bin/bash
source "$(dirname -- "$0")/common.sh"
require_compute
cd "$PROJECT_ROOT"
for script in scripts/*.sh pbs/*.pbs; do bash -n "$script"; done
"$PYTHON_BIN" -m unittest discover -s tests -v
