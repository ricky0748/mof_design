#!/bin/bash
set -u
S=/share/rickyswork/ai_mof/generation/pilots/MOFDiff/pretrained/mofdiff_ckpt/samples_1000_seed_42
P=/share/rickyswork/ai_mof/generation/pilots/MOFDiff/scale1000
PY=/home/ruiqi/miniconda3/envs/mofsimbench/bin/python
while [ ! -f "$S/assembled.pt" ]; do sleep 60; done
mkdir -p "$P/plausibility"
$PY -u /tmp/precheck_dir.py "$S/cif" "$P/plausibility/precheck.csv" --tag MOFDiff-scale1000 > "$P/plausibility/precheck.log" 2>&1
$PY -u /tmp/dedup_dir2.py "$S/cif" "$P/plausibility/dedup.csv" --tag MOFDiff-scale1000 > "$P/plausibility/dedup2.log" 2>&1
rm -rf "$P/cif"; cp -r "$S/cif" "$P/cif"
bash /tmp/run_uff_batch.sh "$P" > "$P/plausibility/uff_batch.log" 2>&1
echo DONE > "$P/plausibility/PIPE_DONE"
