import { createContext, useContext, type PropsWithChildren } from 'react';
import { View, Text, Image, Pressable } from './primitives';
import Icon, { type IconName } from './Icon';
import { assets } from './assets';
import type { Route } from './types';
import { sourceArt, type SourceArtName } from './sourceArt';

export const palette = { green: '#123f2c', black: '#080d16', muted: '#5c626d', border: '#ebe7df', cream: '#faf8f1' };
export const crops: Record<Route, [number, number, number, number]> = {
  onboarding: [38, 38, 786, 1748], home: [42, 38, 777, 1737], scan: [41, 37, 781, 1739],
  'log-meal': [55, 120, 750, 1604], 'weekly-plan': [57, 149, 749, 1537], profile: [50, 166, 760, 1564],
  health: [55, 120, 750, 1604], history: [55, 120, 750, 1604],
};
const Origin = createContext<[number, number]>([0, 0]);
export type Pos = { x: number; y: number; w?: number; h?: number };
export type Style = Record<string, any>;
export function Canvas({ route, width, height, children }: PropsWithChildren<{ route: Route; width: number; height: number }>) {
  const [x, y, w, h] = crops[route];
  const scale = Math.min(width / w, height / h);
  return <View testID={`screen-${route}`} style={{ width, height, backgroundColor: route === 'scan' ? '#111' : palette.cream, overflow: 'hidden' }}>
    <View testID="reference-canvas" style={{ position: 'absolute', left: (width - w * scale) / 2, top: 0, width: w, height: h, transform: [{ scale }], transformOrigin: 'top left' }}>
      <Origin.Provider value={[x, y]}>{children}</Origin.Provider>
    </View>
  </View>;
}
function useRect(p: Pos): Style { const [ox, oy] = useContext(Origin); return { position: 'absolute', left: p.x - ox, top: p.y - oy, width: p.w, height: p.h }; }
export function Box({ children, style, passive = false, ...pos }: PropsWithChildren<Pos & { style?: Style; passive?: boolean }>) { return <View pointerEvents={passive ? 'none' : 'box-none'} style={[useRect(pos), style]}>{children}</View>; }
export function Txt({ children, fs = 36, color = palette.black, bold = false, serif = false, align = 'left', line, maxLines, style, ...pos }: PropsWithChildren<Pos & { fs?: number; color?: string; bold?: boolean; serif?: boolean; align?: 'left' | 'center' | 'right'; line?: number; maxLines?: number; style?: Style }>) {
  return <Text pointerEvents="none" numberOfLines={maxLines} style={[useRect(pos), { fontFamily: serif ? (bold ? 'NutriSerifBold' : 'NutriSerif') : bold ? 'NutriSansBold' : 'NutriSans', fontSize: fs, lineHeight: line ?? fs * 1.18, color, textAlign: align, letterSpacing: -0.7, includeFontPadding: false }, serif && bold && { transform: [{ scaleX: 0.82 }], transformOrigin: 'top left' }, style]}>{children}</Text>;
}
export function Photo({ asset, radius = 0, opacity = 1, mode = 'stretch', ...pos }: Pos & { asset: string; radius?: number; opacity?: number; mode?: 'cover' | 'contain' | 'stretch' }) {
  if (asset === 'scan-photo-region' || asset === 'onboarding-photo-region') throw new Error('Photographic regions with source overlays must use the ScenePhoto exclusion mask.');
  return <Box {...pos} passive><Image source={assets[asset]} resizeMode={mode} style={{ width: '100%', height: '100%', borderRadius: radius, opacity }} /></Box>;
}
export function Surface({ children, radius = 36, fill = '#fffdf9', texture, border = true, ...pos }: PropsWithChildren<Pos & { radius?: number; fill?: string; texture?: string; border?: boolean }>) {
  return <Box {...pos} style={{ backgroundColor: fill, borderRadius: radius, overflow: 'hidden', borderWidth: border ? 1.8 : 0, borderColor: palette.border }}>
    {texture && <View pointerEvents="none" style={{ position: 'absolute', width: '100%', height: '100%' }}><Image source={assets[texture]} resizeMode="stretch" style={{ width: '100%', height: '100%' }} /></View>}{children}
  </Box>;
}
export function Hit({ children, label, onPress, disabled = false, style, ...pos }: PropsWithChildren<Pos & { label: string; onPress: () => void; disabled?: boolean; style?: Style }>) {
  const rect = useRect(pos);
  return <Pressable role="button" aria-label={label} testID={label.toLowerCase().replace(/[^a-z0-9]+/g, '-')} disabled={disabled} onPress={onPress} style={({ pressed }: { pressed: boolean }) => [rect, { opacity: disabled ? 0.4 : pressed ? 0.8 : 1, minHeight: 24 }, style]}>{children}</Pressable>;
}
export function Glyph({ name, size = 45, color = palette.black, weight = 1.8, fill, ...pos }: Pos & { name: IconName; size?: number; color?: string; weight?: number; fill?: string }) {
  return <Box {...pos} passive w={size} h={size}><Icon name={name} size={size} color={color} weight={weight} fill={fill} /></Box>;
}
// Independent original icon artwork. Text and button semantics remain live components.
export function SourceArt({ name, radius = 0, ...pos }: Partial<Pos> & { name: SourceArtName; radius?: number }) {
  const art = sourceArt[name];
  return <Photo x={art.x} y={art.y} w={art.w} h={art.h} {...pos} radius={radius} asset={art.asset} />;
}
export function Divider({ color = palette.border, ...pos }: Pos & { color?: string }) { return <Box {...pos} style={{ backgroundColor: color }} />; }
export function Back({ x = 90, y, onPress, arrow = false }: { x?: number; y: number; onPress: () => void; arrow?: boolean }) {
  return <><Glyph x={x} y={y} name={arrow ? 'ArrowLeft' : 'ChevronLeft'} size={49} weight={2} /><Hit x={x - 22} y={y - 10} w={95} h={85} label="Go back" onPress={onPress} /></>;
}
export function Primary({ x, y, w, h, text, onPress, label = text }: Pos & { text: string; label?: string; onPress: () => void }) {
  return <><Surface x={x} y={y} w={w} h={h} texture="dark-green-texture-tile" fill={palette.green} radius={35} border={false} /><Txt x={x} y={y + ((h ?? 0) - 48) / 2} w={w} fs={42} bold align="center" color="#fff" line={48}>{text}</Txt><Hit x={x} y={y} w={w} h={h} label={label} onPress={onPress} /></>;
}
