#!/usr/bin/env python3
"""render_scene.py — Windows 适配版：Playwright 驱动 Edge + imageio-ffmpeg 合成

与原版契约一致：<scene_dir>/index.html 必须实现 window.setTime(tSeconds)。
差异：
- 浏览器用本机 Microsoft Edge（Chromium 内核），channel="msedge"
- FFmpeg 取自 imageio-ffmpeg 包内置二进制
"""
import argparse, subprocess, sys
from pathlib import Path

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("[Error] 缺少 imageio-ffmpeg：python -m pip install imageio-ffmpeg")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene_dir")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--output", default=None)
    ap.add_argument("--no-subtitle", action="store_true", help="隐藏烧录字幕层（#subtitle）")
    args = ap.parse_args()

    scene = Path(args.scene_dir).resolve()
    html = scene / "index.html"
    if not html.exists():
        sys.exit(f"[Error] 缺少 {html}")
    w, h = (int(x) for x in args.size.lower().split("x"))
    out = Path(args.output).resolve() if args.output else scene / "scene.mp4"
    frames = scene / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()

    n_frames = max(1, round(args.duration * args.fps))

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True,
                                    args=["--no-sandbox", "--disable-gpu", "--force-color-profile=srgb"])
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto(f"file:///{html.as_posix()}?w={w}&h={h}")
        page.wait_for_timeout(500)
        if args.no_subtitle:
            page.add_style_tag(content="#subtitle{display:none!important}")
        if not page.evaluate("typeof window.setTime === 'function'"):
            browser.close()
            sys.exit("[Error] index.html 未实现 window.setTime(t)")
        for i in range(n_frames):
            t = i / args.fps
            page.evaluate(f"window.setTime({t:.6f})")
            page.screenshot(path=str(frames / f"{i+1:05d}.png"))
            if (i + 1) % 30 == 0:
                print(f"[Render] {i+1}/{n_frames} 帧", flush=True)
        browser.close()

    ffmpeg = get_ffmpeg()
    cmd = [ffmpeg, "-y", "-framerate", str(args.fps), "-i", str(frames / "%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-vf", f"scale={w}:{h}:flags=lanczos", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        sys.exit(f"[Error] FFmpeg 合成失败:\n{r.stderr[-2000:]}")
    print(f"[Done] {out}  ({n_frames} 帧, {args.duration}s @ {args.fps}fps, {w}x{h})")

if __name__ == "__main__":
    main()
