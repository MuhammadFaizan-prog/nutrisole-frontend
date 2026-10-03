import { useRef, useState } from 'react';
import { View } from 'react-native';
import { T, Art, Pic, Panel, Tap, Button, Header, Screen, IconButton, MaskedPhoto, useFrame, s } from './components';
import { colors } from '../../src/nutrisole/extensions/model';
import ProgressRing from '../../src/nutrisole/ProgressRing.native';
import type { Store, Profile as ProfileData } from '../../src/nutrisole/store';
import type { AppRoute, Sheet } from '../../src/nutrisole/types';
import type { SourceArtName } from '../../src/nutrisole/sourceArt';
import { edibleMass, energyForMass, type PortionMode } from '../../src/nutrisole/domain';
import { largeTextLayout, homeActionsLayout } from './metrics';
import Icons from '../../src/nutrisole/extensions/Icons.native';
import { foodInfo } from '../../src/nutrisole/extensions/model';
import { mealCarbs, type NativeMeal } from './journeyData';
export type CoreProps = { store: Store; go: (r: AppRoute) => void; back: () => void; home: () => void; open: (sheet: Sheet) => void };

export function Onboarding({ home, go }: CoreProps) {
  const { width, fontScale } = useFrame();
  const largeText = largeTextLayout(width, fontScale);
  const gutter = 28;
  const photoHeight = width * 982 / 786;
  return <Screen route="onboarding" gutter={gutter} paper="paper-onboarding-calibrated" gap={9} footer={<View style={[s.row, { paddingHorizontal: gutter + 10, paddingBottom: 8, justifyContent: 'space-between' }]}><View style={[s.row, { gap: 10 }]}>{[0, 1, 2, 3].map(i => <View key={i} style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: i ? '#dcdcd4' : colors.green }} />)}</View><Tap label="Get started" onPress={() => go('create-account')}><Art name="onboarding-continue" size={70} /></Tap></View>}>
    <View style={[s.row, { marginTop: 8, flexDirection: largeText.expanded ? 'column' : 'row', alignItems: largeText.expanded ? 'stretch' : 'center' }]}><View style={[s.row, !largeText.expanded && s.flex]}><Pic asset="leaf-brand-mark" size={32} radius={0} mode="contain" style={{ height: 40 }} /><T serif size={largeText.brandSize} style={s.flex}>NutriSole</T></View><Tap label="Skip onboarding" onPress={home} style={{ padding: 10, alignSelf: largeText.expanded ? 'flex-end' : 'center' }}><T size={19}>Skip</T></Tap></View>
    <T size={37} serif bold style={{ fontFamily: 'NutriSerifText', lineHeight: 43 }}>Healthy choices,{ '\n' }made simple.</T>
    <T size={19} style={{ lineHeight: 24 }}>{'Scan your food, get instant insights,\nand build a plan that fits your life,\nwith the power of computer vision.'}</T>
    <View style={{ marginHorizontal: -gutter, height: photoHeight }}><MaskedPhoto scene="onboarding" width={width} height={photoHeight} /></View>
    <Panel border={false} texture="" style={{ marginTop: -photoHeight * .51 - 9, marginHorizontal: -15, padding: 10, borderRadius: 26, gap: 8 }}>
      {[
        ['Instant food recognition', 'Know what you’re eating', 'onboarding-recognition'],
        ['Personalized nutrition', 'Get practical, realistic guidance', 'onboarding-personalized'],
        ['Long-term health support', 'Small steps. Real progress.', 'onboarding-support'],
      ].map(([title, sub, art]) => <Panel key={title} texture="onboarding-card-paper" border={false} style={[s.row, { padding: 8, borderRadius: 22, minHeight: 72 }]}><Art name={art as SourceArtName} size={54} /><View style={[s.flex, { gap: 5 }]}><T bold size={18}>{title}</T><T size={16} color="#575b59">{sub}</T></View></Panel>)}
    </Panel>
    <Tap label="Already registered? Sign in" onPress={() => go('sign-in')} style={{ minHeight: 44, justifyContent: 'center' }}><T size={15} color={colors.green} style={s.center}>Already registered? Sign in</T></Tap>
  </Screen>;
}
export function Home({ store, go }: CoreProps) {
  const { compact, width, fontScale } = useFrame();
  const [actionsWidth, setActionsWidth] = useState(width - 24);
  const actionsLayout = homeActionsLayout(actionsWidth, fontScale);
  const extra = store.state.meals.reduce((n, m) => n + m.calories, 0);
  const count = Math.min(5, 3 + store.state.meals.length); const latest = store.state.meals.at(-1) as NativeMeal | undefined;
  const metrics = [
    { value: (1420 + extra).toLocaleString('en-US'), label: 'calories', color: '#e75212', bar: '#ff9448', progress: .98 },
    { value: '82g', label: 'protein', color: '#7780bd', bar: '#98a0ed', progress: .8 },
    { value: `${48 + Math.round(mealCarbs(store.state.meals))}g`, label: 'carbs', color: '#467f79', bar: '#5fcbb9', progress: .85 },
    { value: '62g', label: 'fat', color: '#bb882d', bar: '#fbd47d', progress: .65 },
  ];
  return <Screen route="home" gutter={12} paper="paper-home">
    <View style={[s.row, { paddingHorizontal: 14, marginTop: 0, marginBottom: 3 }]}><View style={s.flex}><T size={21}>Good morning,</T><T size={34} serif bold>{store.state.profile.name.split(' ')[0]}</T></View><Tap label="Open profile" onPress={() => go('profile')}><Pic asset="alex-avatar-home" size={44} radius={30} label="Profile photo" /></Tap><IconButton label="Open menu" name="Settings" onPress={() => go('flow-directory')} /></View>
    <Panel style={{ paddingHorizontal: 20, paddingVertical: 12, gap: 17 }}><View style={[s.row, { alignItems: 'flex-start', flexWrap: compact ? 'wrap' : 'nowrap' }]}><View style={{ flex: 1, minWidth: compact ? 150 : 0, gap: 10 }}><T size={14} color="#5d6264" style={{ letterSpacing: .3 }}>KEEP GOING</T><T size={21} bold>{count === 5 ? 'You’ve reached your meal goal' : `You’re ${5 - count} ${count === 4 ? 'meal' : 'meals'} away from your goal`}</T></View><View style={{ width: 105, height: 105, alignItems: 'center', justifyContent: 'center' }}><View pointerEvents="none" style={{ position: 'absolute' }}>{count === 3 ? <Pic asset="home-progress-ring" size={105} radius={0} /> : <ProgressRing size={105} fraction={count / 5} />}</View><T size={21} bold>{count}/5</T><T size={15} color="#5e6263">meals</T></View></View>
      <View style={[s.wrap, { gap: 0 }]}>{metrics.map(m => <View key={m.label} style={{ width: compact ? '50%' : '25%', paddingVertical: 3, paddingHorizontal: 3, gap: 6 }}><T size={width < 350 ? 20 : 22} bold style={s.center}>{m.value}</T><T size={15} color={m.color} style={s.center}>{m.label}</T><View style={{ height: 8, borderRadius: 5, backgroundColor: m.bar + '44', marginHorizontal: 3 }}><View style={{ height: 8, borderRadius: 5, backgroundColor: m.bar, width: `${m.progress * 100}%` }} /></View></View>)}</View>
    </Panel>
    <Tap label="Scan food" onPress={() => go('scan')}><Panel fill={colors.green} texture="dark-green-scan-texture-tile" border={false} style={[s.row, { padding: 13, minHeight: 108 }]}><Art name="home-scan-camera" size={82} /><View style={[s.flex, { gap: 5 }]}><T size={23} bold color="#fff">Scan Food</T><T size={17} color="#f2f5ea">Instant nutrition insights</T></View><Art name="home-scan-chevron" size={10} /></Panel></Tap>
    <View onLayout={event => setActionsWidth(event.nativeEvent.layout.width)} style={[s.row, { flexDirection: actionsLayout.columns === 1 ? 'column' : 'row', alignItems: 'stretch', gap: 8 }]}>{[
      ['View Plan', 'Meals for your goals', 'weekly-plan', 'home-plan-calendar', 'home-plan-chevron', 'pale-green-texture-tile', '#577060'],
      ['Health', 'Trends & insights', 'health', 'home-health-bars', 'home-health-chevron', 'lavender-texture-tile', '#5c6b9f'],
    ].map(([title, sub, route, art, chevron, texture, color]) => <Tap key={title} label={title === 'Health' ? 'Open health' : 'View plan'} onPress={() => go(route as AppRoute)} style={actionsLayout.columns === 2 ? s.flex : undefined}><Panel texture={texture} border={false} style={{ flexGrow: 1, padding: actionsLayout.padding, minHeight: 113, gap: 6 }}><Art name={art as SourceArtName} size={27} /><View style={[s.row, { gap: 8 }]}><T size={18} bold style={s.flex}>{title}</T><Art name={chevron as SourceArtName} size={8} /></View><T size={15} color={color}>{sub}</T></Panel></Tap>)}</View>
    <Panel style={{ padding: 14, gap: 10 }}><View style={s.row}><T bold size={20} style={s.flex}>Recent Scans</T><Tap label="See all scans" onPress={() => go('history')} style={[s.row, { gap: 5, minHeight: 36 }]}><T size={15} color={colors.green}>See all</T><Art name="home-see-all-chevron" size={7} /></Tap></View><View style={s.divider} />
      {[
        { label: latest ? 'Review latest logged food' : 'Review apple scan', title: latest?.food || 'Apple', sub: latest ? `${Math.round(latest.grams)} g (confirmed)` : '1 medium (confirmed)', calories: latest?.calories ?? 95, time: latest ? 'Just now' : '12:24 PM', asset: latest?.food ? foodInfo(latest.food).asset : 'apple-thumbnail-home', route: latest ? 'history' : 'log-meal' },
        { label: 'Review chicken bowl', title: 'Grilled Chicken Bowl', sub: 'Chicken, rice, veggies', calories: 420, time: 'Yesterday', asset: 'chicken-bowl-home', route: 'history' },
      ].map((m, i) => <View key={m.label} style={{ gap: 10 }}>{i > 0 && <View style={s.divider} />}<Tap label={m.label} onPress={() => go(m.route as AppRoute)} style={[s.row, { gap: 12, alignItems: 'flex-start' }]}><Pic asset={m.asset} size={60} /><View style={[s.flex, { gap: 3 }]}><View style={[s.row, { flexWrap: 'wrap', gap: 3 }]}><T size={16} bold style={{ flexGrow: 1 }}>{m.title}</T><T size={12} color={colors.muted}>{m.time}</T></View><T size={14} color={colors.muted}>{m.sub}</T><T size={16} bold>{m.calories} cal</T></View></Tap></View>)}
    </Panel>
  </Screen>;
}
export type ApplePortion = { mode: PortionMode; quantity: number; weight: number; size: 'small' | 'medium' | 'large' };
export const freshApplePortion = (): ApplePortion => ({ mode: 'amount', quantity: 1, weight: 182, size: 'medium' });
export function LogMeal({ back, home, store, open, go, portion, updatePortion }: CoreProps & { portion: ApplePortion; updatePortion: (change: (old: ApplePortion) => ApplePortion) => void }) {
  const { compact, width, fontScale } = useFrame();
  const largeText = largeTextLayout(width, fontScale);
  const { mode, quantity, weight, size } = portion;
  const setMode = (value: PortionMode) => updatePortion(old => ({ ...old, mode: value }));
  const setQuantity = (change: (old: number) => number) => updatePortion(old => ({ ...old, quantity: change(old.quantity) }));
  const setWeight = (change: number | ((old: number) => number)) => updatePortion(old => ({ ...old, weight: typeof change === 'number' ? change : change(old.weight) }));
  const setSize = (value: ApplePortion['size']) => updatePortion(old => ({ ...old, size: value }));
  const submissionKey = useRef(`portion-${Date.now()}-${Math.random().toString(36).slice(2)}`); const submitted = useRef(false);
  const mass = edibleMass(mode, mode === 'weight' ? weight : quantity, size); const calories = energyForMass(mass);
  const save = (kind: 'consumed' | 'draft') => { if (submitted.current) return; submitted.current = true; store.saveMeal({ id: submissionKey.current, submissionKey: submissionKey.current, grams: mass, calories, createdAt: new Date().toISOString() }, kind); home(); };
  const editWeight = () => open({ title: 'Edible weight', description: 'Enter the apple portion in grams. This is a demo estimate based on 95 cal per 182 g.', fields: [{ key: 'grams', label: 'Weight in grams', value: String(weight), numeric: true }], save: v => { const grams = Number(v.grams); if (!Number.isFinite(grams) || grams <= 0 || grams > 10000) return 'Enter a weight greater than 0 and at most 10,000 g.'; setWeight(grams); } });
  const editSize = () => open({ title: 'Apple size', description: 'Demo edible weights: small 149 g, medium 182 g, large 223 g.', choices: (['small', 'medium', 'large'] as const).map(v => ({ label: `${v[0].toUpperCase()}${v.slice(1)} apple`, selected: size === v, action: () => setSize(v) })) });
  return <Screen route="log-meal" gutter={12} paper="warm-background-tile" gap={22} header={<Header title="Log Meal" back={back} art="log-back" />}>
    <Panel border={false} style={[s.row, { gap: 18, padding: 12 }]}><Pic asset="apple-thumbnail" size={82} radius={16} /><View style={[s.flex, { gap: 4 }]}><T size={19} bold>Apple</T><T size={16} color={colors.muted}>95 cal per medium (182 g)</T></View><Tap label="Nutrition information" onPress={() => open({ title: 'Apple nutrition', description: 'Demo basis: 95 calories per medium apple, with an edible portion of 182 g. Values are estimates. A photo does not measure the weight of your food.', choices: [{ label: 'View nutrition details', action: () => go('nutrition-details') }] })} style={{ minHeight: 44, justifyContent: 'center' }}><Art name="log-info" size={23} /></Tap></Panel>
    <View style={{ gap: 8, paddingHorizontal: 6 }}><T size={23} bold>Confirm portion</T><T size={17} color={colors.muted}>Adjust the amount you plan to eat. This helps us log your meal accurately.</T></View>
    <Panel texture="gray-track-texture-tile" border={false} style={[s.row, { padding: 0, gap: 0, borderRadius: 24, flexWrap: largeText.expanded ? 'wrap' : 'nowrap' }]}>{(['amount', 'weight', 'size'] as const).map(m => <Button key={m} label={`Portion by ${m}`} text={`By ${m}`} onPress={() => { setMode(m); if (m === 'weight') editWeight(); if (m === 'size') editSize(); }} primary={mode === m} style={{ flexGrow: 1, flexBasis: largeText.expanded ? 132 : 0, minWidth: largeText.expanded ? 132 : 0, borderRadius: 24, backgroundColor: mode === m ? colors.green : 'transparent', paddingHorizontal: 5 }} textSize={16} />)}</Panel>
    <View style={[s.row, { flexWrap: compact ? 'wrap' : 'nowrap', gap: 18 }]}><View style={s.row}><Tap label="Decrease portion" disabled={mode !== 'weight' && quantity <= 1} onPress={() => mode === 'weight' ? setWeight(v => Math.max(1, v - 10)) : setQuantity(v => Math.max(1, v - 1))} style={{ padding: 2 }}><Art name="log-minus" size={39} /></Tap><T size={32} bold style={{ minWidth: 30, textAlign: 'center' }}>{mode === 'weight' ? weight : quantity}</T><Tap label="Increase portion" onPress={() => mode === 'weight' ? setWeight(v => Math.min(10000, v + 10)) : setQuantity(v => Math.min(50, v + 1))} style={{ padding: 2 }}><Art name="log-plus" size={39} /></Tap></View><Tap label="Edit portion details" onPress={mode === 'weight' ? editWeight : editSize} style={{ flex: 1, minWidth: compact ? 180 : 0, gap: 5 }}><T size={18} bold>{mode === 'weight' ? 'grams' : `${size} apple${quantity > 1 ? 's' : ''}`}</T><T size={14} color={colors.muted}>{`(about ${Math.round(mass)} g, edible portion)`}</T></Tap></View>
    <Panel texture="pale-green-estimate-texture-tile" border={false} style={[s.row, { alignItems: 'flex-start', padding: 18 }]}><Art name="log-estimate-apple" size={21} /><View style={[s.flex, { gap: 6 }]}><T size={21} bold color="#123e35">≈ {calories} calories</T><T size={16} color="#51646a">Estimated for {mode === 'weight' ? `${weight} g of apple` : `${quantity} ${size} apple${quantity > 1 ? 's' : ''}`}</T><T size={16} color="#51646a">Values are estimates.</T></View></Panel>
    <Button label="Confirm log meal" text="Log Meal" primary onPress={() => save('consumed')} style={{ minHeight: 58 }} textSize={23} /><Tap label="Save for later" onPress={() => save('draft')} style={{ minHeight: 50, justifyContent: 'center' }}><T size={21} bold color="#103e32" style={s.center}>Save for later</T></Tap>
  </Screen>;
}
export function Profile({ store, back, open, go }: CoreProps) {
  const { compact, fontScale, width } = useFrame(); const { profile } = store.state;
  const largeText = largeTextLayout(width, fontScale);
  const stackAccount = fontScale > 1.2 && width < 380;
  function edit(key: keyof ProfileData, label: string) {
    if (key === 'glucoseUnit') return open({ title: 'Glucose Unit', description: 'Choose the display unit for this local demo.', choices: ['mg/dL', 'mmol/L'].map(unit => ({ label: unit, selected: profile.glucoseUnit === unit, action: () => store.update(old => ({ ...old, profile: { ...old.profile, glucoseUnit: unit } })) })) });
    open({ title: label, fields: [{ key, label, value: profile[key] }], save: v => { if (!v[key]?.trim()) return 'Enter a value, or use None for no constraint.'; store.update(old => ({ ...old, profile: { ...old.profile, [key]: v[key].trim() } })); } });
  }
  const preferences: [keyof ProfileData, string, SourceArtName][] = [['dietary', 'Dietary Preferences', 'profile-dietary'], ['allergens', 'Allergens', 'profile-allergens'], ['activity', 'Activity Preferences', 'profile-activity'], ['mobility', 'Mobility Constraints', 'profile-mobility'], ['glucoseUnit', 'Glucose Unit', 'profile-glucose'], ['timezone', 'Timezone', 'profile-timezone']];
  return <Screen route="profile" gutter={12} paper="paper-profile" header={<Header title="Profile & Preferences" back={back} art="profile-back" end={<IconButton label="Open settings" name="Settings" onPress={() => go('flow-directory')} />} />} gap={8}>
    <Tap label="Edit account" onPress={() => open({ title: 'Your profile', fields: [{ key: 'name', label: 'Name', value: profile.name }, { key: 'email', label: 'Email', value: profile.email }], save: v => { if (!v.name?.trim()) return 'Enter a name.'; if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email)) return 'Enter a valid email.'; store.update(old => ({ ...old, profile: { ...old.profile, name: v.name.trim(), email: v.email.trim() } })); } })}><Panel style={[s.row, { flexDirection: stackAccount ? 'column' : 'row', alignItems: stackAccount ? 'stretch' : 'center', padding: 16, gap: 17, minHeight: 89 }]}><Pic asset="alex-avatar" size={68} radius={40} label="Profile photo" /><View style={[!stackAccount && s.flex, { gap: 6 }]}><T size={20} bold>{profile.name}</T><T size={15} color={colors.muted}>{profile.email}</T></View><Art name="profile-account-chevron" size={8} style={{ alignSelf: stackAccount ? 'flex-end' : 'center' }} /></Panel></Tap>
    <Panel texture="warm-card-texture-tile" style={{ paddingVertical: 0, paddingHorizontal: 16, gap: 0 }}>{preferences.map(([key, label, art], i) => <View key={key}>{i > 0 && <View style={s.divider} />}<Tap label={`Edit ${label}`} onPress={() => edit(key, label)} style={[s.row, { paddingVertical: 14, minHeight: 46, gap: 16 }]}><Art name={art} size={21} /><View style={{ flex: 1, gap: 5, flexDirection: compact ? 'column' : 'row', alignItems: compact ? 'flex-start' : 'center' }}><T size={15} style={{ flex: compact ? undefined : 1 }}>{label}</T><T size={13} color="#8a8b92" style={{ flex: compact ? undefined : 1, textAlign: compact ? 'left' : 'right' }}>{profile[key]}</T></View></Tap></View>)}</Panel>
    <Tap label="Manage health connection" onPress={() => go('health-connections')}><Panel style={[s.row, { padding: 13, gap: 12 }]}><Art name="profile-health" size={32} /><View style={[s.flex, { gap: 8 }]}><T size={16}>Connected Health Source</T><View style={[s.row, { flexWrap: 'wrap', gap: 8, flexDirection: largeText.expanded ? 'column' : 'row', alignItems: largeText.expanded ? 'flex-start' : 'center' }]}><T size={15} color={colors.muted} style={{ flexGrow: 1 }}>Apple Health</T><View style={[s.row, { backgroundColor: '#e9f5e7', paddingVertical: 8, paddingHorizontal: 9, borderRadius: 30, gap: 5 }]}>{store.state.connected && <Art name="profile-connected" size={10} />}<T size={13} bold color="#165438">{store.state.connected ? 'Connected' : 'Off'}</T></View></View></View></Panel></Tap>
    <Tap label="Privacy and consent" onPress={() => go('privacy-data-rights')}><Panel style={[s.row, { padding: 16, gap: 18 }]}><Art name="profile-privacy" size={21} /><View style={[s.flex, { gap: 7 }]}><T size={17}>Privacy & Consent</T><T size={14} color="#81858a">Manage your data and permissions</T></View><Art name="profile-privacy-chevron" size={8} /></Panel></Tap>
    <Tap label="Menu and settings" onPress={() => go('flow-directory')} style={[s.row, { padding: 16, minHeight: 52 }]}><Icons name="Settings" size={22} color={colors.green} /><T size={16} bold color={colors.green} style={s.flex}>Menu & Settings</T><Icons name="ChevronRight" size={18} color={colors.green} /></Tap>
  </Screen>;
}
