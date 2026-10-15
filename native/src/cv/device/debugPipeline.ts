// G9 Stage J5: the debug CV pipeline for the phone test (P1), pure and dependency-injected so it is unit-tested in Node.
// Burst of upright stills -> G3 detector (480 letterbox) on each -> wide identity by the FROZEN id policy (idMinHits 3 = 3 stills agreeing
// on the tapped item, idMinScore 0.5) -> tap crop on the last still (detector box containing the tap, else tap ROI) -> H2 close-up ->
// verifyIdentity(FROZEN_VERIFY, policy P-a) -> stageHDecision(grades disabled) -> fromStageH -> DisplayResult (title only).
// The quality gate and occlusion cues are NOT run here, so the outcome is at best "<name>. Not graded" with the reason
// `quality_gate_not_run_in_debug`. No grade, no confidence and no FPS is ever produced for the screen.
import { h2Input, MODEL_IO, type Size } from '../pipeline/camera.ts';
import { detectorToFrame, idPolicy, DEFAULT_ID, type IdResult } from '../pipeline/closeup.ts';
import { decodeRawWithNms } from '../pipeline/postprocess.ts';
import { verifyIdentity, stageHDecision, FROZEN_VERIFY, H2_CLASSES, type VerifyResult } from '../pipeline/verify.ts';
import { fromStageH, checkDisplayResult, type DisplayResult } from '../pipeline/result.ts';
import type { Box } from '../pipeline/preprocess.ts';
import type { Detection } from '../pipeline/tracker.ts';
import { V1_CLASSES } from '../models/labels.ts';
import { cropRgb, detectorInput, asProbs } from './pixels.ts';
import { planTapOnUprightStill } from './orientation.ts';
import type { StillCropPlan } from '../pipeline/camera.ts';
import { domainOf } from './instrument.ts';
import type { DomainId } from '../domainMap.ts';

export type UprightStill = { rgb: Uint8Array; w: number; h: number };
export type Infer = (model: 'h2' | 'g3_det', input: Float32Array, dims: number[]) => Promise<Float32Array>;
export const DET_DECODE_FLOOR = 0.25;   // decode floor only; naming still needs idMinScore 0.5 and 3 agreeing stills
export const BURST = DEFAULT_ID.idMinHits;
const NC = 12; const N_ANCHORS = 4725;

export type DebugOutcome = {
  display: DisplayResult; displayErrors: string[]; wide: IdResult; verify: VerifyResult | null; plan: StillCropPlan | null;
  detections: Detection[][]; tappedPerStill: (number | null)[]; logLines: string[];
  /** J6: always 'real' here (this function only returns after running the injected models); the screen decides the badge. */
  inference: 'real';
  /** J6: canonical domain id via domainMap.ts (citrus -> citrus_orange); null when not identified. */
  domain: { cvClass: string | null; domainId: DomainId | null };
};

const contains = (b: Box, x: number, y: number) => b[0] <= x && x <= b[2] && b[1] <= y && y <= b[3];
const area = (b: Box) => (b[2] - b[0]) * (b[3] - b[1]);
export const labelOf = (classId: number) => V1_CLASSES[classId]?.en ?? 'Item';

/** Smallest detection containing the normalised tap point, or null. */
export function tappedDetection(dets: Detection[], tapN: [number, number], w: number, h: number): Detection | null {
  const hit = dets.filter((d) => contains(d.box, tapN[0] * w, tapN[1] * h));
  return hit.length ? hit.reduce((a, b) => (area(b.box) < area(a.box) ? b : a)) : null;
}

/** Wide identity from a burst: hits = stills whose tapped detection has the modal class; score = the lowest of those scores. */
export function burstWide(tapped: (Detection | null)[]): IdResult {
  const ok = tapped.filter((d): d is Detection => d !== null);
  if (!ok.length) return { status: 'unable', reason: 'nothing_detected_at_tap' };
  const counts = new Map<number, number>(); ok.forEach((d) => counts.set(d.classId, (counts.get(d.classId) ?? 0) + 1));
  const [cls, hits] = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
  const score = Math.min(...ok.filter((d) => d.classId === cls).map((d) => d.score));
  return idPolicy(cls, score, hits);
}

export async function runDebugPipeline(stills: UprightStill[], tap: [number, number], view: Size, infer: Infer,
  now: () => number = () => Date.now()): Promise<DebugOutcome> {
  if (!stills.length) throw new Error('no stills');
  const log: string[] = []; const detections: Detection[][] = []; const tapped: (Detection | null)[] = [];
  const last = stills[stills.length - 1];
  const plan0 = planTapOnUprightStill(tap, view, [last.w, last.h], []);
  if (!plan0) {
    const display = fromStageH(stageHDecision({ status: 'unable', reason: 'tap_outside_image', suggestions: [] }, [], 'not_run', []), labelOf);
    return { display, displayErrors: checkDisplayResult(display), wide: { status: 'unable', reason: 'tap_outside_image' }, verify: null, plan: null, detections, tappedPerStill: [], logLines: log, inference: 'real', domain: domainOf(null) };
  }
  for (const s of stills) {
    const t0 = now();
    const out = await infer('g3_det', detectorInput(s.rgb, s.w, s.h), MODEL_IO.g3_det.inputs[0].shape as number[]);
    if (out.length !== (4 + NC) * N_ANCHORS) throw new Error(`detector output ${out.length} != ${(4 + NC) * N_ANCHORS}`);
    const dets = decodeRawWithNms(out, NC, N_ANCHORS, DET_DECODE_FLOOR).map((d) => ({ ...d, box: detectorToFrame(d.box, s.w, s.h) }));
    detections.push(dets);
    const td = tappedDetection(dets, plan0.framePoint, s.w, s.h); tapped.push(td);
    log.push(`NSCV stage=det ms=${now() - t0}`);
  }
  const wide = burstWide(tapped);
  const plan = planTapOnUprightStill(tap, view, [last.w, last.h], detections[detections.length - 1].map((d) => d.box));
  if (!plan) throw new Error('plan lost');
  const crop = cropRgb(last.rgb, last.w, last.h, plan.crop);
  const t1 = now();
  const probs = asProbs(await infer('h2', h2Input(crop.rgb, crop.w, crop.h), [1, 3, 224, 224]));
  if (probs.length !== H2_CLASSES.length) throw new Error(`h2 output ${probs.length} != ${H2_CLASSES.length}`);
  log.push(`NSCV stage=h2 ms=${now() - t1}`);
  const v = verifyIdentity(wide, null, probs, FROZEN_VERIFY);
  const o = stageHDecision(v, [], 'not_run', ['quality_gate_not_run_in_debug'], false);
  const display = fromStageH(o, labelOf);
  return { display, displayErrors: checkDisplayResult(display), wide, verify: v, plan, detections, tappedPerStill: tapped.map((d) => d?.classId ?? null), logLines: log, inference: 'real', domain: domainOf(v) };
}

// ---- G9 Stage J8: close-up path for LIVE mode. The wide identity comes from the live track (trackWide over the last 3 live frames,
// the unchanged DEFAULT_ID policy); ONE high-resolution photo is captured for the H2 crop (never a preview-resolution crop). The
// verification is the unchanged FROZEN_VERIFY P-a; grades stay blocked. Returns the same DebugOutcome plus the close-up diagnostics.
export type CloseupDiag = { g3AtTap: { classId: number; score: number } | null; h2Top3: { classId: number; p: number }[]; agree: boolean | null; cropSidePx: number; cropW: number; cropH: number };
export function h2Top3(probs: readonly number[]): { classId: number; p: number }[] {
  return probs.map((p, i) => ({ classId: i, p: Math.round(p * 1e4) / 1e4 })).sort((a, b) => b.p - a.p || a.classId - b.classId).slice(0, 3);
}
export async function runCloseupFromTrack(still: UprightStill, tap: [number, number], view: Size, wide: IdResult, infer: Infer,
  now: () => number = () => Date.now()): Promise<DebugOutcome & { closeup: CloseupDiag | null }> {
  const log: string[] = [];
  const t0 = now();
  const out = await infer('g3_det', detectorInput(still.rgb, still.w, still.h), MODEL_IO.g3_det.inputs[0].shape as number[]);
  if (out.length !== (4 + NC) * N_ANCHORS) throw new Error(`detector output ${out.length} != ${(4 + NC) * N_ANCHORS}`);
  const dets = decodeRawWithNms(out, NC, N_ANCHORS, DET_DECODE_FLOOR).map((d) => ({ ...d, box: detectorToFrame(d.box, still.w, still.h) }));
  log.push(`NSCV stage=closeup_det ms=${now() - t0}`);
  const plan = planTapOnUprightStill(tap, view, [still.w, still.h], dets.map((d) => d.box));
  if (!plan) {
    const display = fromStageH(stageHDecision({ status: 'unable', reason: 'tap_outside_image', suggestions: [] }, [], 'not_run', []), labelOf);
    return { display, displayErrors: checkDisplayResult(display), wide, verify: null, plan: null, detections: [dets], tappedPerStill: [], logLines: log, inference: 'real', domain: domainOf(null), closeup: null };
  }
  const td = tappedDetection(dets, plan.framePoint, still.w, still.h);
  const crop = cropRgb(still.rgb, still.w, still.h, plan.crop);
  const t1 = now();
  const probs = asProbs(await infer('h2', h2Input(crop.rgb, crop.w, crop.h), [1, 3, 224, 224]));
  if (probs.length !== H2_CLASSES.length) throw new Error(`h2 output ${probs.length} != ${H2_CLASSES.length}`);
  log.push(`NSCV stage=h2 ms=${now() - t1}`);
  const v = verifyIdentity(wide, null, probs, FROZEN_VERIFY);
  const o = stageHDecision(v, [], 'not_run', ['quality_gate_not_run_in_debug'], false);
  const display = fromStageH(o, labelOf);
  const top = h2Top3(probs);
  const closeup: CloseupDiag = { g3AtTap: td ? { classId: td.classId, score: Math.round(td.score * 1e4) / 1e4 } : null, h2Top3: top,
    agree: wide.status === 'identified' ? top[0].classId === wide.classId : null, cropSidePx: Math.round(plan.sidePx), cropW: crop.w, cropH: crop.h };
  return { display, displayErrors: checkDisplayResult(display), wide, verify: v, plan, detections: [dets], tappedPerStill: [td?.classId ?? null], logLines: log, inference: 'real', domain: domainOf(v), closeup };
}
