#!/bin/bash
set -u
P=/share/rickyswork/ai_mof/generation/pilots/MOFDiff/scale1000
PY=/home/ruiqi/miniconda3/envs/mofsimbench/bin/python
U=$P/plausibility/uff
while [ ! -f "$U/ALL_DONE" ]; do sleep 60; done
$PY /tmp/uff_summary.py --uff-dir "$U" --orig-dir "$P/cif" --out-cif "$U/prim" --out-csv "$U/uff_summary.csv" > "$U/uff_summary.log" 2>&1
$PY - <<EOF
import pandas as pd
U="$U"
R=pd.read_csv(U+"/uff_summary.csv")
fail=[r.name for r in R.itertuples() if not bool(r.uff_ok)]
open(U+"/mace_fail_list.txt","w").write("\n".join(fail)+"\n")
print("fail", len(fail))
EOF
if [ -s "$U/mace_fail_list.txt" ]; then
  mkdir -p "$U/mace"
  $PY /tmp/mace_fallback.py "$U/cif" "$U/mace" "$U/mace_fail_list.txt" > "$U/mace_fallback.log" 2>&1
fi
$PY /tmp/combine_mace.py "$U/uff_summary.csv" "$U/mace" "$P/plausibility/combined.csv" > "$P/plausibility/combine.log" 2>&1
echo DONE > "$P/plausibility/PIPE_DONE"
