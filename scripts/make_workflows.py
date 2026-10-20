"""Build the paired native ComfyUI UI/API workflows from one graph definition."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (
    "Anime-Motion: Use <Picture 1> as the visual reference. "
    "A red kite floats above quiet green hills under a blue sky. "
    "The kite and its ribbon sway gently in the wind, small clouds drift slowly. "
    "Clean anime line art, soft colors, fixed camera, continuous smooth motion."
)


def graph():
    def node(kind, **inputs):
        return {"class_type": kind, "inputs": inputs}

    return {
        "1": node("UNETLoader", unet_name="Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors", weight_dtype="default"),
        "2": node("LoraLoaderModelOnly", model=["1", 0], lora_name="MiniMax-H3-I2V-Anime-Motion-LoRA-1400.safetensors", strength_model=1.0),
        "3": node("CLIPLoader", clip_name="qwen3vl_32b_minimax_h3_int8_convrot.safetensors", type="minimax", device="default"),
        "4": node("VAELoader", vae_name="minimax_h3_video_vae_fp16.safetensors"),
        "5": node("LoadImage", image="smoke-reference.png"),
        "6": node("MiniMaxH3ReferenceToVideo", clip=["3", 0], vae=["4", 0], prompt=PROMPT, width=832, height=480, length=124, ref_image_size="match", **{"ref_images.ref_image_0": ["5", 0]}),
        "7": node("RandomNoise", noise_seed=42),
        "8": node("KSamplerSelect", sampler_name="res_multistep"),
        "9": node("BasicScheduler", model=["2", 0], scheduler="simple", steps=20, denoise=1.0),
        "10": node("BasicGuider", model=["2", 0], conditioning=["6", 0]),
        "11": node("SamplerCustomAdvanced", noise=["7", 0], guider=["10", 0], sampler=["8", 0], sigmas=["9", 0], latent_image=["6", 1]),
        "12": node("VAEDecode", samples=["11", 0], vae=["4", 0]),
        "13": node("CreateVideo", images=["12", 0], fps=24.0, bit_depth=8),
        "14": node("SaveVideo", video=["13", 0], filename_prefix="anime/clip", format="mp4", **{"format.codec": "h264", "format.codec.encoding": "auto"}),
    }


def ui_workflow(api):
    # Explicit output signatures keep this generator independent of ML imports.
    outputs = [
        ["MODEL"], ["MODEL"], ["CLIP"], ["VAE"], ["IMAGE", "MASK"],
        ["CONDITIONING", "LATENT"], ["NOISE"], ["SAMPLER"], ["SIGMAS"],
        ["GUIDER"], ["LATENT", "LATENT"], ["IMAGE"], ["VIDEO"], ["VIDEO"],
    ]
    positions = [
        (0, 0), (410, 0), (0, 260), (0, 490), (0, 680), (830, 0),
        (830, 550), (830, 720), (1240, 400), (1240, 180),
        (1640, 0), (2040, 0), (2440, 0), (2840, 0),
    ]
    nodes, links = [], []
    for index, (key, item) in enumerate(api.items()):
        node = {
            "id": int(key), "type": item["class_type"], "pos": list(positions[index]),
            "size": [360, 430 if key == "6" else 200], "flags": {},
            "order": index, "mode": 0, "inputs": [],
            "outputs": [{"name": t, "type": t, "links": []} for t in outputs[index]],
            "properties": {"cnr_id": "comfy-core", "Node name for S&R": item["class_type"]},
            "widgets_values": [], "widgets_values_named": {},
        }
        for name, value in item["inputs"].items():
            if isinstance(value, list):
                source, slot = value
                kind = outputs[int(source) - 1][slot]
                link_id = len(links) + 1
                links.append([link_id, int(source), slot, int(key), len(node["inputs"]), kind])
                node["inputs"].append({"name": name, "type": kind, "link": link_id})
            else:
                node["widgets_values"].append(value)
                node["widgets_values_named"][name] = value
                if item["class_type"] == "RandomNoise" and name == "noise_seed":
                    node["widgets_values"].append("fixed")
                    node["widgets_values_named"]["control_after_generate"] = "fixed"
        if item["class_type"] == "LoadImage":
            node["widgets_values"].append("image")
        nodes.append(node)
    for link_id, source, slot, *_ in links:
        nodes[source - 1]["outputs"][slot]["links"].append(link_id)
    return {
        "last_node_id": len(nodes), "last_link_id": len(links),
        "nodes": nodes, "links": links, "groups": [], "config": {},
        "extra": {"ds": {"scale": 0.5, "offset": [40, 40]}}, "version": 0.4,
    }


if __name__ == "__main__":
    directory = ROOT / "workflows"
    directory.mkdir(exist_ok=True)
    api = graph()
    for filename, content in [
        ("minimax-h3-anime.api.json", api),
        ("minimax-h3-anime.json", ui_workflow(api)),
    ]:
        (directory / filename).write_text(json.dumps(content, indent=2) + "\n")
