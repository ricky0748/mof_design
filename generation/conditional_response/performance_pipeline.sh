#!/usr/bin/env bash
set -euo pipefail
cd /share/rickyswork/ai_mof/generation/conditional_response_20261116
for ((i=0; i<720; i++)); do
  if [[ -f STRUCTURE_ANALYSIS_DONE && -f performance_preflight_v3/result.json ]]; then break; fi
  sleep 10
done
test -f STRUCTURE_ANALYSIS_DONE
PYTHONPATH=/share/rickyswork/ai_mof/pacmof OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 performance.py > performance.log 2>&1
python3 analyze_performance.py > performance_analysis.log 2>&1
