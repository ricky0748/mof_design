"""Read-only localhost entry for the MOF workbench. No third-party dependencies.

python generation/serve_workbench.py --ensure --open
Only the built workbench and its explicitly referenced evidence files are served.
"""
import argparse
from datetime import datetime, timezone
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'generation/workbench-server.json'
APP = 'ai-mof-workbench'


def allowed_files():
    data = json.loads((ROOT / 'generation/project-workbench.data.json').read_text(encoding='utf-8'))
    paths = {p for n in data['nodes'].values() for p in n['evidence']}
    paths.update({'PROJECT_MAP.md', 'worklog.md'})
    return {('/' + p.replace('\\', '/')): (ROOT / p).resolve() for p in paths}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(self.log_date_time_string(), fmt % args, flush=True)

    def respond(self, status, content, kind):
        data = content.encode('utf-8') if isinstance(content, str) else content
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        requested = unquote(urlsplit(self.path).path)
        if requested == '/health':
            self.respond(200, json.dumps(dict(app=APP, root=str(ROOT), pid=os.getpid())), 'application/json; charset=utf-8')
            return
        if requested in ('/', '/generation/project-workbench.html'):
            self.respond(200, (ROOT / 'generation/project-workbench.html').read_bytes(), 'text/html; charset=utf-8')
            return
        evidence = allowed_files().get(requested)
        if evidence is None or not evidence.is_relative_to(ROOT) or not evidence.is_file():
            self.respond(404, 'This file is not part of the workbench evidence.', 'text/plain; charset=utf-8')
            return
        text = evidence.read_text(encoding='utf-8-sig', errors='replace')
        title = html.escape(str(evidence.relative_to(ROOT)).replace('\\', '/'))
        content = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;background:#f5f7f9;color:#243d4d;font:14px 'Segoe UI','Microsoft YaHei',sans-serif}}
header{{padding:22px 28px;background:#fff;border-bottom:1px solid #dae4e9;position:sticky;top:0}}
a{{color:#087b70}}h1{{font-size:17px;overflow-wrap:anywhere}}main{{max-width:1280px;margin:24px auto;padding:0 24px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.85 Consolas,'Microsoft YaHei',monospace;background:#fff;padding:24px;border:1px solid #dae4e9;border-radius:8px}}</style>
<header><a href="/generation/project-workbench.html">← 返回研究工作台</a><h1>{title}</h1>项目文件 · 只读预览</header>
<main><pre>{html.escape(text)}</pre></main></html>'''
        self.respond(200, content, 'text/html; charset=utf-8')


def healthy(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/health', timeout=0.5) as response:
            state = json.load(response)
        return state.get('app') == APP and state.get('root') == str(ROOT)
    except (OSError, ValueError, URLError):
        return False


def ensure():
    if STATE.exists():
        try:
            port = int(json.loads(STATE.read_text())['port'])
            if healthy(port):
                return port
        except (ValueError, KeyError):
            pass
    log_path = ROOT / 'generation/workbench-server.log'
    with log_path.open('ab') as log:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve())], cwd=str(ROOT),
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                         start_new_session=os.name != 'nt')
    for _ in range(60):
        time.sleep(0.1)
        if STATE.exists():
            try:
                port = int(json.loads(STATE.read_text())['port'])
                if healthy(port):
                    return port
            except (OSError, ValueError, KeyError):
                pass
    raise RuntimeError(f'工作台启动未完成，请查看 {log_path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ensure', action='store_true')
    ap.add_argument('--open', action='store_true')
    args = ap.parse_args()
    if args.ensure:
        port = ensure()
        url = f'http://127.0.0.1:{port}/generation/project-workbench.html'
        print(url, flush=True)
        if args.open:
            webbrowser.open(url)
        return
    for port in range(8765, 8786):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    else:
        raise RuntimeError('8765–8785 端口均不可用。')
    server.daemon_threads = True
    state = dict(app=APP, root=str(ROOT), port=port, pid=os.getpid(),
                 started=datetime.now(timezone.utc).isoformat())
    STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print(f'Workbench ready: http://127.0.0.1:{port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
