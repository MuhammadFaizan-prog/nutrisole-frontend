import { test } from 'node:test';
import assert from 'node:assert/strict';
import { screenGroups, directoryScreens } from '../responsive/directoryManifest.ts';
import { extensionRoutes } from '../../src/nutrisole/extensions/model.ts';

test('the route registry retains every one of the 40 canonical screens exactly once (38 + 2 glucose import screens)', () => {
  const expected = ['onboarding', 'home', 'scan', 'log-meal', 'weekly-plan', 'profile', ...extensionRoutes];
  assert.equal(directoryScreens.length, 40);
  assert.equal(new Set(directoryScreens.map(screen => screen.route)).size, 40);
  assert.deepEqual(directoryScreens.map(screen => screen.route).sort(), [...expected].sort());
  assert.ok(screenGroups.every(group => group.screens.length && group.title));
  assert.ok(directoryScreens.every(screen => screen.label.trim().length > 2));
});
