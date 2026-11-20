#!/usr/bin/env python3
"""结构级 novelty 硬核查：候选 CIF vs CSD MOF Collection / CoRE 2024。

- 先按元素集合与晶胞体积预过滤，再用 pymatgen StructureMatcher 比对；
- CSD 用自定义解析（忽略 occupancy），CoRE 用 pymatgen 直接读取；
- 解析结果缓存为 pickle，重复运行不再解析数据库。

用法:
  python3 structure_novelty.py --db csd --db-dir "C:/.../CSD_MOF_Collection" \
      --cif-dir generation/out/cif --mofs V0186_nbo V0177_nbo ... --out csd_matches.csv
  python3 structure_novelty.py --db core --db-dir "C:/.../core2024/cifs" ...
"""
import argparse, glob, os, pickle, re, sys
import pandas as pd
from pymatgen.core import Structure, Lattice
from pymatgen.analysis.structure_matcher import StructureMatcher

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
FLOAT = re.compile(r"\([^)]*\)")


def fnum(x):
    return float(FLOAT.sub("", x))


def parse_cif_loose(path):
    """CSD 风格解析：忽略 occupancy；返回 Structure 或 None。"""
    try:
        t = open(path, errors="ignore").read().splitlines()
        txt = "\n".join(t)
        def g(k):
            m = re.search(r"^_cell_" + k + r"\s+([-0-9.]+)", txt, re.M)
            return float(m.group(1)) if m else None
        a, b, c, al, be, ga = [g(x) for x in ("length_a", "length_b", "length_c",
                                              "angle_alpha", "angle_beta", "angle_gamma")]
        if None in (a, b, c, al, be, ga):
            return None
        cols, atoms, inloop = [], [], False
        for line in t:
            s = line.strip()
            if s == "loop_":
                cols, inloop = [], True; continue
            if inloop and s.startswith("_"):
                cols.append(s); continue
            if inloop and cols and s and not s.startswith("_"):
                if any(x.startswith("_atom_site") for x in cols):
                    p = s.split()
                    if len(p) >= len(cols) and "_atom_site_fract_x" in cols:
                        if "_atom_site_type_symbol" in cols:
                            sym = p[cols.index("_atom_site_type_symbol")]
                        else:
                            sym = re.match(r"[A-Za-z]+", p[cols.index("_atom_site_label")]).group(0)
                        atoms.append((sym, (fnum(p[cols.index("_atom_site_fract_x")]),
                                            fnum(p[cols.index("_atom_site_fract_y")]),
                                            fnum(p[cols.index("_atom_site_fract_z")]))))
                else:
                    inloop = False
        if len(atoms) < 4:
            return None
        lat = Lattice.from_parameters(a, b, c, al, be, ga)
        return Structure(lat, [x[0] for x in atoms], [x[1] for x in atoms],
                         coords_are_cartesian=False)
    except Exception:
        return None


def parse_core(path):
    try:
        s = Structure.from_file(path)
        return s if len(s) >= 4 else None
    except Exception:
        return None


def load_db(db, db_dir, cache):
    if os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    files = glob.glob(os.path.join(db_dir, "**", "*.cif"), recursive=True)
    out = []
    parse = parse_cif_loose if db == "csd" else parse_core
    for i, p in enumerate(files, 1):
        st = parse(p)
        if st is not None:
            out.append((os.path.basename(p), st))
        if i % 2000 == 0:
            print("parsed", i, "/", len(files), flush=True)
    pickle.dump(out, open(cache, "wb"), protocol=4)
    print("db parsed:", len(out), "->", cache, flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=["csd", "core"], required=True)
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--mofs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    cache = a.cache or os.path.join(os.path.dirname(a.out), f"cache_{a.db}.pkl")
    db = load_db(a.db, a.db_dir, cache)

    cands = {m: Structure.from_file(os.path.join(a.cif_dir, m + ".cif")) for m in a.mofs}
    for m, s in cands.items():
        print("candidate", m, s.composition.reduced_formula, round(s.volume, 1))

    matcher = StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10,
                               primitive_cell=True, attempt_supercell=True)
    rows, cov = [], []
    for m, cand in cands.items():
        els = {str(e) for e in cand.composition.elements}
        allowed = els | {"H", "Cl", "Br", "I"}
        metals = els & METALS
        vlo, vhi = cand.volume * 0.1, cand.volume * 10.0
        filt = [(n, s) for n, s in db
                if {str(e) for e in s.composition.elements} <= allowed
                and (metals <= {str(e) for e in s.composition.elements})
                and vlo <= s.volume <= vhi]
        print(m, "filtered", len(filt), flush=True)
        hits, attempted, errors = 0, 0, 0
        for n, s in filt:
            attempted += 1
            try:
                if matcher.fit(cand, s):
                    rows.append(dict(candidate=m, match=n,
                                     match_formula=s.composition.reduced_formula,
                                     match_volume=round(s.volume, 1)))
                    hits += 1
            except Exception:
                errors += 1
        cov.append(dict(candidate=m, db=a.db, db_total=len(db), db_parsed=len(db),
                        filtered=len(filt), attempted=attempted, errors=errors, matches=hits))
        print(m, "matches", hits, "attempted", attempted, "errors", errors, flush=True)
    pd.DataFrame(rows).to_csv(a.out, index=False)
    cov_path = os.path.splitext(a.out)[0] + "_coverage.csv"
    pd.DataFrame(cov).to_csv(cov_path, index=False)
    print("total matches", len(rows), "->", a.out)
    print("coverage ->", cov_path)


if __name__ == "__main__":
    main()
