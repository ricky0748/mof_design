#!/usr/bin/env python3
"""选出多组分 / 过程条件研究的候选：二元普查命中结构里 logS_CO2 最高的 10 设计 + 5 已知。"""
import hashlib, os
from datetime import datetime, timezone
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
R = pd.read_csv(os.path.join(HERE, "campaign_results_partial.csv"))
S = pd.read_csv(os.path.join(HERE, "campaign_selected.csv"))
M = S.merge(R, on="mof", how="left")
M = M[M.status == "ok"].copy()
M["hit"] = (M.logS_CO2 >= 0.3) & (M.q_SiH4 <= 1.5) & (M.q_CO2 >= 0.001)
H = M[M.hit]

design = H[H.arm == "generated"].sort_values("logS_CO2", ascending=False).head(10)
known = H[H.arm == "known_library"].sort_values("logS_CO2", ascending=False).head(5)
C = pd.concat([design, known], ignore_index=True)
C = C[["mof", "arm", "topo", "route", "logS_CO2", "q_SiH4", "q_CO2", "pred_S_CO2"]]
C = C.rename(columns={"logS_CO2": "binary_logS", "q_SiH4": "binary_q_SiH4",
                      "q_CO2": "binary_q_CO2", "pred_S_CO2": "binary_pred"})
out = os.path.join(HERE, "multicomponent_candidates.csv")
C.to_csv(out, index=False)
h = hashlib.sha256(open(out, "rb").read()).hexdigest()

reg = f"""# 多组分 GCMC / 过程条件（2026-10-30）

- 候选文件：`generation/pilot_selection/exhaustive/multicomponent_candidates.csv`，sha256 `{h}`
- 问题：二元普查的头部命中结构，在加入 N₂/CH₄ 与改变温压后，是否仍保持选择性与容量？
- 候选来源：737 普查已完成结果中，按 logS_CO2 取设计臂前 10、已知库臂前 5（均为冻结判定下的命中结构）。
- 组成（4 组分，ppm 级为代理值）：SiH₄ 0.997、CO₂ 0.001、N₂ 0.001、CH₄ 0.001。
- 条件矩阵：298 K/1 bar（与二元基线直接对照）、273 K/1 bar、323 K/1 bar、298 K/5 bar。
- 精算：PACMOF/UFF/Ewald；30k cycles / 5k init；单位胞沿用对应二元运行。
- 判定（沿用冻结标准）：logS_CO2 ≥ 0.3、q_SiH4 ≤ 1.5、q_CO2 ≥ 0.001；并记录 S_N2、S_CH4。
- 预算：{len(C)} 候选 × 4 条件 = {len(C)*4} 个 GCMC。
- 分析：与二元基线比较 S_CO2/q_SiH4 的变化；Spearman 排名相关；各条件下命中集合的变化。
- 登记时间：{datetime.now(timezone.utc).isoformat()}
"""
open(os.path.join(HERE, "multicomponent_registration.md"), "w", encoding="utf-8").write(reg)
print(C.round(3).to_string(index=False))
print("sha256", h)
