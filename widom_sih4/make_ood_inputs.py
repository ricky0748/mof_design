#!/usr/bin/env python3
"""为组装结构 OOD 试点生成 Widom np 组输入（SiH4、H2、Ar、CH4，无电荷）。

与 CRAFTED 主实验同口径：298 K，5000 cycles，12.8 Å 截断，UFF，np 组关闭 Ewald。
超胞倍数按 2×12.8 Å 的最小盒宽选取，保证最小镜像。

用法:
  python3 make_ood_inputs.py --cif-dir ../ood_assembly/cif --out ../ood_assembly/ood_runs
"""
import argparse, csv, math, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = ["SiH4", "H2", "Ar", "CH4"]


def cif_info(path):
    t = open(path).read().splitlines()
    def g(k):
        m = re.search(r"^_cell_" + k + r"\s+([-0-9.]+)", "\n".join(t), re.M)
        return float(m.group(1)) if m else None
    lengths = [g("length_a"), g("length_b"), g("length_c")]
    i = t.index("_atom_site_label"); j = i + 1
    while j < len(t) and (t[j].startswith("_") or t[j].strip() == ""):
        j += 1
    n = 0
    while j < len(t) and not t[j].startswith("_") and not t[j].startswith("#"):
        if len(t[j].split()) >= 2:
            n += 1
        j += 1
    return lengths, n


def write_input(path, name, uc, cycles=5000):
    L = [
        "SimulationType                MonteCarlo",
        f"NumberOfCycles                {cycles}",
        "NumberOfInitializationCycles  0",
        f"PrintEvery                    {max(1000, cycles // 10)}",
        "",
        "Forcefield                    Local",
        "CutOffVDW                     12.8",
        "CutOffChargeCharge            12.8",
        "ChargeMethod                  None",
        "EwaldPrecision                1.0e-6",
        "UseChargesFromCIFFile         no",
        "",
        "Framework                     0",
        f"FrameworkName                 {name}",
        "RemoveAtomNumberCodeFromLabel yes",
        "UnitCells                     %d %d %d" % uc,
        "ExternalTemperature           298.0",
        "",
    ]
    for i, c in enumerate(COMPS):
        L += [f"Component {i} MoleculeName             {c}",
              "            MoleculeDefinition       Local",
              "            WidomProbability         1.0",
              "            CreateNumberOfMolecules  0", ""]
    open(path, "w").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cycles", type=int, default=5000)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for f in sorted(os.listdir(a.cif_dir)):
        if not f.endswith(".cif"):
            continue
        name = f[:-4]
        lengths, n = cif_info(os.path.join(a.cif_dir, f))
        uc = tuple(max(1, math.ceil(26.0 / x)) for x in lengths)
        d = os.path.join(a.out, name, "np")
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(a.cif_dir, f), d)
        for sub in ("ff", "molecules"):
            for x in os.listdir(os.path.join(HERE, sub)):
                shutil.copy(os.path.join(HERE, sub, x), d)
        write_input(os.path.join(d, "simulation.input"), name, uc, a.cycles)
        rows.append((name, "%dx%dx%d" % uc, n * uc[0] * uc[1] * uc[2]))
    with open(os.path.join(a.out, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["mof", "unit_cells", "atoms_in_supercell"]); w.writerows(rows)
    print(f"{len(rows)} 个结构 -> {a.out}")
    print("超胞原子数: min %d, median %d, max %d" % (
        min(r[2] for r in rows), sorted(r[2] for r in rows)[len(rows) // 2], max(r[2] for r in rows)))


if __name__ == "__main__":
    main()
