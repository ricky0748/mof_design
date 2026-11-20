"""在 CoRE MOF 2024 的 MOFid 配体上验证锚点规则，并与 Nexerra 式纯几何锚点规则对比。

输出:
  core2024_linker_anchors.csv    每个唯一有机组分一行：识别状态、主锚点类型、连接数、出现次数
  core2024_summary.json          覆盖率与类型分布
  geometric_vs_chemical.csv      纯羧酸配体上，几何规则选点与真实羧酸位置是否一致
"""
import json, random, collections, sys, itertools
import numpy as np, pandas as pd
from rdkit import Chem
from anchor_rules import analyze, normalize_smiles, find_anchors, is_organic, embed, Config, TODO_CLASSES

_TODO = {k: Chem.MolFromSmarts(v) for k, v in TODO_CLASSES.items()}


def gap_class(smi):
    """未覆盖配体落在哪类尚未实现的给体上；small_ligand = 甲酸、乙酸、碳酸、草酸等端基/小配体。"""
    m = Chem.MolFromSmiles(smi, sanitize=False)
    if m is None:
        return "unparseable"
    m.UpdatePropertyCache(strict=False); Chem.FastFindRings(m)
    heavy = sum(1 for a in m.GetAtoms() if a.GetSymbol() != "H")
    hits = [k for k, p in _TODO.items() if m.HasSubstructMatch(p)]
    if hits:
        return "+".join(hits)
    if heavy <= 6:
        return "small_ligand"
    return "other"

CSV = "/mnt/user-data/uploads/MOF-公开数据库/core2024/CR_data_CSD_modified_20250227.csv"


def organic_parts(mofid):
    if not isinstance(mofid, str) or " " not in mofid:
        return []
    smi = mofid.split(" ")[0]
    return [p for p in smi.split(".") if p and is_organic(p)]


def geometric_rule(mol_core_h, k):
    """Nexerra 式：在所有与 C 相连的 H 中，选平均两两距离最大的 k 个。
    k≤3 且候选 ≤60 时穷举，否则从最远点对出发贪心扩展。返回其母 C 原子索引集合。"""
    pos = mol_core_h.GetConformer().GetPositions()
    hs = [(a.GetIdx(), a.GetNeighbors()[0].GetIdx()) for a in mol_core_h.GetAtoms()
          if a.GetSymbol() == "H" and a.GetNeighbors()[0].GetSymbol() == "C"]
    if len(hs) < k:
        return None
    P = np.array([pos[i] for i, _ in hs]); M = np.linalg.norm(P[:, None] - P[None], axis=-1)
    score = lambda c: M[np.ix_(c, c)].sum()
    n = len(hs)
    if k <= 3 and n <= 60:
        best = max(itertools.combinations(range(n), k), key=lambda c: score(list(c)))
    else:
        i, j = np.unravel_index(M.argmax(), M.shape); best = [i, j]
        while len(best) < k:
            best.append(max((h for h in range(n) if h not in best), key=lambda h: score(best + [h])))
    return {hs[b][1] for b in best}


def dummy_smiles(core, carbons):
    """在给定 C 上挂哑原子 * 后的规范 SMILES：用于判断几何选点与真实位点是否"化学等价"（考虑分子对称性）。"""
    rw = Chem.RWMol(core)
    for c in carbons:
        d = rw.AddAtom(Chem.Atom(0)); rw.AddBond(int(c), d, Chem.BondType.SINGLE)
        a = rw.GetAtomWithIdx(int(c)); a.SetNumExplicitHs(0); a.SetNoImplicit(True)
    m = rw.GetMol()
    try:
        Chem.SanitizeMol(m)
    except Exception:
        m.UpdatePropertyCache(strict=False)
    return Chem.MolToSmiles(m)


def main(n3d=800):
    c = pd.read_csv(CSV, low_memory=False)
    cnt = collections.Counter(p for m in c["mofid-v1"] for p in set(organic_parts(m)))
    rows = []
    for smi, n in cnt.items():
        r = analyze(smi, embed3d=False)
        rows.append(dict(smiles=smi, n_mofs=n, status=r["status"], n_connections=r.get("n_connections_est"),
                         gap=("" if r["status"] == "ok" else gap_class(smi)),
                         primary_types="+".join(r.get("primary_types", [])), optional="+".join(r.get("optional", []))))
    D = pd.DataFrame(rows).sort_values("n_mofs", ascending=False)
    D.to_csv("core2024_linker_anchors.csv", index=False)
    st = dict(zip(D.smiles, D.status))
    mof_ok = sum(1 for m in c["mofid-v1"] if organic_parts(m) and all(st[p] == "ok" for p in set(organic_parts(m))))
    mof_any = sum(1 for m in c["mofid-v1"] if organic_parts(m))
    summ = dict(
        n_structures=len(c), n_structures_with_organic=mof_any,
        n_unique_organic=len(D), status_counts=D.status.value_counts().to_dict(),
        status_weighted_by_occurrence={k: int(v) for k, v in D.groupby("status").n_mofs.sum().items()},
        frac_structures_all_linkers_ok=round(mof_ok / mof_any, 4),
        primary_type_counts_unique=D[D.status == "ok"].primary_types.value_counts().head(15).to_dict(),
        gap_classes_unique=D[D.status != "ok"].gap.value_counts().to_dict(),
        gap_classes_weighted={k: int(x) for k, x in D[D.status != "ok"].groupby("gap").n_mofs.sum().sort_values(ascending=False).items()},
        top_lt2_examples=D[D.status == "lt2_connections"].head(25)[["smiles", "n_mofs", "primary_types"]].to_dict("records"),
        parse_failed_examples=D[D.status == "parse_failed"].head(10)[["smiles", "n_mofs"]].to_dict("records"),
    )
    # 几何 vs 化学：只取"纯羧酸、≥2 个羧基、无其他给体"的配体
    carb = D[(D.status == "ok") & (D.primary_types == "carboxylate") & (D.optional == "")].copy()
    random.seed(0)
    sample = carb.sample(min(n3d, len(carb)), random_state=0)
    comp = []
    for it, (smi, n) in enumerate(zip(sample.smiles, sample.n_mofs)):
        if it % 50 == 0:
            print("geom", it, flush=True)
        mol = normalize_smiles(smi); anc = [a for a in find_anchors(mol) if a.primary]
        if mol.GetNumHeavyAtoms() > 60:
            continue
        k = len(anc); true_c = {a.attach for a in anc}
        # 剥掉羧基 → H（Nexerra 的"裸核"）
        rw = Chem.RWMol(mol)
        drop = set()
        for a in anc:
            drop.add(a.cut); drop |= {nb.GetIdx() for nb in mol.GetAtomWithIdx(a.cut).GetNeighbors() if nb.GetSymbol() == "O"}
        for i in sorted(drop, reverse=True):
            rw.RemoveAtom(i)
        core = rw.GetMol()
        try:
            Chem.SanitizeMol(core)
        except Exception:
            continue
        # 原子索引映射：删除后索引左移
        remap = {old: old - sum(1 for d in drop if d < old) for old in true_c}
        if core.GetNumAtoms() < 2:
            continue
        try:
            mh = embed(core)
        except Exception:
            mh = None
        if mh is None:
            continue
        g = geometric_rule(mh, k)
        if g is None:
            continue
        tc = {remap[x] for x in true_c}
        comp.append(dict(smiles=smi, n_mofs=n, k=k, n_ch_sites=sum(1 for a in mh.GetAtoms() if a.GetSymbol() == "H"),
                         agree_atoms=(g == tc), agree=(dummy_smiles(core, g) == dummy_smiles(core, tc)), overlap=len(g & tc) / k,
                         geometric=dummy_smiles(core, g), chemical=dummy_smiles(core, tc)))
    G = pd.DataFrame(comp); G.to_csv("geometric_vs_chemical.csv", index=False)
    summ["geometric_vs_chemical"] = dict(n=len(G), exact_agree_symmetry_aware=round(G.agree.mean(), 4),
                                         exact_agree_atom_index=round(G.agree_atoms.mean(), 4),
                                         agree_weighted_by_occurrence=round((G.agree * G.n_mofs).sum() / G.n_mofs.sum(), 4),
                                         mean_site_overlap=round(G.overlap.mean(), 4),
                                         exact_agree_by_k={int(k): round(v, 3) for k, v in G.groupby("k").agree.mean().items()},
                                         n_by_k={int(k): int(v) for k, v in G.k.value_counts().items()})
    json.dump(summ, open("core2024_summary.json", "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k not in ("top_lt2_examples", "parse_failed_examples")}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 800)
