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
