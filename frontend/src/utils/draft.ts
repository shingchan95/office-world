// All horizontal dimensions are in tiles (= world units).
export const DESK_SIZE: [number, number, number] = [0.92, 0.09, 0.68];
export const AVATAR_RADIUS = 0.32;
export function furnitureLayout(size: number) {
 return [3, size-4].flatMap((x,i) => [3,size-4].map((z,j) => ({id:`desk-${i}-${j}`,x,z})));
}
// Reserved perimeter circulation lane; desks occupy only the inner square.
// Constant speed around orthogonal segments avoids corner-cutting and teleporting.
export function walkPosition(seconds: number, size: number) {
 const length=size-3;
 const distance=((seconds*0.7)%(4*length)+4*length)%(4*length);
 const side=Math.floor(distance/length), t=distance%length;
 return side===0 ? {x:1+t,z:1,heading:Math.PI/2} : side===1 ? {x:size-2,z:1+t,heading:0} : side===2 ? {x:size-2-t,z:size-2,heading:-Math.PI/2} : {x:1,z:size-2-t,heading:Math.PI};
}
export const DRAFT_KEY = 'office-world-design-v2';
export const LIMITS = { land: 28, size: 16, floors: 5 };
export interface Draft { version: 2; land: number; size: number; floors: number; selectedFloor: number | null }
export type DraftAction = 'expand-land' | 'expand-office' | 'add-storey' | 'reset';
export function initialDraft(): Draft { return { version: 2, land: 16, size: 10, floors: 2, selectedFloor: null }; }
export function changeDraft(d: Draft, action: DraftAction): Draft {
 switch(action) {
  case 'reset': return initialDraft();
  case 'expand-land': return {...d,land:Math.min(LIMITS.land,d.land+4)};
  case 'expand-office': return {...d,size:Math.min(LIMITS.size,d.land-4,d.size+2)};
  case 'add-storey': return {...d,floors:Math.min(LIMITS.floors,d.floors+1),selectedFloor:Math.min(LIMITS.floors,d.floors+1)-1};
 }
}
export function parseDraft(raw: string | null): Draft {
 try {
  const d=JSON.parse(raw || 'null');
  if(d?.version===2 && Number.isInteger(d.land) && d.land>=16 && d.land<=28 && (d.land-16)%4===0 && Number.isInteger(d.size) && d.size>=10 && d.size<=16 && d.size%2===0 && d.size<=d.land-4 && Number.isInteger(d.floors) && d.floors>=2 && d.floors<=5 && (d.selectedFloor===null || (Number.isInteger(d.selectedFloor) && d.selectedFloor>=0 && d.selectedFloor<d.floors))) {
   return {version:2,land:d.land,size:d.size,floors:d.floors,selectedFloor:d.selectedFloor};
  }
 } catch { /* Corrupt/old drafts fall back safely. */ }
 return initialDraft();
}
