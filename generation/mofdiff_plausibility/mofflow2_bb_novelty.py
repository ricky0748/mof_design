#!/usr/bin/env python3
"""MOFFlow-2 构筑块新颖性：把生成序列拆成 SBU，与训练序列的 SBU 集合比较。

生成序列来自 logs/gen/inference/temp_1.0_target-5.0/preds_samples-100.json；
训练集为 data/seqs/mof_sequence_train.json（187k 条）。
有机 SBU 用 RDKit canonical SMILES 去重；含金属的 SBU 按原字符串比较。

输出：SBU 级 novel 列表 + 汇总。
用法: python mofflow2_bb_novelty.py <gen.json> <train.json> <out.csv>
"""
import os
import sys
import json
import re
import csv
from collections import Counter
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

METALS = set("Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi U Th".split())
EL_RE = re.compile(r"\[([A-Z][a-z]?)[^\]]*\]|(?<!\[)([A-Z][a-z]?)(?=[a-z0-9(]|$)")


def split_seq(s):
    s = s.replace("<BOS>", "").replace("<EOS>", "").replace("<PAD>", "").replace("<UNK>", "")
    groups = [g.strip() for g in s.split("<SEP>")]
    out = []
    for g in groups:
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
    if m is None:
        return None
    return Chem.MolToSmiles(m)


def canon_seq(s):
    parts = []
    for p in split_seq(s):
        parts.append(canon(p) or p)
    return "<SEP>".join(parts)


def main():
    gen_path, train_path, out = sys.argv[1:4]
    gen = json.load(open(gen_path))
    train = json.load(open(train_path))
    if isinstance(train, dict):
        train = list(train.values())

    tr_org, tr_metal, tr_seqs = set(), set(), set()
    for v in train:
        s = v["seq"] if isinstance(v, dict) else str(v)
        tr_seqs.add(canon_seq(s))
        for p in split_seq(s):
            if is_metal(p):
                tr_metal.add(p)
            else:
                tr_org.add(canon(p) or p)
    print(f"train: {len(train)} seqs, {len(tr_org)} organic SBUs, {len(tr_metal)} metal nodes", flush=True)

    gen_org, gen_metal, gen_seqs = Counter(), Counter(), set()
    gen_invalid = Counter()
    per_sample_novel = []
    for s in gen:
        seq_parts = split_seq(s)
        novel_in_sample = 0
        for p in seq_parts:
            if is_metal(p):
                k = p
                gen_metal[k] += 1
                if k not in tr_metal:
                    novel_in_sample += 1
            else:
                c = canon(p)
                if c is None:
                    gen_invalid[p] += 1
                    continue
                gen_org[c] += 1
                if c not in tr_org:
                    novel_in_sample += 1
        cs = canon_seq(s)
        gen_seqs.add(cs)
        per_sample_novel.append(dict(seq_novel=cs not in tr_seqs, novel_sbu=novel_in_sample,
                                     n_sbu=len(seq_parts)))
    novel_org = {k: c for k, c in gen_org.items() if k not in tr_org}
    novel_metal = {k: c for k, c in gen_metal.items() if k not in tr_metal}
    n = len(gen)
    print(f"\ngenerated: {n} sequences; unique sequences {len(gen_seqs)}; "
          f"exact sequence novel {sum(1 for x in per_sample_novel if x['seq_novel'])}/{n}")
    print(f"generated organic SBUs (RDKit-valid): unique {len(gen_org)}, novel {len(novel_org)} "
          f"({len(novel_org)/max(1,len(gen_org)):.1%}); invalid SMILES {sum(gen_invalid.values())} "
          f"({len(gen_invalid)} unique)")
    print(f"generated metal nodes: unique {len(gen_metal)}, novel {len(novel_metal)}")
    print(f"samples containing >=1 novel valid BB: {sum(1 for x in per_sample_novel if x['novel_sbu']>0)}/{n}")
    print("novel organic examples:", list(novel_org.items())[:8])

    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "sbu", "count", "in_train", "valid"])
        for k, c in gen_org.most_common():
            w.writerow(["organic", k, c, int(k in tr_org), 1])
        for k, c in gen_metal.most_common():
            w.writerow(["metal", k, c, int(k in tr_metal), 1])
        for k, c in gen_invalid.most_common():
            w.writerow(["organic_invalid", k, c, 0, 0])
    print(f"-> {out}")


if __name__ == "__main__":
    main()
