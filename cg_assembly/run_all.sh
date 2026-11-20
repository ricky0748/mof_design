#!/bin/bash
# 在服务器 hoomd5 环境中运行：conda activate hoomd5 && bash run_all.sh [并行数]
# 每个用例 3 个随机种子；单个 200k 步，CPU。
P=${1:-6}
mkdir -p runs results
# 冒烟测试：每类节点各跑 2000 步，确认 API/参数无误再全量
for c in C0_patchy3_rod_s1 C2_BDC_pw_s1 C4_BDC_oct_s1 C5_BTC_pw_s1; do python run_cg.py cases/$c.npz smoke 2000 || exit 1; done
ls cases/*.npz | xargs -P $P -I{} sh -c 'n=$(basename {} .npz); python run_cg.py {} runs > runs/$n.out 2>&1 && python analyze_cg.py {} runs/$n.gsd --json results/$n.json > /dev/null'
python summarize.py results > results/summary.txt && cat results/summary.txt
