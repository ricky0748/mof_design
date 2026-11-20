#!/usr/bin/env python3
"""One frozen pcu/N16 build attempt per ligand; controls first."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import numpy as np
from rdkit import Chem


def build(row, out):
    from anchor_rules import analyze, to_pormake_xyz, Config
    import pormake as pm
    t0 = time.monotonic()
    rec = dict(id=row['id'], smiles=row['smiles'], template='pcu/N16', status='failed')
    try:
        config = Config(seed=7)
        result = analyze(row['smiles'], config, node='Zn4O')
        rec['anchor_status'] = result['status']
        if result['status'] != 'ok' or result['n_connections_est'] != 2:
            rec['reason'] = 'anchor_or_embedding_failed'
            return rec
        neutral = Chem.MolToSmiles(Chem.RemoveHs(result['_mh']))
        rec['embedded_smiles'] = neutral
        if 'neutral_smiles' in row and neutral != row['neutral_smiles']:
            rec['reason'] = 'ligand_changed_during_embedding'
            return rec
        xyz = to_pormake_xyz(result['_mh'], result['_anchors'], config)
        lines = xyz.splitlines()
        n = int(lines[0]); xs = list(map(int, lines[1].split()))
        positions = np.array([[float(x) for x in l.split()[1:4]] for l in lines[2:2+n]])
        parents = {}
        for line in lines[2+n:]:
            i, j, _ = line.split(); i, j = int(i), int(j)
            if j in xs: parents[j] = i
            if i in xs: parents[i] = j
        angles = []
        for k, x in enumerate(xs):
            v = positions[x]-positions[parents[x]]
            axis = positions[x]-positions[xs[1-k]]
            angles.append(float(np.degrees(np.arccos(np.clip(v @ axis / np.linalg.norm(v) / np.linalg.norm(axis), -1, 1)))))
        rec['direction_degrees'] = angles
        (out/'bb').mkdir(exist_ok=True)
        path = out/'bb'/(row['id']+'.xyz')
        path.write_text(xyz)
        rec['bb_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        if max(angles) > 20:
            rec.update(status='incompatible', reason='direction_over_20_degrees')
            return rec
        with contextlib.redirect_stdout(io.StringIO()):
            db = pm.Database()
            bb = pm.BuildingBlock(str(path))
            fw = pm.Builder().build_by_type(topology=db.get_topo('pcu'),
                node_bbs={0:db.get_bb('N16')}, edge_bbs={(0,0):bb})
            cif = out/'raw'/('B_'+row['id']+'.cif')
            fw.write_cif(str(cif))
        rec.update(status='built', cif=str(cif), natoms=len(fw.atoms),
                   cif_sha256=hashlib.sha256(cif.read_bytes()).hexdigest())
    except Exception as exc:
        rec['reason'] = type(exc).__name__+': '+str(exc)
    finally:
        rec['seconds'] = round(time.monotonic()-t0, 3)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--controls-only', action='store_true')
    a = ap.parse_args(); out = Path(a.out).resolve()
    sys.path.insert(0, str(out/'support'))
    (out/'raw').mkdir(exist_ok=True)
    rows = json.loads((out/'controls.json').read_text())
    if not a.controls_only:
        controls = json.loads((out/'controls_build.json').read_text())
        if any(r['status'] != 'built' for r in controls):
            raise RuntimeError('Control assembly failed; investigate before rolling out.')
        rows = json.loads((out/'selected.json').read_text())
        frozen = json.loads((out/'frozen.json').read_text())
        if hashlib.sha256((out/'selected.json').read_bytes()).hexdigest() != frozen['selected_sha256']:
            raise RuntimeError('Selected sample manifest changed after freeze')
    records = []
    for row in rows:
        rec = build(row, out)
        records.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    name = 'controls_build.json' if a.controls_only else 'build.json'
    (out/name).write_text(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
