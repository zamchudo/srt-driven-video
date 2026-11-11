#!/usr/bin/env python3
"""check_timeline.py — 分镜时间轴校验

用法:
    python3 check_timeline.py <project_dir>

校验规则（沿用 auto-motion 工程约束）:
    1. storyboard.json 中镜头按 start 排序后首尾相接（无重叠、无遗漏, 容差 0.05s）
    2. 时长之和 与 subtitles.srt 总跨度(末条结束 - 首条开始) 误差 ≤ 0.1s
    3. 每镜引用的 assets/ 路径存在
"""
import json, re, sys
from pathlib import Path

def parse_srt_span(srt_path: Path):
    text = srt_path.read_text(encoding="utf-8")
    times = re.findall(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", text)
    if not times:
        sys.exit(f"[Error] {srt_path} 中未找到字幕时间轴")
    def sec(h, m, s, ms): return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
    starts = [sec(*t[:4]) for t in times]
    ends = [sec(*t[4:]) for t in times]
    return min(starts), max(ends)

def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sb_path, srt_path = proj / "storyboard.json", proj / "subtitles.srt"
    scenes = json.loads(sb_path.read_text(encoding="utf-8"))["scenes"]
    scenes.sort(key=lambda s: s["start"])
    errors, tol = [], 0.05

    srt_start, srt_end = parse_srt_span(srt_path)
    if abs(scenes[0]["start"] - srt_start) > tol:
        errors.append(f"首镜 start={scenes[0]['start']} 与 SRT 起点 {srt_start:.3f} 不一致")
    if abs(scenes[-1]["end"] - srt_end) > tol:
        errors.append(f"末镜 end={scenes[-1]['end']} 与 SRT 终点 {srt_end:.3f} 不一致")
    for a, b in zip(scenes, scenes[1:]):
        if abs(a["end"] - b["start"]) > tol:
            errors.append(f"{a['id']} 与 {b['id']} 之间存在缝隙/重叠: {a['end']} -> {b['start']}")
    total = sum(s["duration_sec"] for s in scenes)
    span = srt_end - srt_start
    if abs(total - span) > 0.1:
        errors.append(f"镜头时长和 {total:.3f}s 与 SRT 跨度 {span:.3f}s 误差 {abs(total-span):.3f}s > 0.1s")
    for s in scenes:
        if abs((s["end"] - s["start"]) - s["duration_sec"]) > 0.01:
            errors.append(f"{s['id']} duration_sec={s['duration_sec']} 与 end-start={s['end']-s['start']:.3f} 不符")
        for asset in s.get("assets", []):
            if not (proj / asset).exists():
                errors.append(f"{s['id']} 引用素材不存在: {asset}")

    if errors:
        print("[FAIL] 时间轴校验未通过:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"[OK] {len(scenes)} 个镜头, 总时长 {total:.3f}s, 校验通过")

if __name__ == "__main__":
    main()
