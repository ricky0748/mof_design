MODEL='/share/rickyswork/ai_mof/mace_medium.model'
SETTINGS=dict(steps=300,timeout=1200,fmax=.2,maxstep=.05,atom_limit=1000,dtype='float64',threads=2,
              neighbor_multiplier=1.15,neighbor_skin=0.,minimum_distance=.9,
              minimum_volume_ratio=.75,maximum_volume_ratio=1.25)

def settings_for(row):return {**SETTINGS,'steps':row['max_steps'],'timeout':row['timeout']}

def reusable_early_result(record,destination_signature):
    src=record.get('calculation_signature',{});dst=destination_signature
    for key in ['input_sha256','model_sha256','scripts']:
        if src.get(key)!=dst.get(key):return False
    ss=src.get('settings',{});ds=dst.get('settings',{})
    if {k:v for k,v in ss.items() if k not in ['steps','timeout']}!={k:v for k,v in ds.items() if k not in ['steps','timeout']}:return False
    return bool(record.get('status')=='completed' and record.get('converged') is True
                and isinstance(record.get('steps'),int) and 0<=record['steps']<=ds['steps']
                and record.get('wall_seconds',float('inf'))<=ds['timeout'])
