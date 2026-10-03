import { useState } from 'react';
import { View, Image, ScrollView, StyleSheet } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { Art, T, Tap, Texture, MaskedPhoto, useFrame, s } from './components';
import { assets } from '../../src/nutrisole/assets.native';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import type { CoreProps } from './CoreScreens';
import { cameraFrameHeight, cameraNeedsScroll } from './metrics';
export default function Scan({ back, go, open }: CoreProps) {
  const { width } = useFrame();
  const [preview, setPreview] = useState({ width, height: 580 });
  const [measured, setMeasured] = useState({ toolbar: 86, detection: 84, instruction: 78 });
  const [mode, setMode] = useState<'PHOTO' | 'VIDEO'>('PHOTO'); const [flash, setFlash] = useState(false); const [selected, setSelected] = useState('Apple'); const [recording, setRecording] = useState(false); const [gallery, setGallery] = useState(false);
  const capture = () => mode === 'PHOTO' ? gallery ? open({ title: 'Demo bowl selected', description: 'The photographed bowl is a local fixture. Use the Apple demo to confirm a portion.', choices: [{ label: 'Use Apple demo', action: () => { setGallery(false); setSelected('Apple'); go('analysis-result'); } }] }) : go('analysis-result') : setRecording(v => !v);
  const compact = preview.height < 430; const gap = compact ? 8 : 18; const margin = compact ? 8 : 14;
  const occupied = measured.toolbar + measured.detection + measured.instruction + margin * 2 + gap;
  const frameWidth = preview.width * .68; const frameHeight = cameraFrameHeight(preview.height, frameWidth, occupied);
  const measure = (key: keyof typeof measured, height: number) => setMeasured(old => old[key] === height ? old : { ...old, [key]: height });
  return <View testID="screen-scan" style={{ flex: 1, backgroundColor: '#111' }}>
    <View style={{ flex: 1, minHeight: 0, overflow: 'hidden' }} onLayout={e => { const { width: w, height } = e.nativeEvent.layout; setPreview(old => old.width === w && old.height === height ? old : { width: w, height }); }}>
      <View pointerEvents="none" style={StyleSheet.absoluteFill}><Image source={assets[gallery ? 'chicken-quinoa-bowl' : 'scan-backdrop-clean']} resizeMode="cover" style={{ width: '100%', height: '100%' }} /></View>
      {/* Use the existing clean photo consistently behind the mask, so displaced
          photographed controls cannot leave visible cutout-shaped seams. */}
      {!gallery && <View pointerEvents="none" style={StyleSheet.absoluteFill}><MaskedPhoto scene="scan" width={preview.width} height={preview.height} slice photoAsset="scan-backdrop-clean" /></View>}
      <ScrollView testID="scroll-scan" style={s.flex} scrollEnabled={cameraNeedsScroll(preview.height, occupied)} contentContainerStyle={{ flexGrow: 1 }} contentInsetAdjustmentBehavior="never" automaticallyAdjustContentInsets={false} showsVerticalScrollIndicator={false}>
      <View onLayout={e => measure('toolbar', e.nativeEvent.layout.height)} style={[s.row, { padding: compact ? 10 : 18, justifyContent: 'space-between' }]}><Tap label="Close camera" onPress={back} style={{ padding: 3 }}><Art name="scan-close" size={46} /></Tap><Tap label="Toggle flash" onPress={() => setFlash(v => !v)} style={{ padding: 3 }}>{flash ? <View style={{ width: 46, height: 46, borderRadius: 25, backgroundColor: '#e7cd67c9', alignItems: 'center', justifyContent: 'center' }}><Icons name="Zap" size={24} color="#fff" /></View> : <Art name="scan-flash" size={46} />}</Tap></View>
      <View style={{ flex: 1, minHeight: measured.detection + gap + frameHeight, alignItems: 'center', justifyContent: 'center', gap }}>
        <View onLayout={e => measure('detection', e.nativeEvent.layout.height)} style={[s.row, { alignSelf: 'center', maxWidth: '90%', borderRadius: 24, paddingVertical: compact ? 10 : 15, paddingHorizontal: 18, backgroundColor: '#172017d4', gap: 16 }]}><Art name="scan-confirmation" size={30} /><View style={{ flexShrink: 1, gap: 4 }}><T size={20} bold color="#fff">{selected}</T><T size={18} color="#fff">Confidence 97%</T></View></View>
        <Svg pointerEvents="none" width={frameWidth} height={frameHeight} viewBox={`0 0 ${frameWidth} ${frameHeight}`}><Path d={`M3 35V25Q3 3 25 3H35 M${frameWidth - 35} 3H${frameWidth - 25}Q${frameWidth - 3} 3 ${frameWidth - 3} 25V35 M3 ${frameHeight - 35}V${frameHeight - 25}Q3 ${frameHeight - 3} 25 ${frameHeight - 3}H35 M${frameWidth - 35} ${frameHeight - 3}H${frameWidth - 25}Q${frameWidth - 3} ${frameHeight - 3} ${frameWidth - 3} ${frameHeight - 25}V${frameHeight - 35}`} stroke="#fff" strokeWidth={5} fill="none" strokeLinecap="round" /></Svg>
      </View>
      <View onLayout={e => measure('instruction', e.nativeEvent.layout.height)} style={[s.row, { marginHorizontal: compact ? 20 : 35, marginVertical: margin, paddingHorizontal: 18, paddingVertical: compact ? 10 : 17, backgroundColor: '#352719ca', borderRadius: 26, gap: 18 }]}><Art name="scan-instruction-target" size={24} /><View style={{ flex: 1, gap: 5 }}><T size={17} bold color="#fff">Point at your food</T><T size={14} color="#ddd8cf">Keep it in frame and well lit</T></View></View>
      </ScrollView>
    </View>
    <View testID="footer-scan" style={{ paddingTop: 14, paddingBottom: 18, backgroundColor: '#11110f', gap: 14 }}><Texture asset="scan-controls-surface" /><View style={[s.row, { paddingHorizontal: 20, justifyContent: 'space-between' }]}><Tap label="Choose gallery image" onPress={() => open({ title: 'Choose a demo photo', description: 'Local sample images only. No camera permission, upload, or AI analysis occurs.', choices: [{ label: 'Apple', action: () => { setSelected('Apple'); setGallery(false); } }, { label: 'Grilled Chicken Bowl', action: () => { setSelected('Chicken Bowl'); setGallery(true); } }, { label: 'Blurred apple · Retake', action: () => go('capture-retry') }] })}><Image source={assets['gallery-thumbnail']} resizeMode="cover" style={{ width: 60, height: 56, borderRadius: 13 }} /></Tap><Tap label="Capture food" onPress={capture}>{recording ? <View style={{ width: 80, height: 80, borderRadius: 40, borderWidth: 5, borderColor: '#fff', alignItems: 'center', justifyContent: 'center' }}><View style={{ width: 60, height: 60, borderRadius: 30, backgroundColor: '#ed3445' }} /></View> : <Art name="scan-shutter" size={80} />}</Tap><View style={{ width: 60 }} /></View><View style={[s.row, { justifyContent: 'center', flexWrap: 'wrap', gap: 30 }]}>{(['PHOTO', 'VIDEO'] as const).map(v => <Tap key={v} label={v === 'PHOTO' ? 'Photo mode' : 'Video mode'} onPress={() => { setRecording(false); setMode(v); }} style={{ minHeight: 44, justifyContent: 'center' }}><T size={19} bold={mode === v} color={mode === v ? '#f2c946' : '#ddd'}>{v}</T></Tap>)}</View>{recording && <T size={13} color="#fff" style={s.center}>Demo recording · Tap to stop</T>}</View>
  </View>;
}
