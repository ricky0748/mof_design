#!/usr/bin/env python3
"""为生产候选的 CO2 验证生成 PACMOF pol Widom 输入。

选定候选后，从单晶胞 CIF 读晶胞和原子数，按 2×12.8 Å 最小盒宽扩超胞，
CIF 用 PACMOF 电荷版，写 N2/O2/CO/CO2（Ewald）输入。

用法:
  python3 make_gen_val_inputs.py --mofs V0039_nbo V0164_nbo ... \
      --cif-dir /share/.../generation/out/cif --pacmof-dir /share/.../generation/pacmof_cif \
      --out /share/.../generation/val_runs
"""
import argparse, csv, math, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = ["N2", "O2", "CO", "CO2"]


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
    L = ["SimulationType                MonteCarlo", f"NumberOfCycles                {cycles}",
         "NumberOfInitializationCycles  0", f"PrintEvery                    {max(1000, cycles // 10)}", "",
         "Forcefield                    Local", "CutOffVDW                     12.8",
         "CutOffChargeCharge            12.8", "ChargeMethod                  Ewald",
         "EwaldPrecision                1.0e-6", "UseChargesFromCIFFile         yes", "",
         "Framework                     0", f"FrameworkName                 {name}",
         "RemoveAtomNumberCodeFromLabel yes", "UnitCells                     %d %d %d" % uc,
         "ExternalTemperature           298.0", ""]
    for i, c in enumerate(COMPS):
        L += [f"Component {i} MoleculeName             {c}", "            MoleculeDefinition       Local",
              "            WidomProbability         1.0", "            CreateNumberOfMolecules  0", ""]
    open(path, "w").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mofs", nargs="+", required=True)
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--pacmof-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ff-dir", default=os.path.join(HERE, "..", "widom_sih4"))
    ap.add_argument("--cycles", type=int, default=5000)
    a = ap.parse_args()
    rows = []
    for mof in a.mofs:
        lengths, n = cif_info(os.path.join(a.cif_dir, mof + ".cif"))
        uc = tuple(max(1, math.ceil(26.0 / x)) for x in lengths)
        dst = os.path.join(a.out, mof, "pol"); os.makedirs(dst, exist_ok=True)
        shutil.copy(os.path.join(a.pacmof_dir, mof + "_charged.cif"), os.path.join(dst, mof + ".cif"))
        for sub in ("ff", "molecules"):
            for f in os.listdir(os.path.join(a.ff_dir, sub)):
                shutil.copy(os.path.join(a.ff_dir, sub, f), dst)
        write_input(os.path.join(dst, "simulation.input"), mof, uc, a.cycles)
        rows.append((mof, "%dx%dx%d" % uc, n * uc[0] * uc[1] * uc[2]))
    with open(os.path.join(a.out, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["mof", "unit_cells", "atoms_in_supercell"]); w.writerows(rows)
    print(f"{len(rows)} 个候选 -> {a.out}")
    print("超胞原子数:", min(r[2] for r in rows), "-", max(r[2] for r in rows))


if __name__ == "__main__":
    main()
