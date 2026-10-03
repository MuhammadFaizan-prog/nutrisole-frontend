import type { Meal, Records } from '../../src/nutrisole/domain';
import type { ExpansionState } from '../../src/nutrisole/extensions/model';
import { foodInfo } from '../../src/nutrisole/extensions/model.ts';
import { recordMeal } from '../../src/nutrisole/domain.ts';
export type NativeMeal = Meal & { food?: string };
export type PortionContext = { food: string; grams: number; draft: boolean; id?: string };
export type JourneyState = Omit<ExpansionState, 'meals'> & { meals: (ExpansionState['meals'][number] & { id?: string })[] };
export function nativeRecord(meal: ExpansionState['meals'][number], id: string, createdAt: string): NativeMeal {
  return { id, submissionKey: id, food: meal.food, grams: meal.grams, calories: meal.calories, createdAt };
}
export function sceneStateFor(state: ExpansionState, records: Records): JourneyState {
  return { ...state, meals: [...state.meals, ...records.meals.map(meal => ({ id: meal.id, food: (meal as NativeMeal).food || 'Apple', grams: meal.grams, calories: meal.calories, draft: false })), ...records.drafts.map(meal => ({ id: meal.id, food: (meal as NativeMeal).food || 'Apple', grams: meal.grams, calories: meal.calories, draft: true }))] };
}
export function portionAction(context: PortionContext) { return `open-portion:${encodeURIComponent(JSON.stringify(context))}`; }
export function portionFromAction(action: string): PortionContext | null {
  if (!action.startsWith('open-portion:')) return null;
  try {
    const value = JSON.parse(decodeURIComponent(action.slice(13))) as PortionContext;
    if (!['Apple', 'Banana', 'Tomato'].includes(value.food) || !Number.isFinite(value.grams) || value.grams <= 0 || typeof value.draft !== 'boolean' || value.id !== undefined && typeof value.id !== 'string') return null;
    return { food: value.food, grams: value.grams, draft: value.draft, ...(value.id ? { id: value.id } : {}) };
  } catch { return null; }
}
export function portionRouteFor(food: string) { return food === 'Apple' ? 'log-meal' as const : 'portion-confirmation' as const; }
/** Updating a saved portion is distinct from submitting a new meal. */
export function savePortionRecord(records: Records, meal: NativeMeal, kind: 'consumed' | 'draft', context: PortionContext | null): Records {
  const source = context?.draft ? records.drafts : records.meals;
  const previous = context?.id ? source.find(record => record.id === context.id) : undefined;
  if (!previous || !context || !context.draft && kind === 'draft') return recordMeal(records, meal, kind);
  const updated = { ...meal, id: previous.id, submissionKey: previous.submissionKey, createdAt: previous.createdAt };
  if (context.draft && kind === 'consumed') return recordMeal(records, updated, kind);
  const key = kind === 'draft' ? 'drafts' : 'meals';
  return { ...records, [key]: records[key].map(record => record.id === previous.id ? updated : record) };
}
export function mealCarbs(meals: NativeMeal[]) { return meals.reduce((total, meal) => total + Number(foodInfo(meal.food || 'Apple').carbs) * meal.grams / 100, 0); }
