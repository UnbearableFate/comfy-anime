"""Require every LoRA A/B pair to match the selected base checkpoint."""
import json
import os
import struct
from pathlib import Path


def header(path):
    with path.open("rb") as stream:
        length = struct.unpack("<Q", stream.read(8))[0]
        if length > 64 * 1024 * 1024:
            raise ValueError(f"Unreasonable safetensors header: {path}")
        return json.loads(stream.read(length))


def main():
    root = Path(os.environ["COMFY_DATA_ROOT"])
    models = json.loads((Path(__file__).resolve().parents[1] / "config/models.json").read_text())
    by_dir = {m["directory"]: root / "ComfyUI/models" / m["directory"] / m["filename"] for m in models}
    base, lora = header(by_dir["diffusion_models"]), header(by_dir["loras"])
    pairs = []
    seen = set()
    for name in lora:
        suffix = ".lora_A.default.weight"
        if not name.endswith(suffix):
            continue
        stem = name[:-len(suffix)]
        b_name = stem + ".lora_B.default.weight"
        a, b = lora[name]["shape"], lora[b_name]["shape"]
        weight = base.get("model.diffusion_model." + stem + ".weight")
        if weight is None or weight["shape"] != [b[0], a[1]] or b[1] != a[0]:
            raise RuntimeError(f"Unmatched LoRA pair: {stem}")
        pairs.append(stem)
        seen.update((name, b_name))
    unknown = set(lora) - seen - {"__metadata__"}
    if not pairs or unknown:
        raise RuntimeError(f"Unaccounted LoRA tensors: {sorted(unknown)}")
    result = {"matched_pairs": len(pairs), "matched_tensors": len(seen), "unmatched": [], "base": str(by_dir["diffusion_models"]), "lora": str(by_dir["loras"])}
    destination = Path(os.environ.get("RUN_DIR", str(root))) / "lora-audit.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
