#!/usr/bin/env bash
set -euo pipefail
OUT=/share/rickyswork/ai_mof/generation/linker_framework_pilot_v2_20261113
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
MACEPY=/home/ruiqi/miniconda3/envs/mofsimbench/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
cd "$OUT"
"$EGPY" test_common.py > tests.log 2>&1
"$EGPY" prepare.py "$OUT" > prepare.log 2>&1
"$EGPY" build.py "$OUT" --controls-only > controls_build.log 2>&1
"$MACEPY" run.py "$OUT" --controls-only > controls_run.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python \
python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/controls_manifest.jsonl" "$OUT/mofid_controls" --workers 3 --timeout 180 > controls_mofid.log 2>&1
"$EGPY" evaluate.py "$OUT" --controls-only > calibration.log 2>&1
"$EGPY" build.py "$OUT" > build.log 2>&1
"$MACEPY" run.py "$OUT" > run.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python \
python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/manifest.jsonl" "$OUT/mofid" --workers 8 --timeout 180 > mofid.log 2>&1
"$EGPY" evaluate.py "$OUT" > report.log 2>&1
