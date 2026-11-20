#!/usr/bin/env bash
set -euo pipefail
cd /share/rickyswork/ai_mof/generation/convergence_sensitivity_20261116
for ((i=0; i<180; i++)); do
  if [[ -f RELAX_DONE ]]; then break; fi
  sleep 10
done
test -f RELAX_DONE
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python python3 /share/rickyswork/ai_mof/tools/mofid_validate.py manifest.jsonl mofid --workers 8 --timeout 180 > mofid.log 2>&1
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
"$EGPY" report.py > report.log 2>&1
"$EGPY" audit.py > audit.log 2>&1
touch ANALYSIS_DONE
