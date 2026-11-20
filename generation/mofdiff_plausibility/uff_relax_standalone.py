#!/usr/bin/env python3
"""Standalone MOFDiff UFF relaxation (extracted from mofdiff/common/relaxation.py).

Avoids importing the full mofdiff package (which requires pytorch_lightning).
Usage: uff_relax_standalone.py <cif1> [cif2 ...]
Writes <cif_dir>/../relaxed/<name>_uff.cif and prints relax JSON per structure.
"""
import sys
import os
import re
import json
import time
import subprocess
from pathlib import Path
from textwrap import dedent

import numpy as np
from pymatgen.core import Element
from lammps import lammps
from pymatgen.io.cif import CifWriter
from pymatgen.core import Structure
from pymatgen.io.lammps import outputs as lmp_outputs


def extract_info_from_log(log_file_path):
    with open(log_file_path) as f:
        lines = f.readlines()
    info = dict(PotEng_start=None, PotEng_end=None, Volume_start=None, Volume_end=None)
    for i, line in enumerate(lines):
        if "ERROR" in line:
            return None
        if "Step" in line and "PotEng" in line and "Volume" in line:
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if nxt is not None:
                sp = nxt.split()
                if info["PotEng_start"] is None:
                    info["PotEng_start"] = float(sp[1])
                    info["Volume_start"] = float(sp[2])
                else:
                    info["PotEng_end"] = float(sp[1])
                    info["Volume_end"] = float(sp[2])
    return info


def initiate_lammps_with_force_field(cif_file, force_field="UFF"):
    subprocess.run(["lammps-interface", cif_file, "-ff", force_field], text=True, input="y")
    fname = Path(cif_file).name.split(".")[0]
    with open("in." + fname) as f:
        txt = f.read()
    block = re.findall("(.*)#### Atom", txt, re.DOTALL)[0]
    block = re.sub("log.+\n", "", block)
    logname = str(Path(cif_file).parent.parent / "relaxed" / f"{fname}_log.lammps")
    lmp = lammps(cmdargs=["-log", logname])
    lmp.commands_string(block)
    return lmp


def relax_structure_and_box(lmp, uid):
    lmp.commands_string(dedent("""
        neighbor 1.0 nsq
        neigh_modify once no every 1 delay 0 check yes
        thermo          100
        thermo_style    custom step pe vol
        thermo_modify    norm no
        timer timeout 1:00:00 every 100
    """).strip())
    for _ in range(2):
        lmp.commands_string(dedent("""
            min_style       cg
            min_modify      dmax 0.01
            minimize        1e-8 1e-8 100000 100000
            fix             minimization_pressure all box/relax tri 0.0
            minimize        1e-8 1e-8 100000 100000
            unfix           minimization_pressure
        """).strip())
    lmp.commands_string(dedent(f"""
        dump            output all atom 1 relaxed_structure_{uid}.dump
        run             0
        undump          output
    """).strip())


def dump_to_structure(dump_file, data_file):
    dump = next(lmp_outputs.parse_lammps_dumps(dump_file))
    with open(data_file) as f:
        masses = re.findall(r"(?<=Masses\n{2})(.*?)(?=\n{2})", f.read(), re.DOTALL)[0]
        masses = masses.split("\n")
    symbols = np.array([str(e) for e in Element])
    emass = np.array([Element(str(e)).atomic_mass for e in Element])
    ident = {}
    for atom in masses:
        ident[atom.split()[0]] = symbols[(np.abs(emass - float(atom.split()[1]))).argmin()]
    dump.data["element"] = dump.data["type"].apply(lambda x: ident[str(x)])
    return Structure(dump.box.to_lattice(), dump.data.element,
                     dump.data.loc[:, ["xs", "ys", "zs"]].to_numpy())


def relax_one(cif_file):
    cif_file = str(Path(cif_file).resolve())
    uid = Path(cif_file).name.split(".")[0]
    outdir = Path(cif_file).parent.parent / "relaxed"
    outdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = dict(cif=cif_file, uid=uid)
    cwd = os.getcwd()
    try:
        os.chdir(str(outdir))
        lmp = initiate_lammps_with_force_field(cif_file)
        relax_structure_and_box(lmp, uid)
        struct = dump_to_structure(str(outdir / f"relaxed_structure_{uid}.dump"),
                                   str(outdir / f"data.{uid}"))
        CifWriter(struct).write_file(str(outdir / f"{uid}_uff.cif"))
        dm = struct.distance_matrix
        np.fill_diagonal(dm, np.inf)
        rec.update(ok=True, natoms=len(struct), V=round(float(struct.volume), 1),
                   dmin=round(float(dm.min()), 3),
                   pairs_lt_0p9=int((dm < 0.9).sum() // 2),
                   pairs_lt_1p2=int((dm < 1.2).sum() // 2),
                   log=extract_info_from_log(str(outdir / f"{uid}_log.lammps")))
        for f in [f"relaxed_structure_{uid}.dump", f"data.{uid}", f"in.{uid}"]:
            try:
                os.remove(f)
            except OSError:
                pass
    except Exception as e:  # noqa
        rec.update(ok=False, error=f"{type(e).__name__}: {e}")
    finally:
        os.chdir(cwd)
        rec["seconds"] = round(time.time() - t0, 1)
    return rec


def main():
    for cif in sys.argv[1:]:
        rec = relax_one(cif)
        print(json.dumps(rec, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
