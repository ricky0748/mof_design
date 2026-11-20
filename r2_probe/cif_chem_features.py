"""从 CRAFTED DDEC CIF 提取化学/电荷特征（纯 python，无依赖）。"""
import os, csv, statistics as st
ROOT = os.path.expanduser("~/mnt/MOF-公开数据库/CRAFTED-2.0.0")
OUT = os.path.expanduser("~/mnt/ai_mof/r2_probe/chem_features_DDEC.csv")
METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
names = [r["FrameworkName"] for r in csv.DictReader(open(f"{ROOT}/RAC_DBSCAN/CRAFTED_MOF_geometric.csv"))]
rows = []
for n in names:
    lines = open(f"{ROOT}/CIF_FILES/DDEC/{n}.cif").read().splitlines()
    cols, atoms, inloop = [], [], False
    for l in lines:
        s = l.strip()
        if s == "loop_": cols, inloop = [], True; continue
        if inloop and s.startswith("_"): cols.append(s); continue
        if inloop and cols and "_atom_site_charge" in cols and s and not s.startswith("_"):
            t = s.split()
            if len(t) >= len(cols):
                sym = t[cols.index("_atom_site_type_symbol")] if "_atom_site_type_symbol" in cols else "".join(ch for ch in t[cols.index("_atom_site_label")] if ch.isalpha())
                sym = sym[:1].upper() + sym[1:2].lower() if len(sym) > 1 and sym[:2].capitalize() in METALS | {"Cl", "Br"} else sym[:1].upper()
                atoms.append((sym, float(t[cols.index("_atom_site_charge")])))
            continue
        if inloop and cols and s and not s.startswith("_"): inloop = False
    el = [a[0] for a in atoms]; q = [a[1] for a in atoms]; N = len(atoms)
    mq = [c for e, c in atoms if e in METALS]
    metals = sorted({e for e in el if e in METALS})
    frac = lambda S: sum(e in S for e in el) / N
    rows.append(dict(mof=n, natoms=N, metal=metals[0] if metals else "none", n_metal_types=len(metals),
        f_metal=frac(METALS), f_N=frac({"N"}), f_O=frac({"O"}), f_H=frac({"H"}), f_C=frac({"C"}),
        f_hal=frac({"F", "Cl", "Br", "I"}), f_S=frac({"S"}), f_P=frac({"P"}),
        q_absmean=sum(map(abs, q)) / N, q_std=st.pstdev(q), q_max=max(q), q_min=min(q),
        q_metal_mean=(sum(mq) / len(mq)) if mq else 0.0, q_metal_max=max(mq) if mq else 0.0,
        f_q_gt05=sum(abs(c) > 0.5 for c in q) / N, f_q_gt1=sum(abs(c) > 1.0 for c in q) / N))
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows))
