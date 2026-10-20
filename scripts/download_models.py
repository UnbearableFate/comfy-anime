"""Download pinned model files using comfy-cli; verify content on compute."""
import hashlib
import json
import os
import subprocess
from pathlib import Path


def main():
    root = Path(os.environ["COMFY_DATA_ROOT"])
    manifest = Path(__file__).resolve().parents[1] / "config/models.json"
    models = json.loads(manifest.read_text())
    for model in models:
        target = root / "ComfyUI/models" / model["directory"] / model["filename"]
        if not target.exists():
            subprocess.run(
                [
                    str(root / "venv/bin/comfy"),
                    "--skip-prompt", "--workspace", str(root / "ComfyUI"),
                    "--where", "local", "model", "download",
                    "--url", model["url"],
                    "--relative-path", f"models/{model['directory']}",
                    "--filename", model["filename"],
                ],
                check=True,
            )
        if target.stat().st_size != model["bytes"]:
            raise RuntimeError(f"Incomplete model: {target}; move it aside and rerun")
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != model["sha256"]:
            raise RuntimeError(f"SHA256 mismatch: {target}; move it aside and rerun")
        print(f"Verified {target.name}", flush=True)
    (root / "models-verified.json").write_text(json.dumps(models, indent=2) + "\n")


if __name__ == "__main__":
    main()
