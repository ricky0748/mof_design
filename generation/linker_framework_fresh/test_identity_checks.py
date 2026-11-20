import json,unittest,tempfile
from pathlib import Path
from identity_checks import check_identity
from eval_helpers import evaluate

TARGET='O=C(O)c1ccc(C(=O)O)cc1'
def record(linkers=None,topology='pcu',status='identified'):
    return dict(linkers=[TARGET] if linkers is None else linkers,result=dict(topology=topology),framework_key='test-key',status=status)

class IdentityTests(unittest.TestCase):
    def test_expected_ligand_and_topology(self):self.assertTrue(check_identity(TARGET,record(),'pcu')['strict_identity'])
    def test_additional_fragment_rejected(self):
        r=check_identity(TARGET,record([TARGET,'[CH2]C']),'pcu');self.assertTrue(r['target_present']);self.assertFalse(r['strict_identity'])
    def test_wrong_topology_rejected(self):self.assertFalse(check_identity(TARGET,record(topology='dia'),'pcu')['strict_identity'])
    def test_missing_or_unparseable_linkers_rejected(self):
        for ss in [[],['bad_smiles'],[TARGET,'bad_smiles']]:self.assertFalse(check_identity(TARGET,record(ss),'pcu')['strict_identity'])
    def test_partial_identity_rejected(self):self.assertFalse(check_identity(TARGET,record(status='partial'),'pcu')['strict_identity'])
    def test_protonation_normalized(self):
        self.assertTrue(check_identity(TARGET,record(['O=C([O-])c1ccc(C(=O)[O-])cc1']),'pcu')['strict_identity'])
    def test_evaluator_exposes_legacy_and_strict_separately(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'records').mkdir();(p/'records/X.json').write_text(json.dumps(dict(status='completed',geometry_valid=True)))
            r=evaluate('X',TARGET,p,{'X':record([TARGET,'[CH2]C'])},expected_topology='pcu')
            self.assertTrue(r['joint']);self.assertFalse(r['strict_joint'])
    def test_archived_fresh_acceptances_unchanged(self):
        p=Path(__file__).resolve().parent/'results';pairs=json.loads((p/'pairs.json').read_text());m={r['id']:r for r in map(json.loads,(p/'mofid/results.jsonl').read_text().splitlines())}
        for row in pairs:
            for arm in ['U7','U19']:
                if row[arm]['joint']:self.assertTrue(check_identity(row['smiles'],m[arm+'_'+row['id']],'pcu')['strict_identity'])
    def test_real_fragmented_results_rejected(self):
        p=Path(__file__).resolve().parent.parent/'steric_precondition/results';selected={r['name']:r for r in json.loads((p/'selected.json').read_text())};m={r['id']:r for r in map(json.loads,(p/'mofid/results.jsonl').read_text().splitlines())}
        for name in ['U7_F11','U19_F04']:
            r=check_identity(selected[name]['smiles'],m[name],'pcu');self.assertTrue(r['target_present']);self.assertFalse(r['strict_identity'])

if __name__=='__main__':unittest.main(verbosity=2)
