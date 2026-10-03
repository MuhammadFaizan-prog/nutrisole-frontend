import { buildScene, type ExtensionRoute, type ExpansionState } from '../../src/nutrisole/extensions/model.ts';
import type { Profile } from '../../src/nutrisole/store';
import { portionAction, portionRouteFor, type JourneyState } from './journeyData.ts';
export function journeyScene(route: ExtensionRoute, state: ExpansionState, profile?: Profile, connected = false, editingMeal = false) {
  const scene = buildScene(route, state);
  if (route === 'analysis-result') scene.layers.forEach(layer => { if (layer.text === 'Confirm food') layer.action = 'go:nutrition-details'; });
  if (route === 'health-connections') scene.layers.forEach(layer => { if (layer.text === 'Not connected') layer.text = connected ? 'Demo connected' : 'Not connected'; });
  if (route === 'plan-generation' && profile) scene.layers.forEach(layer => {
    if (layer.text === 'Balanced, higher protein') layer.text = profile.dietary;
    if (layer.text === 'Tree nuts, shellfish') layer.text = profile.allergens;
    if (layer.text === 'Strength training') layer.text = profile.activity;
    if (layer.text === 'None reported') layer.text = profile.mobility;
  });
  if (route === 'plan-rationale' && profile) scene.layers.forEach(layer => {
    if (layer.text?.startsWith('Meals match your preferences')) layer.text = `Recorded preference: ${profile.dietary}. The weekly menu is a sample preview.`;
    if (layer.text === 'Declared allergens excluded') layer.text = 'Declared allergens';
    if (layer.text?.startsWith('Tree nuts and shellfish are')) layer.text = `Recorded allergens: ${profile.allergens}. Review ingredients before accepting sample meals.`;
    if (layer.text?.startsWith('None reported. Activity follows') || layer.text?.startsWith('A concern is recorded. Activity is')) layer.text = `${profile.mobility}. ${state.choices.mobility === 'Limited' || state.choices.comfort === 'Concern' ? 'Activity is deferred pending qualified assessment.' : 'Activity follows your recorded preferences.'}`;
    if (layer.text?.startsWith('Your weekly plan is tailored')) layer.text = 'Review the information you have shared. This frontend previews a sample weekly menu.';
  });
  if (route === 'nutrition-details') scene.layers.forEach(layer => { if (layer.action === 'go:portion-confirmation') layer.action = `go:${portionRouteFor(state.choices.food)}`; });
  if (route === 'portion-confirmation' && editingMeal) scene.layers.forEach(layer => { if (layer.action === 'save-meal') layer.text = 'Update meal'; });
  let mealIndex = 0;
  const visibleMeals = (state as JourneyState).meals.filter(meal => state.choices.history === 'All' || state.choices.history === (meal.draft ? 'Food' : 'Meals'));
  if (route === 'personal-history') scene.layers.forEach(layer => {
    if (layer.action !== 'go:portion-confirmation') return;
    const saved = layer.text?.includes('This session') ? visibleMeals[mealIndex++] : undefined;
    const label = scene.layers.find(other => other.kind === 'text' && other.bold && other.y >= layer.y && other.y < layer.y + layer.h);
    layer.action = portionAction(saved ? { food: saved.food, grams: saved.grams, draft: saved.draft, ...(saved.id ? { id: saved.id } : {}) } : { food: label?.text || 'Apple', grams: 182, draft: !!layer.text?.includes('draft') });
  });
  return scene;
}
