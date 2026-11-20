#!/usr/bin/env python3
"""汇总 MOFDiff UFF 弛豫结果：抽取 JSON、约化到原胞、计算重叠/片段/体积变化。

用法: python uff_summary.py --uff-dir <plausibility/uff> --orig-dir <pilot100> --out-cif <uff/prim> --out-csv <uff/uff_summary.csv>
"""
import argparse
import csv
import glob
import json
import os

import numpy as np
from ase.io import read
from ase.neighborlist import natural_cutoffs, NeighborList
from pymatgen.io.cif import CifParser, CifWriter


def read_json_line(path):
    for line in open(path, errors="ignore"):
        i = line.find('{"cif"')
        if i >= 0:
            try:
                return json.loads(line[i:])
            except json.JSONDecodeError:
                pass
    return None


def fragments(atoms):
    cut = natural_cutoffs(atoms, mult=1.15)
    nl = NeighborList(cut, self_interaction=False, bothways=True)
    nl.update(atoms)
    m = nl.get_connectivity_matrix(sparse=True).tocsr()
    from scipy.sparse.csgraph import connected_components
    n, lab = connected_components(m, directed=False)
    sizes = sorted(np.bincount(lab).tolist(), reverse=True)
    return int(n), sizes


def metrics(atoms):
    d = atoms.get_all_distances(mic=True)
    np.fill_diagonal(d, np.inf)
    tri = np.triu(np.ones_like(d, dtype=bool), 1)
    return float(d[tri].min()), int((d[tri] < 0.9).sum()), int((d[tri] < 1.2).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uff-dir", required=True)
    ap.add_argument("--orig-dir", required=True)
    ap.add_argument("--out-cif", required=True)
    ap.add_argument("--out-csv", required=True)
    a = ap.parse_args()
    os.makedirs(a.out_cif, exist_ok=True)

    rows = []
    for jf in sorted(glob.glob(os.path.join(a.uff_dir, "relaxed", "*.json"))):
        name = os.path.basename(jf)[:-5]
        rec = read_json_line(jf) or dict(uid=name, ok=False, error="no JSON line")
        r = dict(name=name, uff_ok=bool(rec.get("ok")), error=rec.get("error", ""),
                 seconds=rec.get("seconds"), natoms_uff=rec.get("natoms"),
                 dmin_uff=rec.get("dmin"), pairs_lt_09_uff=rec.get("pairs_lt_0p9"))
        cif_out = os.path.join(a.out_cif, name + ".cif")
        try:
            orig = read(os.path.join(a.orig_dir, name + ".cif"))
            r["natoms_orig"] = len(orig)
            r["V_orig"] = round(float(orig.get_volume()), 1)
        except Exception as e:  # noqa
            r["natoms_orig"] = None
            r["V_orig"] = None
            r["error"] = (r["error"] + " | orig:" + str(e))[:160]

        if r["uff_ok"]:
            try:
                s = CifParser(os.path.join(a.uff_dir, "relaxed", name + "_uff.cif"),
                              occupancy_tolerance=1).parse_structures(primitive=False)[0]
                try:
                    p = s.get_primitive_structure()
                except Exception:  # noqa
                    p = s
                CifWriter(p).write_file(cif_out)
                at = read(cif_out)
                dmin, n09, n12 = metrics(at)
                nfrag, sizes = fragments(at)
                V = float(at.get_volume())
                r.update(V_relax=round(V, 1),
                         V_ratio=round(V / r["V_orig"], 4) if r["V_orig"] else None,
                         natoms_prim=len(at), dmin=round(dmin, 3),
                         pairs_lt_09=n09, pairs_lt_12=n12,
                         n_fragments=nfrag, frag_sizes=str(sizes[:5]))
                r["valid"] = bool(r["natoms_orig"] == len(at) and dmin >= 0.9 and nfrag == 1
                                  and r["V_ratio"] is not None and 0.75 <= r["V_ratio"] <= 1.25)
                r["prim_ok"] = (len(p) < len(s))
            except Exception as e:  # noqa
                r["error"] = (r["error"] + " | post:" + str(e))[:160]
                r["valid"] = False
        else:
            r["valid"] = False
        rows.append(r)

    cols = ["name", "valid", "uff_ok", "prim_ok", "natoms_orig", "natoms_prim", "V_orig",
            "V_relax", "V_ratio", "dmin", "pairs_lt_09", "pairs_lt_12", "n_fragments",
            "frag_sizes", "seconds", "error"]
    with open(a.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    ok = [r for r in rows if r.get("valid")]
    print(f"UFF ok: {sum(r['uff_ok'] for r in rows)}/{len(rows)}; valid: {len(ok)}/{len(rows)}")
    print("valid:", [r["name"] for r in ok])
    print(f"-> {a.out_csv}")


if __name__ == "__main__":
    main()
