"""配位基团类型化的锚点规则（第一版：羧酸、唑类、吡啶）。

为什么要有这个模块
------------------
Nexerra 把配位基团抽象成 [Lr] 占位符，锚点按"平均两两距离最大的一组 H"纯几何选取。
这样会丢掉两样东西：锚点是什么化学基团（决定开放金属位、孔口化学），以及锚点能不能是 N 给体
（几何规则只能在 C–H 上放锚点）。本模块按 SMARTS 识别配位基团，给每个锚点打上类型标签，
算出连接方向，并按 ToBaCCo 约定导出带 X 连接点的构筑块。

约定（可在 Config 里改）
------------------------
- 羧酸 carboxylate_in_node=True（默认，ToBaCCo / CoRE MOFid 的常用拆法）：
  羧基 C 归节点，配体在"芳环 C–羧基 C"处切断，X 放在原羧基 C 的位置。
  =False 时羧基保留在配体上，X 放在两个 O 外侧的金属位置（单齿/桥连都画成一个 X，位于 O–O 中点外推 2.0 Å）。
- N 给体（唑、吡啶）：不切断，X 放在给体 N 的孤对方向上，距 N 为 m_n_dist（默认 2.0 Å，典型 M–N 键长）。
- 吡唑 pyrazolate_single_x=False（默认）：两个相邻 N 各放一个 X（外双齿桥连两个金属）；
  =True 时只在 N–N 中点外推放一个 X（把整个吡唑当作连到一个棒状/簇节点的一个连接）。
- 规则有优先级：四唑 > 三唑 > 吡唑/咪唑 > 羧酸 > 吡啶。已被高优先级规则认领的原子不会被再匹配。
- "主锚点"决定配体的连接数（topicity）。吡啶类 N 在分子里同时存在羧酸或唑时降为"可选给体"
  （例如吡啶二甲酸里的 N 常常不配位），只有纯吡啶类配体（联吡啶柱撑等）才把吡啶 N 算作主锚点。
"""
from __future__ import annotations

import itertools, json, math
from dataclasses import dataclass, field, asdict

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem

RDLogger = __import__("rdkit.RDLogger", fromlist=["RDLogger"])
RDLogger.DisableLog("rdApp.*")


# ---------------------------------------------------------------- 规则表
# donors: SMARTS 映射号中作为配位原子的编号；attach: 切断时配体一侧保留的原子；cut: 被切掉（归节点）的原子
RULES = [
    # 唑类 SMARTS 不依赖芳香性（CoRE/MOFid 常把唑负离子写成带自由基的非芳香 Kekulé 式，如 C1=C[N]C=N1）。
    # 环上 C 要求非 sp3（!X4），排除咪唑烷等饱和环。
    dict(name="tetrazolate", family="azolate", priority=10,
         smarts="[#7:1]1~[#7:2]~[#7:3]~[#7:4]~[#6;!X4:5]~1", donors=[1, 2, 3, 4], default_donors=[2, 3],
         note="5-取代四唑；默认取远离取代基的 N2、N3 作外双齿（M-BTT 类常见桥连方式），N1、N4 记为可选"),
    dict(name="1,2,4-triazolate", family="azolate", priority=9,
         smarts="[#7:1]1~[#7:2]~[#6;!X4:3]~[#7:4]~[#6;!X4:5]~1", donors=[1, 2, 4], default_donors=[1, 2, 4],
         note="1,2,4-三唑，三个 N 都可配位（如 CALF-20、MAF 系列）"),
    dict(name="1,2,3-triazolate", family="azolate", priority=9,
         smarts="[#7:1]1~[#7:2]~[#7:3]~[#6;!X4:4]~[#6;!X4:5]~1", donors=[1, 2, 3], default_donors=[1, 3],
         note="1,2,3-三唑及苯并三唑；默认取 N1、N3"),
    dict(name="pyrazolate", family="azolate", priority=8,
         smarts="[#7:1]1~[#7:2]~[#6;!X4:3]~[#6;!X4:4]~[#6;!X4:5]~1", donors=[1, 2], default_donors=[1, 2],
         note="吡唑，相邻两 N 外双齿桥连（如 MOF-303 的 PZDC、Ni/Co 吡唑盐）"),
    dict(name="imidazolate", family="azolate", priority=8,
         smarts="[#7:1]1~[#6;!X4:2]~[#7:3]~[#6;!X4:4]~[#6;!X4:5]~1", donors=[1, 3], default_donors=[1, 3],
         note="咪唑（含苯并咪唑），1,3 位 N 各配一个金属（ZIF）"),
    dict(name="carboxylate", family="carboxylate", priority=5,
         smarts="[#6:9]-[CX3:8](=[OX1:1])-[OX2H1,OX1-,OX1:2]", donors=[1, 2], default_donors=[1, 2],
         attach=9, cut=8, note="羧酸/羧酸根（含 MOFid 里的 [O] 写法）"),
    dict(name="pyridyl", family="pyridyl", priority=3,
         smarts="[#7X2;r6;!$([#7]~[#7]);!$([#7+]):1]", donors=[1], default_donors=[1],
         note="六元环 sp2 N（吡啶、联吡啶、吡嗪、嘧啶）；与羧基处于邻位时视为螯合，降为可选给体"),
]

# 已知但第一版未实现、校验时单独统计的给体类型（扩展时把规则加进 RULES 即可）
TODO_CLASSES = {
    "phosphonate": "[PX4](=O)([OX2H1,OX1-,OX1])[OX2H1,OX1-,OX1]",
    "sulfonate": "[SX4](=O)(=O)[OX2H1,OX1-,OX1]",
    "N-oxide": "[#7+]-[O-]",
    "aliphatic_amine_pillar": "[NX3;!$(N-C=O);!$(N-a);R]",
    "phenolate/catecholate": "c[OX2H1,OX1-,OX1]",
    "nitrile": "C#N",
}

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Cs Ba "
             "La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po Fr Ra Ac Th Pa U Np Pu".split())

# 节点族与可接受的主锚点类型（用于兼容性检查；可扩展）
NODE_COMPAT = {
    "Zn4O": {"carboxylate"}, "Cu_paddlewheel": {"carboxylate"}, "Zn_paddlewheel": {"carboxylate"},
    "Zr6": {"carboxylate"}, "Al_rod": {"carboxylate"}, "M3O_trimer": {"carboxylate"},
    "M_tetrahedral_ZIF": {"imidazolate"}, "Cu_pyrazolate": {"pyrazolate"},
    "M_triazolate": {"1,2,4-triazolate", "1,2,3-triazolate"}, "pillar_N": {"pyridyl"},
}


@dataclass
class Config:
    carboxylate_in_node: bool = True
    m_n_dist: float = 2.0        # N 给体到 X 的距离 (Å)
    m_o_dist: float = 2.0        # 羧酸保留在配体时 O–O 中点到 X 的外推距离 (Å)
    pyrazolate_single_x: bool = False
    seed: int = 7
    x_convention: str = "pormake"   # "pormake": X 在被切断键的中点（羧酸 X 距芳环 C ≈0.74 Å；N 给体 X 距 N = m_n_dist/2），
                                     # 组装时两侧 X 重合；"tobacco_atom": X 占据被切掉原子的位置（羧基 C 处；N 给体 X 距 N = m_n_dist）


@dataclass
class Anchor:
    rule: str
    family: str
    donors: list            # 原子索引（配位原子）
    optional_donors: list
    primary: bool
    attach: int | None = None
    cut: int | None = None
    x_positions: list = field(default_factory=list)   # 每个 X 的坐标
    x_parent: list = field(default_factory=list)      # 每个 X 键连到的配体原子索引


# ---------------------------------------------------------------- 预处理
def normalize_smiles(smi: str) -> Chem.Mol | None:
    """把 MOFid 里的去质子化/自由基写法尽量还原成中性分子。依次尝试：
    ① 只中和 O（[O-]、[O] → OH）；② 同时中和 N/S 负离子；③ 原样解析。取第一个能通过 RDKit 校验的结果。"""
    def attempt(fix_n):
        m = Chem.MolFromSmiles(smi, sanitize=False)
        if m is None:
            return None
        for a in m.GetAtoms():
            sym = a.GetSymbol()
            if a.GetFormalCharge() < 0 and (sym == "O" or (fix_n and sym in ("N", "S"))):
                a.SetFormalCharge(0); a.SetNumExplicitHs(a.GetNumExplicitHs() + 1); a.SetNoImplicit(False)
            if sym == "O" and a.GetFormalCharge() == 0 and a.GetNoImplicit() and a.GetNumExplicitHs() == 0 and a.GetDegree() == 1:
                a.SetNoImplicit(False)
        try:
            Chem.SanitizeMol(m); return m
        except Exception:
            return None
    def attempt_tautomer():
        """唑环 N 上的 H/电荷写法自相矛盾时（如 [nH][n-]）：清空芳香 N 的 H 与电荷，再逐个尝试给哪些 N 补 H。"""
        base = Chem.MolFromSmiles(smi, sanitize=False)
        if base is None:
            return None
        arn = [a.GetIdx() for a in base.GetAtoms() if a.GetSymbol() == "N" and a.GetIsAromatic()]
        for k in range(0, min(len(arn), 4) + 1):
            for combo in itertools.combinations(arn, k):
                m = Chem.RWMol(base)
                for a in m.GetAtoms():
                    if a.GetSymbol() == "O" and a.GetFormalCharge() < 0:
                        a.SetFormalCharge(0); a.SetNumExplicitHs(1)
                    if a.GetSymbol() == "O" and a.GetNoImplicit() and a.GetNumExplicitHs() == 0 and a.GetDegree() == 1:
                        a.SetNoImplicit(False)
                for i in arn:
                    a = m.GetAtomWithIdx(i); a.SetFormalCharge(0); a.SetNumExplicitHs(1 if i in combo else 0); a.SetNoImplicit(True)
                try:
                    mm = m.GetMol(); Chem.SanitizeMol(mm); return mm
                except Exception:
                    continue
        return None

    def attempt_string_fix():
        """MOFid 偶尔写出 =[N]= 这类超价写法（如三嗪）；退化为普通 N 再解析（仅为识别给体，键级可能不准）。"""
        s2 = smi.replace("=[N]=", "=N").replace("[N]", "N")
        m = Chem.MolFromSmiles(s2)
        return m

    for f in (lambda: attempt(False), lambda: attempt(True), lambda: Chem.MolFromSmiles(smi), attempt_tautomer,
              attempt_string_fix):
        m = f()
        if m is not None:
            return m
    return None


def is_organic(smi: str) -> bool:
    syms = {a.GetSymbol() for a in (Chem.MolFromSmiles(smi, sanitize=False) or Chem.Mol()).GetAtoms()}
    return bool(syms) and not (syms & METALS) and "C" in syms


# ---------------------------------------------------------------- 识别
_COMPILED = [(r, Chem.MolFromSmarts(r["smarts"])) for r in sorted(RULES, key=lambda r: -r["priority"])]


def find_anchors(mol: Chem.Mol, cfg: Config = Config()) -> list[Anchor]:
    claimed, anchors = set(), []
    for r, patt in _COMPILED:
        mapidx = {a.GetAtomMapNum(): a.GetIdx() for a in patt.GetAtoms() if a.GetAtomMapNum()}
        for match in mol.GetSubstructMatches(patt, uniquify=True):
            atoms = {k: match[i] for k, i in mapidx.items()}
            donors = [atoms[k] for k in r["default_donors"]]
            optional = [atoms[k] for k in r["donors"] if k not in r["default_donors"]]
            core = set(donors + optional + ([atoms[r["cut"]]] if "cut" in r else []))
            if core & claimed:
                continue
            claimed |= core
            anchors.append(Anchor(rule=r["name"], family=r["family"], donors=donors, optional_donors=optional,
                                  primary=True, attach=atoms.get(r.get("attach")), cut=atoms.get(r.get("cut"))))
    # 吡啶 N 与羧基邻位（吡啶甲酸、2,6-吡啶二甲酸）→ 螯合，降为可选给体；其余吡啶 N 保留为主锚点
    carb_attach = {a.attach for a in anchors if a.family == "carboxylate"}
    for a in anchors:
        if a.family == "pyridyl":
            nbrs = {n.GetIdx() for n in mol.GetAtomWithIdx(a.donors[0]).GetNeighbors()}
            if nbrs & carb_attach:
                a.primary = False
    return anchors


# ---------------------------------------------------------------- 3D 与 X 放置
def embed(mol: Chem.Mol, seed=7) -> Chem.Mol | None:
    mh = Chem.AddHs(mol)
    p = AllChem.ETKDGv3(); p.randomSeed = seed; p.maxIterations = 200; p.timeout = 20
    if AllChem.EmbedMolecule(mh, p) != 0:
        p.useRandomCoords = True
        if AllChem.EmbedMolecule(mh, p) != 0:
            return None
    try:
        AllChem.MMFFOptimizeMolecule(mh, maxIters=500)
    except Exception:
        pass
    return mh


def _lonepair_dir(pos, mol, idx):
    a = mol.GetAtomWithIdx(idx)
    nb = [pos[n.GetIdx()] for n in a.GetNeighbors() if n.GetSymbol() != "H"]
    v = pos[idx] - np.mean(nb, axis=0)
    return v / (np.linalg.norm(v) + 1e-12)


def place_x(mh: Chem.Mol, anchors: list[Anchor], cfg: Config = Config()):
    pos = mh.GetConformer().GetPositions()
    for a in anchors:
        f = 0.5 if cfg.x_convention == "pormake" else 1.0
        if a.family == "carboxylate":
            if cfg.carboxylate_in_node:
                a.x_positions = [(pos[a.attach] + f * (pos[a.cut] - pos[a.attach])).tolist()]; a.x_parent = [a.attach]
            else:
                mid = (pos[a.donors[0]] + pos[a.donors[1]]) / 2
                v = mid - pos[a.cut]; v /= np.linalg.norm(v)
                a.x_positions = [(mid + f * cfg.m_o_dist * v).tolist()]; a.x_parent = [a.donors[0]]
        elif a.rule == "pyrazolate" and cfg.pyrazolate_single_x:
            d = (_lonepair_dir(pos, mh, a.donors[0]) + _lonepair_dir(pos, mh, a.donors[1])); d /= np.linalg.norm(d)
            mid = (pos[a.donors[0]] + pos[a.donors[1]]) / 2
            a.x_positions = [(mid + f * cfg.m_n_dist * d).tolist()]; a.x_parent = [a.donors[0]]
        else:
            a.x_positions = [(pos[i] + f * cfg.m_n_dist * _lonepair_dir(pos, mh, i)).tolist() for i in a.donors]
            a.x_parent = list(a.donors)
    return anchors


# ---------------------------------------------------------------- 几何描述与兼容性
def geometry_summary(mh, anchors):
    """n_groups = 主锚点基团数；n_connections = X 连接点数（唑类每个给体 N 一个 X，羧酸一个基团一个 X）。
    形状：基团数 ≥2 时用每个基团的 X 均值点；只有 1 个基团（如咪唑、三唑本身就是连接体）时用各 X 点。"""
    prim = [a for a in anchors if a.primary]
    pts = [np.mean(a.x_positions, axis=0) for a in prim]
    if len(pts) < 2:
        pts = [np.array(p) for a in prim for p in a.x_positions]
    out = dict(n_groups=len(prim), n_connections=sum(len(a.x_positions) for a in prim),
               anchor_types=sorted({a.rule for a in prim}))
    out["topicity"] = len(pts)
    if len(pts) >= 2:
        c = np.mean(pts, axis=0)
        vec = [(p - c) / (np.linalg.norm(p - c) + 1e-12) for p in pts]
        pairs = list(itertools.combinations(range(len(pts)), 2))
        ang = [math.degrees(math.acos(np.clip(np.dot(vec[i], vec[j]), -1, 1))) for i, j in pairs]
        dist = [float(np.linalg.norm(pts[i] - pts[j])) for i, j in pairs]
        out.update(max_anchor_dist=round(max(dist), 2), min_anchor_dist=round(min(dist), 2), anchor_angles=[round(x, 1) for x in ang])
        if len(pts) == 2:
            # 两点相对质心永远 180°，改用连接方向（X − 母原子）的夹角：反向平行=直线型
            pos = mh.GetConformer().GetPositions()
            if len(prim) >= 2:
                dirs = [np.mean([np.array(x) - pos[p] for x, p in zip(a.x_positions, a.x_parent)], axis=0) for a in prim]
            else:
                dirs = [np.array(x) - pos[p] for x, p in zip(prim[0].x_positions, prim[0].x_parent)]
            d0, d1 = [d / np.linalg.norm(d) for d in dirs[:2]]
            ca = math.degrees(math.acos(np.clip(np.dot(d0, d1), -1, 1)))
            out["anchor_angles"] = [round(ca, 1)]
            out["shape"] = "linear" if ca >= 160 else "bent"
        elif len(pts) == 3:
            nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0]); nrm /= (np.linalg.norm(nrm) + 1e-12)
            out["shape"] = "trigonal_planar" if all(abs(np.dot(nrm, v)) < 0.25 for v in vec) else "tripodal"
        elif len(pts) == 4:
            nrm = np.linalg.svd(np.array(pts) - c)[2][-1]
            out["shape"] = "square_planar_like" if all(abs(np.dot(nrm, v)) < 0.25 for v in vec) else "tetrahedral_like"
        else:
            out["shape"] = f"{len(pts)}-c"
    return out


def compatible(anchors, node: str) -> bool:
    ok = NODE_COMPAT.get(node)
    prim = {a.rule for a in anchors if a.primary}
    return bool(ok) and bool(prim) and prim <= ok


# ---------------------------------------------------------------- 导出
def to_lr_smiles(mol: Chem.Mol, anchors: list[Anchor], cfg: Config = Config()) -> str:
    """Nexerra / EGMOF 风格的 [Lr] 占位符 SMILES（羧酸切掉换成 [Lr]；N 给体在 N 上挂 [Lr]——仅用于交换，化学上不严格）。"""
    rw = Chem.RWMol(mol)
    to_remove = []
    for a in anchors:
        if not a.primary:
            continue
        if a.family == "carboxylate" and cfg.carboxylate_in_node:
            at = rw.GetAtomWithIdx(a.attach); at.SetNumExplicitHs(0); at.SetNoImplicit(True)
            lr = rw.AddAtom(Chem.Atom(103)); rw.AddBond(a.attach, lr, Chem.BondType.SINGLE)
            to_remove += [a.cut] + [n.GetIdx() for n in mol.GetAtomWithIdx(a.cut).GetNeighbors() if n.GetSymbol() == "O"]
        else:
            for d in a.donors:
                at = rw.GetAtomWithIdx(d); at.SetNumExplicitHs(0); at.SetNoImplicit(True)
                lr = rw.AddAtom(Chem.Atom(103)); rw.AddBond(d, lr, Chem.BondType.SINGLE)
    for i in sorted(set(to_remove), reverse=True):
        rw.RemoveAtom(i)
    m = rw.GetMol()
    try:
        Chem.SanitizeMol(m)
    except Exception:
        pass
    return Chem.MolToSmiles(m)


def to_tobacco_cif(mh: Chem.Mol, anchors: list[Anchor], name: str, cfg: Config = Config(), box_pad=15.0) -> str:
    """ToBaCCo 风格构筑块 CIF：P1 大盒子、笛卡尔转分数坐标、X 为连接点，附 _geom_bond 键表。
    羧酸 in_node 模式下，羧基 C/O 和与之相连的 H 被删除，X 占据原羧基 C 位置。"""
    pos = mh.GetConformer().GetPositions()
    drop = set()
    for a in anchors:
        if a.family == "carboxylate" and cfg.carboxylate_in_node and a.primary:
            drop.add(a.cut)
            for n in mh.GetAtomWithIdx(a.cut).GetNeighbors():
                if n.GetSymbol() == "O":
                    drop.add(n.GetIdx()); drop |= {h.GetIdx() for h in n.GetNeighbors() if h.GetSymbol() == "H"}
    # 唑类 NH 的 H 是去质子化位点，也删掉
    for a in anchors:
        if a.family == "azolate" and a.primary:
            for d in a.donors + a.optional_donors:
                drop |= {h.GetIdx() for h in mh.GetAtomWithIdx(d).GetNeighbors() if h.GetSymbol() == "H"}
    keep = [i for i in range(mh.GetNumAtoms()) if i not in drop]
    xs = [(p, par) for a in anchors if a.primary for p, par in zip(a.x_positions, a.x_parent)]
    allpos = np.array([pos[i] for i in keep] + [p for p, _ in xs])
    L = allpos.max(0) - allpos.min(0) + box_pad
    shift = -allpos.min(0) + box_pad / 2
    label, lines, newidx = {}, [], {}
    counts = {}
    for i in keep:
        s = mh.GetAtomWithIdx(i).GetSymbol(); counts[s] = counts.get(s, 0) + 1
        label[i] = f"{s}{counts[s]}"; f = (pos[i] + shift) / L
        lines.append(f"{label[i]:6s} {s:3s} {f[0]:.6f} {f[1]:.6f} {f[2]:.6f}")
    xlab = []
    for k, (p, par) in enumerate(xs, 1):
        f = (np.array(p) + shift) / L; xlab.append((f"X{k}", par))
        lines.append(f"X{k:<5d} X   {f[0]:.6f} {f[1]:.6f} {f[2]:.6f}")
    bonds = []
    for b in mh.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in label and j in label:
            t = {1.0: "S", 2.0: "D", 3.0: "T", 1.5: "A"}.get(b.GetBondTypeAsDouble(), "S")
            bonds.append((label[i], label[j], float(np.linalg.norm(pos[i] - pos[j])), t))
    for xl, par in xlab:
        p = next(pp for pp, q in xs if q == par)
        bonds.append((label[par], xl, float(np.linalg.norm(pos[par] - np.array(p))), "S"))
    out = [f"data_{name}", "_symmetry_space_group_name_H-M    'P1'", "_symmetry_Int_Tables_number       1",
           f"_cell_length_a                    {L[0]:.4f}", f"_cell_length_b                    {L[1]:.4f}",
           f"_cell_length_c                    {L[2]:.4f}", "_cell_angle_alpha                 90.0000",
           "_cell_angle_beta                  90.0000", "_cell_angle_gamma                 90.0000",
           "loop_", "_symmetry_equiv_pos_as_xyz", "  x,y,z",
           "loop_", "_atom_site_label", "_atom_site_type_symbol", "_atom_site_fract_x", "_atom_site_fract_y",
           "_atom_site_fract_z"] + lines + [
           "loop_", "_geom_bond_atom_site_label_1", "_geom_bond_atom_site_label_2", "_geom_bond_distance",
           "_geom_bond_site_symmetry_2", "_ccdc_geom_bond_type"]
    out += [f"{a:6s} {b:6s} {d:.3f} . {t}" for a, b, d, t in bonds]
    return "\n".join(out) + "\n"


def _strip_for_export(mh, anchors, cfg):
    """导出前要删掉的原子：in_node 模式下的羧基 C/O/OH 上的 H，以及唑类给体 N 上的 H（去质子化位点）。"""
    drop = set()
    for a in anchors:
        if not a.primary:
            continue
        if a.family == "carboxylate" and cfg.carboxylate_in_node:
            drop.add(a.cut)
            for n in mh.GetAtomWithIdx(a.cut).GetNeighbors():
                if n.GetSymbol() == "O":
                    drop.add(n.GetIdx()); drop |= {h.GetIdx() for h in n.GetNeighbors() if h.GetSymbol() == "H"}
        if a.family == "azolate":
            for d in a.donors + a.optional_donors:
                drop |= {h.GetIdx() for h in mh.GetAtomWithIdx(d).GetNeighbors() if h.GetSymbol() == "H"}
    return drop


def to_pormake_xyz(mh, anchors, cfg: Config = Config()) -> str:
    """PORMAKE 构筑块格式：第 1 行原子数；第 2 行连接点 X 的 0 起索引；原子行；键行 "i j 类型(S/D/T/A)"。"""
    pos = mh.GetConformer().GetPositions()
    drop = _strip_for_export(mh, anchors, cfg)
    keep = [i for i in range(mh.GetNumAtoms()) if i not in drop]
    new = {old: k for k, old in enumerate(keep)}
    atoms = [(mh.GetAtomWithIdx(i).GetSymbol(), pos[i]) for i in keep]
    xs = [(np.array(p), par) for a in anchors if a.primary for p, par in zip(a.x_positions, a.x_parent)]
    xidx = list(range(len(atoms), len(atoms) + len(xs)))
    atoms += [("X", p) for p, _ in xs]
    bonds = []
    for b in mh.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in new and j in new:
            t = {1.0: "S", 2.0: "D", 3.0: "T", 1.5: "A"}.get(b.GetBondTypeAsDouble(), "S")
            bonds.append((new[i], new[j], t))
    for k, (_, par) in zip(xidx, xs):
        bonds.append((new[par], k, "S"))
    out = [str(len(atoms)), " ".join(f"{k:4d}" for k in xidx)]
    out += [f"{s:3s} {p[0]:10.4f} {p[1]:10.4f} {p[2]:10.4f}" for s, p in atoms]
    out += [f"{i:4d} {j:4d} {t}" for i, j, t in bonds]
    return "\n".join(out) + "\n"


def to_he_xyz(mh, anchors, comment="") -> str:
    """LEGO-MOF 风格：保留全部配体原子，在每个 X 位置放虚拟 He。"""
    pos = mh.GetConformer().GetPositions()
    rows = [(a.GetSymbol(), pos[a.GetIdx()]) for a in mh.GetAtoms()]
    rows += [("He", np.array(p)) for a in anchors if a.primary for p in a.x_positions]
    return f"{len(rows)}\n{comment}\n" + "\n".join(f"{s} {x:.4f} {y:.4f} {z:.4f}" for s, (x, y, z) in rows) + "\n"


# ---------------------------------------------------------------- 一站式
def apply_node(anchors: list[Anchor], node: str | None) -> list[Anchor]:
    """按目标节点族重新指定主锚点：节点能接受的基团才是主锚点，其余基团不配位、留在孔道里（记为 pore_groups）。
    例：MOF-303 的 PZDC 在 Al 棒节点下只有两个羧基配位，吡唑 NH 朝向孔道——这正是它吸水/吸甲醛的关键位点。"""
    if not node:
        return anchors
    ok = NODE_COMPAT[node]
    for a in anchors:
        a.primary = a.rule in ok
    return anchors


def analyze(smi: str, cfg: Config = Config(), embed3d=True, node: str | None = None) -> dict:
    mol = normalize_smiles(smi)
    if mol is None:
        return dict(smiles=smi, status="parse_failed", primary_types=[], optional=[], n_connections_est=0, lr_smiles="")
    anchors = apply_node(find_anchors(mol, cfg), node)
    res = dict(smiles=smi, canonical=Chem.MolToSmiles(mol), status="ok",
               n_primary=sum(a.primary for a in anchors),
               primary_types=sorted({a.rule for a in anchors if a.primary}),
               optional=sorted({a.rule for a in anchors if not a.primary} |
                               ({a.rule + "(extra N)" for a in anchors if a.optional_donors})),
               node=node, pore_groups=sorted({a.rule for a in anchors if not a.primary}) if node else None)
    res["n_connections_est"] = sum(1 if a.family in ("carboxylate", "pyridyl") or (a.rule == "pyrazolate" and cfg.pyrazolate_single_x)
                                   else len(a.donors) for a in anchors if a.primary)
    if res["n_connections_est"] < 2:
        res["status"] = "lt2_connections"
    if embed3d and res["n_primary"] >= 1:
        mh = embed(mol, cfg.seed)
        if mh is None:
            res["status"] = "embed_failed"
        else:
            # 原子索引在 AddHs 后保持不变（H 加在末尾）
            place_x(mh, anchors, cfg)
            res.update(geometry_summary(mh, anchors))
            res["_mh"], res["_anchors"] = mh, anchors
    res["lr_smiles"] = to_lr_smiles(mol, anchors, cfg) if anchors else ""
    return res


def anchors_json(res) -> str:
    keep = {k: v for k, v in res.items() if not k.startswith("_")}
    keep["anchors"] = [asdict(a) for a in res.get("_anchors", [])]
    return json.dumps(keep, ensure_ascii=False, indent=1)
