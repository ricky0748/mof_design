#!/usr/bin/env python3
"""合并 UFF 与 MACE fallback 的结构有效性结果。

用法: python combine_mace.py <uff_summary.csv> <mace_dir> <out.csv>
规则：
- UFF 成功：以 UFF 判定为准（valid 列）；
- UFF 工具失败：读 <mace_dir>/<name>_mace.cif，按同一标准判定；
- 输出每行：uff_ok/uff_valid/mace_status/mace_valid/final_valid。
"""
import os
import sys
import numpy as np
import pandas as pd
from ase.io import read
from ase.neighborlist import natural_cutoffs, NeighborList
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components


def metrics(path):
    a = read(path)
    d = a.get_all_distances(mic=True)
    np.fill_diagonal(d, np.inf)
    tri = np.triu(np.ones_like(d, dtype=bool), 1)
    vals = d[tri]
    nl = NeighborList(natural_cutoffs(a, mult=1.15), self_interaction=False, bothways=True)
    nl.update(a)
    ncomp, _ = connected_components(csr_matrix(nl.get_connectivity_matrix(sparse=True)), directed=False)
    return len(a), float(a.get_volume()), float(vals.min()), int((vals < 0.9).sum()), int(ncomp)


def main():
    uff_csv, mace_dir, out = sys.argv[1:4]
    R = pd.read_csv(uff_csv)
    rows = []
    for r in R.itertuples():
        rec = dict(name=r.name, uff_ok=bool(r.uff_ok), uff_valid=bool(getattr(r, "valid")),
                   natoms_orig=r.natoms_orig, V_orig=r.V_orig)
        if not r.uff_ok:
            p = os.path.join(mace_dir, r.name + "_mace.cif")
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                rec.update(mace_status="missing", mace_valid=False)
            else:
                try:
                    n, V, dmin, n09, nfrag = metrics(p)
                    ratio = V / r.V_orig if r.V_orig else None
                    rec.update(mace_status="ok", mace_natoms=n, mace_V=round(V, 1),
                               mace_dmin=round(dmin, 3), mace_pairs_lt_09=n09,
                               mace_fragments=nfrag, mace_V_ratio=round(ratio, 4) if ratio else None,
                               mace_valid=bool(n == r.natoms_orig and dmin >= 0.9 and nfrag == 1
                                               and ratio is not None and 0.75 <= ratio <= 1.25))
                except Exception as e:  # noqa
                    rec.update(mace_status=f"error:{type(e).__name__}", mace_valid=False)
        else:
            rec.update(mace_status="not_needed", mace_valid=False)
        rec["final_valid"] = rec["uff_valid"] or rec["mace_valid"]
        rows.append(rec)
    O = pd.DataFrame(rows)
    O.to_csv(out, index=False)
    n = len(O)
    tool_fail = int((~O.uff_ok).sum())
    mace_ok = int((O.mace_status == "ok").sum())
    mace_valid = int(O.mace_valid.sum())
    struct_fail = int((O.uff_ok & ~O.uff_valid).sum())
    print(f"{os.path.basename(uff_csv)}: n={n} | UFF valid {int(O.uff_valid.sum())} | "
          f"tool fails {tool_fail} (MACE ok {mace_ok}, MACE valid {mace_valid}) | "
          f"structural fails among UFF-ok {struct_fail} | final valid {int(O.final_valid.sum())} "
          f"({O.final_valid.mean():.1%})")


if __name__ == "__main__":
    main()
