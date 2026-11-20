"""Strict requests and scene-aware runtime configuration; no model imports."""
import math
from pathlib import Path
from .common import read_json

ENGINES={'egmof':dict(role='default_mof_generator',constraints='post_generation_filter'),
         'mofflow2_linker':dict(role='linker_exploration_with_fixed_assembly',constraints='post_generation_filter')}
ELEMENTS=set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split())

def integer(value, name, lo, hi):
    if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:raise ValueError(f'{name} must be an integer in [{lo}, {hi}]')
    return value

def normalize_request(raw, runtime):
    if not isinstance(raw,dict):raise ValueError('request must be an object')
    allowed={'engine','scene','target_value','num_candidates','max_attempts','seed','walltime_seconds','constraints','validation','sequence_samples'}
    if set(raw)-allowed:raise ValueError('unknown request fields: '+', '.join(sorted(set(raw)-allowed)))
    engine=raw.get('engine','egmof')
    if engine not in ENGINES:raise ValueError('unsupported engine: '+str(engine))
    if engine not in runtime.get('engines',{}):raise ValueError('engine is not configured: '+engine)
    scene_id=raw.get('scene',runtime['engines'][engine].get('default_scene'))
    scene=runtime.get('scenes',{}).get(scene_id)
    if not scene or scene.get('engine')!=engine:raise ValueError('scene is not supported by the selected engine')
    if scene.get('enabled',True) is not True:raise ValueError('scene is disabled')
    target=raw.get('target_value')
    if isinstance(target,bool) or not isinstance(target,(int,float)) or not math.isfinite(target):raise ValueError('target_value must be a finite number in the scene checkpoint scale')
    if 'target_range' in scene and not scene['target_range'][0]<=target<=scene['target_range'][1]:raise ValueError('target_value outside declared scene range')
    count=integer(raw.get('num_candidates',3),'num_candidates',1,100)
    attempts=integer(raw.get('max_attempts',count*3),'max_attempts',count,1000)
    constraints=raw.get('constraints',{})
    if not isinstance(constraints,dict) or set(constraints)-{'allowed_elements','forbidden_elements','topologies','max_atoms'}:raise ValueError('unsupported constraint fields')
    constraints=dict(constraints)
    for key in ['allowed_elements','forbidden_elements','topologies']:
        if key in constraints:
            values=constraints[key]
            if not isinstance(values,list) or not values or not all(isinstance(v,str) and v for v in values):raise ValueError(key+' must be a nonempty string list')
            if key!='topologies' and not set(values)<=ELEMENTS:raise ValueError('unknown element in '+key)
            constraints[key]=sorted(set(values))
    if 'allowed_elements' in constraints and not set(constraints['allowed_elements'])-set(constraints.get('forbidden_elements',[])):raise ValueError('element constraints allow no elements')
    constraints['max_atoms']=integer(constraints.get('max_atoms',1000),'max_atoms',1,1000)
    if engine=='mofflow2_linker' and constraints.get('topologies') and 'pcu' not in constraints['topologies']:raise ValueError('linker exploration currently supports only pcu/N16 (Zn4O)')
    validation=raw.get('validation',{})
    if not isinstance(validation,dict) or set(validation)-{'relax','mofid'}:raise ValueError('unsupported validation fields')
    validation={'relax':validation.get('relax',True),'mofid':validation.get('mofid',False)}
    if not all(isinstance(v,bool) for v in validation.values()):raise ValueError('validation flags must be boolean')
    if validation['relax'] and 'relaxation' not in runtime:raise ValueError('relaxation runtime is required; disable explicitly for geometry-only output')
    if validation['mofid'] and 'mofid' not in runtime:raise ValueError('MOFid runtime is not configured')
    if constraints.get('topologies') and not validation['mofid']:raise ValueError('topology constraints require MOFid validation of the final structure')
    seq=integer(raw.get('sequence_samples',100),'sequence_samples',1,1000)
    if engine=='egmof' and 'sequence_samples' in raw:raise ValueError('sequence_samples applies only to linker exploration')
    result=dict(engine=engine,scene=scene_id,target_value=float(target),num_candidates=count,max_attempts=attempts,
                seed=integer(raw.get('seed',1703),'seed',0,2**31-1),walltime_seconds=integer(raw.get('walltime_seconds',1800),'walltime_seconds',1,86400),constraints=constraints,validation=validation)
    if engine=='mofflow2_linker':result['sequence_samples']=seq
    return result

def load_runtime(source):
    data=read_json(source) if not isinstance(source,dict) else source
    if data.get('version')!=1:raise ValueError('runtime version must be 1')
    if not isinstance(data.get('engines'),dict) or not isinstance(data.get('scenes'),dict):raise ValueError('runtime must define engines and scenes')
    return data

def preflight(request,runtime):
    cfg=runtime['engines'][request['engine']];scene=runtime['scenes'][request['scene']]
    paths={'engine_python':cfg.get('python'),'repository':cfg.get('repository')}
    assets=scene.get('assets',{})
    required=['prop2desc_checkpoint','prop2desc_config'] if request['engine']=='egmof' else ['checkpoint','checkpoint_config','support']
    for name in required:paths[name]=assets.get(name)
    if request['engine']=='egmof':
        for name,rel in [('desc2mof_checkpoint','checkpoints/desc2mof/desc2mof_best.ckpt'),('mof2desc_checkpoint','checkpoints/mof2desc/mof2desc_best.ckpt')]:paths[name]=str(Path(cfg['repository'])/rel)
    else:paths['sequence_python']=cfg.get('sequence_python')
    if request['validation']['relax']:
        paths.update(relaxation_python=runtime['relaxation'].get('python'),mace_model=runtime['relaxation'].get('model'))
    if request['validation']['mofid']:
        paths.update(mofid_python=runtime['mofid'].get('python'),mofid_script=runtime['mofid'].get('script'),mofid_pythonpath=runtime['mofid'].get('pythonpath'),java_bin=runtime['mofid'].get('java_bin'))
    missing=[k for k,p in paths.items() if not isinstance(p,str) or not Path(p).exists()]
    if missing:raise ValueError('runtime assets not available: '+', '.join(missing))
    return paths
