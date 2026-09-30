import test from 'node:test';
import assert from 'node:assert/strict';
import { edibleMass, energyForMass, recordMeal } from '../src/nutrisole/domain.ts';

test('confirmed portions use edible grams and round only displayed energy', () => {
  assert.equal(edibleMass('amount', 2), 364);
  assert.equal(edibleMass('weight', 91), 91);
  assert.equal(energyForMass(91), 48);
  assert.equal(edibleMass('size', 1, 'small'), 149);
});
test('invalid portions cannot become plausible nutrition', () => {
  for (const value of [0, -1, NaN, Infinity]) {
    assert.throws(() => edibleMass('amount', value), /positive/);
    assert.throws(() => energyForMass(value), /positive/);
  }
});
test('saving for later does not add a consumed meal', () => {
  const state = recordMeal({ meals: [], drafts: [] }, { id: 'a', submissionKey: 'a', grams: 182, calories: 95, createdAt: 'demo' }, 'draft');
  assert.equal(state.meals.length, 0);
  assert.equal(state.drafts.length, 1);
});
test('a repeated consumed submission is idempotent', () => {
  const meal = { id: 'a', submissionKey: 'same', grams: 182, calories: 95, createdAt: 'demo' };
  const once = recordMeal({ meals: [], drafts: [] }, meal, 'consumed');
  const twice = recordMeal(once, { ...meal, id: 'b' }, 'consumed');
  assert.equal(twice.meals.length, 1);
  assert.equal(twice.meals[0].calories, 95);
});
test('logging a saved portion preserves its quantity and removes its draft', () => {
  const meal = { id: 'saved', submissionKey: 'saved', grams: 364, calories: 190, createdAt: 'demo' };
  const draft = recordMeal({ meals: [], drafts: [] }, meal, 'draft');
  const logged = recordMeal(draft, meal, 'consumed');
  assert.deepEqual(logged.meals, [meal]);
  assert.equal(logged.drafts.length, 0);
});
