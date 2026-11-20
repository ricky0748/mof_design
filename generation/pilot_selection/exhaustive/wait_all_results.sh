#!/bin/bash
# 等待多组分、SiH4 敏感性、CoRE2019 novelty 全部结束，拉回结果
SSH="ssh -n -o ConnectTimeout=20 -o BatchMode=yes -i $HOME/.ssh/id_rsa -p 2242 ruiqi@36.103.234.242"
REMOTE=/share/rickyswork/ai_mof/generation/pilot_selection/exhaustive
LOCAL=/c/Users/PC/Desktop/skills_all/ai_mof/generation/pilot_selection/exhaustive
for i in $(seq 1 72); do
  m=$($SSH "grep -l 'Simulation finished' $REMOTE/multicomponent/*/*/gcmc/Output/System_0/*.data 2>/dev/null | wc -l" 2>/dev/null)
  s=$($SSH "grep -l 'Simulation finished' $REMOTE/sih4_sensitivity/*/*/gcmc/Output/System_0/*.data 2>/dev/null | wc -l" 2>/dev/null)
  c=$($SSH "test -f $REMOTE/novelty_core2019/core2019_matches.csv && echo 1 || echo 0" 2>/dev/null)
  echo "$(date +%H:%M) multi=${m:-?}/60 sih4=${s:-?}/32 core2019=${c:-?}"
  if [ "${m:-0}" -ge 60 ] && [ "${s:-0}" -ge 32 ] && [ "$c" = "1" ]; then break; fi
  sleep 300
done
$SSH "test -f $REMOTE/MULTI_PARSED && echo MULTI_PARSED; test -f $REMOTE/SIH4_PARSED && echo SIH4_PARSED" 2>/dev/null
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/multicomponent_results.csv $LOCAL/ 2>/dev/null
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/sih4_sensitivity_results.csv $LOCAL/ 2>/dev/null
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/sih4_sensitivity_summary.csv $LOCAL/ 2>/dev/null
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/novelty_core2019/core2019_matches.csv $LOCAL/ 2>/dev/null
echo DONE
