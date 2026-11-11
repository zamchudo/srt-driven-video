#!/usr/bin/env python3
"""mix_sfx.py — 音效混音：按 assets/sfx/mix_timeline.json 全局时间轴，
用 FFmpeg adelay + amix 一次性叠加全部音效事件，产出 output/sfx_mix.wav。

mix_timeline.json 全部字段（脚本零硬编码，一切由 JSON 驱动）：
{
  "video_duration_sec": 187.5,                       // 必填：混音输出时长
  "normalize_first": {"file": "xxx.mp3", "target_peak": 0.9},   // 可选：先归一化的素材
  "events": [
    {"time": 10.5, "file": "whoosh.mp3", "gain_db": 0.0, "note": "转场"},
    {"time": 37.35, "file": "tick.mp3", "gain_db": -2.0,
     "expand": {"count": 12, "step": 0.13},          // 可选：成组事件展开（time + i*step）
     "note": "逐字 tick"},
    {"time": 185.75, "file": "ending.mp3", "gain_db": -2.0,
     "trim_sec": 1.75, "fade_out_sec": 0.5,          // 可选：截断 + 末尾淡出
     "note": "尾音"}
  ]
}

输出端固定 alimiter=limit=0.891:level=0（-1dB 安全限幅，防多事件叠加削波；
level=0 必须显式，否则限幅后自动回补增益）。

用法：python mix_sfx.py [project_dir]
"""
import json, math, re, subprocess, sys
from pathlib import Path

SAMPLE_RATE = 48000
LIMITER = "alimiter=limit=0.891:level=0"   # -1dB 安全限幅（不改变各事件相对增益）


def get_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("[Error] 缺少 imageio-ffmpeg")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        sys.exit(f"[Error] 命令失败: {cmd[0]} ...\n{r.stderr[-2000:]}")
    return r


def detect_max_volume_db(ffmpeg, path):
    """volumedetect 取峰值电平（dBFS）"""
    r = subprocess.run([ffmpeg, "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    m = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
    if not m:
        sys.exit(f"[Error] 无法解析 max_volume: {path}")
    return float(m.group(1))


def expand_events(timeline):
    """展开成组事件（expand.count × expand.step），返回扁平事件列表"""
    events = []
    for ev in timeline["events"]:
        t = round(float(ev["time"]), 3)
        base = {"file": ev["file"], "gain_db": float(ev.get("gain_db", 0.0)),
                "trim_sec": ev.get("trim_sec"), "fade_out_sec": ev.get("fade_out_sec", 0.5)}
        exp = ev.get("expand")
        if exp:
            n, step = int(exp["count"]), float(exp["step"])
            for i in range(n):
                events.append({**base, "time": round(t + i * step, 3),
                               "note": f"{ev.get('note', '')} · {i+1}/{n}"})
        else:
            events.append({**base, "time": t, "note": ev.get("note", "")})
    return events


def main():
    proj = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sfx_dir = proj / "assets" / "sfx"
    out_dir = proj / "output"
    out_dir.mkdir(exist_ok=True)
    ffmpeg = get_ffmpeg()

    timeline = json.loads((sfx_dir / "mix_timeline.json").read_text(encoding="utf-8"))
    duration = float(timeline["video_duration_sec"])
    manifest_path = sfx_dir / "manifest.json"
    manifest = ({m["file"]: m for m in json.loads(manifest_path.read_text(encoding="utf-8"))}
                if manifest_path.exists() else {})

    events = expand_events(timeline)
    print(f"[Mix] 时间线事件 {len(timeline['events'])} 个 -> 展开后 {len(events)} 个")

    # 归一化（normalize_first）：素材级增益，叠加到每个引用该素材的事件上
    norm_gain_db = {}
    nf = timeline.get("normalize_first", {})
    if nf.get("file"):
        peak_db = detect_max_volume_db(ffmpeg, sfx_dir / nf["file"])
        target = float(nf.get("target_peak", 0.9))
        target_db = 20 * math.log10(target)
        norm_gain_db[nf["file"]] = target_db - peak_db
        print(f"[Norm] {nf['file']}: 实测 peak {peak_db:.2f} dB -> 增益 {norm_gain_db[nf['file']]:+.2f} dB 至 peak {target}")

    # 构建 filter_complex：每事件一路 输入 -> 截断/淡出 -> volume -> adelay
    inputs, chains, labels = [], [], []
    for i, ev in enumerate(events):
        f = ev["file"]
        path = sfx_dir / f
        if not path.exists():
            sys.exit(f"[Error] 缺少素材: {path}")
        if manifest and f not in manifest:
            print(f"[Warn] {f} 不在 manifest.json 中")
        inputs += ["-i", str(path)]

        gain_db = ev["gain_db"] + norm_gain_db.get(f, 0.0)
        chain = f"[{i}:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=stereo"
        if ev["trim_sec"]:
            trim = float(ev["trim_sec"])
            fade = float(ev["fade_out_sec"])
            chain += f",atrim=0:{trim},afade=t=out:st={trim - fade}:d={fade}"
        chain += f",volume={10 ** (gain_db / 20):.6f}"
        delay_ms = int(round(ev["time"] * 1000))
        chain += f",adelay={delay_ms}|{delay_ms}[a{i}]"
        chains.append(chain)
        labels.append(f"[a{i}]")

    chains.append("".join(labels) +
                  f"amix=inputs={len(events)}:normalize=0"
                  f",{LIMITER}"
                  f",atrim=0:{duration},asetpts=PTS-STARTPTS[out]")
    filter_str = ";\n".join(chains)
    (out_dir / "mix_filter.txt").write_text(filter_str, encoding="utf-8")  # 留档备查

    out_wav = out_dir / "sfx_mix.wav"
    run([ffmpeg, "-y", *inputs,
         "-filter_complex", filter_str,
         "-map", "[out]", "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), str(out_wav)])
    print(f"[Done] {out_wav}  ({len(events)} 事件叠加, {duration}s)")

    # 质检：时长 + 峰值
    r = subprocess.run([ffmpeg, "-i", str(out_wav), "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    dur_m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    dur = int(dur_m.group(1)) * 3600 + int(dur_m.group(2)) * 60 + float(dur_m.group(3)) if dur_m else -1
    peak_m = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
    mean_m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", r.stderr)
    print(f"[QC] sfx_mix.wav 时长 {dur:.3f}s | max_volume {peak_m.group(1) if peak_m else '?'} dB | "
          f"mean_volume {mean_m.group(1) if mean_m else '?'} dB")
    if abs(dur - duration) > 0.1:
        sys.exit(f"[Error] 混音时长 {dur:.3f}s 偏离 {duration}s")
    if peak_m and float(peak_m.group(1)) > 0.0:
        print(f"[Warn] 混音峰值 {peak_m.group(1)} dB 超过 0 dBFS，存在削波风险")


if __name__ == "__main__":
    main()
