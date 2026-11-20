"""Map native outputs through explicit original selected-sequence data_idx."""
import json,pickle
from pathlib import Path
import torch
from pymatgen.core import Structure,Lattice
p=Path(__file__).resolve().parent
d=torch.load(p/'inference/predictions_0.pt',map_location='cpu',weights_only=False)
indices=d['gt_data_batch'].data_idx.tolist()
cached=pickle.loads((p/'processed_data.pkl').read_bytes())
assert sorted(indices)==sorted(int(r['data_idx']) for r in cached)
selected=json.loads((p/'selected.json').read_text());counts=d['num_atoms'][0].tolist()
assert len(indices)==len(counts) and len(set(indices))==len(indices)
(p/'native').mkdir(exist_ok=True);start=0;mapping=[]
for j,(idx,n) in enumerate(zip(indices,counts)):
    n=int(n);row=dict(prediction_index=j,selected_index=idx,id=selected[idx]['id'])
    try:
        coords=d['cart_coords'][0][start:start+n].numpy();types=d['atom_types'][0][start:start+n].tolist();lat=d['lattices'][0][j].tolist()
        s=Structure(Lattice.from_parameters(*lat),types,coords,coords_are_cartesian=True)
        dest=p/'native'/('A_'+row['id']+'.cif');s.to(filename=str(dest));row.update(status='built',cif=str(dest))
    except Exception as e:row.update(status='conversion_failed',reason=str(e))
    mapping.append(row);start+=n
assert start==d['cart_coords'][0].shape[0]
(p/'native_mapping.json').write_text(json.dumps(mapping,indent=2));print('Native mapping',len(mapping),flush=True)
