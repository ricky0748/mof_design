#!/usr/bin/env python3
"""Select and freeze 20 source ligands without using structural outcome labels."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
from rdkit import Chem, RDLogger

RDLogger.DisableLog('rdApp.*')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='/share/rickyswork/ai_mof')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'frozen.json').exists():
        raise RuntimeError('Inputs already frozen; use existing records, do not overwrite.')
    sys.path.insert(0, str(out / 'support'))
    from anchor_rules import normalize_smiles, find_anchors, METALS
    base = root / 'generation/pilots/MOFFlow-2/scale1000'
    seqpath = base / 'inference/temp_1.0_target-5.0/preds_samples-1000.json'
    chem_path = base / 'plausibility/chemfilter_1000_end2end.csv'
    novel_path = base / 'plausibility/bb_novelty_1000.csv'
    seqs = json.loads(seqpath.read_text())
    # Deliberately take only identity, mapping, and chemical fields, not struct_valid.
    eligible = {int(r['seq_idx']): r['cif'] for r in csv.DictReader(chem_path.open()) if r['chem_pass'] == '1'}
    novelty = {r['sbu']: r['in_train'] == '0' for r in csv.DictReader(novel_path.open()) if r['kind'] == 'organic'}
    pool, excluded = {}, []
    for i, name in sorted(eligible.items()):
        seq = seqs[i].split('<EOS>')[0].replace('<BOS>', '').replace('<PAD>', '')
        org, metals = set(), set()
        for piece in seq.replace('<SEP>', '.').split('.'):
            mol = Chem.MolFromSmiles(piece.strip())
            if mol is None:
                continue
            els = {at.GetSymbol() for at in mol.GetAtoms()}
            if els & METALS:
                metals.update(els & METALS)
            elif 'C' in els:
                org.add(Chem.MolToSmiles(mol))
        reason = None
        if len(org) != 1:
            reason = 'not_single_unique_organic_linker'
        else:
            smi = next(iter(org))
            m = normalize_smiles(smi)
            anchors = find_anchors(m) if m is not None else []
            if m is None:
                reason = 'normalization_failed'
            elif m.GetNumHeavyAtoms() > 60:
                reason = 'over_60_heavy_atoms'
            elif len(anchors) != 2 or any(a.rule != 'carboxylate' for a in anchors):
                reason = 'not_exactly_two_carboxylate_anchors'
            elif smi not in novelty:
                reason = 'missing_training_novelty_label'
        if reason:
            excluded.append(dict(seq_idx=i, source_name=name, reason=reason))
            continue
        if smi in pool:
            pool[smi]['other_seq_idx'].append(i)
            continue
        source = base / 'uffp/cif' / (name + '.cif')
        if not source.exists():
            raise FileNotFoundError(source)
        pool[smi] = dict(smiles=smi, neutral_smiles=Chem.MolToSmiles(m),
                         source_seq_idx=i, source_name=name, source_cif=str(source),
                         source_sha256=digest(source), source_metals=sorted(metals),
                         novel_sequence_fragment=novelty[smi], other_seq_idx=[],
                         rank=hashlib.sha256(('20261113|' + smi).encode()).hexdigest())
    values = sorted(pool.values(), key=lambda r: r['rank'])
    novel = [r for r in values if r['novel_sequence_fragment']][:12]
    known = [r for r in values if not r['novel_sequence_fragment']]
    selected = novel + known[:20-len(novel)]
    if len(selected) != 20:
        raise ValueError(f'Need 20 eligible unique ligands, found {len(selected)}')
    for i, row in enumerate(selected):
        row['id'] = f'L{i+1:02d}'
    eg = root / 'generation/pilots/EGMOF/scale1000'
    valid = sorted(r['name'] for r in csv.DictReader((eg / 'plausibility/combined.csv').open())
                   if r['final_valid'] == 'True' and r['name'].startswith('pcu+N16+'))
    if not valid:
        raise ValueError('No measured valid EGMOF pcu/N16 host')
    host = eg / 'cif' / (valid[0] + '.cif')
    if not host.exists():
        raise FileNotFoundError(host)
    (out / 'selected.json').write_text(json.dumps(selected, ensure_ascii=False, indent=2))
    (out / 'eligible_pool.json').write_text(json.dumps(values, ensure_ascii=False, indent=2))
    (out / 'exclusions.json').write_text(json.dumps(excluded, ensure_ascii=False, indent=2))
    controls = [dict(id='C_BDC', smiles='O=C(O)c1ccc(C(=O)O)cc1'),
                dict(id='C_BPDC', smiles='O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1')]
    (out / 'controls.json').write_text(json.dumps(controls, indent=2))
    frozen = dict(date='2026-11-13', stage='before_template_build_and_new_relaxation',
                  n=20, novel=len(novel), known=20-len(novel), eligible_unique=len(pool),
                  exclusions=Counter(r['reason'] for r in excluded),
                  template=dict(topology='pcu', node='N16', node_family='Zn4O',
                                egmof_host=valid[0], host_sha256=digest(host)),
                  parameters=dict(seed=7, direction_max_degrees=20, steps=150, fmax=0.2,
                                  maxstep=0.05, timeout_seconds=600, atom_limit=1000, max_workers=8),
                  sources={str(p):digest(p) for p in (seqpath, chem_path, novel_path)},
                  selected_sha256=digest(out/'selected.json'),
                  protocol_sha256=digest(out/'PROTOCOL.md'),
                  model_sha256=digest(root/'mace_medium.model'),
                  script_sha256={p.name:digest(p) for p in sorted(out.glob('*.py'))})
    (out / 'frozen.json').write_text(json.dumps(frozen, ensure_ascii=False, indent=2))
    print(json.dumps(frozen, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
