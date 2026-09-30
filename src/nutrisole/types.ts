export type Route = 'onboarding' | 'home' | 'scan' | 'log-meal' | 'weekly-plan' | 'profile' | 'health' | 'history';
export type AppRoute = Route | import('./extensions/model').ExtensionRoute;
export type Navigation = { go: (next: AppRoute) => void; back: () => void; home: () => void };
export type SheetField = { key: string; label: string; value: string; multiline?: boolean; numeric?: boolean };
export type Sheet = {
  title: string; description?: string; fields?: SheetField[];
  choices?: { label: string; action: () => void; selected?: boolean }[];
  save?: (values: Record<string, string>) => string | void;
};
