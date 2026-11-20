#!/bin/bash
set -u
G=/share/rickyswork/ai_mof/generation/pilots/EGMOF/scale1000
PY=/home/ruiqi/miniconda3/envs/mofsimbench/bin/python
U=$G/plausibility/uff
while [ ! -f "$U/ALL_DONE" ]; do sleep 60; done
$PY /tmp/uff_summary.py --uff-dir "$U" --orig-dir "$G/cif" --out-cif "$U/prim" --out-csv "$U/uff_summary.csv" > "$U/uff_summary.log" 2>&1
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
$PY /tmp/combine_mace.py "$U/uff_summary.csv" "$U/mace" "$G/plausibility/combined.csv" > "$G/plausibility/combine.log" 2>&1
echo DONE > "$G/plausibility/PIPE_DONE"
