// Shared contracts for every non-manual way of getting readings in (file, OCR, device).
// Each path produces ImportCandidates that land on the review screen; nothing is saved
// until the user confirms rows there (see review.ts).
import type { GlucoseUnit, MealContext } from '../types';

export type ImportMethod = 'file' | 'ocr' | 'health_connect' | 'healthkit' | 'ble_meter';
export type ImportFormat = 'csv' | 'xlsx' | 'pdf-text' | 'pdf-ocr' | 'image-ocr' | 'camera-ocr' | 'health_connect' | 'healthkit' | 'ble_gls';

/** How the unit of a candidate was established. `inferred` always carries a flag. */
export type UnitSource = 'explicit' | 'column' | 'report' | 'inferred' | 'device';

export type CandidateFlag =
  | 'unit-inferred' | 'unit-ambiguous' | 'implausible' | 'out-of-range' | 'missing-date' | 'missing-time' | 'year-assumed'
  | 'future' | 'duplicate-existing' | 'duplicate-batch' | 'already-imported' | 'low-confidence' | 'specimen' | 'control-solution'
  | 'sensor-status' | 'meter-clock' | 'invalid';

export type Provenance = {
  method: ImportMethod;
  format: ImportFormat;
  /** Stable provider label stored in source_provider, e.g. "file:csv", "ocr:PP-OCRv5 mobile (on-device)", "ble:gls". */
  provider: string;
  /** Immutable source-side id stored in source_record_id (file hash + row, BLE sequence, HC record id). */
  recordId: string;
  device: string | null;
  fileName: string | null;
  fileSha256: string | null;
  /** Human locator: "row 5", "page 1 line 12", "sequence 7". */
  locator: string;
  /** Exact source text/bytes summary the value was read from (trimmed to 200 chars). */
  raw: string;
  engine: string | null;
};

export type ImportCandidate = {
  id: string;
  /** Editable fields, in the same display formats manual entry uses ("Oct 16, 2026", "8:15 AM"). */
  value: string;
  unit: GlucoseUnit | null;
  unitSource: UnitSource;
  date: string;
  time: string;
  /** Exact offset when the source supplies one (Health Connect, HealthKit); otherwise device offset. */
  tzOffsetMinutes: number | null;
  mealContext: MealContext;
  note: string;
  /** 0..1 parser confidence; < LOW_CONFIDENCE adds a flag. */
  confidence: number;
  /** Parser-level flags (review.ts adds validation / duplicate flags on top). */
  flags: CandidateFlag[];
  /** The value and unit exactly as found in the source, before any edit. */
  original: { value: string; unit: string | null };
  provenance: Provenance;
  decision: 'pending' | 'confirmed' | 'rejected';
  edited: boolean;
};

/** A lab value that is not a glucose reading (HbA1c, eAG, urine sugar...). Shown, never imported. */
export type NonGlucoseFinding = { kind: 'hba1c' | 'eag' | 'urine' | 'ogtt' | 'other'; label: string; value: string; unit: string; raw: string; locator: string };

export type TabularMapping = {
  header: string[];
  headerRow: number;
  datetime: number | null; date: number | null; time: number | null; value: number | null; unit: number | null; context: number | null; note: number | null;
  /** Unit stated once for the whole value column, e.g. "Reading [mg/dL]". */
  columnUnit: GlucoseUnit | null;
  dateOrder: 'DMY' | 'MDY' | 'YMD';
  auto: boolean;
  /** Why each column was chosen (shown in the mapper). */
  reasons: string[];
};

export type ImportBatch = {
  id: string;
  method: ImportMethod;
  format: ImportFormat;
  title: string;
  fileName: string | null;
  fileSha256: string | null;
  createdAt: string;
  candidates: ImportCandidate[];
  nonGlucose: NonGlucoseFinding[];
  /** Plain-language notes about the whole file (skipped rows, scanned PDF, OCR engine...). */
  notes: string[];
  /** Present for CSV/XLSX: the parsed table and the current column mapping. */
  table: { rows: string[][]; mapping: TabularMapping } | null;
  /** Mean OCR confidence 0..1 when OCR was used. */
  ocrConfidence: number | null;
};

export const LOW_CONFIDENCE = 0.6;
export const MAX_IMPORT_ROWS = 2000;
