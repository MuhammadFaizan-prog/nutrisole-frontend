import assert from 'node:assert/strict';
import { test } from 'node:test';
import { extensionRoutes } from '../../src/nutrisole/extensions/model.ts';
import { canonicalRoute, navigationReducer, sectionForRoute, showTabs, taskLinks, settingsGroups, journeyGraph, type NavigationState } from '../responsive/navigation.ts';

test('task controls connect all 38 screens from onboarding without a screen catalog', () => {
  const seen = new Set<string>();
  const queue = ['onboarding'];
  while (queue.length) {
    const route = queue.shift()!;
    if (seen.has(route)) continue;
    seen.add(route);
    queue.push(...(journeyGraph()[route] || []).filter(next => !seen.has(next)));
  }
  const expected = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile', ...extensionRoutes];
  assert.deepEqual([...seen].sort(), expected.sort());
  assert.ok(settingsGroups.flatMap(group => group.items).length < 20, 'Settings must be a task menu, not a 38-screen catalog');
  assert.ok(!settingsGroups.flatMap(group => group.items).some(item => /all screens|verify|reset password|reading details|nutrition details/i.test(item.label)));
});

test('food, plan and health features have contextual entry points', () => {
  assert.deepEqual(taskLinks('weekly-plan').map(item => item.route), ['plan-generation', 'plan-rationale', 'activity-plan']);
  assert.ok(taskLinks('glucose-overview').some(item => item.route === 'foot-questionnaire'));
  assert.ok(journeyGraph().scan.includes('analysis-result'));
  assert.ok(journeyGraph()['analysis-result'].includes('food-selector'));
  assert.ok(journeyGraph()['nutrition-details'].includes('portion-confirmation'));
  assert.ok(journeyGraph()['portion-confirmation'].includes('personal-history'));
});

test('contextual back returns to its parent and primary tab changes do not stack tabs', () => {
  const state: NavigationState = { route: 'home', history: [] };
  const health = navigationReducer(state, { type: 'tab', route: 'glucose-overview' });
  const add = navigationReducer(health, { type: 'push', route: 'add-reading' });
  const details = navigationReducer(add, { type: 'push', route: 'reading-detail' });
  assert.equal(navigationReducer(details, { type: 'back' }).route, 'add-reading');
  const profile = navigationReducer(details, { type: 'tab', route: 'profile' });
  assert.deepEqual(profile.history, []);
  assert.equal(navigationReducer(profile, { type: 'back' }).route, 'home');
  assert.equal(navigationReducer(profile, { type: 'push', route: 'profile' }), profile);
});

test('legacy destinations retain their primary section and detail forms remain focused', () => {
  assert.equal(canonicalRoute('health'), 'glucose-overview');
  assert.equal(canonicalRoute('history'), 'personal-history');
  assert.equal(sectionForRoute('reading-detail'), 'glucose-overview');
  assert.equal(sectionForRoute('plan-rationale'), 'weekly-plan');
  assert.equal(sectionForRoute('flow-directory'), 'profile');
  assert.equal(showTabs('add-reading'), false);
  assert.equal(showTabs('create-account'), false);
  assert.equal(showTabs('home'), true);
  assert.equal(showTabs('profile'), true);
});
test('editing a saved reading keeps its detail parent and retake uses an explicit return intent', () => {
  const health: NavigationState = { route: 'glucose-overview', history: [] };
  const add = navigationReducer(health, { type: 'push', route: 'add-reading' });
  const saved = navigationReducer(add, { type: 'replace', route: 'reading-detail' });
  const edit = navigationReducer(saved, { type: 'push', route: 'add-reading' });
  assert.equal(navigationReducer(edit, { type: 'back' }).route, 'reading-detail');
  const revisit = navigationReducer({ route: 'reading-detail', history: ['glucose-overview', 'add-reading'] }, { type: 'push', route: 'add-reading' });
  assert.equal(navigationReducer(revisit, { type: 'back' }).route, 'reading-detail');
  const retry = navigationReducer({ route: 'capture-retry', history: ['home', 'scan'] }, { type: 'popTo', route: 'scan' });
  assert.deepEqual(retry, { route: 'scan', history: ['home'] });
});
