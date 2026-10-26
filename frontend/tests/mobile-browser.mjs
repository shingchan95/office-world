import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, rm } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import puppeteer from 'puppeteer-core';

// Serve only the built draft, on an ephemeral loopback port; always clean up.
const root = resolve('dist');
let extraMembers=[];
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    // Explicit test fixture only; production uses the authenticated Office API.
    if(path==='/api/teams'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify([{name:'Test Engineering',status:'active',members:['Alice','Zed 1','Zed 2','Zed 3']},{name:'Test Design',status:'active',members:['Carol','Zed 4','Zed 5','Zed 6',...extraMembers]}]));return;}
    if (!path.startsWith('/design/')) { res.writeHead(404).end(); return; }
    const file = resolve(root, path.slice('/design/'.length) || 'index.html');
    if (!file.startsWith(root + '/')) { res.writeHead(403).end(); return; }
    res.setHeader('Content-Type', ({ '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.svg': 'image/svg+xml' })[extname(file)] || 'application/octet-stream');
    res.end(await readFile(file));
  } catch { res.writeHead(404).end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
let browser;
try {
  await mkdir('.tmp', { recursive: true });
  browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, env: { ...process.env, TMPDIR: resolve('.tmp') }, args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const errors = [], external = [], failed = [];
  page.on('pageerror', e => {errors.push(e.message);console.error('PAGEERROR',e.message);});
  page.on('console', m=>{if(m.type()==='error')console.error('BROWSER',m.text());});
  page.on('request', r => { if (!r.url().startsWith('http://127.0.0.1:') && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) external.push(r.url()); });
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) failed.push(`${r.status()} ${r.url()}`); });
  await page.goto(`http://127.0.0.1:${server.address().port}/design/`, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.waitForSelector('canvas', { timeout: 60000 });
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===8);
  assert.equal(await page.$eval('[aria-label="Activity preview"]',e=>e.value),'mixed');
  const mixed=await page.$$eval('[data-avatar]',els=>els.map(el=>({activity:el.dataset.activity,floor:el.dataset.floor,x:Number(el.dataset.worldX),y:Number(el.dataset.worldY)})));
  assert.equal(mixed.filter(a=>a.activity==='leisure').length,2);
  assert.equal(mixed.filter(a=>a.activity==='walking').length,2);
  assert.equal(mixed.filter(a=>a.activity==='working').length,4);
  assert.deepEqual(mixed.filter(a=>a.floor==='0'&&a.activity==='working').map(a=>a.x).sort(),mixed.filter(a=>a.floor==='1'&&a.activity==='working').map(a=>a.x).sort(),'storeys share stacked X coordinates');
  assert.ok(mixed.filter(a=>a.floor==='1').every(a=>a.y>=3),'upper floor stays vertically above ground floor');
  assert.equal(await page.$eval('[aria-label="Visible level"]',e=>e.value),'exterior');
  assert.ok(await page.$eval('.avatar-label',el=>{const s=getComputedStyle(el);return s.borderWidth==='0px'&&s.backgroundColor==='rgba(0, 0, 0, 0)'&&parseFloat(s.fontSize)<=8;}));
  // Exercise the rendered team avatar, not just the standalone route model.
  await page.select('[aria-label="Activity preview"]','stairs');
  await page.waitForSelector('[data-avatar="Alice"][data-activity="stairs"]');
  await page.click('[aria-controls="time-settings"]');
  await page.focus('#simulation-speed');await page.keyboard.press('End');
  await page.waitForFunction(()=>document.querySelector('#time-settings label')?.textContent.includes('3x'));
  await page.click('[aria-controls="time-settings"]');
  const stairSamples=[];
  for(let i=0;i<80;i++){
   await new Promise(r=>setTimeout(r,150));
   stairSamples.push(await page.$eval('[data-activity="stairs"]',el=>({x:Number(el.dataset.worldX),y:Number(el.dataset.worldY),z:Number(el.dataset.worldZ),phase:el.dataset.phase})));
  }
  assert.ok(Math.max(...stairSamples.map(p=>p.y))>=3,'avatar reaches upper landing');
  assert.ok(stairSamples.some(p=>p.phase==='up')&&stairSamples.some(p=>p.phase==='down'),'avatar traverses both directions');
  await page.click('[aria-label="Pause simulation"]');
  const stairPaused=await page.$eval('[data-activity="stairs"]',el=>[el.dataset.worldX,el.dataset.worldY,el.dataset.worldZ]);
  await new Promise(r=>setTimeout(r,300));
  assert.deepEqual(await page.$eval('[data-activity="stairs"]',el=>[el.dataset.worldX,el.dataset.worldY,el.dataset.worldZ]),stairPaused);
  await page.screenshot({path:'tests/stairs-mobile.png'});
  await page.click('[aria-label="Play simulation"]');
  await page.select('[aria-label="Activity preview"]','mixed');
  await page.click('[aria-controls="time-settings"]');
  await page.focus('#simulation-speed');await page.keyboard.press('Home');await page.keyboard.press('ArrowRight');
  await page.click('[aria-controls="time-settings"]');
  assert.equal(await page.$eval('a.back-to-teams', a => a.getAttribute('href')), '/');
  assert.match(await page.$eval('.draft-label', el => el.textContent), /simulated design draft/i);
  assert.equal(await page.$eval('[aria-controls="time-settings"]', el => el.getAttribute('aria-expanded')), 'false');
  assert.equal(await page.$('#time-settings'), null);
  const initial = await page.evaluate(() => {
    const box = s => { const r = document.querySelector(s).getBoundingClientRect(); return { top:r.top,bottom:r.bottom,left:r.left,right:r.right,height:r.height }; };
    return { header:box('.draft-header'), canvas:box('canvas'), toolbar:box('.scene-toolbar'), overflow:document.documentElement.scrollWidth > innerWidth };
  });
  assert.equal(initial.overflow, false);
  assert.ok(initial.canvas.top >= initial.header.bottom && initial.canvas.bottom <= initial.toolbar.top, JSON.stringify(initial));
  assert.ok(initial.canvas.height >= 550, JSON.stringify(initial));
  await page.waitForSelector('[data-draft-size="10"][data-draft-floors="2"]', {timeout:5000});
  await page.select('[aria-label="Visible level"]','0');
  { await page.select('[aria-label="Activity preview"]','working');
  await page.waitForSelector('[data-avatar="Alice"]');
  await new Promise(r=>setTimeout(r,200));
  const stationary=await page.$$eval('[data-avatar]',els=>els.map(e=>[e.dataset.worldX,e.dataset.worldZ]));
  assert.equal(new Set(stationary.map(p=>p.join(','))).size,stationary.length,'each agent has a distinct desk');
  await new Promise(r=>setTimeout(r,200));
  assert.deepEqual(await page.$$eval('[data-avatar]',els=>els.map(e=>[e.dataset.worldX,e.dataset.worldZ])),stationary);
  await page.select('[aria-label="Activity preview"]','walking'); }
  await page.waitForSelector('[data-avatar="Carol"]');
  const location = () => page.$eval('[data-avatar="Carol"]', el => [Number(el.dataset.worldX), Number(el.dataset.worldZ)]);
  let before=await location(),travel=0;
  for(let sample=0;sample<12;sample++){
   await new Promise(r=>setTimeout(r,100));const after=await location();travel+=Math.hypot(after[0]-before[0],after[1]-before[1]);before=after;
   const positions=await page.$$eval('[data-avatar]',els=>els.map(el=>[Number(el.dataset.worldX),Number(el.dataset.worldZ)]));
   for(let a=0;a<positions.length;a++)for(let b=a+1;b<positions.length;b++)assert.ok(Math.hypot(positions[a][0]-positions[b][0],positions[a][1]-positions[b][1])>=.64,'avatars must never overlap');
  }
  assert.ok(travel>.15,'avatar must translate in X/Z, not merely bob');
  await page.click('[aria-label="Pause simulation"]');
  const paused=await location(); await new Promise(r=>setTimeout(r,300)); assert.deepEqual(await location(),paused);
  await page.select('[aria-label="Visible level"]','0');
  await page.waitForSelector('[data-avatar="Alice"]');
  assert.ok(await page.$('[data-avatar="Carol"]'));
  assert.equal(await page.$eval('[data-avatar="Alice"]',el=>el.textContent),'Alice');
  assert.equal(await page.$eval('[data-avatar="Carol"]',el=>el.textContent),'Carol');
  await page.select('[aria-label="Visible level"]','1');
  await page.click('[aria-controls="design-sidebar"]');
  await page.screenshot({path:'tests/design-controls-mobile.png'});
  await page.click('[data-action="expand-office"]');
  assert.equal(await page.$eval('.office-world',e=>e.dataset.draftSize),'12');
  await page.click('[data-action="expand-land"]');
  await page.click('[data-action="add-storey"]');
  assert.equal(await page.$eval('.office-world',e=>e.dataset.draftFloors),'3');
  await page.reload({waitUntil:'networkidle0'});
  await page.waitForSelector('[data-draft-size="12"][data-draft-floors="3"][data-draft-land="20"]');
  await new Promise(r=>setTimeout(r,300));
  await page.screenshot({path:'tests/expanded-three-storeys-mobile.png'});
  await page.click('[aria-controls="design-sidebar"]');
  for(let i=0;i<8;i++) for(const action of ['expand-land','expand-office','add-storey']) await page.$eval(`[data-action="${action}"]`,e=>{if(!e.disabled)e.click()});
  assert.equal(await page.$eval('.office-world',e=>e.dataset.draftFloors),'5');
  assert.equal(await page.$eval('.office-world',e=>e.dataset.draftSize),'16');
  assert.equal(await page.$eval('.office-world',e=>e.dataset.draftLand),'28');
  for(const action of ['expand-land','expand-office','add-storey']) assert.ok(await page.$eval(`[data-action="${action}"]`,e=>e.disabled));
  await page.click('[data-action="reset"]');
  await page.waitForSelector('[data-draft-size="10"][data-draft-floors="2"]');
  await page.click('[aria-label="Close design controls"]');
  await page.click('[aria-label="Pause simulation"]');
  await page.waitForSelector('[aria-label="Play simulation"]');
  await page.click('[aria-controls="time-settings"]');
  await page.waitForSelector('#time-settings');
  await page.$eval('#simulation-speed', el => { el.value = 100; el.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.click('[aria-controls="time-settings"]');
  await page.click('[aria-controls="design-sidebar"]');
  await page.waitForSelector('#design-sidebar');
  assert.ok(await page.$eval('[aria-label="Close design controls"]', el => { const r=el.getBoundingClientRect(); return r.width>=44 && r.height>=44 && document.elementFromPoint(r.x+r.width/2,r.y+r.height/2) === el; }));
  await page.setViewport({ width: 390, height: 500, isMobile: true, hasTouch: true });
  await new Promise(r => setTimeout(r, 200));
  const scroll = await page.$eval('.sidebar-content', el => { el.scrollTop=10000; return { scrollTop:el.scrollTop, scrollable:el.scrollHeight>el.clientHeight }; });
  assert.ok(scroll.scrollable && scroll.scrollTop>0, JSON.stringify(scroll));
  await page.click('[aria-label="Close design controls"]');
  assert.equal(await page.$('#design-sidebar'), null);
  await page.setViewport({ width: 844, height: 390, isMobile: true, hasTouch: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await page.screenshot({ path:'tests/mobile-390x844.png' });
  await page.setViewport({width:1440,height:1000});
  await new Promise(r=>setTimeout(r,300));
  await page.waitForSelector('[data-avatar]',{timeout:10000});
  assert.ok(await page.$$eval('[data-avatar]',els=>els.length)>0,'avatars must render at desktop viewport too');
  await page.screenshot({path:'tests/desktop-cutaway.png'});
  await page.select('[aria-label="Visible level"]','exterior');
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===8);
  assert.equal(await page.$$eval('[data-avatar]',els=>els.length),8);
  assert.ok(await page.$$eval('[data-avatar]',els=>els.every(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;})),'all avatar labels fit the desktop overview');
  await new Promise(r=>setTimeout(r,300));
  await page.screenshot({path:'tests/desktop-exterior.png'});
  await page.evaluate(()=>localStorage.setItem('office-world-design-v2','{"version":2,"size":999}'));
  await page.reload({waitUntil:'networkidle0'});
  await page.waitForSelector('[data-draft-size="10"][data-draft-floors="2"]');
  assert.equal(await page.$eval('[aria-label="Visible level"]',e=>e.value),'exterior');
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  assert.deepEqual(failed, []);
  // Regression: roster growth 8 -> 11 -> 12 must place every member without a page reload.
  extraMembers=['Zed 7','Zed 8','Zed 9'];
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===11);
  assert.equal(await page.$eval('.office-world',el=>el.dataset.draftSize),'12');
  assert.equal(await page.$eval('.office-world',el=>el.dataset.draftFloors),'2');
  extraMembers.push('Zed 10');
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===12);
  extraMembers=[];
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===8);
  assert.equal(await page.$eval('.office-world',el=>el.dataset.draftSize),'12','roster removals do not shrink the designed office');
  // An unsigned desktop browser must explain the empty scene, not silently hide identities.
  await page.setRequestInterception(true);
  let signedInFixture=false;
  page.on('request',req=>{if(new URL(req.url()).pathname==='/api/teams'&&!signedInFixture)void req.respond({status:401,contentType:'application/json',body:'{"error":"Sign in to Office."}'});else void req.continue();});
  await page.reload({waitUntil:'networkidle0'});
  await page.waitForSelector('.roster-notice a[href="/"]');
  assert.match(await page.$eval('.roster-notice',el=>el.textContent),/Sign in/);
  assert.equal(await page.$$eval('[data-avatar]',els=>els.length),0);
  signedInFixture=true;
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await page.waitForFunction(()=>document.querySelectorAll('[data-avatar]').length===8,{timeout:10000});
  console.log('PASS: 390x844 scene clearance, navigation/draft label, collapsed/expandable time controls, reachable 44px sidebar close, sidebar scroll, landscape overflow, no JS errors/external requests/failed assets.');
  console.log(JSON.stringify(initial));
} catch(error) {
 console.error('Browser failure:', error.message);
 if(browser){for(const page of await browser.pages()){console.error(await page.evaluate(()=>document.querySelector('.scene-space')?.innerHTML));await page.screenshot({path:'tests/failure.png'});}}
 throw error;
} finally {
  await browser?.close();
  await new Promise(r => server.close(r));
  await rm(resolve('.tmp'), { recursive: true, force: true });
}
