#!/usr/bin/env python3
"""基于 exact reduced-formula 预筛的结构 novelty 查询。

对每个候选 CIF：
1. 用 fast_db_index 的轻量解析得到 gcd 约化化学式 key 和体积；
2. 在所有 DB 索引中查同 key 的条目（结构相同 ⇒ 组成相同，必要不充分）；
3. 对同 key 条目做 StructureMatcher，确认是否为同一结构。
输出逐候选 CSV + 汇总。

用法: python novelty_lookup.py <candidate_cif_dir> <index_dir> <out.csv> [--tag NAME]
"""
import os
import sys
import csv
import argparse
from collections import defaultdict

from pymatgen.io.cif import CifParser
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

sys.path.insert(0, "/tmp")
from fast_db_index import index_one  # noqa: E402


def load_index(path):
    idx = defaultdict(list)
    errors = 0
    for r in csv.DictReader(open(path)):
        if r.get("error"):
            errors += 1
            continue
        try:
            idx[r["key"]].append((r["db"], r["path"], float(r["volume"])))
        except (ValueError, KeyError):
            errors += 1
    return idx, errors


def parse_struct(path):
    try:
        return CifParser(path, occupancy_tolerance=1).parse_structures(primitive=False)[0]
    except Exception:
        try:
            return Structure.from_file(path)
        except Exception:
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cif_dir")
    ap.add_argument("index_dir")
    ap.add_argument("out")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    dbs = ["CSD_MOF_Collection", "core2024", "hmof", "mosaec-db"]
    indices = {}
    for db in dbs:
        p = os.path.join(a.index_dir, db + "_idx.csv")
        if os.path.exists(p):
            indices[db], err = load_index(p)
            print(f"{db}: keys={len(indices[db])} errors={err}", flush=True)

    sm = StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10,
                          primitive_cell=True, scale=True, attempt_supercell=True)
    files = sorted(f for f in os.listdir(a.cif_dir) if f.endswith(".cif"))
    rows, summary = [], defaultdict(lambda: defaultdict(int))
    struct_cache = {}
    for i, f in enumerate(files, 1):
        path = os.path.join(a.cif_dir, f)
        name = f[:-4]
        rec = index_one(path)
        row = dict(engine=a.tag, name=name, key=rec.get("key", ""), volume=rec.get("volume", ""),
                   error=rec.get("error", ""))
        for db in dbs:
            row[f"{db}_key"] = 0
            row[f"{db}_match"] = 0
            row[f"{db}_hits"] = ""
        if not rec.get("error"):
            cand = parse_struct(path)
            for db, idx in indices.items():
                entries = idx.get(rec["key"], [])
                row[f"{db}_key"] = len(entries)
                if not entries:
                    continue
                if cand is None:
                    continue
                hits = []
                for (d, p, V) in entries:
                    if not (0.1 <= rec["volume"] / V <= 10.0):
                        continue
                    s = struct_cache.get(p)
                    if s is None:
                        s = parse_struct(p)
                        struct_cache[p] = s if s is not None else False
                    if s is False or s is None:
                        continue
                    try:
                        if sm.fit(cand, s):
                            hits.append(os.path.basename(p))
                    except Exception:
                        pass
                row[f"{db}_match"] = len(hits)
                row[f"{db}_hits"] = ";".join(sorted(set(hits))[:5])
                summary[db]["key_candidates"] += 1 if entries else 0
                summary[db]["struct_candidates"] += 1 if hits else 0
                summary[db]["struct_hits"] += len(hits)
        rows.append(row)
        if i % 10 == 0 or i == len(files):
            print(f"{i}/{len(files)}", flush=True)

    cols = ["engine", "name", "key", "volume", "error"]
    for db in dbs:
        cols += [f"{db}_key", f"{db}_match", f"{db}_hits"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print("\n=== summary ===")
    for db in dbs:
        n_c = sum(1 for r in rows if r[f"{db}_match"] > 0)
        n_k = sum(1 for r in rows if r[f"{db}_key"] > 0)
        print(f"{db}: candidates with same formula {n_k}, structural matches {n_c}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
