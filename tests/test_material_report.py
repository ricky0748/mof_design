import tempfile
import unittest
from pathlib import Path

from mof_design.common import write_json, read_json, sha
from mof_design.material_report import describe, render_material_reports


class MaterialReportTests(unittest.TestCase):
    def test_crystal_parameters_recover_known_cubic_cell(self):
        from ase import Atoms
        from ase.io import write
        with tempfile.TemporaryDirectory() as directory:
            cif=Path(directory)/'example.cif'
            write(cif,Atoms('ZnO',positions=[[0,0,0],[2,2,2]],cell=[10,10,10],pbc=True))
            data,_=describe(cif,dict(id='C0001',validation={}),dict(engine='egmof',scene='test'))
            self.assertEqual(data['formula'],'OZn')
            self.assertEqual(data['metals'],['Zn'])
            self.assertAlmostEqual(data['volume_angstrom3'],1000)
            self.assertAlmostEqual(data['density_g_cm3'],(65.38+15.999)/1000*1.66053906660,places=6)
            self.assertIsNone(data['topology'])

    def test_missing_analysis_and_tampered_cif_remain_visible(self):
        from ase import Atoms
        from ase.io import write
        with tempfile.TemporaryDirectory() as directory:
            task=Path(directory);(task/'cifs').mkdir()
            cif=task/'cifs/C0001.cif'
            write(cif,Atoms('ZnO',positions=[[0,0,0],[2,2,2]],cell=[10,10,10],pbc=True))
            write_json(task/'request.json',dict(engine='egmof',scene='test'))
            write_json(task/'status.json',dict(task_id='test'))
            record=dict(id='C0001',status='accepted',cif='cifs/C0001.cif',sha256=sha(cif),validation={})
            write_json(task/'candidates.json',[record])
            files=render_material_reports(task)
            self.assertIn('materials/C0001/structure.svg',files)
            self.assertEqual(len(read_json(task/'materials.json')['materials']),1)
            index=task/'materials/C0001/index.html'
            self.assertTrue(index.exists())
            self.assertIn('待独立孔隙计算',index.read_text(encoding='utf-8'))
            cif.write_text('tampered',encoding='utf-8')
            render_material_reports(task)
            data=read_json(task/'materials.json')
            self.assertEqual(data['materials'],[])
            self.assertIn('hash mismatch',data['errors'][0]['error'])


if __name__=='__main__':unittest.main()
