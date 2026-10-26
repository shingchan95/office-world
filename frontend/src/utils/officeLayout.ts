export type AgentActivity='working'|'leisure'|'walking'|'stairs';
export type PreviewActivity=AgentActivity|'mixed';
export function previewActivity(index:number,mode:PreviewActivity):AgentActivity { return mode==='stairs'?(index===0?'stairs':'working'):mode==='mixed'?(['working','leisure','walking','working'] as const)[index%4]:mode; }
export function deskCapacity(size:number){return Math.floor((size-5)/2)*Math.floor((size-3)/3);}
export function officeSlots(size:number,count:number) {
 const columns=Math.floor((size-5)/2), rows=Math.floor((size-3)/3);
 const capacity=columns*rows;
 return Array.from({length:count},(_,index)=>({index,floor:Math.floor(index/capacity),x:2+(index%capacity%columns)*2,z:2+Math.floor((index%capacity)/columns)*3}));
}
// Grow the footprint first, preserving the user's storey count where possible.
// Do not shrink an existing design when a member is removed.
export function fitRoster<T extends {size:number;land:number;floors:number}>(draft:T,count:number,limits:{size:number;land:number;floors:number}):T {
 if(!Number.isSafeInteger(count)||count<0)return draft;
 let {size,land,floors}=draft;
 while(count>deskCapacity(size)*floors && size<limits.size){
  const nextSize=Math.min(limits.size,size+2);
  while(land<nextSize+4 && land<limits.land)land=Math.min(limits.land,land+4);
  if(land<nextSize+4)break;
  size=nextSize;
 }
 while(count>deskCapacity(size)*floors && floors<limits.floors)floors++;
 return size===draft.size&&land===draft.land&&floors===draft.floors?draft:{...draft,size,land,floors};
}
// Equal arc spacing and a shared speed prevent bunching on the circulation lane.
export function walkOffset(index:number,count:number,size:number){return index*4*(size-3)/Math.max(1,count)/.7;}
