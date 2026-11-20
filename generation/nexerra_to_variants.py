#!/usr/bin/env python3
"""把 Nexerra 的 [Lr] SMILES 转成 anchor_rules / PORMAKE 能吃的配体变体。

Nexerra 只生成骨架，配位基团用 [Lr] 占位。第一版统一把 [Lr] 替换成羧酸
（默认 C(=O)[O-]），再用 anchor_rules 检查连接数和锚点类型；不合法的丢弃。

输入:
  - .txt: 每行一个 SMILES（Direct Design 的 output.txt）
  - .csv: 取 linker 列（ScafDesign 的 output.csv）
输出:
  variants_nexerra.csv（列与 generation/variants.csv 兼容，可直接给 build_candidates.py）
"""
import argparse, os, sys
import pandas as pd
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "anchor_rules"))
from anchor_rules import analyze, Config


from rdkit.Chem import rdMolDescriptors

ALLENE = Chem.MolFromSmarts("[CX2]=[CX2]=[CX2]")
KETENE = Chem.MolFromSmarts("[CX2]=[CX2]=[OX1]")


def rigid_ok(m, max_rot=6):
    """拒绝明显不稳定/难合成的骨架：小环、累积双键、非芳香环、过多可旋转键。"""
    if not any(a.GetIsAromatic() for a in m.GetAtoms()):
        return False, "no_aromatic"
    ri = m.GetRingInfo()
    for ring in ri.AtomRings():
        if all(m.GetAtomWithIdx(i).GetIsAromatic() for i in ring):
            continue
        if len(ring) not in (5, 6):
            return False, "small_nonaromatic_ring"
        for i in ring:
            a = m.GetAtomWithIdx(i)
            if a.GetHybridization() == Chem.HybridizationType.SP:
                return False, "sp_in_nonaromatic_ring"
            if sum(1 for b in a.GetBonds() if b.GetBondType() == Chem.BondType.DOUBLE) >= 2:
                return False, "cumulene_in_ring"
    if ALLENE is not None and m.HasSubstructMatch(ALLENE):
        return False, "allene"
    if KETENE is not None and m.HasSubstructMatch(KETENE):
        return False, "ketene"
    if rdMolDescriptors.CalcNumRotatableBonds(m) > max_rot:
        return False, "too_flexible"
    return True, "ok"


def read_smiles(path):
    if path.endswith(".csv"):
        d = pd.read_csv(path)
        for c in ("linker", "smiles", "SMILES"):
            if c in d:
                return d[c].dropna().astype(str).tolist()
        return []
    return [l.strip() for l in open(path) if l.strip() and not l.startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "variants_nexerra.csv"))
    ap.add_argument("--anchor", default="C(=O)([O-])", help="替换 [Lr] 的配位基团 SMILES；注意最后一个原子要接芳环，羧酸碳需写成 C(=O)([O-])")
    ap.add_argument("--max-heavy", type=int, default=60)
    ap.add_argument("--max-rot", type=int, default=6)
    ap.add_argument("--no-rigid-filter", action="store_true")
    ap.add_argument("--prefix", default="N", help="变体 ID 前缀，避免不同批次撞名")
    a = ap.parse_args()
    raw = read_smiles(a.input)
    rows, seen, fail = [], set(), {"rdkit": 0, "anchor": 0, "dup": 0}
    for i, smi in enumerate(raw):
        if "[Lr]" not in smi:
            continue
        conv = smi.replace("[Lr]", a.anchor)
        m = Chem.MolFromSmiles(conv)
        if m is None or len(Chem.GetMolFrags(m)) != 1 or m.GetNumHeavyAtoms() > a.max_heavy:
            fail["rdkit"] += 1; continue
        if any(at.GetNumRadicalElectrons() for at in m.GetAtoms()):
            fail["rdkit"] += 1; continue
        if not a.no_rigid_filter:
            ok, why = rigid_ok(m, a.max_rot)
            if not ok:
                fail[why] = fail.get(why, 0) + 1
                continue
        can = Chem.MolToSmiles(m)
        r = analyze(can, Config(), node="Zn4O")
        if r.get("status") != "ok" or int(r.get("n_connections", 0)) not in (2, 3):
            fail["anchor"] += 1; continue
        pt = r.get("primary_types"); pts = pt if isinstance(pt, list) else [pt]
        if pts != ["carboxylate"]:
            fail["anchor"] += 1; continue
        if can in seen:
            fail["dup"] += 1; continue
        seen.add(can)
        rows.append(dict(variant_id=f"{a.prefix}{len(rows):04d}", seed="Nexerra", seed_smiles=smi,
                         substituent="nexerra", smiles=can, n_connections=int(r["n_connections"]),
                         heavy_atoms=m.GetNumHeavyAtoms()))
    D = pd.DataFrame(rows)
    D.to_csv(a.out, index=False)
    print(f"输入 {len(raw)}，保留 {len(D)} -> {a.out}")
    print("丢弃:", fail)
    if len(D):
        print(D.groupby("n_connections").size().to_string())


if __name__ == "__main__":
    main()
