"""Fail closed before reusing unsigned, stale, or altered calculation records."""
import hashlib,json
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def signature(cif,model,code_dir,settings):
    code_dir=Path(code_dir)
    code={p.name:sha(p) for p in sorted(code_dir.glob('*.py'))}
    return dict(schema=1,input_sha256=sha(cif),model_sha256=sha(model),
                scripts=code,settings=settings)

def verify_frozen(out,model):
    out=Path(out);f=json.loads((out/'frozen.json').read_text())
    for name,expected in f['inputs'].items():
        if sha(out/name)!=expected:raise RuntimeError('Frozen input changed: '+name)
    for name,expected in f['scripts'].items():
        if sha(out/name)!=expected:raise RuntimeError('Frozen script changed: '+name+'; use a new run directory')
    if sha(out/'support/anchor_rules.py')!=f['support']:raise RuntimeError('Frozen support changed')
    if sha(model)!=f['model']:raise RuntimeError('Frozen model changed')

def validate_record(path,expected):
    r=json.loads(Path(path).read_text())
    if r.get('calculation_signature')!=expected:
        raise RuntimeError('Unsigned or stale record: '+str(path)+'; use a new run directory')
    if r.get('status')=='completed':
        p=Path(r['out'])
        if not p.exists() or sha(p)!=r.get('output_sha256'):
            raise RuntimeError('Missing or altered relaxed CIF: '+str(p))
    return r
