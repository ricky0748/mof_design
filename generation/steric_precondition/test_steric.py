import unittest
import numpy as np
from ase import Atoms
from ase.optimize import BFGS
from steric import StericCalculator

class StericTests(unittest.TestCase):
    def test_nonbonded_force_repels(self):
        a=Atoms('CC',positions=[[0,0,0],[.5,0,0]],cell=[10,10,10],pbc=True);a.calc=StericCalculator(a,[])
        self.assertLess(a.get_forces()[0,0],0);self.assertGreater(a.get_forces()[1,0],0)
    def test_bond_excluded_from_repulsion(self):
        a=Atoms('HH',positions=[[0,0,0],[.74,0,0]],cell=[10,10,10],pbc=True);a.calc=StericCalculator(a,[(0,1)])
        np.testing.assert_allclose(a.get_forces(),0,atol=1e-12)
    def test_analytic_forces_match_energy_derivative(self):
        a=Atoms('CCC',positions=[[0,0,0],[1.4,0,0],[1.7,.3,0]],cell=[10,10,10],pbc=True);a.calc=StericCalculator(a,[(0,1)])
        a.positions[1,1]+=.04;forces=a.get_forces();epsilon=1e-6
        for i in range(3):
            for axis in range(3):
                x=a.positions[i,axis];a.positions[i,axis]=x+epsilon;plus=a.get_potential_energy();a.positions[i,axis]=x-epsilon;minus=a.get_potential_energy();a.positions[i,axis]=x
                self.assertAlmostEqual(forces[i,axis],-(plus-minus)/(2*epsilon),places=5)
    def test_toy_collision_removed_with_bond_preserved(self):
        a=Atoms('CCC',positions=[[0,0,0],[1.4,0,0],[1.7,.3,0]],cell=[10,10,10],pbc=True);a.calc=StericCalculator(a,[(0,1)])
        BFGS(a,logfile=None,maxstep=.05).run(fmax=.2,steps=50)
        self.assertGreater(a.get_distance(1,2,mic=True),.9);self.assertLess(abs(a.get_distance(0,1,mic=True)-1.4),.3)

if __name__=='__main__':unittest.main(verbosity=2)
