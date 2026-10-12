// G4.5 ripeness chip (unripe / ripe / overripe). EXACT mirror of ml/grading/ripeness.py
// (parity: native/tests/cvRipeness.test.ts replays ml/eval/fixtures/ripeness_parity.json).
// Separate from fresh/rotten and never merged into the A/B/C grade until human graders validate a mapping.
import type { CvObject } from '../contracts.ts';

export const RIPENESS_STAGES = ['unripe', 'ripe', 'overripe'] as const;
export const RIPENESS_CLASSES = ['banana', 'mango', 'tomato', 'guava'];
export type RipenessParams = { minConfidence: number; minMargin: number; includeCitrus: boolean };
export const DEFAULT_RIPENESS: RipenessParams = { minConfidence: 0.6, minMargin: 0.15, includeCitrus: false };

export function ripenessFromProbs(className: string, probs: number[], params: Partial<RipenessParams> = {}): CvObject['ripeness'] | null {
  const p = { ...DEFAULT_RIPENESS, ...params };
  const allowed = p.includeCitrus ? [...RIPENESS_CLASSES, 'citrus'] : RIPENESS_CLASSES;
  if (!allowed.includes(className)) return null;
  if (probs.length !== RIPENESS_STAGES.length || probs.some((v) => !(v >= 0 && v <= 1))) return { stage: 'unknown', status: 'unknown' };
  const order = [0, 1, 2].sort((a, b) => probs[b] - probs[a] || a - b);
  const top = probs[order[0]];
  const second = probs[order[1]];
  const confidence = Math.round(top * 10000) / 10000;
  if (top < p.minConfidence || top - second < p.minMargin) return { stage: 'unknown', status: 'unknown', confidence };
  return { stage: RIPENESS_STAGES[order[0]], status: 'assessed', confidence };
}
