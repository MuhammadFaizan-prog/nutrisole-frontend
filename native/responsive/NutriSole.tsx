import { useEffect, useReducer, useState } from 'react';
import { Keyboard, View } from 'react-native';
import type { AppRoute, Sheet } from '../../src/nutrisole/types';
import { useDemoStore } from '../../src/nutrisole/store';
import { useExpansion } from '../../src/nutrisole/extensions/useExpansion';
import { extensionRoutes, type ExtensionRoute } from '../../src/nutrisole/extensions/model';
import { useSystemBack } from '../../src/nutrisole/useSystemBack.native';
import { Onboarding, Home, LogMeal, Profile, freshApplePortion } from './CoreScreens';
import WeeklyPlan from './WeeklyScreen';
import Scan from './ScanScreen';
import ExpandedScreen from './ExpandedScreen';
import ScreenDirectory from './ScreenDirectory';
import TabBar from './TabBar';
import { canonicalRoute, navigationReducer, primaryTabs, showTabs } from './navigation';
import { sceneStateFor, nativeRecord, portionFromAction, savePortionRecord, type PortionContext } from './journeyData';
import { mealResult } from '../../src/nutrisole/extensions/domain';
export const routes: AppRoute[] = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile', 'health', 'history', ...extensionRoutes];
export default function NutriSole({ open, requestedRoute = 'onboarding', requestedIntent = 'reset', navigationToken = 0, routeChanged }: { open: (sheet: Sheet) => void; requestedRoute?: AppRoute; requestedIntent?: 'reset' | 'push'; navigationToken?: number; routeChanged?: (route: AppRoute) => void }) {
  const store = useDemoStore(); const expansion = useExpansion();
  const [{ route, history }, dispatch] = useReducer(navigationReducer, { route: canonicalRoute(requestedRoute), history: [] });
  const [signedIn, setSignedIn] = useState(false);
  const [portionRecord, setPortionRecord] = useState<PortionContext | null>(null);
  const [applePortion, setApplePortion] = useState(freshApplePortion);
  const mobility = /^(none|unrestricted)$/i.test(store.state.profile.mobility.trim()) ? 'Unrestricted' : 'Limited';
  const sceneState = sceneStateFor({ ...expansion.state, choices: { ...expansion.state.choices, mobility } }, store.state);
  useEffect(() => { if (expansion.state.choices.mobility !== mobility) expansion.action(`choose:mobility:${mobility}`, () => {}, () => {}, open); }, [mobility, expansion, open]);
  useEffect(() => { Keyboard.dismiss(); dispatch({ type: requestedIntent, route: requestedRoute }); }, [requestedRoute, requestedIntent, navigationToken]);
  useEffect(() => routeChanged?.(route), [route, routeChanged]);
  const go = (destination: AppRoute) => {
    Keyboard.dismiss();
    const next = canonicalRoute(destination);
    if (next === 'analysis-result') { setFood('Apple'); setApplePortion(freshApplePortion()); }
    if (next === 'glucose-overview') expansion.action(`choose:unit:${store.state.profile.glucoseUnit}`, go, back, open);
    if (route === 'log-meal' && next === 'nutrition-details') expansion.action('choose:food:Apple', go, back, open);
    const returning = route === 'capture-retry' && next === 'scan' || ['recover-account', 'reset-password', 'verify-email', 'create-account'].includes(route) && next === 'sign-in';
    dispatch({ type: primaryTabs.some(tab => tab.route === next) && next !== 'scan' ? 'tab' : returning ? 'popTo' : 'push', route: next });
  };
  const back = () => { Keyboard.dismiss(); dispatch({ type: 'back' }); };
  const home = () => { Keyboard.dismiss(); setApplePortion(freshApplePortion()); dispatch({ type: 'reset', route: 'home' }); };
  useSystemBack(back, history.length > 0 || route !== 'home' && route !== 'onboarding');
  const setFood = (food: string) => { setPortionRecord(null); expansion.action(`choose:food:${food}`, go, back, open); expansion.action('choose:portion:By amount', go, back, open); expansion.field('amount', '1'); expansion.field('grams', ''); };
  const action = (value: string) => {
    if (value === 'noop') return;
    Keyboard.dismiss();
    if (value.startsWith('open-portion:')) {
      const context = portionFromAction(value);
      if (!context) { open({ title: 'Portion unavailable', description: 'Open a supported food record from History.' }); return; }
      setFood(context.food); setPortionRecord(context);
      expansion.action('choose:portion:By weight', go, back, open); expansion.field('grams', String(context.grams));
      go('portion-confirmation'); return;
    }
    if (value.startsWith('choose:mobility:')) store.update(old => ({ ...old, profile: { ...old.profile, mobility: value.endsWith(':Limited') ? 'Limited' : 'None' } }));
    if (value === 'sign-out') { open({ title: 'Sign out of the demo?', description: 'Your local demo records remain on this device.', choices: [{ label: 'Sign out', action: () => { setSignedIn(false); expansion.field('password', ''); go('sign-in'); } }] }); return; }
    if (value === 'my-reports') { if (expansion.state.reportSubmitted) go('report-status'); else open({ title: 'No reports yet', description: 'Reports you submit from a result or the Assistant appear here.', choices: [{ label: 'Report a result', action: () => go('report-output') }] }); return; }
    if (value === 'provider-info') { open({ title: 'Apple Health', description: 'This connection is simulated. No HealthKit access or real provider data is requested.', choices: [{ label: store.state.connected ? 'Disconnect demo source' : 'Connect demo source', action: () => store.update(old => ({ ...old, connected: !old.connected })) }] }); return; }
    if (value === 'reading-unit') { open({ title: 'Display unit', choices: ['mg/dL', 'mmol/L'].map(unit => ({ label: unit, selected: sceneState.choices.unit === unit, action: () => { expansion.action(`choose:unit:${unit}`, go, back, open); store.update(old => ({ ...old, profile: { ...old.profile, glucoseUnit: unit } })); } })) }); return; }
    if (value.startsWith('choose:unit:')) store.update(old => ({ ...old, profile: { ...old.profile, glucoseUnit: value.slice(12) } }));
    const preference = { 'profile-diet': 'dietary', 'profile-allergens': 'allergens', 'profile-activity': 'activity' }[value] as 'dietary' | 'allergens' | 'activity' | undefined;
    if (preference) { open({ title: preference === 'dietary' ? 'Dietary Preferences' : preference === 'allergens' ? 'Allergens' : 'Activity Preferences', fields: [{ key: preference, label: 'Preference', value: store.state.profile[preference] }], save: values => { if (!values[preference]?.trim()) return 'Enter your preference, or None.'; store.update(old => ({ ...old, profile: { ...old.profile, [preference]: values[preference].trim() } })); }, choices: preference === 'activity' ? [{ label: 'Review foot support', action: () => go('foot-questionnaire') }] : undefined }); return; }
    if (value === 'save-meal' || value === 'draft-meal') {
      const result = mealResult(sceneState, value === 'draft-meal');
      if (!result.meal) { open({ title: 'Check portion', description: result.error }); return; }
      const meal = result.meal; const id = `journey-${Date.now()}-${Math.random().toString(36).slice(2)}`; let saved = false;
      open({ title: meal.draft ? 'Save this draft?' : 'Confirm meal', description: `${meal.food} · ${Math.round(meal.grams)} g · ≈ ${meal.calories} cal\n${meal.draft ? 'Drafts are not marked as consumed.' : 'Values are sample estimates.'}`, choices: [{ label: meal.draft ? 'Save draft' : portionRecord?.id && !portionRecord.draft ? 'Update confirmed meal' : 'Log confirmed meal', action: () => { if (saved) return; saved = true; store.update(old => ({ ...old, ...savePortionRecord(old, nativeRecord(meal, id, new Date().toISOString()), meal.draft ? 'draft' : 'consumed', portionRecord) })); setPortionRecord(null); dispatch({ type: 'reset', route: 'personal-history' }); } }] }); return;
    }
    if (value === 'export') { open({ title: 'Export local demo records', description: 'Preview your local records as JSON. Nothing is sent to a server.', fields: [{ key: 'json', label: 'Session export', value: JSON.stringify({ readings: sceneState.readings, meals: sceneState.meals, report: sceneState.reportSubmitted ? { id: 'DEMO-104', reason: sceneState.choices.reason } : null }, null, 2), multiline: true }] }); return; }
    if (value === 'retained') { open({ title: 'Retained records', description: `${sceneState.readings.length} manual readings, ${sceneState.meals.length} meal entries.`, choices: [{ label: 'Clear local records', action: () => open({ title: 'Clear local demo records?', description: 'This clears the local demo preferences, readings and meal entries.', choices: [{ label: 'Confirm clear records', action: () => { store.reset(); expansion.reset(); setSignedIn(false); } }] }) }] }); return; }
    const destination = (next: AppRoute) => {
      if (next === 'add-reading' && value !== 'new-reading' && value !== 'edit-reading') { expansion.action('new-reading', go, back, open); return; }
      if (value === 'choose-photo' && next === 'analysis-result') setFood('Apple');
      if (value === 'go:portion-confirmation' || value === 'go:log-meal') setPortionRecord(null);
      if (value === 'sign-in' && next === 'flow-directory') { home(); return; }
      if (value === 'create-account' && next === 'verify-email') store.update(old => ({ ...old, profile: { ...old.profile, name: expansion.state.fields.name.trim(), email: expansion.state.fields.email.trim() } }));
      if (value === 'review-reading' && next === 'reading-detail' || value === 'review-report' && next === 'report-status' || value === 'create-plan' && next === 'plan-rationale') dispatch({ type: 'replace', route: next });
      else go(next);
    };
    const flowSheet = (sheet: Sheet) => {
      if (value === 'sign-in' && sheet.title === 'Frontend demo') { setSignedIn(true); store.update(old => ({ ...old, profile: { ...old.profile, email: expansion.state.fields.email.trim() } })); sheet.choices?.[0].action(); return; }
      const save = sheet.save;
      open({ ...sheet, choices: sheet.choices?.map(choice => ({ ...choice, label: choice.label === 'Explore all flows' ? 'Back to settings' : choice.label })), save: save ? values => { const error = save(values); if (!error && value === 'delete-account') { store.reset(); setSignedIn(false); } return error; } : undefined });
    };
    expansion.action(value, destination, back, flowSheet);
  };
  const props = { store, go, back, home, open };
  const content = route === 'flow-directory' ? <ScreenDirectory go={go} back={back} action={action} signedIn={signedIn} />
    : (extensionRoutes as readonly string[]).includes(route) ? <ExpandedScreen key={`${route}-${navigationToken}`} route={route as ExtensionRoute} state={sceneState} profile={store.state.profile} connected={store.state.connected} editingMeal={!!portionRecord?.id && !portionRecord.draft} field={expansion.field} action={action} go={go} back={back} />
    : route === 'home' ? <Home {...props} /> : route === 'scan' ? <Scan {...props} />
    : route === 'log-meal' ? <LogMeal key={`${route}-${history.length}`} {...props} portion={applePortion} updatePortion={setApplePortion} /> : route === 'weekly-plan' ? <WeeklyPlan {...props} />
    : route === 'profile' ? <Profile {...props} /> : <Onboarding {...props} />;
  return <View style={{ flex: 1 }}><View style={{ flex: 1 }}>{content}</View>{showTabs(route) && <TabBar route={route} navigate={next => { Keyboard.dismiss(); if (next === 'glucose-overview') expansion.action(`choose:unit:${store.state.profile.glucoseUnit}`, go, back, open); dispatch({ type: 'tab', route: next }); }} />}</View>;
}
