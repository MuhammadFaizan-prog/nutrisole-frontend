import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { DEFAULT_CITRUS_AMBIGUITY, citrusDisplayLabel, decodeRawWithNms, decodeRawWithNmsCitrus, isCitrusAmbiguous } from '../src/cv/pipeline/postprocess.ts';

type Fx = { cases: Array<{ top: number; scores: number[]; ratio: number; expected: boolean }> };
const fx = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/citrus_parity.json', import.meta.url), 'utf8')) as Fx;

test('citrus ambiguity rule matches the Python reference', () => {
  for (const c of fx.cases) assert.equal(isCitrusAmbiguous(c.top, c.scores, { ratio: c.ratio }), c.expected);
});

test('default is OFF and the OFF path equals decodeRawWithNms', () => {
  assert.equal(DEFAULT_CITRUS_AMBIGUITY.enabled, false);
  const nc = 12, n = 3;
  const raw = new Float32Array((4 + nc) * n);
  const put = (j: number, box: number[], scores: Record<number, number>) => {
    box.forEach((v, k) => { raw[k * n + j] = v; });
    for (const [c, s] of Object.entries(scores)) raw[(4 + Number(c)) * n + j] = s;
  };
  put(0, [100, 100, 50, 50], { 6: 0.8, 3: 0.6 }); // lemon with strong citrus second score
  put(1, [300, 300, 40, 40], { 3: 0.9, 6: 0.1 }); // clear citrus
  put(2, [200, 50, 30, 30], { 0: 0.7, 3: 0.69 }); // banana: never ambiguous
  assert.deepEqual(decodeRawWithNmsCitrus(raw, nc, n, 0.25), decodeRawWithNms(raw, nc, n, 0.25));
  const on = decodeRawWithNmsCitrus(raw, nc, n, 0.25, { enabled: true, ratio: 0.5 });
  const byCls = new Map(on.map((d) => [d.classId, d]));
  assert.equal(byCls.get(6)?.citrusAmbiguous, true);
  assert.equal(byCls.get(3)?.citrusAmbiguous, undefined);
  assert.equal(byCls.get(0)?.citrusAmbiguous, undefined);
  assert.equal(citrusDisplayLabel('Lemon / lime', true), 'citrus (lemon/orange?)');
  assert.equal(citrusDisplayLabel('Lemon / lime', false), 'Lemon / lime');
});
