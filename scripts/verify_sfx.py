#!/usr/bin/env python3
"""阶段 3c：FFmpeg 解码验证音效素材，输出时长/声道/采样率/电平。"""
import json, subprocess, sys
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SFX = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/sfx")

def probe(p: Path):
    # decode to raw f32le mono 22050 Hz and measure level
    cmd = [FFMPEG, "-v", "error", "-i", str(p), "-ac", "1", "-ar", "22050",
           "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None, r.stderr.decode(errors="replace")[:200]
    import struct
    n = len(r.stdout) // 4
    peak = 0.0
    vals = struct.unpack(f"<{n}f", r.stdout)
    peak = max(abs(v) for v in vals)
    return {"peak": round(peak, 4), "samples": n,
            "duration_sec": round(n / 22050.0, 3)}, None

files = sorted(SFX.glob("*.mp3"))
print(f"{len(files)} files")
for f in files:
    info, err = probe(f)
    if err:
        print(f"FAIL\t{f.name}\t{err}")
    else:
        print(f"OK\t{f.name}\t{info['duration_sec']}s\tpeak={info['peak']}\tn={info['samples']}")
