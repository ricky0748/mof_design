"""Versioned calculation and geometry settings for new runs."""
MODEL = '/share/rickyswork/ai_mof/mace_medium.model'
SETTINGS = dict(steps=100, fmax=0.2, maxstep=0.05, timeout=600,
                atom_limit=1000, dtype='float64', threads=2,
                neighbor_multiplier=1.15, neighbor_skin=0.0,
                minimum_distance=0.9, minimum_volume_ratio=0.75,
                maximum_volume_ratio=1.25)

SETTINGS.update(precondition_steps=50, precondition_target=1.2, precondition_repulsion=100.0, precondition_bond=100.0, precondition_position=1.0, precondition_min_distance=0.9, precondition_max_bond_shift=0.3)
