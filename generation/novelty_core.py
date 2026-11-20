#!/usr/bin/env python3
"""用 CoRE MOF 2024 的 MOFid-v1 字符串做框架级 novelty 比对。

思路：把 MOFid-v1 拆成「金属节点元素集合 + 有机配体骨架集合 + 拓扑 + catenation」，
生成结构用同样的键去查 CoRE。两层判定：
- exact：拓扑、cat、金属集合、配体骨架全部一致 -> 很可能是已有框架（或同构体）；
- topo_linker：拓扑和配体骨架一致、金属不同 -> 已有配体的金属类似物，novelty 有限。
配体骨架用 InChIKey 第一段（连通性），对质子化/电荷不敏感。

用法:
  python3 novelty_core.py --core-csv "C:/.../core2024/CR_data_CSD_modified_20250227.csv" \
      --variants variants.csv --candidates out/candidates.csv --out novelty_core.csv
"""
import argparse, os, re, sys
import pandas as pd
from rdkit import Chem, RDLogger
RDLogger.DisableLog("rdApp.*")
HERE = os.path.dirname(os.path.abspath(__file__))
METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Th U".split())
NODE_METALS = {"N16": {"Zn"}, "N419": {"Zr"}, "N17": {"Cu"}}


def ikey(smi):
    m = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
    if m is None:
        return None
    try:
        return Chem.MolToInchiKey(m).split("-")[0]
    except Exception:
        return None


def parse_mofid(s):
    """-> dict(topos, cat, metal, linkers) or None."""
    if not isinstance(s, str) or " MOFid-v1." not in s:
        return None
    pre, post = s.split(" MOFid-v1.", 1)
    topo_s, cat_s = post.split(".cat", 1) if ".cat" in post else (post.split(";")[0], "0")
    cat = "cat" + cat_s.split(";")[0]
    topos = [t for t in topo_s.split(",") if t and t not in ("ERROR", "unknown", "unstable")]
    metal, linkers = set(), set()
    for comp in pre.split("."):
        if not comp:
            continue
        elems = re.findall(r"[A-Z][a-z]?", comp)
        ms = {e for e in elems if e in METALS}
        if ms:
            metal |= ms
        elif "C" in elems:
            k = ikey(comp)
            if k:
                linkers.add(k)
    return dict(topos=topos, cat=cat, metal=frozenset(metal), linkers=frozenset(linkers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core-csv", required=True)
    ap.add_argument("--variants", default=os.path.join(HERE, "variants.csv"))
    ap.add_argument("--candidates", default=os.path.join(HERE, "out", "candidates.csv"))
    ap.add_argument("--out", default=os.path.join(HERE, "novelty_core.csv"))
    a = ap.parse_args()
    C = pd.read_csv(a.core_csv, usecols=["mofid-v1", "refcode", "topology(AllNodes)"])
    exact, topo_linker, metal_linker = {}, {}, {}
    bad = 0
    for mofid_s, refcode, topo_all in C[["mofid-v1", "refcode", "topology(AllNodes)"]].itertuples(index=False, name=None):
        p = parse_mofid(mofid_s)
        if not p:
            bad += 1; continue
        topos = p["topos"]
        if not topos and isinstance(topo_all, str) and topo_all not in ("unnamed", "unstable", "ERROR", "unknown"):
            topos = [topo_all]
        metal, linkers, cat = p["metal"], p["linkers"], p["cat"]
        for t in topos:
            exact.setdefault((t, cat, metal, linkers), []).append(refcode)
            topo_linker.setdefault((t, linkers), []).append(refcode)
        metal_linker.setdefault((metal, linkers), []).append(refcode)
    print(f"CoRE 2024: {len(C)} 行，解析成功 {len(C)-bad}，无 MOFid 标记 {bad}")
    print(f"exact keys {len(exact)}，topo+linker keys {len(topo_linker)}，metal+linker keys {len(metal_linker)}")

    V = pd.read_csv(a.variants)[["variant_id", "substituent"]]
    G = pd.read_csv(a.candidates); G = G[G.success].merge(V, on="variant_id")
    rows = []
    for r in G.itertuples():
        k = ikey(r.smiles)
        metal = NODE_METALS.get(r.node, set())
        topos = [r.topo]
        ex = []
        for t in topos:
            ex += exact.get((t, "cat0", frozenset(metal), frozenset({k})), [])
        tl = []
        for t in topos:
            tl += topo_linker.get((t, frozenset({k})), [])
        ml = metal_linker.get((frozenset(metal), frozenset({k})), [])
        rows.append(dict(mof=f"{r.variant_id}_{r.topo}", seed=r.seed, substituent=r.substituent,
                         topo=r.topo, node=r.node, ligand_ikey=k, metal=",".join(sorted(metal)),
                         exact_hits=";".join(sorted(set(ex))[:5]), n_exact=len(ex),
                         toplinker_hits=";".join(sorted(set(tl))[:5]), n_topolinker=len(tl),
                         metallinker_hits=";".join(sorted(set(ml))[:5]), n_metallinker=len(ml)))
    R = pd.DataFrame(rows); R.to_csv(a.out, index=False)
    print(f"\n生成结构 {len(R)} 个 -> {a.out}")
    print("exact 命中:", int((R.n_exact > 0).sum()), "/", len(R))
    print("topo+ligand 命中（含金属类似物）:", int((R.n_topolinker > 0).sum()), "/", len(R))
    print("metal+ligand 命中（不看拓扑）:", int((R.n_metallinker > 0).sum()), "/", len(R))
    print(R.groupby(["topo"]).agg(n=("mof", "size"), exact=("n_exact", lambda s: int((s > 0).sum())),
                                  toplinker=("n_topolinker", lambda s: int((s > 0).sum())),
                                  metallinker=("n_metallinker", lambda s: int((s > 0).sum()))).to_string())
    print("\nTop CO2 候选的 CoRE 命中：")
    top = ["V0164_nbo", "V0039_nbo", "V0035_nbo", "V0032_nbo", "V0033_nbo", "V0058_nbo"]
    print(R[R.mof.isin(top)][["mof", "exact_hits", "n_exact", "toplinker_hits", "n_topolinker",
                              "metallinker_hits", "n_metallinker"]].to_string(index=False))


if __name__ == "__main__":
    main()
