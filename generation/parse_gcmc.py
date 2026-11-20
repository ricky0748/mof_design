#!/usr/bin/env python3
"""解析 SiH4/CO2 混合 GCMC 输出，计算 1000 ppm 条件下的 S_CO2。

用法: python3 parse_gcmc.py <gcmc_runs目录> [--out gcmc_results.csv]
"""
import argparse, glob, os, re
import pandas as pd

PAT = re.compile(r"Average loading absolute \[mol/kg framework\]\s+([-+0-9.eE]+)\s+\+/-\s+([-+0-9.eE]+)")
Y_CO2, Y_SIH4 = 0.001, 0.999


def one(d):
    fs = glob.glob(os.path.join(d, "Output", "System_0", "*.data"))
    if not fs:
        return dict(mof=os.path.basename(os.path.dirname(d)), status="missing")
    t = open(fs[0], errors="ignore").read()
    if "Simulation finished" not in t:
        return dict(mof=os.path.basename(os.path.dirname(d)), status="unfinished")
    # 按 component 段落切
    secs = re.split(r"Component\s+(\d+)\s+\[([^\]]+)\]", t)
    vals = {}
    for i in range(1, len(secs), 3):
        name = secs[i + 1]
        m = PAT.search(secs[i + 2])
        if m:
            vals[name] = (float(m.group(1)), float(m.group(2)))
    qs = vals.get("SiH4"); qc = vals.get("CO2")
    if not qs or not qc:
        return dict(mof=os.path.basename(os.path.dirname(d)), status="parse_fail", keys=str(list(vals)))
    if qs[0] <= 0:
        S = float("nan")
        logS = float("nan")
    elif qc[0] <= 0:
        S = 0.0
        logS = float("-inf")
    else:
        S = (qc[0] / qs[0]) / (Y_CO2 / Y_SIH4)
        logS = float(__import__("math").log10(S))
    return dict(mof=os.path.basename(os.path.dirname(d)), status="ok",
                q_SiH4=qs[0], q_SiH4_err=qs[1], q_CO2=qc[0], q_CO2_err=qc[1],
                S_CO2=S, logS_CO2=logS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--out", default="gcmc_results.csv")
    a = ap.parse_args()
    rows = [one(d) for d in sorted(glob.glob(os.path.join(a.runs, "*", "gcmc")))]
    R = pd.DataFrame(rows); R.to_csv(a.out, index=False)
    print(f"{len(R)} 个 -> {a.out}")
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
