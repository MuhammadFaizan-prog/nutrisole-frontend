// Import UI state + the plain strings the shared scene builder renders for the import
// chooser and the review screen (web and native).
import type { GlucoseReading } from '../types';
import { contextLabel } from '../validation';
import type { ImportBatch } from './types';
import { assessBatch, flagText, summarize, INFO, type AssessedCandidate } from './review';
import type { BleMeter } from './scan';

export const IMPORT_PAGE_SIZE = 40;
export type ImportUiState = { batch: ImportBatch | null; busy: string | null; error: string | null; saving: boolean; result: string | null; lastSequence: Record<string, number>; foundMeters?: BleMeter[]; page?: number };
export const initialImportState = (): ImportUiState => ({ batch: null, busy: null, error: null, saving: false, result: null, lastSequence: {} });

export type ImportRowView = { id: string; title: string; description: string; decision: 'pending' | 'confirmed' | 'rejected'; flagged: boolean; icon: string };
export type ImportView = {
  platform: 'web' | 'native';
  busy: string | null; saving: boolean; error: string | null; result: string | null;
  hasBatch: boolean; title: string; subtitle: string; summary: string;
  notes: string[]; nonGlucose: string | null; mapping: { label: string; value: string } | null;
  rows: ImportRowView[]; hiddenRows: number; confirmed: number; saveLabel: string; canSave: boolean;
  page: number; pageCount: number; pageStart: number; pageEnd: number; totalRows: number;
  meters: BleMeter[]; importedCount: number; lastImport: string;
};

const methodLabel: Record<ImportBatch['format'], string> = { csv: 'CSV file', xlsx: 'Excel file', 'pdf-text': 'PDF report', 'pdf-ocr': 'Scanned report', 'image-ocr': 'Photo', 'camera-ocr': 'Photo', health_connect: 'Health Connect', healthkit: 'Apple Health', ble_gls: 'Bluetooth meter' };

export function rowView(a: AssessedCandidate): ImportRowView {
  const issues = a.allFlags.filter(f => !INFO.includes(f));
  const short = (t: string) => (t.length > 40 ? `${t.slice(0, 39)}…` : t);
  const flags = issues.length ? `⚠ ${short(flagText[issues[0]])}${issues.length > 1 ? ` +${issues.length - 1}` : ''}` : a.allFlags.length ? short(flagText[a.allFlags[0]]) : 'No issues found';
  const when = a.date || a.time ? `${a.date || 'No date'} · ${a.time || 'no time'}` : 'No date or time';
  return {
    id: a.id, title: `${a.value} ${a.unit || ''}`,
    description: `${when}${a.mealContext === 'unspecified' ? '' : ` · ${contextLabel(a.mealContext)}`}${issues.length ? `\n${flags.replace('⚠ ', '')}` : ''}`,
    decision: a.decision, flagged: issues.length > 0 || a.error !== null,
    icon: a.decision === 'confirmed' ? 'Check' : a.decision === 'rejected' ? 'Trash2' : issues.length ? 'TriangleAlert' : 'Clock3',
  };
}

export function buildImportView(ui: ImportUiState | undefined, existing: GlucoseReading[], platform: 'web' | 'native', now = new Date(), maxRows = IMPORT_PAGE_SIZE): ImportView {
  const s = ui ?? initialImportState(); const b = s.batch;
  const assessed = b ? assessBatch(b, existing, now) : [];
  const sum = summarize(assessed);
  const pageSize = Math.max(1, Math.floor(maxRows) || IMPORT_PAGE_SIZE);
  const pageCount = Math.max(1, Math.ceil(assessed.length / pageSize));
  const page = Math.max(0, Math.min(pageCount - 1, Math.floor(s.page || 0)));
  const pageStart = page * pageSize; const pageEnd = Math.min(assessed.length, pageStart + pageSize);
  const m = b?.table?.mapping;
  const col = (i: number | null) => (i === null || !m ? '—' : m.header[i] || `column ${i + 1}`);
  const imported = existing.filter(r => r.source.type !== 'manual');
  const lastImport = imported.reduce<string | null>((last, r) => last === null || r.createdAt > last ? r.createdAt : last, null);
  return {
    meters: s.foundMeters || [], importedCount: imported.length,
    lastImport: lastImport ? `${lastImport.replace('T', ' ').slice(0, 16)} UTC` : 'No imports saved',
    platform, busy: s.busy, saving: s.saving, error: s.error, result: s.result,
    hasBatch: Boolean(b), title: b ? b.title : 'Nothing to review', subtitle: b ? methodLabel[b.format] : 'Attach a file, scan a report or import from a device first.',
    summary: b ? `${sum.total} reading${sum.total === 1 ? '' : 's'} · ${sum.confirmed} confirmed` : '',
    notes: b?.notes.filter(Boolean).slice(0, 3) ?? [],
    nonGlucose: b?.nonGlucose.length ? `Not imported as glucose: ${b.nonGlucose.map(n => `${n.label} ${n.value}${n.unit ? ` ${n.unit}` : ''}`).join(' · ')}` : null,
    mapping: m ? { label: m.auto ? 'Columns · detected' : 'Columns · set by you', value: `Value: ${col(m.value)}${m.columnUnit ? ` (${m.columnUnit})` : m.unit !== null ? ` · Unit: ${col(m.unit)}` : ''} · ${m.datetime !== null ? `Date & time: ${col(m.datetime)}` : `Date: ${col(m.date)} · Time: ${col(m.time)}`} · ${m.dateOrder}` } : null,
    page, pageCount, pageStart, pageEnd, totalRows: assessed.length,
    rows: assessed.slice(pageStart, pageEnd).map(rowView), hiddenRows: Math.max(0, assessed.length - pageSize),
    confirmed: sum.confirmed, saveLabel: s.saving ? 'Saving…' : s.busy ? 'Transfer in progress…' : sum.confirmed ? `Save ${sum.confirmed} reading${sum.confirmed === 1 ? '' : 's'}` : 'Review readings', canSave: assessed.some(c => c.decision !== 'rejected') && !s.saving && !s.busy,
  };
}
