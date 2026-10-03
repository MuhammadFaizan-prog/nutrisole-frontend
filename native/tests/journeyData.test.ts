import assert from 'node:assert/strict';
import { test } from 'node:test';
import { initialExpansionState, buildScene } from '../../src/nutrisole/extensions/model.ts';
import { sceneStateFor, nativeRecord, portionFromAction, portionRouteFor, savePortionRecord, mealCarbs } from '../responsive/journeyData.ts';
import { journeyScene } from '../responsive/journeyScene.ts';

test('original and assessment meals share history while drafts stay unconsumed', () => {
  const original = { id: 'original', submissionKey: 'original', grams: 182, calories: 95, createdAt: '2026-10-03T00:00:00Z' };
  const banana = nativeRecord({ food: 'Banana', grams: 118, calories: 105, draft: false }, 'banana', original.createdAt);
  const draft = nativeRecord({ food: 'Tomato', grams: 123, calories: 22, draft: true }, 'draft', original.createdAt);
  const state = sceneStateFor(initialExpansionState(), { meals: [original, banana], drafts: [draft] });
  assert.deepEqual(state.meals.map(meal => [meal.food, meal.calories, meal.draft]), [['Apple', 95, false], ['Banana', 105, false], ['Tomato', 22, true]]);
  assert.equal(banana.submissionKey, 'banana');
});
test('assessment can continue directly while correction remains available through evidence', () => {
  const original = buildScene('analysis-result');
  const adapted = journeyScene('analysis-result', initialExpansionState());
  assert.ok(original.layers.some(layer => layer.text === 'Confirm food' && layer.action === 'go:food-selector'));
  assert.ok(adapted.layers.some(layer => layer.text === 'Confirm food' && layer.action === 'go:nutrition-details'));
  assert.ok(adapted.layers.some(layer => layer.action === 'evidence'));
});
test('opening a history portion carries the food belonging to that row', () => {
  const state = initialExpansionState();
  state.choices.food = 'Banana';
  const scene = journeyScene('personal-history', state);
  assert.ok(scene.layers.some(layer => portionFromAction(layer.action || '')?.food === 'Apple'));
  assert.ok(!scene.layers.some(layer => layer.action === 'go:portion-confirmation'));
});
test('saved draft context retains its record and measured portion when reopened', () => {
  const record = nativeRecord({ food: 'Tomato', grams: 500, calories: 90, draft: true }, 'saved-draft', '2026-10-03T00:00:00Z');
  const state = sceneStateFor(initialExpansionState(), { meals: [], drafts: [record] });
  const scene = journeyScene('personal-history', state);
  const row = scene.layers.find(layer => layer.text === 'Open Saved draft · This session');
  assert.ok(row);
  assert.deepEqual(portionFromAction(row.action!), { id: 'saved-draft', food: 'Tomato', grams: 500, draft: true });
});
test('fresh Apple captures keep the original Log Meal route reachable after other foods are logged', () => {
  assert.equal(portionRouteFor('Apple'), 'log-meal');
  assert.equal(portionRouteFor('Banana'), 'portion-confirmation');
  assert.equal(portionRouteFor('Tomato'), 'portion-confirmation');
});
test('plan explanations reflect edited dietary, allergen and mobility inputs', () => {
  const profile = { name: 'Alex', email: 'alex@example.com', dietary: 'Vegan', allergens: 'Peanuts', activity: 'Walking', mobility: 'Limited', glucoseUnit: 'mg/dL', timezone: 'Pacific Time' };
  const scene = journeyScene('plan-rationale', initialExpansionState(), profile);
  const text = scene.layers.map(layer => layer.text || '').join('\n');
  assert.ok(text.includes('Vegan') && text.includes('Peanuts') && text.includes('Limited'));
  assert.ok(!text.includes('higher protein diet') && !text.includes('Tree nuts and shellfish are'));
});
test('consuming a saved draft retains its quantity and identity without duplicating the entry', () => {
  const draft = nativeRecord({ food: 'Tomato', grams: 500, calories: 90, draft: true }, 'draft-500', '2026-10-03T00:00:00Z');
  const context = { food: 'Tomato', grams: 500, draft: true, id: draft.id };
  const saved = savePortionRecord({ meals: [], drafts: [draft] }, { ...draft, id: 'new', submissionKey: 'new' }, 'consumed', context);
  assert.equal(saved.drafts.length, 0);
  assert.deepEqual(saved.meals, [draft]);
  const edited = savePortionRecord(saved, { ...draft, grams: 200, calories: 36 }, 'consumed', { ...context, draft: false });
  assert.equal(edited.meals.length, 1);
  assert.equal(edited.meals[0].grams, 200);
  const updatedDraft = savePortionRecord({ meals: [], drafts: [draft] }, { ...draft, grams: 250, calories: 45 }, 'draft', context);
  assert.equal(updatedDraft.drafts[0].grams, 250);
  assert.equal(updatedDraft.drafts.length, 1);
});
test('mixed-food carbohydrate totals use each food composition', () => {
  const tomato = nativeRecord({ food: 'Tomato', grams: 123, calories: 22, draft: false }, 'tomato', 'now');
  const banana = nativeRecord({ food: 'Banana', grams: 118, calories: 105, draft: false }, 'banana', 'now');
  assert.ok(Math.abs(mealCarbs([tomato, banana]) - (4.797 + 26.904)) < .001);
});
test('history contexts reject malformed or unsupported food data', () => {
  for (const value of ['open-portion:Apple', 'open-portion:%7Bbad', 'open-portion:%7B%22food%22:%22Unknown%22%7D']) assert.equal(portionFromAction(value), null);
});
