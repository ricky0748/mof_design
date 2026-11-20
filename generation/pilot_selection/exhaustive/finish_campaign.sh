#!/bin/bash
# 主批量结束后：用更长超时重跑 11 个超时任务（大超胞），再统一解析
set -u
GEN=/share/rickyswork/ai_mof/generation
DIR=$GEN/pilot_selection/exhaustive
RUNS=$DIR/campaign_runs
while pgrep -f "launch_gcmc.sh .*campaign_runs 48 18000" > /dev/null; do sleep 120; done
sleep 30
echo "main batch done $(date); retrying timeouts" > $DIR/retry.log
bash $GEN/launch_gcmc.sh "$RUNS" 11 43200 >> $DIR/retry.log 2>&1
cd $GEN/pilot_selection && python3 ../parse_gcmc.py exhaustive/campaign_runs --out exhaustive/campaign_results.csv > $DIR/parse.log 2>&1
echo "parsed $(date); remaining timeouts: $(find $RUNS -name TIMEOUT | wc -l)" >> $DIR/retry.log
date > $DIR/PARSED
