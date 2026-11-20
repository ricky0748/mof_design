#!/usr/bin/env python3
"""CSD MOF Collection 结构级 novelty 检查（头部候选）。

CSD CIF 的 occupancy 字段会让 pymatgen 解析失败，这里用自定义解析（忽略 occupancy），
按 Cu/羧酸/元素/体积预过滤，再用 StructureMatcher 比对。
"""
import argparse, glob, os, re, sys
import pandas as pd
from pymatgen.core import Structure, Lattice
from pymatgen.analysis.structure_matcher import StructureMatcher

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
fnum = lambda x: float(re.sub(r"\([^)]*\)", "", x))


def parse_csd(path):
    t = open(path, errors="ignore").read().splitlines(); txt = "\n".join(t)
    def g(k):
        m = re.search(r"^_cell_" + k + r"\s+([-0-9.]+)", txt, re.M); return float(m.group(1)) if m else None
    a, b, c, al, be, ga = [g(x) for x in ("length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma")]
    cols, atoms, inloop = [], [], False
    for line in t:
        s = line.strip()
        if s == "loop_": cols, inloop = [], True; continue
        if inloop and s.startswith("_"): cols.append(s); continue
        if inloop and cols and s and not s.startswith("_"):
            if any(x.startswith("_atom_site") for x in cols):
                p = s.split()
                if len(p) >= len(cols) and "_atom_site_fract_x" in cols:
                    sym = p[cols.index("_atom_site_type_symbol")] if "_atom_site_type_symbol" in cols else re.match(r"[A-Za-z]+", p[cols.index("_atom_site_label")]).group(0)
                    atoms.append((sym, (fnum(p[cols.index("_atom_site_fract_x")]),
                                        fnum(p[cols.index("_atom_site_fract_y")]),
                                        fnum(p[cols.index("_atom_site_fract_z")]))))
            else: inloop = False
        elif inloop and s and not s.startswith("_") and not cols: inloop = False
    if not atoms: return None
    lat = Lattice.from_parameters(a, b, c, al, be, ga)
    return Structure(lat, [x[0] for x in atoms], [x[1] for x in atoms], coords_are_cartesian=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csd-dir", default="C:/Users/PC/Desktop/MOF-公开数据库/CSD_MOF_Collection/CSD_MOF_Collection")
    ap.add_argument("--cif-dir", default="C:/Users/PC/Desktop/skills_all/ai_mof/generation/out/cif")
    ap.add_argument("--mofs", nargs="+", default=["V0041_nbo", "V0024_nbo", "V0023_nbo", "V0006_nbo"])
    ap.add_argument("--out", default="C:/Users/PC/Desktop/skills_all/ai_mof/generation/pilot_selection/csd_matches.csv")
    a = ap.parse_args()
    cands = {m: Structure.from_file(os.path.join(a.cif_dir, m + ".cif")) for m in a.mofs}
    cand_els = set().union(*[{str(e) for e in s.composition.elements} for s in cands.values()])
    allowed = cand_els | {"Cl", "Br", "I"}
    vol_lo = min(s.volume for s in cands.values()) * 0.05
    vol_hi = max(s.volume for s in cands.values()) * 20
    print("candidates", list(cands), "allowed elements", sorted(allowed), "volume window", round(vol_lo), round(vol_hi))

    filtered = []
    for p in glob.glob(os.path.join(a.csd_dir, "*.cif")):
        try:
            st = parse_csd(p)
        except Exception:
            continue
        if st is None: continue
        els = {str(e) for e in st.composition.elements}
        if "Cu" not in els or "O" not in els: continue
        if not els <= allowed: continue
        if (els & METALS) != {"Cu"}: continue
        if not (vol_lo <= st.volume <= vol_hi): continue
        filtered.append((os.path.basename(p), st))
    print("filtered CSD structures:", len(filtered))

    matcher = StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10, primitive_cell=True, attempt_supercell=True)
    rows = []
    for m, cand in cands.items():
        hits = 0
        for i, (name, st) in enumerate(filtered, 1):
            try:
                if matcher.fit(cand, st):
                    rows.append(dict(candidate=m, csd=name, csd_formula=st.composition.reduced_formula,
                                     csd_volume=round(st.volume, 1), cand_volume=round(cand.volume, 1)))
                    hits += 1
            except Exception:
                pass
            if i % 500 == 0:
                print(m, i, "/", len(filtered), "hits", hits, flush=True)
        print(m, "done hits", hits, flush=True)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    print("matches", len(rows), "->", a.out)


if __name__ == "__main__":
    main()
