import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
const model = async () => { const url=new URL('../src/utils/draft.ts',import.meta.url); assert.ok(existsSync(url), 'draft dimension model is missing'); return import(url); };
test('local draft expands land, footprint and storeys with bounded validated persistence', async () => {
 const m=await model(); let d=m.initialDraft();
 assert.deepEqual([d.land,d.size,d.floors,d.selectedFloor], [16,10,2,null]);
 d=m.changeDraft(d,'expand-office'); assert.equal(d.size,12);
 for(let i=0;i<30;i++) {d=m.changeDraft(d,'expand-land'); d=m.changeDraft(d,'expand-office'); d=m.changeDraft(d,'add-storey');}
 assert.deepEqual([d.land,d.size,d.floors], [28,16,5]);
 assert.ok(d.size<=d.land-4);
 assert.deepEqual(m.parseDraft(JSON.stringify(d)), d);
 for(const bad of ['bad','null','{"version":1}',JSON.stringify({...d,size:100}),JSON.stringify({...d,floors:2.5}), JSON.stringify({...d,selectedFloor:9})]) assert.deepEqual(m.parseDraft(bad),m.initialDraft());
 assert.deepEqual(m.changeDraft(d,'reset'),m.initialDraft());
});
test('one-tile desktops and avatars fit, walking routes translate continuously without furniture collisions', async () => {
 const m=await model();
 assert.ok(m.DESK_SIZE[0]<=1 && m.DESK_SIZE[2]<=1);
 assert.ok(m.AVATAR_RADIUS*2<=1);
 for(const size of [10,12,14,16]) {
  const furniture=m.furnitureLayout(size);
  for(const item of furniture) assert.ok(item.x>=1 && item.x<size-1 && item.z>=1 && item.z<size-1);
  const a=m.walkPosition(0,size), b=m.walkPosition(.5,size);
  assert.ok(Math.hypot(a.x-b.x,a.z-b.z)>.2);
  for(let t=0;t<150;t+=.1) {
   const p=m.walkPosition(t,size);
   assert.ok(p.x>=0 && p.x<=size-1 && p.z>=0 && p.z<=size-1);
   for(const f of furniture) assert.ok(Math.abs(p.x-f.x)>.5+m.AVATAR_RADIUS || Math.abs(p.z-f.z)>.5+m.AVATAR_RADIUS, 'route clips furniture');
   const next=m.walkPosition(t+.01,size);
   assert.ok(Math.hypot(next.x-p.x,next.z-p.z)<=.011);
  }
 }
});
