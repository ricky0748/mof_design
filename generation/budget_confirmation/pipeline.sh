#!/usr/bin/env bash
set -euo pipefail
OUT=/share/rickyswork/ai_mof/generation/budget_confirmation_20261113
M=/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2
E=/share/rickyswork/ai_mof/envs/mofflow2
EGPY=/share/rickyswork/ai_mof/generation/pilots/EGMOF/.venv/bin/python
MACEPY=/home/ruiqi/miniconda3/envs/mofsimbench/bin/python
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
cd "$OUT"
"$EGPY" -m unittest discover -p 'test_*.py' > tests.log 2>&1
"$EGPY" setup_run.py > setup.log 2>&1
cd "$M"
PROJECT_ROOT=$M PYTHONPATH=$M CUDA_VISIBLE_DEVICES=5 LD_LIBRARY_PATH=$E/lib:${LD_LIBRARY_PATH:-} "$EGPY" "$OUT/stage.py" sequence "$OUT/stage_times.json" -- "$E/bin/python" -m experiments.predict_seq inference.ckpt_path=$OUT/seq_module_cond/ckpt.pt inference.seed=1301 inference.total_samples=600 inference.temperature=1.0 inference.target_property=5.0 inference.batch_size=50 hydra.run.dir=$OUT/hydra_seq > "$OUT/sequence.log" 2>&1
"$EGPY" "$OUT/choose.py" > "$OUT/selection.log" 2>&1
"$EGPY" "$OUT/training_labels.py" > "$OUT/training_labels.log" 2>&1 &
LABEL_PID=$!
PROJECT_ROOT=$M PYTHONPATH=$M CUDA_VISIBLE_DEVICES=5 LD_LIBRARY_PATH=$E/lib:${LD_LIBRARY_PATH:-} "$EGPY" "$OUT/stage.py" native_prediction "$OUT/stage_times.json" -- "$E/bin/python" -m experiments.predict inference.task=gen inference.ckpt_path=$OUT/sp_module/ckpt.pt inference.seed=1301 inference.gen.metal_lib_path=$M/data/metals/metal_lib_train.pkl inference.gen.mof_seqs_path=$OUT/selected_sequences.json inference.num_samples=1 inference.num_devices=1 hydra.run.dir=$OUT/hydra_pred > "$OUT/prediction.log" 2>&1
cd "$OUT"
LD_LIBRARY_PATH=$E/lib:${LD_LIBRARY_PATH:-} "$E/bin/python" convert.py > convert.log 2>&1
"$EGPY" build.py > build.log 2>&1
"$MACEPY" run.py "$OUT" --phase controls > controls_run.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/controls_manifest.jsonl" "$OUT/mofid_controls" --workers 2 --timeout 180 > controls_mofid.log 2>&1
"$EGPY" calibrate.py > calibration.log 2>&1
"$MACEPY" run.py "$OUT" --phase primary > primary.log 2>&1
"$MACEPY" run.py "$OUT" --phase secondary > secondary.log 2>&1
"$MACEPY" run.py "$OUT" --phase manifest > manifest.log 2>&1
PATH=/share/rickyswork/ai_mof/tools/jre17/bin:/usr/bin:/bin PYTHONPATH=/share/rickyswork/ai_mof/tools/mofid_python python3 /share/rickyswork/ai_mof/tools/mofid_validate.py "$OUT/manifest.jsonl" "$OUT/mofid" --workers 8 --timeout 180 > mofid.log 2>&1
wait "$LABEL_PID"
"$EGPY" report.py > report.log 2>&1
"$EGPY" audit.py > audit.log 2>&1

