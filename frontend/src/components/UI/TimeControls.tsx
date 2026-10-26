import { useState } from 'react';
import { useDraftStore } from '../../store/draftStore';
export function TimeControls() {
 const {playing,togglePlaying,speed,setSpeed}=useDraftStore();
 const [expanded,setExpanded]=useState(false);
 return <div className="time-controls"><button aria-label={playing?'Pause simulation':'Play simulation'} onClick={togglePlaying}>{playing?'⏸':'▶'}</button><button aria-controls="time-settings" aria-expanded={expanded} onClick={()=>setExpanded(!expanded)}>Walk {expanded?'▾':'▴'}</button>{expanded&&<div id="time-settings" className="time-settings"><label htmlFor="simulation-speed">Walk demo speed · {speed}x</label><input id="simulation-speed" type="range" min={.5} max={3} step={.5} value={speed} onChange={e=>setSpeed(Number(e.target.value))}/><span>Simulation only · no live agent activity</span></div>}</div>;
}
export default TimeControls;
