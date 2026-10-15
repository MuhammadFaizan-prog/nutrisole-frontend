// G9 Stage J4: phone-test debug flag + NSCV log-line formatters (pure; no React Native imports).
// Default OFF. On a device/debug build the tester turns it on once at start-up (e.g. `if (__DEV__) setCvDebug(true)`) and every
// line goes to console.log with the NSCV tag, which native/scripts/g9i-device-check.ps1 already parses from logcat.
// Lines carry geometry, timings and result STATES only: never a confidence number shown as a result, never a grade.
import type { StillCropPlan } from './pipeline/camera.ts';
import type { DisplayResult } from './pipeline/result.ts';

const state = { enabled: false, sink: (line: string) => console.log(line) };
export const cvDebugEnabled = () => state.enabled;
export function setCvDebug(on: boolean, sink?: (line: string) => void) { state.enabled = on; if (sink) state.sink = sink; }

const r = (v: number) => Math.round(v * 1000) / 1000;
export function nscvMapLine(tap: [number, number], plan: StillCropPlan, still: [number, number], rotation: number, mirrored: boolean): string {
  const c = plan.crop;
  return `NSCV map tap=${r(tap[0])},${r(tap[1])} frame=${r(plan.framePoint[0])},${r(plan.framePoint[1])} still=${still[0]}x${still[1]} ` +
    `crop=${c.x},${c.y},${c.w},${c.h} src=${plan.source} rot=${rotation} mirror=${mirrored ? 1 : 0}`;
}
export const nscvStageLine = (stage: 'crop' | 'h2' | 'occl' | 'det' | 'track', ms: number) => `NSCV stage=${stage} ms=${r(ms)}`;
export const nscvResultLine = (d: DisplayResult) =>
  `NSCV event=result state=${d.state} origin=${d.origin} identity=${d.identityLabel ?? '-'} grade=none reasons=${d.reasons.join('|') || '-'}`;

/** Emit only when the flag is on. Returns the line (or null) so tests can check it. */
export function nscv(line: string): string | null { if (!state.enabled) return null; state.sink(line); return line; }
