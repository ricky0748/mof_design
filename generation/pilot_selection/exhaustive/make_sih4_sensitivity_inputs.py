#!/usr/bin/env python3
"""SiH4 单点 LJ 参数敏感性：构建 ±20% ε、±0.1 Å σ 的二元 GCMC 输入。

基线：SiH4 ε/kB = 207.6 K, σ = 4.084 Å（现有单点模型）。
其余分子与力场规则不变；候选沿用二元普查的 UnitCells。
"""
import argparse, csv, os, re, shutil

VARIANTS = {
    "eps_m20": (166.08, 4.084),
    "eps_p20": (249.12, 4.084),
    "sig_m01": (207.60, 3.984),
    "sig_p01": (207.60, 4.184),
}
COMPS = [("SiH4", 0.999), ("CO2", 0.001)]


def parse_base(path):
    t = open(path).read()
    uc = re.search(r"UnitCells\s+(\d+)\s+(\d+)\s+(\d+)", t)
    cyc = re.search(r"NumberOfCycles\s+(\d+)", t)
    init = re.search(r"NumberOfInitializationCycles\s+(\d+)", t)
    return tuple(int(x) for x in uc.groups()), int(cyc.group(1)), int(init.group(1))


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


def patch_ff(ff_dir, eps, sig):
    p = os.path.join(ff_dir, "force_field_mixing_rules.def")
    t = open(p).read()
    t2 = re.sub(r"^SiH4_sp\s+lennard-jones\s+[0-9.]+\s+[0-9.]+",
                f"SiH4_sp        lennard-jones    {eps:.4f}    {sig:.4f}", t, flags=re.M)
    assert t2 != t, "SiH4_sp line not found"
    open(p, "w").write(t2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--base-runs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ff-dir", required=True)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.candidates)))
    for v, (eps, sig) in VARIANTS.items():
        for r in rows:
            mof = r["mof"]
            base = os.path.join(a.base_runs, mof, "gcmc")
            uc, cycles, init = parse_base(os.path.join(base, "simulation.input"))
            dst = os.path.join(a.out, v, mof, "gcmc")
            os.makedirs(dst, exist_ok=True)
            shutil.copy(os.path.join(base, mof + ".cif"), os.path.join(dst, mof + ".cif"))
            for sub in ("ff", "molecules"):
                for f in os.listdir(os.path.join(a.ff_dir, sub)):
                    shutil.copy(os.path.join(a.ff_dir, sub, f), dst)
            patch_ff(dst, eps, sig)
            write_input(os.path.join(dst, "simulation.input"), mof, uc, cycles, init)
        print(v, eps, sig, len(rows))


if __name__ == "__main__":
    main()
