#!/usr/bin/env python3
"""MOFFlow-2 生成序列的化学后过滤 + 端到端有效性评估。

规则（对每个有机 SBU）：
- RDKit 可解析；
- 无自由基；
- 结合基团 ≥2（羧酸根/羧酸 + 芳香 N + 硫醇 + 膦酸）；
- 至少 1 个芳环；
- 电荷 ≤0 且 |charge| ≤ 阴离子基团数；
- SAscore ≤ 5。
金属节点只要求非空且含金属。

映射：processed_data.pkl 的 data_idx -> 原始 100 条序列；CIF 顺序为 000..076。
用法: python filter_generated_sbus.py <preds.json> <processed.pkl> <combined.csv> <train_sbus.smi> <out_prefix>
"""
import os
import sys
import json
import pickle
import re
import csv

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import rdMolDescriptors, RDConfig

RDLogger.DisableLog("rdApp.*")
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer  # noqa: E402

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
EL_RE = re.compile(r"\[([A-Z][a-z]?)[^\]]*\]|(?<!\[)([A-Z][a-z]?)(?=[a-z0-9(]|$)")
COO = Chem.MolFromSmarts("[CX3](=O)[O-]")
COOH = Chem.MolFromSmarts("[CX3](=O)[OH]")
THIOL = Chem.MolFromSmarts("[SX2H]")
PHOS = Chem.MolFromSmarts("[PX4](=O)([OX2])[OX2]")
NMINUS = Chem.MolFromSmarts("[n-]")
HYDROXYL = Chem.MolFromSmarts("[OX2H;!$(O[CX3]=O);!$(OS(=O)=O)]")
NITRILE = Chem.MolFromSmarts("[NX1]#[CX2]")
AMINE = Chem.MolFromSmarts("[NX3;H1,H2;!$(N[CX3]=O);!$(N=S)]")
SULFONATE = Chem.MolFromSmarts("[SX4](=O)(=O)[O-]")
NODE_ANIONS = {"[O-2]", "[O-]", "[OH-]", "[S-2]", "[SH-]", "[N-3]", "[NH2-]", "[NH-]",
               "[F-]", "[Cl-]", "[Br-]", "[I-]", "[O]", "[N]", "O", "N"}


def split_seq(s):
    s = s.replace("<BOS>", "").replace("<EOS>", "").replace("<PAD>", "").replace("<UNK>", "")
    out = []
    for g in s.split("<SEP>"):
        for p in g.split("."):
            p = p.strip()
            if p:
                out.append(p)
    return out


def elements_of(sbu):
    els = set()
    for m in EL_RE.finditer(sbu):
        els.add(m.group(1) or m.group(2))
    return els


def is_metal(sbu):
    return bool(elements_of(sbu) & METALS)


def has_carbon(sbu):
    return "C" in elements_of(sbu)


def check_sbu(sbu):
    """返回 (ok, reasons, info)。"""
    m = Chem.MolFromSmiles(sbu)
    if m is None:
        return False, ["rdkit_invalid"], {}
    can = Chem.MolToSmiles(m)
    n_coo = len(m.GetSubstructMatches(COO)) + len(m.GetSubstructMatches(COOH))
    n_aromN = sum(1 for at in m.GetAtoms() if at.GetIsAromatic() and at.GetSymbol() == "N")
    n_thiol = len(m.GetSubstructMatches(THIOL))
    n_phos = len(m.GetSubstructMatches(PHOS))
    n_nminus = len(m.GetSubstructMatches(NMINUS))
    n_oh = len(m.GetSubstructMatches(HYDROXYL))
    n_cn = len(m.GetSubstructMatches(NITRILE))
    n_nh = len(m.GetSubstructMatches(AMINE))
    n_so3 = len(m.GetSubstructMatches(SULFONATE))
    bind = n_coo + n_aromN + n_thiol + n_phos + n_oh + n_cn + n_nh + n_so3
    anions = n_coo + n_nminus + n_thiol + n_phos + n_so3
    radicals = sum(at.GetNumRadicalElectrons() for at in m.GetAtoms())
    charge = Chem.GetFormalCharge(m)
    rings = rdMolDescriptors.CalcNumAromaticRings(m)
    sa = sascorer.calculateScore(m)
    reasons = []
    if radicals > 0:
        reasons.append(f"radicals{radicals}")
    if charge > 0:
        reasons.append("positive_charge")
    if bind < 2:
        reasons.append("lt2_binding")
    if charge < -max(anions, 1):
        reasons.append("charge_below_anions")
    hard_ok = (radicals == 0 and charge <= 0)
    linker_ok = hard_ok and bind >= 2
    return linker_ok, reasons, dict(can=can, bind=bind, n_coo=n_coo, charge=charge,
                                    radicals=radicals, rings=rings, sa=round(sa, 2),
                                    hard_ok=hard_ok, linker_ok=linker_ok)


def main():
    preds_path, proc_path, combined, train_smi, out_prefix = sys.argv[1:6]
    cif_prefix = sys.argv[6] if len(sys.argv) > 6 else "mofflow2"
    seqs = json.load(open(preds_path))
    proc = pickle.load(open(proc_path, "rb"))
    data_idx = [x["data_idx"] for x in proc]

    # 训练 SBU 校准
    tr = [l.strip() for l in open(train_smi) if l.strip()]
    tr_hard = tr_link = 0
    tr_reasons = {}
    for s in tr:
        ok, reasons, info = check_sbu(s)
        tr_hard += info.get("hard_ok", False)
        tr_link += info.get("linker_ok", False)
        for r in reasons:
            tr_reasons[r] = tr_reasons.get(r, 0) + 1
    print(f"train SBUs: {len(tr)}, hard-valid {tr_hard} ({tr_hard/max(1,len(tr)):.1%}), "
          f"linker-suitable {tr_link} ({tr_link/max(1,len(tr)):.1%}), reasons {tr_reasons}")

    rows = []
    for i, s in enumerate(seqs):
        parts = split_seq(s)
        bad = []
        n_org = 0
        hard_all = True
        for p in parts:
            if is_metal(p):
                continue
            if not has_carbon(p):
                # 无机节点组分（氧化物/氢氧化物/卤素等）接受；其他非碳小分子判为 guest/噪声
                if p in NODE_ANIONS:
                    continue
                bad.append((p[:60], ["non_mof_guest"]))
                hard_all = False
                continue
            n_org += 1
            ok, reasons, info = check_sbu(p)
            hard_all = hard_all and info.get("hard_ok", False)
            if not ok:
                bad.append((p[:60], reasons))
        rows.append(dict(seq_idx=i, n_sbu=len(parts), n_org=n_org,
                         hard_pass=int(n_org > 0 and hard_all),
                         chem_pass=int(n_org > 0 and not bad),
                         reasons=";".join(f"{p}:{','.join(r)}" for p, r in bad)[:400]))
    n_pass = sum(r["chem_pass"] for r in rows)
    n_hard = sum(r["hard_pass"] for r in rows)
    print(f"generated sequences: {len(rows)}, hard-valid {n_hard} ({n_hard/len(rows):.1%}), "
          f"linker-suitable {n_pass} ({n_pass/len(rows):.1%})")

    # 端到端映射
    cs = list(csv.DictReader(open(combined)))
    by_name = {r["name"]: r for r in cs}
    e2e = []
    for i, idx in enumerate(data_idx):
        cif = f"{cif_prefix}_{i:03d}"
        r = by_name.get(cif)
        if r is None:
            continue
        sv = str(r["final_valid"]).strip().lower() in ("true", "1")
        e2e.append(dict(seq_idx=idx, cif=cif,
                        hard_pass=rows[idx]["hard_pass"],
                        chem_pass=rows[idx]["chem_pass"],
                        struct_valid=int(sv),
                        end_to_end=int(rows[idx]["chem_pass"] and sv)))
    n_e2e = sum(x["end_to_end"] for x in e2e)
    print(f"assembled {len(e2e)}; chemically valid {sum(x['chem_pass'] for x in e2e)}; "
          f"chem+struct valid {n_e2e} ({n_e2e/len(seqs):.1%} of 100 raw samples)")

    with open(out_prefix + "_sequences.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(out_prefix + "_end2end.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(e2e[0].keys()))
        w.writeheader(); w.writerows(e2e)
    print(f"-> {out_prefix}_sequences.csv, {out_prefix}_end2end.csv")


if __name__ == "__main__":
    main()
