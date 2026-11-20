#!/usr/bin/env python3
"""汇总 Widom 结果 -> henry_long.csv（逐 MOF × 分子）和 henry_wide.csv（逐 MOF，一行）。

用法: python3 parse_widom.py <runs目录> [--out 目录]
提取：Henry 常数 K (mol/kg/Pa) 及误差、吸附能 <U_gh>-<U_h> (kJ/mol) 及误差、Widom Rosenbluth 权重。
状态列 status：ok / missing（无输出）/ unfinished（输出不完整）/ timeout。
"""
import argparse, csv, glob, os, re

PAT_K = re.compile(r"\[(\S+)\] Average Henry coefficient:\s+([-+0-9.eE]+) \+/- ([-+0-9.eE]+)")
PAT_U = re.compile(r"\[(\S+)\] Average  <U_gh>_1-<U_h>_0:.*\(\s*([-+0-9.eE]+) \+/-\s+([-+0-9.eE]+) kJ/mol\)")
PAT_W = re.compile(r"\[(\S+)\] Average Widom Rosenbluth-weight:\s+([-+0-9.eE]+) \+/- ([-+0-9.eE]+)")


def parse_dir(d):
    if os.path.exists(os.path.join(d, "TIMEOUT")):
        return "timeout", {}
    fs = glob.glob(os.path.join(d, "Output", "System_0", "*.data"))
    if not fs:
        return "missing", {}
    txt = open(fs[0], errors="ignore").read()
    if "Simulation finished" not in txt:
        return "unfinished", {}
    res = {}
    for m in PAT_K.finditer(txt):
        res.setdefault(m.group(1), {}).update(K=float(m.group(2)), K_err=float(m.group(3)))
    for m in PAT_U.finditer(txt):
        res.setdefault(m.group(1), {}).update(U=float(m.group(2)), U_err=float(m.group(3)))
    for m in PAT_W.finditer(txt):
        res.setdefault(m.group(1), {}).update(W=float(m.group(2)), W_err=float(m.group(3)))
    return "ok", res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs"); ap.add_argument("--out", default=".")
    a = ap.parse_args()
    jobs = list(csv.DictReader(open(os.path.join(a.runs, "jobs.csv"))))
    long_rows, wide = [], {}
    for j in jobs:
        m = j["mof"]; wide[m] = {"mof": m}
        for g in ("np", "pol"):
            st, res = parse_dir(os.path.join(a.runs, m, g))
            wide[m][f"status_{g}"] = st
            for mol, v in res.items():
                long_rows.append(dict(mof=m, group=g, molecule=mol, **v))
                wide[m][f"K_{mol}"] = v.get("K"); wide[m][f"Kerr_{mol}"] = v.get("K_err"); wide[m][f"U_{mol}"] = v.get("U")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "henry_long.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mof", "group", "molecule", "K", "K_err", "U", "U_err", "W", "W_err"])
        w.writeheader(); w.writerows(long_rows)
    cols = sorted({k for r in wide.values() for k in r}, key=lambda k: (k != "mof", not k.startswith("status"), k))
    with open(os.path.join(a.out, "henry_wide.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(wide.values())
    n_ok = sum(1 for r in wide.values() if r.get("status_np") == "ok" and r.get("status_pol") == "ok")
    print(f"{len(wide)} 个 MOF，两组都完成 {n_ok} 个 -> {a.out}/henry_*.csv")


if __name__ == "__main__":
    main()
