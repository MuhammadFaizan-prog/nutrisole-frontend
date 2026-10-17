// Device sources → review candidates. Health Connect / HealthKit give exact instants with
// a zone offset; a Bluetooth meter gives its own wall clock (zone unknown), so those rows
// carry a 'meter-clock' flag and use this phone's offset at that wall-clock time.
import type { MealContext } from '../types';
import type { CandidateFlag, ImportBatch, ImportCandidate, NonGlucoseFinding } from './types';
import { wallClockStrings } from './review';
import { displayDate, displayTime } from './dates';
import type { GlsDownload } from './gls';
import { plausibilityFlags } from './unitDetect';
import { deviceOffsetMinutes } from '../time';

export function newBatchId(prefix: string, now = new Date()) { return `${prefix}-${now.getTime().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; }

export function emptyBatch(partial: Pick<ImportBatch, 'id' | 'method' | 'format' | 'title'> & Partial<ImportBatch>): ImportBatch {
  return { fileName: null, fileSha256: null, createdAt: new Date().toISOString(), candidates: [], nonGlucose: [], notes: [], table: null, ocrConfidence: null, ...partial };
}

// ---- Bluetooth GLS ----
export function glsToBatch(download: GlsDownload, device: { id: string; name: string | null }, now = new Date()): ImportBatch {
  const id = newBatchId('ble', now);
  const candidates: ImportCandidate[] = []; const nonGlucose: NonGlucoseFinding[] = []; const notes: string[] = [download.message];
  for (const r of download.records) {
    if (r.context?.hba1cPercent != null) nonGlucose.push({ kind: 'hba1c', label: 'HbA1c (from meter context)', value: String(r.context.hba1cPercent), unit: '%', raw: r.context.raw, locator: `sequence ${r.sequence}` });
    if (r.value === null) continue;
    const [y, mo, d, h, mi] = r.wallClock.split(/[-T:]/).map(Number);
    const clock = { year: y, month: mo - 1, day: d, hour: h, minute: mi };
    const flags: CandidateFlag[] = ['meter-clock', ...plausibilityFlags(r.value, r.unit)];
    if (r.specimen === 'control_solution') flags.push('control-solution');
    else if (r.specimen === 'interstitial_fluid' || r.specimen.startsWith('venous') || r.specimen.startsWith('arterial')) flags.push('specimen');
    if (r.sensorStatus.length) flags.push('sensor-status');
    const meal: MealContext = r.context?.meal || 'unspecified';
    candidates.push({
      id: `${id}-s${r.sequence}`, value: r.value, unit: r.unit, unitSource: 'device', date: displayDate(clock), time: displayTime(clock), tzOffsetMinutes: deviceOffsetMinutes(clock), sourceInstant: new Date(Date.parse(`${r.wallClock}Z`) - deviceOffsetMinutes(clock) * 60_000).toISOString(),
      mealContext: meal, note: [r.sensorStatus.length ? `Meter warning: ${r.sensorStatus.join(', ')}` : '', r.location !== 'finger' && r.location !== 'not available' ? `Site: ${r.location}` : ''].filter(Boolean).join(' · '),
      confidence: 1, flags, original: { value: r.value, unit: r.unit },
      provenance: { method: 'ble_meter', format: 'ble_gls', provider: 'ble:gls', recordId: `seq${r.sequence}@${r.wallClock}`, device: device.id, fileName: null, fileSha256: null, locator: `sequence ${r.sequence}`, raw: r.raw, engine: null },
      decision: 'pending', edited: false,
    });
  }
  if (download.parseErrors.length) notes.push(`${download.parseErrors.length} record(s) could not be decoded and were skipped.`);
  return emptyBatch({ id, method: 'ble_meter', format: 'ble_gls', title: device.name || 'Bluetooth meter', candidates, nonGlucose, notes });
}

// ---- Health Connect (react-native-health-connect BloodGlucoseRecord result) ----
export type HealthConnectGlucoseResult = { metadata?: { id?: string; dataOrigin?: string }; time: string; zoneOffset?: { totalSeconds: number } | null; level: { inMilligramsPerDeciliter: number; inMillimolesPerLiter?: number }; specimenSource?: number; relationToMeal?: number; mealType?: number };
const HC_SPECIMEN: Record<number, string> = { 0: 'unknown', 1: 'interstitial_fluid', 2: 'capillary_blood', 3: 'plasma', 4: 'serum', 5: 'tears', 6: 'whole_blood' };
const HC_RELATION: Record<number, MealContext> = { 0: 'unspecified', 1: 'random', 2: 'fasting', 3: 'before_meal', 4: 'after_meal' };

export function healthConnectToBatch(records: HealthConnectGlucoseResult[], now = new Date()): ImportBatch {
  const id = newBatchId('hc', now);
  const candidates: ImportCandidate[] = records.filter(r => r.metadata?.id).map(r => {
    const offset = Math.round((r.zoneOffset?.totalSeconds ?? -new Date(r.time).getTimezoneOffset() * 60) / 60);
    const w = wallClockStrings(new Date(r.time).toISOString(), offset);
    // Health Connect stores mg/dL; keep that as the original unit (no double conversion).
    const value = String(Math.round(r.level.inMilligramsPerDeciliter * 10) / 10);
    const specimen = HC_SPECIMEN[r.specimenSource ?? 0] || 'unknown';
    const flags: CandidateFlag[] = [...plausibilityFlags(value, 'mg/dL')];
    if (specimen === 'interstitial_fluid' || specimen === 'tears') flags.push('specimen');
    return {
      id: `${id}-${r.metadata!.id}`, value, unit: 'mg/dL' as const, unitSource: 'device' as const, date: w.date, time: w.time, tzOffsetMinutes: offset, sourceInstant: new Date(r.time).toISOString(),
      mealContext: HC_RELATION[r.relationToMeal ?? 0] || 'unspecified', note: specimen === 'unknown' || specimen === 'capillary_blood' ? '' : `Specimen: ${specimen.replace('_', ' ')}`,
      confidence: 1, flags, original: { value: String(r.level.inMilligramsPerDeciliter), unit: 'mg/dL' },
      provenance: { method: 'health_connect' as const, format: 'health_connect' as const, provider: r.metadata?.dataOrigin || 'health_connect', recordId: r.metadata!.id!, device: null, fileName: null, fileSha256: null, locator: `record ${r.metadata!.id}`, raw: JSON.stringify({ time: r.time, mgdl: r.level.inMilligramsPerDeciliter, specimen: r.specimenSource, relation: r.relationToMeal }).slice(0, 200), engine: null },
      decision: 'pending' as const, edited: false,
    };
  });
  return emptyBatch({ id, method: 'health_connect', format: 'health_connect', title: 'Health Connect', candidates, notes: candidates.length ? [] : ['Health Connect returned no blood glucose records for that period.'] });
}

// ---- Apple HealthKit (typed only; no iOS build here) ----
export type HealthKitGlucoseSample = { uuid: string; startDate: string; /** mg/dL */ value: number; sourceName?: string; sourceBundleId?: string; metadata?: { HKBloodGlucoseMealTime?: 1 | 2 } };
export function healthKitToBatch(samples: HealthKitGlucoseSample[], now = new Date()): ImportBatch {
  const id = newBatchId('hk', now);
  const candidates: ImportCandidate[] = samples.map(s => {
    const offset = -new Date(s.startDate).getTimezoneOffset(); const w = wallClockStrings(new Date(s.startDate).toISOString(), offset);
    const value = String(Math.round(s.value * 10) / 10);
    return { id: `${id}-${s.uuid}`, value, unit: 'mg/dL' as const, unitSource: 'device' as const, date: w.date, time: w.time, tzOffsetMinutes: offset, mealContext: s.metadata?.HKBloodGlucoseMealTime === 1 ? 'before_meal' as const : s.metadata?.HKBloodGlucoseMealTime === 2 ? 'after_meal' as const : 'unspecified' as const, note: '', confidence: 1, flags: plausibilityFlags(value, 'mg/dL'), original: { value: String(s.value), unit: 'mg/dL' }, provenance: { method: 'healthkit' as const, format: 'healthkit' as const, provider: s.sourceBundleId || 'healthkit', recordId: s.uuid, device: s.sourceName || null, fileName: null, fileSha256: null, locator: `sample ${s.uuid}`, raw: JSON.stringify(s).slice(0, 200), engine: null }, decision: 'pending' as const, edited: false };
  });
  return emptyBatch({ id, method: 'healthkit', format: 'healthkit', title: 'Apple Health', candidates });
}
