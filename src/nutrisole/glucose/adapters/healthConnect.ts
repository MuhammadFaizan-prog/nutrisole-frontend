// RESEARCH-ONLY contract for Android Health Connect BloodGlucoseRecord.
// The mapper is pure and tested with synthetic records. The adapter is disabled: no
// native package is added, no permission is requested, and no Pakistan-available meter
// app is documented to write finger-prick readings to Health Connect.
import type { ConnectionStatus, GlucoseImportAdapter, ImportedSample, MealContext } from '../types';

export const HEALTH_CONNECT_READ_PERMISSION = 'android.permission.health.READ_BLOOD_GLUCOSE';
/** Subset of androidx.health.connect.client.records.BloodGlucoseRecord as surfaced by a bridge. */
export type HealthConnectBloodGlucose = { metadata: { id: string; dataOrigin: string }; time: string; zoneOffsetSeconds?: number | null; level: { inMilligramsPerDeciliter: number }; specimenSource: number; relationToMeal: number };

const specimen: Record<number, ImportedSample['specimen']> = { 0: 'unknown', 1: 'interstitial_fluid', 2: 'capillary_blood', 3: 'plasma', 4: 'plasma', 6: 'whole_blood' };
const relation: Record<number, MealContext> = { 0: 'unspecified', 1: 'random', 2: 'fasting', 3: 'before_meal', 4: 'after_meal' };

export function mapHealthConnectRecord(r: HealthConnectBloodGlucose): ImportedSample {
  return {
    sourceRecordId: r.metadata.id, provider: r.metadata.dataOrigin, device: null, measuredAt: new Date(r.time).toISOString(),
    tzOffsetMinutes: Math.round((r.zoneOffsetSeconds ?? 0) / 60),
    // Health Connect stores mg/dL internally; keep that as the original unit (no double conversion).
    value: String(Math.round(r.level.inMilligramsPerDeciliter * 10) / 10), unit: 'mg/dL',
    specimen: specimen[r.specimenSource] || 'unknown', mealContext: relation[r.relationToMeal] || 'unspecified',
  };
}

export const healthConnectAdapter: GlucoseImportAdapter = {
  id: 'health_connect', label: 'Android Health Connect', evidence: 'UNVERIFIED', enabled: false,
  async status(): Promise<ConnectionStatus> { return { state: 'research-only', reason: 'Health Connect import is not enabled in this build. No Pakistan-available meter app is documented to write finger-prick readings to it yet.' }; },
  async requestPermission() { return this.status(); },
  async readSince() { throw new Error('Health Connect import is disabled (research only).'); },
};
