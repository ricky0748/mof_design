#!/usr/bin/env python3
"""Prepare immutable manifests and reconstruct MOFFlow-2 training CIFs.

Training coordinates follow upstream preprocess/check_mof_validity.py.
Example: python mofid_prepare.py --root /share/rickyswork/ai_mof --out OUT --limit 100
Use --limit 0 for the full training set. Training keys must also occur in sequence JSON.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import pickle
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=100)
    a = ap.parse_args()
    root, out = Path(a.root), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = root / 'generation/pilots/MOFFlow-2/data'
    import lmdb
    from pymatgen.core import Structure
    from rdkit import Chem
    sys.path.insert(0, str(root / 'generation/pilots/MOFDiff'))
    from mofdiff.common.constants import METALS
    metals = set(METALS)
    seq = json.loads((data / 'seqs/mof_sequence_train.json').read_text())
    env = lmdb.open(str(data / 'lmdb/gen/MetalOxo_final_train.lmdb'),
                    subdir=False, readonly=True, lock=False, readahead=False)
    train_dir = out / 'train_cif'
    train_dir.mkdir(exist_ok=True)
    count, checked, mismatches = 0, 0, []
    with env.begin() as txn, (out / 'training_manifest.jsonl').open('w') as stream:
        for key, value in txn.cursor():
            key = key.decode()
            if key not in seq:
                raise ValueError('LMDB key absent from sequence training set: ' + key)
            d = pickle.loads(value)
            # Verify the molecular blocks match the sequence at sampled keys.
            if checked < 20:
                blocks = []
                for block in d['bb_mols']:
                    mol = Chem.MolFromMolBlock(block, removeHs=True)
                    if mol is not None:
                        smiles = Chem.MolToSmiles(mol)
                        if any(at.GetAtomicNum() in metals for at in mol.GetAtoms()):
                            # Upstream extract_sequence joins disconnected metals.
                            smiles = smiles.replace('.', '')
                        blocks.extend(smiles.split('.'))
                s = seq[key]['seq']
                for token in ('<BOS>', '<EOS>', '<PAD>'):
                    s = s.replace(token, '')
                reference = []
                for group in s.split('<SEP>'):
                    for piece in group.strip().split('.'):
                        if piece.strip():
                            mol = Chem.MolFromSmiles(piece.strip())
                            reference.append(Chem.MolToSmiles(mol) if mol is not None else piece.strip())
                if set(blocks) != set(reference):
                    mismatches.append(key)
                checked += 1
            path = train_dir / (key + '.cif')
            if not path.exists():
                structure = Structure(lattice=d['cell_1'].numpy(), species=d['atom_types'].numpy(),
                                      coords=d['gt_coords'].numpy(), coords_are_cartesian=True)
                structure.to(filename=str(path))
            stream.write(json.dumps(dict(id=key, cohort='mofflow2_train', cif=str(path), source_key=key)) + '\n')
            count += 1
            if count % 1000 == 0:
                print('training CIFs', count, flush=True)
            if a.limit and count >= a.limit:
                break
    # Keep raw and relaxed generated structures in distinct cohorts.
    scale = root / 'generation/pilots/MOFFlow-2/scale1000'
    rows = []
    for path in sorted((scale / 'uffp/cif').glob('*.cif')):
        rows.append(dict(id=path.stem, cohort='mofflow2_raw', cif=str(path)))
    for rec in csv.DictReader((scale / 'plausibility/combined.csv').open()):
        if rec['final_valid'] != 'True':
            continue
        if rec['uff_valid'] == 'True':
            path = scale / 'uffp/plausibility/uff/prim' / (rec['name'] + '.cif')
        else:
            path = scale / 'uffp/mace' / (rec['name'] + '_mace.cif')
        if not path.exists():
            raise FileNotFoundError(path)
        rows.append(dict(id=rec['name'], cohort='mofflow2_relaxed_valid', cif=str(path)))
    (out / 'generated_manifest.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    provenance = dict(training_exported=count, training_total=len(seq),
                      sampled_sequence_checks=checked, sampled_sequence_mismatches=mismatches,
                      coordinate_source='gt_coords Cartesian + cell_1; upstream check_mof_validity.py',
                      generated=len(rows))
    for name in ('training_manifest.jsonl', 'generated_manifest.jsonl'):
        provenance[name + '_sha256'] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    (out / 'preparation.json').write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance), flush=True)


if __name__ == '__main__':
    main()
