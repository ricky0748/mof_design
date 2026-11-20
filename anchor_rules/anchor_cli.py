#!/usr/bin/env python3
"""锚点规则命令行：读一批配体 SMILES，输出锚点标注和 ToBaCCo 构筑块。

用法:
  python3 anchor_cli.py linkers.smi --out out_dir [--node Zn4O] [--require-connections 2]
                        [--carboxylate-in-linker] [--pyrazolate-single-x] [--m-n-dist 2.0]
linkers.smi 每行: SMILES [名字]

输出（out_dir/）:
  summary.csv                 每个配体：状态、主锚点类型、连接数、形状、锚点间距、与 --node 是否兼容、[Lr] SMILES
  tobacco/<名字>.cif          ToBaCCo 风格构筑块（X 为连接点，带 _geom_bond 键表）
  he_xyz/<名字>.xyz           LEGO-MOF 风格（X 位置放虚拟 He）
  json/<名字>.json            完整锚点信息（类型、给体原子、可选给体、X 坐标）
"""
import argparse, csv, os
from anchor_rules import Config, analyze, compatible, to_tobacco_cif, to_he_xyz, anchors_json, NODE_COMPAT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("smi"); ap.add_argument("--out", default="anchor_out")
    ap.add_argument("--node", choices=sorted(NODE_COMPAT), default=None,
                    help="目标节点族：按节点重新指定主锚点（不兼容的基团记为孔道基团），并只导出连接数够的配体")
    ap.add_argument("--require-connections", type=int, default=2)
    ap.add_argument("--carboxylate-in-linker", action="store_true")
    ap.add_argument("--pyrazolate-single-x", action="store_true")
    ap.add_argument("--m-n-dist", type=float, default=2.0)
    a = ap.parse_args()
    cfg = Config(carboxylate_in_node=not a.carboxylate_in_linker, pyrazolate_single_x=a.pyrazolate_single_x, m_n_dist=a.m_n_dist)
    for sub in ("tobacco", "he_xyz", "json"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    rows = []
    for k, line in enumerate(open(a.smi)):
        p = line.split()
        if not p or p[0].startswith("#"):
            continue
        smi, name = p[0], (p[1] if len(p) > 1 else f"L{k:05d}")
        r = analyze(smi, cfg, node=a.node)
        ok = r["status"] == "ok" and r.get("n_connections", 0) >= a.require_connections
        comp = (r["status"] == "ok") if a.node else None
        if ok and "_mh" in r and (comp is None or comp):
            open(os.path.join(a.out, "tobacco", name + ".cif"), "w").write(to_tobacco_cif(r["_mh"], r["_anchors"], name, cfg))
            open(os.path.join(a.out, "he_xyz", name + ".xyz"), "w").write(to_he_xyz(r["_mh"], r["_anchors"], name))
        open(os.path.join(a.out, "json", name + ".json"), "w").write(anchors_json(r))
        rows.append(dict(name=name, smiles=smi, status=r["status"], primary_types="+".join(r.get("primary_types", [])),
                         optional="+".join(r.get("optional", [])), pore_groups="+".join(r.get("pore_groups") or []), n_groups=r.get("n_groups"), n_connections=r.get("n_connections"),
                         shape=r.get("shape"), anchor_angles=r.get("anchor_angles"), max_anchor_dist=r.get("max_anchor_dist"),
                         node=a.node, node_compatible=comp, exported=bool(ok and (comp is None or comp)), lr_smiles=r.get("lr_smiles")))
    with open(os.path.join(a.out, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} 个配体，导出 {sum(r['exported'] for r in rows)} 个构筑块 -> {a.out}")


if __name__ == "__main__":
    main()
