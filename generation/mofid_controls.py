#!/usr/bin/env python3
"""Create name-change and supercell invariance controls for HKUST-1."""
import json
from pathlib import Path
import shutil
from pymatgen.core import Structure

root = Path('/share/rickyswork/ai_mof')
out = root / 'generation/mofid_validation/controls'
out.mkdir(exist_ok=True)
source = root / 'tools/mofid-master/Resources/TestCIFs/P1-Cu-BTC.cif'
shutil.copyfile(source, out / 'renamed_hkust.cif')
structure = Structure.from_file(source)
structure.make_supercell([2, 1, 1])
structure.to(filename=str(out / 'supercell_hkust.cif'))
rows = [dict(id='original_hkust', cohort='control', cif=str(source)),
        dict(id='renamed_hkust', cohort='control', cif=str(out / 'renamed_hkust.cif')),
        dict(id='supercell_hkust', cohort='control', cif=str(out / 'supercell_hkust.cif'))]
(out / 'manifest.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
