import { test } from 'node:test';
import assert from 'node:assert/strict';
import { viewport, typography, cameraFrameHeight, cameraNeedsScroll, largeTextLayout, homeActionsLayout, weekStripLayout } from '../responsive/metrics.ts';

test('safe viewport excludes asymmetric iPhone insets exactly once', () => {
  const frame = viewport(390, 844, { top: 59, bottom: 34, left: 0, right: 0 });
  assert.equal(frame.height, 751);
  assert.equal(frame.width, 390);
});
test('Android side/system bars leave a usable compact viewport', () => {
  const frame = viewport(360, 640, { top: 24, bottom: 48, left: 8, right: 8 });
  assert.equal(frame.width, 344);
  assert.equal(frame.height, 568);
  assert.equal(frame.compact, true);
});
test('a short phone or visible keyboard does not compress typography', () => {
  assert.deepEqual(typography(390, 844), typography(390, 300));
  assert.ok(typography(320, 568).body >= 16);
});
test('camera framing clears measured instructions and detection on a short phone', () => {
  assert.equal(cameraFrameHeight(314, 218, 284), 72);
  assert.equal(cameraFrameHeight(630, 267, 285), 267);
  assert.equal(cameraNeedsScroll(314, 284), true);
  assert.equal(cameraNeedsScroll(630, 285), false);
});

test('large system text reserves whole navigation words and a full brand row', () => {
  assert.deepEqual(largeTextLayout(393, 1), { expanded: false, navigationColumns: 5, brandSize: 32 });
  assert.deepEqual(largeTextLayout(430, 1.5), { expanded: false, navigationColumns: 5, brandSize: 32 });
  assert.deepEqual(largeTextLayout(320, 2), { expanded: true, navigationColumns: 3, brandSize: 24 });
  assert.deepEqual(largeTextLayout(430, 2), { expanded: true, navigationColumns: 3, brandSize: 32 });
});

test('Home actions keep two cards at the reference width and stack before labels are cramped', () => {
  assert.equal(homeActionsLayout(353, 1).columns, 2);
  assert.equal(homeActionsLayout(288, 1).columns, 1);
  assert.equal(homeActionsLayout(320, 1).columns, 2);
  assert.equal(homeActionsLayout(320, 1.3).columns, 1);
  assert.equal(homeActionsLayout(390, 1.5).columns, 1);
  for (const width of [288, 320, 350, 372, 390]) {
    assert.equal(homeActionsLayout(width, 2).columns, 1);
  }
});

test('all seven weekdays fit one row on default-text phones and scroll on enlarged text', () => {
  for (const width of [296, 336, 366, 388, 406]) {
    const layout = weekStripLayout(width, 7, 1);
    assert.equal(layout.scroll, false);
    assert.ok(Math.abs(layout.cellWidth * 7 + layout.gap * 6 - width) < .01);
  }
  const enlarged = weekStripLayout(296, 7, 2);
  assert.equal(enlarged.scroll, true);
  assert.ok(enlarged.cellWidth >= 68, 'Weekday labels must retain space for enlarged text');
});
