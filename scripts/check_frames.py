#!/usr/bin/env python3
"""check_frames.py — 阶段 3b 新增：抓取镜头指定时刻的关键帧并拼成一张对照图。

用法：
  python tools/check_frames.py scenes/scene-NNN --times 0.5,3,6,9.2 --size 960x540

产物：scenes/scene-NNN/keyframes.jpg（2 列拼图，附时刻标注）
只读镜头源码，不修改任何文件（临时帧放在系统临时目录）。
"""
import argparse, sys, tempfile
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene_dir")
    ap.add_argument("--times", required=True, help="逗号分隔的本地时刻（秒）")
    ap.add_argument("--size", default="960x540")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    scene = Path(args.scene_dir).resolve()
    html = scene / "index.html"
    if not html.exists():
        sys.exit(f"[Error] 缺少 {html}")
    w, h = (int(x) for x in args.size.lower().split("x"))
    times = [float(x) for x in args.times.split(",")]
    out = Path(args.out).resolve() if args.out else scene / "keyframes.jpg"

    from playwright.sync_api import sync_playwright
    tmp = Path(tempfile.mkdtemp(prefix="kf_"))
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True,
                                    args=["--no-sandbox", "--disable-gpu", "--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(f"file:///{html.as_posix()}?w={w}&h={h}")
        page.wait_for_timeout(500)
        if not page.evaluate("typeof window.setTime === 'function'"):
            browser.close()
            sys.exit("[Error] index.html 未实现 window.setTime(t)")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for i, t in enumerate(times):
            page.evaluate(f"window.setTime({t:.6f})")
            fp = tmp / f"{i:02d}_{t:.2f}.png"
            page.screenshot(path=str(fp))
            shots.append((t, fp))
        browser.close()
    if errors:
        print(f"[Warn] 页面脚本错误: {errors[:3]}")

    from PIL import Image, ImageDraw
    cols = 2
    rows = (len(shots) + 1) // 2
    label_h = 34
    canvas = Image.new("RGB", (w * cols, (h + label_h) * rows), (10, 12, 20))
    draw = ImageDraw.Draw(canvas)
    for i, (t, fp) in enumerate(shots):
        im = Image.open(fp).convert("RGB")
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        canvas.paste(im, (x, y + label_h))
        draw.text((x + 10, y + 6), f"t = {t:.2f}s", fill=(0, 229, 255))
    canvas.save(out, quality=88)
    print(f"[Done] {out}")

if __name__ == "__main__":
    main()
