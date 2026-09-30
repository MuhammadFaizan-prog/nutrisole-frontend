import { useState } from 'react';
import { Box, Txt, Photo, Surface, Glyph, SourceArt, Hit } from './ui';
import type { Sheet } from './types';
import ScenePhoto, { CameraFrame } from './ScenePhoto';

export default function Scan({ back, capture, open }: { back: () => void; capture: () => void; open: (sheet: Sheet) => void }) {
  const [mode, setMode] = useState<'PHOTO' | 'VIDEO'>('PHOTO');
  const [flash, setFlash] = useState(false);
  const [selected, setSelected] = useState('Apple');
  const [recording, setRecording] = useState(false);
  const [galleryPhoto, setGalleryPhoto] = useState(false);
  return <>
    <Photo x={41} y={37} w={781} h={1371} asset="scan-backdrop-clean" />
    <Photo x={116} y={73} w={74} h={37} asset="scan-time-background" />
    <Photo x={620} y={71} w={160} h={40} asset="scan-indicators-background" />
    {!galleryPhoto && <ScenePhoto scene="scan" />}
    {galleryPhoto && <Photo x={41} y={37} w={781} h={1371} asset="chicken-quinoa-bowl" mode="cover" />}
    <SourceArt name="scan-close" radius={50} />
    <Hit x={73} y={163} w={109} h={109} label="Close camera" onPress={back} />
    {flash ? <><Surface x={691} y={169} w={96} h={96} radius={53} fill="#e7cd67c9" border={false} /><Glyph x={718} y={194} name="Zap" size={45} color="#fff" weight={1.5} /></> : <SourceArt name="scan-flash" radius={50} />}
    <Hit x={684} y={162} w={110} h={110} label="Toggle flash" onPress={() => setFlash(v => !v)} />
    <Surface x={264} y={412} w={484} h={156} radius={49} fill="#172017d4" texture="scan-detection-surface" border={false} />
    <Box x={490} y={558} w={20} h={20} style={{ backgroundColor: '#33312a', transform: [{ rotate: '45deg' }] }} />
    <SourceArt name="scan-confirmation" radius={32} />
    <Txt x={395} y={447} w={330} fs={40} bold color="#fff">{selected}</Txt>
    <Txt x={395} y={497} w={340} fs={38} color="#fff">Confidence 97%</Txt>
    <CameraFrame />
    <Surface x={142} y={1226} w={583} h={155} radius={54} fill="#352719ca" texture="scan-instruction-surface" border={false} />
    <SourceArt name="scan-instruction-target" />
    <Txt x={328} y={1269} w={365} fs={34} bold color="#fff">Point at your food</Txt>
    <Txt x={328} y={1316} w={380} fs={30} color="#ddd8cf">Keep it in frame and well lit</Txt>
    <Surface x={41} y={1408} w={781} h={368} radius={0} fill="#11110fee" texture="scan-controls-surface" border={false} />
    <Photo x={80} y={1461} w={123} h={113} radius={28} asset="gallery-thumbnail" />
    <Hit x={74} y={1455} w={135} h={127} label="Choose gallery image" onPress={() => open({ title: 'Choose a demo photo', description: 'Local sample images only. No camera permission, upload, or AI analysis occurs.', choices: [{ label: 'Apple', action: () => { setSelected('Apple'); setGalleryPhoto(false); } }, { label: 'Grilled Chicken Bowl', action: () => { setSelected('Chicken Bowl'); setGalleryPhoto(true); } }] })} />
    {recording ? <><Surface x={348} y={1443} w={164} h={164} radius={92} fill="#fff" border={false} /><Surface x={357} y={1452} w={146} h={146} radius={82} fill="#111" border={false} /><Surface x={364} y={1459} w={132} h={132} radius={80} fill="#ed3445" border={false} /></> : <SourceArt name="scan-shutter" radius={84} />}
    <Hit x={348} y={1443} w={164} h={164} label="Capture food" onPress={() => mode === 'PHOTO' ? (galleryPhoto ? open({ title: 'Demo bowl selected', description: 'The photographed bowl is a local fixture. Use the Apple demo to confirm a portion.', choices: [{ label: 'Use Apple demo', action: () => { setGalleryPhoto(false); setSelected('Apple'); capture(); } }] }) : capture()) : setRecording(v => !v)} />
    <Txt x={332} y={1644} w={202} fs={40} bold={mode === 'PHOTO'} align="center" color={mode === 'PHOTO' ? '#f2c946' : '#ddd'}>PHOTO</Txt>
    <Txt x={535} y={1644} w={169} fs={39} bold={mode === 'VIDEO'} align="center" color={mode === 'VIDEO' ? '#f2c946' : '#ddd'}>VIDEO</Txt>
    <Hit x={330} y={1624} w={206} h={85} label="Photo mode" onPress={() => { setRecording(false); setMode('PHOTO'); }} />
    <Hit x={535} y={1624} w={174} h={85} label="Video mode" onPress={() => setMode('VIDEO')} />
    {recording && <Txt x={229} y={1710} w={400} fs={26} color="#fff" align="center">Demo recording · Tap to stop</Txt>}
  </>;
}
