import type { AppRoute } from '../../src/nutrisole/types';
export type DirectoryScreen = { route: AppRoute; label: string };
export const screenGroups: { title: string; screens: DirectoryScreen[] }[] = [
  { title: 'Main screens', screens: [
    { route: 'onboarding', label: 'Onboarding' }, { route: 'home', label: 'Home' },
    { route: 'scan', label: 'Scan food' }, { route: 'log-meal', label: 'Log meal' },
    { route: 'weekly-plan', label: 'Weekly plan' }, { route: 'profile', label: 'Profile & preferences' },
  ] },
  { title: 'Accounts', screens: [
    { route: 'sign-in', label: 'Sign in' }, { route: 'create-account', label: 'Create account' },
    { route: 'verify-email', label: 'Verify email' }, { route: 'recover-account', label: 'Recover account' },
    { route: 'reset-password', label: 'Reset password' },
  ] },
  { title: 'Food assessment', screens: [
    { route: 'analysis-result', label: 'Analysis result' }, { route: 'market-reference', label: 'Market reference' },
    { route: 'capture-retry', label: 'Retry capture' }, { route: 'food-selector', label: 'Choose a food' },
    { route: 'nutrition-details', label: 'Nutrition details' }, { route: 'portion-confirmation', label: 'Confirm portion' },
  ] },
  { title: 'Health & connections', screens: [
    { route: 'glucose-overview', label: 'Glucose overview' }, { route: 'add-reading', label: 'Add a reading' },
    { route: 'reading-detail', label: 'Reading details' }, { route: 'health-connections', label: 'Health connections' },
  ] },
  { title: 'Planning & foot support', screens: [
    { route: 'plan-generation', label: 'Build a plan' }, { route: 'activity-plan', label: 'Activity plan' },
    { route: 'plan-rationale', label: 'Plan rationale' }, { route: 'foot-questionnaire', label: 'Foot questionnaire' },
    { route: 'foot-guidance', label: 'Foot guidance' },
  ] },
  { title: 'Assistant', screens: [{ route: 'assistant', label: 'Nutrition assistant' }] },
  { title: 'Privacy & reminders', screens: [
    { route: 'privacy-data-rights', label: 'Privacy & data rights' }, { route: 'reminders', label: 'Reminders' },
  ] },
  { title: 'Reports & history', screens: [
    { route: 'report-output', label: 'Report output' }, { route: 'report-status', label: 'Report status' },
    { route: 'personal-history', label: 'Personal history' },
  ] },
  { title: 'Staff workspace', screens: [
    { route: 'catalog-queue', label: 'Catalog queue' }, { route: 'catalog-review', label: 'Catalog review' },
    { route: 'model-release', label: 'Model release' }, { route: 'operations-audit', label: 'Operations audit' },
    { route: 'report-triage', label: 'Report triage' },
  ] },
  { title: 'App navigation', screens: [{ route: 'flow-directory', label: 'Menu & settings' }] },
];
export const directoryScreens = screenGroups.flatMap(group => group.screens);
