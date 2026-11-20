import argparse
import json
import sys
from .common import read_json
from .config import ENGINES,load_runtime,normalize_request,preflight
from .api import run_design,submit_design,get_status,cancel_design

def main():
    ap=argparse.ArgumentParser(prog='python -m mof_design');sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('engines')
    p=sub.add_parser('scenes');p.add_argument('--runtime',required=True)
    for name in ['validate','run','submit']:
        p=sub.add_parser(name);p.add_argument('--request',required=True);p.add_argument('--runtime',required=True);p.add_argument('--out',default='design_runs')
    for name in ['status','cancel']:
        p=sub.add_parser(name);p.add_argument('task')
    p=sub.add_parser('material-report');p.add_argument('task')
    args=ap.parse_args()
    try:
        if args.command=='engines':data=ENGINES
        elif args.command=='scenes':
            runtime=load_runtime(args.runtime);data={k:{x:v for x,v in s.items() if x!='assets'} for k,s in runtime['scenes'].items()}
        elif args.command in ['status','cancel']:data=(get_status if args.command=='status' else cancel_design)(args.task)
        elif args.command=='material-report':
            from .material_report import render_material_reports
            data=dict(files=render_material_reports(args.task),note='Material reports refreshed; existing candidate ZIP and provenance unchanged.')
        else:
            runtime=load_runtime(args.runtime);request=normalize_request(read_json(args.request),runtime)
            if args.command=='validate':data=dict(valid=True,request=request,assets=preflight(request,runtime),scene={k:v for k,v in runtime['scenes'][request['scene']].items() if k!='assets'})
            else:data=(run_design if args.command=='run' else submit_design)(request,runtime,args.out)
        print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps(dict(error=type(exc).__name__,message=str(exc)),ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
