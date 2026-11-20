#!/bin/bash
# 多组分 GCMC：构建输入 -> 运行 -> 自动解析
set -u
GEN=/share/rickyswork/ai_mof/generation
DIR=$GEN/pilot_selection/exhaustive
RUNS=$DIR/multicomponent
python3 $DIR/make_multicomponent_inputs.py --candidates $DIR/multicomponent_candidates.csv \
  --base-runs $DIR/campaign_runs --out "$RUNS" --ff-dir /share/rickyswork/ai_mof/widom_sih4
for cond in T298_P1 T273_P1 T323_P1 T298_P5; do
  bash $GEN/launch_gcmc.sh "$RUNS/$cond" 5 14400 >> $DIR/multicomponent.log 2>&1 &
done
wait
cd $GEN/pilot_selection && python3 $DIR/parse_gcmc_multi.py exhaustive/multicomponent \
  --out exhaustive/multicomponent_results.csv > $DIR/multicomponent_parse.log 2>&1
date > $DIR/MULTI_PARSED
