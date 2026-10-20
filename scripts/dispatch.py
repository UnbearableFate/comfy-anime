"""Read the argv file rather than interpolating user prompts into a PBS shell."""
import json
import os
import sys
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text())
root = Path(__file__).resolve().parents[1]
commands = {
    "install": "install.sh", "download": "download-models.sh",
    "run": "run.sh", "serve": "serve.sh", "check": "check.sh",
}
script = commands[request["action"]]
os.execv("/bin/bash", ["bash", str(root / "scripts" / script), *request["args"]])
