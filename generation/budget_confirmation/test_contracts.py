import unittest,copy
from compute_config import reusable_early_result
from analysis_rules import choose_combination,wilson

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.dst=dict(input_sha256='input',model_sha256='model',scripts={'worker':'hash'},settings=dict(steps=150,timeout=600,fmax=.2))
        self.rec=dict(status='completed',converged=True,steps=50,wall_seconds=30,calculation_signature={**self.dst,'settings':dict(steps=300,timeout=1200,fmax=.2)})
    def test_early_converged_reusable(self):self.assertTrue(reusable_early_result(self.rec,self.dst))
    def test_151_steps_not_reusable(self):self.rec['steps']=151;self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_long_wall_time_not_reusable(self):self.rec['wall_seconds']=601;self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_unconverged_not_reusable(self):self.rec['converged']=False;self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_failed_not_reusable(self):self.rec['status']='unresolved';self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_input_mismatch_not_reusable(self):self.dst['input_sha256']='other';self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_threshold_mismatch_not_reusable(self):self.dst['settings']['fmax']=.05;self.assertFalse(reusable_early_result(self.rec,self.dst))
    def test_same_yield_prefers_single(self):self.assertEqual(choose_combination(25,25,40,60)['recommendation'],'S')
    def test_quality_gain_bounded_cost_prefers_dual(self):self.assertEqual(choose_combination(25,28,40,47)['recommendation'],'D')
    def test_costly_gain_not_automatic_dual(self):self.assertEqual(choose_combination(25,28,40,49)['recommendation'],'S')
    def test_no_success_unconfirmed(self):self.assertEqual(choose_combination(0,0,None,None)['recommendation'],'unconfirmed')
    def test_wilson_contains_observed_rate(self):
        low,high=wilson(27,30);self.assertLess(low,.9);self.assertGreater(high,.9)

if __name__=='__main__':unittest.main(verbosity=2)
