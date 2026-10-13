import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { ripenessFromProbs } from '../src/cv/pipeline/ripeness.ts';

type Fx = { cases: Array<{ cls: string; probs: number[]; params: { includeCitrus?: boolean }; expected: unknown }> };
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/ripeness_parity.json', import.meta.url), 'utf8')) as Fx;

test('TypeScript ripeness chip reproduces Python case by case', () => {
  for (const c of fx.cases) assert.deepStrictEqual(ripenessFromProbs(c.cls, c.probs, c.params), c.expected, `${c.cls} ${c.probs}`);
});

test('ripeness is never produced for classes without a ripeness model', () => {
  assert.equal(ripenessFromProbs('potato', [0.9, 0.05, 0.05]), null);
  assert.equal(ripenessFromProbs('citrus', [0.9, 0.05, 0.05]), null);
});

// G7.1 per-fruit head (config default OFF)
import { DEFAULT_PERFRUIT, ripenessPerFruit } from '../src/cv/pipeline/ripeness.ts';
type PFx = { model_classes: string[]; cases: Array<{ cls: string; probs: number[]; params: { enabled?: boolean }; expected: unknown }> };
const pfx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/ripeness_perfruit_parity.json', import.meta.url), 'utf8')) as PFx;

test('per-fruit ripeness head reproduces Python case by case', () => {
  for (const c of pfx.cases) assert.deepStrictEqual(ripenessPerFruit(c.cls, pfx.model_classes, c.probs, c.params), c.expected, `${c.cls} ${c.probs}`);
});

test('per-fruit head is OFF by default and returns "unable to assess" when the classifier disagrees on the fruit', () => {
  assert.equal(DEFAULT_PERFRUIT.enabled, false);
  const C = pfx.model_classes;
  const probs = C.map((c) => (c === 'mango_ripe' ? 0.9 : 0.1 / (C.length - 1)));
  assert.equal(ripenessPerFruit('banana', C, probs), null);
  assert.deepStrictEqual(ripenessPerFruit('banana', C, probs, { enabled: true })?.status, 'unknown');
  assert.deepStrictEqual(ripenessPerFruit('mango', C, probs, { enabled: true })?.stage, 'ripe');
  assert.equal(ripenessPerFruit('potato', C, probs, { enabled: true }), null);
});
