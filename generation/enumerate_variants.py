#!/usr/bin/env python3
"""规则式种子邻域采样：在种子配体的芳香 C–H 上枚举单取代变体。

约束（与项目"偏向可合成"的路线一致）：
- 保留种子的连接数（2 或 3）和锚点类型（羧酸）；
- 只做单取代，取代基限定为常见官能团；
- RDKit 可解析、无自由基、重原子 ≤ 60；
- 按规范 SMILES 去重，种子本身也保留。

用法: python3 enumerate_variants.py [--seeds seeds.smi] [--out variants.csv]
"""
import argparse, os
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
RDLogger.DisableLog("rdApp.*")
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "anchor_rules"))
from anchor_rules import analyze, Config

# 反应 SMARTS：把芳香 C–H 替换成取代基
SUBS = [
    ("F", "[cH:1]>>[c:1]F"),
    ("Cl", "[cH:1]>>[c:1]Cl"),
    ("Br", "[cH:1]>>[c:1]Br"),
    ("Me", "[cH:1]>>[c:1]C"),
    ("OH", "[cH:1]>>[c:1]O"),
    ("NH2", "[cH:1]>>[c:1]N"),
    ("OMe", "[cH:1]>>[c:1]OC"),
    ("CF3", "[cH:1]>>[c:1]C(F)(F)F"),
    ("CN", "[cH:1]>>[c:1]C#N"),
    ("NO2", "[cH:1]>>[c:1][N+](=O)[O-]"),
]


def read_seeds(path):
    out = []
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, smi = line.split(None, 1)
        out.append((name, smi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=os.path.join(os.path.dirname(__file__), "seeds.smi"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "variants.csv"))
    ap.add_argument("--max-heavy", type=int, default=60)
    a = ap.parse_args()
    rows, seen = [], set()
    for seed_name, seed_smi in read_seeds(a.seeds):
        mol = Chem.MolFromSmiles(seed_smi)
        if mol is None:
            print("SKIP invalid seed", seed_name); continue
        base = analyze(seed_smi, Config(), node="Zn4O")
        if base.get("status") != "ok":
            print("SKIP no anchors", seed_name); continue
        n_conn = int(base["n_connections"])
        cands = [("seed", seed_smi)]
        for sub_name, smarts in SUBS:
            rxn = AllChem.ReactionFromSmarts(smarts)
            for prod in rxn.RunReactants((mol,)):
                m = prod[0]
                try:
                    Chem.SanitizeMol(m)
                except Exception:
                    continue
                if len(Chem.GetMolFrags(m)) != 1 or m.GetNumHeavyAtoms() > a.max_heavy:
                    continue
                if any(at.GetNumRadicalElectrons() for at in m.GetAtoms()):
                    continue
                smi = Chem.MolToSmiles(m)
                cands.append((sub_name, smi))
        for sub_name, smi in cands:
            if smi in seen:
                continue
            r = analyze(smi, Config(), node="Zn4O")
            if r.get("status") != "ok" or int(r.get("n_connections", 0)) != n_conn:
                continue
            pt = r.get("primary_types")
            pts = pt if isinstance(pt, list) else [pt]
            if pts != ["carboxylate"]:
                continue
            seen.add(smi)
            rows.append(dict(variant_id=f"V{len(rows):04d}", seed=seed_name, seed_smiles=seed_smi,
                             substituent=sub_name, smiles=smi, n_connections=n_conn,
                             heavy_atoms=Chem.MolFromSmiles(smi).GetNumHeavyAtoms()))
    D = pd.DataFrame(rows)
    D.to_csv(a.out, index=False)
    print(f"{len(D)} variants -> {a.out}")
    if len(D):
        print(D.groupby(["seed", "substituent"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
