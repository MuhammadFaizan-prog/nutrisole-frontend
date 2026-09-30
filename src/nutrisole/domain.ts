export type PortionMode = 'amount' | 'weight' | 'size';
export function edibleMass(mode: PortionMode, value: number, size: 'small' | 'medium' | 'large' = 'medium'): number {
  if (!Number.isFinite(value) || value <= 0) throw new Error('Enter a positive portion.');
  return mode === 'weight' ? value : value * (mode === 'size' ? { small: 149, medium: 182, large: 223 }[size] : 182);
}
export function energyForMass(grams: number): number {
  if (!Number.isFinite(grams) || grams <= 0) throw new Error('Enter a positive edible mass.');
  return Math.round(95 * grams / 182);
}
export type Meal = { id: string; submissionKey: string; grams: number; calories: number; createdAt: string };
export type Records = { meals: Meal[]; drafts: Meal[] };
export function recordMeal(state: Records, meal: Meal, kind: 'consumed' | 'draft'): Records {
  edibleMass('weight', meal.grams);
  const field = kind === 'consumed' ? 'meals' : 'drafts';
  if (state[field].some(item => item.submissionKey === meal.submissionKey)) return state;
  return { ...state, [field]: [...state[field], meal], ...(kind === 'consumed' ? { drafts: state.drafts.filter(item => item.submissionKey !== meal.submissionKey) } : {}) };
}
