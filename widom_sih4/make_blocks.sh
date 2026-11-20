#!/bin/bash
# 【可选，未在本次测试中验证】用 Zeo++ 为每个 MOF × 分子生成不可及孔袋的 block 文件，
# 避免 Widom 把分子插进分子进不去的孤立孔袋（会高估 K，对 SiH4 这类大分子影响最大）。
# 用法: bash make_blocks.sh <CRAFTED DDEC CIF 目录> <输出目录> [并行数]
# 探针半径取动力学直径/2（Å）。生成后：python3 make_inputs.py ... --block-dir <输出目录>
set -u
CIFDIR=$1; OUT=$2; NP=${3:-8}
command -v network >/dev/null || { echo "找不到 Zeo++ 的 network 命令"; exit 1; }
mkdir -p "$OUT"
declare -A R=( [SiH4]=2.04 [CH4]=1.90 [Ar]=1.70 [H2]=1.445 [N2]=1.82 [O2]=1.73 [CO]=1.88 [CO2]=1.65 )
for cif in "$CIFDIR"/*.cif; do
  m=$(basename "$cif" .cif); [[ "$m" =~ N[0-9]$ ]] && continue   # 跳过 CURATED-COF
  for mol in "${!R[@]}"; do echo "$cif $m $mol ${R[$mol]}"; done
done | xargs -P "$NP" -n 4 sh -c 'network -ha -block "$3" 200 "'"$OUT"'/$1_$2.block" "$0" > /dev/null 2>&1'
echo "生成 $(ls "$OUT"/*.block 2>/dev/null | wc -l) 个 block 文件 -> $OUT"
