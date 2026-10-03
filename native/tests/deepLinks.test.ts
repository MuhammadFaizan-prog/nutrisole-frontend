import assert from 'node:assert/strict';
import { test } from 'node:test';
import { routeFromURL } from '../deepLinks.ts';

const screens = ['onboarding', 'home', 'log-meal', 'add-reading'] as const;
test('opens known screens using either supported app link format', () => {
  assert.equal(routeFromURL('nutrisole://screens/log-meal', screens), 'log-meal');
  assert.equal(routeFromURL('nutrisole://add-reading', screens), 'add-reading');
  assert.equal(routeFromURL('nutrisole://home?source=test', screens), 'home');
});
test('ignores external, malformed and unknown links without breaking navigation', () => {
  for (const url of [null, '', 'broken', 'https://screens/home', 'nutrisole://screens/missing', 'nutrisole://screens/home/extra', 'nutrisole://screens/%FF']) {
    assert.equal(routeFromURL(url, screens), null, String(url));
  }
});
test('works in a native runtime without the browser URL implementation', () => {
  const original = globalThis.URL;
  Reflect.deleteProperty(globalThis, 'URL');
  try {
    assert.equal(routeFromURL('nutrisole://screens/home', screens), 'home');
  } finally {
    globalThis.URL = original;
  }
});
