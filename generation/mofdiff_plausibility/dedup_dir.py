#!/usr/bin/env python3
"""结构去重：对同一引擎生成的 CIF 做 StructureMatcher 两两比较，输出唯一结构和重复组。

用法: python dedup_dir.py <cif_dir> <out.csv> [--tag name]
"""
import os
import sys
import csv
import numpy as np
from pymatgen.io.cif import CifParser
from pymatgen.analysis.structure_matcher import StructureMatcher


def load(path):
    try:
        s = CifParser(path, occupancy_tolerance=1).parse_structures(primitive=False)[0]
        return s
    except Exception:
        return None


def main():
    d, out = sys.argv[1], sys.argv[2]
    tag = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--tag" else os.path.basename(os.path.normpath(d))
    files = sorted(f for f in os.listdir(d) if f.endswith(".cif"))
    names, structs = [], []
    for f in files:
        s = load(os.path.join(d, f))
        if s is None:
            continue
        names.append(f[:-4])
        structs.append(s)

    n = len(structs)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    sm = StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10, primitive_cell=True, scale=True)
    pairs = 0
    for i in range(n):
        ci = structs[i].composition.reduced_formula
        vi = structs[i].volume
        for j in range(i + 1, n):
            if structs[j].composition.reduced_formula != ci:
                continue
            vj = structs[j].volume
            if not (0.5 <= vi / vj <= 2.0):
                continue
            pairs += 1
            try:
                if sm.fit(structs[i], structs[j]):
                    union(i, j)
            except Exception:
                pass

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    uniq = len(groups)
    dup_groups = [g for g in groups.values() if len(g) > 1]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["engine", "group", "members"])
        for gid, g in enumerate(sorted(groups.values(), key=len, reverse=True)):
            if len(g) > 1:
                w.writerow([tag, gid, ";".join(names[i] for i in g)])
    print(f"{tag}: {n} parsed, {uniq} unique ({uniq/max(1,n):.1%}), "
          f"{len(dup_groups)} duplicate groups, {pairs} pairs compared -> {out}")


if __name__ == "__main__":
    main()
