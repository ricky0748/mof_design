#!/bin/bash
# 并行跑 GCMC：launch_gcmc.sh <gcmc_runs目录> <并行数> [单任务超时秒数]
set -u
RUNS=$(realpath "$1"); NP=${2:-12}; TMO=${3:-14400}
list=$(mktemp)
find "$RUNS" -mindepth 2 -maxdepth 2 -type d -name gcmc > "$list"
run_one() {
  d=$1; tmo=$2
  [ -f "$d/simulation.input" ] || exit 0
  if grep -qs "Simulation finished" "$d"/Output/System_0/*.data 2>/dev/null; then exit 0; fi
  cd "$d" && rm -rf Output Movies VTK Restart TIMEOUT
  timeout "$tmo" simulate simulation.input > raspa.log 2>&1 || { [ $? -eq 124 ] && touch TIMEOUT; }
}
export -f run_one
echo "共 $(wc -l < "$list") 个任务，$NP 并行，开始 $(date)"
xargs -a "$list" -P "$NP" -I{} bash -c 'run_one "$@"' _ {} "$TMO"
echo "完成 $(date)；超时任务数: $(find "$RUNS" -name TIMEOUT | wc -l)"
rm -f "$list"
