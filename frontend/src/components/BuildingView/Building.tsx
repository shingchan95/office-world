import { stairGeometry } from '../../utils/stairs';
import { useDraftStore } from '../../store/draftStore';
import { floorElevation, FLOOR_HEIGHT, floorOffset } from '../../utils/coordinates';
function Block({position,size,name='structure',opacity=1}:{position:[number,number,number];size:[number,number,number];name?:string;opacity?:number}) {
 return <mesh name={name} position={position} receiveShadow castShadow><boxGeometry args={size}/><meshStandardMaterial color="#fbfcfa" roughness={.55} transparent={opacity<1} opacity={opacity} depthWrite={opacity===1}/></mesh>;
}
export function Building() {
 const {size,floors,selectedFloor}=useDraftStore(s=>s.draft);
 const count=selectedFloor===null?floors:selectedFloor+1,half=size/2;
 // Reserve a stairwell strip, including openings through every upper slab.
 const {left,right,back,front,steps}=stairGeometry(size,FLOOR_HEIGHT);
 return <group name="open-office-platforms">
  {Array.from({length:count},(_,floor)=>{
   const y=floorElevation(floor);
   return <group key={floor} name={`storey-${floor}`} position={[floorOffset(floor,size,floors,selectedFloor===null),0,0]}>
    {floor===0?<Block position={[0,y-.11,0]} size={[size,.22,size]}/>:<>
     <Block opacity={1} position={[(-half+left)/2,y-.11,0]} size={[left+half,.22,size]}/>
     <Block opacity={1} position={[(right+half)/2,y-.11,0]} size={[half-right,.22,size]}/>
     <Block opacity={1} position={[(left+right)/2,y-.11,(-half+back)/2]} size={[right-left,.22,back+half]}/>
     <Block opacity={1} position={[(left+right)/2,y-.11,(front+half)/2]} size={[right-left,.22,half-front]}/>
    </>}
    <Block name="back-wall" position={[0,y+.8,-half]} size={[size,1.6,.1]}/>
    <Block name="back-wall" position={[-half,y+.8,0]} size={[.1,1.6,size]}/>
    {floor<floors-1 && <group name="stairs-to-next-storey">{Array.from({length:steps},(_,i)=>{
     const height=(i+1)*FLOOR_HEIGHT/steps;
     return <Block key={i} name="stair-step" position={[(left+right)/2,y+height/2,back+(i+.5)*(front-back)/steps]} size={[.85,height,(front-back)/steps]}/>;
    })}</group>}
   </group>;
  })}
 </group>;
}
export default Building;
