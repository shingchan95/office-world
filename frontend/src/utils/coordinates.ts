// Tile indices refer to cell centres. Every draft system uses this contract.
export const TILE_SIZE = 1;
export const BUILDING_SIZE = 10;
export const FLOOR_HEIGHT = 3;
export const FLOOR_COUNT = 2;
export function tilePosition(x: number, z: number, size = BUILDING_SIZE): [number, number] {
  return [(x + 0.5) * TILE_SIZE - size * TILE_SIZE / 2, (z + 0.5) * TILE_SIZE - size * TILE_SIZE / 2];
}
export function floorElevation(floor: number): number { return floor * FLOOR_HEIGHT; }
// All views preserve the physical stacked building; never move floors apart.
export function floorOffset(_floor:number,_size:number,_floors:number,_overview:boolean):number { return 0; }
