"""Versioned identity checks: distinguish target presence from retained types."""
from common import ligand_key

VERSION='linker-type-set-v2'

def check_identity(target,mofid,expected_topology=None):
    expected=ligand_key(target) if target else None
    observed=[ligand_key(s) for s in mofid.get('linkers',[])]
    present=bool(expected and expected in observed)
    exact=bool(expected and observed and all(observed) and set(observed)=={expected})
    identified=bool(mofid.get('framework_key')) and mofid.get('status')=='identified'
    topology=mofid.get('result',{}).get('topology')
    topology_matches=bool(identified and (expected_topology is None or topology==expected_topology))
    return dict(identity_check_version=VERSION,target_present=present,exact_linker_set=exact,
                expected_topology=expected_topology,topology_matches=topology_matches,
                strict_identity=bool(exact and topology_matches))
