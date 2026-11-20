#!/usr/bin/env python3
"""BW-DB 断点续传 watchdog：Zenodo 限流时等待，恢复后按 16MB 块补齐缺失块。
用法: python bwdb_watch.py URL OUT [THREADS] [MAX_HOURS]
"""
import os, sys, time, numpy as np, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

url, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
max_h = float(sys.argv[4]) if len(sys.argv) > 4 else 24.0
CH = 16 * 1024 * 1024
PROBE = {"Range": "bytes=0-1023", "User-Agent": "Mozilla/5.0"}


def log(msg):
    print(time.strftime("%m-%d %H:%M:%S"), msg, flush=True)


def probe():
    try:
        r = requests.get(url, headers=PROBE, timeout=45, allow_redirects=True)
        return r.status_code, len(r.content)
    except Exception as e:
        return "ERR", repr(e)[:60]


def scan(total):
    missing = []
    with open(out, "rb") as f:
        for s in range(0, total, CH):
            f.seek(s)
            buf = f.read(min(CH, total - s))
            if float(np.frombuffer(buf, dtype=np.uint8).__eq__(0).mean()) > 0.01:
                missing.append(s)
    return missing


def dl(s, total):
    b = min(s + CH, total) - 1
    for _ in range(4):
        try:
            rr = requests.get(url, headers={"Range": f"bytes={s}-{b}", "User-Agent": "Mozilla/5.0"},
                              timeout=300, allow_redirects=True)
            if rr.status_code in (200, 206) and len(rr.content) == b - s + 1:
                with open(out, "r+b") as fh:
                    fh.seek(s)
                    fh.write(rr.content)
                return b - s + 1
        except Exception:
            pass
        time.sleep(10)
    return 0


t0 = time.time()
while (time.time() - t0) / 3600 < max_h:
    code, size = probe()
    log(f"probe {code} ({size})")
    if code in (200, 206):
        break
    time.sleep(180)
else:
    log("give up: still blocked")
    sys.exit(1)

r = requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True, timeout=60)
total = int(r.headers["content-length"])
if not os.path.exists(out):
    with open(out, "wb") as f:
        f.truncate(total)
elif os.path.getsize(out) != total:
    with open(out, "r+b") as f:
        f.truncate(total)
log(f"total {total}")

for p in range(1, 21):
    missing = scan(total)
    log(f"pass {p}: missing {len(missing)} chunks (~{sum(min(CH, total-s) for s in missing)/1e9:.2f} GB)")
    if not missing:
        break
    done = ok = 0
    with ThreadPoolExecutor(n) as ex:
        futs = {ex.submit(dl, s, total): s for s in missing}
        for i, fut in enumerate(as_completed(futs), 1):
            got = fut.result()
            done += got
            ok += int(got > 0)
            if i % 8 == 0 or i == len(futs):
                log(f"  {done/1e9:.2f} GB ({i}/{len(futs)}, ok {ok})")
    if ok == 0:
        log("all failed this pass; sleeping 3 min")
        time.sleep(180)

missing = scan(total)
log(f"FINAL missing {len(missing)}")
if not missing:
    import subprocess
    log("gzip -t ...")
    rc = subprocess.run(["gzip", "-t", out]).returncode
    log(f"gzip test rc={rc}")
