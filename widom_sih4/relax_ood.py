#!/usr/bin/env python3
"""用 MACE-MP 对组装结构做快速弛豫（可含晶胞），检查是否回到 CRAFTED 适用域。

用法:
  CUDA_VISIBLE_DEVICES=0 python3 relax_ood.py --cif in.cif --out out.cif \
      --steps 40 --fmax 0.2 --maxstep 0.05 [--fixed-cell]
模型默认 /share/rickyswork/ai_mof/mace_medium.model。
"""
import argparse, json, time, warnings
warnings.filterwarnings("ignore")
from ase.io import read, write
from ase.optimize import BFGS
from ase.filters import FrechetCellFilter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cif", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="/share/rickyswork/ai_mof/mace_medium.model")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--fmax", type=float, default=0.2)
    ap.add_argument("--maxstep", type=float, default=0.05)
    ap.add_argument("--fixed-cell", action="store_true")
    a = ap.parse_args()
    from mace.calculators import mace_mp
    t0 = time.time()
    atoms = read(a.cif)
    atoms.calc = mace_mp(model=a.model, default_dtype="float64", device=a.device)
    v0, e0 = atoms.get_volume(), atoms.get_potential_energy()
    target = atoms if a.fixed_cell else FrechetCellFilter(atoms)
    opt = BFGS(target, logfile=None, maxstep=a.maxstep)
    opt.run(fmax=a.fmax, steps=a.steps)
    write(a.out, atoms)
    print(json.dumps(dict(cif=a.cif, out=a.out, n_atoms=len(atoms), fixed_cell=a.fixed_cell,
                          steps=opt.nsteps, V0=round(v0, 1), V1=round(atoms.get_volume(), 1),
                          V_ratio=round(atoms.get_volume() / v0, 4),
                          E0=round(float(e0), 3), E1=round(float(atoms.get_potential_energy()), 3),
                          seconds=round(time.time() - t0, 1)), ensure_ascii=False))


if __name__ == "__main__":
    main()
