#!/usr/bin/env python3
"""为同预算对照的 known_holdout / generated 两臂构建 SiH4/CO2 GCMC 输入。

已知库用 CRAFTED PACMOF CIF（<mof>.cif）；生成臂用 generation/pacmof_cif（<mof>_charged.cif）。
超胞按 2×12.8 Å 最小盒宽从 CIF 晶胞计算。
"""
import argparse, csv, math, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_gcmc_inputs import write_input


def cif_info(path):
    t = [l.strip() for l in open(path, errors="ignore").read().splitlines()]
    def g(k):
        m = re.search(r"^_cell_" + k + r"\s+([-0-9.]+)", "\n".join(t), re.M)
        return float(m.group(1)) if m else None
    lengths = [g("length_a"), g("length_b"), g("length_c")]
    i = t.index("_atom_site_label"); j = i + 1
    while j < len(t) and (t[j].startswith("_") or t[j].strip() == ""):
        j += 1
    n = 0
    while j < len(t) and not t[j].startswith("_") and not t[j].startswith("#"):
        if len(t[j].split()) >= 2:
            n += 1
        j += 1
    return lengths, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", required=True)
    ap.add_argument("--crafted-pacmof", required=True)
    ap.add_argument("--gen-pacmof", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ff-dir", default=os.path.join(HERE, "..", "widom_sih4"))
    ap.add_argument("--cycles", type=int, default=30000)
    ap.add_argument("--init", type=int, default=5000)
    a = ap.parse_args()
    rows = []
    for r in csv.DictReader(open(a.selected)):
        mof, arm = r["mof"], r["arm"]
        cif = os.path.join(a.crafted_pacmof, mof + ".cif") if arm.startswith("known") \
            else os.path.join(a.gen_pacmof, mof + "_charged.cif")
        lengths, n = cif_info(cif)
        uc = tuple(max(1, math.ceil(26.0 / x)) for x in lengths)
        dst = os.path.join(a.out, mof, "gcmc"); os.makedirs(dst, exist_ok=True)
        shutil.copy(cif, os.path.join(dst, mof + ".cif"))
        for sub in ("ff", "molecules"):
            for f in os.listdir(os.path.join(a.ff_dir, sub)):
                shutil.copy(os.path.join(a.ff_dir, sub, f), dst)
        write_input(os.path.join(dst, "simulation.input"), mof, uc, a.cycles, a.init)
        rows.append((mof, "%dx%dx%d" % uc, n * uc[0] * uc[1] * uc[2]))
    with open(os.path.join(a.out, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["mof", "unit_cells", "atoms_in_supercell"]); w.writerows(rows)
    print(f"{len(rows)} -> {a.out}")
    print("atoms:", min(r[2] for r in rows), "-", max(r[2] for r in rows))


if __name__ == "__main__":
    main()
