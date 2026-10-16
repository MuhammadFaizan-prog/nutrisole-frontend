// Shared import reconciliation for every future adapter. Pure and unit-tested.
// Rules: finger-prick (capillary) samples only; the original value/unit is kept; the
// source record id makes re-imports idempotent; nothing is merged with manual entries.
import type { GlucoseDraft, GlucoseReading, ImportedSample, ImportResult, GlucoseSourceType } from '../types';
import { decimalPlaces, hardRange, maxDecimals, normalizeDecimal, toMgDl } from '../units';

export function importKey(type: GlucoseSourceType, provider: string, device: string | null, recordId: string) { return `${type}|${provider}|${device ?? ''}|${recordId}`; }

export function reconcileImport(type: Exclude<GlucoseSourceType, 'manual'>, samples: ImportedSample[], existing: GlucoseReading[], now = new Date()): { drafts: GlucoseDraft[]; result: Omit<ImportResult, 'cursor'> } {
  const seen = new Set(existing.filter(r => r.source.recordId && r.source.provider).map(r => importKey(r.source.type, r.source.provider || '', r.source.device, r.source.recordId || '')));
  const drafts: GlucoseDraft[] = []; const rejected: ImportResult['rejected'] = []; let skippedDuplicates = 0;
  // Out-of-order downloads are fine: order does not affect identity.
  for (const s of samples) {
    const key = importKey(type, s.provider, s.device, s.sourceRecordId);
    if (!s.sourceRecordId || !s.provider) { rejected.push({ sourceRecordId: s.sourceRecordId || '(missing)', reason: 'Missing stable source id or provider.' }); continue; }
    if (seen.has(key)) { skippedDuplicates++; continue; }
    if (s.specimen !== 'capillary_blood' && s.specimen !== 'whole_blood') { rejected.push({ sourceRecordId: s.sourceRecordId, reason: s.specimen === 'interstitial_fluid' ? 'CGM/interstitial readings are outside this strip-meter feature.' : 'Specimen type is not a finger-prick reading; needs user confirmation.' }); continue; }
    const value = normalizeDecimal(s.value);
    const [min, max] = hardRange[s.unit] || [0, 0];
    if (!value || decimalPlaces(value) > maxDecimals[s.unit] || Number(value) < min || Number(value) > max) { rejected.push({ sourceRecordId: s.sourceRecordId, reason: 'Value/unit outside the possible meter range; not reinterpreted.' }); continue; }
    if (Number.isNaN(Date.parse(s.measuredAt)) || Date.parse(s.measuredAt) > now.getTime() + 5 * 60_000) { rejected.push({ sourceRecordId: s.sourceRecordId, reason: 'Missing or future measurement time.' }); continue; }
    seen.add(key);
    drafts.push({ measuredAt: new Date(s.measuredAt).toISOString(), tzOffsetMinutes: s.tzOffsetMinutes, tzName: null, valueOriginal: value, unitOriginal: s.unit, valueMgDl: toMgDl(value, s.unit), mealContext: s.mealContext || 'unspecified', note: null, source: { type, provider: s.provider, device: s.device, recordId: s.sourceRecordId } });
  }
  return { drafts, result: { imported: drafts.length, skippedDuplicates, rejected } };
}
