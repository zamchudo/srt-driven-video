# 可选音效模块（默认关闭）

> **仅在用户明确要卡点音效时启用。** 阶段 0 决策表"声音"一栏就应问清；用户无要求则终片无声，不要在阶段 4 临时加。

## 两条交付路径（先问用户选哪条）

| 路径 | 说明 | 适用 |
|---|---|---|
| A. FFmpeg 自动混音 | mix_sfx.py 按时间线一次性叠加进 final.mp4 | 用户接受程序化混音效果 |
| B. 导出对点清单 | 生成 cue sheet，用户在剪映等软件手动添加 | 用户对音效品质要求高（实测教训：FFmpeg 混音版被用户否过一轮，最终走了这条） |

两条路径都先做"素材下载 + 混音时间线"，分叉只在最后一步。

## 素材下载（Freesound CC0）

外部工具：**[vibe-motion/sound](https://github.com/vibe-motion/sound)**（克隆到项目 `tools/sound/` 使用；支持 Freesound/Pixabay/Mixkit/Kenney 搜索下载，本机实测搜索→下载→解码全链路可用）。注意：**克隆时仓库无 LICENSE，仅作内部下载工具**；真正的许可层是 Freesound 单条音效的声明。

```bash
python tools/sound/scripts/sfx.py freesound "<英文关键词>" --license cc0 --urls   # 搜索
python tools/sound/scripts/sfx.py get assets/sfx/ fs:<id>                          # 下载
```

纪律：

1. **只下载 CC0**（零署名负担）；下载后逐条核验：
   `python <skill>/scripts/check_license.py <freesound_id>...`（依赖 sfx.py 的缓存索引 `~/.cache/sfx-sources/index.json` 取作者页 URL；无缓存时退化为按 id 抓页面）。
2. 解码验证：`python <skill>/scripts/verify_sfx.py assets/sfx`（时长/峰值；MP3 解码填充会使实测比标称长约 0.02s，可忽略）。
3. 生成 `assets/sfx/manifest.json`：每条含 file / cues / freesound_id / license / duration_sec。
4. 时长超限的候选剔除换备选；无人声、无音乐旋律（与"无 BGM"兼容）。

## 混音时间线（assets/sfx/mix_timeline.json）

mix_sfx.py 与 make_cue_sheet.py 共用同一份 JSON，**脚本零硬编码**，全部字段：

```json
{
  "video_duration_sec": 187.5,
  "normalize_first": {"file": "xxx.mp3", "target_peak": 0.9, "reason": "原始电平过低"},
  "events": [
    {"time": 10.5, "file": "whoosh.mp3", "gain_db": 0.0, "note": "scene-002 转场"},
    {"time": 37.35, "file": "char_tick.mp3", "gain_db": -2.0,
     "expand": {"count": 12, "step": 0.13}, "note": "scene-005 逐字 tick"},
    {"time": 185.75, "file": "ending.mp3", "gain_db": -2.0,
     "trim_sec": 1.75, "fade_out_sec": 0.5, "note": "尾音（片尾前截断淡出）"}
  ],
  "stage4_notes": ["预审决议等自由文本"]
}
```

- 全局时间秒；事件发生时刻 = storyboard 各镜 start 或画面动画关键时刻（**以抽帧实测为准**，勿只信标注）。
- 成组事件（逐字 tick、连续滴答）用 `expand`：只写组起点，脚本按 count × step 展开；密度列入预审请用户拍板。
- 需要在片尾/下一事件前收净的素材用 `trim_sec` + `fade_out_sec`。
- **混音前先给用户一版预审**：把全部事件连同待决项（密度、取舍、时刻分歧）列成清单请用户确认，决议写回 JSON。实测四个待决项一次问清最省事。
- 电平偏低的素材在 `normalize_first` 声明归一化目标（peak 0.9）。

## 路径 A：FFmpeg 混音

```bash
python <skill>/scripts/mix_sfx.py <project_dir>          # → output/sfx_mix.wav
python <skill>/scripts/concat_final.py <project_dir> --sfx output/sfx_mix.wav
```

mix_sfx.py 行为：读 mix_timeline.json → 展开成组事件 → adelay+amix（normalize=0，保持相对增益）→ `alimiter=limit=0.891:level=0` 防叠加削波（**level=0 必须显式，否则限幅后自动回补**）→ 自检时长/峰值。

## 路径 B：对点清单（剪映手动）

```bash
python <skill>/scripts/make_cue_sheet.py   # 内部读 assets/sfx/mix_timeline.json → output/sfx_cue_sheet.txt
```

清单含 mm:ss.mmm 时间码 + 素材 + 建议增益 + 画面说明；附实操备注（低电平素材先加拉、成组事件可减密度简化等）。终片交付无声版即可。
