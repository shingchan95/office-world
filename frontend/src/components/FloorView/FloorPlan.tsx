import { useDraftStore } from '../../store/draftStore';
import { useUIStore } from '../../store/uiStore';
import { floorElevation, tilePosition, floorOffset } from '../../utils/coordinates';
import { DESK_SIZE } from '../../utils/draft';
import { type PreviewActivity, officeSlots, previewActivity } from '../../utils/officeLayout';
function Desk({x,z,size,index}:{x:number;z:number;size:number;index:number}) {
 const [wx,wz]=tilePosition(x,z,size);
 return <group position={[wx,0,wz]} name="one-tile-workstation">
  <mesh position={[0,.66,0]} castShadow receiveShadow><boxGeometry args={DESK_SIZE}/><meshStandardMaterial color="#e5c9a3" roughness={.65}/></mesh>
  {[-.34,.34].flatMap(lx=>[-.23,.23].map(lz=><mesh key={`${lx}-${lz}`} position={[lx,.31,lz]}><boxGeometry args={[.045,.62,.045]}/><meshStandardMaterial color="#f8faf9"/></mesh>))}
  <mesh position={[0,.92,-.18]}><boxGeometry args={[.44,.3,.04]}/><meshStandardMaterial color="#274554"/></mesh>
  <mesh position={[0,.92,-.155]}><planeGeometry args={[.37,.23]}/><meshBasicMaterial color={index%2?'#acdbe4':'#b7e3cf'}/></mesh>
  <mesh position={[0,.74,-.18]}><boxGeometry args={[.05,.14,.05]}/><meshStandardMaterial color="#526e78"/></mesh>
  <mesh position={[0,.72,.12]}><boxGeometry args={[.32,.025,.12]}/><meshStandardMaterial color="#f7f9f8"/></mesh>
  <mesh position={[0,.38,.65]} castShadow><boxGeometry args={[.47,.12,.42]}/><meshStandardMaterial color={index%2?'#a7c3d5':'#9fc9b4'}/></mesh>
  <mesh position={[0,.6,.81]}><boxGeometry args={[.47,.4,.08]}/><meshStandardMaterial color={index%2?'#a7c3d5':'#9fc9b4'}/></mesh>
  <mesh position={[0,.18,.65]}><cylinderGeometry args={[.035,.035,.36,8]}/><meshStandardMaterial color="#6f7d83"/></mesh>
 </group>;
}
export function FloorPlan({count,activity}:{count:number;activity:PreviewActivity}) {
 const {size,floors,selectedFloor}=useDraftStore(s=>s.draft);
 const grid=useUIStore(s=>s.showGrid), zones=useUIStore(s=>s.showZones);
 const visible=selectedFloor===null?floors:selectedFloor+1;
 return <group name="floor-interiors">{Array.from({length:visible},(_,floor)=><group key={floor} position={[floorOffset(floor,size,floors,selectedFloor===null),floorElevation(floor)+.015,0]}>
  {floor===0 && <mesh rotation={[-Math.PI/2,0,0]} receiveShadow><planeGeometry args={[size-.12,size-.12]}/><meshStandardMaterial color="#eef0e9" roughness={.85}/></mesh>}
  {grid && <gridHelper args={[size,size,'#b2c5c7','#d2dcd9']} position={[0,.012,0]}/>}
  {officeSlots(size,count).filter(slot=>slot.floor===floor).map((item,i)=><group key={item.index}>
   {zones && <mesh position={[...tilePosition(item.x,item.z,size).slice(0,1),.018,tilePosition(item.x,item.z,size)[1]] as [number,number,number]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[1.5,1.9]}/><meshStandardMaterial color={i%2?'#dbe8ef':'#dceade'} transparent opacity={.6} depthWrite={false}/></mesh>}
   <Desk {...item} size={size} index={i}/>
   {previewActivity(item.index,activity)!=='walking' && <mesh name="leisure-seat" position={[tilePosition(item.x,item.z,size)[0],.2,tilePosition(item.x,item.z,size)[1]+1.55]}><boxGeometry args={[.65,.4,.5]}/><meshStandardMaterial color="#adcbb6"/></mesh>}
  </group>)}
 </group>)}</group>;
}
export default FloorPlan;
