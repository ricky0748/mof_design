#!/usr/bin/env python3
"""生成 CRAFTED 690 MOF 的 Widom 输入（SiH4 + 7 种常规杂质，298 K，一个 MOF 一个 run 目录）。

每个 MOF 两个 run 目录：np/（SiH4、H2、Ar、CH4，无电荷，不开 Ewald）和 pol/（N2、O2、CO、CO2，DDEC 电荷 + Ewald）。
每个 run 目录：simulation.input、<MOF>.cif（CRAFTED DDEC 电荷版）、ff/*.def、molecules/*.def 的拷贝。
晶胞数沿用 CRAFTED 自己 GCMC 输入里的 UnitCells（保证截断 12.8 Å 下的最小镜像约定，与 CO2/N2 数据一致）。

用法:
  python3 make_inputs.py --crafted <CRAFTED-2.0.0 目录> --out runs [--cycles 5000] [--block-dir blocks] [--only ABUWOJ ACOLIP]
纯标准库，可在 Windows、本机 Linux 或服务器上运行。
"""
import argparse, csv, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
# 无电荷分子不需要 Ewald，单独一组跑可省大量时间（实测 ABUWOJ：非极性组 60 s，极性组 392 s，2000 cycles）
GROUPS = {"np": ["SiH4", "H2", "Ar", "CH4"], "pol": ["N2", "O2", "CO", "CO2"]}
COMPONENTS = GROUPS["np"] + GROUPS["pol"]


def unit_cells(crafted, mof):
    p = os.path.join(crafted, "INPUT_FILES", f"DDEC_{mof}_UFF_CO2_298.input")
    m = re.search(r"UnitCells\s+(\d+)\s+(\d+)\s+(\d+)", open(p).read())
    return tuple(int(x) for x in m.groups())


def write_input(path, mof, uc, cycles, comps, ewald, block=None):
    L = [
        "SimulationType                MonteCarlo",
        f"NumberOfCycles                {cycles}",
        "NumberOfInitializationCycles  0",
        f"PrintEvery                    {max(1000, cycles // 10)}",
        "",
        "Forcefield                    Local",
        "CutOffVDW                     12.8",
        "CutOffChargeCharge            12.8",
        "ChargeMethod                  %s" % ("Ewald" if ewald else "None"),
        "EwaldPrecision                1.0e-6",
        "UseChargesFromCIFFile         %s" % ("yes" if ewald else "no"),
        "",
        "Framework                     0",
        f"FrameworkName                 {mof}",
        "RemoveAtomNumberCodeFromLabel yes",
        "UnitCells                     %d %d %d" % uc,
        "ExternalTemperature           298.0",
        "",
    ]
    for i, c in enumerate(comps):
        L += [f"Component {i} MoleculeName             {c}",
              "            MoleculeDefinition       Local",
              "            WidomProbability         1.0"]
        if block and c in block:
            L += ["            BlockPockets             yes",
                  f"            BlockPocketsFileName     {block[c]}"]
        L += ["            CreateNumberOfMolecules  0", ""]
    open(path, "w").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crafted", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "runs"))
    ap.add_argument("--cycles", type=int, default=5000)
    ap.add_argument("--block-dir", default=None,
                    help="可选：Zeo++ 生成的 .block 文件目录，命名 <MOF>_<分子>.block（见 make_blocks.sh）")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--skip-existing", action="store_true", help="已生成（np 与 pol 的 simulation.input 都在）的 MOF 不再重复拷贝")
    ap.add_argument("--max-new", type=int, default=0, help="本次最多新生成多少个 MOF（0=不限），用于在慢速磁盘上分批生成")
    a = ap.parse_args()
    names = [r["FrameworkName"] for r in csv.DictReader(open(os.path.join(a.crafted, "RAC_DBSCAN", "CRAFTED_MOF_geometric.csv")))]
    if a.only:
        names = [n for n in names if n in a.only]
    os.makedirs(a.out, exist_ok=True)
    rows, new = [], 0
    for n in names:
        uc = unit_cells(a.crafted, n)
        done = all(os.path.exists(os.path.join(a.out, n, g, "simulation.input")) for g in GROUPS)
        skip = (a.skip_existing and done) or (a.max_new and new >= a.max_new)
        if not skip:
            new += 1
        for g, comps in ([] if skip else GROUPS.items()):
            d = os.path.join(a.out, n, g)
            os.makedirs(d, exist_ok=True)
            shutil.copy(os.path.join(a.crafted, "CIF_FILES", "DDEC", n + ".cif"), d)
            for sub in ("ff", "molecules"):
                for f in os.listdir(os.path.join(HERE, sub)):
                    shutil.copy(os.path.join(HERE, sub, f), d)
            block = None
            if a.block_dir:
                block = {}
                for c in comps:
                    b = os.path.join(a.block_dir, f"{n}_{c}.block")
                    if os.path.exists(b):
                        shutil.copy(b, os.path.join(d, f"{n}_{c}.block")); block[c] = f"{n}_{c}"
            write_input(os.path.join(d, "simulation.input"), n, uc, a.cycles, comps, g == "pol", block)
        natoms = sum(1 for l in open(os.path.join(a.crafted, "CIF_FILES", "DDEC", n + ".cif"))
                     if re.match(r"^\s*[A-Z][a-z]?\S*\s+-?[0-9.]+\s+-?[0-9.]+\s+-?[0-9.]+\s+-?[0-9.]+\s*$", l))
        rows.append((n, "%dx%dx%d" % uc, natoms * uc[0] * uc[1] * uc[2]))
    with open(os.path.join(a.out, "jobs.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["mof", "unit_cells", "atoms_in_supercell"]); w.writerows(rows)
    ready = sum(all(os.path.exists(os.path.join(a.out, r[0], g, "simulation.input")) for g in GROUPS) for r in rows)
    print(f"本次新生成 {new} 个；共 {len(rows)} 个 MOF，已就绪 {ready} 个（每个 np + pol 两个 run 目录）-> {a.out}")


if __name__ == "__main__":
    main()
