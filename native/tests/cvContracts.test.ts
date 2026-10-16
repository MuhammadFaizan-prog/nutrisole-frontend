import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { validateCvAssessment, type CvAssessment } from '../src/cv/contracts.ts';
import { V1_CLASSES } from '../src/cv/models/labels.ts';
import { decodeEndToEnd, decodeRawWithNms } from '../src/cv/pipeline/postprocess.ts';

const good: CvAssessment = {
  assessmentId: 'a1', frameTimestampMs: 1234, modelVersion: 'det-yolo26n-v1@sha', rubricVersion: 'rubric-v0.1-g1', status: 'supported',
  imageQuality: { blur: 120, lighting: 'ok', reasons: [] },
  objects: [{ trackingId: 't1', bboxNormalized: [0.1, 0.2, 0.5, 0.6], produce: { classId: 'apple', label: 'Apple', calibratedConfidence: 0.91 },
    visibleDefects: [{ type: 'dark_area', areaPercent: 4.2 }], visualGrade: { grade: 'B', reasons: ['Small dark marks ~4% of visible surface'] } }],
  limitations: ['Visible condition only'],
};

test('valid assessment passes; absent optional fields are fine', () => {
  assert.equal(validateCvAssessment(good).ok, true);
  const minimal = { assessmentId: 'x', frameTimestampMs: 0, modelVersion: 'm', rubricVersion: 'r', status: 'unsupported', objects: [], limitations: [] };
  assert.equal(validateCvAssessment(minimal).ok, true);
});

test('invalid shapes, out-of-range numbers and safety claims are rejected', () => {
  const bad = (patch: (a: any) => void) => { const a = structuredClone(good) as any; patch(a); return validateCvAssessment(a); };
  for (const r of [
    bad((a) => { a.status = 'great'; }),
    bad((a) => { a.objects[0].bboxNormalized = [0.5, 0.2, 0.1, 0.6]; }),
    bad((a) => { a.objects[0].bboxNormalized = [0, 0, 1.2, 1]; }),
    bad((a) => { a.objects[0].produce.calibratedConfidence = 97; }),
    bad((a) => { a.objects[0].visualGrade.grade = 'A+'; }),
    bad((a) => { a.objects[0].visualGrade.reasons = ['Safe to eat']; }),
    bad((a) => { a.objects[0].visibleDefects[0].areaPercent = 140; }),
    bad((a) => { a.objects = []; }),
    bad((a) => { delete a.modelVersion; }),
  ]) assert.equal(r.ok, false);
  assert.equal(validateCvAssessment(null).ok, false);
});

test('class order equals ml/data/class_map.csv and the detector config', () => {
  const csv = readFileSync(new URL('../../ml/data/class_map.csv', import.meta.url), 'utf8').trim().split('\n').slice(1).map((l) => l.split(','));
  const v1 = csv.filter((r) => r[0] === 'nutrisole').map((r) => [Number(r[4]), r[3]]);
  assert.deepEqual(v1, V1_CLASSES.map((c) => [c.id, c.classId]));
  const yaml = readFileSync(new URL('../../ml/configs/det_v1.yaml', import.meta.url), 'utf8');
  for (const c of V1_CLASSES) assert.ok(yaml.includes(`  ${c.id}: ${c.classId}`), c.classId);
});

test('decoders: end-to-end (N,300,6) and raw (4+nc,N) with class-wise NMS', () => {
  const e2e = new Float32Array(300 * 6);
  e2e.set([10, 10, 50, 50, 0.9, 1], 0);
  e2e.set([60, 60, 90, 90, 0.2, 3], 6);
  const d = decodeEndToEnd(e2e, 300, 0.25);
  assert.equal(d.length, 1);
  assert.deepEqual([d[0].classId, d[0].box], [1, [10, 10, 50, 50]]);
  const nc = 2, n = 3;
  const raw = new Float32Array((4 + nc) * n);
  const put = (j: number, cx: number, cy: number, w: number, h: number, s0: number, s1: number) => {
    raw[j] = cx; raw[n + j] = cy; raw[2 * n + j] = w; raw[3 * n + j] = h; raw[4 * n + j] = s0; raw[5 * n + j] = s1;
  };
  put(0, 30, 30, 40, 40, 0.9, 0.1);
  put(1, 31, 31, 40, 40, 0.8, 0.1); // duplicate of 0 -> suppressed
  put(2, 31, 31, 40, 40, 0.1, 0.7); // other class, same place -> kept (class-wise)
  const r = decodeRawWithNms(raw, nc, n, 0.25);
  assert.deepEqual(r.map((x) => x.classId), [0, 1]);
});
