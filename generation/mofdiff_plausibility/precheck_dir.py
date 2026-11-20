#!/usr/bin/env python3
"""不依赖 UFF/LAMMPS 的结构预筛查：原子重叠、连通片段、金属配位、组成。

用法: python precheck_dir.py <cif_dir> <out.csv> [--tag name]
"""
import os
import sys
import csv
import numpy as np
from ase.io import read
from ase.neighborlist import natural_cutoffs, NeighborList
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
DONORS = {"O", "N", "S"}


def fragments(atoms):
    cut = natural_cutoffs(atoms, mult=1.15)
    nl = NeighborList(cut, self_interaction=False, bothways=True)
    nl.update(atoms)
    m = nl.get_connectivity_matrix(sparse=True).tocsr()
    n, lab = connected_components(m, directed=False)
    sizes = sorted(np.bincount(lab).tolist(), reverse=True)
    return int(n), sizes


def one(path, name):
    try:
        a = read(path)
    except Exception as e:  # noqa
        return dict(name=name, error=f"read: {e}"[:100])
    syms = a.get_chemical_symbols()
    d = a.get_all_distances(mic=True)
    np.fill_diagonal(d, np.inf)
    tri = np.triu(np.ones_like(d, dtype=bool), 1)
    vals = d[tri]
    nfrag, sizes = fragments(a)
    donors = [i for i, s in enumerate(syms) if s in DONORS]
    metals = [i for i, s in enumerate(syms) if s in METALS]
    cns = []
    for m in metals:
        if donors:
            cns.append(int((d[m, donors] < 2.6).sum()))
    return dict(
        name=name, natoms=len(a), formula=a.get_chemical_formula(),
        V=round(float(a.get_volume()), 1),
        dmin=round(float(vals.min()), 3),
        pairs_lt_09=int((vals < 0.9).sum()),
        pairs_lt_07=int((vals < 0.7).sum()),
        n_fragments=nfrag,
        largest_fragment=sizes[0] if sizes else 0,
        frag_sizes=";".join(map(str, sizes[:5])),
        n_metals=len(metals),
        metal_cn_min=int(min(cns)) if cns else None,
        metal_cn_max=int(max(cns)) if cns else None,
        clean_geom=bool(vals.min() >= 0.9 and nfrag == 1),
        error="",
    )


def main():
    d = sys.argv[1]
    out = sys.argv[2]
    tag = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--tag" else os.path.basename(os.path.normpath(d))
    rows = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".cif"):
            continue
        name = f[:-4]
        r = one(os.path.join(d, f), name)
        r["engine"] = tag
        rows.append(r)
    cols = ["engine", "name", "natoms", "formula", "V", "dmin", "pairs_lt_09", "pairs_lt_07",
            "n_fragments", "largest_fragment", "frag_sizes", "n_metals",
            "metal_cn_min", "metal_cn_max", "clean_geom", "error"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    ok = sum(1 for r in rows if r.get("clean_geom"))
    print(f"{tag}: {len(rows)} CIF, clean_geom {ok} ({ok/max(1,len(rows)):.1%}) -> {out}")


if __name__ == "__main__":
    main()
