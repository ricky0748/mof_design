"""锚点规则 → patchy 粗粒化自组装体系（HOOMD 5 输入）。

在 mof303/cg_patchy3.py（六位点八面体 + 直链约束，已在 MOF-303 上验证）的基础上做两处泛化：
  1. 配体几何不再手写：由 anchor_rules 的锚点输出自动粗粒化
     - 每个"环体系"（稠环合并）一个 R bead，位于环原子质心
     - 每个连接点 X 一个 C bead，位于 X 处（PORMAKE 约定：被切断键中点）
     - R–R、R–C 键长与 R 上所有邻居对的夹角都取自 3D 构象（键 + 谐振角，与 cg_patchy3 同一写法）
  2. 节点族模板化（中心 M + 方向性位点）
     - rod          Al(OH) 链（MOF-303）：A×2 轴向（成链）+ E×4 赤道；角约束与 cg_patchy3 完全相同
     - paddlewheel  Cu 桨轮：E×4 平面方形 + B×2 轴向惰性位点（代表轴向溶剂封端，只有体积排除）
     - octahedral   Zn4O：E×6 八面体
     paddlewheel/octahedral 额外加相邻位点 90° 角约束（cg_patchy3 的 rod 没有加，保持原样以便复现）

长度单位 σ：用 PZDC 校准，使 PZDC 的 R–C 距离 = 1.2σ（cg_patchy3 的 R0），得 σ ≈ 1.58 Å。
节点尺寸 node_size="real" 时取 PORMAKE 节点构筑块的连接点半径（Zn4O 4.33 Å，桨轮 3.26 Å）；
"patchy3" 时与 cg_patchy3 相同（位点距中心 0.7σ）。

输出 spec.npz（不依赖 hoomd，可在任何地方生成/检查）：粒子、键、角、对势表、运行参数、以及每个粒子属于哪个节点/配体。
"""
import json, sys, os
import numpy as np
import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "anchor_rules"))
from anchor_rules import analyze, Config, _strip_for_export  # noqa: E402

TYPES = ["M", "A", "E", "B", "R", "C"]
SIG = {"M": 1.0, "A": 0.3, "E": 0.3, "B": 0.3, "R": 1.0, "C": 0.5}
PZDC = "OC(=O)c1cc(C(=O)O)[nH]n1"
REAL_NODE_RX = {"paddlewheel": 3.26, "octahedral": 4.33}   # Å，PORMAKE N17 / N16 连接点到中心距离
CONTACT = 0.45        # E–C 吸引（σ=0.4）的平衡距离 ≈ 2^(1/6)·0.4
NODE_FAMILY = {"Al_rod": "rod", "Cu_paddlewheel": "paddlewheel", "Zn_paddlewheel": "paddlewheel", "Zn4O": "octahedral"}


# ---------------------------------------------------------------- 配体粗粒化
def _ring_systems(mh, keep):
    rings = [set(r) & keep for r in mh.GetRingInfo().AtomRings()]
    rings = [r for r in rings if len(r) >= 3]
    merged = []
    for r in rings:
        hit = [m for m in merged if m & r]
        for m in hit:
            merged.remove(m); r |= m
        merged.append(r)
    return merged


def cg_linker_geometry(smi, node, sigma=None):
    """返回 Å 单位的 CG 配体模板：beads=[(type, xyz)], bonds=[(i,j)], angles=[(i,j,k)]（j 为顶点）。"""
    cfg = Config()
    r = analyze(smi, cfg, node=node)
    if r["status"] != "ok" or "_mh" not in r:
        raise ValueError(f"{smi}: 锚点状态 {r['status']}")
    mh, anc = r["_mh"], r["_anchors"]
    pos = mh.GetConformer().GetPositions()
    drop = _strip_for_export(mh, anc, cfg)
    keep = {a.GetIdx() for a in mh.GetAtoms() if a.GetIdx() not in drop and a.GetSymbol() != "H"}
    systems = _ring_systems(mh, keep)
    G = nx.Graph()
    G.add_nodes_from(keep)
    G.add_edges_from((b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mh.GetBonds()
                     if b.GetBeginAtomIdx() in keep and b.GetEndAtomIdx() in keep)
    if not systems:
        systems = [set(keep)]
    owner = {a: k for k, s in enumerate(systems) for a in s}

    def system_of(atom):
        if atom in owner:
            return owner[atom]
        d = nx.single_source_shortest_path_length(G, atom)
        return min((d[a], owner[a]) for a in owner if a in d)[1]

    beads = [("R", pos[sorted(s)].mean(axis=0)) for s in systems]
    bonds, nbr = [], {k: [] for k in range(len(systems))}
    # 环体系之间：存在一条不经过第三个环体系的路径即相连
    for a in range(len(systems)):
        for b in range(a + 1, len(systems)):
            others = set().union(*[systems[c] for c in range(len(systems)) if c not in (a, b)]) if len(systems) > 2 else set()
            H = G.subgraph(keep - others)
            if any(nx.has_path(H, i, j) for i in list(systems[a])[:1] for j in list(systems[b])[:1]):
                bonds.append((a, b)); nbr[a].append(b); nbr[b].append(a)
    for a in anc:
        if not a.primary:
            continue
        for xp, par in zip(a.x_positions, a.x_parent):
            k = len(beads); beads.append(("C", np.array(xp)))
            s = system_of(par); bonds.append((s, k)); nbr[s].append(k)
    angles = [(i, j, k) for j in nbr for ii, i in enumerate(nbr[j]) for k in nbr[j][ii + 1:]]
    out = dict(smiles=smi, node=node, beads=beads, bonds=bonds, angles=angles,
               n_conn=sum(1 for t, _ in beads if t == "C"))
    if sigma:
        out = scale(out, sigma)
    return out


def scale(geo, sigma):
    g = dict(geo)
    g["beads"] = [(t, np.asarray(p) / sigma) for t, p in geo["beads"]]
    c = np.mean([p for _, p in g["beads"]], axis=0)
    g["beads"] = [(t, p - c) for t, p in g["beads"]]
    return g


def calibrate_sigma():
    g = cg_linker_geometry(PZDC, "Al_rod")
    R = [p for t, p in g["beads"] if t == "R"][0]
    return float(np.mean([np.linalg.norm(p - R) for t, p in g["beads"] if t == "C"]) / 1.2)


def patchy3_pzdc():
    """cg_patchy3 原版配体：R + 2C，R0=1.2σ，C-R-C=120°。"""
    th = np.radians(120.0)
    b = [("R", np.zeros(3)), ("C", np.array([1.2, 0, 0])), ("C", np.array([1.2 * np.cos(th), 1.2 * np.sin(th), 0]))]
    return dict(smiles="patchy3_PZDC", node="Al_rod", beads=b, bonds=[(0, 1), (0, 2)], angles=[(1, 0, 2)], n_conn=2)


# ---------------------------------------------------------------- 节点模板
def node_template(family, node_size, sigma):
    if family == "rod" or node_size == "patchy3":
        d, msig = 0.7, 1.0
    else:
        d = REAL_NODE_RX[family] / sigma - CONTACT
        msig = d / 0.7            # 保持 cg_patchy3 的 M 半径 / 位点距离比例
    ex, ey, ez = np.eye(3)
    if family == "rod":
        sites = [("A", d * ez), ("A", -d * ez), ("E", d * ex), ("E", -d * ex), ("E", d * ey), ("E", -d * ey)]
        angles = [(1, 0, 2, "AMA"), (3, 0, 4, "EME"), (5, 0, 6, "EME")]      # 与 cg_patchy3 一致（索引含中心 0）
        n_conn = 4
    else:
        types = ["E"] * 6 if family == "octahedral" else ["E", "E", "E", "E", "B", "B"]
        dirs = [ex, -ex, ey, -ey, ez, -ez]
        sites = [(t, d * v) for t, v in zip(types, dirs)]
        angles = []
        for i in range(6):
            for j in range(i + 1, 6):
                c = float(dirs[i] @ dirs[j])
                angles.append((i + 1, 0, j + 1, "OPP" if c < -0.5 else "ADJ"))
        n_conn = types.count("E")
    return dict(family=family, d=d, m_sigma=msig, sites=sites, angles=angles, n_conn=n_conn)


# ---------------------------------------------------------------- 体系构建
def _rot(rng):
    q = rng.normal(size=4); q /= np.linalg.norm(q); w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _mind(placed, p, L):
    if not placed:
        return 1e9
    d = np.asarray(placed) - p; d -= L * np.round(d / L)
    return float(np.sqrt((d * d).sum(1)).min())


def build(case, n_m, seed, sigma, node_size="real", eps_aa=8.0, eps_ec=20.0, t_high=3.0, t_low=0.4,
          n_steps=200000, n_anneal=200000, dt=0.004, k_link_angle=200.0, k_link_bond=200.0, density_ref=36 / 16.0 ** 3,
          patch="single"):
    """patch="legacy"：与 cg_patchy3 完全相同（E–C 吸引截断 1.5σ）。实测 cg_patchy3 末帧里一个 E 位点可同时吸住 2–4 个 C
    （fix_v3：144 个 E 中 46 个空、36 个多占），"每金属 4 个 C"并不等于"4 个位点各配 1 个"。
    patch="single"：E–C 截断缩到 0.8σ，C–C 体积排除 σ 增到 1.45（接触距离 1.63 > 2×0.8），使每个 E 位点只能配 1 个 C。"""
    lig = case["linker"]
    node = node_template(case["family"], node_size, sigma)
    k = lig["n_conn"]
    if (n_m * node["n_conn"]) % k:
        raise ValueError("化学计量不整除：调整 n_m")
    n_l = n_m * node["n_conn"] // k
    # 盒子：保持 cg_patchy3 的"重复单元长度"密度。单元长度 = 节点有效半径(d + 0.45) + 配体半跨度；
    # cg_patchy3：0.7 + 0.45 + 1.04 = 2.19σ，36 节点 / 16³
    C = np.array([p for t, p in lig["beads"] if t == "C"])
    span = (max(np.linalg.norm(a - b) for a in C for b in C) / 2 if k == 2
            else max(np.linalg.norm(c - C.mean(0)) for c in C))
    unit = node["d"] + CONTACT + span
    rho = density_ref * (2.19 / unit) ** 3
    L = float((n_m / rho) ** (1 / 3))
    rng = np.random.default_rng(seed)
    pos, typ, bonds, angles, owner, kind = [], [], [], [], [], []
    bond_types, angle_types = ["MP"], ["AMA", "EME", "OPP", "ADJ"]
    bond_par = {"MP": dict(k=500.0, r0=node["d"])}
    angle_par = {"AMA": dict(k=300.0, t0=np.pi), "EME": dict(k=200.0, t0=np.pi),
                 "OPP": dict(k=200.0, t0=np.pi), "ADJ": dict(k=200.0, t0=np.pi / 2)}
    # 配体键/角类型
    lb, la = [], []
    for i, j in lig["bonds"]:
        name = f"L{len(bond_types)}"; bond_types.append(name)
        bond_par[name] = dict(k=k_link_bond, r0=float(np.linalg.norm(lig["beads"][i][1] - lig["beads"][j][1]))); lb.append(name)
    for i, j, kk in lig["angles"]:
        v1 = lig["beads"][i][1] - lig["beads"][j][1]; v2 = lig["beads"][kk][1] - lig["beads"][j][1]
        t0 = float(np.arccos(np.clip(v1 @ v2 / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1)))
        name = f"T{len(angle_types)}"; angle_types.append(name); angle_par[name] = dict(k=k_link_angle, t0=t0); la.append(name)
    half = L / 2
    minsep_m = 1.5 * node["m_sigma"]; minsep_l = 0.7
    placed, placed_C = [], []
    minsep_cc = 1.45 if patch == "single" else 0.0     # 单占位模式下 C–C 体积排除变大，初始放置要避开

    def add(t, p, o, kd):
        pos.append(p); typ.append(TYPES.index(t)); placed.append(np.asarray(p)); owner.append(o); kind.append(kd)
        return len(pos) - 1

    for m in range(n_m):
        for _ in range(8000):
            c = rng.uniform(-half + 1.0, half - 1.0, 3)
            if _mind(placed, c, L) > minsep_m:
                break
        R = _rot(rng)
        ci = add("M", c, m, 0)
        idx = [ci] + [add(t, c + R @ v, m, 0) for t, v in node["sites"]]
        bonds += [(ci, i, "MP") for i in idx[1:]]
        angles += [(idx[a], idx[b], idx[cc], t) for a, b, cc, t in node["angles"]]
    for l in range(n_l):
        for _ in range(8000):
            c = rng.uniform(-half + 1.2, half - 1.2, 3); R = _rot(rng)
            P = [c + R @ p for _, p in lig["beads"]]
            if all(_mind(placed, p, L) > minsep_l for p in P) and \
                    all(_mind(placed_C, p, L) > minsep_cc for (t, _), p in zip(lig["beads"], P) if t == "C"):
                break
        else:
            raise RuntimeError("配体放不下：降低密度或减少节点数")
        placed_C += [p for (t, _), p in zip(lig["beads"], P) if t == "C"]
        idx = [add(t, p, n_m + l, 1) for (t, _), p in zip(lig["beads"], P)]
        bonds += [(idx[i], idx[j], n) for (i, j), n in zip(lig["bonds"], lb)]
        angles += [(idx[i], idx[j], idx[kk], n) for (i, j, kk), n in zip(lig["angles"], la)]
    P = np.array(pos); P -= L * np.round(P / L)          # 折回盒内
    sig = dict(SIG, M=node["m_sigma"])
    if patch == "legacy":
        pair = dict(sigma=sig, attract=[["A", "A", eps_aa, 0.4, 1.5], ["E", "C", eps_ec, 0.4, 1.5]], repulse=[])
    else:
        pair = dict(sigma=sig, attract=[["A", "A", eps_aa, 0.4, 1.5], ["E", "C", eps_ec, 0.4, 0.8]], repulse=[["C", "C", 1.45]])
    meta = dict(patch=patch, case=case["name"], smiles=lig["smiles"], node=lig["node"], family=node["family"], node_size=node_size,
                sigma_A=sigma, n_m=n_m, n_l=n_l, L=L, seed=seed, node_d=node["d"], node_conn=node["n_conn"], linker_conn=k,
                bond_types=bond_types, bond_par=bond_par, angle_types=angle_types,
                angle_par={a: dict(k=v["k"], t0=v["t0"]) for a, v in angle_par.items()},
                pair=pair, run=dict(t_high=t_high, t_low=t_low, n_steps=n_steps, n_anneal=n_anneal, dt=dt))
    return dict(position=P, typeid=np.array(typ, dtype=np.uint32), types=np.array(TYPES),
                bond_group=np.array([(a, b) for a, b, _ in bonds], dtype=np.uint32),
                bond_typeid=np.array([bond_types.index(t) for *_, t in bonds], dtype=np.uint32),
                angle_group=np.array([(a, b, c) for a, b, c, _ in angles], dtype=np.uint32),
                angle_typeid=np.array([angle_types.index(t) for *_, t in angles], dtype=np.uint32),
                owner=np.array(owner), kind=np.array(kind), meta=np.array(json.dumps(meta, ensure_ascii=False)))
