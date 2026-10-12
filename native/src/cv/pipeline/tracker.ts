// Per-object IoU tracker with label hysteresis (master prompt rule 8.9).
// Mirrors ml/eval/tracker.py exactly; native/tests/cvTracker.test.ts replays the
// Python-generated fixture ml/eval/fixtures/tracker_parity.json and requires identical
// output, so the desktop video gauntlet measures the same smoothing the app runs.
//
// - Greedy IoU matching (pairs sorted by IoU desc, then track id, then detection index).
// - Box EMA; per-class score EMA; the displayed label switches only after another class
//   leads by `switchMargin` for `switchFrames` consecutive updates (hysteresis).
// - A NEW object always starts a NEW track with fresh state, so an old label never
//   sticks to a new fruit. Tracks die after `maxMissed` frames without a match, and
//   `reset()` (scene cut / camera restart) clears everything.
// - `stableSinceMs`: time since the raw box last moved (IoU < stableIou vs previous raw
//   box). Quality grading is throttled until a track has been stable for stableMs.

import { iou, type Box } from './preprocess.ts';

export type Detection = { box: Box; classId: number; score: number };
export type TrackerParams = {
  iouMatch: number; boxAlpha: number; scoreAlpha: number; switchMargin: number; switchFrames: number;
  minHits: number; maxMissed: number; stableIou: number; stableMs: number;
};
export const DEFAULT_TRACKER_PARAMS: TrackerParams = {
  iouMatch: 0.3, boxAlpha: 0.6, scoreAlpha: 0.35, switchMargin: 0.15, switchFrames: 3,
  minHits: 2, maxMissed: 4, stableIou: 0.8, stableMs: 500,
};

export type Track = {
  id: number; box: Box; rawBox: Box; label: number; scores: Record<number, number>;
  hits: number; missed: number; pendingLabel: number; pendingCount: number;
  stableSinceMs: number; firstSeenMs: number;
};
export type TrackOutput = { id: number; box: Box; label: number; score: number; stable: boolean; ageMs: number };

export class IouTracker {
  params: TrackerParams;
  tracks: Track[] = [];
  nextId = 1;

  constructor(params: Partial<TrackerParams> = {}) {
    this.params = { ...DEFAULT_TRACKER_PARAMS, ...params };
  }

  reset(): void {
    this.tracks = [];
  }

  update(dets: Detection[], tMs: number): TrackOutput[] {
    const P = this.params;
    const pairs: Array<[number, number, number]> = [];
    this.tracks.forEach((t, ti) => dets.forEach((d, di) => {
      const v = iou(t.box, d.box);
      if (v >= P.iouMatch) pairs.push([v, ti, di]);
    }));
    pairs.sort((a, b) => b[0] - a[0] || this.tracks[a[1]].id - this.tracks[b[1]].id || a[2] - b[2]);
    const usedT = new Set<number>();
    const usedD = new Set<number>();
    for (const [, ti, di] of pairs) {
      if (usedT.has(ti) || usedD.has(di)) continue;
      usedT.add(ti); usedD.add(di);
      const t = this.tracks[ti];
      const d = dets[di];
      if (iou(t.rawBox, d.box) < P.stableIou) t.stableSinceMs = tMs;
      t.rawBox = [d.box[0], d.box[1], d.box[2], d.box[3]];
      t.box = [0, 1, 2, 3].map((k) => (1 - P.boxAlpha) * t.box[k] + P.boxAlpha * d.box[k]) as Box;
      const classes = new Set<number>([...Object.keys(t.scores).map(Number), d.classId]);
      for (const c of classes) {
        const prev = t.scores[c] ?? 0;
        t.scores[c] = (1 - P.scoreAlpha) * prev + P.scoreAlpha * (c === d.classId ? d.score : 0);
      }
      this.applyHysteresis(t);
      t.hits += 1;
      t.missed = 0;
    }
    const survivors: Track[] = [];
    this.tracks.forEach((t, ti) => {
      if (!usedT.has(ti)) t.missed += 1;
      if (t.missed <= P.maxMissed) survivors.push(t);
    });
    this.tracks = survivors;
    dets.forEach((d, di) => {
      if (usedD.has(di)) return;
      this.tracks.push({
        id: this.nextId++, box: [...d.box] as Box, rawBox: [...d.box] as Box, label: d.classId,
        scores: { [d.classId]: d.score }, hits: 1, missed: 0, pendingLabel: -1, pendingCount: 0,
        stableSinceMs: tMs, firstSeenMs: tMs,
      });
    });
    return this.tracks
      .filter((t) => t.hits >= P.minHits && t.missed === 0)
      .map((t) => ({ id: t.id, box: t.box, label: t.label, score: t.scores[t.label] ?? 0, stable: tMs - t.stableSinceMs >= P.stableMs, ageMs: tMs - t.firstSeenMs }));
  }

  private applyHysteresis(t: Track): void {
    const P = this.params;
    let best = t.label;
    let bestScore = t.scores[t.label] ?? 0;
    for (const k of Object.keys(t.scores).map(Number).sort((a, b) => a - b)) {
      if (t.scores[k] > bestScore) { best = k; bestScore = t.scores[k]; }
    }
    if (best !== t.label && bestScore - (t.scores[t.label] ?? 0) >= P.switchMargin) {
      if (t.pendingLabel === best) t.pendingCount += 1;
      else { t.pendingLabel = best; t.pendingCount = 1; }
      if (t.pendingCount >= P.switchFrames) { t.label = best; t.pendingLabel = -1; t.pendingCount = 0; }
    } else {
      t.pendingLabel = -1; t.pendingCount = 0;
    }
  }
}
