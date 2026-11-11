# srt-driven-video

SRT 驱动、代码生成视觉的讲解汇报视频流水线（Kimi skill）。把一篇口播稿变成一部带字幕条的讲解视频：大纲 → 文稿+SRT → 分镜 storyboard → HTML/JS 逐镜确定性渲染（Playwright + FFmpeg）→ 拼接交付。

- **SRT 是唯一时间基准**：分镜边界落在字幕条边界，总跨度误差 ≤0.1s，脚本强制校验
- **确定性渲染**：每镜一个 HTML 页面，实现 `window.setTime(t)`，逐帧截图合成，无随机性漂移
- **跨会话接力**：WORKLOG.md 单一状态载体 + 决策表锁定 + 每阶段用户确认门
- **可选音效模块**（默认关闭）：Freesound CC0 素材 → 混音时间线预审 → FFmpeg 自动混音，或导出剪映手动对点清单
- 附已拍板的科技霓虹风起步模板（`assets/neon-theme/`）

入口与完整说明见 [SKILL.md](SKILL.md)；流水线细节在 [references/](references/)；脚本在 [scripts/](scripts/)。

## 环境

Windows（Playwright `channel="msedge"` + imageio-ffmpeg）；Linux/macOS 需去掉 `channel="msedge"` 改用系统 ffmpeg。

```bash
pip install playwright imageio-ffmpeg
```

## 参考的外部工具

- [vibe-motion/sound](https://github.com/)（Freesound 搜索/下载 CLI，克隆到项目 tools/sound/ 使用）：仓库无 LICENSE，仅作内部下载工具；许可以 Freesound 单条音效 CC0 声明为准。
