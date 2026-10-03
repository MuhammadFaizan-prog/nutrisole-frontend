import type { AppRoute, Sheet } from '../src/nutrisole/types';
export function withNativeDestinations(sheet: Sheet, go: (route: AppRoute) => void): Sheet {
  const destinations: { label: string; route: AppRoute }[] = sheet.title === 'Privacy & Consent'
    ? [{ label: 'Privacy and data controls', route: 'privacy-data-rights' }]
    : sheet.title === 'Your profile' ? [{ label: 'Account & settings', route: 'flow-directory' }] : [];
  if (!destinations.length) return sheet;
  return { ...sheet, choices: [...(sheet.choices || []), ...destinations.map(({ label, route }) => ({ label, action: () => go(route) }))] };
}
