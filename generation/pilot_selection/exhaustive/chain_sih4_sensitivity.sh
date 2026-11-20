#!/bin/bash
# 等多组分 campaign 结束后再启动 SiH4 敏感性，避免过载
set -u
DIR=/share/rickyswork/ai_mof/generation/pilot_selection/exhaustive
while pgrep -f "launch_multicomponent.sh" > /dev/null; do sleep 300; done
sleep 60
bash $DIR/launch_sih4_sensitivity.sh
