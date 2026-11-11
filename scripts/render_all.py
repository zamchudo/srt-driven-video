#!/usr/bin/env python3
"""render_all.py — 批量渲染全部镜头（读取 storyboard.json 的时长），支持变体输出。

用法（在项目根目录执行）：
  python <skill>/scripts/render_all.py .                        # 全量渲染到 scenes/<id>/scene.mp4
  python <skill>/scripts/render_all.py . scene-003 scene-005    # 只渲染指定镜头
  python <skill>/scripts/render_all.py . --no-subtitle --outdir output/nosub
      # 无字幕变体：隐藏 #subtitle 层，输出到 output/nosub/scene-NNN.mp4，不动 scenes/
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("scenes", nargs="*", help="只渲染这些镜头（默认全部）")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--no-subtitle", action="store_true", help="隐藏烧录字幕层（#subtitle）")
    ap.add_argument("--outdir", default=None, help="变体输出目录（默认写回 scenes/<id>/scene.mp4）")
    args = ap.parse_args()

    proj = Path(args.project_dir).resolve()
    sb = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))["scenes"]
    sb.sort(key=lambda s: s["start"])
    only = set(args.scenes)

    outdir = Path(args.outdir).resolve() if args.outdir else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)

    renderer = Path(__file__).resolve().parent / "render_scene.py"
    failed = []
    for s in sb:
        name = s["id"]
        if only and name not in only:
            continue
        dur = s["duration_sec"]
        out = (outdir / f"{name}.mp4") if outdir else (proj / "scenes" / name / "scene.mp4")
        t0 = time.time()
        print(f"[render] {name} duration={dur}s -> {out}", flush=True)
        cmd = [sys.executable, str(renderer), str(proj / "scenes" / name),
               "--duration", str(dur), "--fps", str(args.fps), "--size", args.size,
               "--output", str(out)]
        if args.no_subtitle:
            cmd.append("--no-subtitle")
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        cost = time.time() - t0
        if r.returncode != 0:
            failed.append(name)
            print(f"[FAIL] {name} ({cost:.0f}s)\n{r.stdout}\n{r.stderr}", flush=True)
        else:
            print(f"[ok] {name} ({cost:.0f}s)", flush=True)
    print("FAILED:", failed if failed else "none", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
