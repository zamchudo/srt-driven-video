---
name: srt-driven-video
description: 文稿/SRT 驱动、代码生成视觉的讲解汇报视频流水线。Use when 用户要把口播稿/汇报内容做成带字幕条的视频（汇报视频、讲解视频、口播视频、发布会风格视频、文稿驱动视频、SRT 驱动动画），覆盖五阶段：大纲 → 文稿+SRT → 分镜 storyboard → HTML/JS 逐镜确定性渲染（Playwright+FFmpeg）→ 拼接交付 final.mp4。支持多画幅（16:9 / 竖屏 9:16 / 4:3 / 正方形）。内含可选音效模块（Freesound CC0 下载、adelay+amix 混音或剪映对点清单，默认关闭）与跨会话 WORKLOG 接力机制。
---

# SRT-Driven Video（SRT 驱动视频流水线）

把一篇口播稿变成一部代码生成视觉的讲解视频。**以 SRT 为唯一时间基准**，分五阶段推进，每阶段结束暂停等用户确认。

## 环境与依赖

- Windows：Playwright（`channel="msedge"`，用本机 Edge 免装 Chromium）+ imageio-ffmpeg（提供 ffmpeg；**不含 ffprobe**，用 `ffmpeg -i` stderr 解析规格）。
- 依赖安装：`pip install playwright imageio-ffmpeg`（脚本内已处理 ffmpeg 定位）。
- 本 skill 的 scripts/ 全部为 Windows 实测适配版；Linux/macOS 需去掉 `channel="msedge"` 并改用系统 ffmpeg。

## 五阶段总览

| 阶段 | 产物 | 确认门 |
|---|---|---|
| 0 大纲 | outline.md + 决策表 | 用户确认大纲与决策 |
| 1 文稿+SRT | script.md / subtitles.srt / 讲者备注.md | 用户确认文稿 |
| 2 分镜 | storyboard.json（check_timeline.py 必过） | 用户确认分镜 |
| 3a 首镜+组件库 | assets/shared/ + scene-001 低清样片 | **用户拍板风格后才批量** |
| 3b 逐镜批量 | scenes/scene-NNN/scene.mp4 × N | 用户复核重点镜头 |
| 4 拼接交付 | output/final.mp4 + cover.png | 用户确认终片 |

详细流程、决策表字段、常见坑（imageio-ffmpeg 无 filter_complex_script、alimiter 的 level 陷阱等）见 [references/pipeline.md](references/pipeline.md)。

## 三条核心契约（不可省）

1. **SRT 时间基准**：分镜边界落在字幕条边界，总跨度误差 ≤0.1s；`python scripts/check_timeline.py <project_dir>` 每阶段复检。
2. **WORKLOG 接力**：项目根建 `WORKLOG.md`（模板见 [references/worklog-template.md](references/worklog-template.md)），跨会话唯一状态载体；决策表锁定后不可擅改；阶段 3/4 起基线文件（outline/script/SRT/讲者备注/storyboard/assets/shared/scenes）冻结。
3. **阶段确认门**：每阶段汇报后暂停，等用户明确确认再进下一阶段。

## 场景渲染（阶段 3）

每镜是独立 HTML 页面，实现 `window.setTime(t)` 确定性渲染（一切动画是 t 的纯函数）；字幕烧录用统一契约元素 `div#subtitle`。完整开发契约、质检流程（check_frames.py 关键帧拼图）、设计红线见 [references/visual-authoring.md](references/visual-authoring.md)。

起步模板：`assets/neon-theme/`（已拍板的科技霓虹风 theme.css + components.js，含粒子/逐字飞入/数据卡片/对比条形/风险色标/转场/字幕组件）——用户要同款风格直接复制到项目 `assets/shared/`，其他风格以其为结构蓝本。

```bash
python scripts/render_scene.py scenes/scene-001 --duration 10.5 --fps 30 --size 960x540   # 低清样片
python scripts/check_frames.py scenes/scene-NNN --times 0.5,3,6,9.2                        # 渲染前质检
python scripts/render_all.py .                                                             # 批量全清
python scripts/render_all.py . --no-subtitle --outdir output/nosub                         # 无字幕变体
python scripts/concat_final.py .                                                           # 拼接 + 封面
```

## 可选音效模块（默认关闭）

仅当用户明确要卡点音效时启用，且阶段 0 决策表就锁定。素材走 Freesound CC0（逐条核验许可），时间线落 `assets/sfx/mix_timeline.json` 并先给用户预审；交付两条路径二选一：FFmpeg 自动混音（mix_sfx.py），或导出剪映对点清单（make_cue_sheet.py）由用户手动添加——后者实测更稳。完整流程见 [references/sound.md](references/sound.md)。

### 参考的外部 skill / 工具

- **[vibe-motion/auto-motion](https://github.com/vibe-motion/auto-motion)**：SRT→MG 动画工作流，本 skill 的时间轴校验等工程约束沿用自它（check_timeline.py 注释有标注）。
- **[vibe-motion/sound](https://github.com/vibe-motion/sound)**：音效搜索/下载 CLI（Freesound/Pixabay/Mixkit/Kenney），克隆到项目 tools/sound/ 使用。**克隆时仓库无 LICENSE，仅作内部下载工具**；许可以 Freesound 单条音效 CC0 声明为准。

## 交付规格

final.mp4：默认 1920×1080 / 30fps / h264 / yuv420p，时长精确匹配 SRT 总跨度；**画幅在阶段 0 决策表锁定**（16:9 1920×1080 / 竖屏 9:16 1080×1920 / 4:3 1440×1080 / 正方形 1080×1080，渲染与拼接全程同一 `--size`，选择引导见 pipeline.md 阶段 0）；cover.png 取高潮定格帧（抽帧实测定位）；核验时长、帧数、规格、音轨电平后更新 WORKLOG 再汇报。
