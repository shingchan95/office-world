import {test} from 'node:test';
import assert from 'node:assert/strict';
import {officeSlots} from '../src/utils/officeLayout.ts';
import {teamRoster} from '../src/utils/teamRoster.ts';
test('desks scale with unique roster and reserve non-overlapping work/leisure/roam spaces',()=>{
 const roster=teamRoster([{name:'A',status:'active',members:['One','Shared']},{name:'B',status:'planned',members:['Two','Shared']},{name:'Old',status:'disbanded',members:['Old']}]);
 assert.equal(roster.length,3);assert.deepEqual(roster.find(a=>a.name==='Shared').teams,['A','B']);
 for(const size of [10,12,14,16]){
  const slots=officeSlots(size,100);
  assert.equal(slots.length,100);
  for(const a of slots){
   assert.ok(a.x>=2 && a.x+.62<size-3 && a.z+2.32<size);
   for(const b of slots){if(a.index>=b.index||a.floor!==b.floor)continue;
    // Worst-case independent wander bounds: ±.3 X and ±.2 Z plus avatar radii.
    const dx=Math.max(0,Math.abs(a.x-b.x)-.6),dz=Math.max(0,Math.abs(a.z-b.z)-.4);
    assert.ok(Math.hypot(dx,dz)>.64);
   }
  }
 }
});
