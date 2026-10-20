"""Wait for this run's server, refusing to reuse an existing listener."""
import json
import os
import time
import urllib.request
from pathlib import Path

deadline = time.monotonic() + 180
log = Path(os.environ["RUN_DIR"]) / "server.log"
while time.monotonic() < deadline:
    os.kill(int(os.environ["SERVER_PID"]), 0)
    # Read a bounded tail. This marker is emitted only after successful binding.
    with log.open("rb") as stream:
        stream.seek(max(0, log.stat().st_size - 16384))
        started = b"To see the GUI go to:" in stream.read()
    if started:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{os.environ['COMFY_PORT']}/object_info", timeout=5
            ) as response:
                info = json.load(response)
            if "MiniMaxH3ReferenceToVideo" not in info:
                raise RuntimeError("MiniMax H3 core node is missing")
            (log.parent / "object_info.json").write_text(json.dumps(info))
            break
        except OSError:
            pass
    time.sleep(1)
else:
    raise TimeoutError(f"ComfyUI did not start; inspect {log}")
