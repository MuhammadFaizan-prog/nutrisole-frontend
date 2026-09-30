import { useEffect, useState, lazy, Suspense } from 'react';
import { Canvas } from './ui';
import { useDemoStore } from './store';
import type { Route, AppRoute, Sheet, Navigation } from './types';
import { extensionRoutes, type ExtensionRoute } from './extensions/model';
import { View } from './primitives';
const ExpansionScreen = lazy(() => import('./extensions/ExpansionScreen'));
import { useExpansion } from './extensions/useExpansion';
import Onboarding from './Onboarding';
import Home from './Home';
import Scan from './Scan';
import LogMeal from './LogMeal';
import WeeklyPlan from './WeeklyPlan';
import Profile from './Profile';
import Secondary from './Secondary';
import { useSystemBack } from './useSystemBack';

export const routes: AppRoute[] = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile', 'health', 'history', ...extensionRoutes];
export default function NutriSole({ width, height, open, requestedRoute = 'onboarding', navigationToken = 0, resetToken = 0, navigation, routeChanged, beforeNavigate }: {
  width: number; height: number; open: (sheet: Sheet) => void; requestedRoute?: AppRoute; navigationToken?: number; resetToken?: number; navigation?: Navigation; routeChanged?: (route: AppRoute) => void; beforeNavigate?: () => void;
}) {
  const store = useDemoStore();
  const expansion = useExpansion();
  const [route, setRoute] = useState<AppRoute>(requestedRoute);
  const [history, setHistory] = useState<AppRoute[]>([]);
  useEffect(() => { beforeNavigate?.(); setHistory([]); setRoute(requestedRoute); }, [requestedRoute, navigationToken]);
  useEffect(() => { if (resetToken) { store.reset(); expansion.reset(); setHistory([]); setRoute(requestedRoute); } }, [resetToken]);
  useEffect(() => routeChanged?.(route), [route]);
  const go = (next: AppRoute) => { beforeNavigate?.(); if (next === route) return; if (navigation) return navigation.go(next); setHistory(old => [...old, route]); setRoute(next); };
  const back = () => { beforeNavigate?.(); if (navigation) return navigation.back(); setRoute(history.at(-1) || 'home'); setHistory(old => old.slice(0, -1)); };
  const home = () => { beforeNavigate?.(); if (navigation) return navigation.home(); setHistory([]); setRoute('home'); };
  useSystemBack(back, route !== 'home' && route !== 'onboarding');
  // Replace only the two former placeholder destinations. The six source screens
  // and their calls to health/history remain unchanged.
  const expandedRoute = route === 'health' ? 'glucose-overview' : route === 'history' ? 'personal-history' : route;
  if ((extensionRoutes as readonly string[]).includes(expandedRoute)) return <Suspense fallback={<View style={{ width, height, backgroundColor: '#faf8f1' }} />}><ExpansionScreen route={expandedRoute as ExtensionRoute} width={width} height={height} state={expansion.state} field={expansion.field} action={value => { if (value !== 'noop') beforeNavigate?.(); expansion.action(value, go, back, open); }} /></Suspense>;
  return <Canvas key={resetToken} width={width} height={height} route={route as Route}>
    {route === 'onboarding' && <Onboarding home={home} />}
    {route === 'home' && <Home go={go} store={store} />}
    {route === 'scan' && <Scan back={back} capture={() => go('log-meal')} open={open} />}
    {route === 'log-meal' && <LogMeal key={`${route}-${history.length}`} back={back} home={home} store={store} open={open} />}
    {route === 'weekly-plan' && <WeeklyPlan back={back} open={open} store={store} />}
    {route === 'profile' && <Profile back={back} open={open} store={store} />}
    {(route === 'health' || route === 'history') && <Secondary route={route} back={back} go={go} store={store} open={open} />}
  </Canvas>;
}
