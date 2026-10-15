// G9 Stage J6 (cv-gauntlet-device): what the debug camera says about WHERE its output comes from, and the latency / memory hooks.
// Pure, unit-tested. Nothing here measures a phone: timings are whatever `now()` returns on the device that runs it, and the host
// harness (native/scripts/g9j6_host_pipeline.ts) labels its own numbers host-side. No FPS figure is ever produced for the screen.
import { domainIdForClassIndex, cvClassOf, type DomainId } from '../domainMap.ts';
import type { VerifyResult } from '../pipeline/verify.ts';

/** real = both ONNX sessions loaded and the shown result came from runDebugPipeline on captured stills;
 *  placeholder = no model ran (loading, models missing, error, or the normal demo Scan screen). */
export type InferenceSource = 'real' | 'placeholder';
export type InferenceBadge = { source: InferenceSource; text: string; color: string };
export const REAL_BADGE_TEXT = 'REAL INFERENCE · G3 + H2 ONNX on this device';
export const PLACEHOLDER_BADGE_TEXT = 'PLACEHOLDER · no model output';

export function inferenceBadge(sessionsLoaded: boolean, resultFromPipeline: boolean, reason = ''): InferenceBadge {
  return sessionsLoaded && resultFromPipeline
    ? { source: 'real', text: REAL_BADGE_TEXT, color: '#7fd38b' }
    : { source: 'placeholder', text: reason ? `${PLACEHOLDER_BADGE_TEXT} (${reason})` : PLACEHOLDER_BADGE_TEXT, color: '#f2a446' };
}

/** CV identity -> canonical domain id (nutrition / Lahore lookup key) through domainMap.ts only. Null unless verified/confirmed. */
export function domainOf(v: VerifyResult | null): { cvClass: string | null; domainId: DomainId | null } {
  if (!v || v.status === 'unable') return { cvClass: null, domainId: null };
  return { cvClass: cvClassOf('h2', v.classId), domainId: domainIdForClassIndex('h2', v.classId) };
}

/** Latency hooks: mark named spans, summarise (n, p50, p95, max) and emit NSCV lines. Values are ms on the running device. */
export type LatencyRecorder = { start: (k: string) => () => number; record: (k: string, ms: number) => void; summary: () => Record<string, { n: number; p50: number; p95: number; max: number }>; lines: () => string[] };
export function createLatencyRecorder(now: () => number): LatencyRecorder {
  const s = new Map<string, number[]>();
  const record = (k: string, ms: number) => { if (!(ms >= 0) || !Number.isFinite(ms)) return; (s.get(k) ?? s.set(k, []).get(k)!).push(ms); };
  const q = (a: number[], p: number) => { const b = [...a].sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.max(0, Math.ceil(p * b.length) - 1))]; };
  const summary = () => Object.fromEntries([...s.entries()].map(([k, a]) => [k, { n: a.length, p50: q(a, 0.5), p95: q(a, 0.95), max: Math.max(...a) }]));
  return {
    start: (k) => { const t0 = now(); return () => { const ms = now() - t0; record(k, ms); return ms; }; },
    record, summary,
    lines: () => Object.entries(summary()).map(([k, v]) => `NSCV latency span=${k} n=${v.n} p50_ms=${Math.round(v.p50)} p95_ms=${Math.round(v.p95)} max_ms=${Math.round(v.max)}`),
  };
}

/** UI responsiveness: JS event-loop lag sampler. tick() is called from a setInterval(intervalMs); lag = late arrival beyond the interval. */
export function createLagSampler(now: () => number, intervalMs = 100) {
  let last = now(); const lags: number[] = [];
  return {
    tick: () => { const t = now(); lags.push(Math.max(0, t - last - intervalMs)); last = t; },
    line: () => { const a = [...lags].sort((x, y) => x - y); const p = (f: number) => (a.length ? a[Math.min(a.length - 1, Math.ceil(f * a.length) - 1)] : 0);
      return `NSCV ui_lag n=${a.length} p50_ms=${Math.round(p(0.5))} p95_ms=${Math.round(p(0.95))} max_ms=${Math.round(a[a.length - 1] ?? 0)}`; },
  };
}

/** Host-side memory ESTIMATE for the two models (weights + one float32 input/output buffer each). Not a phone measurement:
 *  real numbers come from `adb shell dumpsys meminfo <app>` (see the P1 guide). */
export function modelMemoryEstimateBytes(weightBytes: number[], tensors: number[][]): number {
  const t = tensors.reduce((a, dims) => a + 4 * dims.reduce((x, y) => x * y, 1), 0);
  return weightBytes.reduce((a, b) => a + b, 0) + t;
}
