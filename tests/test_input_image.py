import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

PREPARE_RUN = Path(__file__).resolve().parents[1] / "scripts/prepare_run.py"
COLORS = {
    "R": (255, 0, 0),
    "G": (0, 255, 0),
    "B": (0, 0, 255),
    "Y": (255, 255, 0),
}


class InputImageContracts(unittest.TestCase):
    def quadrant_image(self):
        image = Image.new("RGB", (960, 640))
        for color, box in zip(
            "RGBY",
            [(0, 0, 480, 320), (480, 0, 960, 320),
             (0, 320, 480, 640), (480, 320, 960, 640)],
        ):
            image.paste(COLORS[color], box)
        return image

    def stage(self, source, root):
        original = source.read_bytes()
        completed = subprocess.run(
            [sys.executable, str(PREPARE_RUN), "--image", str(source)],
            env={**os.environ, "COMFY_DATA_ROOT": str(root / "data")},
            capture_output=True, text=True, check=True, timeout=30,
        )
        run_dir = Path(completed.stdout.strip())
        staged = Path((run_dir / "input.txt").read_text().strip())
        api = json.loads((run_dir / "workflow.api.json").read_text())
        self.assertEqual(api["5"]["inputs"]["image"], staged.name)
        self.assertEqual(source.read_bytes(), original)
        return staged

    def test_jpeg_exif_rotations_and_mirrors(self):
        # Expected displayed quadrant order: top-left, top-right, bottom-left,
        # bottom-right. Hard-coded so the oracle does not reuse EXIF transpose.
        orders = {
            None: "RGBY", 1: "RGBY", 2: "GRYB", 3: "YBGR",
            4: "BYRG", 5: "RBGY", 6: "BRYG", 7: "YGBR", 8: "GYRB",
        }
        for orientation, order in orders.items():
            with self.subTest(orientation=orientation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "reference.jpg"
                exif = Image.Exif()
                if orientation is not None:
                    exif[274] = orientation
                with self.quadrant_image() as image:
                    image.save(source, quality=100, subsampling=0, exif=exif)
                with Image.open(self.stage(source, root)) as staged:
                    self.assertEqual(staged.format, "PNG")
                    self.assertEqual(staged.mode, "RGB")
                    expected_size = (640, 960) if orientation in (5, 6, 7, 8) else (960, 640)
                    self.assertEqual(staged.size, expected_size)
                    self.assertIn(staged.getexif().get(274), (None, 1))
                    w, h = staged.size
                    points = [(w // 4, h // 4), (3 * w // 4, h // 4),
                              (w // 4, 3 * h // 4), (3 * w // 4, 3 * h // 4)]
                    for point, color in zip(points, order):
                        for actual, expected in zip(staged.getpixel(point), COLORS[color]):
                            self.assertLessEqual(abs(actual - expected), 3)

    def test_png_without_exif_preserves_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "reference.png"
            with self.quadrant_image() as image:
                image.save(source)
                with Image.open(self.stage(source, root)) as staged:
                    self.assertEqual(staged.size, image.size)
                    self.assertEqual(staged.tobytes(), image.tobytes())


if __name__ == "__main__":
    unittest.main()
