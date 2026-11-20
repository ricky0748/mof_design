#!/usr/bin/env bash
set -euo pipefail
OUT=/share/rickyswork/ai_mof/generation/linker_framework_pilot_20261113
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
cd "$OUT"
"$EGPY" -c 'import json; assert json.load(open("control_evaluation.json"))["passed"]'
"$EGPY" build.py "$OUT" > build.log 2>&1
python3 run_relax.py "$OUT" > relax.log 2>&1
python3 evaluate.py manifest "$OUT"
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python \
python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/mofid_manifest.jsonl" "$OUT/mofid" --workers 8 --timeout 180 > mofid.log 2>&1
"$EGPY" evaluate.py report "$OUT" > report.log 2>&1
