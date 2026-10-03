import assert from 'node:assert/strict';
import { test } from 'node:test';
import { withNativeDestinations } from '../nativeMenu.ts';

test('privacy sheets lead to data controls while preserving existing choices', () => {
  const visited: string[] = [];
  let retained = false;
  const original = { title: 'Privacy & Consent', choices: [{ label: 'Existing choice', action: () => { retained = true; } }] };
  const menu = withNativeDestinations(original, route => visited.push(route));
  assert.equal(original.choices.length, 1);
  menu.choices?.[0].action();
  assert.ok(retained);
  const explore = menu.choices?.find(choice => choice.label === 'Privacy and data controls');
  assert.ok(explore);
  explore.action();
  assert.deepEqual(visited, ['privacy-data-rights']);
});
test('preserves profile editing and leads to account settings', () => {
  const visited: string[] = [];
  const save = () => undefined;
  const original = { title: 'Your profile', fields: [{ key: 'name', label: 'Name', value: 'Alex' }], save };
  const menu = withNativeDestinations(original, route => visited.push(route));
  assert.equal(menu.save, save);
  assert.equal(menu.fields, original.fields);
  menu.choices?.find(choice => choice.label === 'Account & settings')?.action();
  assert.deepEqual(visited, ['flow-directory']);
});
test('leaves other native sheets untouched', () => {
  const sheet = { title: 'Apple nutrition' };
  assert.equal(withNativeDestinations(sheet, () => {}), sheet);
});
