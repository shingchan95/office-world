import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as coords from '../src/utils/coordinates.ts';

test('compact starter has two equal-height storeys and a one-unit tile contract', () => {
  assert.equal(coords.TILE_SIZE, 1);
  assert.equal(coords.BUILDING_SIZE, 10);
  assert.equal(coords.FLOOR_COUNT, 2);
  assert.equal(coords.FLOOR_HEIGHT, 3);
  assert.deepEqual([0,1,2].map(coords.floorElevation), [0,3,6]);
  for (const size of [10,12,16]) for (let x=0;x<size;x++) for(let z=0;z<size;z++) {
    const [wx,wz]=coords.tilePosition(x,z,size);
    assert.ok(Math.abs(wx)+.5<=size/2 && Math.abs(wz)+.5<=size/2);
  }
});
test('production assets remain scoped to canonical design path', () => {
 assert.match(readFileSync(new URL('../vite.config.ts',import.meta.url),'utf8'), /base:\s*['"]\/design\/['"]/);
});
