import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from make_workflows import graph, ui_workflow
from prepare_run import parse_args


class WorkflowContracts(unittest.TestCase):
    def test_reference_and_lora_reach_sampler(self):
        api = graph()
        self.assertEqual(api["6"]["inputs"]["ref_images.ref_image_0"], ["5", 0])
        self.assertEqual(api["10"]["inputs"]["conditioning"], ["6", 0])
        self.assertEqual(api["11"]["inputs"]["latent_image"], ["6", 1])
        for node in ("9", "10"):
            self.assertEqual(api[node]["inputs"]["model"], ["2", 0])
        self.assertEqual(api["2"]["class_type"], "LoraLoaderModelOnly")
        self.assertGreater(api["2"]["inputs"]["strength_model"], 0)

    def test_saved_graphs_match_and_links_roundtrip(self):
        api = graph()
        directory = Path(__file__).resolve().parents[1] / "workflows"
        self.assertEqual(json.loads((directory / "minimax-h3-anime.api.json").read_text()), api)
        ui = ui_workflow(api)
        self.assertEqual(json.loads((directory / "minimax-h3-anime.json").read_text()), ui)
        links = {link[0]: link for link in ui["links"]}
        for node in ui["nodes"]:
            key = str(node["id"])
            for item in node["inputs"]:
                link = links[item["link"]]
                self.assertEqual(api[key]["inputs"][item["name"]], [str(link[1]), link[2]])
                self.assertEqual(link[3], node["id"])

    def parse(self, *args):
        with patch.object(sys, "argv", ["prepare_run", "--smoke", *args]), contextlib.redirect_stderr(io.StringIO()):
            return parse_args()

    def test_reject_invalid_geometry_frame_grid_and_no_lora(self):
        for args in [
            ("--width", "0"), ("--height", "513"), ("--frames", "24"),
            ("--frames", "0"), ("--fps", "0"), ("--steps", "0"),
            ("--seed", "-1"), ("--lora-strength", "0"),
            ("--lora-strength", "nan"),
        ]:
            with self.subTest(args=args), self.assertRaises(SystemExit):
                self.parse(*args)

    def test_explicit_config_overrides_smoke(self):
        args = self.parse("--width", "512", "--frames", "124", "--seed", "123", "--fps", "12")
        self.assertEqual((args.width, args.frames, args.seed, args.fps), (512, 124, 123, 12))


if __name__ == "__main__":
    unittest.main()
