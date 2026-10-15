// G9 Stage J4: debug flag is off by default; NSCV lines match the PowerShell parser and never carry a grade or confidence.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { setCvDebug, cvDebugEnabled, nscv, nscvMapLine, nscvStageLine, nscvResultLine } from '../src/cv/debug.ts';
import { stillCropPlan } from '../src/cv/pipeline/camera.ts';
import { demoResult } from '../src/cv/pipeline/result.ts';

test('flag defaults off; nothing is logged until enabled', () => {
  assert.equal(cvDebugEnabled(), false);
  const got: string[] = []; setCvDebug(false, (l) => got.push(l));
  assert.equal(nscv('NSCV x'), null); assert.equal(got.length, 0);
  setCvDebug(true); assert.equal(nscv('NSCV y'), 'NSCV y'); assert.deepEqual(got, ['NSCV y']); setCvDebug(false);
});

test('map / stage / result lines match the g9i-device-check.ps1 regexes', () => {
  const plan = stillCropPlan([206, 457], [412, 915], [1920, 1080], [4032, 3024], [], 90)!;
  const m = nscvMapLine([206, 457], plan, [4032, 3024], 90, false);
  assert.match(m, /^NSCV map tap=[\d.]+,[\d.]+ frame=[\d.]+,[\d.]+ still=4032x3024 crop=\d+,\d+,\d+,\d+ src=\w+ rot=90 mirror=0$/);
  assert.match(nscvStageLine('h2', 12.3456), /NSCV.*stage=(\w+).*ms=([\d.]+)/);
  const res = nscvResultLine(demoResult('Apple'));
  assert.match(res, /event=(\w+)/); assert.match(res, /grade=none/); assert.doesNotMatch(res, /\d+\s?%/);
});
