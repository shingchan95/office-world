import {test} from 'node:test';
import assert from 'node:assert/strict';
import {stairGeometry,stairTestRoute,stairTestPosition} from '../src/utils/stairs.ts';
test('stair test follows shared stairwell up every storey and back down without jumps',()=>{
 for(const size of [10,12,14,16])for(const floors of [2,3,4,5]){
  const geometry=stairGeometry(size),route=stairTestRoute(size,floors),duration=route.reduce((sum,s)=>sum+s.duration,0);
  for(let i=1;i<route.length;i++)assert.deepEqual(route[i].a,route[i-1].b,'segments join without teleporting');
  let previous=stairTestPosition(0,size,floors),highest=0;const phases=new Set();
  for(let time=.025;time<duration;time+=.025){
   const p=stairTestPosition(time,size,floors);highest=Math.max(highest,p.y);phases.add(p.phase);
   assert.ok(p.y>=-1e-8&&p.y<=(floors-1)*3+1e-8);
   assert.ok(Math.hypot(p.x-previous.x,p.y-previous.y,p.z-previous.z)<=1.4*.025+.00001,'bounded continuous velocity');
   if(p.phase==='up'||p.phase==='down')assert.ok(p.x>geometry.left&&p.x<geometry.right);
   previous=p;
  }
  assert.equal(highest,(floors-1)*3);assert.ok(phases.has('up')&&phases.has('down')&&phases.has('upper landing'));
  assert.deepEqual(stairTestPosition(duration,size,floors),stairTestPosition(0,size,floors),'repeat joins at bottom landing');
 }
});
