#!/usr/bin/env python3
"""为头部候选生成 SiH4/CO2 混合 GCMC 输入。

条件：298 K，1 bar（ExternalPressure 100000 Pa），CO2 1000 ppm（MolFraction 0.001），
SiH4 平衡；PACMOF 电荷 + UFF + Ewald；UnitCells 沿用对应 pol Widom 运行。

用法:
  python3 make_gcmc_inputs.py --mofs V0039_nbo ... \
      --cif-dir /share/.../generation/pacmof_cif --uc-dir /share/.../generation/val_runs \
      --out /share/.../generation/gcmc_runs [--cycles 30000] [--init 5000]
"""
import argparse, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = [("SiH4", 0.999), ("CO2", 0.001)]


def unit_cells(path):
    m = re.search(r"UnitCells\s+(\d+)\s+(\d+)\s+(\d+)", open(path).read())
    return tuple(int(x) for x in m.groups())


def write_input(path, name, uc, cycles, init):
    L = ["SimulationType                MonteCarlo", f"NumberOfCycles                {cycles}",
         f"NumberOfInitializationCycles  {init}", "PrintEvery                    1000", "",
         "Forcefield                    Local", "CutOffVDW                     12.8",
         "CutOffChargeCharge            12.8", "ChargeMethod                  Ewald",
         "EwaldPrecision                1.0e-6", "UseChargesFromCIFFile         yes", "",
         "Framework                     0", f"FrameworkName                 {name}",
         "RemoveAtomNumberCodeFromLabel yes", "UnitCells                     %d %d %d" % uc,
         "ExternalTemperature           298.0", "ExternalPressure              100000.0", ""]
    for i, (comp, y) in enumerate(COMPS):
        L += [f"Component {i} MoleculeName             {comp}",
              f"            MolFraction                  {y}",
              "            MoleculeDefinition           Local",
              "            FugacityCoefficient          1.0",
              "            TranslationProbability       1.0",
              "            RotationProbability          1.0",
              "            ReinsertionProbability       1.0",
              "            SwapProbability              1.0",
              "            CreateNumberOfMolecules      0", ""]
    open(path, "w").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mofs", nargs="+", required=True)
    ap.add_argument("--cif-dir", required=True)
    ap.add_argument("--uc-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ff-dir", default=os.path.join(HERE, "..", "widom_sih4"))
    ap.add_argument("--cycles", type=int, default=30000)
    ap.add_argument("--init", type=int, default=5000)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for mof in a.mofs:
        uc = unit_cells(os.path.join(a.uc_dir, mof, "pol", "simulation.input"))
        dst = os.path.join(a.out, mof, "gcmc"); os.makedirs(dst, exist_ok=True)
        shutil.copy(os.path.join(a.cif_dir, mof + "_charged.cif"), os.path.join(dst, mof + ".cif"))
        for sub in ("ff", "molecules"):
            for f in os.listdir(os.path.join(a.ff_dir, sub)):
                shutil.copy(os.path.join(a.ff_dir, sub, f), dst)
        write_input(os.path.join(dst, "simulation.input"), mof, uc, a.cycles, a.init)
        print(mof, uc)
    print(f"{len(a.mofs)} 个候选 -> {a.out}")


if __name__ == "__main__":
    main()
