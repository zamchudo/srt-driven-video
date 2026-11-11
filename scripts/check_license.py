#!/usr/bin/env python3
"""阶段 3c：逐条抓取 Freesound 声音页面，核对许可声明为 CC0。"""
import re, sys, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) sfx-license-check"}

ids = sys.argv[1:]
for sid in ids:
    url = f"https://freesound.org/sounds/{sid}/"
    try:
        import json
        from pathlib import Path
        idx = json.loads((Path.home() / ".cache" / "sfx-sources" / "index.json").read_text(encoding="utf-8"))
        author = idx[f"fs:{sid}"]["author"]
        url = f"https://freesound.org/people/{author}/sounds/{sid}/"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            html = r.read().decode("utf-8", errors="replace")
        if "creativecommons.org/publicdomain/zero/1.0/" in html or 'class="bw-icon-zero"' in html:
            lic = "Creative Commons 0 (CC0)"
        else:
            m = re.search(r'title="License: ([^"]+)"', html)
            lic = ("NON-CC0: " + m.group(1)) if m else "NOT FOUND"
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        t = title.group(1).strip().replace("\n", " ")[:60] if title else "?"
        ok = "creative commons 0" in lic.lower()
        print(f"{'OK ' if ok else 'BAD'} fs:{sid}\t{lic}\t{t}")
    except Exception as e:
        print(f"ERR fs:{sid}\t{e!r}")
