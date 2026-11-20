import json
from pathlib import Path
import numpy as np
from ase.io import read
p=Path(__file__).resolve().parent/'performance_preflight'
a=read(p/'control.cif');b=read(next((p/'charged').glob('*.cif')),store_tags=True)
print('counts',len(a),len(b));print('cells',a.cell.cellpar(),b.cell.cellpar());print('symbols_order_equal',a.get_chemical_symbols()==b.get_chemical_symbols());print('positions',a.get_scaled_positions()[:5],b.get_scaled_positions()[:5]);print('info',b.info.keys())
from scipy.optimize import linear_sum_assignment
d=a.get_scaled_positions()[:,None,:]-b.get_scaled_positions()[None,:,:];d-=np.rint(d);cost=np.linalg.norm(d@a.cell.array,axis=2);cost[np.array(a.get_chemical_symbols())[:,None]!=np.array(b.get_chemical_symbols())[None,:]]=1e6
i,j=linear_sum_assignment(cost);print('matching_max_distance',cost[i,j].max());print('matching_rms_distance',np.sqrt(np.mean(cost[i,j]**2)));print('charge_sum',sum(map(float,b.info['_atom_site_charge'])))
