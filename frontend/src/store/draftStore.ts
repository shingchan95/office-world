import { create } from 'zustand';
import { DRAFT_KEY, LIMITS, changeDraft, initialDraft, parseDraft } from '../utils/draft';
import { fitRoster } from '../utils/officeLayout';
import type { Draft, DraftAction } from '../utils/draft';
function load() { try { return {draft:{...parseDraft(localStorage.getItem(DRAFT_KEY)),selectedFloor:null},storageAvailable:true}; } catch {return {draft:initialDraft(),storageAvailable:false};} }
interface DraftState {
 draft: Draft; storageAvailable: boolean; playing: boolean; speed: number;
 ensureCapacity: (count:number) => void;
 act: (action: DraftAction) => void; selectFloor: (floor: number|null) => void;
 togglePlaying: () => void; setSpeed: (speed:number) => void;
}
export const useDraftStore=create<DraftState>((set,get)=> {
 const save=(draft:Draft) => {
  let storageAvailable=true;
  try {localStorage.setItem(DRAFT_KEY,JSON.stringify(draft));} catch {storageAvailable=false;}
  set({draft,storageAvailable});
 };
 return {...load(),playing:true,speed:1,
 ensureCapacity:count=>{const current=get().draft;const next=fitRoster(current,count,LIMITS);if(next!==current)save(next);},
 act: action => {save(changeDraft(get().draft,action));if(action==='reset')set({playing:true,speed:1});},
 selectFloor: floor => {if(floor===null || (Number.isInteger(floor) && floor>=0 && floor<get().draft.floors))save({...get().draft,selectedFloor:floor});},
 togglePlaying:()=>set({playing:!get().playing}), setSpeed:speed=>set({speed:Math.max(.5,Math.min(3,speed))})
 };
});
