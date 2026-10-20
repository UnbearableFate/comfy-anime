"""Verify the prompt, LoRA application, and every decoded output video frame."""
import json
import os
import platform
import socket
import sys
import urllib.request
from pathlib import Path

import av
import numpy as np


def main():
    directory = Path(sys.argv[1])
    envelopes = [
        json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()
        if line.startswith("{")
    ]
    final = next(item for item in reversed(envelopes) if item.get("type") == "envelope")
    if not final["ok"]:
        raise RuntimeError(final)
    prompt_id = final["data"]["prompt_id"]
    with urllib.request.urlopen(
        f"http://127.0.0.1:{os.environ.get('COMFY_PORT', '8188')}/history/{prompt_id}",
        timeout=30,
    ) as response:
        history = json.load(response)[prompt_id]
    (directory / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    if not history["status"]["completed"] or history["status"]["status_str"] != "success":
        raise RuntimeError(history["status"])
    log = (directory / "server.log").read_text()
    if any(marker in log for marker in ("lora key not loaded", "NOT LOADED", "size mismatch", "ERROR lora")):
        raise RuntimeError("LoRA/model loading warning found; inspect server.log")
    params = json.loads((directory / "parameters.json").read_text())
    audit = json.loads((directory / "lora-audit.json").read_text())
    outputs = list((Path(os.environ["COMFY_DATA_ROOT"]) / "output" / directory.name).glob("*.mp4"))
    if len(outputs) != 1:
        raise RuntimeError(f"Expected one MP4, found {outputs}")
    path = outputs[0]
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        width, height, fps = stream.width, stream.height, float(stream.average_rate)
        count, spatial_std, temporal_delta, previous = 0, 0.0, 0.0, None
        for frame in container.decode(video=0):
            pixels = frame.to_ndarray(format="rgb24").astype(np.float32)
            spatial_std += float(pixels.std())
            if previous is not None:
                temporal_delta += float(np.abs(pixels - previous).mean())
            if count == 0:
                frame.to_image().save(directory / "first-frame.png")
            previous = pixels
            count += 1
    if (width, height, count) != (params["width"], params["height"], params["frames"]):
        raise RuntimeError(f"Unexpected video geometry/frame count: {(width, height, count)}")
    if abs(fps - params["fps"]) > 0.01 or spatial_std <= 0 or temporal_delta <= 0:
        raise RuntimeError("Invalid FPS, blank frames, or no frame variation")
    result = {
        "success": True, "prompt_id": prompt_id, "pbs_job_id": os.environ["PBS_JOBID"],
        "hostname": socket.gethostname(), "architecture": platform.machine(),
        "video": str(path), "bytes": path.stat().st_size,
        "width": width, "height": height, "frames": count, "fps": fps,
        "duration_seconds": count / fps,
        "mean_spatial_std": spatial_std / count,
        "mean_frame_delta": temporal_delta / (count - 1),
        "lora_strength": params["lora_strength"],
        "matched_lora_tensors": audit["matched_tensors"],
    }
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
