import { useId } from 'react';
import { assets } from './assets';
import { Box } from './ui';
import { framePaths, sceneDimensions } from './sceneGeometry';

// The mask removes the photographed UI before any pixels are displayed.
// All text, controls, indicators, and target strokes are separate live elements.
export default function ScenePhoto({ scene }: { scene: 'scan' | 'onboarding' }) {
  const id = `scene-${useId().replaceAll(':', '')}`;
  const d = sceneDimensions[scene];
  return <Box {...d} passive><svg width={d.w} height={d.h} viewBox={`${d.x} ${d.y} ${d.w} ${d.h}`} aria-hidden="true">
    <defs><mask id={id} maskUnits="userSpaceOnUse" x={d.x} y={d.y} width={d.w} height={d.h}>
      <rect x={d.x} y={d.y} width={d.w} height={d.h} fill="#fff" />
      {scene === 'scan' ? <g fill="#000">
        <rect x="116" y="73" width="74" height="37" />
        <rect x="304" y="53" width="255" height="77" rx="39" />
        <rect x="620" y="71" width="160" height="40" />
        <circle cx="127.5" cy="217.5" r="49" />
        <circle cx="739" cy="217" r="49" />
        <rect x="264" y="412" width="484" height="156" rx="49" />
        <path d="M480 559H520L500 585Z" />
        <rect x="142" y="1226" width="583" height="155" rx="54" />
        {framePaths.map(path => <path key={path} d={path} fill="none" stroke="#000" strokeWidth="16" strokeLinecap="round" />)}
      </g> : <rect x="62" y="1089" width="737" height="505" rx="52" fill="#000" />}
    </mask></defs>
    <image x={d.x} y={d.y} width={d.w} height={d.h} href={assets[d.asset].uri} mask={`url(#${id})`} />
  </svg></Box>;
}
export function CameraFrame() {
  return <Box x={41} y={37} w={781} h={1371} passive><svg width="781" height="1371" viewBox="41 37 781 1371" aria-hidden="true">
    {framePaths.map(path => <path key={path} d={path} fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" />)}
  </svg></Box>;
}
