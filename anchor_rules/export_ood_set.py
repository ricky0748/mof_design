#!/usr/bin/env python3
"""把 assembly_results.csv 里"化学锚点 + 几何判据成功"的结构全部导出为 CIF，作为代理模型
分布外验证的第一批候选（组装后结构）。不重新跑配体筛选，只重建 PORMAKE 框架。

用法: python3 export_ood_set.py
输出: assembly_out/ood_cif/*.cif + assembly_out/ood_cif/index.csv
"""
import os, io, contextlib, warnings
import pandas as pd
import pormake
warnings.filterwarnings("ignore")

from assembly_test import chem_bb

OUT = os.path.join("assembly_out", "ood_cif")
os.makedirs(OUT, exist_ok=True)


def main():
    R = pd.read_csv(os.path.join("assembly_out", "assembly_results.csv"))
    S = R[(R["mode"] == "chem") & R["success"]].copy()
    db = pormake.Database()
    topos = {t: db.get_topo(t) for t in ("pcu", "fcu", "nbo", "tbo")}
    bbs = {b: db.get_bb(b) for b in ("N16", "N419", "N17")}
    fs = [f for f in os.listdir(OUT) if f.endswith(".cif")]
    for f in fs:
        os.remove(os.path.join(OUT, f))

    cache, rows = {}, []
    for i, r in enumerate(S.itertuples()):
        key = r.smiles
        if key not in cache:
            with contextlib.redirect_stdout(io.StringIO()):
                xyz, st = chem_bb(key, "Zn4O")
            cache[key] = xyz
        xyz = cache[key]
        if not xyz:
            continue
        bbpath = os.path.join(OUT, "_bb_tmp.xyz")
        open(bbpath, "w").write(xyz)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                bb = pormake.BuildingBlock(bbpath)
                b = pormake.Builder()
                if r.topo in ("pcu", "fcu", "nbo"):
                    fw = b.build_by_type(topology=topos[r.topo], node_bbs={0: bbs[r.node]},
                                         edge_bbs={(0, 0): bb})
                elif r.topo == "tbo":
                    t = topos["tbo"]
                    types = {int(cn): int(nt) for nt, cn in zip(t.unique_node_types, t.unique_cn)}
                    fw = b.build_by_type(topology=t, node_bbs={types[3]: bb, types[4]: bbs["N17"]})
                else:
                    continue
                name = f"O{i:04d}_{r.topo}"
                fw.write_cif(os.path.join(OUT, name + ".cif"))
            rows.append(dict(cif=name + ".cif", topo=r.topo, node=r.node, smiles=r.smiles,
                             atoms_in_cell=r.n_atoms))
        except Exception as e:
            print("FAIL", i, r.topo, repr(e)[:100])
        finally:
            if os.path.exists(bbpath):
                os.remove(bbpath)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "index.csv"), index=False)
    print(f"导出 {len(rows)} 个结构 -> {OUT}")
    print(pd.DataFrame(rows).groupby("topo").size().to_string())


if __name__ == "__main__":
    main()
