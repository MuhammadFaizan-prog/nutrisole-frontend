import { View, Text, Image, Pressable } from '../primitives';
import { buildScene, colors, type ExtensionRoute, type ExpansionState, type Layer } from './model';
import Input from './Input';
import Icons from './Icons';
import { extensionAssets } from './assets';
import Viewport from './Viewport';
type Props = { route: ExtensionRoute; width: number; height: number; state: ExpansionState; field: (key: string, value: string) => void; action: (value: string) => void };
export default function ExpansionScreen({ route, width, height, state, field, action }: Props) {
  const scene = buildScene(route, state);
  return <Viewport width={width} height={height} scene={scene} render={(l, i) => <LayerView key={`${route}-${i}`} layer={l} field={field} action={action} />} />;
}
function LayerView({ layer: l, field, action }: { layer: Layer; field: Props['field']; action: Props['action'] }) {
  const rect = { position: 'absolute' as const, left: l.x, top: l.y, width: l.w, height: l.h };
  const labelStyle = { fontFamily: l.serif ? l.bold ? 'NutriSerifBold' : 'NutriSerif' : l.bold ? 'NutriSansBold' : 'NutriSans', fontSize: l.size || 16, lineHeight: l.line || (l.size || 16) * 1.22, color: l.color || colors.ink, textAlign: l.align || 'left', includeFontPadding: false, letterSpacing: l.serif ? -.65 : -.15 };
  const label = <Text pointerEvents="none" style={labelStyle}>{l.text}</Text>;
  if (l.kind === 'text') return <Text pointerEvents="none" style={{ ...rect, ...labelStyle }}>{l.text}</Text>;
  if (l.kind === 'surface') return <View pointerEvents="none" style={{ ...rect, backgroundColor: l.fill, borderRadius: l.radius, borderWidth: l.strokeWidth ?? (l.fill === colors.card ? .6 : 0), borderColor: l.stroke || colors.border }} />;
  if (l.kind === 'photo') return <Image accessibilityLabel={l.asset === 'leaf-brand-mark' ? 'NutriSole leaf' : l.asset?.includes('avatar') ? 'Profile photo' : 'Food photo'} source={extensionAssets[l.asset || '']} resizeMode="cover" style={{ ...rect, borderRadius: l.radius }} />;
  if (l.kind === 'input') return <Input label={l.text || ''} placeholder={l.placeholder} value={l.value || ''} secure={l.secure} numeric={l.numeric} multiline={l.multiline} maxLength={l.maxLength} onChange={value => field(l.field || '', value)} style={{ ...rect, backgroundColor: l.fill, borderRadius: l.radius, borderWidth: l.strokeWidth ?? .7, borderColor: colors.border, padding: 16, paddingLeft: l.leadingIcon ? 52 : 16, color: colors.ink, fontFamily: 'NutriSans', fontSize: l.size || 16, lineHeight: 21 }} />;
  const press = (children: React.ReactNode, style: object = {}) => <Pressable role="button" aria-label={l.text || l.icon} testID={`action-${(l.action || '').replaceAll(':', '-')}`} disabled={l.disabled} onPress={() => action(l.action || '')} style={({ pressed }: { pressed: boolean }) => ({ ...rect, justifyContent: 'center', alignItems: 'center', opacity: l.disabled ? .62 : pressed ? .7 : 1, ...style })}>{children}</Pressable>;
  if (l.kind === 'icon') { const glyph = <Icons name={l.icon || ''} size={l.w} color={l.color} />; return l.action ? press(glyph) : <View pointerEvents="none" style={rect}>{glyph}</View>; }
  if (l.kind === 'toggle') return press(<View pointerEvents="none" style={{ width: l.w, height: l.h, borderRadius: 14, backgroundColor: l.selected ? colors.green : '#d8dad4', justifyContent: 'center' }}><View style={{ marginLeft: l.selected ? l.w - 24 : 3, width: 20, height: 20, borderRadius: 10, backgroundColor: '#fffdf9' }} /></View>);
  if (l.kind === 'radio') { const style = { borderRadius: 14, borderWidth: 1, borderColor: l.selected ? colors.green : '#999c97', backgroundColor: l.selected ? colors.green : 'transparent', alignItems: 'center' as const, justifyContent: 'center' as const }; const glyph = l.selected ? <Icons name="Check" size={18} color="#fff" /> : null; return l.action ? press(glyph, style) : <View pointerEvents="none" style={{ ...rect, ...style }}>{glyph}</View>; }
  return press(l.icon ? <Icons name={l.icon} size={23} color={l.color} /> : label, { backgroundColor: l.fill, borderRadius: l.radius, borderWidth: l.fill === colors.card ? .8 : 0, borderColor: colors.border });
}
