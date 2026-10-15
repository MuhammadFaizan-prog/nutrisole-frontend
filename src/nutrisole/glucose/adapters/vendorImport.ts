// Vendor cloud API / CSV import: UNSUPPORTED. No public SMBG API was found for the
// researched vendors, and no real export sample is available to define a parser.
import type { ConnectionStatus, GlucoseImportAdapter } from '../types';
export const vendorImportAdapter: GlucoseImportAdapter = {
  id: 'vendor_import', label: 'Vendor export (CSV)', evidence: 'UNSUPPORTED', enabled: false,
  async status(): Promise<ConnectionStatus> { return { state: 'research-only', reason: 'No documented vendor API or verified export format. Not available.' }; },
  async requestPermission() { return this.status(); },
  async readSince() { throw new Error('Vendor import is disabled (research only).'); },
};
