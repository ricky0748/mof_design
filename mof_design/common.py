import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone

TERMINAL = {'completed', 'partial', 'failed', 'cancelled', 'timed_out'}

def now(): return datetime.now(timezone.utc).isoformat()

def read_json(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def inside(path, root):
    p=Path(path).resolve();p.relative_to(Path(root).resolve());return p

def event(task, stage, **fields):
    with (Path(task)/'events.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(dict(time=now(),stage=stage,**fields),ensure_ascii=False,allow_nan=False)+'\n')

def state(task, **updates):
    p=Path(task)/'status.json';data=read_json(p);data.update(updates,updated_at=now());write_json(p,data);return data

def plain(value):
    """Convert upstream scalar metadata without serializing model objects."""
    if value is None or isinstance(value,(str,bool,int)):return value
    if isinstance(value,float):return value if math.isfinite(value) else None
    if hasattr(value,'item'):return plain(value.item())
    return str(value)
