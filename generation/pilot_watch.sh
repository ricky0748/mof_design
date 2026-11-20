#!/bin/bash
SSH="ssh -n -o ConnectTimeout=20 -o BatchMode=yes -i $HOME/.ssh/id_rsa -p 2242 ruiqi@36.103.234.242"
REMOTE=/share/rickyswork/ai_mof/generation/pilots/EGMOF
LOCAL=/c/Users/PC/Desktop/skills_all/ai_mof/generation
for i in $(seq 1 72); do
  d=$($SSH "test -f $REMOTE/smoke/SMOKE_DONE && echo 1 || echo 0" 2>/dev/null)
  p=$($SSH "stat -c %s $REMOTE/checkpoints/prop2desc_ckpt.zip 2>/dev/null || echo 0")
  u=$($SSH "pgrep -f 'uv sync' >/dev/null && echo 1 || echo 0" 2>/dev/null)
  echo "$(date +%H:%M) smoke_done=${d:-0} prop2desc=$(( ${p:-0} / 1000000 ))MB uv_running=${u:-?}"
  [ "$d" = "1" ] && break
  sleep 300
done
mkdir -p "$LOCAL/pilots_smoke"
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/smoke/smoke.log "$LOCAL/pilots_smoke/" 2>/dev/null
scp -q -i $HOME/.ssh/id_rsa -P 2242 ruiqi@36.103.234.242:$REMOTE/smoke/samples.csv "$LOCAL/pilots_smoke/" 2>/dev/null
echo DONE
