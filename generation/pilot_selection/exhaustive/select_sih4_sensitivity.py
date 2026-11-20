#!/usr/bin/env python3
"""SiH4 力场敏感性候选：多组分研究候选中取 5 设计 + 3 已知。"""
import hashlib, os
from datetime import datetime, timezone
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C = pd.read_csv(os.path.join(HERE, "multicomponent_candidates.csv"))
sel = pd.concat([C[C.arm == "generated"].head(5), C[C.arm == "known_library"].head(3)],
                ignore_index=True)
out = os.path.join(HERE, "sih4_sensitivity_candidates.csv")
sel.to_csv(out, index=False)
h = hashlib.sha256(open(out, "rb").read()).hexdigest()
reg = f"""# SiH4 单点 LJ 参数敏感性（2026-10-30）

- 候选文件：`generation/pilot_selection/exhaustive/sih4_sensitivity_candidates.csv`，sha256 `{h}`
- 问题：SiH4 单点 LJ 参数调整是否改变 S_CO2 / q_SiH4 以及命中判定？
- 基线：ε/kB = 207.6 K、σ = 4.084 Å（现有模型，普查结果直接作基线）。
- 变体：ε −20%（166.08）、ε +20%（249.12）、σ −0.1 Å（3.984）、σ +0.1 Å（4.184）。
- 候选：{len(sel)} 个（5 设计 + 3 已知，均为二元普查命中结构）。
- 条件：298 K、1 bar、CO₂ 1000 ppm + SiH₄ 平衡；PACMOF/UFF/Ewald；30k/5k。
- 判定：沿用冻结标准；分析 logS_CO2、q_SiH4 的相对变化及命中集合变化。
- 预算：{len(sel)*4} 个 GCMC（4 变体 × {len(sel)}）。
- 登记时间：{datetime.now(timezone.utc).isoformat()}
"""
open(os.path.join(HERE, "sih4_sensitivity_registration.md"), "w", encoding="utf-8").write(reg)
print(sel[["mof", "arm"]].to_string(index=False)); print("sha256", h)
