#!/usr/bin/env python3
"""全池普查：设计池 vs 已知库 的等条件 GCMC 命中密度对照。

与 UCB 小样本对照不同，这里不做任何代理选择：
  - 设计臂：所有通过护栏的规则式取代变体（含 proxy / gcmc 两种路由）
  - 已知臂：所有通过同样护栏的 CRAFTED MOF
两臂用相同的 GCMC 条件，最终比较完整命中率（census，而非抽样）。

输出 campaign_selected.csv + campaign_registration.md（含 sha256）。
"""
import hashlib, os
from datetime import datetime, timezone
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

VALIDATED = {"V0039_nbo", "V0164_nbo", "V0037_nbo", "V0033_nbo", "V0032_nbo", "V0036_nbo",
             "V0017_nbo", "V0156_nbo", "V0035_nbo", "V0058_nbo", "V0064_fcu", "V0003_fcu",
             "V0001_fcu", "V0000_nbo", "V0011_nbo"}
PILOT = {"V0157_nbo", "V0031_nbo", "V0041_nbo", "V0034_nbo", "V0023_nbo",
         "V0015_pcu", "V0053_nbo", "V0042_pcu", "V0140_fcu", "V0013_pcu"}
FEEDBACK = {"V0006_nbo", "V0048_nbo", "V0047_nbo", "V0067_nbo", "V0024_nbo"}
MIN_DFS, MIN_AV = 3.3, 0.02


def main():
    crafted = pd.read_csv(os.path.join(ROOT, "widom_sih4/results/crafted_zeo.csv"))
    genz = pd.read_csv(os.path.join(ROOT, "widom_sih4/results/gen_zeo.csv")).rename(columns={"name": "mof"})
    scored = pd.read_csv(os.path.join(ROOT, "generation/scored_full.csv"))

    known = crafted[(crafted.D_fs >= MIN_DFS) & (crafted.AV_Volume_fraction >= MIN_AV)].copy()
    known = known[["name", "D_fs", "AV_Volume_fraction"]].rename(columns={"name": "mof"})
    known["arm"] = "known_library"
    known["smiles"] = None
    known["topo"] = None
    known["route"] = None
    known["pred_S_CO2"] = None

    gen = scored.merge(genz[["mof", "D_fs", "AV_Volume_fraction"]], on="mof")
    gen = gen[(~gen.mof.isin(VALIDATED)) & (~gen.mof.isin(PILOT)) & (~gen.mof.isin(FEEDBACK)) &
              (gen.novelty_tier != "known_control")]
    gen = gen[(gen.D_fs >= MIN_DFS) & (gen.AV_Volume_fraction >= MIN_AV)].copy()
    design = pd.DataFrame({
        "mof": gen.mof, "arm": "generated", "smiles": gen.smiles, "topo": gen.topo,
        "route": gen.action, "pred_S_CO2": gen.pred_S_CO2,
        "D_fs": gen.D_fs, "AV_Volume_fraction": gen.AV_Volume_fraction,
    })
    design["novelty"] = "substituted_variant"

    out = pd.concat([known, design], ignore_index=True)
    out["novelty"] = out.get("novelty")
    out = out.sort_values(["arm", "mof"]).reset_index(drop=True)
    csv_path = os.path.join(HERE, "campaign_selected.csv")
    out.to_csv(csv_path, index=False)
    h = hashlib.sha256(open(csv_path, "rb").read()).hexdigest()

    reg = f"""# 全池普查：设计候选 vs 已知库（GCMC 命中密度）

- 候选文件：`generation/pilot_selection/exhaustive/campaign_selected.csv`，sha256 `{h}`
- 问题：在同一条 GCMC 条件下，**整个**设计候选池与**整个**合格已知库的命中密度各是多少？
- 与 UCB 小样本对照的区别：不做代理选择、不抽样；两臂所有合格结构全部精算。
- 设计臂：{len(design)} 个规则式候选（268 个合格 CIF 中，排除已验证 {len(VALIDATED)}、试点 {len(PILOT)}、反馈 {len(FEEDBACK)}、known control 17 个后，通过护栏者；含 proxy {int((design.route=='proxy').sum())} + gcmc {int((design.route=='gcmc').sum())} 两种路由）。
- 已知臂：{len(known)} 个 CRAFTED MOF（690 个中通过同一护栏者）。
- 护栏（两臂相同）：D_fs ≥ {MIN_DFS} Å、AV_Volume_fraction ≥ {MIN_AV}。
- 精算条件：298 K、1 bar、CO₂ 1000 ppm + SiH₄ 平衡；PACMOF/UFF/Ewald；30k cycles / 5k init；与既往一致。
- 判定（运行前冻结）：GCMC logS_CO2 ≥ 0.3 **且** q_SiH4 ≤ 1.5 mol/kg **且** q_CO2 ≥ 0.001 mol/kg。阈值敏感性（q_SiH4 ≤ 2.0 / 2.5）另行报告。
- 预算：共 {len(out)} 个 GCMC；不追加、不中途看结果改协议。
- 说明：设计臂的结构来自规则式枚举 + PORMAKE 组装 + PACMOF 电荷；已知臂来自 CRAFTED。两臂均未使用代理分数做取舍，代理预测仅用于事后校准分析。
- 登记时间：{datetime.now(timezone.utc).isoformat()}
"""
    open(os.path.join(HERE, "campaign_registration.md"), "w", encoding="utf-8").write(reg)
    print(f"design {len(design)} (proxy {int((design.route=='proxy').sum())}, gcmc {int((design.route=='gcmc').sum())}) + known {len(known)} = {len(out)}")
    print("sha256", h)


if __name__ == "__main__":
    main()
