import { useEffect, useRef } from 'react';
import { useDraftStore } from '../../store/draftStore';
import { useUIStore } from '../../store/uiStore';
import { LIMITS } from '../../utils/draft';
export function Sidebar({onClose}:{onClose:()=>void}) {
 const close=useRef<HTMLButtonElement>(null),aside=useRef<HTMLElement>(null);
 const {draft,act,storageAvailable}=useDraftStore();
 const {cameraView,setCameraView,showGrid,toggleGrid,showZones,toggleZones}=useUIStore();
 useEffect(()=>{close.current?.focus();},[]);
 return <aside ref={aside} id="design-sidebar" className="design-sidebar" role="dialog" aria-modal="true" aria-label="Design controls" onKeyDown={e=>{
  if(e.key!=='Tab')return;
  const items=aside.current?.querySelectorAll<HTMLElement>('button:not(:disabled),select,input,a[href]');
  if(!items?.length)return;
  const first=items[0],last=items[items.length-1];
  if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
 }}>
  <div className="sidebar-heading"><strong>Design your draft</strong><button ref={close} aria-label="Close design controls" onClick={onClose}>✕ Close</button></div>
  <p className="sidebar-disclaimer">Browser-local design draft. Names come from your signed-in Office teams; walking is simulated. Read-only team access — no team-data writes.</p>
  <div className="sidebar-content">
   <section><span className="eyebrow">01 / SPACE TO GROW</span><h2>Small office, big ideas.</h2><p>One tile = one world unit. Desktops and walking avatars each fit inside a tile. Every storey is 3 tiles high.</p>
    <dl className="draft-counts"><div><dt>Land</dt><dd>{draft.land} × {draft.land}</dd></div><div><dt>Office</dt><dd>{draft.size} × {draft.size}</dd></div><div><dt>Storeys</dt><dd>{draft.floors} / {LIMITS.floors}</dd></div><div><dt>Total floor tiles</dt><dd>{draft.size*draft.size*draft.floors}</dd></div></dl>
    <button data-action="expand-land" disabled={draft.land>=LIMITS.land} onClick={()=>act('expand-land')}>Expand land <span>+4 tiles · max 28 × 28</span></button>
    <button data-action="expand-office" disabled={draft.size>=LIMITS.size || draft.size>=draft.land-4} onClick={()=>act('expand-office')}>Expand office <span>+2 tiles · max 16 × 16</span></button>
    <p className="control-note">A two-tile garden margin is reserved on every side. The office automatically grows to seat your roster, preserving the current storey count where possible; manual expansion remains available.</p>
    <button data-action="add-storey" disabled={draft.floors>=LIMITS.floors} onClick={()=>act('add-storey')}>Add storey <span>+1 level · max 5</span></button>
   </section>
   <section><span className="eyebrow">02 / TAKE A LOOK</span><h3>Camera</h3><div className="camera-options">{(['isometric','perspective','top','section'] as const).map(v=><button key={v} aria-pressed={cameraView===v} onClick={()=>setCameraView(v)}>{v}</button>)}</div>
    <p>Two back walls frame the open front, without pillars. All office keeps the storeys stacked with solid white floors. Individual levels are optional. Mixed demo previews work, leisure and walking together; these are not live states. Activity preview is not live status.</p>
    <button aria-pressed={showGrid} onClick={toggleGrid}>Tile grid <span>{showGrid?'On':'Off'}</span></button>
    <button aria-pressed={showZones} onClick={toggleZones}>Desk zone rugs <span>{showZones?'On':'Off'}</span></button>
   </section>
   <section><span className="eyebrow">03 / YOUR BROWSER ONLY</span><p role="status">{storageAvailable?'Dimensions and visible level save automatically on this browser.':'Browser storage unavailable. This draft lasts for this visit only.'}</p><button data-action="reset" className="reset-draft" onClick={()=>act('reset')}>Reset draft <span>10 × 10 · two storeys</span></button><p>Reset affects this draft only. Walking uses separate bounded random roam areas. Working/leisure/walking are draft previews, not live agent status. Choose Stairs test in the preview selector to send the first team avatar up through the storeys and back down. Pause and speed controls also apply; this is a draft animation, not agent execution.</p></section>
  </div>
 </aside>;
}
export default Sidebar;
