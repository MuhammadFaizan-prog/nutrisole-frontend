import { useId } from 'react';
import Svg, { Defs, Mask, Rect, G, Circle, Path, Image } from 'react-native-svg';
import { assets } from './assets';
import { Box } from './ui';
import { framePaths, sceneDimensions } from './sceneGeometry';
export default function ScenePhoto({ scene }: { scene: 'scan' | 'onboarding' }) {
  const id = `scene-${useId().replaceAll(':', '')}`;
  const d = sceneDimensions[scene];
  return <Box {...d} passive><Svg width={d.w} height={d.h} viewBox={`${d.x} ${d.y} ${d.w} ${d.h}`}>
    <Defs><Mask id={id} maskUnits="userSpaceOnUse" x={d.x} y={d.y} width={d.w} height={d.h}>
      <Rect x={d.x} y={d.y} width={d.w} height={d.h} fill="#fff" />
      {scene === 'scan' ? <G fill="#000">
        <Rect x={116} y={73} width={74} height={37} />
        <Rect x={304} y={53} width={255} height={77} rx={39} />
        <Rect x={620} y={71} width={160} height={40} />
        <Circle cx={127.5} cy={217.5} r={49} />
        <Circle cx={739} cy={217} r={49} />
        <Rect x={264} y={412} width={484} height={156} rx={49} />
        <Path d="M480 559H520L500 585Z" />
        <Rect x={142} y={1226} width={583} height={155} rx={54} />
        {framePaths.map(path => <Path key={path} d={path} fill="none" stroke="#000" strokeWidth={16} strokeLinecap="round" />)}
      </G> : <Rect x={62} y={1089} width={737} height={505} rx={52} fill="#000" />}
    </Mask></Defs>
    <Image x={d.x} y={d.y} width={d.w} height={d.h} href={assets[d.asset]} mask={`url(#${id})`} />
  </Svg></Box>;
}
export function CameraFrame() {
  return <Box x={41} y={37} w={781} h={1371} passive><Svg width={781} height={1371} viewBox="41 37 781 1371">
    {framePaths.map(path => <Path key={path} d={path} fill="none" stroke="#fff" strokeWidth={11} strokeLinecap="round" />)}
  </Svg></Box>;
}
