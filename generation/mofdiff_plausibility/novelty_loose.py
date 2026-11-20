#!/usr/bin/env python3
"""宽松结构 novelty：元素集合 + 体积窗口 + StructureMatcher。

用于补充 exact-formula 预筛漏掉的“同框架但组成略有差异”的情况。
对每个候选，按元素集合规则和体积比 0.5–2.0 过滤 DB，按体积接近度取前 N 个再匹配。
默认只查 CSD / CoRE 2024 / hMOF（实验 + 常用假设库）；MOSAEC 30 万结构留作 exact pass。

用法: python novelty_loose.py <cand_dir> <index_dir> <out.csv> [--tag T] [--topn 400] [--workers 12]
"""
import os
import sys
import csv
import math
import argparse
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor

from pymatgen.io.cif import CifParser
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

sys.path.insert(0, "/tmp")
from fast_db_index import index_one  # noqa: E402

try:
    sys.path.insert(0, "/share/rickyswork/ai_mof/generation/pilot_selection/exhaustive")
    from structure_novelty import parse_cif_loose  # noqa: E402
except Exception:  # noqa
    parse_cif_loose = None

ALLOWED_EXTRA = {"H", "Cl", "Br", "I"}


def split_key(key):
    els, metals = set(), set()
    for part in key.split(";"):
        el = "".join(ch for ch in part if ch.isalpha() or (ch.islower() and len(part) > 1))
        # 简化：元素符号是开头大写+可选小写
        import re
        m = re.match(r"([A-Z][a-z]?)", part)
        if m:
            e = m.group(1)
            els.add(e)
            if e not in {"H", "B", "C", "N", "O", "F", "P", "S", "Cl", "Br", "I", "Se"}:
                metals.add(e)
    return els, metals


def parse_db_struct(db, path):
    if db == "CSD_MOF_Collection" and parse_cif_loose is not None:
        return parse_cif_loose(path)
    try:
        return CifParser(path, occupancy_tolerance=1).parse_structures(primitive=False)[0]
    except Exception:
        try:
            return Structure.from_file(path)
        except Exception:
            return None


def build_db(db, index_dir):
    p = os.path.join(index_dir, db + "_idx.csv")
    out = []
    for r in csv.DictReader(open(p)):
        if r.get("error"):
            continue
        try:
            els, metals = split_key(r["key"])
            out.append((r["path"], float(r["volume"]), els, metals))
        except Exception:
            pass
    return out


DB_CACHE = {}


def check_candidate(args):
    cand_path, name, dbs, topn = args
    rec = index_one(cand_path)
    if rec.get("error"):
        return dict(name=name, error=rec["error"])
    import re
    cels, cmetals = split_key(rec["key"])
    allowed = cels | ALLOWED_EXTRA
    sm = StructureMatcher(ltol=0.3, stol=0.5, angle_tol=10,
                          primitive_cell=True, scale=True, attempt_supercell=True)
    try:
        cand = CifParser(cand_path, occupancy_tolerance=1).parse_structures(primitive=False)[0]
    except Exception:
        cand = None
    row = dict(name=name, key=rec["key"], volume=rec["volume"], error="")
    for db in dbs:
        entries = DB_CACHE[db]
        filt = []
        for (path, V, els, metals) in entries:
            if not cmetals <= els:
                continue
            if not els <= allowed:
                continue
            ratio = rec["volume"] / V
            if not (0.5 <= ratio <= 2.0):
                continue
            filt.append((abs(math.log(ratio)), path, V))
        filt.sort()
        keep = filt[:topn]
        hits = []
        attempted = 0
        if cand is not None:
            for _, path, V in keep:
                s = parse_db_struct(db, path)
                if s is None:
                    continue
                attempted += 1
                try:
                    if sm.fit(cand, s):
                        hits.append(os.path.basename(path))
                except Exception:
                    pass
        row[f"{db}_filtered"] = len(filt)
        row[f"{db}_attempted"] = attempted
        row[f"{db}_matches"] = len(hits)
        row[f"{db}_hits"] = ";".join(sorted(set(hits))[:5])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cand_dir")
    ap.add_argument("index_dir")
    ap.add_argument("out")
    ap.add_argument("--tag", default="")
    ap.add_argument("--topn", type=int, default=400)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--dbs", nargs="+", default=["CSD_MOF_Collection", "core2024", "hmof"])
    a = ap.parse_args()
    for db in a.dbs:
        DB_CACHE[db] = build_db(db, a.index_dir)
        print(f"{db}: {len(DB_CACHE[db])} entries", flush=True)
    files = sorted(f for f in os.listdir(a.cand_dir) if f.endswith(".cif"))
    jobs = [(os.path.join(a.cand_dir, f), f[:-4], a.dbs, a.topn) for f in files]
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(check_candidate, jobs, chunksize=1), 1):
            r["engine"] = a.tag
            rows.append(r)
            if i % 10 == 0 or i == len(files):
                print(f"{i}/{len(files)}", flush=True)
    cols = ["engine", "name", "key", "volume", "error"]
    for db in a.dbs:
        cols += [f"{db}_filtered", f"{db}_attempted", f"{db}_matches", f"{db}_hits"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print("\n=== summary ===")
    for db in a.dbs:
        nc = sum(1 for r in rows if int(r.get(f"{db}_matches", 0) or 0) > 0)
        print(f"{db}: candidates with structural matches {nc}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
