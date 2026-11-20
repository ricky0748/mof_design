#!/usr/bin/env bash
set -euo pipefail
cd /share/rickyswork/ai_mof/generation/conditional_response_20261116
for ((i=0; i<180; i++)); do
  if [[ -f GENERATION_DONE ]]; then break; fi
  sleep 10
done
test -f GENERATION_DONE
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
"$EGPY" select_candidates.py > selection.log 2>&1
"$EGPY" build.py > build.log 2>&1
/home/ruiqi/miniconda3/envs/mofsimbench/bin/python run_structures.py > structures.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python python3 /share/rickyswork/ai_mof/tools/mofid_validate.py manifest.jsonl mofid --workers 8 --timeout 180 > mofid.log 2>&1
"$EGPY" summarize_structures.py > structure_summary.log 2>&1
