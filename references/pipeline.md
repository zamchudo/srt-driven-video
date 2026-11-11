# 流水线详细流程（阶段 0–4）

> 总原则：**SRT 是唯一时间基准**；每阶段结束**暂停等用户确认**再进下一阶段；跨会话用 WORKLOG 接力。

## 目录契约

```
<project>/
├── WORKLOG.md            # 唯一状态载体（模板见 worklog-template.md）
├── outline.md            # 阶段 0 产物
├── script.md             # 阶段 1：口播正文
├── subtitles.srt         # 阶段 1：全流程时间基准
├── 讲者备注.md            # 阶段 1：现场讲解提词卡
├── storyboard.json       # 阶段 2：分镜（含每镜 start/end/duration_sec/assets/音效卡点标注）
├── assets/
│   ├── shared/           # 阶段 3a：共享组件库（theme.css + components.js）
│   ├── images/           # 截图/图片素材
│   ├── videos/           # CC0 实拍空镜（仅确需时）
│   └── sfx/              # 可选音效模块（见 sound.md）
├── scenes/scene-NNN/     # 阶段 3b：每镜 index.html + scene.css + scene.js + scene.mp4
├── tools/                # 从 skill scripts/ 复制或引用
└── output/               # 阶段 4：final.mp4 + cover.png
```

## 阶段 0 大纲

- 产出 `outline.md`：章节结构 + 每章要点 + 预估字数。
- **开工前先与用户锁定决策表**（写入 WORKLOG"已锁定的决策"，之后不可擅改）：
  受众（年龄/背景→决定语速、字号、动效强度）、总时长、讲解形式（真人讲解 or 配音）、视觉风格（给参考案例但明确"参考而非照搬"）、声音方案（无 BGM / 卡点音效 / 后制）。
- 年长受众实测约束：语速 4 字/秒、每屏 ≤3 行字、正文 ≥44px、核心数字 ≥100px、一屏一个核心信息、无频闪（glitch 降级为扫描线+闪白 ≤0.3s）、数字口播带全单位（"一千零六十亿元"）。

## 阶段 1 文稿 + SRT

- 产出 `script.md`（按汉字计字数，不含标点）、`subtitles.srt`、`讲者备注.md`。
- SRT 规范：每条 1.00–3.00 秒、连续无空隙、总跨度=视频总时长；时间用 `HH:MM:SS,mmm`。
- 自检：字幕拼接可逐字还原口播正文；口播无英文缩写、阿拉伯数字改中文口播。

## 阶段 2 分镜

- 产出 `storyboard.json`：
  ```json
  {"scenes": [{"id": "scene-001", "start": 0.0, "end": 10.5, "duration_sec": 10.5,
               "chapter": "第一章", "visual": "画面描述", "sfx_cue": "音效卡点标注", "assets": []}]}
  ```
- 硬约束：镜头边界必须落在字幕条边界上；单镜 8–12s 为原则（例外须注明理由）；全程无重叠无遗漏。
- 校验：`python <skill>/scripts/check_timeline.py <project_dir>` 必须通过（容差 0.05s，总跨度误差 ≤0.1s）。

## 阶段 3a 首镜 + 组件库（风格定调）

- 先做 `assets/shared/`（theme.css 色板 + components.js 确定性组件）和 scene-001 **低清样片**（960×540）：
  `python <skill>/scripts/render_scene.py scenes/scene-001 --duration 10.5 --fps 30 --size 960x540`
- 首镜必须一屏展示全部角色色（主背景/主强调/辅助/正文/分级色），供用户一次拍板。**拍板前不做批量**。

## 阶段 3b 逐镜批量

- 每镜契约见 visual-authoring.md。每镜渲染前先质检：
  `python <skill>/scripts/check_frames.py scenes/scene-NNN --times 0.5,<中段>,<结尾前>,<转场点>` → 人工看图，确认无空白帧/脚本错误/文字溢出/字幕错句/数字与 storyboard 一致。
- 批量全清渲染：`python <skill>/scripts/render_all.py .`（或指定镜头 `... . scene-003 scene-005`）。
- 实测速度参考：Playwright+Edge 约 0.13–0.3 s/帧；3 分钟全片全清约 15–30 分钟。
- 完成后 `check_timeline.py` 复检 + FFmpeg 逐镜核验规格（1920×1080/30fps/yuv420p/时长与 storyboard 一致）。

## 阶段 4 拼接交付

- `python <skill>/scripts/concat_final.py <project_dir>` → `output/final.mp4` + `cover.png`。
  - 规格不一致的镜头会自动规范化转码；`--cover-time <秒>` 指定封面取帧（**选高潮定格帧，逐帧找真实定格时刻，勿信标注**）。
  - 无 BGM 默认；`--bgm` / `--sfx`（音效轨，需先跑 sound 模块的 mix_sfx.py）可选。
- 核验清单：时长精确到 0.01s、帧数=时长×fps、1920×1080、30fps、h264、yuv420p、音轨 volumedetect 无削波（max ≤ -0.3dB）。
- 无字幕变体：`render_all.py . --no-subtitle --outdir output/nosub` 后再用 concat 命令拼接（参考本项目 render_nosub 用法；#subtitle 层由 `--no-subtitle` 注入 CSS 隐藏）。

## 常见坑（本次实测）

1. imageio-ffmpeg 精简构建**不支持 `-filter_complex_script`**，filter 图须内联 `-filter_complex` 传参（subprocess 列表传参可超 8191 字符，不要用 cmd /c）。
2. imageio-ffmpeg **不含 ffprobe**：用 `ffmpeg -i` 的 stderr 解析规格（concat_final.py 的 probe() 已是此实现）。
3. Windows 渲染用 Playwright `channel="msedge"`（免装 Chromium）；首次运行需 `playwright install` 不要求，Edge 需已安装。
4. FFmpeg `alimiter` 默认 `level=1` 会在限幅后自动回补增益——防削波必须显式 `level=0`。
5. 烧录字幕修改（哪怕只去句号）影响全部镜头，须全量重渲染；先把文案类反馈收集齐再渲染。
6. 画面动画的实际定格时刻可能与分镜标注不同，封面/音效卡点以抽帧实测为准。
