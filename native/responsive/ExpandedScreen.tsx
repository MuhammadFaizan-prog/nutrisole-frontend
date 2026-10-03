import { useState } from 'react';
import { View, Image, TextInput, Pressable } from 'react-native';
import { colors, type ExtensionRoute, type ExpansionState, type Layer } from '../../src/nutrisole/extensions/model';
import type { Profile } from '../../src/nutrisole/store';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import { extensionAssets } from '../../src/nutrisole/extensions/assets.native';
import { compileScene, flowBands, fixedColumnWidth, type FlowNode } from './sceneFlow';
import { T, Header, Screen, WeekStrip, useFrame } from './components';
import { journeyScene } from './journeyScene';
import TaskLinks from './TaskLinks';
type Events = { field: (key: string, value: string) => void; action: (value: string) => void };
export default function ExpandedScreen({ route, state, field, action, profile, connected, editingMeal, go, back }: Events & { route: ExtensionRoute; state: ExpansionState; profile: Profile; connected: boolean; editingMeal?: boolean; go: (route: import('../../src/nutrisole/types').AppRoute) => void; back: () => void }) {
  const flow = compileScene(journeyScene(route, state, profile, connected, editingMeal));
  const { gutter } = useFrame();
  const missingBack = ['sign-in', 'create-account', 'catalog-queue', 'model-release', 'operations-audit', 'report-triage'].includes(route);
  const header = missingBack ? <Header title={route === 'sign-in' ? 'Sign in' : route === 'create-account' ? 'Create account' : 'Staff preview'} back={back} /> : flow.header.length ? <View style={{ paddingVertical: 8 }}><Flow nodes={flow.header} origin={54} field={field} action={action} /></View> : undefined;
  const footer = flow.footer.length ? <View style={{ paddingHorizontal: gutter, paddingVertical: 8 }}><Flow nodes={flow.footer} origin={Math.min(...flow.footer.map(n => n.layer.y))} field={field} action={action} /></View> : undefined;
  return <Screen route={route} header={header} footer={footer} gap={0}>{missingBack && flow.header.length > 0 && <Flow nodes={flow.header} origin={54} field={field} action={action} />}<Flow nodes={flow.body} origin={flow.header.length ? 100 : 54} field={field} action={action} /><TaskLinks route={route} go={go} />{route === 'sign-in' && <T size={12} color={colors.muted} style={{ marginVertical: 12, textAlign: 'center' }}>Frontend demo · Account validation is simulated.</T>}</Screen>;
}
function Flow({ nodes, origin = 0, field, action, tabs = false }: Events & { nodes: FlowNode[]; origin?: number; tabs?: boolean }) {
  const { fontScale } = useFrame();
  if (tabs && nodes.length >= 7) return <WeekStrip items={nodes.map(n => <Node key={n.index} node={n} dayTab field={field} action={action} />)} />;
  if (tabs) return <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 3 }}>{nodes.map(n => <View key={n.index} style={{ flexGrow: 1, flexBasis: Math.max(35, 345 / nodes.length - 9), minWidth: nodes.length >= 7 && fontScale > 1.25 ? Math.max(42, Math.ceil(32 * fontScale + 8)) : 0 }}><Node node={n} dayTab={nodes.length >= 7} field={field} action={action} /></View>)}</View>;
  return <View>{flowBands(nodes, origin).map((band, i) => {
    const layers = band.columns.flat();
    const brand = layers.length === 2 && layers.some(n => n.layer.asset === 'leaf-brand-mark') && layers.some(n => n.layer.text === 'NutriSole');
    const divider = layers.length === 3 && layers.filter(n => n.layer.kind === 'surface' && n.layer.h <= 4).length === 2 && layers.some(n => n.layer.text === 'or');
    const stackButtons = fontScale > 1.6 && band.columns.length > 1 && band.columns.every(column => column.every(n => n.layer.kind === 'button'));
    if (brand) return <View key={i} style={{ marginTop: Math.min(band.gap, 36), flexDirection: 'row', alignItems: 'center', justifyContent: Math.min(...layers.map(n => n.layer.x)) > 60 ? 'center' : 'flex-start', gap: 8 }}>{layers.map(n => <Node key={n.index} node={n} field={field} action={action} />)}</View>;
    if (divider) return <View key={i} style={{ marginTop: Math.min(band.gap, 36), flexDirection: 'row', alignItems: 'center', gap: 14 }}>{[...layers].sort((a, b) => a.layer.kind === 'text' ? b.layer.x < 196 ? 1 : -1 : b.layer.kind === 'text' ? a.layer.x < 196 ? -1 : 1 : a.layer.x - b.layer.x).map(n => <View key={n.index} style={n.layer.kind === 'surface' ? { flex: 1 } : undefined}><Node node={n} field={field} action={action} /></View>)}</View>;
    return <View key={i} style={{ marginTop: Math.min(band.gap, 36), flexDirection: stackButtons ? 'column' : 'row', alignItems: stackButtons ? 'stretch' : 'center', gap: band.columns.length > 1 ? 10 : 0 }}>
    {band.columns.map((column, c) => {
      const fixed = column.every(n => ['icon', 'photo', 'radio', 'toggle'].includes(n.layer.kind));
      const referenceWidth = Math.max(...column.map(n => n.layer.x + n.layer.w)) - Math.min(...column.map(n => n.layer.x));
      const single = column.length === 1 ? column[0].layer : null;
      const centered = band.columns.length === 1 && single && referenceWidth < 160 && Math.abs(single.x + single.w / 2 - 196.5) < 45;
      return <View key={c} style={stackButtons ? { width: '100%' } : band.columns.length === 1 ? { flex: 1, alignItems: centered ? 'center' : fixed && referenceWidth < 160 ? 'flex-start' : 'stretch' } : fixed ? { width: fixedColumnWidth(column), flexShrink: 0 } : { flexGrow: referenceWidth, flexBasis: 0, minWidth: 0 }}>
        {column.map((n, j) => <View key={n.index} style={{ marginTop: j ? Math.max(5, Math.min(20, n.layer.y - (column[j - 1].layer.y + column[j - 1].layer.h))) : 0 }}><Node node={n} field={field} action={action} /></View>)}
      </View>;
    })}
  </View>;
  })}</View>;
}
function Input({ layer: l, field }: { layer: Layer; field: Events['field'] }) {
  const [visible, setVisible] = useState(false); const [contentHeight, setContentHeight] = useState(0);
  return <View style={{ flexDirection: 'row', alignItems: l.multiline ? 'flex-start' : 'center', minHeight: Math.max(48, l.h), borderRadius: l.radius || 12, backgroundColor: l.fill || colors.card, borderWidth: l.strokeWidth ?? .7, borderColor: colors.border, paddingHorizontal: 12, gap: 10 }}>
    {l.leadingIcon && <Icons name={l.leadingIcon} color={colors.muted} size={21} />}
    <TextInput accessibilityLabel={l.text} testID={`field-${l.field}`} value={l.value || ''} onChangeText={value => field(l.field || '', value)} placeholder={l.placeholder} placeholderTextColor="#8a8d87" secureTextEntry={l.secure && !visible} keyboardType={l.numeric ? 'decimal-pad' : l.field === 'email' ? 'email-address' : 'default'} autoCapitalize={l.secure || l.field === 'email' ? 'none' : 'sentences'} autoCorrect={!l.secure && l.field !== 'email'} multiline={l.multiline} maxLength={l.maxLength ?? (l.multiline ? 1000 : 200)} onContentSizeChange={e => l.multiline && setContentHeight(e.nativeEvent.contentSize.height)} style={{ flex: 1, minWidth: 0, fontFamily: 'NutriSans', fontSize: l.size || 16, lineHeight: (l.size || 16) * 1.3, color: colors.ink, includeFontPadding: false, paddingVertical: 13, paddingHorizontal: 0, minHeight: l.multiline ? Math.max(l.h, contentHeight) : 48, textAlignVertical: l.multiline ? 'top' : 'center' }} />
    {l.secure && <Pressable accessibilityRole="button" accessibilityLabel={`${visible ? 'Hide' : 'Show'} ${l.text}`} testID={`visibility-${l.field}`} onPress={() => setVisible(v => !v)} style={{ minWidth: 36, minHeight: 44, alignItems: 'center', justifyContent: 'center' }}><Icons name={visible ? 'EyeOff' : 'Eye'} color={colors.muted} size={22} /></Pressable>}
  </View>;
}
function Node({ node, field, action, dayTab = false }: Events & { node: FlowNode; dayTab?: boolean }) {
  const l = node.layer;
  const pressProps = (override = l) => ({ accessibilityRole: 'button' as const, accessibilityLabel: override.text || override.icon, testID: `action-${(override.action || '').replaceAll(':', '-')}`, disabled: override.disabled, onPress: () => action(override.action || '') });
  if (l.kind === 'text') return <T size={l.size} bold={l.bold} serif={l.serif} color={l.color} style={{ textAlign: l.align || 'left', lineHeight: l.line || (l.size || 16) * 1.22 }}>{l.text}</T>;
  if (l.kind === 'photo') {
    const props = { accessibilityLabel: l.asset?.includes('avatar') ? 'Profile photo' : l.asset === 'leaf-brand-mark' ? 'NutriSole leaf' : 'Food photo', source: extensionAssets[l.asset || ''] };
    if (l.w >= 200) return <View style={{ width: '100%', aspectRatio: l.w / l.h, borderRadius: l.radius, overflow: 'hidden' }}><Image {...props} resizeMode="cover" style={{ width: '100%', height: '100%' }} /></View>;
    return <Image {...props} resizeMode={l.asset === 'leaf-brand-mark' ? 'contain' : 'cover'} style={{ borderRadius: l.radius, width: l.w, height: l.h, flexShrink: 0 }} />;
  }
  if (l.kind === 'input') return <Input layer={l} field={field} />;
  if (l.kind === 'surface') {
    if (l.h <= 4) return <View pointerEvents="none" style={{ height: l.h, backgroundColor: l.fill }} />;
    const tabs = node.children.length > 1 && node.children.every(n => n.layer.kind === 'button');
    const decorative = l.w < 180 && node.children.every(n => n.layer.kind === 'icon' && !n.layer.action);
    const style = { width: decorative ? l.w : undefined, minHeight: tabs ? 0 : l.h, backgroundColor: l.fill, borderRadius: l.radius, borderWidth: l.strokeWidth ?? (l.fill === colors.card ? .6 : 0), borderColor: l.stroke || colors.border, padding: tabs ? 4 : 12 };
    const contents = <Flow nodes={node.children} origin={l.y + (tabs ? 4 : 12)} tabs={tabs} field={field} action={action} />;
    return node.actionLayer ? <Pressable {...pressProps(node.actionLayer)} style={({ pressed }) => [style, { opacity: pressed ? .75 : 1 }]}>{contents}</Pressable> : <View style={style}>{contents}</View>;
  }
  if (l.kind === 'icon') { const glyph = <Icons name={l.icon || ''} size={Math.min(l.w, 74)} color={l.color} />; return l.action ? <Pressable {...pressProps()} style={{ minHeight: 44, minWidth: 36, justifyContent: 'center', alignItems: 'center' }}>{glyph}</Pressable> : <View pointerEvents="none" style={{ alignItems: 'center' }}>{glyph}</View>; }
  if (l.kind === 'toggle') return <Pressable {...pressProps()} accessibilityRole="switch" accessibilityState={{ checked: Boolean(l.selected) }} hitSlop={8} style={{ minHeight: 44, minWidth: 43, alignItems: 'center', justifyContent: 'center' }}><View style={{ width: 43, height: 26, borderRadius: 14, backgroundColor: l.selected ? colors.green : '#d8dad4', justifyContent: 'center' }}><View style={{ marginLeft: l.selected ? 19 : 3, width: 20, height: 20, borderRadius: 10, backgroundColor: '#fffdf9' }} /></View></Pressable>;
  if (l.kind === 'radio') { const glyph = <View style={{ width: 24, height: 24, borderRadius: 14, borderWidth: 1, borderColor: l.selected ? colors.green : '#999c97', backgroundColor: l.selected ? colors.green : 'transparent', alignItems: 'center', justifyContent: 'center' }}>{l.selected && <Icons name="Check" size={18} color="#fff" />}</View>; return l.action ? <Pressable {...pressProps()} accessibilityRole="radio" accessibilityState={{ checked: Boolean(l.selected) }} style={{ minHeight: 44, alignItems: 'center', justifyContent: 'center' }}>{glyph}</Pressable> : <View pointerEvents="none" style={{ alignItems: 'center', justifyContent: 'center' }}>{glyph}</View>; }
  return <Pressable {...pressProps()} style={({ pressed }) => ({ minHeight: Math.max(44, l.h), paddingVertical: 10, paddingHorizontal: dayTab ? 2 : 10, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, opacity: l.disabled ? .62 : pressed ? .7 : 1, backgroundColor: l.fill, borderRadius: l.radius, borderWidth: l.fill === colors.card ? .8 : 0, borderColor: colors.border })}>
    {l.icon ? <Icons name={l.icon} size={23} color={l.color} /> : <T size={l.size || 16} bold={l.bold} color={l.color} style={{ textAlign: l.align || 'center', flexShrink: 1 }}>{l.text}</T>}
    {node.children.filter(c => c.layer.kind === 'icon').map(c => <View key={c.index} pointerEvents="none" style={{ flexShrink: 0 }}><Icons name={c.layer.icon || ''} size={22} color={c.layer.color} /></View>)}
  </Pressable>;
}
