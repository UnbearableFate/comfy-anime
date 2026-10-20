"""Stage an image and parameterized API graph in a durable run directory."""
import argparse
import json
import os
import shutil
import uuid
from pathlib import Path

from make_workflows import PROMPT


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--prompt", default=PROMPT)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--fps", type=float, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--lora-strength", type=float, default=1.0)
    args = parser.parse_args()
    for name, default in {
        "width": 384 if args.smoke else 832,
        "height": 256 if args.smoke else 480,
        "frames": 39 if args.smoke else 124,
        "steps": 20,
    }.items():
        if getattr(args, name) is None:
            setattr(args, name, default)
    if not args.smoke and args.image is None:
        parser.error("--image is required unless --smoke is set")
    if any(x < 32 or x % 32 for x in (args.width, args.height)):
        parser.error("width and height must be positive multiples of 32")
    if not 5 <= args.frames <= 3600 or args.frames % 17 != 5:
        parser.error("frames must follow 17k+5 (5, 22, 39, ... 124, ...), up to 3600")
    if not 1 <= args.fps <= 120 or not 1 <= args.steps <= 10000:
        parser.error("fps must be in [1,120]; steps must be in [1,10000]")
    if not 0 <= args.seed < 2**64:
        parser.error("seed must fit uint64")
    if not 0 < args.lora_strength <= 2:
        parser.error("lora-strength must be in (0,2]")
    return args


def test_image(path):
    # A deterministic synthetic fixture; no third-party image/license dependency.
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (384, 256), "#bde6ff")
    draw = ImageDraw.Draw(im)
    draw.ellipse((290, 20, 336, 66), fill="#fff4b8")
    draw.ellipse((-80, 180, 290, 370), fill="#68b48a")
    draw.ellipse((140, 170, 490, 370), fill="#44967d")
    for x, y in [(30, 30), (220, 85)]:
        draw.ellipse((x, y, x + 90, y + 25), fill="#ffffff")
    draw.line([(180, 135), (175, 158), (190, 178), (180, 206)], fill="#35465b", width=2)
    draw.polygon([(180, 50), (215, 90), (180, 140), (145, 90)], fill="#e7546b", outline="#35465b")
    draw.line([(180, 50), (180, 140)], fill="#ffe9c5", width=2)
    draw.line([(145, 90), (215, 90)], fill="#ffe9c5", width=2)
    im.save(path)


def main():
    args = parse_args()
    root = Path(os.environ["COMFY_DATA_ROOT"])
    run_id = f"{'smoke' if args.smoke else 'run'}-{uuid.uuid4().hex[:12]}"
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    input_dir = root / "input"
    input_dir.mkdir(exist_ok=True)
    image = input_dir / f"{run_id}.png"
    if args.image:
        from PIL import Image, ImageOps
        with Image.open(args.image) as im:
            # Bake EXIF rotation/mirroring into pixels before converting to PNG.
            ImageOps.exif_transpose(im).convert("RGB").save(image)
    else:
        test_image(image)
        # Also make the checked-in UI workflow immediately usable.
        shutil.copyfile(image, input_dir / "smoke-reference.png")
    template = Path(__file__).resolve().parents[1] / "workflows/minimax-h3-anime.api.json"
    api = json.loads(template.read_text())
    api["5"]["inputs"]["image"] = image.name
    api["6"]["inputs"].update(prompt=args.prompt, width=args.width, height=args.height, length=args.frames)
    api["7"]["inputs"]["noise_seed"] = args.seed
    api["9"]["inputs"]["steps"] = args.steps
    api["2"]["inputs"]["strength_model"] = args.lora_strength
    api["13"]["inputs"]["fps"] = args.fps
    api["14"]["inputs"]["filename_prefix"] = f"{run_id}/video"
    (run_dir / "workflow.api.json").write_text(json.dumps(api, indent=2) + "\n")
    (run_dir / "parameters.json").write_text(json.dumps(vars(args), default=str, indent=2) + "\n")
    (run_dir / "input.txt").write_text(str(image) + "\n")
    print(run_dir)


if __name__ == "__main__":
    main()
