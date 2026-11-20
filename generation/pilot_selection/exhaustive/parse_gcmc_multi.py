#!/usr/bin/env python3
"""解析多组分 GCMC 输出：<runs>/<条件>/<mof>/gcmc/Output/System_0/*.data"""
import argparse, glob, math, os, re
import pandas as pd

PAT = re.compile(r"Average loading absolute \[mol/kg framework\]\s+([-+0-9.eE]+)\s+\+/-\s+([-+0-9.eE]+)")


def comps_from_input(path):
    t = open(path).read()
    return {m.group(1): float(m.group(2)) for m in
            re.finditer(r"MoleculeName\s+(\S+)\s*\n\s*MolFraction\s+([0-9.]+)", t)}


def one(cond, d):
    fs = glob.glob(os.path.join(d, "gcmc", "Output", "System_0", "*.data"))
    mof = os.path.basename(d)
    if not fs:
        return dict(cond=cond, mof=mof, status="missing")
    t = open(fs[0], errors="ignore").read()
    if "Simulation finished" not in t:
        return dict(cond=cond, mof=mof, status="unfinished")
    secs = re.split(r"Component\s+\d+\s+\[([^\]]+)\]", t)
    vals = {}
    for i in range(1, len(secs), 2):
        m = PAT.search(secs[i + 1])
        if m:
            vals[secs[i]] = float(m.group(1))
    y = comps_from_input(os.path.join(d, "gcmc", "simulation.input"))
    if "SiH4" not in vals or "SiH4" not in y:
        return dict(cond=cond, mof=mof, status="parse_fail", keys=str(list(vals)))
    row = dict(cond=cond, mof=mof, status="ok")
    for c in ("SiH4", "CO2", "N2", "CH4"):
        if c in vals:
            row["q_" + c] = vals[c]
            S = (vals[c] / vals["SiH4"]) / (y[c] / y["SiH4"])
            row["S_" + c] = S
            if c == "CO2":
                row["logS_CO2"] = math.log10(S)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs")
    ap.add_argument("--out", default="multicomponent_results.csv")
    a = ap.parse_args()
    rows = []
    for d in sorted(glob.glob(os.path.join(a.runs, "*", "*"))):
        if os.path.isdir(os.path.join(d, "gcmc")):
            rows.append(one(os.path.basename(os.path.dirname(d)), d))
    R = pd.DataFrame(rows); R.to_csv(a.out, index=False)
    print(f"{len(R)} -> {a.out}")
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
