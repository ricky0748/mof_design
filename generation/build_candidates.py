#!/usr/bin/env python3
"""把配体变体组装成候选框架 CIF（PORMAKE + 现有几何判据）。

判据与 anchor_rules/assembly_test.py 一致：
- 连接方向偏差 ≤ 20°（二齿相对 X–X 轴，三齿相对质心→X）
- 无碰撞（重原子 ≥1.5 Å，含 H ≥1.0 Å，排除 1-2/1-3）
- 有机部分键长 0.85–1.9 Å
- 三齿配体额外要求 Locator RMSD ≤ 0.3

用法:
  python3 build_candidates.py [--variants variants.csv] [--out out] [--limit N] [--topos pcu fcu nbo]
输出:
  out/cif/<variant>_<topo>.cif   成功组装的候选
  out/candidates.csv             所有尝试的元数据（含失败原因）
"""
import argparse, contextlib, io, os, sys, traceback
import pandas as pd
import pormake

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "anchor_rules"))
from assembly_test import chem_bb, deviation, check_fw

DEV_MAX, RMSD_MAX = 20.0, 0.3
CASES2 = [("pcu", "N16", "Zn4O"), ("fcu", "N419", "Zr6"), ("nbo", "N17", "Cu_paddlewheel")]
CASES3 = [("tbo", "N17", "Cu_paddlewheel")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=os.path.join(HERE, "variants.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--topos", nargs="*", default=["pcu", "fcu", "nbo", "tbo"])
    a = ap.parse_args()
    for sub in ("cif", "bb"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    V = pd.read_csv(a.variants)
    if a.limit:
        V = V.head(a.limit)
    db = pormake.Database()
    topos = {t: db.get_topo(t) for t in ("pcu", "fcu", "nbo", "tbo")}
    bbs = {b: db.get_bb(b) for b in ("N16", "N419", "N17")}
    loc = pormake.Locator()

    rows = []
    for i, v in V.iterrows():
        n_conn = int(v.n_connections)
        cases = CASES2 if n_conn == 2 else CASES3
        cases = [c for c in cases if c[0] in a.topos]
        for topo, nodebb, nodename in cases:
            r = dict(variant_id=v.variant_id, seed=v.seed, smiles=v.smiles, n_connections=n_conn,
                     topo=topo, node=nodebb, build=False, dev_max=None, dev_ok=False, rmsd=None,
                     rmsd_ok=True, n_clash=None, n_bad_bond=None, n_atoms=None, success=False,
                     cif=None, error=None)
            try:
                xyz, st = chem_bb(v.smiles, nodename)
                if not xyz:
                    r["error"] = "no_bb:" + str(st); rows.append(r); continue
                devs = deviation(xyz)
                r["dev_max"] = round(max(devs), 1); r["dev_ok"] = max(devs) <= DEV_MAX
                name = f"{v.variant_id}_{topo}"
                bbpath = os.path.join(a.out, "bb", name + ".xyz")
                open(bbpath, "w").write(xyz)
                with contextlib.redirect_stdout(io.StringIO()):
                    bb = pormake.BuildingBlock(bbpath)
                    b = pormake.Builder()
                    if n_conn == 2:
                        fw = b.build_by_type(topology=topos[topo], node_bbs={0: bbs[nodebb]},
                                             edge_bbs={(0, 0): bb})
                    else:
                        t = topos["tbo"]
                        types = {int(cn): int(nt) for nt, cn in zip(t.unique_node_types, t.unique_cn)}
                        ls3 = t.unique_local_structures[list(t.unique_cn).index(3)]
                        r["rmsd"] = round(float(loc.calculate_rmsd(ls3, bb)), 3)
                        r["rmsd_ok"] = r["rmsd"] <= RMSD_MAX
                        fw = b.build_by_type(topology=t, node_bbs={types[3]: bb, types[4]: bbs["N17"]})
                r["build"] = True
                r.update(check_fw(fw, None))
                r["success"] = bool(r["dev_ok"] and r["rmsd_ok"] and r["n_clash"] == 0 and r["n_bad_bond"] == 0)
                if r["success"]:
                    cif = os.path.join(a.out, "cif", name + ".cif")
                    with contextlib.redirect_stdout(io.StringIO()):
                        fw.write_cif(cif)
                    r["cif"] = os.path.relpath(cif, HERE)
            except Exception as e:
                r["error"] = repr(e)[:160]
            rows.append(r)
        if (i + 1) % 25 == 0:
            print(f"{i+1}/{len(V)}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(a.out, "candidates.csv"), index=False)
    print(f"\n尝试 {len(R)} 个组装；成功 {R.success.sum()} 个 -> {a.out}")
    print(R.groupby(["topo", "success"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
