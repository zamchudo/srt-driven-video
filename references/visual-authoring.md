# 场景开发契约（scenes/scene-NNN）

## 渲染契约（硬性）

每镜 `index.html` 必须实现 **`window.setTime(tSeconds)`**：给定镜头本地时间 t，页面确定性呈现该时刻画面。渲染器逐帧调用 setTime 再截图，因此：

- 禁止依赖真实时间（Date.now / requestAnimationFrame 自发推进）驱动画面；一切动画 = t 的纯函数。
- 禁止随机数失控：粒子等用带种子的伪随机（seededRandom）。
- 设计坐标固定 1920×1080，用 `fitStage(stage, w, h)` 整体缩放适配视口（组件库已含）。
- 页面从 URL query 读取 `?w=&h=`。

## 文件结构

```
scenes/scene-NNN/
├── index.html   # 引入 ../../assets/shared/theme.css + components.js + 本镜 scene.css/scene.js
├── scene.css    # 本镜布局
└── scene.js     # setTime 实现 + 字幕 cues（SRT 全局时间换算为本地时间）
```

## 字幕烧录（现场字幕条）

- 统一元素：`<div id="subtitle" class="subtitle-band"></div>`（**这个 id 是契约**——无字幕变体靠它隐藏）。
- 用 `SubtitleTrack(element, cues)`，cues 的 start/end 为**镜头本地时间**（SRT 全局时间 − 本镜 start）。
- 字幕条样式：发光描边、底部横条；由 theme.css 的 `.subtitle-band` 提供。

## 转场

- 每镜末尾 0.3s 统一转场（扫描线+闪白，`TransitionFX`），末镜为渐隐。**≤0.3s，无频闪**。
- 镜头 start 时间即音效卡点标注点（写入 storyboard 的 sfx_cue 字段）。

## 组件库起步

`assets/neon-theme/`（本 skill 内）是已拍板的科技霓虹风参考实现：theme.css（色板/字幕条/转场/数据卡片样式）+ components.js（深空粒子 SpaceField、逐字飞入 neonText/revealText、数据卡片 dataCard、对比条形 comparisonBars、风险色标 riskLegend、转场 TransitionFX、字幕 SubtitleTrack、fitStage）。

- 用户要同款霓虹风 → 直接复制到项目 `assets/shared/`。
- 其他风格 → 以它为结构蓝本重写 theme.css（色板、字号阶梯），组件接口保持不变可少踩坑。

## 质检流程（每镜必做，渲染前）

```bash
python <skill>/scripts/check_frames.py scenes/scene-NNN --times 0.5,<中段>,<结尾前0.5s>,<转场中>
```

人工查看 keyframes.jpg：无空白帧、无脚本错误（脚本会打印 pageerror）、无文字溢出、无字幕错句、**画面数字与 storyboard 逐一核对**。

## 设计红线（面向年长受众时）

- 每屏 ≤3 行字、正文 ≥44px（1920×1080 设计坐标）、核心数字 ≥100px、一屏一个核心信息。
- 文字实心高亮，禁用细描边小字；零网络梗、零英文缩写（写"人工智能"不写 AI）。
- 屏幕上的关键数字带完整单位；与口播一致。
