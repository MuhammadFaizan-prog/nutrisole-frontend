import { useCallback, useEffect, useState } from 'react';
import { storage } from './storage';
import { recordMeal, type Meal, type Records } from './domain';

export const initialProfile = {
  name: 'Alex Chen', email: 'alex.chen@email.com', dietary: 'Balanced, Higher protein', allergens: 'Tree nuts, Shellfish',
  activity: 'Strength training, 3–4 days/week', mobility: 'None', glucoseUnit: 'mg/dL', timezone: '(UTC-8) Pacific Time',
};
export type Profile = typeof initialProfile;
export type DemoState = Records & { version: 1; profile: Profile; connected: boolean; accepted: string[]; substitutes: Record<string, string>; feedback: Record<string, string>; retainImages: boolean };
export const freshState = (): DemoState => ({ version: 1, profile: { ...initialProfile }, connected: true, meals: [], drafts: [], accepted: [], substitutes: {}, feedback: {}, retainImages: false });
function loadState(text: string | null): DemoState {
  try {
    const s = JSON.parse(text || 'null') as DemoState;
    if (s?.version !== 1 || !s.profile || !Object.keys(initialProfile).every(k => typeof s.profile[k as keyof Profile] === 'string') || typeof s.connected !== 'boolean' || !Array.isArray(s.meals) || !Array.isArray(s.drafts) || !Array.isArray(s.accepted) || !s.substitutes || !s.feedback) return freshState();
    return s;
  } catch { return freshState(); }
}
export function useDemoStore() {
  const [state, setState] = useState<DemoState>(freshState);
  const [ready, setReady] = useState(false);
  useEffect(() => { let alive = true; storage.get().then(text => { if (alive) { setState(loadState(text)); setReady(true); } }); return () => { alive = false; }; }, []);
  useEffect(() => { if (ready) void storage.set(JSON.stringify(state)); }, [state, ready]);
  const update = useCallback((fn: (old: DemoState) => DemoState) => setState(fn), []);
  const saveMeal = useCallback((meal: Meal, kind: 'consumed' | 'draft') => update(old => ({ ...old, ...recordMeal(old, meal, kind) })), [update]);
  const reset = useCallback(() => setState(freshState()), []);
  return { state, ready, update, saveMeal, reset };
}
export type Store = ReturnType<typeof useDemoStore>;
