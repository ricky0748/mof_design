#!/usr/bin/env python3
"""轻量 CIF 索引：从 P1 CIF 的 atom_site 循环提取化学式计数与晶胞体积。

输出 CSV: db,path,key,volume,natoms,p1,error
key 为按 gcd 约化后的元素计数（如 C38;Cu2;H52;N6;O12），用于 exact formula 预筛。
用法: python fast_db_index.py <db_name> <dir> <out.csv> [--workers 64] [--limit N]
"""
import os
import sys
import csv
import re
import math
import argparse
from collections import Counter
from math import gcd
from functools import reduce
from concurrent.futures import ProcessPoolExecutor


def parse_formula(s):
    toks = re.findall(r"([A-Z][a-z]?)\s*([0-9.]*)", s)
    out = Counter()
    for el, n in toks:
        if not n:
            out[el] += 1
        else:
            try:
                out[el] += int(round(float(n)))
            except ValueError:
                pass
    return out if out else None


def index_one(path):
    try:
        with open(path, errors="ignore") as f:
            txt = f.read()
    except Exception as e:  # noqa
        return dict(path=path, error=f"read:{e}"[:80])
    def g(k):
        m = re.search(r"^_cell_" + k + r"\s+([-0-9.]+)", txt, re.M)
        return float(m.group(1)) if m else None
    a, b, c, al, be, ga = [g(x) for x in ("length_a", "length_b", "length_c",
                                          "angle_alpha", "angle_beta", "angle_gamma")]
    V = None
    m = re.search(r"^_cell_volume\s+([-0-9.]+)", txt, re.M)
    if m:
        V = float(m.group(1))
    elif None not in (a, b, c, al, be, ga):
        ca, cb, cg = map(math.cos, map(math.radians, (al, be, ga)))
        V = a * b * c * math.sqrt(max(0.0, 1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg))
    p1 = bool(re.search(r"_symmetry_Int_Tables_number\s+1\b", txt)) or \
         bool(re.search(r"_symmetry_space_group_name_H-M\s+[\"']?P ?1\b", txt))
    counts = None
    m = re.search(r"_chemical_formula_sum\s+[\"']([^\"']+)[\"']", txt)
    if m:
        counts = parse_formula(m.group(1))
    if not counts:
        cols, inloop, elems = [], False, []
        for line in txt.splitlines():
            s = line.strip()
            if s == "loop_":
                cols, inloop = [], True
                continue
            if inloop and s.startswith("_"):
                cols.append(s)
                continue
            if inloop and cols and s and not s.startswith("_"):
                if "_atom_site" in "".join(cols):
                    t = s.split()
                    if len(t) >= len(cols) and ("_atom_site_type_symbol" in cols or "_atom_site_label" in cols):
                        if "_atom_site_type_symbol" in cols:
                            sym = t[cols.index("_atom_site_type_symbol")]
                        else:
                            mm = re.match(r"[A-Za-z]+", t[cols.index("_atom_site_label")])
                            sym = mm.group(0) if mm else ""
                        if sym:
                            sym = sym[:1].upper() + sym[1:2].lower() if len(sym) > 1 else sym.upper()
                            elems.append(sym)
                else:
                    inloop = False
        if elems:
            counts = Counter(elems)
    if not counts or V is None or V <= 0:
        return dict(path=path, error="parse")
    gd = reduce(gcd, counts.values()) or 1
    key = ";".join(f"{el}{counts[el] // gd}" for el in sorted(counts))
    return dict(path=path, key=key, volume=round(V, 2), natoms=sum(counts.values()),
                p1=int(p1), error="")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("dir")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    files = []
    for root, _, fs in os.walk(a.dir):
        for f in fs:
            if f.endswith(".cif"):
                files.append(os.path.join(root, f))
    files.sort()
    if a.limit:
        files = files[:a.limit]
    print(f"{a.db}: {len(files)} CIF", flush=True)
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(index_one, files, chunksize=200), 1):
            r["db"] = a.db
            rows.append(r)
            if i % 5000 == 0 or i == len(files):
                print(f"{i}/{len(files)}", flush=True)
    cols = ["db", "path", "key", "volume", "natoms", "p1", "error"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    ok = sum(1 for r in rows if not r.get("error"))
    print(f"done {ok}/{len(rows)} -> {a.out}")


if __name__ == "__main__":
    main()
