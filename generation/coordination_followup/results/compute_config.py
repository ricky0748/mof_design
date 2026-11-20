"""Versioned calculation and geometry settings for new runs."""
MODEL = '/share/rickyswork/ai_mof/mace_medium.model'
SETTINGS = dict(steps=300, fmax=0.05, maxstep=0.05, timeout=600,
                atom_limit=1000, dtype='float64', threads=2,
                neighbor_multiplier=1.15, neighbor_skin=0.0,
                minimum_distance=0.9, minimum_volume_ratio=0.75,
                maximum_volume_ratio=1.25)
