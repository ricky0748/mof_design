#!/usr/bin/env bash
set -euo pipefail
OUT=/share/rickyswork/ai_mof/generation/coordination_followup_20261113
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
cd "$OUT"
"$EGPY" freeze.py > freeze.log 2>&1
/home/ruiqi/miniconda3/envs/mofsimbench/bin/python run.py "$OUT" > run.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/manifest.jsonl" "$OUT/mofid" --workers 5 --timeout 180 > mofid.log 2>&1
"$EGPY" report.py > report.log 2>&1
