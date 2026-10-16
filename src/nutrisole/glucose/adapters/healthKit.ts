// RESEARCH-ONLY contract for Apple HealthKit (HKQuantityTypeIdentifier.bloodGlucose).
// Disabled: iOS native work needs macOS/Xcode and an iPhone for permission testing.
import type { ConnectionStatus, GlucoseImportAdapter } from '../types';
export const HEALTHKIT_TYPE = 'HKQuantityTypeIdentifierBloodGlucose';
export const healthKitAdapter: GlucoseImportAdapter = {
  id: 'healthkit', label: 'Apple Health', evidence: 'UNVERIFIED', enabled: false,
  async status(): Promise<ConnectionStatus> { return { state: 'research-only', reason: 'Apple Health import is planned for a later iOS build. Not available here.' }; },
  async requestPermission() { return this.status(); },
  async readSince() { throw new Error('Apple Health import is disabled (research only).'); },
};
