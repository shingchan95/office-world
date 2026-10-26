import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Vector3 } from 'three';
import type { Group } from 'three';
import { useDraftStore } from '../../store/draftStore';
import { floorElevation, tilePosition, floorOffset, FLOOR_HEIGHT } from '../../utils/coordinates';
import type { TeamAvatar } from '../../utils/teamRoster';
import { officeSlots, walkOffset, previewActivity, type AgentActivity, type PreviewActivity } from '../../utils/officeLayout';
import { stairTestPosition } from '../../utils/stairs';
import { AVATAR_RADIUS } from '../../utils/draft';
function Walker({name,teams,color,floor,size,offset,desk,activity}:{name:string;teams:string[];color:string;floor:number;size:number;offset:number;desk:{x:number;z:number};activity:AgentActivity}) {
 const root=useRef<Group>(null), body=useRef<Group>(null), left=useRef<Group>(null),right=useRef<Group>(null);
 const label=useRef<HTMLDivElement|null>(null), elapsed=useRef(offset);
 const {gl,camera,size:viewport}=useThree();
 const projected=useRef(new Vector3());
 const roam=useRef({x:0,z:0,tx:.3,tz:.15});
 // A lightweight DOM overlay avoids a separate React root per avatar.
 useEffect(()=>{
  const el=document.createElement('div');el.className='avatar-label';el.dataset.avatar=name;el.dataset.activity=activity;el.textContent=name;
  el.title=teams.join(' · '); // Identity only: no badge or fabricated work-state label.
  gl.domElement.parentElement?.appendChild(el);label.current=el;
  return()=>{el.remove();label.current=null;};
 },[gl,name,teams,activity]);
 useFrame((_,delta)=>{
  const {playing,speed}=useDraftStore.getState();
  if(playing)elapsed.current+=Math.min(delta,.1)*speed;
  const r=roam.current;
  if(playing&&activity==='walking'){
   const dx=r.tx-r.x,dz=r.tz-r.z,distance=Math.hypot(dx,dz),step=Math.min(delta,.1)*speed*.55;
   if(distance<=step){r.x=r.tx;r.z=r.tz;r.tx=(Math.random()-.5)*.6;r.tz=(Math.random()-.5)*.4;}
   else {r.x+=dx/distance*step;r.z+=dz/distance*step;}
  }
  const p=activity==='walking'?{x:desk.x+r.x,z:desk.z+1.8+r.z,heading:Math.atan2(r.tx-r.x,r.tz-r.z)}:{x:desk.x,z:desk.z+(activity==='working'?.65:1.55),heading:activity==='leisure'?0:Math.PI};
  const [x,z]=tilePosition(p.x,p.z,size);
  const stair=activity==='stairs'?stairTestPosition(elapsed.current,size,useDraftStore.getState().draft.floors,FLOOR_HEIGHT):null;
  const stepping=playing&&(activity==='walking'||!!stair?.moving);
  if(root.current && stair)root.current.position.set(stair.x,stair.y+.035,stair.z);
  else if(root.current)root.current.position.set(x+floorOffset(floor,size,useDraftStore.getState().draft.floors,useDraftStore.getState().draft.selectedFloor===null),floorElevation(floor)+(activity==='walking'?.035:.25),z);
  if(body.current) {body.current.rotation.y=(stair?.heading??p.heading)+(activity==='leisure'?Math.sin(elapsed.current*.7)*.15:0);body.current.position.y=stepping?Math.abs(Math.sin(elapsed.current*8))*.035:activity==='leisure'?Math.sin(elapsed.current*1.2)*.008:0;}
  if(left.current)left.current.rotation.x=stepping?Math.sin(elapsed.current*8)*.35:0;
  if(right.current)right.current.rotation.x=stepping?-Math.sin(elapsed.current*8)*.35:0;
  // Browser regression samples actual rendered group coordinates, not a second simulation.
  if(label.current && root.current) {
   label.current.dataset.phase=stair?.phase??activity;label.current.dataset.floor=String(stair?Math.round(stair.y/FLOOR_HEIGHT):floor);label.current.dataset.worldY=root.current.position.y.toFixed(4);
   label.current.dataset.worldX=root.current.position.x.toFixed(4);label.current.dataset.worldZ=root.current.position.z.toFixed(4);
   const p=projected.current.copy(root.current.position);p.y+=1.22;p.project(camera);
   label.current.style.transform=`translate(${(p.x*.5+.5)*viewport.width}px,${(-p.y*.5+.5)*viewport.height}px) translate(-50%,-50%)`;
   label.current.style.display=p.z>1||p.z< -1?'none':'';
  }
 });
 return <group ref={root} name={`walking-${name}`}>
  <group ref={body}>
   <mesh position={[0,.45,0]} castShadow><capsuleGeometry args={[AVATAR_RADIUS*.73,.22,4,10]}/><meshStandardMaterial color={color} roughness={.6}/></mesh>
   <mesh position={[0,.88,.01]} castShadow><sphereGeometry args={[.29,16,12]}/><meshStandardMaterial color="#fff8e8" roughness={.7}/></mesh>
   {[-.10,.10].map(x=><mesh key={x} position={[x,.91,.276]}><sphereGeometry args={[.035,8,6]}/><meshBasicMaterial color="#263e47"/></mesh>)}
   <mesh position={[0,.81,.288]}><sphereGeometry args={[.035,8,6]}/><meshBasicMaterial color="#c88177"/></mesh>
   {[-1,1].map(side=><mesh key={side} position={[side*.265,.47,0]} rotation={[0,0,side*.16]}><capsuleGeometry args={[.055,.19,3,8]}/><meshStandardMaterial color={color}/></mesh>)}
   <group ref={left} position={[-.13,.19,0]}><mesh position={[0,-.08,.04]} castShadow><boxGeometry args={[.16,.17,.28]}/><meshStandardMaterial color="#344f60"/></mesh></group>
   <group ref={right} position={[.13,.19,0]}><mesh position={[0,-.08,.04]} castShadow><boxGeometry args={[.16,.17,.28]}/><meshStandardMaterial color="#344f60"/></mesh></group>
  </group>
 </group>;
}
export function Agents({members,activity}:{members:TeamAvatar[];activity:PreviewActivity}) {
 const {size,selectedFloor,floors}=useDraftStore(s=>s.draft);

 // Show every unique team member on the inspected level; never hide half the roster.
 const slots=officeSlots(size,members.length);
 const names=members.map((agent,i)=>({agent,slot:slots[i]})).filter(item=>item.slot.floor<floors && (selectedFloor===null||item.slot.floor===selectedFloor));
 return <group name="simulated-walking-agents">{names.map(({agent,slot},i)=><Walker desk={slot} activity={previewActivity(slot.index,activity)} key={`${agent.id}-${size}-${activity}`} name={agent.name} teams={agent.teams} color={agent.color} floor={slot.floor} size={size} offset={walkOffset(i,names.length,size)}/>)}</group>;
}
export default Agents;
