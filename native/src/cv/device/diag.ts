// G9 Stage J8 (cv-gauntlet-device): per-decision diagnostic records for the QA build (live + close-up paths). REPORT-ONLY:
// nothing here feeds back into a label, a score, a threshold or the verification policy. Records go to logcat (tag NutriSoleCV,
// prefix "NSCV diag") and to a JSONL file in the app's external files dir; frames/crops of wrong-looking or contested decisions are
// saved next to it (see docs/cv/gauntlet/G9_stageJ8_LIVE_CV_P1_GUIDE.md for the adb pull commands).
import type { Box } from '../pipeline/preprocess.ts';
import type { IdResult } from '../pipeline/closeup.ts';
import type { VerifyResult } from '../pipeline/verify.ts';
import { V1_CLASSES } from '../models/labels.ts';
import { H2_CLASSES } from '../pipeline/verify.ts';
import type { QualityMetrics, Hint } from './live.ts';
import type { Suppressed } from './guard.ts';
import type { SceneGuardParams } from '../pipeline/postprocess.ts';

export const DIAG_DIR_NAME = 'diag';
export const DIAG_JSONL = 'nscv_diag.jsonl';
export const DIAG_MAX_SAVES_PER_MIN = 6;   // bounded disk use; QA only

const cls = (i: number | null | undefined) => (i === null || i === undefined ? null : V1_CLASSES[i]?.classId ?? `c${i}`);
const h2c = (i: number) => H2_CLASSES[i] ?? `c${i}`;
const r = (v: number, d = 3) => Math.round(v * 10 ** d) / 10 ** d;

export type DiagInput = {
  path: 'live' | 'closeup' | 'tap3'; tMs: number; trackId: number | null;
  g3: { classId: number; score: number } | null; competing?: { classId: number; score: number }[];
  wide: IdResult | null; h2Top3?: { classId: number; p: number }[] | null; verify?: VerifyResult | null;
  box: Box | null; frame: [number, number]; crop?: { w: number; h: number; sidePx: number } | null;
  quality?: QualityMetrics | null; hints?: Hint[]; shownLabel: string | null; title?: string | null;
};
export type DiagRecord = Record<string, unknown> & { contested: boolean; reasonCode: string };

/** Contested = the models or frames disagree about what this object is: a competing G3 class on the same fruit, H2's top-1
 *  differs from the wide (G3) class, or the verifier refused with a contradiction. Report-only flag used to decide what to save. */
export function isContested(d: Pick<DiagInput, 'g3' | 'competing' | 'wide' | 'h2Top3' | 'verify'>): boolean {
  if (d.competing && d.competing.length) return true;
  const wideCls = d.wide && d.wide.status === 'identified' ? d.wide.classId : d.g3?.classId ?? null;
  if (d.h2Top3 && d.h2Top3.length && wideCls !== null && d.h2Top3[0].classId !== wideCls) return true;
  if (d.verify && d.verify.status === 'unable' && /contradict/.test(d.verify.reason)) return true;
  return false;
}

/** Final decision reason code, one word, for grepping. */
export function reasonCode(d: Pick<DiagInput, 'path' | 'wide' | 'verify' | 'shownLabel'>): string {
  if (d.path === 'live') return d.shownLabel ? 'live_label_wide_policy' : d.wide ? `live_${d.wide.status}_${(d.wide as { reason?: string }).reason ?? ''}`.replace(/[^a-z0-9_]+/gi, '_').replace(/_+$/, '') : 'live_no_track';
  if (!d.verify) return 'closeup_not_run';
  return d.verify.status === 'unable' ? `closeup_unable_${d.verify.reason}` : `closeup_${d.verify.status}_${(d.verify as { evidence: string }).evidence}`.replace(/\+/g, '_');
}

export function diagRecord(d: DiagInput): DiagRecord {
  const contested = isContested(d);
  const wideCls = d.wide && d.wide.status === 'identified' ? d.wide.classId : null;
  return {
    v: 1, path: d.path, t_ms: d.tMs, track: d.trackId,
    g3_class: cls(d.g3?.classId), g3_score: d.g3 ? r(d.g3.score) : null,
    competing: (d.competing ?? []).map((c) => ({ cls: cls(c.classId), score: r(c.score) })),
    wide: d.wide ? (d.wide.status === 'identified' ? `identified:${cls(d.wide.classId)}` : `${d.wide.status}:${d.wide.reason}`) : null,
    h2_top3: d.h2Top3 ? d.h2Top3.map((t) => ({ cls: h2c(t.classId), p: r(t.p) })) : null,
    g3_h2_agree: d.h2Top3 && d.h2Top3.length && wideCls !== null ? d.h2Top3[0].classId === wideCls : null,
    verify: d.verify ? (d.verify.status === 'unable' ? `unable:${d.verify.reason}` : `${d.verify.status}:${cls(d.verify.classId)}`) : null,
    box: d.box ? d.box.map((v) => Math.round(v)) : null, frame: d.frame, crop: d.crop ?? null,
    q: d.quality ? { side_px: Math.round(d.quality.sidePx), area_frac: r(d.quality.areaFrac, 4), mean_v: Math.round(d.quality.meanV), luma: Math.round(d.quality.luma),
      blur_var: r(d.quality.blurVar, 1), edge: d.quality.touchesEdge } : null,
    hints: (d.hints ?? []).map((h) => `${h.code}:${h.why}`), shown: d.shownLabel, title: d.title ?? null,
    contested, reasonCode: reasonCode(d),
  };
}
export const diagLine = (rec: DiagRecord) => `NSCV diag ${JSON.stringify(rec)}`;

/** Save frame + crop when the decision is contested, or a close-up ended "Unable to identify", rate-limited. */
export function shouldSave(rec: DiagRecord, savesInLastMinute: number): boolean {
  if (savesInLastMinute >= DIAG_MAX_SAVES_PER_MIN) return false;
  return rec.contested || (rec.path !== 'live' && typeof rec.verify === 'string' && rec.verify.startsWith('unable'));
}

/** RGB uint8 -> base64 (bridge transport for the native JPEG writer). No Buffer/btoa dependency. */
const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
export function toBase64(u: Uint8Array): string {
  let s = ''; let i = 0;
  for (; i + 2 < u.length; i += 3) { const n = (u[i] << 16) | (u[i + 1] << 8) | u[i + 2]; s += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + B64[(n >> 6) & 63] + B64[n & 63]; }
  if (i < u.length) { const n = (u[i] << 16) | ((u[i + 1] ?? 0) << 8); s += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + (i + 1 < u.length ? B64[(n >> 6) & 63] : '=') + '='; }
  return s;
}

// ---- G9 Stage J9: scene-guard suppressions, logged SEPARATELY from decisions (logcat prefix "NSCV suppressed", JSONL kind
// 'scene_guard_suppressed'). Report-only. Rate-limited: at most one record per SUPPRESSED_LOG_MIN_MS per path; the counts between two
// records are accumulated so nothing is silently lost.
export const SUPPRESSED_LOG_MIN_MS = 1000;
export type SuppressedInput = { path: 'live' | 'closeup' | 'tap3'; tMs: number; frame: [number, number]; params: SceneGuardParams; decodeFloor: number; nIn: number; suppressed: Suppressed[];
  framesSinceLast?: number; suppressedSinceLast?: number; droppedTracks?: number; hintVisible?: boolean };
export function suppressedRecord(d: SuppressedInput): Record<string, unknown> {
  return {
    v: 1, kind: 'scene_guard_suppressed', path: d.path, t_ms: d.tMs, frame: d.frame,
    guard: { min_area_frac: d.params.minAreaFrac, max_same_class: d.params.maxSameClass }, decode_floor: d.decodeFloor,
    n_in: d.nIn, n_kept: d.nIn - d.suppressed.length, n_suppressed: d.suppressed.length,
    frames_since_last: d.framesSinceLast ?? 1, suppressed_since_last: d.suppressedSinceLast ?? d.suppressed.length,
    dropped_tracks: d.droppedTracks ?? 0, move_closer_hint: d.hintVisible ?? false,
    items: d.suppressed.slice(0, 8).map((s) => ({ cls: cls(s.classId), score: r(s.score), area_frac: r(s.areaFrac, 5), reason: s.reason, box: s.box.map((v) => Math.round(v)) })),
  };
}
export const suppressedLine = (rec: Record<string, unknown>) => `NSCV suppressed ${JSON.stringify(rec)}`;
/** Per-path rate limiter for suppressed records. */
export function createSuppressedLogger(minMs = SUPPRESSED_LOG_MIN_MS) {
  let last = -Infinity; let frames = 0; let n = 0;
  return {
    /** Feed every guarded frame; returns the accumulators when a record is due (null otherwise). */
    feed(tMs: number, nSuppressed: number): { framesSinceLast: number; suppressedSinceLast: number } | null {
      if (nSuppressed > 0) { frames += 1; n += nSuppressed; }
      if (!n || tMs - last < minMs) return null;
      const out = { framesSinceLast: frames, suppressedSinceLast: n }; last = tMs; frames = 0; n = 0; return out;
    },
  };
}
