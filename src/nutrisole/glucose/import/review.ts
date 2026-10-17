// Review flow for every imported/OCR'd/device reading. Pure functions: the UI keeps an
// ImportBatch in state and calls these. Nothing here writes to the repository; only
// confirmed, valid rows become drafts in draftsToSave().
import type { GlucoseDraft, GlucoseReading, GlucoseSourceType } from '../types';
import { validateGlucoseInput } from '../validation';
import { instantToWallClock } from '../time';
import type { CandidateFlag, ImportBatch, ImportCandidate } from './types';
import { LOW_CONFIDENCE } from './types';
import { mgDlOf, plausibilityFlags } from './unitDetect';
import { displayDate, displayTime } from './dates';

/** Flags that stop "Confirm all unflagged" and need a per-row look. */
export const BLOCKING: CandidateFlag[] = ['invalid', 'out-of-range', 'missing-date', 'missing-time', 'future', 'duplicate-existing', 'duplicate-batch', 'already-imported', 'specimen', 'control-solution'];
/** Flags the user may accept explicitly on a row, but never in bulk. */
export const NEEDS_LOOK: CandidateFlag[] = ['unit-inferred', 'unit-ambiguous', 'implausible', 'low-confidence', 'year-assumed', 'sensor-status', 'meter-clock'];
/** Informational flags: shown on the row but do not hold back bulk confirm. */
export const INFO: CandidateFlag[] = ['meter-clock'];
const needsAttention = (a: { allFlags: CandidateFlag[]; error: string | null }) => a.error !== null || a.allFlags.some(f => !INFO.includes(f));
/** Flags that make saving impossible until edited. */
export const HARD: CandidateFlag[] = ['invalid', 'out-of-range', 'missing-date', 'missing-time', 'future', 'already-imported', 'specimen', 'control-solution'];

export const flagText: Record<CandidateFlag, string> = {
  'unit-inferred': 'Unit not written next to the value; inferred', 'unit-ambiguous': 'Unit unclear (could be mg/dL or mmol/L)',
  implausible: 'Outside 10–600 mg/dL; check the value and unit', 'out-of-range': 'Not a possible meter value in this unit',
  'missing-date': 'No date found', 'missing-time': 'No time found', 'year-assumed': 'Year not shown; current year assumed', future: 'Time is in the future',
  'duplicate-existing': 'Same value and time already in your history', 'duplicate-batch': 'Repeated in this import', 'already-imported': 'Already imported from this source',
  'low-confidence': 'Low recognition confidence', specimen: 'Not a finger-prick blood sample (e.g. CGM)', 'control-solution': 'Control-solution test, not a reading',
  'sensor-status': 'Meter reported a sensor/strip warning', 'meter-clock': 'Meter clock zone assumed to be this phone’s', invalid: 'Value is not a valid number',
};

export type AssessedCandidate = ImportCandidate & { allFlags: CandidateFlag[]; error: string | null; mgDl: number | null; measuredAt: string | null };

const sourceType = (c: ImportCandidate): Exclude<GlucoseSourceType, 'manual'> => c.provenance.method === 'file' ? 'file' : c.provenance.method;
type ExistingIndex = { sources: Set<string>; content: Set<string> };
const sourceKey = (type: string, provider: string | null, device: string | null, recordId: string | null) => JSON.stringify([type, provider, device, recordId]);
function indexExisting(existing: GlucoseReading[]): ExistingIndex {
  return { sources: new Set(existing.filter(r => r.source.recordId).map(r => sourceKey(r.source.type, r.source.provider, r.source.device, r.source.recordId))), content: new Set(existing.map(r => dedupeKey(r.measuredAt, r.valueMgDl))) };
}

/** Content key used to spot the same reading from two sources: minute instant + mg/dL. */
export function dedupeKey(measuredAt: string, mgDl: number) { return `${new Date(Math.floor(Date.parse(measuredAt) / 60_000) * 60_000).toISOString()}|${mgDl.toFixed(1)}`; }

export function assessCandidate(c: ImportCandidate, existing: GlucoseReading[], now = new Date(), index = indexExisting(existing)): AssessedCandidate {
  const flags = new Set<CandidateFlag>(c.edited ? c.flags.filter(f => !['unit-inferred', 'unit-ambiguous', 'implausible', 'missing-date', 'missing-time', 'year-assumed', 'low-confidence', 'invalid'].includes(f)) : c.flags);
  if (c.confidence < LOW_CONFIDENCE && !c.edited) flags.add('low-confidence');
  if (!c.date) flags.add('missing-date'); if (!c.time) flags.add('missing-time');
  if (c.unit) for (const f of plausibilityFlags(c.value, c.unit)) flags.add(f);
  let error: string | null = null; let measuredAt: string | null = null; let mgDl: number | null = null;
  if (c.unit && c.date && c.time) {
    const v = validateGlucoseInput({ value: c.value, unit: c.unit, date: c.date, time: c.time, tzOffsetMinutes: c.tzOffsetMinutes ?? undefined, tzName: null, mealContext: c.mealContext, note: c.note }, { now, existing: [] });
    if (!v.ok) { error = v.error; flags.add(v.field === 'value' ? 'out-of-range' : v.field === 'date' && /future/.test(v.error) ? 'future' : 'invalid'); }
    else { measuredAt = c.sourceInstant && Number.isFinite(Date.parse(c.sourceInstant)) && Math.floor(Date.parse(c.sourceInstant) / 60_000) === Math.floor(Date.parse(v.draft.measuredAt) / 60_000) ? c.sourceInstant : v.draft.measuredAt; mgDl = v.draft.valueMgDl; }
  } else if (!c.unit) { error = 'Choose mg/dL or mmol/L.'; flags.add('unit-ambiguous'); }
  if (mgDl === null && c.unit) mgDl = mgDlOf(c.value, c.unit);
  if (measuredAt && mgDl !== null) {
    const key = dedupeKey(measuredAt, mgDl);
    if (index.sources.has(sourceKey(sourceType(c), c.provenance.provider, c.provenance.device, c.provenance.recordId))) flags.add('already-imported');
    else if (index.content.has(key)) flags.add('duplicate-existing');
  }
  return { ...c, allFlags: [...flags], error, mgDl, measuredAt };
}

export function assessBatch(batch: ImportBatch, existing: GlucoseReading[], now = new Date()): AssessedCandidate[] {
  const index = indexExisting(existing);
  const assessed = batch.candidates.map(c => assessCandidate(c, [], now, index));
  const seen = new Map<string, string>();
  for (const a of assessed) {
    if (!a.measuredAt || a.mgDl === null || a.decision === 'rejected') continue;
    const key = dedupeKey(a.measuredAt, a.mgDl);
    if (seen.has(key)) a.allFlags.push('duplicate-batch'); else seen.set(key, a.id);
  }
  return assessed;
}

export function setDecision(batch: ImportBatch, id: string, decision: ImportCandidate['decision']): ImportBatch {
  return { ...batch, candidates: batch.candidates.map(c => c.id === id ? { ...c, decision } : c) };
}

/** Edit a row. Keeps `original` untouched; an edit clears parser warnings the user has now resolved. */
export function editCandidate(batch: ImportBatch, id: string, patch: Partial<Pick<ImportCandidate, 'value' | 'unit' | 'date' | 'time' | 'mealContext' | 'note'>>): ImportBatch {
  return { ...batch, candidates: batch.candidates.map(c => c.id === id ? { ...c, ...patch, ...((patch.date !== undefined && patch.date !== c.date) || (patch.time !== undefined && patch.time !== c.time) ? { sourceInstant: undefined } : {}), unitSource: patch.unit && patch.unit !== c.unit ? 'explicit' : c.unitSource, edited: true, decision: c.decision === 'rejected' ? 'pending' : c.decision } : c) };
}

/** Bulk actions. "confirm-clean" only confirms rows with no flag at all; flagged rows stay pending. */
export function bulk(batch: ImportBatch, action: 'confirm-clean' | 'reject-all' | 'reject-flagged' | 'reset', existing: GlucoseReading[], now = new Date()): ImportBatch {
  const assessed = new Map(assessBatch(batch, existing, now).map(a => [a.id, a]));
  return { ...batch, candidates: batch.candidates.map(c => {
    const a = assessed.get(c.id)!; const flagged = needsAttention(a);
    if (action === 'confirm-clean') return !flagged && c.decision === 'pending' ? { ...c, decision: 'confirmed' } : c;
    if (action === 'reject-all') return { ...c, decision: 'rejected' };
    if (action === 'reject-flagged') return flagged && c.decision !== 'confirmed' ? { ...c, decision: 'rejected' } : c;
    return { ...c, decision: 'pending' };
  }) };
}

/** Whether a single row may be confirmed (explicitly, by the user). */
export function canConfirm(a: AssessedCandidate): { ok: boolean; reason: string | null } {
  const hard = a.allFlags.filter(f => HARD.includes(f));
  if (a.error) return { ok: false, reason: a.error };
  if (hard.length) return { ok: false, reason: hard.map(f => flagText[f]).join('; ') };
  return { ok: true, reason: null };
}

export type ReviewSummary = { total: number; confirmed: number; rejected: number; pending: number; flagged: number; clean: number; blockedConfirmed: number };
export function summarize(assessed: AssessedCandidate[]): ReviewSummary {
  const flagged = assessed.filter(needsAttention).length;
  return { total: assessed.length, confirmed: assessed.filter(a => a.decision === 'confirmed').length, rejected: assessed.filter(a => a.decision === 'rejected').length, pending: assessed.filter(a => a.decision === 'pending').length, flagged, clean: assessed.length - flagged, blockedConfirmed: assessed.filter(a => a.decision === 'confirmed' && !canConfirm(a).ok).length };
}

/** Only confirmed rows that pass validation and are not duplicates become drafts. */
export function draftsToSave(batch: ImportBatch, existing: GlucoseReading[], now = new Date()): { drafts: GlucoseDraft[]; blocked: { id: string; reason: string }[] } {
  const drafts: GlucoseDraft[] = []; const blocked: { id: string; reason: string }[] = [];
  for (const a of assessBatch(batch, existing, now)) {
    if (a.decision !== 'confirmed') continue;
    const ok = canConfirm(a);
    if (!ok.ok || !a.measuredAt || a.mgDl === null || !a.unit) { blocked.push({ id: a.id, reason: ok.reason || a.error || 'Incomplete row.' }); continue; }
    if (a.allFlags.includes('duplicate-batch')) { blocked.push({ id: a.id, reason: flagText['duplicate-batch'] }); continue; }
    const v = validateGlucoseInput({ value: a.value, unit: a.unit, date: a.date, time: a.time, tzOffsetMinutes: a.tzOffsetMinutes ?? undefined, tzName: null, mealContext: a.mealContext, note: a.note }, { now });
    if (!v.ok) { blocked.push({ id: a.id, reason: v.error }); continue; }
    const p = a.provenance;
    drafts.push({ ...v.draft, measuredAt: a.measuredAt, source: {
      type: sourceType(a), provider: p.provider, device: p.device, recordId: p.recordId,
      meta: { format: p.format, fileName: p.fileName, fileSha256: p.fileSha256, locator: p.locator, raw: p.raw, engine: p.engine, confidence: a.confidence, flags: a.allFlags, edited: a.edited, originalValue: a.original.value, originalUnit: a.original.unit, unitSource: a.unitSource },
      batchId: batch.id, dedupeKey: dedupeKey(v.draft.measuredAt, v.draft.valueMgDl),
    } });
  }
  return { drafts, blocked };
}

/** Device samples arrive with an exact instant: render it as the wall clock at its offset. */
export function wallClockStrings(instant: string, offsetMinutes: number) { const c = instantToWallClock(instant, offsetMinutes); return { date: displayDate(c), time: displayTime(c) }; }
