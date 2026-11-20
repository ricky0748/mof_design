#!/bin/bash
# SiH4 LJ 敏感性：构建 4 个变体输入 -> 各 4 并行运行 -> 解析并合并
set -u
GEN=/share/rickyswork/ai_mof/generation
DIR=$GEN/pilot_selection/exhaustive
OUT=$DIR/sih4_sensitivity
python3 $DIR/make_sih4_sensitivity_inputs.py --candidates $DIR/sih4_sensitivity_candidates.csv \
  --base-runs $DIR/campaign_runs --out $OUT --ff-dir /share/rickyswork/ai_mof/widom_sih4
for v in eps_m20 eps_p20 sig_m01 sig_p01; do
  bash $GEN/launch_gcmc.sh "$OUT/$v" 4 14400 >> $DIR/sih4_sensitivity.log 2>&1 &
done
wait
cd $GEN/pilot_selection
for v in eps_m20 eps_p20 sig_m01 sig_p01; do
  python3 ../parse_gcmc.py "exhaustive/sih4_sensitivity/$v" --out "exhaustive/sih4_sensitivity/results_$v.csv" > /dev/null 2>&1
done
python3 $DIR/merge_sih4_sensitivity.py > $DIR/sih4_sensitivity_parse.log 2>&1
date > $DIR/SIH4_PARSED
