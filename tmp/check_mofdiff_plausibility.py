#!/usr/bin/env python3
"""MOFDiff 头部结构合理性核查：原子重叠、金属配位、PACMOF 电荷、连通性。

用法: python check_mofdiff_plausibility.py <pilot100_dir> <out.json>
"""
import os
import sys
import json
import numpy as np
from ase.io import read
from ase.neighborlist import natural_cutoffs, NeighborList
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

NAMES = ["sample_10", "sample_21", "sample_66", "sample_74", "sample_78", "sample_94"]
METALS = {"Cu", "Zn", "Cr", "V", "Ni", "Ba", "Co", "Fe", "Mn", "Zr", "Al", "Ca", "Mg"}
DONORS = {"O", "N", "S"}


def read_charges(path):
    els, qs = [], []
    in_loop = False
    for line in open(path):
        s = line.strip()
        if s.startswith("_atom_site_charge"):
            in_loop = True
            continue
        if in_loop:
            if not s or s.startswith("_") or s.startswith("loop_") or s.startswith("#"):
                if els:
                    break
                continue
            tok = s.split()
            if len(tok) >= 9:
                els.append(tok[7])
                try:
                    qs.append(float(tok[8]))
                except ValueError:
                    qs.append(np.nan)
    return els, np.array(qs)


def fragments(atoms):
    cut = natural_cutoffs(atoms, mult=1.15)
    nl = NeighborList(cut, self_interaction=False, bothways=True)
    nl.update(atoms)
    m = nl.get_connectivity_matrix(sparse=True).tocsr()
    ncomp, labels = connected_components(csr_matrix(m), directed=False)
    comps = []
    for c in range(ncomp):
        idx = np.where(labels == c)[0]
        els = [atoms.get_chemical_symbols()[i] for i in idx]
        comps.append(dict(n=int(len(idx)), formula="".join(sorted(set(els))),
                          counties={e: els.count(e) for e in sorted(set(els))}))
    comps.sort(key=lambda x: -x["n"])
    return int(ncomp), comps


def metrics(atoms):
    d = atoms.get_all_distances(mic=True)
    np.fill_diagonal(d, np.inf)
    tri = np.triu(np.ones_like(d, dtype=bool), 1)
    vals = d[tri]
    order = np.argsort(vals)
    ii, jj = np.where(tri)
    syms = atoms.get_chemical_symbols()
    pos = atoms.get_scaled_positions(wrap=True)
    close = []
    for k in order[:12]:
        a, b = int(ii[k]), int(jj[k])
        close.append(dict(i=a, j=b, pair=syms[a] + "-" + syms[b],
                          dist=round(float(vals[k]), 3),
                          fi=[round(float(x), 4) for x in pos[a]],
                          fj=[round(float(x), 4) for x in pos[b]]))
    return d, vals, close


def one(base, name, kind="pacmof"):
    cif = (os.path.join(base, "pacmof_cif", f"{name}_charged.cif") if kind == "pacmof"
           else os.path.join(base, f"{name}.cif"))
    atoms = read(cif)
    syms = atoms.get_chemical_symbols()
    n = len(atoms)
    d, vals, close = metrics(atoms)
    ncomp, comps = fragments(atoms)

    metals = [i for i, s in enumerate(syms) if s in METALS]
    donors = [i for i, s in enumerate(syms) if s in DONORS]
    mrows = []
    for m in metals:
        ds = d[m, donors]
        order = np.argsort(ds)
        mrows.append(dict(
            idx=m, el=syms[m],
            cn26=int((ds < 2.6).sum()),
            cn24=int((ds < 2.4).sum()),
            nearest=[[syms[donors[j]], round(float(ds[j]), 3)] for j in order[:6]],
        ))

    row = dict(
        name=name, kind=kind, natoms=n, formula=atoms.get_chemical_formula(),
        V=round(float(atoms.get_volume()), 1),
        density=round(float(atoms.get_masses().sum() / atoms.get_volume() / 6.02214076e23 * 1e24), 3),
        dmin=round(float(vals.min()), 3),
        n_pairs_lt_0p9=int((vals < 0.9).sum()),
        n_pairs_lt_0p7=int((vals < 0.7).sum()),
        n_pairs_lt_1p2=int((vals < 1.2).sum()),
        closest=close,
        n_fragments=ncomp, fragments=comps,
        metals=mrows,
    )
    if kind == "pacmof":
        els, qs = read_charges(cif)
        qstat = {}
        for el in sorted(set(els)):
            q = qs[[i for i, e in enumerate(els) if e == el]]
            qstat[el] = dict(n=int(len(q)), min=round(float(np.nanmin(q)), 3),
                             max=round(float(np.nanmax(q)), 3),
                             mean=round(float(np.nanmean(q)), 3))
        row.update(charges=qstat, qsum=round(float(np.nansum(qs)), 3),
                   metal_charges=[round(float(qs[i]), 3) for i in metals if i < len(qs)])
    return row


def main():
    base, out = sys.argv[1], sys.argv[2]
    rows = []
    for n in NAMES:
        rows.append(one(base, n, "pacmof"))
        try:
            rows.append(one(base, n, "orig"))
        except Exception as e:  # noqa
            rows.append(dict(name=n, kind="orig", error=str(e)))
    with open(out, "w") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    for r in rows:
        if "error" in r:
            print(f"{r['name']} orig ERROR {r['error']}")
            continue
        print(f"{r['name']:10s} {r['kind']:6s} n={r['natoms']:3d} dmin={r['dmin']:.3f} "
              f"<0.9={r['n_pairs_lt_0p9']:4d} <0.7={r['n_pairs_lt_0p7']:4d} <1.2={r['n_pairs_lt_1p2']:5d} "
              f"frag={r['n_fragments']} comp={[(c['n'], c['formula']) for c in r['fragments'][:3]]}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
