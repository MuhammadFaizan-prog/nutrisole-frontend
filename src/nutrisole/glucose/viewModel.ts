// Turns the glucose store snapshot + screen choices into plain strings for the shared
// scene builder (extensions/model.ts), so the same honest states render on web and native.
import type { GlucoseReading, GlucoseUnit } from './types';
import type { GlucoseSnapshot } from './store';
import { chartModel, filterReadings, rangeLabels, readingWhen, type GlucoseRange } from './history';
import { displayValue, fromMgDl } from './units';
import { contextLabel } from './validation';
import { deviceOffsetMinutes, deviceTimeZoneName, timeZoneLabel, formatDisplayDate, formatDisplayTime, instantToWallClock } from './time';

export type GlucoseListItem = { id: string; value: string; unit: GlucoseUnit; when: string; context: string; source: string };
export type GlucoseDetail = { id: string; value: string; unit: GlucoseUnit; alt: string; date: string; time: string; timeZone: string; context: string; note: string; source: string; savedLabel: string; entered: string };
export type GlucoseSceneView = {
  mode: GlucoseSnapshot['mode'];
  status: GlucoseSnapshot['status'];
  ready: boolean;
  /** Title/message shown in place of data when the list cannot be shown. */
  stateTitle: string; stateMessage: string; stateAction: { label: string; action: string } | null;
  /** One-line truthful banner (demo / offline / stale), or null. */
  banner: string | null;
  displayUnit: GlucoseUnit; range: GlucoseRange; rangeSubtitle: string;
  chart: { bars: { value: string; ratio: number; label: string }[]; summary: string; latest: string; first: string; last: string } | null;
  list: GlucoseListItem[]; listTotal: number; total: number;
  detail: GlucoseDetail | null; removed: boolean;
  form: { editing: boolean; busy: boolean; timeZone: string; saveNote: string };
  busy: GlucoseSnapshot['busy'];
};

const sourceLabel = (r: GlucoseReading) => r.source.type === 'manual' ? 'Manual meter entry' : `Imported · ${r.source.provider || r.source.type}`;

export function stateCopy(s: Pick<GlucoseSnapshot, 'mode' | 'status' | 'error'>): { title: string; message: string; action: { label: string; action: string } | null } {
  switch (s.status) {
    case 'unconfigured': return { title: 'Database not configured', message: 'This build is not connected to the NutriSole database, so readings cannot be saved or loaded yet.', action: null };
    case 'signed-out': return { title: 'Sign in to see your readings', message: 'Your glucose readings are saved to your NutriSole account.', action: { label: 'Sign in', action: 'glucose-sign-in' } };
    case 'loading': return { title: 'Loading your readings…', message: 'Fetching your glucose history.', action: null };
    case 'offline': return { title: 'You are offline', message: s.error || 'NutriSole could not reach the database. Nothing was changed.', action: { label: 'Retry', action: 'glucose-retry' } };
    case 'schema-missing': return { title: 'Database setup pending', message: s.error || 'The glucose table is not set up yet.', action: { label: 'Retry', action: 'glucose-retry' } };
    case 'error': return { title: 'Could not load readings', message: s.error || 'Something went wrong.', action: { label: 'Retry', action: 'glucose-retry' } };
    default: return { title: 'No readings yet', message: 'Add a meter reading to start your history.', action: null };
  }
}

export function buildGlucoseView(snapshot: GlucoseSnapshot, opts: { displayUnit: GlucoseUnit; range: GlucoseRange; currentId: string | null; removed: boolean; editingId: string | null; editOffset: number | null; editTzName?: string | null; now?: Date }): GlucoseSceneView {
  const now = opts.now ?? new Date();
  const ready = snapshot.status === 'ready' || (snapshot.stale && snapshot.readings.length > 0);
  const filtered = filterReadings(snapshot.readings, opts.range, now);
  const copy = stateCopy(snapshot);
  const emptyInRange = ready && snapshot.readings.length > 0 && filtered.length === 0;
  const banner = snapshot.mode === 'demo' ? 'Demo mode · readings stay in this session only and are not saved to a database.'
    : snapshot.stale ? `Showing readings from your last successful load. ${snapshot.error || ''}`.trim() : null;
  const chart = ready ? chartModel(filtered, opts.displayUnit) : null;
  const list = ready ? [...filtered].reverse().slice(0, 30).map(r => { const w = readingWhen(r); return { id: r.id, value: displayValue(r, opts.displayUnit), unit: opts.displayUnit, when: `${w.date} · ${w.time}`, context: contextLabel(r.mealContext), source: sourceLabel(r) }; }) : [];
  const current = opts.currentId ? snapshot.readings.find(r => r.id === opts.currentId) || null : null;
  let detail: GlucoseDetail | null = null;
  if (current) {
    const w = readingWhen(current);
    const other: GlucoseUnit = current.unitOriginal === 'mg/dL' ? 'mmol/L' : 'mg/dL';
    const otherValue = other === 'mmol/L' ? fromMgDl(current.valueMgDl, other).toFixed(1) : String(fromMgDl(current.valueMgDl, other));
    const created = instantToWallClock(current.createdAt, -new Date(current.createdAt).getTimezoneOffset());
    detail = {
      id: current.id, value: current.valueOriginal, unit: current.unitOriginal, alt: `≈ ${otherValue} ${other} · entered in ${current.unitOriginal}`,
      date: w.date, time: w.time, timeZone: timeZoneLabel(current.tzName, current.tzOffsetMinutes), context: contextLabel(current.mealContext), note: current.note || 'None',
      source: sourceLabel(current), savedLabel: snapshot.mode === 'supabase' ? 'Saved to your account' : 'Demo session · not saved', entered: `${formatDisplayDate(created)} · ${formatDisplayTime(created)}`,
    };
  }
  const nowClock = { year: now.getFullYear(), month: now.getMonth(), day: now.getDate(), hour: now.getHours(), minute: now.getMinutes() };
  const offset = opts.editOffset ?? deviceOffsetMinutes(nowClock);
  const saveNote = snapshot.mode === 'unconfigured' ? 'Database not configured: this reading cannot be saved in this build.'
    : snapshot.status === 'signed-out' ? 'Sign in to save this reading to your account.'
    : snapshot.status === 'offline' ? 'You are offline. The reading will not be saved until you retry online.'
    : snapshot.mode === 'demo' ? 'Demo mode: saved only for this session, not to a database.'
    : 'Enter an existing meter reading.\nNutriSole does not measure or interpret glucose.';
  const fromDays = opts.range === '7d' ? 6 : opts.range === '30d' ? 29 : opts.range === '90d' ? 89 : null;
  const fromDate = fromDays === null ? null : new Date(now.getFullYear(), now.getMonth(), now.getDate() - fromDays);
  const short = (d: Date) => formatDisplayDate({ year: d.getFullYear(), month: d.getMonth(), day: d.getDate() }).replace(/, \d{4}$/, '');
  return {
    mode: snapshot.mode, status: snapshot.status, ready,
    stateTitle: emptyInRange ? 'No readings in this range' : copy.title, stateMessage: emptyInRange ? 'Choose a longer range or add a reading.' : copy.message, stateAction: emptyInRange ? null : copy.action,
    banner, displayUnit: opts.displayUnit, range: opts.range, rangeSubtitle: fromDate ? `${short(fromDate)} – ${short(now)}` : rangeLabels.all,
    chart: chart ? { bars: chart.bars.map(b => ({ value: b.value, ratio: b.heightRatio, label: b.label })), summary: chart.summary, latest: `${chart.latest} ${chart.unit}`, first: chart.first, last: chart.last } : null,
    list, listTotal: filtered.length, total: snapshot.readings.length,
    detail, removed: opts.removed,
    form: { editing: Boolean(opts.editingId), busy: snapshot.busy === 'saving', timeZone: timeZoneLabel(opts.editingId ? (opts.editTzName ?? null) : deviceTimeZoneName(), offset), saveNote },
    busy: snapshot.busy,
  };
}
