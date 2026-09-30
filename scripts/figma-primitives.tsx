import React from 'react';
import { sourceArt } from '../src/nutrisole/sourceArt';
export const palette = {green:'#123f2c',black:'#080d16',muted:'#5c626d',border:'#ebe7df',cream:'#faf8f1'};
function N({kind,children,...p}:any){return <n-node data-props={JSON.stringify({kind,...p})}>{children}</n-node>;}
export function Box(p:any){return <N kind="box" {...p}/>;}
export function Txt(p:any){return <N kind="text" {...p}/>;}
export function Text(p:any){return <N kind="inline" {...p}/>;}
export function Photo(p:any){return <N kind="photo" {...p}/>;}
export function Surface(p:any){return <N kind="surface" {...p}/>;}
export function Hit({onPress,...p}:any){return <N kind="hit" {...p}/>;}
export function SourceArt({name,...p}:any){return <N kind="art" name={name} {...sourceArt[name as keyof typeof sourceArt]} {...p}/>;}
export function Divider(p:any){return <N kind="divider" {...p}/>;}
export function Glyph(p:any){return <N kind="glyph" {...p}/>;}
export function Primary({text,label,onPress,...p}:any){return <><Surface {...p} texture="dark-green-texture-tile" fill={palette.green} radius={35} border={false}/><Txt x={p.x} y={p.y+(p.h-48)/2} w={p.w} fs={42} bold align="center" color="#fff" line={48}>{text}</Txt><Hit {...p} label={label||text}/></>;}
export default function ScenePhoto({scene}:any){return <N kind="scene" scene={scene}/>;}
export function CameraFrame(){return <N kind="camera-frame"/>;}
