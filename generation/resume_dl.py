#!/usr/bin/env python3
"""断点续传：扫描已下载文件中全零的 16MB 块，只重下缺失块。
用法: python resume_dl.py URL OUT [THREADS]
"""
import os, sys, numpy as np, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

url, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 16
CH = 16 * 1024 * 1024

r = requests.head(url, allow_redirects=True, timeout=60)
total = int(r.headers["content-length"])
print(f"total {total} bytes", flush=True)

if not os.path.exists(out):
    with open(out, "wb") as f:
        f.truncate(total)
elif os.path.getsize(out) != total:
    with open(out, "r+b") as f:
        f.truncate(total)

starts = list(range(0, total, CH))
missing = []
with open(out, "rb") as f:
    for s in starts:
        f.seek(s)
        buf = f.read(min(CH, total - s))
        zf = float(np.frombuffer(buf, dtype=np.uint8).__eq__(0).mean())
        # 压缩流里零字节约 0.4%；>1% 视为缺失/半写
        if zf > 0.01:
            missing.append(s)
print(f"chunks {len(starts)}, missing {len(missing)}, have {len(starts)-len(missing)}", flush=True)
print(f"missing bytes ~{sum(min(CH, total-s) for s in missing)/1e9:.2f} GB", flush=True)


def dl(s):
    b = min(s + CH, total) - 1
    for _ in range(8):
        try:
            rr = requests.get(url, headers={"Range": f"bytes={s}-{b}"}, timeout=300)
            if rr.status_code in (200, 206) and len(rr.content) == b - s + 1:
                with open(out, "r+b") as fh:
                    fh.seek(s)
                    fh.write(rr.content)
                return b - s + 1
        except Exception:
            pass
    return 0

done = 0
ok = 0
with ThreadPoolExecutor(n) as ex:
    futs = {ex.submit(dl, s): s for s in missing}
    for i, fut in enumerate(as_completed(futs), 1):
        got = fut.result()
        done += got
        ok += int(got > 0)
        if i % 8 == 0 or i == len(futs):
            print(f"{done/1e9:.2f} GB 已补 ({i}/{len(futs)} 块, 成功 {ok})", flush=True)
print("DONE", done, "bytes", flush=True)
