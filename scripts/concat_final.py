#!/usr/bin/env python3
"""concat_final.py — Windows 适配版：拼接 + 规范化 + BGM + 封面

差异：ffprobe 用 ffmpeg -i 的 stderr 输出解析替代（imageio-ffmpeg 不含 ffprobe）。
BGM 可选；本视频项目默认无 BGM（真人现场讲解）。
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

W, H, FPS = 1920, 1080, 30

def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("[Error] 缺少 imageio-ffmpeg")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        sys.exit(f"[Error] 命令失败: {' '.join(str(c) for c in cmd)}\n{r.stderr[-2000:]}")
    return r

def probe(ffmpeg, path):
    """用 ffmpeg -i 的 stderr 解析 宽/高/fps/像素格式"""
    r = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    info = r.stderr
    m = re.search(r"Video:\s+\S+\s+\(([^)]*)\)\s*,?\s*(\w+)?,?\s*(\d{2,5})x(\d{2,5})", info)
    if not m:
        m2 = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", info)
        if not m2:
            sys.exit(f"[Error] 无法解析视频流信息: {path}")
        w, h = int(m2.group(1)), int(m2.group(2))
        pix = "yuv420p" if "yuv420p" in info else "unknown"
    else:
        pix = m.group(2) or ("yuv420p" if "yuv420p" in info else "unknown")
        w, h = int(m.group(3)), int(m.group(4))
    fps_m = re.search(r"(\d+(?:\.\d+)?)\s*fps", info)
    fps = float(fps_m.group(1)) if fps_m else 0.0
    return w, h, fps, pix

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--bgm", default=None)
    ap.add_argument("--bgm-volume", type=float, default=-18)
    ap.add_argument("--sfx", default=None, help="预混音效轨（如 output/sfx_mix.wav），等长叠加，不循环")
    ap.add_argument("--cover-time", type=float, default=1.0, help="封面取帧时刻（秒）")
    args = ap.parse_args()
    ffmpeg = get_ffmpeg()
    proj = Path(args.project_dir).resolve()
    out_dir = proj / "output"
    out_dir.mkdir(exist_ok=True)

    scenes = json.loads((proj / "storyboard.json").read_text(encoding="utf-8"))["scenes"]
    scenes.sort(key=lambda s: s["start"])
    normalized = []
    for s in scenes:
        mp4 = proj / "scenes" / s["id"] / "scene.mp4"
        if not mp4.exists():
            sys.exit(f"[Error] 缺少镜头成片: {mp4}")
        w, h, fps, pix = probe(ffmpeg, mp4)
        if (w, h, round(fps), pix) != (W, H, FPS, "yuv420p"):
            norm = mp4.with_name("scene_norm.mp4")
            print(f"[Norm] {s['id']} 规格不一致({w}x{h}@{fps:.2f} {pix}), 转码规范化")
            run([ffmpeg, "-y", "-i", str(mp4), "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(norm)])
            mp4 = norm
        normalized.append(mp4)

    lst = out_dir / "concat.txt"
    lst.write_text("".join(f"file '{m.as_posix()}'\n" for m in normalized), encoding="utf-8")
    video_only = out_dir / "video_only.mp4"
    run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(video_only)])

    final = out_dir / "final.mp4"
    if args.bgm:
        bgm = str((proj / args.bgm).resolve())
        dur_r = subprocess.run([ffmpeg, "-i", str(video_only)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
        dur_m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", dur_r.stderr)
        dur = int(dur_m.group(1))*3600 + int(dur_m.group(2))*60 + float(dur_m.group(3)) if dur_m else 0
        fade_start = max(0.0, dur - 2.0)
        vol = 10 ** (args.bgm_volume / 20)
        run([ffmpeg, "-y", "-i", str(video_only), "-stream_loop", "-1", "-i", bgm,
             "-filter_complex",
             f"[1:a]volume={vol:.4f},afade=t=out:st={fade_start:.3f}:d=2[music]",
             "-map", "0:v", "-map", "[music]", "-c:v", "copy", "-c:a", "aac",
             "-shortest", str(final)])
    elif args.sfx:
        sfx = str((proj / args.sfx).resolve())
        run([ffmpeg, "-y", "-i", str(video_only), "-i", sfx,
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", str(final)])
    else:
        video_only.replace(final)

    run([ffmpeg, "-y", "-ss", f"{args.cover_time:.3f}", "-i", str(final), "-frames:v", "1",
         str(out_dir / "cover.png")])
    print(f"[Done] {final}")

if __name__ == "__main__":
    main()
