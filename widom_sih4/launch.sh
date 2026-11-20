#!/bin/bash
# 并行跑全部 Widom 任务。用法: bash launch.sh <runs目录> <并行核数> [单任务超时秒数，默认 14400]
# - 按超胞原子数从大到小排，pol（Ewald，慢）优先，减少尾部等待
# - 已完成（输出含 "Simulation finished"）的目录自动跳过，可断点续跑
# - 超时的任务写 TIMEOUT 标记，不影响其他任务
set -u
RUNS=$(realpath "$1"); NP=${2:-8}; TMO=${3:-14400}
command -v simulate >/dev/null || { echo "找不到 simulate（RASPA2），请先 source RASPA 环境"; exit 1; }
list=$(mktemp)
python3 - "$RUNS" > "$list" <<'PY'
import csv, sys, os
runs = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(runs, "jobs.csv"))))
rows.sort(key=lambda r: -int(r["atoms_in_supercell"]))
for g in ("pol", "np"):
    for r in rows:
        print(os.path.join(runs, r["mof"], g))
PY
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
