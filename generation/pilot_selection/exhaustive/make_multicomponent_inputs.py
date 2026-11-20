#!/usr/bin/env python3
"""为多组分 / 过程条件研究构建 RASPA 输入。

沿用候选二元运行的 UnitCells 与 cycles，只替换组分、温度和压力。
"""
import argparse, csv, os, re, shutil

CONDITIONS = {
    "T298_P1": dict(T=298.0, P=100000.0),
    "T273_P1": dict(T=273.0, P=100000.0),
    "T323_P1": dict(T=323.0, P=100000.0),
    "T298_P5": dict(T=298.0, P=500000.0),
}
COMPS = [("SiH4", 0.997), ("CO2", 0.001), ("N2", 0.001), ("CH4", 0.001)]


def parse_base(path):
    t = open(path).read()
    uc = re.search(r"UnitCells\s+(\d+)\s+(\d+)\s+(\d+)", t)
    cyc = re.search(r"NumberOfCycles\s+(\d+)", t)
    init = re.search(r"NumberOfInitializationCycles\s+(\d+)", t)
    return tuple(int(x) for x in uc.groups()), int(cyc.group(1)), int(init.group(1))


def write_input(path, name, uc, cycles, init, T, P):
    L = ["SimulationType                MonteCarlo", f"NumberOfCycles                {cycles}",
         f"NumberOfInitializationCycles  {init}", "PrintEvery                    1000", "",
         "Forcefield                    Local", "CutOffVDW                     12.8",
         "CutOffChargeCharge            12.8", "ChargeMethod                  Ewald",
         "EwaldPrecision                1.0e-6", "UseChargesFromCIFFile         yes", "",
         "Framework                     0", f"FrameworkName                 {name}",
         "RemoveAtomNumberCodeFromLabel yes", "UnitCells                     %d %d %d" % uc,
         f"ExternalTemperature           {T}", f"ExternalPressure              {P}", ""]
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
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--base-runs", required=True, help="exhaustive/campaign_runs（取 simulation.input 与 CIF）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ff-dir", required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.candidates)))
    for cond, cfg in CONDITIONS.items():
        for r in rows:
            mof = r["mof"]
            base = os.path.join(a.base_runs, mof, "gcmc")
            uc, cycles, init = parse_base(os.path.join(base, "simulation.input"))
            dst = os.path.join(a.out, cond, mof, "gcmc")
            os.makedirs(dst, exist_ok=True)
            shutil.copy(os.path.join(base, mof + ".cif"), os.path.join(dst, mof + ".cif"))
            for sub in ("ff", "molecules"):
                for f in os.listdir(os.path.join(a.ff_dir, sub)):
                    shutil.copy(os.path.join(a.ff_dir, sub, f), dst)
            write_input(os.path.join(dst, "simulation.input"), mof, uc, cycles, init,
                        cfg["T"], cfg["P"])
        print(cond, len(rows), "->", os.path.join(a.out, cond))


if __name__ == "__main__":
    main()
