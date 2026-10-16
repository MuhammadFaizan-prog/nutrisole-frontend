// G9 Stage J9 (cv-gauntlet-device): the FROZEN G3 scene guard applied to every user-facing device detection path (live frames,
// the live close-up photo and the optional tap-3 burst). Nothing here re-implements or tunes the policy: it calls sceneGuard() /
// DEFAULT_SCENE_GUARD from pipeline/postprocess.ts unchanged (minAreaFrac 0.01; maxSameClass 0 = rule 2 off since G4), which is the
// exact mirror of ml/eval/scene_guard.py (parity fixture ml/eval/fixtures/scene_guard_parity.json).
//
// Coordinate space = the one ml/eval/video_gauntlet.py uses: detector box -> undo the 480 letterbox (detectorToFrame) -> pixels of
// the ORIGINAL upright image / frame -> divide by that image's width and height -> normalised [0,1] box -> sceneGuard. Callers pass
// boxes that are already in upright original-image pixels (after rotation, letterbox removal and scaling) and that image's size.
// The live path's buffer is a uniform (aspect-preserving) scale of the camera frame, so its per-axis normalisation is identical to
// normalising by the full camera frame. The on-screen preview crop ("cover") is NOT used: the guard is relative to the full frame,
// as in the eval.
//
// A suppressed detection gets: no box, no label, not tappable, never confirmed, never fed to the tracker as a hit.
import type { Box } from '../pipeline/preprocess.ts';
import type { Detection } from '../pipeline/tracker.ts';
import { sceneGuard, DEFAULT_SCENE_GUARD, type SceneGuardParams } from '../pipeline/postprocess.ts';
import { DEFAULT_ID } from '../pipeline/closeup.ts';
import { iou } from '../pipeline/preprocess.ts';

export type Suppressed<D extends Detection = Detection> = D & { areaFrac: number; reason: 'below_min_area' | 'same_class_scene' };
export type GuardResult<D extends Detection = Detection> = { kept: D[]; suppressed: Suppressed<D>[]; frame: [number, number]; params: SceneGuardParams };

/** Normalised box (frame-fraction coords) of an original-image pixel box. */
export const normBox = (b: Box, w: number, h: number): Box => [b[0] / w, b[1] / h, b[2] / w, b[3] / h];
/** Box area as a fraction of the original image, computed exactly as sceneGuard computes it on the normalised box. */
export const areaFracOf = (b: Box, w: number, h: number): number => { const n = normBox(b, w, h); return (n[2] - n[0]) * (n[3] - n[1]); };

/** Apply the frozen sceneGuard to detections whose boxes are in upright ORIGINAL-image pixels of a w x h image.
 *  Kept detections are returned unchanged (same objects, same order, pixel boxes). */
export function guardFrame<D extends Detection>(dets: D[], w: number, h: number, params: Partial<SceneGuardParams> = {}): GuardResult<D> {
  if (!(w > 0) || !(h > 0)) throw new Error(`guardFrame: bad image size ${w}x${h}`);
  const P: SceneGuardParams = { ...DEFAULT_SCENE_GUARD, ...params };
  const norm = dets.map((d, i) => ({ box: normBox(d.box, w, h), classId: d.classId, score: d.score, i }));
  const keptIdx = new Set((sceneGuard(norm, P) as typeof norm).map((d) => d.i));
  const kept: D[] = []; const suppressed: Suppressed<D>[] = [];
  dets.forEach((d, i) => {
    if (keptIdx.has(i)) { kept.push(d); return; }
    const a = (norm[i].box[2] - norm[i].box[0]) * (norm[i].box[3] - norm[i].box[1]);
    suppressed.push({ ...d, areaFrac: a, reason: a < P.minAreaFrac ? 'below_min_area' : 'same_class_scene' });
  });
  return { kept, suppressed, frame: [w, h], params: P };
}

/** Suppressed detections that would otherwise have been a nameable item (score >= the EXISTING idMinScore 0.5, DEFAULT_ID).
 *  Only these can trigger the "Move closer" hint, so faint 0.25-floor noise does not spam the screen. UI only. */
export const closerCandidates = <D extends Detection>(s: Suppressed<D>[]) => s.filter((d) => d.reason === 'below_min_area' && d.score >= DEFAULT_ID.idMinScore);

/** Smallest suppressed box containing a point (pixels), for "tap on a too-small item" handling. */
export function suppressedAt<D extends Detection>(s: Suppressed<D>[], x: number, y: number): Suppressed<D> | null {
  const hit = s.filter((d) => d.box[0] <= x && x <= d.box[2] && d.box[1] <= y && y <= d.box[3]);
  return hit.length ? hit.reduce((a, b) => ((b.box[2] - b.box[0]) * (b.box[3] - b.box[1]) < (a.box[2] - a.box[0]) * (a.box[3] - a.box[1]) ? b : a)) : null;
}

/** Does a suppressed box overlap a live track (same IoU match the tracker uses)? Used to drop that track at once (no stale box). */
export const overlapsAny = (b: Box, others: Box[], thr: number) => others.some((o) => iou(b, o) >= thr);

// ---------------------------------------------------------------- discreet, rate-limited "Move closer" hint (UI only)
/** One small hint for the whole screen, never one per box:
 *  - appears only when NO guarded item is on screen and a nameable item was suppressed as too small on >= minFrames processed frames
 *    in a row (one noisy frame never shows it);
 *  - once shown it stays at least holdMs (no flicker), then hides when the condition clears; a guarded item appearing hides it at once;
 *  - after hiding because the condition cleared (not because an item appeared) it cannot reappear for cooldownMs. */
export const CLOSER_HINT = { minFrames: 2, holdMs: 1500, cooldownMs: 2000 } as const;
export type CloserHint = { visible: boolean; update: (closerCount: number, keptCount: number, tMs: number) => boolean; reset: () => void };
export function createCloserHint(p: { minFrames: number; holdMs: number; cooldownMs: number } = CLOSER_HINT): CloserHint {
  let run = 0; let shownAt = -Infinity; let hiddenAt = -Infinity;
  const h: CloserHint = {
    visible: false,
    update(closerCount, keptCount, tMs) {
      const want = closerCount > 0 && keptCount === 0;
      run = want ? run + 1 : 0;
      if (h.visible) {
        // a guarded item on screen hides it at once (its own box/hints take over); otherwise it is held >= holdMs
        if (keptCount > 0) h.visible = false;   // no cooldown: the item may shrink again right away
        else if (!want && tMs - shownAt >= p.holdMs) { h.visible = false; hiddenAt = tMs; }
      } else if (run >= p.minFrames && tMs - hiddenAt >= p.cooldownMs) { h.visible = true; shownAt = tMs; }
      return h.visible;
    },
    reset() { run = 0; h.visible = false; shownAt = -Infinity; hiddenAt = -Infinity; },
  };
  return h;
}
