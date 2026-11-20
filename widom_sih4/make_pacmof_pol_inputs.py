#!/usr/bin/env python3
"""构建 PACMOF 电荷版的 pol 组 Widom 输入（N2/O2/CO/CO2，Ewald）。

mode=crafted: 复用 widom_sih4/runs/<mof>/pol 的 simulation.input/ff/molecules，
              把 CIF 换成 crafted_pacmof/<mof>.cif。
mode=ood:     复用 ood_assembly/ood_runs/<mof>/np 的 UnitCells，
              把 CIF 换成 ood_assembly/pacmof_cif/<mof>_charged.cif，并新写 pol 输入。

用法:
  python3 make_pacmof_pol_inputs.py --mode crafted \
      --runs-dir /share/rickyswork/ai_mof/widom_sih4/runs \
      --pacmof-dir /share/rickyswork/ai_mof/crafted_pacmof \
      --out /share/rickyswork/ai_mof/widom_pacmof/runs
  python3 make_pacmof_pol_inputs.py --mode ood \
      --runs-dir /share/rickyswork/ai_mof/ood_assembly/ood_runs \
      --pacmof-dir /share/rickyswork/ai_mof/ood_assembly/pacmof_cif \
      --out /share/rickyswork/ai_mof/ood_assembly/ood_pol_runs
"""
import argparse, csv, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = ["N2", "O2", "CO", "CO2"]


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
        "ChargeMethod                  Ewald",
        "EwaldPrecision                1.0e-6",
        "UseChargesFromCIFFile         yes",
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
    ap.add_argument("--mode", choices=["crafted", "ood"], required=True)
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--pacmof-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    jobs = list(csv.DictReader(open(os.path.join(a.runs_dir, "jobs.csv"))))
    rows = []
    for j in jobs:
        mof, ucs = j["mof"], j["unit_cells"]
        uc = tuple(int(x) for x in ucs.split("x"))
        src = os.path.join(a.runs_dir, mof, "pol" if a.mode == "crafted" else "np")
        dst = os.path.join(a.out, mof, "pol")
        os.makedirs(dst, exist_ok=True)
        # 力场与分子定义
        if a.mode == "crafted":
            for f in os.listdir(src):
                if f.endswith(".def") or f == "simulation.input":
                    shutil.copy(os.path.join(src, f), dst)
        else:
            for sub in ("ff", "molecules"):
                for f in os.listdir(os.path.join(HERE, sub)):
                    shutil.copy(os.path.join(HERE, sub, f), dst)
        # CIF
        cif_src = os.path.join(a.pacmof_dir, mof + (".cif" if a.mode == "crafted" else "_charged.cif"))
        shutil.copy(cif_src, os.path.join(dst, mof + ".cif"))
        # input
        if a.mode == "ood":
            write_input(os.path.join(dst, "simulation.input"), mof, uc)
        rows.append((mof, ucs, j["atoms_in_supercell"]))
    with open(os.path.join(a.out, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["mof", "unit_cells", "atoms_in_supercell"]); w.writerows(rows)
    print(f"{len(rows)} 个 MOF -> {a.out}")


if __name__ == "__main__":
    main()
