import { useCallback, useEffect, useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';
import { useUIStore } from '../store/uiStore';
import { useDraftStore } from '../store/draftStore';
import { type TeamAvatar, teamRoster } from '../utils/teamRoster';
import { officeSlots, type PreviewActivity } from '../utils/officeLayout';
import { floorElevation } from '../utils/coordinates';
import { Building } from './BuildingView/Building';
import { FloorPlan } from './FloorView/FloorPlan';
import { Agents } from './Agents/Agents';
import { DaylightEnvironment } from './DaylightEnvironment';
import { Sidebar } from './UI/Sidebar';
import { TimeControls } from './UI/TimeControls';
import { FloorIndicator } from './UI/FloorIndicator';
function CameraRig() {
 const {camera,size:viewport}=useThree();
 const {size,floors,selectedFloor}=useDraftStore(s=>s.draft);
 const view=useUIStore(s=>s.cameraView);
 const controls=useRef<OrbitControlsImpl>(null);
 useEffect(()=>{
  const height=floorElevation(selectedFloor===null?floors:selectedFloor+1);
  const target=new THREE.Vector3(0,height*.43,0);
  const distance=Math.max(size+3,height*1.4)/Math.tan(Math.PI/8)/Math.min(1,viewport.width/viewport.height)*.7;
  const direction=view==='top'?new THREE.Vector3(0,1,.001):view==='section'?new THREE.Vector3(1,.55,.05):new THREE.Vector3(1,view==='perspective'?.6:.65,1);
  camera.position.copy(target).add(direction.normalize().multiplyScalar(distance));
  camera.lookAt(target);camera.updateProjectionMatrix();
  if(controls.current){controls.current.target.copy(target);controls.current.update();}
 },[camera,size,floors,selectedFloor,view,viewport.width,viewport.height]);
 return <OrbitControls ref={controls} enableDamping minDistance={5} maxDistance={300} maxPolarAngle={Math.PI/2-.02}/>;
}
function Scene({members,activity}:{members:TeamAvatar[];activity:PreviewActivity}) {
 const {land,size,floors,selectedFloor}=useDraftStore(s=>s.draft);
 return <>
  <color attach="background" args={['#c3deed']}/>
  <fog attach="fog" args={['#c3deed',350,900]}/>
  <DaylightEnvironment/>
  <hemisphereLight args={['#e4f4ff','#a4b893',2]}/>
  <ambientLight intensity={.5}/>
  <directionalLight position={[15,24,12]} intensity={2.5} castShadow shadow-mapSize={[1024,1024]} shadow-camera-left={-20} shadow-camera-right={20} shadow-camera-top={20} shadow-camera-bottom={-20} shadow-normalBias={.04}/>
  <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.24,0]} receiveShadow><planeGeometry args={[land*3+floors*(size+2),land*3]}/><meshStandardMaterial color="#8cae78" roughness={1}/></mesh>
  <mesh position={[0,-.19,0]} receiveShadow><boxGeometry args={[land,.12,land]}/><meshStandardMaterial color="#9fbe86" roughness={1}/></mesh>
  <mesh position={[0,-.115,0]} receiveShadow><boxGeometry args={[size+1,.08,size+1]}/><meshStandardMaterial color="#cbd4c5" roughness={1}/></mesh>
  <Building/><FloorPlan count={members.length} activity={activity}/><Agents members={members} activity={activity}/><CameraRig/>
 </>;
}
export function OfficeWorld() {
 const sidebarOpen=useUIStore(s=>s.sidebarOpen),toggleSidebar=useUIStore(s=>s.toggleSidebar);
 const draft=useDraftStore(s=>s.draft);
 const [activity,setActivity]=useState<PreviewActivity>('mixed');
 const [members,setMembers]=useState<TeamAvatar[]>([]);
 const [rosterStatus,setRosterStatus]=useState('Loading team members…');
 useEffect(()=>{useDraftStore.getState().ensureCapacity(members.length);},[members.length,draft.size,draft.land,draft.floors]);
 useEffect(()=>{
  const controller=new AbortController();
  const refresh=async()=>{try {
   const response=await fetch('/api/teams',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(!response.ok) {setMembers([]);setRosterStatus(response.status===401?'Sign in via Back to teams to see your agents.':'Team members unavailable — open teams to check your account.');return;}
   const names=teamRoster(await response.json());useDraftStore.getState().ensureCapacity(names.length);setMembers(names);
   const current=useDraftStore.getState().draft;
   if(names.length && current.selectedFloor!==null && !officeSlots(current.size,names.length).some(slot=>slot.floor===current.selectedFloor))useDraftStore.getState().selectFloor(0);setRosterStatus(names.length?`${names.length} agents · ${new Set(names.flatMap(agent=>agent.teams)).size} teams · walking simulated`:'No members in planned or active teams yet.');
  }catch {if(!controller.signal.aborted){setMembers([]);setRosterStatus('Unable to load team members.');}}};
  void refresh();const timer=setInterval(()=>void refresh(),30000);
  const focus=()=>void refresh();window.addEventListener('focus',focus);
  return()=>{controller.abort();clearInterval(timer);window.removeEventListener('focus',focus);};
 },[]);
 const [isMobile,setIsMobile]=useState(()=>window.matchMedia('(max-width:767px)').matches);
 const menuRef=useRef<HTMLButtonElement>(null);
 const close=useCallback(()=>{toggleSidebar();menuRef.current?.focus();},[toggleSidebar]);
 useEffect(()=>{const query=window.matchMedia('(max-width:767px)');const update=()=>setIsMobile(query.matches);query.addEventListener('change',update);return()=>query.removeEventListener('change',update);},[]);
 useEffect(()=>{if(!sidebarOpen)return;const key=(event:KeyboardEvent)=>{if(event.key==='Escape')close();};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key);},[sidebarOpen,close]);
 return <div className="office-world" data-draft-size={draft.size} data-draft-floors={draft.floors} data-draft-land={draft.land}>
  <header className="draft-header"><a className="back-to-teams" href="/">← Back to teams</a><span className="draft-label">Office World · Simulated design draft</span><button ref={menuRef} className="menu-button" aria-controls="design-sidebar" aria-expanded={sidebarOpen} onClick={toggleSidebar}>☰ Design</button></header>
  <main className="scene-space" aria-label="Interactive simulated office scene">
   <div className="scene-caption"><strong>OPEN OFFICE</strong><span>{draft.size} × {draft.size} tiles · {draft.floors} storeys</span><span>{draft.selectedFloor===null?'All office · stacked cutaway':'Open level '+(draft.selectedFloor+1)+' · walk demo'}</span><span role="status">{rosterStatus}</span>{activity==='stairs'&&members.length>0&&<span>Stairs test: {members[0].name} · up, landing, down · simulation only</span>}<span>{officeSlots(draft.size,members.length).filter(slot=>slot.floor<draft.floors&&(draft.selectedFloor===null||slot.floor===draft.selectedFloor)).length} avatars / desks placed · work state not connected</span>{officeSlots(draft.size,members.length).some(slot=>slot.floor>=draft.floors)&&<span>Add a storey or expand the office to seat all members.</span>}</div>
   <Canvas camera={{position:[18,15,18],fov:45,near:.1,far:300}} shadows={!isMobile} dpr={isMobile?1:[1,1.5]} gl={{antialias:!isMobile,toneMapping:THREE.ACESFilmicToneMapping,toneMappingExposure:1}}><Scene members={members} activity={activity}/></Canvas>
   {!members.length && <div className="roster-notice" role="status"><strong>{rosterStatus}</strong><p>Your desktop Office session is separate from your phone. Sign in in the new tab, then return here.</p><a href="/" target="_blank" rel="noopener">Sign in to Office →</a><button className="retry-roster" onClick={()=>window.location.reload()}>Check sign-in again</button></div>}
   <span className="scene-hint">Drag to orbit · pinch / scroll to zoom</span>
  </main>
  <footer className="scene-toolbar"><label>Preview <select aria-label="Activity preview" value={activity} onChange={e=>{const mode=e.target.value as PreviewActivity;setActivity(mode);if(mode==='stairs'){useDraftStore.getState().selectFloor(null);useUIStore.getState().setCameraView('section');}}}><option value="mixed">Mixed demo</option><option value="stairs">Stairs test ↕</option><option value="working">At desks</option><option value="leisure">Leisure</option><option value="walking">Walking</option></select></label><TimeControls/><FloorIndicator/></footer>
  {sidebarOpen && <div className="sidebar-layer"><button className="sidebar-backdrop" aria-label="Dismiss design controls" onClick={close}/><Sidebar onClose={close}/></div>}
 </div>;
}
export default OfficeWorld;
