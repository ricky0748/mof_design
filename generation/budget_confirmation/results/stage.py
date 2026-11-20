import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('key');p.add_argument('out');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
command=a.command[1:] if a.command and a.command[0]=='--' else a.command
start=time.monotonic();r=subprocess.run(command)
out=Path(a.out);data=json.loads(out.read_text()) if out.exists() else {}
data[a.key]=dict(wall_seconds=time.monotonic()-start,returncode=r.returncode,command=command);out.write_text(json.dumps(data,indent=2))
raise SystemExit(r.returncode)
