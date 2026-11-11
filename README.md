# srt-driven-video

> 以 SRT 为时间基准、代码生成视觉的讲解视频流水线：大纲→SRT→分镜→确定性渲染→拼接；多画幅，可选音效，WORKLOG 接力。
> SRT-driven pipeline turning a narration script into a code-generated subtitled video (Playwright + FFmpeg). Multi-aspect, optional SFX, WORKLOG handoff.

在 [vibe-motion/auto-motion](https://github.com/vibe-motion/auto-motion) 的工程约束（SRT 时间基准、逐镜独立目录、FFmpeg 拼接）上，面向**真人现场讲解的汇报视频**场景演化：增加决策表锁定、每阶段用户确认门、跨会话 WORKLOG 接力，以及可选的 Freesound CC0 卡点音效模块。全流水线在一个真实项目（18 镜 / 187.5s / 1080p30）上完整验证过。

## 特性

- **SRT 是唯一时间基准**：分镜边界必须落在字幕条边界，总跨度误差 ≤0.1s，`check_timeline.py` 强制校验，不过不进下一阶段
- **确定性渲染**：每镜一个 HTML 页面实现 `window.setTime(t)`，一切动画是 t 的纯函数；Playwright 逐帧截图 + FFmpeg 合成，渲染结果可复现、可任意抽帧质检
- **多画幅**：16:9 1920×1080（默认）/ 竖屏 9:16 1080×1920 / 4:3 1440×1080 / 正方形 1080×1080，阶段 0 按投放场景锁定
- **阶段确认门**：首镜样片先定风格，用户拍板后才批量渲染，把返工挡在最便宜的环节
- **跨会话接力**：`WORKLOG.md` 单一状态载体 + 决策表锁定 + 基线文件冻结，换会话/换模型无缝接手
- **可选音效模块**（默认关闭）：Freesound CC0 素材 → 时间线预审 → FFmpeg 混音**或**导出剪映手动对点清单
- **变体输出**：一行参数产出无字幕版（`--no-subtitle`），不动原镜头

## 流水线架构

| 阶段 | 产物 | 确认门 |
|---|---|---|
| 0 大纲 | `outline.md` + 决策表 | 用户确认大纲与决策 |
| 1 文稿+SRT | `script.md` / `subtitles.srt` / `讲者备注.md` | 用户确认文稿 |
| 2 分镜 | `storyboard.json`（`check_timeline.py` 必过） | 用户确认分镜 |
| 3a 首镜+组件库 | `assets/shared/` + scene-001 低清样片 | **用户拍板风格后才批量** |
| 3b 逐镜批量 | `scenes/scene-NNN/scene.mp4` × N | 用户复核重点镜头 |
| 4 拼接交付 | `output/final.mp4` + `cover.png` | 用户确认终片 |

三条核心契约：

1. **SRT 时间基准**——所有镜头时长和与 SRT 跨度误差 ≤0.1s；
2. **WORKLOG 接力**——决策表锁定后不可擅改，阶段 3/4 起基线文件冻结；
3. **阶段确认门**——每阶段汇报后暂停，等用户确认再进下一阶段。

## 目录说明

```
.
├── SKILL.md                  # skill 入口：五阶段总览、核心契约、交付规格
├── references/
│   ├── pipeline.md           # 阶段 0–4 详细流程 + 决策表字段 + 实测踩坑
│   ├── visual-authoring.md   # 场景开发契约（setTime/字幕烧录/转场/质检/设计红线）
│   ├── worklog-template.md   # WORKLOG 跨会话接力模板 + 确认门规则
│   └── sound.md              # 可选音效模块完整流程
├── scripts/
│   ├── render_scene.py       # 单镜渲染（Playwright 逐帧截图 → FFmpeg 合成）
│   ├── render_all.py         # 批量渲染（读 storyboard 时长，支持 --no-subtitle/--outdir 变体）
│   ├── check_timeline.py     # 分镜时间轴 vs SRT 强制校验
│   ├── check_frames.py       # 关键帧拼图质检（渲染前必做）
│   ├── concat_final.py       # 拼接 + 规格规范化 + BGM/音效轨 + 封面（--size 多画幅）
│   ├── mix_sfx.py            # 音效混音（adelay+amix，JSON 时间线驱动，-1dB 限幅）
│   ├── make_cue_sheet.py     # 剪映手动对点清单导出
│   ├── verify_sfx.py         # 素材解码验证（时长/电平）
│   └── check_license.py      # Freesound 页面逐条 CC0 核验
└── assets/neon-theme/        # 已拍板的科技霓虹风起步模板（theme.css + components.js）
```

## 前提条件

- Windows 10/11 + Microsoft Edge（渲染器用 Playwright `channel="msedge"`，免装 Chromium）
- Python 3.10+

```bash
pip install playwright imageio-ffmpeg pillow
```

> Linux/macOS：去掉脚本中的 `channel="msedge"` 并改用系统 ffmpeg（imageio-ffmpeg 仅用于定位 ffmpeg 二进制；它**不含 ffprobe**，脚本已用 `ffmpeg -i` stderr 解析替代）。

## 快速开始

把本仓库放入 Kimi skills 目录（或项目 `.agents/skills/`），然后对 agent 说：

> 用 srt-driven-video 把这份汇报内容做成一个 3 分钟讲解视频

agent 会按五阶段推进。画幅在阶段 0 与用户确认（竖屏自媒体 1080×1920、横屏 1920×1080、4:3 1440×1080、正方形 1080×1080）。各阶段关键命令（agent 自动执行，此处供人工核对）：

```bash
# 阶段 2：分镜时间轴校验（必须通过）
python scripts/check_timeline.py <project_dir>

# 阶段 3a：首镜低清样片（风格定调）
python scripts/render_scene.py scenes/scene-001 --duration 10.5 --fps 30 --size 960x540

# 阶段 3b：每镜渲染前关键帧质检 → 批量全清渲染
python scripts/check_frames.py scenes/scene-NNN --times 0.5,3,6,9.2
python scripts/render_all.py .

# 阶段 4：拼接 + 封面（--cover-time 指定高潮定格帧，--size 多画幅）
python scripts/concat_final.py . --cover-time 109.0
python scripts/concat_final.py . --size 1080x1920   # 竖屏项目

# 变体：无字幕版（不动 scenes/ 原镜头）
python scripts/render_all.py . --no-subtitle --outdir output/nosub
```

## 可选音效模块（默认关闭）

仅当用户明确要卡点音效时启用，且在阶段 0 决策表就锁定：

1. **素材**：用 [vibe-motion/sound](https://github.com/vibe-motion/sound) 从 Freesound 按 CC0 筛选下载，`check_license.py` 逐条核验许可、`verify_sfx.py` 解码验证，落 `assets/sfx/manifest.json`；
2. **时间线**：`assets/sfx/mix_timeline.json`（事件时刻/增益/成组展开/截断淡出全部 JSON 声明，脚本零硬编码），**先给用户预审再混音**；
3. **交付二选一**：`mix_sfx.py` 自动混音叠加，或 `make_cue_sheet.py` 导出剪映对点清单由用户手动添加（实测教训：对音效品质要求高时后者更稳）。

完整流程见 [references/sound.md](references/sound.md)。

## 交付规格与质检

`final.mp4`：决策表锁定的画幅（默认 1920×1080）/ 30fps / h264 / yuv420p，时长精确匹配 SRT 总跨度（帧数 = 时长 × fps 逐一核对）；有音轨时 volumedetect 峰值 ≤ -0.3dB 无削波；`cover.png` 取高潮定格帧（抽帧实测定位，不信标注）。

## 参考与致谢

- [vibe-motion/auto-motion](https://github.com/vibe-motion/auto-motion)：SRT→MG 动画工作流，本 skill 的时间轴校验等工程约束沿用自它
- [vibe-motion/sound](https://github.com/vibe-motion/sound)：音效搜索/下载 CLI（克隆时仓库无 LICENSE，仅作内部下载工具；许可以 Freesound 单条音效 CC0 声明为准）
- [Freesound](https://freesound.org/)：CC0 音效素材来源

## License

[MIT](LICENSE)。引用的外部工具与素材以其各自声明为准。
