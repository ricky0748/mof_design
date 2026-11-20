#!/usr/bin/env python3
"""用 Zeo++ 计算与 CRAFTED 同口径的几何特征（G 组）。

口径由 ABUWOJ 反校准确定：-ha -res；-sa/-vol 均为 1.4 Å 探针、20000 采样。
在该口径下 D_is/D_fs/D_isfs、ASA_m^2/cm^3、ASA_m^2/g 与 CRAFTED CSV 精确一致；
AV 有约 1.5% 的版本差异。为提高与训练标签的一致性，建议用本脚本重算 CRAFTED 的 G 组。

用法:
  python3 zeo_features.py --list list.csv --out out.csv --network /path/to/network [--workers 32]
  list.csv 两列: name,cif
输出列: name + D_is D_fs D_isfs ASA_A2 ASA_m2_cm3 ASA_m2_g NASA_A2 NASA_m2_cm3 NASA_m2_g
        Unitcell_volume Density AV_A3 AV_Volume_fraction AV_cm3_g NAV_A3 NAV_Volume_fraction
        NAV_cm3_g n_channels n_pockets
"""
import argparse, csv, os, re, subprocess, tempfile, shutil
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

NUM = r"([-+0-9.eE]+)"
PAT_SA = {
    "Unitcell_volume": r"Unitcell_volume:\s*" + NUM,
    "Density": r"Density:\s*" + NUM,
    "ASA_A2": r"ASA_A\^2:\s*" + NUM,
    "ASA_m2_cm3": r"ASA_m\^2/cm\^3:\s*" + NUM,
    "ASA_m2_g": r"ASA_m\^2/g:\s*" + NUM,
    "NASA_A2": r"NASA_A\^2:\s*" + NUM,
    "NASA_m2_cm3": r"NASA_m\^2/cm\^3:\s*" + NUM,
    "NASA_m2_g": r"NASA_m\^2/g:\s*" + NUM,
}
PAT_VOL = {
    "AV_A3": r"AV_A\^3:\s*" + NUM,
    "AV_Volume_fraction": r"AV_Volume_fraction:\s*" + NUM,
    "AV_cm3_g": r"AV_cm\^3/g:\s*" + NUM,
    "NAV_A3": r"NAV_A\^3:\s*" + NUM,
    "NAV_Volume_fraction": r"NAV_Volume_fraction:\s*" + NUM,
    "NAV_cm3_g": r"NAV_cm\^3/g:\s*" + NUM,
}


def parse_sa(path):
    t = open(path).read()
    d = {}
    for k, p in PAT_SA.items():
        m = re.search(p, t)
        d[k] = float(m.group(1)) if m else None
    m = re.search(r"Number_of_channels:\s*(\d+)", t); d["n_channels"] = int(m.group(1)) if m else None
    m = re.search(r"Number_of_pockets:\s*(\d+)", t); d["n_pockets"] = int(m.group(1)) if m else None
    return d


def parse_vol(path):
    t = open(path).read()
    d = {}
    for k, p in PAT_VOL.items():
        m = re.search(p, t)
        d[k] = float(m.group(1)) if m else None
    return d


def one(job):
    name, cif, network, timeout = job
    tmp = tempfile.mkdtemp(prefix="zeo_", dir="/tmp")
    try:
        res, sa, vol = [os.path.join(tmp, x) for x in ("o.res", "o.sa", "o.vol")]
        cmd = [network, "-ha", "-res", res,
               "-sa", "1.4", "1.4", "20000", sa,
               "-vol", "1.4", "1.4", "20000", vol, cif]
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        if r.returncode != 0 or not os.path.exists(res):
            return dict(name=name, error=f"exit {r.returncode}")
        p = open(res).read().split()
        d = dict(name=name, D_is=float(p[1]), D_fs=float(p[2]), D_isfs=float(p[3]))
        d.update(parse_sa(sa)); d.update(parse_vol(vol))
        return d
    except subprocess.TimeoutExpired:
        return dict(name=name, error="timeout")
    except Exception as e:
        return dict(name=name, error=repr(e)[:120])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--network", default="/share/rickyswork/ai_mof/zeoplusplus/network")
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    jobs = [(r["name"], r["cif"], a.network, a.timeout) for r in csv.DictReader(open(a.list))]
    rows = []
    with ThreadPoolExecutor(a.workers) as ex:
        for i, d in enumerate(ex.map(one, jobs), 1):
            rows.append(d)
            if i % 25 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(a.out, index=False)
    bad = R[R.get("error").notna()] if "error" in R else R.iloc[:0]
    print(f"done: {len(R)} rows, {len(bad)} errors -> {a.out}")
    if len(bad):
        print(bad[["name", "error"]].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
