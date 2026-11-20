#!/usr/bin/env python3
"""MOFFlow-2 生成序列的化学后过滤（仅序列级，不需要结构结果）。
用法: python chem_filter_seqs.py <preds.json> <out.csv>
复用 /tmp/filter_generated_sbus.py 的 check_sbu / split_seq / is_metal / has_carbon。
"""
import sys
import json
import csv

sys.path.insert(0, "/tmp")
from filter_generated_sbus import check_sbu, split_seq, is_metal, has_carbon, NODE_ANIONS  # noqa: E402


def main():
    preds_path, out = sys.argv[1], sys.argv[2]
    seqs = json.load(open(preds_path))
    rows = []
    for i, s in enumerate(seqs):
        parts = split_seq(s)
        bad = []
        n_org = 0
        hard_all = True
        guest = False
        for p in parts:
            if is_metal(p):
                continue
            if not has_carbon(p):
                if p in NODE_ANIONS:
                    continue
                guest = True
                bad.append((p[:60], ["non_mof_guest"]))
                hard_all = False
                continue
            n_org += 1
            ok, reasons, info = check_sbu(p)
            hard_all = hard_all and info.get("hard_ok", False)
            if not ok:
                bad.append((p[:60], reasons))
        rows.append(dict(seq_idx=i, n_sbu=len(parts), n_org=n_org,
                         hard_pass=int(n_org > 0 and hard_all),
                         chem_pass=int(n_org > 0 and not bad),
                         no_guest=int(not guest),
                         reasons=";".join(f"{p}:{','.join(r)}" for p, r in bad)[:400]))
    n = len(rows)
    h = sum(r["hard_pass"] for r in rows)
    c = sum(r["chem_pass"] for r in rows)
    ng = sum(r["no_guest"] for r in rows)
    print(f"sequences {n}: hard-valid {h} ({h/n:.1%}), linker-suitable {c} ({c/n:.1%}), "
          f"no-guest {ng} ({ng/n:.1%})")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
