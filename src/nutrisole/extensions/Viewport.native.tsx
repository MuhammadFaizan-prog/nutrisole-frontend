import type { ReactNode } from 'react';
import { View, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { colors, type Layer, type Scene } from './model';
import { fixedFooterStart, headerHeight } from './layout';
export type ViewportProps = { width: number; height: number; scene: Scene; render: (l: Layer, i: number) => ReactNode };
export default function Viewport({ width, height, scene, render }: ViewportProps) {
  const scale = Math.min(width / 393, height / 852); const nodes = scene.layers.map((l, i) => ({ l, i }));
  const top = headerHeight(scene); const footerStart = fixedFooterStart(scene); const footerHeight = footerStart === null ? 0 : 818 - footerStart;
  const plane = (items: { l: Layer; i: number }[], offset = 0, h = scene.height) => <View style={{ width: 393, height: h, transform: [{ scale }], transformOrigin: 'top left' }}>{items.map(({ l, i }) => render({ ...l, y: l.y - offset }, i))}</View>;
  return <KeyboardAvoidingView testID={`screen-${scene.id}`} behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ width, height, backgroundColor: colors.cream }}>
    <View style={{ height: top * scale, marginLeft: (width - 393 * scale) / 2 }}>{plane(nodes.filter(({ l }) => l.y < top), 0, top)}</View>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ height: Math.max(scene.height - top, 852 - top) * scale, marginLeft: (width - 393 * scale) / 2 }} style={{ flex: 1 }}>
      {plane(nodes.filter(({ l }) => l.y >= top && (footerStart === null || l.y < footerStart)), top, scene.height - top)}
    </ScrollView>
    {footerStart !== null && <View style={{ height: footerHeight * scale, marginLeft: (width - 393 * scale) / 2 }}>{plane(nodes.filter(({ l }) => l.y >= footerStart), footerStart, footerHeight)}</View>}
    <View style={{ height: 34 }} />
  </KeyboardAvoidingView>;
}
