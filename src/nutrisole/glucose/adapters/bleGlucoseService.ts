// RESEARCH-ONLY prototype for the Bluetooth SIG Glucose Service (0x1808).
// Parses Glucose Measurement (0x2A18) bytes per GLS v1.0.1. It is NOT wired to any BLE
// stack, needs no native package, and the adapter below is disabled until a specific
// meter (candidate: Accu-Chek Instant, Bluetooth model) passes a real hardware test.
import type { ConnectionStatus, GlucoseImportAdapter, ImportedSample } from '../types';

export const GLUCOSE_SERVICE = 0x1808;
export const GLUCOSE_MEASUREMENT = 0x2a18;
export const GLUCOSE_MEASUREMENT_CONTEXT = 0x2a34;
export const GLUCOSE_FEATURE = 0x2a51;
export const RECORD_ACCESS_CONTROL_POINT = 0x2a52; // resolve ONLY inside service 0x1808 (vendor decoy reuses this UUID)

/** IEEE-11073 16-bit SFLOAT. Returns null for NaN/NRes/±INF/reserved. */
export function decodeSfloat(raw: number): number | null {
  const v = raw & 0xffff;
  if ([0x07ff, 0x0800, 0x07fe, 0x0802, 0x0801].includes(v)) return null;
  let mantissa = v & 0x0fff; if (mantissa >= 0x0800) mantissa -= 0x1000;
  let exponent = v >> 12; if (exponent >= 0x8) exponent -= 0x10;
  return exponent < 0 ? mantissa / 10 ** -exponent : mantissa * 10 ** exponent;
}

const typeNames: Record<number, ImportedSample['specimen']> = { 1: 'capillary_blood', 2: 'capillary_blood', 3: 'whole_blood', 4: 'plasma', 5: 'whole_blood', 6: 'plasma', 7: 'whole_blood', 8: 'plasma', 9: 'interstitial_fluid' };

export type GlsMeasurement = { sequence: number; baseTime: string; offsetMinutes: number; value: string | null; unit: 'mg/dL' | 'mmol/L'; specimen: ImportedSample['specimen']; controlSolution: boolean; contextFollows: boolean };

export function parseGlucoseMeasurement(bytes: Uint8Array): GlsMeasurement {
  if (bytes.length < 10) throw new RangeError('Glucose Measurement too short.');
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const flags = dv.getUint8(0); let i = 1;
  const sequence = dv.getUint16(i, true); i += 2;
  const year = dv.getUint16(i, true); const month = dv.getUint8(i + 2); const day = dv.getUint8(i + 3); const hour = dv.getUint8(i + 4); const minute = dv.getUint8(i + 5); const second = dv.getUint8(i + 6); i += 7;
  let offsetMinutes = 0; if (flags & 0x01) { offsetMinutes = dv.getInt16(i, true); i += 2; }
  let value: string | null = null; let specimen: ImportedSample['specimen'] = 'unknown'; let controlSolution = false;
  const unit = flags & 0x04 ? 'mmol/L' as const : 'mg/dL' as const;
  if (flags & 0x02) {
    const conc = decodeSfloat(dv.getUint16(i, true)); const typeLoc = dv.getUint8(i + 2); i += 3;
    const type = typeLoc & 0x0f; controlSolution = type === 10; specimen = typeNames[type] || 'unknown';
    // kg/L → mg/dL ×1e5 ; mol/L → mmol/L ×1e3. Rounded to the unit's display precision.
    if (conc !== null) value = unit === 'mg/dL' ? String(Math.round(conc * 1e5)) : (Math.round(conc * 1e3 * 10) / 10).toFixed(1);
  }
  // User-facing time = Base Time + Time Offset (both are meter wall clock; meter zone unknown).
  const wall = Date.UTC(year, month - 1, day, hour, minute, second) + offsetMinutes * 60_000;
  return { sequence, baseTime: new Date(wall).toISOString().replace('Z', ''), offsetMinutes, value, unit, specimen, controlSolution, contextFollows: Boolean(flags & 0x10) };
}

export const bleGlucoseAdapter: GlucoseImportAdapter = {
  id: 'ble_meter', label: 'Bluetooth meter (Glucose Service 0x1808)', evidence: 'REQUIRES HARDWARE TEST', enabled: false,
  async status(): Promise<ConnectionStatus> { return { state: 'research-only', reason: 'Direct Bluetooth import needs a hardware-tested meter and a BLE native module. Not available in this build.' }; },
  async requestPermission() { return this.status(); },
  async readSince() { throw new Error('Bluetooth import is disabled (research only).'); },
};
