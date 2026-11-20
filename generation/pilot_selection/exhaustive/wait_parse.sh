#!/bin/bash
# 等待 737 个 GCMC 全部结束后自动解析（服务器端运行，setsid 保活）
set -u
GEN=/share/rickyswork/ai_mof/generation
DIR=$GEN/pilot_selection/exhaustive
while pgrep -f "launch_gcmc.sh .*campaign_runs" > /dev/null; do sleep 300; done
sleep 60
cd $GEN/pilot_selection && python3 ../parse_gcmc.py exhaustive/campaign_runs --out exhaustive/campaign_results.csv > $DIR/parse.log 2>&1
date > $DIR/PARSED
