"""Transfer audited charges onto unchanged source CIF coordinates."""
from pathlib import Path
import numpy as np
from ase.io import read
from scipy.optimize import linear_sum_assignment
def preserve_geometry(source,charged):
    source=Path(source);charged=Path(charged);a=read(source,store_tags=True);b=read(charged,store_tags=True)
    if len(a)!=len(b) or sorted(a.symbols)!=sorted(b.symbols):raise ValueError('charge atom mismatch')
    if not np.allclose(a.cell.cellpar(),b.cell.cellpar(),atol=.001,rtol=0):raise ValueError('charge cell mismatch')
    delta=a.get_scaled_positions()[:,None,:]-b.get_scaled_positions()[None,:,:];delta-=np.rint(delta);cost=np.linalg.norm(delta@a.cell.array,axis=2);cost[np.array(a.symbols)[:,None]!=np.array(b.symbols)[None,:]]=1e6;i,j=linear_sum_assignment(cost)
    if cost[i,j].max()>.001:raise ValueError('charge positions mismatch')
    q=np.array(b.info['_atom_site_charge'],dtype=float)[j]
    if len(q)!=len(a) or not np.isfinite(q).all() or abs(q.sum())>1e-3:raise ValueError('invalid charges')
    lines=source.read_text().splitlines();start=next(i for i,s in enumerate(lines) if s.strip()=='_atom_site_type_symbol');end=start
    while end<len(lines) and lines[end].strip().startswith('_'):end+=1
    data=[k for k in range(end,len(lines)) if lines[k].strip() and not lines[k].lstrip().startswith('#')]
    if len(data)!=len(a):raise ValueError('source atom loop not supported')
    for k,charge in zip(data,q):lines[k]+=' '+format(float(charge),'.12g')
    lines.insert(end,'  _atom_site_charge');charged.write_text('\n'.join(lines)+'\n');c=read(charged,store_tags=True)
    if not np.allclose(a.cell.array,c.cell.array,atol=1e-10,rtol=0) or not np.allclose(a.get_scaled_positions(),c.get_scaled_positions(),atol=1e-10,rtol=0):raise ValueError('geometry transfer failed')
    return dict(serialization_max_displacement=float(cost[i,j].max()),charge_sum=float(q.sum()))
