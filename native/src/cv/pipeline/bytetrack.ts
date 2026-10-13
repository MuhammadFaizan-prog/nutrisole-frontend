// G7.3 ByteTrack association, ported from Ultralytics 8.4.175 BYTETracker (trackers/byte_tracker.py, utils/matching.py,
// utils/kalman_filter.py KalmanFilterXYAH, utils/stracks.py) plus the label layer of ml/eval/bytetrack_adapter.py
// (score EMA, hysteresis and 'stable' flag identical to IouTracker). EXACT mirror of ml/eval/bytetrack_adapter.py:
// native/tests/cvByteTrack.test.ts replays the Python-generated fixture ml/eval/fixtures/bytetrack_parity.json.
//
// Behind a flag: `createTracker(kind)` / DEFAULT_TRACKER_KIND = 'iou'. ByteTrack is NOT the app default (G6/G7 decision:
// non-inferior on the synthetic TEST gauntlet, fewer ID switches, but only a post-hoc rule supports it; it is the
// candidate for a phone / labelled-real-footage A/B). Feed it detections down to trackLowThresh (0.1); only tracks
// confirmed by a detection >= trackHighThresh are ever created/shown.
//
// Float handling mirrors numpy: detection boxes are float32 (Math.fround), IoU/fused costs are float32, the Kalman
// filter is float64. Assignment = exact min-cost matching with lapjv's extend_cost/cost_limit semantics.

import type { Box } from './preprocess.ts';
import { DEFAULT_TRACKER_PARAMS, IouTracker, type Detection, type TrackOutput, type TrackerParams } from './tracker.ts';

export type ByteTrackParams = {
  trackHighThresh: number; trackLowThresh: number; newTrackThresh: number; trackBuffer: number; matchThresh: number; fuseScore: boolean;
  scoreAlpha: number; switchMargin: number; switchFrames: number; minHits: number; stableIou: number; stableMs: number; boxAlpha: number;
};
export const DEFAULT_BYTETRACK_PARAMS: ByteTrackParams = {
  trackHighThresh: 0.35, trackLowThresh: 0.1, newTrackThresh: 0.35, trackBuffer: 15, matchThresh: 0.8, fuseScore: true,
  scoreAlpha: DEFAULT_TRACKER_PARAMS.scoreAlpha, switchMargin: DEFAULT_TRACKER_PARAMS.switchMargin, switchFrames: DEFAULT_TRACKER_PARAMS.switchFrames,
  minHits: DEFAULT_TRACKER_PARAMS.minHits, stableIou: DEFAULT_TRACKER_PARAMS.stableIou, stableMs: DEFAULT_TRACKER_PARAMS.stableMs, boxAlpha: DEFAULT_TRACKER_PARAMS.boxAlpha,
};

const f32 = Math.fround;
const TRACKED = 1, LOST = 2, REMOVED = 3, NEW = 0;

// ---------------- Kalman filter (XYAH, float64) ----------------
type Vec = number[];
type Mat = number[][];
const SW_POS = 1.0 / 20, SW_VEL = 1.0 / 160;
const zeros = (r: number, c: number): Mat => Array.from({ length: r }, () => new Array<number>(c).fill(0));
function kfInitiate(m: Vec): [Vec, Mat] {
  const mean = [m[0], m[1], m[2], m[3], 0, 0, 0, 0];
  const h = m[3];
  const std = [2 * SW_POS * h, 2 * SW_POS * h, 0.01, 2 * SW_POS * h, 10 * SW_VEL * h, 10 * SW_VEL * h, 1e-5, 10 * SW_VEL * h];
  const cov = zeros(8, 8);
  for (let i = 0; i < 8; i++) cov[i][i] = std[i] * std[i];
  return [mean, cov];
}
function kfPredict(mean: Vec, cov: Mat): [Vec, Mat] {
  const h = mean[3];
  const std = [SW_POS * h, SW_POS * h, 0.01, SW_POS * h, SW_VEL * h, SW_VEL * h, 1e-5, SW_VEL * h];
  const nm = mean.slice();
  for (let i = 0; i < 4; i++) nm[i] = mean[i] + mean[i + 4];
  // F P F^T with F = [[I, I], [0, I]]
  const A = zeros(8, 8); // F P
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) A[i][j] = i < 4 ? cov[i][j] + cov[i + 4][j] : cov[i][j];
  const out = zeros(8, 8); // (F P) F^T
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) out[i][j] = j < 4 ? A[i][j] + A[i][j + 4] : A[i][j];
  for (let i = 0; i < 8; i++) out[i][i] += std[i] * std[i];
  return [nm, out];
}
function solve4(S: Mat, B: Mat): Mat { // solve S X = B (S 4x4, B 4xk), partial pivoting (LAPACK gesv equivalent up to rounding)
  const n = 4, k = B[0].length;
  const a = S.map((r) => r.slice());
  const b = B.map((r) => r.slice());
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
    [a[c], a[p]] = [a[p], a[c]]; [b[c], b[p]] = [b[p], b[c]];
    for (let r = c + 1; r < n; r++) {
      const f = a[r][c] / a[c][c];
      for (let j = c; j < n; j++) a[r][j] -= f * a[c][j];
      for (let j = 0; j < k; j++) b[r][j] -= f * b[c][j];
    }
  }
  const x = zeros(n, k);
  for (let r = n - 1; r >= 0; r--) for (let j = 0; j < k; j++) {
    let s = b[r][j];
    for (let q = r + 1; q < n; q++) s -= a[r][q] * x[q][j];
    x[r][j] = s / a[r][r];
  }
  return x;
}
function kfUpdate(mean: Vec, cov: Mat, meas: Vec): [Vec, Mat] {
  const h = mean[3];
  const std = [SW_POS * h, SW_POS * h, 0.1, SW_POS * h];
  const S = zeros(4, 4);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) S[i][j] = cov[i][j] + (i === j ? std[i] * std[i] : 0);
  // K^T = solve(S, P[:, :4]^T)  (4x8); K = 8x4
  const PT = zeros(4, 8);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 8; j++) PT[i][j] = cov[j][i];
  const KT = solve4(S, PT);
  const innov = [0, 1, 2, 3].map((i) => meas[i] - mean[i]);
  const nm = mean.map((v, i) => v + innov.reduce((s, d, j) => s + d * KT[j][i], 0));
  // P - K S K^T
  const KS = zeros(8, 4);
  for (let i = 0; i < 8; i++) for (let j = 0; j < 4; j++) { let s = 0; for (let q = 0; q < 4; q++) s += KT[q][i] * S[q][j]; KS[i][j] = s; }
  const nc = zeros(8, 8);
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { let s = 0; for (let q = 0; q < 4; q++) s += KS[i][q] * KT[q][j]; nc[i][j] = cov[i][j] - s; }
  return [nm, nc];
}

// ---------------- tracks ----------------
type STrack = {
  trackId: number; tlwh32: Vec; mean: Vec | null; cov: Mat | null; isActivated: boolean; state: number;
  score: number; cls: number; idx: number; frameId: number; startFrame: number;
};
function newSTrack(cx: number, cy: number, w: number, h: number, score: number, cls: number, idx: number): STrack {
  return { trackId: 0, tlwh32: [f32(cx - w / 2), f32(cy - h / 2), w, h], mean: null, cov: null, isActivated: false, state: NEW, score, cls, idx, frameId: 0, startFrame: 0 };
}
function tlwh(t: STrack): Vec {
  if (!t.mean) return t.tlwh32.slice();
  const r = t.mean.slice(0, 4);
  r[2] *= r[3];
  r[0] -= r[2] / 2; r[1] -= r[3] / 2;
  return r;
}
function xyxy(t: STrack): Vec {
  const r = tlwh(t);
  if (!t.mean) return [r[0], r[1], f32(r[2] + r[0]), f32(r[3] + r[1])];
  return [r[0], r[1], r[2] + r[0], r[3] + r[1]];
}
function detXyah(t: STrack): Vec { // float32 like numpy on the float32 _tlwh
  const r = t.tlwh32;
  const cx = f32(r[0] + f32(r[2] / 2)), cy = f32(r[1] + f32(r[3] / 2));
  return [cx, cy, f32(r[2] / r[3]), r[3]];
}

function iouDistance(a: STrack[], b: STrack[]): number[][] {
  const A = a.map((t) => xyxy(t).map(f32)), B = b.map((t) => xyxy(t).map(f32));
  return A.map((p) => B.map((q) => {
    const iw = Math.max(0, f32(Math.min(p[2], q[2]) - Math.max(p[0], q[0])));
    const ih = Math.max(0, f32(Math.min(p[3], q[3]) - Math.max(p[1], q[1])));
    const inter = f32(iw * ih);
    const a2 = f32(f32(q[2] - q[0]) * f32(q[3] - q[1]));
    const a1 = f32(f32(p[2] - p[0]) * f32(p[3] - p[1]));
    const area = f32(f32(a2 + a1) - inter);
    return f32(1 - f32(inter / f32(area + f32(1e-7))));
  }));
}
function fuseScore(c: number[][], dets: STrack[]): number[][] {
  return c.map((row) => row.map((v, j) => f32(1 - f32(f32(1 - v) * f32(dets[j].score)))));
}

/** Exact min-cost assignment with lapjv(extend_cost=True, cost_limit=thresh) semantics:
 *  an unmatched row or column costs thresh/2, so a pair is matched only when it is part of the global optimum. */
export function linearAssignment(cost: number[][], thresh: number, nCols?: number): { matches: Array<[number, number]>; uA: number[]; uB: number[] } {
  const n = cost.length, m = nCols ?? (n ? cost[0].length : 0);
  if (n === 0 || m === 0) return { matches: [], uA: [...Array(n).keys()], uB: [...Array(m).keys()] };
  const N = n + m;
  const C = (i: number, j: number): number => (i < n && j < m ? cost[i][j] : i >= n && j >= m ? 0 : thresh / 2);
  // Hungarian (Kuhn-Munkres, potentials), 1-indexed
  const u = new Array<number>(N + 1).fill(0), v = new Array<number>(N + 1).fill(0), p = new Array<number>(N + 1).fill(0), way = new Array<number>(N + 1).fill(0);
  for (let i = 1; i <= N; i++) {
    p[0] = i; let j0 = 0;
    const minv = new Array<number>(N + 1).fill(Infinity), used = new Array<boolean>(N + 1).fill(false);
    do {
      used[j0] = true; const i0 = p[j0]; let delta = Infinity, j1 = 0;
      for (let j = 1; j <= N; j++) if (!used[j]) {
        const cur = C(i0 - 1, j - 1) - u[i0] - v[j];
        if (cur < minv[j]) { minv[j] = cur; way[j] = j0; }
        if (minv[j] < delta) { delta = minv[j]; j1 = j; }
      }
      for (let j = 0; j <= N; j++) { if (used[j]) { u[p[j]] += delta; v[j] -= delta; } else minv[j] -= delta; }
      j0 = j1;
    } while (p[j0] !== 0);
    do { const j1 = way[j0]; p[j0] = p[j1]; j0 = j1; } while (j0);
  }
  const rowTo = new Array<number>(n).fill(-1), colTo = new Array<number>(m).fill(-1);
  for (let j = 1; j <= N; j++) { const i = p[j] - 1; if (i < n && j - 1 < m) { rowTo[i] = j - 1; colTo[j - 1] = i; } }
  const matches: Array<[number, number]> = [];
  rowTo.forEach((j, i) => { if (j >= 0) matches.push([i, j]); });
  return { matches, uA: rowTo.map((j, i) => (j < 0 ? i : -1)).filter((i) => i >= 0), uB: colTo.map((i, j) => (i < 0 ? j : -1)).filter((j) => j >= 0) };
}

const joint = (a: STrack[], b: STrack[]): STrack[] => { const ids = new Set(a.map((t) => t.trackId)); return [...a, ...b.filter((t) => !ids.has(t.trackId))]; };
const sub = (a: STrack[], b: STrack[]): STrack[] => { const ids = new Set(b.map((t) => t.trackId)); return a.filter((t) => !ids.has(t.trackId)); };

/** Ultralytics BYTETracker.update: returns [x1,y1,x2,y2,id,score,cls,idx] for activated tracked tracks. */
export class ByteTrackCore {
  tracked: STrack[] = []; lost: STrack[] = []; removed: STrack[] = []; frameId = 0; nextId = 1;
  a: ByteTrackParams;
  constructor(a: ByteTrackParams) { this.a = a; }

  update(dets: Detection[]): Array<{ box: Vec; id: number; idx: number }> {
    const A = this.a;
    this.frameId += 1;
    const activated: STrack[] = [], refind: STrack[] = [], lostNow: STrack[] = [], removedNow: STrack[] = [];
    const high: STrack[] = [], low: STrack[] = [];
    dets.forEach((d, i) => {
      const b = d.box.map(f32);
      const cx = f32(f32(b[0] + b[2]) / 2), cy = f32(f32(b[1] + b[3]) / 2), w = f32(b[2] - b[0]), h = f32(b[3] - b[1]);
      const s = f32(d.score);
      if (!(w > 0 && h > 0)) return;
      if (s >= A.trackHighThresh) high.push(newSTrack(cx, cy, w, h, s, d.classId, i));
      else if (s > A.trackLowThresh) low.push(newSTrack(cx, cy, w, h, s, d.classId, i));
    });
    const unconfirmed = this.tracked.filter((t) => !t.isActivated);
    const trackedAct = this.tracked.filter((t) => t.isActivated);
    const pool = joint(trackedAct, this.lost);
    for (const t of pool) {
      const m = t.mean!.slice();
      if (t.state !== TRACKED) m[7] = 0;
      [t.mean, t.cov] = kfPredict(m, t.cov!);
    }
    const dists = (ts: STrack[], ds: STrack[]): number[][] => { const c = iouDistance(ts, ds); return A.fuseScore ? fuseScore(c, ds) : c; };
    const apply = (t: STrack, d: STrack): void => {
      [t.mean, t.cov] = kfUpdate(t.mean!, t.cov!, detXyah(d));
      if (t.state === TRACKED) activated.push(t); else refind.push(t);
      t.state = TRACKED; t.isActivated = true; t.frameId = this.frameId; t.score = d.score; t.cls = d.cls; t.idx = d.idx;
    };
    // first association (high)
    const r1 = linearAssignment(dists(pool, high), A.matchThresh, high.length);
    for (const [it, id] of r1.matches) apply(pool[it], high[id]);
    // second association (low) on still-tracked unmatched
    const rTracked = r1.uA.map((i) => pool[i]).filter((t) => t.state === TRACKED);
    let uT: number[];
    if (rTracked.length && low.length) {
      const r2 = linearAssignment(iouDistance(rTracked, low), 0.5, low.length);
      for (const [it, id] of r2.matches) apply(rTracked[it], low[id]);
      uT = r2.uA;
    } else uT = rTracked.map((_, i) => i);
    for (const i of uT) { rTracked[i].state = LOST; lostNow.push(rTracked[i]); }
    // unconfirmed
    const restDets = r1.uB.map((i) => high[i]);
    let uD: number[];
    if (!unconfirmed.length) uD = restDets.map((_, i) => i);
    else {
      const r3 = linearAssignment(dists(unconfirmed, restDets), 0.7, restDets.length);
      for (const [it, id] of r3.matches) {
        const t = unconfirmed[it], d = restDets[id];
        [t.mean, t.cov] = kfUpdate(t.mean!, t.cov!, detXyah(d));
        t.state = TRACKED; t.isActivated = true; t.frameId = this.frameId; t.score = d.score; t.cls = d.cls; t.idx = d.idx;
        activated.push(t);
      }
      for (const i of r3.uA) { unconfirmed[i].state = REMOVED; removedNow.push(unconfirmed[i]); }
      uD = r3.uB;
    }
    // new tracks
    for (const i of uD) {
      const t = restDets[i];
      if (t.score < A.newTrackThresh) continue;
      t.trackId = this.nextId++;
      [t.mean, t.cov] = kfInitiate(detXyah(t));
      t.state = TRACKED; t.isActivated = this.frameId === 1; t.frameId = this.frameId; t.startFrame = this.frameId;
      activated.push(t);
    }
    for (const t of this.lost) if (this.frameId - t.frameId > A.trackBuffer) { t.state = REMOVED; removedNow.push(t); }
    // merge pools
    this.tracked = this.tracked.filter((t) => t.state === TRACKED);
    this.tracked = joint(this.tracked, activated);
    this.tracked = joint(this.tracked, refind);
    this.lost = sub(this.lost, this.tracked);
    this.lost.push(...lostNow);
    this.lost = sub(this.lost, this.removed);
    // remove duplicates between tracked and lost
    const pd = iouDistance(this.tracked, this.lost);
    const dupA = new Set<number>(), dupB = new Set<number>();
    pd.forEach((row, p) => row.forEach((v, q) => {
      if (v < 0.15) {
        const tp = this.tracked[p].frameId - this.tracked[p].startFrame, tq = this.lost[q].frameId - this.lost[q].startFrame;
        if (tp > tq) dupB.add(q); else dupA.add(p);
      }
    }));
    this.tracked = this.tracked.filter((_, i) => !dupA.has(i));
    this.lost = this.lost.filter((_, i) => !dupB.has(i));
    this.removed.push(...removedNow);
    if (this.removed.length > 1000) this.removed = this.removed.slice(-1000);
    return this.tracked.filter((t) => t.isActivated).map((t) => ({ box: xyxy(t), id: t.trackId, idx: t.idx }));
  }
}

type LabelState = {
  id: number; box: Box; rawBox: Box; label: number; scores: Record<number, number>; hits: number;
  pendingLabel: number; pendingCount: number; stableSinceMs: number; firstSeenMs: number;
};

/** Same interface as IouTracker (update(dets, tMs) -> TrackOutput[], reset()). Mirrors ml/eval/bytetrack_adapter.py. */
export class ByteTrackTracker {
  params: ByteTrackParams;
  core: ByteTrackCore;
  state = new Map<number, LabelState>();

  constructor(params: Partial<ByteTrackParams> = {}) {
    this.params = { ...DEFAULT_BYTETRACK_PARAMS, ...params };
    this.core = new ByteTrackCore(this.params);
  }

  reset(): void {
    this.core = new ByteTrackCore(this.params);
    this.state = new Map();
  }

  update(dets: Detection[], tMs: number): TrackOutput[] {
    const P = this.params;
    const out = this.core.update(dets);
    const live: LabelState[] = [];
    const liveIds = new Set<number>();
    for (const r of out) {
      const d = dets[r.idx];
      let t = this.state.get(r.id);
      if (!t) {
        t = { id: r.id, box: [...d.box] as Box, rawBox: [...d.box] as Box, label: d.classId, scores: { [d.classId]: d.score }, hits: 1,
          pendingLabel: -1, pendingCount: 0, stableSinceMs: tMs, firstSeenMs: tMs };
        this.state.set(r.id, t);
      } else {
        if (boxIou(t.rawBox, d.box) < P.stableIou) t.stableSinceMs = tMs;
        t.rawBox = [d.box[0], d.box[1], d.box[2], d.box[3]];
        t.box = [0, 1, 2, 3].map((k) => (1 - P.boxAlpha) * t!.box[k] + P.boxAlpha * d.box[k]) as Box;
        const classes = [...new Set<number>([...Object.keys(t.scores).map(Number), d.classId])];
        for (const c of classes) {
          const prev = t.scores[c] ?? 0;
          t.scores[c] = (1 - P.scoreAlpha) * prev + P.scoreAlpha * (c === d.classId ? d.score : 0);
        }
        this.hyst(t);
        t.hits += 1;
      }
      live.push(t); liveIds.add(r.id);
    }
    const keep = new Set<number>([...this.core.tracked, ...this.core.lost].map((s) => s.trackId));
    for (const k of [...this.state.keys()]) if (!keep.has(k) && !liveIds.has(k)) this.state.delete(k);
    return live.filter((t) => t.hits >= P.minHits).map((t) => ({
      id: t.id, box: t.box, label: t.label, score: t.scores[t.label] ?? 0, stable: tMs - t.stableSinceMs >= P.stableMs, ageMs: tMs - t.firstSeenMs,
    }));
  }

  private hyst(t: LabelState): void {
    const P = this.params;
    let best = t.label;
    let bestS = t.scores[t.label] ?? 0;
    for (const k of Object.keys(t.scores).map(Number).sort((a, b) => a - b)) if (t.scores[k] > bestS) { best = k; bestS = t.scores[k]; }
    if (best !== t.label && bestS - (t.scores[t.label] ?? 0) >= P.switchMargin) {
      if (t.pendingLabel === best) t.pendingCount += 1; else { t.pendingLabel = best; t.pendingCount = 1; }
      if (t.pendingCount >= P.switchFrames) { t.label = best; t.pendingLabel = -1; t.pendingCount = 0; }
    } else { t.pendingLabel = -1; t.pendingCount = 0; }
  }
}

function boxIou(a: Box, b: Box): number { // same formula as ml/eval/tracker.iou (float64)
  const ix = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0]));
  const iy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
  const inter = ix * iy;
  const ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter;
  return ua > 0 ? inter / ua : 0;
}

// ---------------- flag ----------------
export type TrackerKind = 'iou' | 'bytetrack';
/** App default stays IouTracker (G7 decision). ByteTrack only when explicitly requested. */
export const DEFAULT_TRACKER_KIND: TrackerKind = 'iou';
export type AnyTracker = { update(dets: Detection[], tMs: number): TrackOutput[]; reset(): void };
export function createTracker(kind: TrackerKind = DEFAULT_TRACKER_KIND, params: Partial<TrackerParams> | Partial<ByteTrackParams> = {}): AnyTracker {
  return kind === 'bytetrack' ? new ByteTrackTracker(params as Partial<ByteTrackParams>) : new IouTracker(params as Partial<TrackerParams>);
}
