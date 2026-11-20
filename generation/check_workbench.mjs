import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const root=path.resolve('generation');
const profile=await fs.mkdtemp(path.join(os.tmpdir(),'mof-map-chrome-'));
const chrome='C:/Program Files/Google/Chrome/Application/chrome.exe';
const child=spawn(chrome,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
let ws;
try{
  let port;
  for(let i=0;i<80;i++){try{port=(await fs.readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break}catch{await new Promise(r=>setTimeout(r,150))}}
  if(!port)throw Error('Chrome did not expose DevTools');
  const version=await(await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  ws=new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
  let serial=0;const pending=new Map();
  ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}};
  const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(Error('Timed out: '+method))}},15000).unref()});
  const {targetId}=await send('Target.createTarget',{url:'about:blank'});
  const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
  const call=(m,p={})=>send(m,p,sessionId);
  const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value};
  await call('Page.enable');await call('Runtime.enable');
  await call('Emulation.setDeviceMetricsOverride',{width:1600,height:1050,deviceScaleFactor:1,mobile:false});
  await call('Page.navigate',{url:process.env.WORKBENCH_URL||pathToFileURL(path.join(root,'project-workbench.html')).href});
  for(let i=0;i<50;i++){if(await evaluate('!!window.MOFWorkbench'))break;await new Promise(r=>setTimeout(r,100))}
  const bytes=await fs.readFile(path.join(root,'project-workbench.html'));
  const receipt={entry:process.env.WORKBENCH_URL||'file',artifact:{sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length},views:[],interaction:{},screenshots:[]};
  const capture=async(name)=>{await new Promise(r=>setTimeout(r,240));const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(path.join(root,name),Buffer.from(shot.data,'base64'));receipt.screenshots.push(name)};
  for(const id of ['overview','generation','quality','identity','performance','research']){
    await evaluate(`MOFWorkbench.showView(${JSON.stringify(id)})`);
    await new Promise(r=>setTimeout(r,80));
    const r=await evaluate(`(()=>{const v=MOFWorkbench.data.views.find(v=>v.id===MOFWorkbench.state.view),hits=[];document.querySelectorAll('.edge').forEach(g=>{const points=g.querySelector('path').getAttribute('d').match(/[ML][^ML]+/g).map(p=>p.slice(1).split(',').map(Number));for(let i=1;i<points.length;i++){const [x1,y1]=points[i-1],[x2,y2]=points[i];for(const n of v.positions){if([g.dataset.a,g.dataset.b].includes(n.id))continue;const hit=x1===x2?x1>n.x+1&&x1<n.x+289&&Math.max(Math.min(y1,y2),n.y+1)<Math.min(Math.max(y1,y2),n.y+153):y1>n.y+1&&y1<n.y+153&&Math.max(Math.min(x1,x2),n.x+1)<Math.min(Math.max(x1,x2),n.x+289);if(hit)hits.push({from:g.dataset.a,to:g.dataset.b,obstacle:n.id})}}});return {view:v.id,nodes:v.positions.length,edges:document.querySelectorAll('.edge').length,bodyOverflow:document.documentElement.scrollWidth>innerWidth,clipped:[...document.querySelectorAll('.node')].filter(n=>n.scrollHeight>n.clientHeight+1).map(n=>n.dataset.id),nodeRouteCollisions:hits}})()`);
    receipt.views.push(r);
    await capture('project-workbench.'+id+'.png');
  }
  await evaluate("MOFWorkbench.showView('identity'); MOFWorkbench.select('mofid')");
  receipt.interaction.inspector=await evaluate("document.getElementById('inspector').classList.contains('open')&&document.getElementById('detailTitle').textContent.includes('CIF')&&document.querySelectorAll('.evidence').length>0");
  await capture('project-workbench.detail.png');
  await evaluate("MOFWorkbench.select('idcompare'); MOFWorkbench.trace('up')");
  receipt.interaction.trace=await evaluate("MOFWorkbench.state.traced.includes('mofid')&&MOFWorkbench.state.traced.includes('trainref')&&document.querySelectorAll('.node.dim').length>0");
  await evaluate("MOFWorkbench.reset(); document.getElementById('search').value='MOFid'; document.getElementById('search').dispatchEvent(new Event('input'))");
  receipt.interaction.search=await evaluate("document.querySelectorAll('.node.search-hit').length>0&&document.getElementById('searchCount').textContent.includes('项')");
  await evaluate("MOFWorkbench.select('mofid'); document.querySelector('.notes').value='验证备注'; document.querySelector('.notes').dispatchEvent(new Event('input')); MOFWorkbench.select('mofid')");
  receipt.interaction.notes=await evaluate("document.querySelector('.notes').value==='验证备注'");
  await evaluate("localStorage.removeItem('mof-workbench-note-mofid'); MOFWorkbench.reset(); MOFWorkbench.showView('overview'); document.getElementById('fit').click()");
  receipt.interaction.fit=await evaluate("document.getElementById('space').getBoundingClientRect().width<=document.getElementById('scroller').clientWidth");
  receipt.interaction.export=await evaluate("(async()=>{let blob;const oldURL=URL.createObjectURL,oldClick=HTMLAnchorElement.prototype.click;URL.createObjectURL=b=>{blob=b;return 'blob:export-test'};HTMLAnchorElement.prototype.click=function(){};MOFWorkbench.exportSVG();URL.createObjectURL=oldURL;HTMLAnchorElement.prototype.click=oldClick;const doc=new DOMParser().parseFromString(await blob.text(),'image/svg+xml');return !doc.querySelector('parsererror')&&doc.querySelectorAll('rect').length>10})()");
  for(const width of [1440,1920]){await call('Emulation.setDeviceMetricsOverride',{width,height:width===1440?900:1080,deviceScaleFactor:1,mobile:false});await evaluate("MOFWorkbench.showView('overview'); document.getElementById('fit').click()");await capture(`project-workbench.overview-${width}.png`)}
  receipt.narrow=[];
  for(const width of [900,600]){await call('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await evaluate("MOFWorkbench.showView('overview')");receipt.narrow.push(await evaluate("({width:innerWidth,bodyOverflow:document.documentElement.scrollWidth>innerWidth,mapFits:document.getElementById('space').getBoundingClientRect().width<=document.getElementById('scroller').clientWidth,zoom:MOFWorkbench.state.zoom})"));await capture(`project-workbench.narrow-${width}.png`)}
  receipt.ok=receipt.views.every(v=>!v.bodyOverflow&&!v.clipped.length&&!v.nodeRouteCollisions.length)&&Object.values(receipt.interaction).every(Boolean)&&receipt.narrow.every(v=>!v.bodyOverflow&&v.mapFits);
  await fs.writeFile(path.join(root,'project-workbench.check.json'),JSON.stringify(receipt,null,2));
  console.log(JSON.stringify(receipt,null,2));
  await send('Browser.close');
  if(!receipt.ok)process.exitCode=1;
}finally{ws?.close();child.kill();}
