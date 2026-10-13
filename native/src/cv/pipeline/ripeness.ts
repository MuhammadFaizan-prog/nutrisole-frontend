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

// G7.1 per-fruit ripeness head (optional, config DEFAULT OFF). EXACT mirror of ml/grading/ripeness.py ripeness_per_fruit
// (parity: native/tests/cvRipeness.test.ts replays ml/eval/fixtures/ripeness_perfruit_parity.json).
// Model classes "<fruit>_<stage>"; the detector class selects its fruit's stages (conditional softmax). 'unknown' = the app's
// "unable to assess": classifier mass on that fruit < minFruitMass, or top < minConfidence / margin < minMargin.
export type PerFruitParams = { enabled: boolean; minFruitMass: number; minConfidence: number; minMargin: number; fruitMap: Record<string, string> };
export const DEFAULT_PERFRUIT: PerFruitParams = { enabled: false, minFruitMass: 0.5, minConfidence: 0.6, minMargin: 0.15, fruitMap: { citrus: 'orange' } };
const r4 = (v: number): number => Math.round(v * 10000) / 10000;

export function ripenessPerFruit(className: string, modelClasses: string[], probs: number[], params: Partial<PerFruitParams> = {}): CvObject['ripeness'] | null {
  const p = { ...DEFAULT_PERFRUIT, ...params };
  if (!p.enabled) return null;
  const fruit = p.fruitMap[className] ?? className;
  const idx = RIPENESS_STAGES.map((s) => modelClasses.indexOf(`${fruit}_${s}`));
  if (idx.every((i) => i < 0)) return null;
  if (probs.length !== modelClasses.length || probs.some((v) => !(v >= 0 && v <= 1))) return { stage: 'unknown', status: 'unknown' };
  const sp = idx.map((i) => (i >= 0 ? probs[i] : 0));
  const mass = sp[0] + sp[1] + sp[2];
  if (mass < p.minFruitMass) return { stage: 'unknown', status: 'unknown', confidence: r4(mass) };
  const cp = sp.map((v) => v / mass);
  const order = [0, 1, 2].sort((a, b) => cp[b] - cp[a] || a - b);
  const top = cp[order[0]];
  const second = cp[order[1]];
  if (top < p.minConfidence || top - second < p.minMargin) return { stage: 'unknown', status: 'unknown', confidence: r4(top) };
  return { stage: RIPENESS_STAGES[order[0]], status: 'assessed', confidence: r4(top) };
}
