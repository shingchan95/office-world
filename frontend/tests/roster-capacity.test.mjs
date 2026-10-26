import {test} from 'node:test';
import assert from 'node:assert/strict';
import {deskCapacity,fitRoster,officeSlots} from '../src/utils/officeLayout.ts';
import {initialDraft,LIMITS,parseDraft} from '../src/utils/draft.ts';
test('11-member roster grows the starter office and creates one place per unique member',()=>{
 const initial=initialDraft();assert.equal(deskCapacity(initial.size)*initial.floors,8);
 assert.equal(fitRoster(initial,8,LIMITS),initial);
 const fit=fitRoster(initial,11,LIMITS);
 assert.equal(fit.floors,2);assert.equal(fit.size,12);
 const slots=officeSlots(fit.size,11);assert.equal(slots.length,11);
 assert.ok(slots.every(slot=>slot.floor<fit.floors));
 assert.equal(new Set(slots.map(slot=>`${slot.floor}:${slot.x}:${slot.z}`)).size,11);
 assert.deepEqual(parseDraft(JSON.stringify(fit)),fit);
 assert.equal(fitRoster(fit,11,LIMITS),fit,'idempotent refresh');
 assert.equal(fitRoster(fit,6,LIMITS),fit,'removal does not shrink the office');
});
test('roster sizing expands land and then storeys without exceeding configured limits',()=>{
 for(let count=0;count<=100;count++){
  const fit=fitRoster(initialDraft(),count,LIMITS);
  assert.ok(deskCapacity(fit.size)*fit.floors>=count);
  assert.ok(fit.size<=fit.land-4&&fit.size<=LIMITS.size&&fit.land<=LIMITS.land&&fit.floors<=LIMITS.floors);
 }
 const fit=fitRoster(initialDraft(),101,LIMITS);assert.equal(deskCapacity(fit.size)*fit.floors,100);
});
