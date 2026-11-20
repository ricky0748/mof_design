#!/usr/bin/env python3
"""给生产批次加 novelty / known-control 标注。

三个层次：
1. seed_structure：未取代种子搭出的结构，多数是教科书 MOF（known control，不能算生成新颖度）；
2. ligand_in_core：配体本身能在 CoRE 2024 的 1,738 个唯一配体里找到；
3. substituted_variant：种子骨架 + 新取代基；配体层面可能是新的，但骨架家族已知。

框架级 novelty 还需要 MOFid 对 CoRE/BW-DB 比对，这一步先做配体级和 known-control 分层。

用法: python3 annotate_novelty.py [--out annotated.csv]
"""
import argparse, os, sys
import pandas as pd
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "anchor_rules"))

# 仅用于给未取代种子结构一个可读名字，不参与任何打分
KNOWN = {
    ("BDC", "pcu", "N16"): "MOF-5 / IRMOF-1",
    ("BDC", "fcu", "N419"): "UiO-66",
    ("BDC", "nbo", "N17"): "Cu paddlewheel BDC family",
    ("BTC", "tbo", "N17"): "HKUST-1",
    ("2,6-NDC", "pcu", "N16"): "IRMOF-8",
    ("BPDC", "pcu", "N16"): "IRMOF-10",
    ("NH2-BDC", "fcu", "N419"): "UiO-66-NH2",
    ("TDC", "fcu", "N419"): "UiO-66-thiophene analog",
    ("TDC", "pcu", "N16"): "IRMOF-thiophene analog",
    ("DOBDC", "fcu", "N419"): "UiO-66-(OH)2 analog",
    ("DOBDC", "pcu", "N16"): "IRMOF-(OH)2 analog",
    ("DM-BDC", "pcu", "N16"): "IRMOF-(CH3)2 analog",
}


def canon(s):
    m = Chem.MolFromSmiles(s) if isinstance(s, str) else None
    return Chem.MolToSmiles(m) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "annotated.csv"))
    a = ap.parse_args()
    V = pd.read_csv(os.path.join(HERE, "variants.csv"))
    G = pd.read_csv(os.path.join(HERE, "out", "candidates.csv"))
    G = G[G.success].merge(V[["variant_id", "substituent"]], on="variant_id")
    C = pd.read_csv(os.path.join(ROOT, "anchor_rules", "core2024_linker_anchors.csv"))
    core = set(filter(None, (canon(s) for s in C.smiles.dropna())))
    G["canon"] = G.smiles.map(canon)
    G["ligand_in_core"] = G.canon.isin(core)
    G["seed_structure"] = G.substituent == "seed"
    G["known_name"] = [KNOWN.get((r.seed, r.topo, r.node), "") for r in G.itertuples()]
    G["novelty_tier"] = G.apply(
        lambda r: "known_control" if r.seed_structure else
                  ("ligand_in_core" if r.ligand_in_core else "substituted_variant"), axis=1)
    # 把已有的打分/适用域带上
    S = pd.read_csv(os.path.join(HERE, "scored.csv"))
    S["mof"] = S.mof
    G["mof"] = G.variant_id + "_" + G.topo
    out = G.merge(S.drop(columns=[c for c in ("seed", "topo", "node", "smiles", "n_connections") if c in S]),
                  on="mof", how="left")
    out.to_csv(a.out, index=False)
    print(f"{len(out)} 个候选 -> {a.out}")
    print(out.novelty_tier.value_counts().to_string())
    print("\nknown controls:")
    print(out[out.seed_structure][["mof", "seed", "topo", "known_name"]].to_string(index=False))
    print("\nby scaffold family:")
    print(out.groupby(["seed", "topo"]).novelty_tier.value_counts().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
