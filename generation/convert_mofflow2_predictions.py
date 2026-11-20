#!/usr/bin/env python3
"""把 MOFFlow-2 predictions_*.pt 转成 CIF（pymatgen）。

用法: python convert_mofflow2_predictions.py <predictions.pt> <out_dir> [prefix]
"""
import os, sys
import numpy as np
import torch
from pymatgen.core import Lattice, Structure


def main():
    src, out = sys.argv[1], sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else "mofflow2"
    os.makedirs(out, exist_ok=True)
    d = torch.load(src, map_location="cpu", weights_only=False)
    coords = d["cart_coords"][0].numpy()
    na = d["num_atoms"][0].numpy()
    types = d["atom_types"][0].numpy()
    lat = d["lattices"][0].numpy()
    start, ok, bad = 0, 0, 0
    for i, n in enumerate(na):
        n = int(n)
        c = coords[start:start + n]
        t = types[start:start + n]
        start += n
        try:
            L = Lattice.from_parameters(*[float(x) for x in lat[i]])
            s = Structure(L, [int(x) for x in t], c.tolist(), coords_are_cartesian=True)
            s.to(filename=os.path.join(out, f"{prefix}_{i:03d}.cif"))
            ok += 1
        except Exception as e:
            bad += 1
            print("FAIL", i, e)
    print(f"written {ok}/{len(na)} (bad {bad}) -> {out}")


if __name__ == "__main__":
    main()
