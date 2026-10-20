# MiniMax H3 Anime I2V on Miyabi-G

用 comfy-cli 管理 ComfyUI，在 Miyabi-G 的 PBS 计算节点上把参考图生成短视频。
源码项目：`/work/xg24i002/x10041/comfy-anime`。脚本可从任意 checkout 使用，
会自动确定自身的仓库路径；提交后请保持该 checkout 可读，直到作业结束。

## 持久目录与模型

**后续任务复用 `/work/xg24i002/x10041/comfy-anime-data`，不必重新安装或下载。**
默认值在 `config/runtime.env`；可用环境变量 `COMFY_DATA_ROOT` 覆盖为另一个绝对路径。
该目录必须在 Git 工作树外。模型、虚拟环境、输入图片、输出视频和缓存均不提交到 Git。

| 路径（相对于持久目录） | 用途 |
| --- | --- |
| `venv/` | Python 3.12、comfy-cli 1.22.0 |
| `ComfyUI/` | 固定提交的 ComfyUI 与 Manager |
| `ComfyUI/.venv/` | aarch64 推理环境，PyTorch 2.11.0+cu130 |
| `ComfyUI/models/` | 固定版本的模型权重 |
| `input/`、`output/` | 输入图片和 MP4 |
| `runs/<run-id>/` | 本次参数、API 图、日志、history、LoRA 检查、视频校验结果 |
| `logs/`、`requests/` | PBS 日志、提交参数 |
| `models-verified.json` | 所有模型 SHA256 检查通过后的清单 |
| `installed-requirements.txt`、`comfy-snapshot.json` | 实际依赖版本和 comfy-cli 环境快照 |

模型清单 `config/models.json` 固定 Hugging Face revision、文件长度与 SHA256，
共约 **53.4 GB**。环境、下载缓存也需要空间，建议预留至少 100 GB。

| 组件 | 文件 |
| --- | --- |
| [WarmBloodAban/Minimax-h3_Singularity](https://huggingface.co/WarmBloodAban/Minimax-h3_Singularity) | `Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors` |
| [Anime Motion LoRA](https://huggingface.co/prithivMLmods/MiniMax-H3-I2V-Anime-Motion-LoRA) | `MiniMax-H3-I2V-Anime-Motion-LoRA-1400.safetensors` |
| [H3 文本/视觉编码器](https://huggingface.co/Comfy-Org/MiniMax-H3) | `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` |
| H3 视频 VAE | `minimax_h3_video_vae_fp16.safetensors` |

LoRA 的触发词是 `Anime-Motion`。该 LoRA 没有 AdaLN 权重，适用于这里选用的裁剪版。
每次 headless 运行前都会检查全部 A/B 权重对是否匹配基础模型形状，
结束时也会拒绝存在未加载 LoRA 权重警告的结果。

## 工作流

导入 `workflows/minimax-h3-anime.json` 可在 ComfyUI 中编辑；
`workflows/minimax-h3-anime.api.json` 可直接提交 API。
两个文件由 `scripts/make_workflows.py` 同时生成。

```text
UNETLoader → LoraLoaderModelOnly ────────────┐
                                           ├→ SamplerCustomAdvanced
LoadImage → MiniMaxH3ReferenceToVideo ───────┤          ↓
              ↑ CLIPLoader、VAELoader       │      VAEDecode
RandomNoise、BasicGuider、BasicScheduler ────┘          ↓
                                                CreateVideo → SaveVideo
```

指定的 Singularity 文件属于 **ref2va** 模型族，因此使用原生
`MiniMaxH3ReferenceToVideo` 接入参考图片，提示词以 `<Picture 1>` 指代输入。
这是参考图驱动的视频生成；它不承诺第一帧逐像素等于输入图。
没有替换成另一个 FL2VA 基础模型。参考图同时进入视觉编码器和 VAE 条件，
LoRA 同时连接采样器的模型及时间表。使用 `res_multistep` + `simple`。
本流程导出无声 H.264 MP4，不下载音频 VAE。

所有必需节点均已由固定版本的 ComfyUI 原生提供，无需第三方自定义节点包。
ComfyUI-Manager 通过 comfy-cli 安装；可用以下命令查看或管理后续增加的节点：

```bash
source scripts/common.sh
comfy node simple-show installed --mode local
# 需要增加节点时，在计算节点执行：
# comfy node install <registry-id>
```

## 首次安装和模型下载

登录节点只进行编辑、调度和轻量检查。安装、下载校验、测试、模型加载、
推理都由脚本强制要求有效的 Miyabi-G PBS 分配。不要在登录节点直接运行 ComfyUI。
需要 `uv`、Miyabi 的 PBS/Modules，以及已有的
`/work/xg24i002/x10041/.codex/skills/miyabi-pbs-cmd`；
后者位置可用 `MIYABI_PBS_CMD_ROOT` 覆盖。

从仓库根目录提交安装：

```bash
bash scripts/submit.sh install
```

确认该作业成功后，再提交下载：

```bash
bash scripts/submit.sh download
```

安装使用 `comfy install --version nightly --commit ... --nvidia --cuda-version 13.0 --fast-deps`，
并固定 torch/torchvision/torchaudio 的 CUDA 13.0 aarch64 wheels。
PBS 内加载站点的 `cuda/13.2` module；CUDA 13 驱动是此环境的前提。
ComfyUI 当前版本的 INT8 CUDA 后端需要 cu130 或更高版本。
每个权重使用 `comfy model download` 下载，随后检查大小和 SHA256。
已存在且校验通过的文件复用；损坏文件会报错，不会静默使用。

也可以在交互计算分配中顺序执行，便于检查日志：

```bash
qsub -I -q interact-g -W group_list=xg24i002 \
  -l select=1:mpiprocs=1 -l walltime=00:55:00
# 进入计算节点后：
cd /work/xg24i002/x10041/comfy-anime
bash scripts/install.sh
bash scripts/download-models.sh
```

## 一条命令提交图生视频

环境和模型准备好后，从登录节点执行：

```bash
bash scripts/submit.sh run --image /absolute/path/reference.png \
  --prompt 'Anime-Motion: Use <Picture 1> as reference. Hair and clothing sway gently in the breeze, fixed camera.' \
  --width 832 --height 480 --frames 124 --fps 24 --steps 20 \
  --seed 42 --lora-strength 1.0
```

提交器将参数存入 JSON，提示词不作为 shell 代码求值。相对图片路径会在提交时转为绝对路径。
输出直接写回共享持久目录，计算节点退出后仍保留：

```text
comfy-anime-data/output/run-<id>/video_00001_.mp4
comfy-anime-data/runs/run-<id>/result.json
```

PBS 日志会打印具体路径。`result.json` 只有在工作流成功、视频所有帧可解码、
参数一致、有画面及帧间变化、LoRA 检查通过后才会生成。
这些校验用于发现流程故障，不等同于画面质量评测。

在已分配的计算节点上，可直接用同一命令运行并等待输出：

```bash
bash scripts/run.sh --image /absolute/path/reference.png --seed 123
```

| 参数 | 默认值 | 约束/含义 |
| --- | --- | --- |
| `--prompt` | 内置风筝场景提示词 | 使用 `Anime-Motion` 和 `<Picture 1>` |
| `--width`、`--height` | 832、480 | 32 的正整数倍 |
| `--frames` | 124 | `17k+5`：5、22、39、…、124；最多 3600 |
| `--fps` | 24 | 1–120，改变导出播放速度；模型本身按 24 FPS 建模 |
| `--steps` | 20 | 没有启用额外 Turbo LoRA |
| `--seed` | 42 | uint64 |
| `--lora-strength` | 1.0 | 大于 0、不超过 2 |

H3 训练时长约 5–15 秒；超过此范围的长度、较大尺寸和不同播放帧率需要自行评估质量和显存。
参考：[ComfyUI H3 文档](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)。

默认队列 `short-g`，计费组 `xg24i002`，1 节点，55 分钟。可覆盖：

```bash
PBS_QUEUE=short-g PBS_WALLTIME=00:30:00 bash scripts/submit.sh run --smoke
```

`pbs/comfy.pbs` 是复用的 PBS 入口。调度和日志查询：

```bash
/usr/bin/python3 -I /work/xg24i002/x10041/.codex/skills/miyabi-pbs-cmd/scripts/qstat_json.py JOB_ID --summary
ls /work/xg24i002/x10041/comfy-anime-data/logs/
```

若超时或出错，查看对应 PBS 日志以及 `runs/<id>/server.log`、`events.jsonl`；
没有 `result.json` 的运行不能视为成功。不要同时在同一节点的同一端口启动多个服务；
需要时用 `COMFY_PORT=8189` 覆盖。作业结束即释放 GPU，不提供脱离 PBS 的常驻服务。

## 启动 Web UI

```bash
bash scripts/submit.sh serve
```

也可在交互分配中执行 `bash scripts/serve.sh`。
服务仅监听计算节点 `127.0.0.1:8188`；PBS 日志给出实际主机名。
在本地电脑通过自己的 Miyabi 登录主机建立 SSH 隧道（替换示例主机）：

```bash
ssh -J x10041@YOUR_MIYABI_LOGIN -L 8188:127.0.0.1:8188 x10041@COMPUTE_HOST
```

浏览器打开 `http://localhost:8188`，导入工作流、在 LoadImage 节点上传图片。
SSH 到计算节点须符合站点规则，并处于自己有效的分配内。
MP4 在共享文件系统上；下载到本地可用：

```bash
scp x10041@YOUR_MIYABI_LOGIN:/work/xg24i002/x10041/comfy-anime-data/output/run-ID/video_00001_.mp4 .
```

## 验证

```bash
# 计算节点上的脚本/工作流合同测试
bash scripts/submit.sh check
# 自动创建合成参考图，执行真实模型 + LoRA 推理，并校验视频
bash scripts/submit.sh run --smoke
```

冒烟默认 384×256、39 帧、24 FPS、20 步、seed 42、LoRA 1.0。
它用于验证加载与整条链路，不作为正式画质设置。每次运行保存完整参数、
实际提交图、ComfyUI history、LoRA 权重匹配计数及 MP4 检查结果。
输入图由脚本绘制，无需外部图片文件或服务。

修改图后，在计算节点执行以下命令重新生成两个 JSON，再检查：

```bash
/work/xg24i002/x10041/comfy-anime-data/ComfyUI/.venv/bin/python scripts/make_workflows.py
bash scripts/check.sh
```
