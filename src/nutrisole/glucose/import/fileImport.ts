// One entry point for "attach a file" and "scan a report": detects the file type and
// routes it to the tabular parser, the PDF text layer (with OCR fallback for scans) or
// OCR. Text extraction and OCR are injected per platform (pdf.js + tesseract.js on web,
// ML Kit on Android/iOS), so this module stays pure and testable.
import type { ImportBatch, ImportFormat } from './types';
import { autoMap, parseDelimited, rowsToCandidates } from './tabular';
import { isXlsx, readXlsx } from './xlsx';
import { parseReportText, type TextLine } from './labText';
import { sha256Hex } from './sha256';
import { emptyBatch, newBatchId } from './devices';

export type PickedFile = { name: string; mime: string | null; bytes: Uint8Array };
export type OcrResult = { lines: TextLine[]; confidence: number | null; engine: string };
export type TextExtractors = {
  /** PDF text layer as lines (null when this platform cannot read PDFs). */
  pdfText?: (bytes: Uint8Array) => Promise<TextLine[] | null>;
  /** Rasterise a scanned PDF and OCR it (null when unsupported). */
  pdfOcr?: (bytes: Uint8Array, onProgress?: (p: string) => void) => Promise<OcrResult | null>;
  /** OCR an image file/photo. */
  imageOcr?: (file: PickedFile, onProgress?: (p: string) => void, mode?: 'document' | 'sparse') => Promise<OcrResult>;
};
export class ImportFileError extends Error { kind: 'unsupported' | 'empty' | 'too-large' | 'unreadable'; constructor(kind: ImportFileError['kind'], message: string) { super(message); this.kind = kind; this.name = 'ImportFileError'; } }

export const MAX_FILE_BYTES = 15 * 1024 * 1024;

export function detectKind(file: PickedFile): 'csv' | 'xlsx' | 'pdf' | 'image' | 'unknown' {
  const name = file.name.toLowerCase(); const mime = (file.mime || '').toLowerCase(); const b = file.bytes;
  if (b.length > 4 && b[0] === 0x25 && b[1] === 0x50 && b[2] === 0x44 && b[3] === 0x46) return 'pdf';
  if (isXlsx(b) && (name.endsWith('.xlsx') || mime.includes('spreadsheetml') || !name.includes('.'))) return 'xlsx';
  if ((b[0] === 0xff && b[1] === 0xd8) || (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) || (b[0] === 0x52 && b[1] === 0x49 && b[8] === 0x57 && b[9] === 0x45) || mime.startsWith('image/') || /\.(jpe?g|png|webp|heic|bmp)$/.test(name)) return 'image';
  if (name.endsWith('.xls')) return 'unknown';
  if (/\.(csv|tsv|txt)$/.test(name) || mime.includes('csv') || mime.startsWith('text/')) return 'csv';
  return 'unknown';
}

export async function fileToBatch(file: PickedFile, x: TextExtractors, opts: { camera?: boolean; now?: Date; onProgress?: (p: string) => void } = {}): Promise<ImportBatch> {
  if (!file.bytes.length) throw new ImportFileError('empty', 'This file is empty.');
  if (file.bytes.length > MAX_FILE_BYTES) throw new ImportFileError('too-large', 'This file is larger than 15 MB. Export a shorter date range or a smaller image.');
  const kind = detectKind(file);
  const sha = sha256Hex(file.bytes);
  const base = { fileName: file.name, fileSha256: sha };
  if (kind === 'csv' || kind === 'xlsx') {
    let rows: string[][]; const notes: string[] = [];
    if (kind === 'xlsx') { const wb = readXlsx(file.bytes); rows = wb.rows; notes.push(`Read worksheet "${wb.sheetName}" (first sheet only).`); }
    else rows = parseDelimited(decodeUtf8(file.bytes));
    if (!rows.length) throw new ImportFileError('empty', 'No rows were found in this file.');
    const id = newBatchId(kind, opts.now); const mapping = autoMap(rows);
    const res = rowsToCandidates(rows, mapping, { format: kind, fileName: file.name, fileSha256: sha, batchId: id });
    return emptyBatch({ id, method: 'file', format: kind, title: file.name, ...base, candidates: res.candidates, notes: [...notes, ...mapping.reasons.slice(0, 1), ...res.notes], table: { rows, mapping } });
  }
  if (kind === 'pdf') {
    const id = newBatchId('pdf', opts.now);
    const lines = x.pdfText ? await x.pdfText(file.bytes) : null;
    if (lines === null) throw new ImportFileError('unsupported', 'PDF reports can be read in the NutriSole web app. On this phone, scan the printed report with the camera or attach a photo of it.');
    const textChars = lines.reduce((n, l) => n + l.text.replace(/\s/g, '').length, 0);
    if (textChars >= 40) {
      const r = parseReportText(lines, { format: 'pdf-text', method: 'file', fileName: file.name, fileSha256: sha, batchId: id, engine: 'pdf.js text layer', now: opts.now });
      return emptyBatch({ id, method: 'file', format: 'pdf-text', title: file.name, ...base, candidates: r.candidates, nonGlucose: r.nonGlucose, notes: ['Read from the PDF text layer.', ...r.notes] });
    }
    const ocr = x.pdfOcr ? await x.pdfOcr(file.bytes, opts.onProgress) : null;
    if (!ocr) throw new ImportFileError('unsupported', 'This PDF is a scanned image without a text layer, and OCR for PDFs is not available here. Attach a photo of the page instead.');
    const r = parseReportText(ocr.lines, { format: 'pdf-ocr', method: 'ocr', fileName: file.name, fileSha256: sha, batchId: id, engine: ocr.engine, now: opts.now });
    return emptyBatch({ id, method: 'ocr', format: 'pdf-ocr', title: file.name, ...base, candidates: r.candidates, nonGlucose: r.nonGlucose, ocrConfidence: ocr.confidence, notes: [`Scanned PDF (no text layer): read with on-device OCR (${ocr.engine}).`, ...r.notes] });
  }
  if (kind === 'image') {
    if (!x.imageOcr) throw new ImportFileError('unsupported', 'Image OCR is not available on this platform.');
    const id = newBatchId(opts.camera ? 'scan' : 'img', opts.now);
    let ocr = await x.imageOcr(file, opts.onProgress, 'document');
    const format: ImportFormat = opts.camera ? 'camera-ocr' : 'image-ocr';
    const parse = (o: OcrResult) => parseReportText(o.lines, { format, method: 'ocr', fileName: file.name, fileSha256: sha, batchId: id, engine: o.engine, now: opts.now });
    let r = parse(ocr);
    if (!r.candidates.length && !r.nonGlucose.length) {
      // Meter screens: very large digits are often missed by document layout analysis; retry as sparse text.
      const sparse = await x.imageOcr(file, opts.onProgress, 'sparse');
      const r2 = parse(sparse); if (r2.candidates.length || r2.nonGlucose.length) { r = r2; ocr = sparse; }
    }
    return emptyBatch({ id, method: 'ocr', format, title: opts.camera ? 'Scanned report' : file.name, ...base, candidates: r.candidates, nonGlucose: r.nonGlucose, ocrConfidence: ocr.confidence, notes: [`Read on this device with ${ocr.engine}; every value needs your check.`, ...r.notes] });
  }
  throw new ImportFileError('unsupported', name(file) + ' is not a supported file. Use CSV, XLSX, PDF or an image (JPG/PNG).');
}
const name = (f: PickedFile) => f.name || 'This file';

/** UTF-8 decode that also works where TextDecoder is missing (older Hermes). Falls back to Latin-1 on invalid bytes. */
export function decodeUtf8(bytes: Uint8Array): string {
  if (typeof TextDecoder !== 'undefined') { try { return new TextDecoder('utf-8', { fatal: true }).decode(bytes); } catch { return Array.from(bytes, b => String.fromCharCode(b)).join(''); } }
  let out = ''; let i = 0;
  while (i < bytes.length) {
    const b = bytes[i];
    if (b < 0x80) { out += String.fromCharCode(b); i++; }
    else if (b >= 0xc2 && b < 0xe0 && i + 1 < bytes.length) { out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[i + 1] & 0x3f)); i += 2; }
    else if (b >= 0xe0 && b < 0xf0 && i + 2 < bytes.length) { out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[i + 1] & 0x3f) << 6) | (bytes[i + 2] & 0x3f)); i += 3; }
    else if (b >= 0xf0 && i + 3 < bytes.length) { const cp = ((b & 0x07) << 18) | ((bytes[i + 1] & 0x3f) << 12) | ((bytes[i + 2] & 0x3f) << 6) | (bytes[i + 3] & 0x3f); out += String.fromCodePoint(cp); i += 4; }
    else { out += String.fromCharCode(b); i++; }
  }
  return out;
}

/** Re-run the tabular parser after the user changes the column mapping. */
export function remapBatch(batch: ImportBatch, mapping: NonNullable<ImportBatch['table']>['mapping']): ImportBatch {
  if (!batch.table) return batch;
  const res = rowsToCandidates(batch.table.rows, mapping, { format: batch.format, fileName: batch.fileName, fileSha256: batch.fileSha256, batchId: batch.id });
  return { ...batch, candidates: res.candidates, table: { rows: batch.table.rows, mapping }, notes: [mapping.auto ? 'Columns detected automatically.' : 'Columns set manually.', ...res.notes] };
}
