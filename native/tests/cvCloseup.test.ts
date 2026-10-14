// G9 Stage G: close-up path + price display parity with the Python reference (ml/eval/closeup.py, ml/prices/display.py).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  detectorToFrame, cropRect, roiFromTap, idPolicy, qualityReasons, GradeGate, FROZEN_GATE, DEFAULT_GATE, blockiness, touchesEdge, gateMessage,
  type GateParams, type QualityInputs, type Assessment,
} from '../src/cv/pipeline/closeup.ts';
import { computeTransform, srcToDst, type Box } from '../src/cv/pipeline/preprocess.ts';
import { categoryPrice, gradedPrice, PRICE_LABEL } from '../src/cv/prices/display.ts';
import type { PriceSource } from '../src/cv/prices/reference.ts';

const F = JSON.parse(readFileSync(new URL('../../ml/eval/fixtures/closeup_parity.json', import.meta.url), 'utf8'));
const close = (a: number, b: number, eps = 1e-6) => Math.abs(a - b) <= eps;

test('frozen gate equals the Python frozen gate', () => {
  for (const [k, v] of Object.entries(F.gate as GateParams)) assert.equal((FROZEN_GATE as Record<string, unknown>)[k], v, k);
  assert.equal(FROZEN_GATE.minSidePx, 96); assert.equal(FROZEN_GATE.minFrames, 3);
});

test('480 detector box -> full-res frame pixels matches Python and inverts preprocess.srcToDst', () => {
  for (const c of F.mapping) {
    const out = detectorToFrame(c.box as Box, c.W, c.H);
    out.forEach((v, i) => assert.ok(close(v, c.out[i], 1e-6), `${c.W}x${c.H} ${i}: ${v} vs ${c.out[i]}`));
    // round trip through the existing letterbox transform (unclipped boxes only)
    const t = computeTransform(c.W, c.H, 480, 480, 'letterbox');
    const back = srcToDst(out, t);
    const inside = out[0] > 0 && out[1] > 0 && out[2] < c.W && out[3] < c.H;
    if (inside) back.forEach((v, i) => assert.ok(close(v, c.box[i], 1e-6)));
  }
});

test('a 12 px detector box on a 4K frame is ~96 px of real pixels (why the gate uses frame pixels)', () => {
  const fb = detectorToFrame([200, 200, 212, 212], 3840, 2160);
  const cr = cropRect(fb, 3840, 2160);
  assert.ok(cr.sidePx >= 95 && cr.sidePx <= 97, String(cr.sidePx));
});

test('crop rectangle, edge test and ROI match Python', () => {
  for (const c of F.crop) assert.deepEqual(cropRect(c.box, c.W, c.H), c.out);
  for (const c of F.edge) assert.equal(touchesEdge(c.box, c.W, c.H, 0.01), c.out);
  for (const c of F.roi) {
    const r = roiFromTap(c.tap, c.W, c.H, c.boxes);
    assert.equal(r.source, c.out.source);
    r.box.forEach((v, i) => assert.ok(close(v, c.out.box[i])));
  }
});

test('ROI fallback: tap with no track gives a square user ROI inside the frame', () => {
  const r = roiFromTap([0.99, 0.01], 1920, 1080, []);
  assert.equal(r.source, 'tap_roi');
  assert.ok(r.box[0] >= 0 && r.box[1] >= 0 && r.box[2] <= 1920 && r.box[3] <= 1080);
  assert.ok(close(r.box[2] - r.box[0], 0.35 * 1080));
});

test('identification policy: "Unable to identify" instead of a forced label', () => {
  for (const c of F.id) assert.deepEqual(idPolicy(c.args[0], c.args[1], c.args[2], c.args[3]), c.out);
  assert.equal(idPolicy(1, 0.49, 10).status, 'unable');
  assert.equal(idPolicy(3, 0.99, 10, true).status, 'unable');
});

test('quality checks match Python', () => {
  for (const c of F.quality) assert.deepEqual(qualityReasons(c.q as QualityInputs, FROZEN_GATE), c.out);
});

test('quality checks: each degradation alone yields Not graded; confidence alone never grades', () => {
  const good: QualityInputs = { sidePx: 200, blurVar: 300, meanV: 150, touchesEdge: false, visibleFrac: 0.6, maxProb: 0.99, margin: 0.98, blockiness: 1.05 };
  assert.deepEqual(qualityReasons(good, FROZEN_GATE), []);
  const bad: Array<[Partial<QualityInputs>, string]> = [
    [{ sidePx: 95 }, 'too_small: move closer'], [{ blurVar: 10 }, 'blurry'], [{ meanV: 60 }, 'too_dark'], [{ meanV: 250 }, 'overexposed'],
    [{ touchesEdge: true }, 'truncated: keep the whole item in view'], [{ visibleFrac: 0.2 }, 'occluded_or_little_surface'],
    [{ maxProb: 0.6 }, 'model_uncertain'], [{ margin: 0.1 }, 'model_uncertain'], [{ blockiness: 2.0 }, 'compression_artifacts'],
  ];
  for (const [patch, reason] of bad) assert.deepEqual(qualityReasons({ ...good, ...patch, maxProb: patch.maxProb ?? 0.999 }, FROZEN_GATE), [reason]);
  // a tiny crop with a very confident model is still refused
  assert.ok(qualityReasons({ ...good, sidePx: 24, maxProb: 1, margin: 1 }, FROZEN_GATE).includes('too_small: move closer'));
});

test('grade gate sequences match Python (count and score modes)', () => {
  for (const s of F.gate_seqs) {
    const g = new GradeGate({ ...FROZEN_GATE, mode: s.mode });
    for (const st of s.seq) assert.deepEqual(g.push(st.a as Assessment), st.out);
  }
});

test('grade gate: 3 agreeing frames grade; disagreement or a failed frame resets; messages', () => {
  const g = new GradeGate(FROZEN_GATE);
  const A = (grade: string, ok = true): Assessment => ({ ok, grade, pFresh: 0.9, reasons: ok ? [] : ['too_small: move closer'] });
  assert.equal(g.push(A('B')).status, 'pending'); assert.equal(g.push(A('B')).status, 'pending');
  assert.deepEqual(g.push(A('B')), { status: 'graded', grade: 'B' });
  assert.equal(g.push(A('A')).status, 'pending');
  const ng = g.push(A('A', false)); assert.equal(ng.status, 'not_graded'); assert.equal(gateMessage(ng), 'Move closer to check quality');
  assert.equal(gateMessage({ status: 'not_graded', reasons: ['blurry'] }), 'Could not be graded reliably');
  assert.equal(DEFAULT_GATE.minSidePx, 96);
});

test('blockiness matches Python', () => {
  for (const c of F.block) assert.ok(close(blockiness(c.gray, c.w, c.h), c.out, 1e-4), `${blockiness(c.gray, c.w, c.h)} vs ${c.out}`);
});

test('price display contract matches Python and never invents or relabels a price', () => {
  const S = F.price_sources as PriceSource[];
  for (const c of F.price) {
    const out = c.fn === 'category' ? categoryPrice(c.args[0], c.args[1], S, c.args[2]) : gradedPrice(c.args[0], c.args[1], c.args[2], S, c.args[3]);
    assert.deepEqual(out, c.out, JSON.stringify(c.args));
    if (out.show) {
      const l = out.line;
      assert.ok(l.source && l.listDate && l.location && l.unit, 'source, date, location and unit are always present');
      assert.equal(l.label, PRICE_LABEL);
      assert.ok(!/seller|worth|value of this|your price|offer/i.test(l.text), l.text);
    }
  }
  assert.equal(categoryPrice(false, 'apple', S, '2026-10-14').show, false);
  assert.equal(categoryPrice(true, 'pomegranate_unknown', S, '2026-10-14').show, false);
  assert.equal(categoryPrice(true, 'apple', S, '2026-10-20').show, false, 'stale list is not shown as current');
  assert.equal(gradedPrice(true, 'apple', 'Reject', S, '2026-10-14').show, false);
});

import { toCvAssessment } from '../src/cv/pipeline/closeup.ts';
import { validateCvAssessment } from '../src/cv/contracts.ts';
import { V1_CLASSES } from '../src/cv/models/labels.ts';

test('close-up results validate against the existing CvAssessment contract (API/DB interface)', () => {
  const ids = V1_CLASSES.map((c) => c.classId); const labels = V1_CLASSES.map((c) => c.en);
  const base = { assessmentId: 'a1', frameTimestampMs: 10, modelVersion: 'G3+E224', rubricVersion: 'rubric-v0.2-g2', frameW: 1920, frameH: 1080, box: [100, 100, 400, 380] as Box, classIds: ids, labels };
  const cases = [
    toCvAssessment({ ...base, id: { status: 'identified', classId: 1 }, decision: { status: 'graded', grade: 'A' } }),
    toCvAssessment({ ...base, id: { status: 'identified', classId: 1 }, decision: { status: 'not_graded', reasons: ['too_small: move closer'] } }),
    toCvAssessment({ ...base, id: { status: 'identified', classId: 7 }, decision: { status: 'not_graded', reasons: ['blurry', 'model_uncertain'] }, blurVar: 9 }),
    toCvAssessment({ ...base, id: { status: 'unable', reason: 'low confidence' }, decision: { status: 'not_graded', reasons: [] } }),
  ];
  for (const a of cases) { const v = validateCvAssessment(a); assert.ok(v.ok, JSON.stringify(v)); }
  assert.equal(cases[0].objects[0].visualGrade?.grade, 'A');
  assert.equal(cases[1].objects[0].visualGrade?.grade, 'ungradable');
  assert.equal(cases[3].objects.length, 0);
  assert.ok(!JSON.stringify(cases).toLowerCase().includes('rs '), 'no price inside the assessment');
});
