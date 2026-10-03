import type { AppRoute } from '../../src/nutrisole/types';
import { extensionRoutes, initialExpansionState } from '../../src/nutrisole/extensions/model.ts';
import { journeyScene } from './journeyScene.ts';
import { portionFromAction } from './journeyData.ts';

export type TaskLink = { label: string; description?: string; icon: string; route: AppRoute };
export type MenuItem = Omit<TaskLink, 'route'> & { route?: AppRoute; action?: 'staff-workspace' };
export const primaryTabs: { label: string; route: AppRoute }[] = [
  { label: 'Home', route: 'home' }, { label: 'Plan', route: 'weekly-plan' },
  { label: 'Scan', route: 'scan' }, { label: 'Health', route: 'glucose-overview' }, { label: 'Profile', route: 'profile' },
];
export function canonicalRoute(route: AppRoute): AppRoute {
  return route === 'health' ? 'glucose-overview' : route === 'history' ? 'personal-history' : route;
}
export function showTabs(route: AppRoute) { return ['home', 'weekly-plan', 'glucose-overview', 'profile', 'flow-directory'].includes(canonicalRoute(route)); }
export function sectionForRoute(route: AppRoute): AppRoute {
  const next = canonicalRoute(route);
  if (['weekly-plan', 'plan-generation', 'plan-rationale', 'activity-plan'].includes(next)) return 'weekly-plan';
  if (['glucose-overview', 'add-reading', 'reading-detail', 'health-connections', 'foot-questionnaire', 'foot-guidance'].includes(next)) return 'glucose-overview';
  if (['profile', 'flow-directory', 'privacy-data-rights', 'reminders', 'sign-in', 'create-account', 'verify-email', 'recover-account', 'reset-password'].includes(next)) return 'profile';
  return 'home';
}
const links: Partial<Record<AppRoute, TaskLink[]>> = {
  'weekly-plan': [
    { label: 'Build a plan', description: 'Use your preferences', icon: 'CalendarDays', route: 'plan-generation' },
    { label: 'Why this plan?', description: 'Review the plan inputs', icon: 'Info', route: 'plan-rationale' },
    { label: 'Weekly activity', description: 'Movement and progress', icon: 'Activity', route: 'activity-plan' },
  ],
  'glucose-overview': [
    { label: 'Foot support', description: 'Fit, comfort and mobility', icon: 'Footprints', route: 'foot-questionnaire' },
    { label: 'Weekly activity', description: 'Review your movement plan', icon: 'Activity', route: 'activity-plan' },
  ],
  'activity-plan': [{ label: 'Foot support', description: 'Review fit and movement', icon: 'Footprints', route: 'foot-questionnaire' }],
};
export function taskLinks(route: AppRoute): TaskLink[] { return links[canonicalRoute(route)] || []; }
export const settingsGroups: { title: string; items: MenuItem[] }[] = [
  { title: 'Your tools', items: [
    { label: 'History', description: 'Food, meals and saved plans', icon: 'NotebookText', route: 'personal-history' },
    { label: 'NutriSole Assistant', description: 'Food and plan questions', icon: 'MessageSquare', route: 'assistant' },
    { label: 'Foot support', description: 'Fit, comfort and mobility', icon: 'Footprints', route: 'foot-questionnaire' },
    { label: 'Weekly activity', description: 'Your movement plan', icon: 'Activity', route: 'activity-plan' },
  ] },
  { title: 'Account & preferences', items: [
    { label: 'Profile & preferences', description: 'Diet, allergens and personal details', icon: 'UserRound', route: 'profile' },
    { label: 'Sign in', description: 'Or create an account', icon: 'LockKeyhole', route: 'sign-in' },
    { label: 'Reminders', description: 'Schedule and quiet hours', icon: 'Bell', route: 'reminders' },
    { label: 'Health connections', description: 'Sources and sharing preferences', icon: 'Heart', route: 'health-connections' },
    { label: 'Privacy & data', description: 'Consent, records and export', icon: 'Shield', route: 'privacy-data-rights' },
  ] },
  { title: 'Help & feedback', items: [
    { label: 'Report a result', description: 'Request a review of an output', icon: 'FileClock', route: 'report-output' },
    { label: 'My report', description: 'View your submitted report', icon: 'NotebookText', route: 'report-status' },
    { label: 'Getting started', description: 'NutriSole introduction', icon: 'Leaf', route: 'onboarding' },
  ] },
  { title: 'Staff preview', items: [{ label: 'Staff workspace', description: 'Synthetic curator and admin workflows', icon: 'Settings', action: 'staff-workspace' }] },
];
export type NavigationState = { route: AppRoute; history: AppRoute[] };
export type NavigationEvent = { type: 'push' | 'tab' | 'replace' | 'reset' | 'popTo'; route: AppRoute } | { type: 'back' };
export function navigationReducer(state: NavigationState, event: NavigationEvent): NavigationState {
  if (event.type === 'back') return { route: state.history.at(-1) || (state.route === 'onboarding' ? 'onboarding' : 'home'), history: state.history.slice(0, -1) };
  const route = canonicalRoute(event.route);
  if (event.type === 'reset' || event.type === 'tab' && route !== 'scan') return { route, history: [] };
  if (route === state.route) return state;
  if (event.type === 'replace') return { route, history: state.history };
  const earlier = event.type === 'popTo' ? state.history.lastIndexOf(route) : -1;
  return { route, history: earlier < 0 ? [...state.history, state.route] : state.history.slice(0, earlier) };
}
/** Dynamic destinations belong to the named actions' actual confirmation sheets. */
const actionDestinations: Record<string, AppRoute[]> = {
  'sign-in': ['home'], 'create-account': ['verify-email'], recover: ['reset-password', 'sign-in'],
  'reset-password': ['sign-in'], resend: ['sign-in'], 'verify-demo': ['sign-in'],
  evidence: ['food-selector', 'report-output'], 'choose-photo': ['analysis-result', 'capture-retry'],
  'new-reading': ['add-reading'], 'review-reading': ['reading-detail'], 'latest-reading': ['reading-detail'], 'edit-reading': ['add-reading'],
  permissions: ['add-reading', 'privacy-data-rights'], 'profile-activity': ['foot-questionnaire'],
  'create-plan': ['plan-rationale', 'foot-guidance'], 'review-foot': ['foot-guidance'],
  'delete-account': ['sign-in'], 'save-preferences': ['reminders', 'flow-directory'],
  'review-report': ['report-status'], 'triage-save': ['report-status'],
  'save-meal': ['personal-history'], 'draft-meal': ['personal-history'],
  'staff-workspace': ['catalog-queue', 'model-release', 'operations-audit', 'report-triage'],
};
export function journeyGraph(): Record<string, AppRoute[]> {
  const graph: Record<string, AppRoute[]> = {
    onboarding: ['home', 'create-account', 'sign-in'],
    home: ['scan', 'weekly-plan', 'glucose-overview', 'profile', 'flow-directory', 'personal-history'],
    scan: ['analysis-result', 'capture-retry'], 'log-meal': ['home', 'nutrition-details'],
    profile: ['flow-directory', 'privacy-data-rights', 'health-connections'], 'weekly-plan': [],
  };
  for (const route of extensionRoutes) {
    graph[route] = route === 'flow-directory' ? settingsGroups.flatMap(group => group.items.flatMap(item => item.route ? [item.route] : actionDestinations[item.action!] || []))
      : ['Apple', 'Banana', 'Tomato'].flatMap(food => {
        const state = initialExpansionState(); state.choices.food = food;
        return journeyScene(route, state).layers.flatMap(layer => layer.action?.startsWith('go:') ? [canonicalRoute(layer.action.slice(3) as AppRoute)] : portionFromAction(layer.action || '') ? ['portion-confirmation' as AppRoute] : actionDestinations[layer.action || ''] || []);
      });
  }
  for (const route of Object.keys(graph) as AppRoute[]) {
    graph[route].push(...taskLinks(route).map(item => item.route));
    if (showTabs(route)) graph[route].push(...primaryTabs.map(tab => tab.route));
    graph[route] = [...new Set(graph[route])];
  }
  return graph;
}
