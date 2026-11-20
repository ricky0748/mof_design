"""生成 Widom 用力场文件：框架沿用 CRAFTED 的 UFF（与 CO2/N2 摸底一致），追加 SiH4 和常规杂质分子。

吸附质参数与来源（全部刚性，Lorentz-Berthelot 混合，12.8 Å 截断，shifted，无尾修正，Ewald）：
  SiH4  单位点 LJ  ε/k=207.6 K σ=4.084 Å          Svehla 1962 (NASA TR R-132)；Bird-Stewart-Lightfoot 表 E.1
        ※ 由气相输运性质反推的粗模型，未对吸附校验，见 README "力场风险"
  H2    单位点 LJ  ε/k=34.2 K  σ=2.96 Å           Buch 1994（MOF 中 H2 常用，忽略四极矩）
  N2    TraPPE 3 位点  N: 36.0 K, 3.31 Å, q=-0.482；COM q=+0.964；N–N 1.10 Å   Potoff & Siepmann 2001（与 CRAFTED 相同）
  O2    TraPPE 3 位点  O: 49.0 K, 3.02 Å, q=-0.113；COM q=+0.226；O–O 1.21 Å   Zhang & Siepmann 2005
  Ar    单位点 LJ  ε/k=119.8 K σ=3.40 Å           RASPA 示例 / Hirschfelder
  CH4   TraPPE-UA   ε/k=148.0 K σ=3.73 Å           Martin & Siepmann 1998
  CO    3 位点      C: 16.141 K, 3.636 Å, q=-0.2424；O: 98.014 K, 2.979 Å, q=-0.2744；COM q=+0.5168；C–O 1.128 Å
                                                    Martín-Calero et al. 2006
  CO2   TraPPE 3 位点（与 CRAFTED 相同）            Potoff & Siepmann 2001
"""
import os, sys

CRAFTED_UFF = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/mnt/MOF-公开数据库/CRAFTED-2.0.0/FORCEFIELDS/UFF")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff")
os.makedirs(OUT, exist_ok=True)

# (type, mass, charge, eps_K, sigma_A)；eps=None 表示无 LJ 的电荷点
ADS = [
    ("C_co2", 12.0107, 0.700, 27.0, 2.80), ("O_co2", 15.9994, -0.350, 79.0, 3.05),
    ("N_n2", 14.0067, -0.482, 36.0, 3.31), ("N_com", 0.0, 0.964, None, None),
    ("SiH4_sp", 32.1173, 0.0, 207.6, 4.084),
    ("H2_sp", 2.01588, 0.0, 34.2, 2.96),
    ("O_o2", 15.9994, -0.113, 49.0, 3.02), ("O_com", 0.0, 0.226, None, None),
    ("Ar_sp", 39.948, 0.0, 119.8, 3.40),
    ("CH4_sp3", 16.04246, 0.0, 148.0, 3.73),
    ("C_co", 12.0107, -0.2424, 16.141, 3.636), ("O_co", 15.9994, -0.2744, 98.014, 2.979), ("CO_com", 0.0, 0.5168, None, None),
]

with open(os.path.join(OUT, "pseudo_atoms.def"), "w") as f:
    f.write("#number of pseudo atoms\n%d\n" % len(ADS))
    f.write("#type       print   as    chem  oxidation   mass        charge   polarization B-factor radii  connectivity anisotropic anisotropic-type   tinker-type\n")
    for t, m, q, e, s in ADS:
        chem = "".join(c for c in t.split("_")[0] if c.isalpha())[:2]
        chem = chem if chem in ("Si", "Ar") else chem[:1]
        f.write("%-12s %-7s %-5s %-5s 0  %10.5f  %9.5f  0.0  1.0  0.7000  0  0  relative  0\n"
                % (t, "no" if m == 0.0 else "yes", chem, chem, m, q))

# 框架部分：原样拷贝 CRAFTED 的 UFF 相互作用行
src = open(os.path.join(CRAFTED_UFF, "force_field_mixing_rules.def")).read().splitlines()
fw = [l for l in src[6:] if l.strip() and not l.startswith("#") and not l.split()[0] in
      ("C_co2", "O_co2", "N_n2", "N_com") and "lennard-jones" in l]
ads_lines = []
for t, m, q, e, s in ADS:
    ads_lines.append("%-14s none" % t if e is None else "%-14s lennard-jones  %10.4f  %8.4f" % (t, e, s))
with open(os.path.join(OUT, "force_field_mixing_rules.def"), "w") as f:
    f.write("# general rule for shifted vs truncated\nshifted\n# general rule for tail corrections\nno\n")
    f.write("# number of defined interactions\n%d\n# type,        interaction,  epsilon [K],  sigma [A]\n" % (len(fw) + len(ads_lines)))
    f.write("\n".join(fw + ads_lines) + "\n# mixing rule\nLorentz-Berthelot\n")
with open(os.path.join(OUT, "force_field.def"), "w") as f:
    f.write("# rules to overwrite\n0\n# number of defined interactions\n0\n# mixing rules to overwrite\n0\n")
print("framework types:", len(fw), " adsorbate types:", len(ads_lines))
