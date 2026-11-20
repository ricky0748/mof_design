"""从 CRAFTED-2.0.0 抽取 690 个 MOF 在 298 K 下的 CO2/N2 等温线与吸附焓（长表）。
用法: python3 extract_crafted.py <charge_scheme>
"""
import sys, os, csv
ROOT = os.path.expanduser("~/mnt/MOF-公开数据库/CRAFTED-2.0.0")
OUT = os.path.expanduser("~/mnt/ai_mof/r2_probe/raw")
scheme = sys.argv[1]
names = [r["FrameworkName"] for r in csv.DictReader(open(f"{ROOT}/RAC_DBSCAN/CRAFTED_MOF_geometric.csv"))]
rows = []
for n in names:
    for ff in ("UFF", "DREIDING"):
        for gas in ("CO2", "N2"):
            key = f"{scheme}_{n}_{ff}_{gas}_298.csv"
            iso, ent = f"{ROOT}/ISOTHERM_FILES/{key}", f"{ROOT}/ENTHALPY_FILES/{key}"
            if not os.path.exists(iso):
                continue
            H = {}
            if os.path.exists(ent):
                for l in open(ent):
                    if l.startswith("#") or not l.strip(): continue
                    p, h, u = l.split(",")[:3]; H[float(p)] = float(h)
            for l in open(iso):
                if l.startswith("#") or not l.strip(): continue
                p, q, e = map(float, l.split(",")[:3])
                rows.append((n, scheme, ff, gas, p, q, e, H.get(p, "")))
with open(f"{OUT}/crafted_{scheme}_298.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["mof","charge","ff","gas","p_pa","q_molkg","q_err","dH_kjmol"]); w.writerows(rows)
print(scheme, len(rows))
