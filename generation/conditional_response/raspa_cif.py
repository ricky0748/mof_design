"""Adapt P1 symmetry tag aliases without altering numeric CIF data."""
from pathlib import Path
import numpy as np
from ase.io import read
def adapt(path):
    p=Path(path);a=read(p);text=p.read_text();text=text.replace('_space_group_name_H-M_alt','_symmetry_space_group_name_H-M').replace('_space_group_IT_number','_symmetry_Int_Tables_number').replace('_space_group_symop_operation_xyz','_symmetry_equiv_pos_as_xyz');p.write_text(text);b=read(p)
    if a.get_chemical_symbols()!=b.get_chemical_symbols() or not np.allclose(a.cell.array,b.cell.array,atol=1e-10,rtol=0) or not np.allclose(a.get_scaled_positions(),b.get_scaled_positions(),atol=1e-10,rtol=0):raise ValueError('metadata adaptation changed structure')
