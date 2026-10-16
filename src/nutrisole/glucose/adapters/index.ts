import { bleGlucoseAdapter } from './bleGlucoseService';
import { healthConnectAdapter } from './healthConnect';
import { healthKitAdapter } from './healthKit';
import { vendorImportAdapter } from './vendorImport';
import type { GlucoseImportAdapter } from '../types';
/** Every adapter is disabled in this branch; the UI lists them as research-only. */
export const glucoseAdapters: readonly GlucoseImportAdapter[] = [healthConnectAdapter, healthKitAdapter, bleGlucoseAdapter, vendorImportAdapter];
