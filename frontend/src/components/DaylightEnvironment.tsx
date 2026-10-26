import { useMemo, useEffect } from 'react';
import { Environment } from '@react-three/drei';
import * as THREE from 'three';
// Locally generated sky/ground + softbox highlights. Uploaded once; no HDR fetches
// or per-frame cube captures. Shared scene.environment is PMREM-filtered by Three.
export function DaylightEnvironment() {
 const texture=useMemo(()=>{
  const width=256,height=128,data=new Uint8Array(width*height*4);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++) {
   const t=y/height;
   const color=new THREE.Color(t<.5 ? '#b7ddf5' : '#8ca67c');
   const cloud=(y>22 && y<44 && ((x>18 && x<65)||(x>130 && x<180))) || (x>210 && x<224 && y<62);
   if(cloud)color.set('#ffffff');
   const i=(y*width+x)*4; data[i]=color.r*255;data[i+1]=color.g*255;data[i+2]=color.b*255;data[i+3]=255;
  }
  const texture=new THREE.DataTexture(data,width,height,THREE.RGBAFormat);
  texture.mapping=THREE.EquirectangularReflectionMapping;texture.needsUpdate=true;
  return texture;
 },[]);
 useEffect(()=>()=>texture.dispose(),[texture]);
 return <Environment map={texture}/>;
}
