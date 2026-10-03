import React, { createContext, useContext, useId, useState, type PropsWithChildren } from 'react';
import { View, Text, Image, Pressable, ScrollView, StyleSheet, useWindowDimensions, type TextStyle, type ViewStyle, type ImageStyle, type StyleProp } from 'react-native';
import Svg, { Defs, Mask, Rect, Circle, G, Path, Image as SvgImage } from 'react-native-svg';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import { assets } from '../../src/nutrisole/assets.native';
import { extensionAssets } from '../../src/nutrisole/extensions/assets.native';
import { sourceArt, type SourceArtName } from '../../src/nutrisole/sourceArt';
import { framePaths, sceneDimensions } from '../../src/nutrisole/sceneGeometry';
import { colors } from '../../src/nutrisole/extensions/model';
import { typography, weekStripLayout } from './metrics';

const Frame = createContext({ width: 393, height: 800, fontScale: 1, gutter: 20, compact: false });
export const useFrame = () => useContext(Frame);
export function FrameProvider({ children }: PropsWithChildren) {
  const window = useWindowDimensions();
  const [size, setSize] = useState({ width: window.width, height: window.height });
  const value = { ...size, fontScale: window.fontScale, gutter: size.width < 360 ? 16 : 20, compact: size.width < 380 || window.fontScale > 1.2 };
  return <View style={s.flex} onLayout={event => { const { width, height } = event.nativeEvent.layout; setSize(old => old.width === width && old.height === height ? old : { width, height }); }}><Frame.Provider value={value}>{children}</Frame.Provider></View>;
}
export function T({ children, size, bold = false, serif = false, color = colors.ink, style, ...props }: PropsWithChildren<{ size?: number; bold?: boolean; serif?: boolean; color?: string; style?: StyleProp<TextStyle>; testID?: string; selectable?: boolean }>) {
  const frame = useFrame();
  const fontSize = size ?? typography(frame.width, frame.height).body;
  return <Text {...props} style={[{ fontFamily: serif ? bold ? 'NutriSerifBold' : 'NutriSerif' : bold ? 'NutriSansBold' : 'NutriSans', fontSize, lineHeight: fontSize * (serif ? 1.16 : 1.24), color, includeFontPadding: false, flexShrink: 1 }, style]}>{children}</Text>;
}
export function Art({ name, size = 28, style }: { name: SourceArtName; size?: number; style?: StyleProp<ImageStyle> }) {
  const art = sourceArt[name];
  const round = ['onboarding-recognition', 'onboarding-personalized', 'onboarding-support', 'onboarding-continue', 'home-scan-camera', 'home-nav-camera', 'scan-close', 'scan-flash', 'scan-confirmation', 'scan-shutter'].includes(name);
  return <Image accessible={false} source={assets[art.asset]} resizeMode="contain" style={[{ width: size, height: size * art.h / art.w, flexShrink: 0, borderRadius: round ? size / 2 : 0 }, style]} />;
}
export function Pic({ asset, size = 62, radius = 12, style, mode = 'cover', label = 'Food photo' }: { asset: string; size?: number; radius?: number; style?: StyleProp<ImageStyle>; mode?: 'cover' | 'contain'; label?: string }) {
  if (asset === 'scan-photo-region' || asset === 'onboarding-photo-region') throw new Error('Use MaskedPhoto for photographed source overlays');
  return <Image source={assets[asset] || extensionAssets[asset]} resizeMode={mode} accessibilityLabel={label} style={[{ width: size, height: size, borderRadius: radius, flexShrink: 0 }, style]} />;
}
export function Texture({ asset, radius = 0 }: { asset: string; radius?: number }) { return <View pointerEvents="none" style={[StyleSheet.absoluteFill, { borderRadius: radius, overflow: 'hidden' }]}><Image accessible={false} source={assets[asset]} resizeMode="stretch" style={{ width: '100%', height: '100%' }} /></View>; }
export function Panel({ children, fill = colors.card, texture = 'warm-card-texture-tile', style, border = true }: PropsWithChildren<{ fill?: string; texture?: string; style?: StyleProp<ViewStyle>; border?: boolean }>) {
  const radius = StyleSheet.flatten(style)?.borderRadius;
  return <View style={[s.panel, { backgroundColor: fill, borderWidth: border ? .6 : 0 }, style]}>{texture && <Texture asset={texture} radius={typeof radius === 'number' ? radius : 18} />}{children}</View>;
}
export const idFor = (label: string) => label.toLowerCase().replace(/[^a-z0-9]+/g, '-');
export function Button({ label, text = label, onPress, primary = false, icon, art, disabled, style, children, textSize = 17, artSize = 23 }: PropsWithChildren<{ label: string; text?: string; onPress: () => void; primary?: boolean; disabled?: boolean; icon?: string; art?: SourceArtName; style?: StyleProp<ViewStyle>; textSize?: number; artSize?: number }>) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} testID={idFor(label)} disabled={disabled} onPress={onPress} style={({ pressed }) => [s.button, { backgroundColor: primary ? colors.green : colors.card, opacity: disabled ? .4 : pressed ? .75 : 1 }, style]}>
    {primary && <Texture asset="dark-green-texture-tile" radius={17} />}
    {children || <>{art ? <Art name={art} size={artSize} /> : icon ? <Icons name={icon} size={23} color={primary ? '#fff' : colors.ink} /> : null}<T size={textSize} bold={primary} color={primary ? '#fff' : colors.ink} style={s.buttonText}>{text}</T></>}
  </Pressable>;
}
export function Tap({ label, onPress, children, style, disabled, testID }: PropsWithChildren<{ label: string; onPress: () => void; style?: StyleProp<ViewStyle>; disabled?: boolean; testID?: string }>) { return <Pressable accessibilityRole="button" accessibilityLabel={label} testID={testID || idFor(label)} disabled={disabled} onPress={onPress} style={({ pressed }) => [{ opacity: disabled ? .4 : pressed ? .75 : 1 }, style]}>{children}</Pressable>; }
export function WeekStrip({ items }: { items: React.ReactNode[] }) {
  const frame = useFrame();
  const [availableWidth, setAvailableWidth] = useState(frame.width - frame.gutter * 2);
  const layout = weekStripLayout(availableWidth, items.length, frame.fontScale);
  return <ScrollView horizontal testID="week-strip" nestedScrollEnabled scrollEnabled={layout.scroll} showsHorizontalScrollIndicator={layout.scroll} style={{ flexGrow: 0 }} onLayout={event => setAvailableWidth(event.nativeEvent.layout.width)} contentContainerStyle={{ gap: layout.gap, alignItems: 'stretch' }}>
    {items.map((item, index) => <View key={index} style={{ width: layout.cellWidth }}>{item}</View>)}
  </ScrollView>;
}
export function IconButton({ label, onPress, name, art, color }: { label: string; onPress: () => void; name?: string; art?: SourceArtName; color?: string }) { return <Tap label={label} onPress={onPress} style={s.iconButton}>{art ? <Art name={art} size={23} /> : <Icons name={name || 'ChevronLeft'} size={25} color={color || colors.ink} />}</Tap>; }
export function Header({ title, subtitle, back, art, end }: { title: string; subtitle?: string; back: () => void; art?: SourceArtName; end?: React.ReactNode }) {
  return <View style={s.header}><IconButton label="Go back" onPress={back} art={art} /><View style={s.flex}><T size={21} bold style={s.center}>{title}</T>{subtitle && <T size={15} color={colors.muted} style={s.center}>{subtitle}</T>}</View><View style={s.headerEnd}>{end}</View></View>;
}
export function Screen({ route, children, header, footer, paper, gap = 12, gutter: overrideGutter }: PropsWithChildren<{ route: string; header?: React.ReactNode; footer?: React.ReactNode; paper?: string; gap?: number; gutter?: number }>) {
  const frame = useFrame();
  const gutter = overrideGutter ?? frame.gutter;
  return <View testID={`screen-${route}`} style={s.screen}>
    {paper && <Texture asset={paper} />}
    {header && <View style={{ paddingHorizontal: gutter }}>{header}</View>}
    <ScrollView testID={`scroll-${route}`} style={[s.flex, s.scroll]} keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag" contentInsetAdjustmentBehavior="never" automaticallyAdjustContentInsets={false} contentContainerStyle={{ paddingHorizontal: gutter, paddingTop: 12, paddingBottom: 20, gap, flexGrow: 1 }} showsVerticalScrollIndicator={false}>{children}</ScrollView>
    {footer && <View testID={`footer-${route}`} style={s.footer}>{footer}</View>}
  </View>;
}
/** Original exclusion mask hides all photographed labels, controls and device chrome. */
export function MaskedPhoto({ scene, width, height, slice = false, photoAsset }: { scene: 'scan' | 'onboarding'; width: number; height: number; slice?: boolean; photoAsset?: string }) {
  const id = `responsive-${useId().replaceAll(':', '')}`;
  const d = sceneDimensions[scene];
  return <Svg pointerEvents="none" width={width} height={height} viewBox={`${d.x} ${d.y} ${d.w} ${d.h}`} preserveAspectRatio={slice ? 'xMidYMid slice' : 'xMidYMid meet'}>
    <Defs><Mask id={id} maskUnits="userSpaceOnUse" x={d.x} y={d.y} width={d.w} height={d.h}><Rect x={d.x} y={d.y} width={d.w} height={d.h} fill="#fff" />
      {scene === 'scan' ? <G fill="#000"><Rect x={116} y={73} width={74} height={37} /><Rect x={304} y={53} width={255} height={77} rx={39} /><Rect x={620} y={71} width={160} height={40} /><Circle cx={127.5} cy={217.5} r={49} /><Circle cx={739} cy={217} r={49} /><Rect x={264} y={412} width={484} height={156} rx={49} /><Path d="M480 559H520L500 585Z" /><Rect x={142} y={1226} width={583} height={155} rx={54} />{framePaths.map(p => <Path key={p} d={p} fill="none" stroke="#000" strokeWidth={16} strokeLinecap="round" />)}</G> : <G fill="#000"><Rect x={38} y={609} width={786} height={20} /><Rect x={62} y={1089} width={737} height={505} rx={52} /></G>}
    </Mask></Defs><SvgImage x={d.x} y={d.y} width={d.w} height={d.h} href={assets[photoAsset ?? d.asset]} mask={`url(#${id})`} />
  </Svg>;
}
export const s = StyleSheet.create({
  flex: { flex: 1 }, row: { flexDirection: 'row', alignItems: 'center', gap: 12 }, wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 }, center: { textAlign: 'center' },
  screen: { flex: 1, backgroundColor: colors.cream }, scroll: { overflow: 'hidden' }, panel: { borderRadius: 18, borderColor: colors.border, padding: 16, gap: 12 },
  button: { minHeight: 48, paddingVertical: 12, paddingHorizontal: 14, borderRadius: 17, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  buttonText: { textAlign: 'center', flexShrink: 1 }, iconButton: { width: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, minHeight: 56 }, headerEnd: { minWidth: 44, alignItems: 'center' },
  footer: { backgroundColor: colors.cream, borderTopWidth: .5, borderColor: colors.border, paddingTop: 8 }, divider: { height: .6, backgroundColor: colors.border },
});
