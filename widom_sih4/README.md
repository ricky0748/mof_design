# SiH4 + 常规杂质 Widom 批量计算（CRAFTED 690 MOF）

目的：给 R² 摸底提供痕量体系的标签。上一轮摸底发现，痕量极限的选择性如果靠等温线拟合外推，噪声会被放大；这一轮直接用 Widom 插入算 Henry 常数。

## 计算设定

| 项目 | 设定 |
|---|---|
| 结构 | CRAFTED-2.0.0 的 690 个 CoRE-2014 MOF，DDEC 电荷 CIF（与上一轮 CO2/N2 摸底同一批） |
| 框架力场 | CRAFTED 的 UFF 参数原样沿用（`build_ff.py` 从 CRAFTED/FORCEFIELDS/UFF 生成） |
| 相互作用 | LJ 12.8 Å 截断、shifted、无尾修正、Lorentz-Berthelot 混合；极性组用 Ewald（精度 1e-6） |
| 晶胞 | 沿用 CRAFTED 每个 MOF 自己 GCMC 输入里的 UnitCells |
| 温度 | 298 K |
| Widom | 默认 5,000 cycles，每个 run 一组 4 个分子 |
| 分组 | `np/`：SiH4、H2、Ar、CH4（无电荷，关闭 Ewald 和框架电荷）；`pol/`：N2、O2、CO、CO2（DDEC 电荷 + Ewald） |

### 吸附质模型

| 分子 | 模型 | 参数 | 来源 |
|---|---|---|---|
| SiH4 | 单位点 LJ | ε/k = 207.6 K，σ = 4.084 Å | Svehla 1962（NASA TR R-132） |
| H2 | 单位点 LJ | ε/k = 34.2 K，σ = 2.96 Å | Buch 1994 |
| N2 | TraPPE 3 位点 | N：36.0 K，3.31 Å，q = −0.482；COM q = +0.964 | Potoff & Siepmann 2001（与 CRAFTED 相同） |
| O2 | TraPPE 3 位点 | O：49.0 K，3.02 Å，q = −0.113；COM q = +0.226 | Zhang & Siepmann 2005 |
| Ar | 单位点 LJ | ε/k = 119.8 K，σ = 3.40 Å | RASPA 示例参数 |
| CH4 | TraPPE-UA | ε/k = 148.0 K，σ = 3.73 Å | Martin & Siepmann 1998 |
| CO | 3 位点 | C：16.141 K，3.636 Å，q = −0.2424；O：98.014 K，2.979 Å，q = −0.2744；COM q = +0.5168 | Martín-Calero et al. 2006 |
| CO2 | TraPPE 3 位点 | C：27.0 K，2.80 Å，q = +0.70；O：79.0 K，3.05 Å，q = −0.35 | Potoff & Siepmann 2001（与 CRAFTED 相同） |

### 力场风险（结果解读时要记住）

- **SiH4 的单位点模型是整套设定里最弱的一环。** 参数来自气相输运性质，没有针对吸附校验过。所有 S_杂质 = K_杂质/K_SiH4 都以它为分母，它的系统偏差会整体平移所有选择性。好在 R² 摸底看的是排序和可解释性，整体平移影响不大；但**绝对选择性数值不能直接用于工艺判断**。后续需要做两件事：用 SiH4 的第二维里系数或饱和蒸气数据校验，或者换成多位点模型（Si + 4H，带电荷）做对照。
- 单位点 H2 忽略了四极矩，在开放金属位附近会低估。
- 框架使用 UFF 加 DDEC 电荷；开放金属位的系统偏差参见 gcmc_mof 项目的结论。

## 运行步骤

```bash
# 0. （已完成）生成力场文件
python3 build_ff.py <CRAFTED-2.0.0>/FORCEFIELDS/UFF

# 1. 生成输入（已在本机生成好，即 runs/ 目录；换机器重新生成也只要几秒）
python3 make_inputs.py --crafted <CRAFTED-2.0.0> --out runs --cycles 5000

# 2. 把 runs/ 传到服务器后并行运行（需要 simulate 在 PATH 里；支持断点续跑）
bash launch.sh runs 64 14400        # 64 并行，单任务超时 4 小时

# 3. 汇总结果
python3 parse_widom.py runs --out results

# 4. R² 摸底（需要 lightgbm；可以在本机或云端跑）
python3 analyze_henry.py --henry results/henry_wide.csv --crafted <CRAFTED-2.0.0> \
    --chem ../r2_probe/chem_features_DDEC.csv --crafted-targets ../r2_probe/targets_all.csv --out results
```

可选（未测试）：先运行 `make_blocks.sh` 用 Zeo++ 生成不可及孔袋的 block 文件，再在第 1 步加上 `--block-dir`。这一步对 SiH4 这类大分子最有意义。

## 已做的验证（云端编译 RASPA 2.0.4，ABUWOJ）

| 检查项 | 结果 |
|---|---|
| 8 个分子合在一个 run 里跑 vs 拆成 np/pol 两组 | Henry 常数在误差内一致 |
| Widom K_N2 vs CRAFTED 等温线外推 | 8.1e-6 vs 8.0e-6 mol/kg/Pa |
| Widom K_CO2 vs CRAFTED 等温线外推 | (4.4–6.2)e-3 ± 30% vs 4.1e-3 |
| Widom CO2 吸附能 vs CRAFTED 低压吸附焓 | −40.1 vs −40.2 kJ/mol |
| 耗时（2,000 cycles，1,792 原子超胞） | np 组 60 s，pol 组 392 s |
| 统计误差（2,000 cycles） | SiH4 约 5%，H2/Ar/CH4/O2/CO 1–4%，N2 约 4–7%，CO2 约 30%（强吸附位点导致，属于 Widom 的固有难点） |

`Matrix Inversion, Gauss-Jordan: Singular Matrix` 提示来自单原子刚性分子的转动惯量矩阵，不影响结果。

## 机时估算

见 `runs/cost_estimate.txt`（按超胞原子数线性外推实测耗时）。CO2 的误差最大；如果需要更准，可以只对 pol 组单独加 cycles 重跑。

## 文件

| 文件 | 作用 |
|---|---|
| `build_ff.py` / `ff/` / `molecules/` | 力场与分子定义 |
| `make_inputs.py` | 生成 runs/ |
| `launch.sh` | 并行运行（带超时和断点续跑） |
| `parse_widom.py` | 汇总为 henry_long.csv / henry_wide.csv |
| `analyze_henry.py` | 计算 SiH4 体系目标量，跑 R² 摸底，并与 CRAFTED 做一致性检查 |
| `make_blocks.sh` | 可选：Zeo++ 生成 block 文件（未测试） |
| `test_ABUWOJ/` | 云端测试的输入与输出摘要 |
