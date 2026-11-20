#!/usr/bin/env python3
"""批量用 PACMOF 给 CIF 分配电荷，输出带 _atom_site_charge 的 CIF。

用法（需 PYTHONPATH 指向 pacmof 仓库根目录）:
  PYTHONPATH=/share/rickyswork/ai_mof/pacmof python3 pacmof_batch.py \
      --cif-dir ../ood_assembly/cif --out ../ood_assembly/pacmof_cif --workers 8
"""
import argparse, os, sys, traceback
from concurrent.futures import ProcessPoolExecutor


def one(job):
    cif, out = job
    try:
        import pacmof
        pacmof.get_charges_single_serial(cif, create_cif=True, path_to_output_dir=out)
        return (os.path.basename(cif), True, None)
    except Exception:
        return (os.path.basename(cif), False, traceback.format_exc().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jobs = [(os.path.join(a.cif_dir, f), a.out) for f in sorted(os.listdir(a.cif_dir)) if f.endswith(".cif")]
    ok = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (name, good, err) in enumerate(ex.map(one, jobs), 1):
            ok += good
            if not good:
                print("FAIL", name, err, flush=True)
            if i % 10 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)} ok={ok}", flush=True)
    print(f"done: {ok}/{len(jobs)} -> {a.out}")


if __name__ == "__main__":
    main()
