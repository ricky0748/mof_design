#!/usr/bin/env python3
"""逐条审查 MOFFlow-2 的新有机 SBU：化学合理性、连接基团、SAscore、与训练 SBU 的最近邻。

输出 CSV + 汇总。
用法: python review_novel_sbus.py <bb_csv> <train_json> <out.csv> [--cache train_sbus.smi]
"""
import os
import sys
import csv
import json
import argparse
from collections import Counter

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem, RDConfig

RDLogger.DisableLog("rdApp.*")
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer  # noqa: E402

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
EL_RE = __import__("re").compile(r"\[([A-Z][a-z]?)[^\]]*\]|(?<!\[)([A-Z][a-z]?)(?=[a-z0-9(]|$)")
COO = Chem.MolFromSmarts("[CX3](=O)[O-]")
COOH = Chem.MolFromSmarts("[CX3](=O)[OH]")
THIOL = Chem.MolFromSmarts("[SX2H]")
PHOS = Chem.MolFromSmarts("[PX4](=O)([OX2])[OX2]")
NMINUS = Chem.MolFromSmarts("[n-]")


def split_seq(s):
    s = s.replace("<BOS>", "").replace("<EOS>", "").replace("<PAD>", "").replace("<UNK>", "")
    out = []
    for g in s.split("<SEP>"):
        for p in g.split("."):
            p = p.strip()
            if p:
                out.append(p)
    return out


def is_metal(sbu):
    els = set()
    for m in EL_RE.finditer(sbu):
        els.add(m.group(1) or m.group(2))
    return bool(els & METALS)


def canon(sbu):
    m = Chem.MolFromSmiles(sbu)
    return None if m is None else Chem.MolToSmiles(m)


def load_train_sbus(train_path, cache):
    if os.path.exists(cache):
        smis = [l.strip() for l in open(cache) if l.strip()]
        return smis
    train = json.load(open(train_path))
    if isinstance(train, dict):
        train = list(train.values())
    seen = set()
    for v in train:
        s = v["seq"] if isinstance(v, dict) else str(v)
        for p in split_seq(s):
            if is_metal(p):
                continue
            c = canon(p)
            if c:
                seen.add(c)
    smis = sorted(seen)
    with open(cache, "w") as f:
        f.write("\n".join(smis))
    return smis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bb_csv")
    ap.add_argument("train_json")
    ap.add_argument("out")
    ap.add_argument("--cache", default="/tmp/train_sbus.smi")
    a = ap.parse_args()

    tr = load_train_sbus(a.train_json, a.cache)
    print(f"training organic SBUs: {len(tr)}", flush=True)
    tr_fps = []
    tr_mols = []
    for s in tr:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        tr_mols.append(s)
        tr_fps.append(AllChem.GetMorganFingerprintAsBitVect(m, 2, 2048))
    print(f"training fingerprints: {len(tr_fps)}", flush=True)

    R = list(csv.DictReader(open(a.bb_csv)))
    novel = [r["sbu"] for r in R if r["kind"] == "organic" and r["in_train"] == "0" and r.get("valid", "1") == "1"]
    print(f"novel SBUs to review: {len(novel)}", flush=True)

    rows = []
    for s in novel:
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        can = Chem.MolToSmiles(m)
        n_coo = len(m.GetSubstructMatches(COO)) + len(m.GetSubstructMatches(COOH))
        n_aromN = sum(1 for at in m.GetAtoms() if at.GetIsAromatic() and at.GetSymbol() == "N")
        n_thiol = len(m.GetSubstructMatches(THIOL))
        n_phos = len(m.GetSubstructMatches(PHOS))
        n_nminus = len(m.GetSubstructMatches(NMINUS))
        bind = n_coo + n_aromN + n_thiol + n_phos
        n_anion = n_coo + n_nminus + n_thiol + n_phos
        radicals = sum(at.GetNumRadicalElectrons() for at in m.GetAtoms())
        charge = Chem.GetFormalCharge(m)
        rings = rdMolDescriptors.CalcNumAromaticRings(m)
        rot = rdMolDescriptors.CalcNumRotatableBonds(m)
        sa = sascorer.calculateScore(m)
        fp = AllChem.GetMorganFingerprintAsBitVect(m, 2, 2048)
        sims = DataStructs.BulkTanimotoSimilarity(fp, tr_fps)
        j = int(np.argmax(sims))
        maxsim = float(sims[j])
        flags = []
        if bind < 2:
            flags.append("lt2_binding")
        if radicals > 0:
            flags.append(f"radicals{radicals}")
        if rings == 0:
            flags.append("no_aromatic_ring")
        if charge > 0:
            flags.append("positive_charge")
        if charge < -max(n_anion, 1):
            flags.append("charge_below_anion_count")
        if "N=N" in can or "N=N" in s:
            flags.append("azo")
        plausible = (bind >= 2 and radicals == 0 and rings >= 1 and charge <= 0
                     and charge >= -max(n_anion, 1))
        rows.append(dict(sbu=can, formula=rdMolDescriptors.CalcMolFormula(m), MW=round(Descriptors.MolWt(m), 1),
                         charge=charge, n_coo=n_coo, n_aromN=n_aromN, binding=bind,
                         arom_rings=rings, rot_bonds=rot, radicals=radicals, sascore=round(sa, 2),
                         max_tanimoto=round(maxsim, 3), nearest_train=tr_mols[j],
                         plausible=int(plausible), flags=";".join(flags)))

    rows.sort(key=lambda r: (-r["plausible"], -r["binding"], r["sascore"]))
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\n=== summary ===")
    print(f"reviewed {len(rows)}; plausible MOF linkers (>=2 binding, no radical, aromatic): "
          f"{sum(r['plausible'] for r in rows)}")
    print(f"with >=2 carboxylates: {sum(r['n_coo']>=2 for r in rows)}")
    print(f"with radicals: {sum(r['radicals']>0 for r in rows)}; no aromatic ring: {sum(r['arom_rings']==0 for r in rows)}")
    print(f"SAscore median {np.median([r['sascore'] for r in rows]):.2f} "
          f"(min {min(r['sascore'] for r in rows):.2f}, max {max(r['sascore'] for r in rows):.2f})")
    print(f"near-known (Tanimoto>=0.7): {sum(r['max_tanimoto']>=0.7 for r in rows)}; "
          f"new scaffold (<0.4): {sum(r['max_tanimoto']<0.4 for r in rows)}")
    for r in rows:
        print(f"  {r['plausible']} bind={r['binding']} coo={r['n_coo']} SA={r['sascore']:.1f} "
              f"Tmax={r['max_tanimoto']:.2f} {r['flags']:<20s} {r['sbu'][:70]}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
