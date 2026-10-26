// Shared by the visible stair meshes and the traversal preview.
export function stairGeometry(size:number,height=3) {
 const half=size/2;
 return {left:half-3,right:half-2,back:-half+1.8,front:-half+5.2,steps:12,height};
}
type Point={x:number;y:number;z:number};
type Segment={a:Point;b:Point;duration:number;phase:string};
export function stairTestRoute(size:number,floors:number,height=3) {
 const g=stairGeometry(size,height),x=(g.left+g.right)/2,depth=(g.front-g.back)/g.steps;
 const route:Segment[]=[];
 let last:Point={x,y:0,z:g.back-.55};
 const move=(b:Point,phase:string,hold=0)=>{
  const duration=hold||Math.hypot(b.x-last.x,b.y-last.y,b.z-last.z)/1.4;
  if(duration>0)route.push({a:last,b,duration,phase});last=b;
 };
 move({...last},'bottom landing',.8);
 const ascent:Segment[]=[];
 for(let floor=0;floor<floors-1;floor++){
  const y=floor*height;
  move({x,y,z:g.back-.15},'approaching stairs');
  for(let step=0;step<g.steps;step++){
   // Lift at the riser, then plant the feet on its tread, never tunnel through it.
   move({x,y:y+(step+1)*height/g.steps,z:g.back+step*depth-.15},'up');
   move({x,y:y+(step+1)*height/g.steps,z:g.back+(step+1)*depth-.15},'up');
  }
  move({x,y:y+height,z:g.front+.55},'upper landing');
  move({...last},'upper landing',.9);
  if(floor<floors-2){
   const side=g.right+.65;
   move({x:side,y:y+height,z:g.front+.55},'landing corridor');
   move({x:side,y:y+height,z:g.back-.55},'landing corridor');
   move({x,y:y+height,z:g.back-.55},'landing corridor');
  }
 }
 ascent.push(...route.slice(1));
 for(const segment of [...ascent].reverse())route.push({a:segment.b,b:segment.a,duration:segment.duration,phase:segment.phase==='up'?'down':segment.phase});
 moveToBottom();
 function moveToBottom(){const bottom={x,y:0,z:g.back-.55};route.push({a:bottom,b:bottom,duration:.8,phase:'bottom landing'});}
 return route;
}
export function stairTestPosition(seconds:number,size:number,floors:number,height=3){
 const route=stairTestRoute(size,floors,height),period=route.reduce((sum,s)=>sum+s.duration,0);
 let time=((seconds%period)+period)%period;
 for(const s of route){
  if(time<=s.duration){const t=time/s.duration;return {x:s.a.x+(s.b.x-s.a.x)*t,y:s.a.y+(s.b.y-s.a.y)*t,z:s.a.z+(s.b.z-s.a.z)*t,heading:Math.atan2(s.b.x-s.a.x,s.b.z-s.a.z),moving:s.a.x!==s.b.x||s.a.y!==s.b.y||s.a.z!==s.b.z,phase:s.phase};}
  time-=s.duration;
 }
 return {x:route[0].a.x,y:0,z:route[0].a.z,heading:0,moving:false,phase:'bottom landing'};
}
