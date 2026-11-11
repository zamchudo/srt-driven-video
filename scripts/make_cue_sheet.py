#!/usr/bin/env python3
"""make_cue_sheet.py — 把 assets/sfx/mix_timeline.json 导成剪辑软件手动对点用的纯文本清单
（mm:ss.mmm 时间码 + 素材 + 建议增益 + 画面说明），产出 output/sfx_cue_sheet.txt。

与 mix_sfx.py 共用同一份 mix_timeline.json 字段约定（expand / trim_sec / fade_out_sec /
normalize_first / video_duration_sec），零硬编码。

用法：python make_cue_sheet.py [project_dir]
"""
import json
import sys
from pathlib import Path


def tc(sec):
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sfx = proj / "assets" / "sfx"
    tl = json.loads((sfx / "mix_timeline.json").read_text(encoding="utf-8"))
    manifest_path = sfx / "manifest.json"
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else [])
    duration = tl.get("video_duration_sec", "?")

    lines = []
    lines.append(f"剪映音效对点清单（视频总时长 {duration}s）")
    lines.append("生成自 assets/sfx/mix_timeline.json + manifest.json")
    lines.append("用法：把素材拖到音效轨，按左侧时间码对齐素材起点；增益列为建议音量调整。")
    lines.append("")
    lines.append("=" * 76)
    lines.append("事件时间线（按时间先后；时间码 = 分:秒.毫秒）")
    lines.append("=" * 76)

    cur_group = ""
    for ev in tl["events"]:
        t = float(ev["time"]); f = ev["file"]; g = float(ev.get("gain_db", 0.0))
        note = ev.get("note", "")
        # 按 note 前缀（如 scene-NNN）分组加分隔线
        group = note.split(" ")[0] if note else ""
        if group and group != cur_group:
            cur_group = group
            lines.append("")
            lines.append(f"--- {group} " + "-" * max(4, 68 - len(group)))
        gain = f"{g:+.0f}dB" if g else "  0dB"
        exp = ev.get("expand")
        if exp:
            n, step = int(exp["count"]), float(exp["step"])
            end = t + (n - 1) * step
            lines.append(f"{tc(t)} ~ {tc(end)}  {f:<26} {gain}  {note}")
            lines.append(f"             └ 成组事件共 {n} 发，间隔 {step}s"
                         f"（剪辑软件里可复制粘贴后批量微调，或简化只留首尾 2~3 发）")
        else:
            lines.append(f"{tc(t)}  {f:<26} {gain}  {note}")
        if ev.get("trim_sec"):
            lines.append(f"             └ 素材需在 {tc(t + float(ev['trim_sec']))} 前截短至 "
                         f"{ev['trim_sec']}s 并淡出 {ev.get('fade_out_sec', 0.5)}s")

    if manifest:
        lines.append("")
        lines.append("=" * 76)
        lines.append(f"素材一览（{len(manifest)} 条）")
        lines.append("=" * 76)
        for m in manifest:
            extra = f"  fs:{m['freesound_id']}" if m.get("freesound_id") else ""
            lic = f"  [{m['license']}]" if m.get("license") else ""
            lines.append(f"{m['file']:<26} {m.get('duration_sec', '?'):>7}s{extra}{lic}  {m.get('cues', '')}")

    remarks = []
    nf = tl.get("normalize_first", {})
    if nf.get("file"):
        remarks.append(f"{nf['file']} 原始电平偏低，剪辑软件里请先拉高音量（目标 peak "
                       f"{nf.get('target_peak', 0.9)}）再按清单增益使用。")
    hi = [f"{tc(float(e['time']))} {e.get('note', '')}" for e in tl["events"]
          if float(e.get("gain_db", 0)) > 0]
    if hi:
        remarks.append("正增益（全片最重）音效位：" + "；".join(hi))
    if remarks:
        lines.append("")
        lines.append("备注：")
        lines += [f"{i}. {r}" for i, r in enumerate(remarks, 1)]

    out = proj / "output" / "sfx_cue_sheet.txt"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[Done] {out}  ({len(lines)} 行)")


if __name__ == "__main__":
    main()
