#!/usr/bin/env python3
"""并行 Range 下载（Zenodo 单连接慢时用）。用法: python parallel_dl.py URL OUT [THREADS]"""
import os, sys, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

url, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 16
r = requests.head(url, allow_redirects=True, timeout=60)
total = int(r.headers["content-length"])
chunk = 16 * 1024 * 1024
ranges = [(s, min(s + chunk, total) - 1) for s in range(0, total, chunk)]
with open(out, "wb") as f:
    f.truncate(total)


def dl(a, b):
    for _ in range(6):
        try:
            rr = requests.get(url, headers={"Range": f"bytes={a}-{b}"}, timeout=180)
            if rr.status_code in (200, 206) and len(rr.content) == b - a + 1:
                with open(out, "r+b") as fh:
                    fh.seek(a)
                    fh.write(rr.content)
                return b - a + 1
        except Exception:
            pass
    return 0


done = 0
with ThreadPoolExecutor(n) as ex:
    futs = {ex.submit(dl, a, b): (a, b) for a, b in ranges}
    for i, fut in enumerate(as_completed(futs), 1):
        done += fut.result()
        if i % 8 == 0 or i == len(futs):
            print(f"{done/1e9:.2f}/{total/1e9:.2f} GB ({i}/{len(futs)})", flush=True)
print("DONE", done, "of", total)
