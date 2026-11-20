#!/usr/bin/env bash
set -euo pipefail
ROOT=/share/rickyswork/ai_mof
OUT=$ROOT/generation/mofid_validation/full_reference
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
mkdir -p "$OUT"
"$ROOT/envs/mofflow2/bin/python" "$ROOT/tools/mofid_prepare.py" --root "$ROOT" --out "$OUT" --limit 0 > "$OUT/prepare.log" 2>&1
export PATH="$ROOT/tools/jre17/bin:/usr/bin:/bin"
export PYTHONPATH="$ROOT/tools/mofid_python"
python3 "$ROOT/tools/mofid_validate.py" "$OUT/training_manifest.jsonl" "$OUT/results" --workers 16 --timeout 180 > "$OUT/run.log" 2>&1
# Compare after both stages finish. No absent-from-training label on incomplete reference coverage.
while [ ! -f "$ROOT/generation/mofid_validation/generated/summary.json" ]; do sleep 30; done
python3 "$ROOT/tools/mofid_compare.py" "$OUT/results/results.jsonl" "$ROOT/generation/mofid_validation/generated/results.jsonl" "$ROOT/generation/mofid_validation/comparison" --expected-reference 187047
date -Is > "$OUT/ALL_DONE"
