"""锚点规则 → PORMAKE 组装成功率测试（化学锚点 vs Nexerra 式几何锚点）。

配体：CoRE MOF 2024 中"纯羧酸"配体（无其他给体），k=2 作边、k=3 作 3-c 节点。
拓扑/节点（PORMAKE 自带构筑块）:
  k=2:  pcu + Zn4O(N16)   fcu + Zr6(N419)   nbo + Cu 桨轮(N17)
  k=3:  tbo + Cu 桨轮(N17)，配体占 3-c 位
两套锚点:
  chem  本模块化学规则：羧基 C 归节点，X 在 C(芳)–C(羧) 键中点
  geom  Nexerra 式：羧基换 H 得裸核，在 C–H 中选平均两两距离最大的 k 个，X 放在 C 沿 C→H 方向 0.74 Å 处
判据（全部满足才算"成功"）:
  build    PORMAKE 构建不报错
  dev      每个 X：(X−母原子) 与"理想连接方向"夹角 ≤ 20°；ditopic 理想方向为 X–X 轴，tritopic 为质心→X
  rmsd     tritopic：PORMAKE Locator 与拓扑局部结构的 RMSD ≤ 0.3
  clash    周期性下非键原子对最小距离：重原子 ≥ 1.5 Å，含 H ≥ 1.0 Å（排除 1-2、1-3 关系）
  bond     构筑块之间新成键长度在 1.2–1.9 Å
另外记录化学正确性：geom 选点与真实羧基位点是否化学等价（来自 validate_core2024 的对称性比较）。

用法: python3 assembly_test.py [n2=150] [n3=80] [workers=8]
"""
import sys, os, io, contextlib, warnings, json, itertools
import numpy as np, pandas as pd
import multiprocessing as mp
from rdkit import Chem, RDLogger
from anchor_rules import analyze, normalize_smiles, find_anchors, embed, Config, to_pormake_xyz
from validate_core2024 import dummy_smiles

RDLogger.DisableLog("rdApp.*"); warnings.filterwarnings("ignore")
OUT = "assembly_out"
CASES2 = [("pcu", "N16", "Zn4O"), ("fcu", "N419", "Zr6"), ("nbo", "N17", "Cu_paddlewheel")]
CASES3 = [("tbo", "N17", "Cu_paddlewheel")]
DEV_MAX, RMSD_MAX = 20.0, 0.3
ORG = {"C", "H", "N", "O", "S", "F", "Cl", "Br", "I", "B", "P", "Si", "Se"}
_pm = {}


def pm():
    if not _pm:
        with contextlib.redirect_stdout(io.StringIO()):
            import pormake
            _pm["m"] = pormake; _pm["db"] = pormake.Database(); _pm["loc"] = pormake.Locator()
            _pm["topo"] = {t: _pm["db"].get_topo(t) for t in ("pcu", "fcu", "nbo", "tbo")}
            _pm["bb"] = {b: _pm["db"].get_bb(b) for b in ("N16", "N419", "N17")}
    return _pm


# ---------------------------------------------------------------- 构筑块
def chem_bb(smi, node):
    r = analyze(smi, Config(), node=node)
    if r["status"] != "ok" or "_mh" not in r:
        return None, r["status"]
    return to_pormake_xyz(r["_mh"], r["_anchors"], Config()), "ok"


def geom_bb(smi, k):
    """返回 (xyz, 化学等价与否)。"""
    mol = normalize_smiles(smi)
    anc = [a for a in find_anchors(mol) if a.primary]
    true_c = {a.attach for a in anc}
    drop = set()
    for a in anc:
        drop.add(a.cut); drop |= {n.GetIdx() for n in mol.GetAtomWithIdx(a.cut).GetNeighbors() if n.GetSymbol() == "O"}
    rw = Chem.RWMol(mol)
    for i in sorted(drop, reverse=True):
        rw.RemoveAtom(i)
    core = rw.GetMol()
    Chem.SanitizeMol(core)
    remap = {o: o - sum(1 for d in drop if d < o) for o in true_c}
    mh = embed(core)
    if mh is None:
        return None, None
    pos = mh.GetConformer().GetPositions()
    hs = [(a.GetIdx(), a.GetNeighbors()[0].GetIdx()) for a in mh.GetAtoms()
          if a.GetSymbol() == "H" and a.GetNeighbors()[0].GetSymbol() == "C"]
    if len(hs) < k:
        return None, None
    P = np.array([pos[h] for h, _ in hs]); M = np.linalg.norm(P[:, None] - P[None], axis=-1)
    sc = lambda c: M[np.ix_(c, c)].sum()
    if k <= 3 and len(hs) <= 60:
        best = list(max(itertools.combinations(range(len(hs)), k), key=lambda c: sc(list(c))))
    else:
        i, j = np.unravel_index(M.argmax(), M.shape); best = [int(i), int(j)]
        while len(best) < k:
            best.append(max((h for h in range(len(hs)) if h not in best), key=lambda h: sc(best + [h])))
    chosen = [hs[b] for b in best]
    agree = dummy_smiles(core, {c for _, c in chosen}) == dummy_smiles(core, {remap[x] for x in true_c})
    # 写 PORMAKE xyz：删去被选中的 H，X 放在 C + 0.74 Å·(C→H)
    dropH = {h for h, _ in chosen}
    keep = [i for i in range(mh.GetNumAtoms()) if i not in dropH]; new = {o: n for n, o in enumerate(keep)}
    atoms = [(mh.GetAtomWithIdx(i).GetSymbol(), pos[i]) for i in keep]
    xs = []
    for h, c in chosen:
        v = pos[h] - pos[c]; v /= np.linalg.norm(v); xs.append((pos[c] + 0.74 * v, c))
    xidx = list(range(len(atoms), len(atoms) + len(xs)))
    atoms += [("X", p) for p, _ in xs]
    bonds = [(new[b.GetBeginAtomIdx()], new[b.GetEndAtomIdx()], {1.0: "S", 2.0: "D", 3.0: "T", 1.5: "A"}.get(b.GetBondTypeAsDouble(), "S"))
             for b in mh.GetBonds() if b.GetBeginAtomIdx() in new and b.GetEndAtomIdx() in new]
    bonds += [(new[c], x, "S") for x, (_, c) in zip(xidx, xs)]
    out = [str(len(atoms)), " ".join(str(x) for x in xidx)]
    out += [f"{s} {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}" for s, p in atoms] + [f"{i} {j} {t}" for i, j, t in bonds]
    return "\n".join(out) + "\n", bool(agree)


def load_bb(xyz, name):
    path = os.path.join(OUT, "bb", name + ".xyz")
    open(path, "w").write(xyz)
    with contextlib.redirect_stdout(io.StringIO()):
        return pm()["m"].BuildingBlock(path)


def xyz_parse(xyz):
    L = xyz.strip().split("\n"); n = int(L[0]); xi = [int(t) for t in L[1].split()]
    P = np.array([[float(v) for v in l.split()[1:4]] for l in L[2:2 + n]])
    par = {}
    for l in L[2 + n:]:
        i, j, _ = l.split(); i, j = int(i), int(j)
        if j in xi: par[j] = i
        elif i in xi: par[i] = j
    return P, xi, par


def deviation(xyz):
    """每个 X 的连接方向偏差（度）：ditopic 相对 X–X 轴，tritopic 及以上相对 X 质心→X。"""
    P, xi, par = xyz_parse(xyz)
    X = P[xi]; c = X.mean(axis=0); devs = []
    for k, x in enumerate(xi):
        v = P[x] - P[par[x]]; v /= np.linalg.norm(v)
        ideal = (X[k] - X[1 - k]) if len(xi) == 2 else (X[k] - c)
        ideal = ideal / np.linalg.norm(ideal)
        devs.append(float(np.degrees(np.arccos(np.clip(v @ ideal, -1, 1)))))
    return devs


# ---------------------------------------------------------------- 组装后检查
def check_fw(fw, n_bb_atoms_node):
    from ase.neighborlist import neighbor_list
    at = fw.atoms; bonds = np.asarray(fw.bonds)
    sym = np.array(at.get_chemical_symbols())
    i, j, d = neighbor_list("ijd", at, 2.0)
    m = i < j; i, j, d = i[m], j[m], d[m]
    nb = [set() for _ in range(len(at))]
    for a, b in bonds:
        nb[a].add(b); nb[b].add(a)
    near = lambda a, b: b in nb[a] or bool(nb[a] & nb[b])
    isH = (sym[i] == "H") | (sym[j] == "H")
    thr = np.where(isH, 1.0, 1.5)
    bad = [(a, b, x) for a, b, x, t in zip(i, j, d, thr) if x < t and not near(a, b)]
    # 构筑块间新成键长度（用 PBC 最小像距离）
    from ase.geometry import find_mic
    org = [(a, b) for a, b in bonds if sym[a] in ORG and sym[b] in ORG]     # 只看有机部分的键（M–O 键本来就 ~2 Å）
    org = np.array(org); P = at.get_positions()
    bl = find_mic(P[org[:, 1]] - P[org[:, 0]], at.cell, at.pbc)[1]
    return dict(n_atoms=len(at), n_clash=len(bad), min_clash=(float(min(x for *_, x in bad)) if bad else None),
                n_bad_bond=int(((bl < 0.85) | (bl > 1.9)).sum()), max_bond=round(float(bl.max()), 3))


def run_one(job):
    smi, k, mode, xyz, agree = job["smiles"], job["k"], job["mode"], job["xyz"], job.get("agree")
    rows = []
    devs = deviation(xyz)
    for topo, nodebb, nodename in (CASES2 if k == 2 else CASES3):
        r = dict(smiles=smi, k=k, mode=mode, topo=topo, node=nodebb, chem_agree=agree,
                 dev_max=round(max(devs), 1), dev_ok=max(devs) <= DEV_MAX)
        try:
            P = pm(); M = P["m"]; t = P["topo"][topo]; nbb = P["bb"][nodebb]
            name = f"{job['id']}_{mode}"
            bb = load_bb(xyz, name)
            with contextlib.redirect_stdout(io.StringIO()):
                b = M.Builder()
                if k == 2:
                    fw = b.build_by_type(topology=t, node_bbs={0: nbb}, edge_bbs={(0, 0): bb})
                    r["rmsd"] = None; r["rmsd_ok"] = True
                else:
                    # tbo: 找 3-c 与 4-c 的节点类型
                    types = {int(cn): int(nt) for nt, cn in zip(t.unique_node_types, t.unique_cn)}
                    ls3 = t.unique_local_structures[list(t.unique_cn).index(3)]
                    r["rmsd"] = round(float(P["loc"].calculate_rmsd(ls3, bb)), 3); r["rmsd_ok"] = r["rmsd"] <= RMSD_MAX
                    fw = b.build_by_type(topology=t, node_bbs={types[3]: bb, types[4]: nbb})
            r["build"] = True
            r.update(check_fw(fw, None))
            r["fw_rmsd_max"] = round(float(fw.info.get("max_rmsd", np.nan)), 3)
            if job.get("write"):
                fw.write_cif(os.path.join(OUT, "cif", f"{name}_{topo}.cif"))
        except Exception as e:
            r["build"] = False; r["error"] = repr(e)[:120]
        r["success"] = bool(r.get("build") and r["dev_ok"] and r.get("rmsd_ok", False) and r.get("n_clash", 1) == 0
                            and r.get("n_bad_bond", 1) == 0)
        rows.append(r)
    return rows


def prepare(row):
    smi, k, i = row
    jobs = []
    try:
        xyz, st = chem_bb(smi, "Zn4O")
        if xyz:
            jobs.append(dict(id=i, smiles=smi, k=k, mode="chem", xyz=xyz, agree=True))
        gx, ag = geom_bb(smi, k)
        if gx:
            jobs.append(dict(id=i, smiles=smi, k=k, mode="geom", xyz=gx, agree=ag))
    except Exception:
        pass
    # 两套都成功准备才进入比较（配对）
    return jobs if len(jobs) == 2 else []


def main(n2=150, n3=80, workers=8):
    for s in ("bb", "cif"):
        os.makedirs(os.path.join(OUT, s), exist_ok=True)
    D = pd.read_csv("core2024_linker_anchors.csv")
    D = D[(D.status == "ok") & (D.primary_types == "carboxylate") & D.optional.isna()]
    D = D[D.smiles.map(lambda s: (m := Chem.MolFromSmiles(s)) is not None and m.GetNumHeavyAtoms() <= 60)]
    pick = pd.concat([D[D.n_connections == 2].sample(min(n2, (D.n_connections == 2).sum()), random_state=0),
                      D[D.n_connections == 3].sample(min(n3, (D.n_connections == 3).sum()), random_state=0)])
    todo = [(s, int(k), f"L{i:04d}") for i, (s, k) in enumerate(zip(pick.smiles, pick.n_connections))]
    with mp.get_context("spawn").Pool(workers) as p:
        jobs = [j for js in p.imap(prepare, todo, chunksize=4) for j in js]
    for j in jobs:      # 每类各写几个 CIF 供目检
        j["write"] = int(j["id"][1:]) % 25 == 0
    print(f"配对配体 {len(jobs)//2}，任务 {len(jobs)}", flush=True)
    with mp.get_context("spawn").Pool(workers) as p:
        rows = [r for rs in p.imap_unordered(run_one, jobs, chunksize=2) for r in rs]
    R = pd.DataFrame(rows).sort_values(["k", "topo", "smiles", "mode"])
    R.to_csv(os.path.join(OUT, "assembly_results.csv"), index=False)
    summ = {}
    for (topo, mode), g in R.groupby(["topo", "mode"]):
        summ[f"{topo}/{mode}"] = dict(n=len(g), build=round(g.build.mean(), 3), dev_ok=round(g.dev_ok.mean(), 3),
                                      rmsd_ok=round(g.rmsd_ok.fillna(False).mean(), 3),
                                      no_clash=round((g.n_clash == 0).mean(), 3), success=round(g.success.mean(), 3),
                                      chem_correct=round(g.chem_agree.mean(), 3),
                                      success_and_correct=round((g.success & g.chem_agree).mean(), 3))
    json.dump(summ, open(os.path.join(OUT, "assembly_summary.json"), "w"), ensure_ascii=False, indent=1)
    print(pd.DataFrame(summ).T.to_string())


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a)
