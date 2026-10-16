// NutriSole glucose domain contracts (finger-prick / test-strip readings only).
// Manual entry and every future import adapter write through the same validated
// boundary into one canonical record. Nothing here interprets a value clinically.

export type GlucoseUnit = 'mg/dL' | 'mmol/L';
export const glucoseUnits: readonly GlucoseUnit[] = ['mg/dL', 'mmol/L'];

/** Where a record came from. `file`/`ocr` and the device sources always pass the review screen first. */
export type GlucoseSourceType = 'manual' | 'file' | 'ocr' | 'health_connect' | 'healthkit' | 'ble_meter' | 'vendor_import';

/** Self-reported measurement context. Labels only, never a diagnosis. */
export type MealContext = 'fasting' | 'before_meal' | 'after_meal' | 'bedtime' | 'random' | 'other' | 'unspecified';
export const mealContexts: readonly { value: MealContext; label: string }[] = [
  { value: 'fasting', label: 'Fasting' },
  { value: 'before_meal', label: 'Before a meal' },
  { value: 'after_meal', label: 'After a meal' },
  { value: 'bedtime', label: 'Bedtime' },
  { value: 'random', label: 'Random' },
  { value: 'other', label: 'Other' },
];

export type GlucoseSource = {
  type: GlucoseSourceType;
  /** Stable provider id for imports (e.g. Health Connect data origin package). Null for manual. */
  provider: string | null;
  /** Optional device label/identifier supplied by an authorized source. Never a secret. */
  device: string | null;
  /** Immutable source-side record id used for idempotent import. Null for manual. */
  recordId: string | null;
  /** Import provenance (file name/hash, row/line, raw text, OCR engine, confidence, original value/unit). Null for manual. */
  meta?: Record<string, unknown> | null;
  /** Review batch the row was confirmed in (one file / scan / device sync). */
  batchId?: string | null;
  /** Content key (minute instant + mg/dL) used to spot the same reading from two sources. */
  dedupeKey?: string | null;
};

/** Canonical persisted reading (mirrors public.glucose_readings). */
export type GlucoseReading = {
  id: string;
  userId: string;
  /** ISO-8601 instant of the measurement on the meter (UTC). */
  measuredAt: string;
  /** Offset of the wall clock where the reading was taken, minutes east of UTC. */
  tzOffsetMinutes: number;
  tzName: string | null;
  /** Exactly what the user/source entered, as a decimal string (no float drift). */
  valueOriginal: string;
  unitOriginal: GlucoseUnit;
  /** Canonical mg/dL computed once from the original (DB generated column). */
  valueMgDl: number;
  mealContext: MealContext;
  note: string | null;
  source: GlucoseSource;
  /** When the row was created/imported in NutriSole (distinct from measuredAt). */
  createdAt: string;
  updatedAt: string;
};

/** What a user or adapter submits. Validation turns this into a GlucoseDraft. */
export type GlucoseInput = {
  value: string;
  unit: GlucoseUnit;
  /** Local wall-clock date "Oct 16, 2026" and time "8:15 AM" as shown in the existing UI. */
  date: string;
  time: string;
  /** Minutes east of UTC for that wall clock; defaults to the device offset on that date. */
  tzOffsetMinutes?: number;
  tzName?: string | null;
  mealContext: MealContext;
  note?: string;
};

/** Validated, normalized payload ready for a repository write. */
export type GlucoseDraft = {
  measuredAt: string;
  tzOffsetMinutes: number;
  tzName: string | null;
  valueOriginal: string;
  unitOriginal: GlucoseUnit;
  valueMgDl: number;
  mealContext: MealContext;
  note: string | null;
  source: GlucoseSource;
};

export type GlucoseWarningCode = 'unusual-low' | 'unusual-high' | 'possible-unit-mismatch' | 'possible-duplicate';
export type GlucoseWarning = { code: GlucoseWarningCode; message: string };
export type GlucoseValidation =
  | { ok: true; draft: GlucoseDraft; warnings: GlucoseWarning[] }
  | { ok: false; field: 'value' | 'unit' | 'date' | 'time' | 'note' | 'context'; error: string };

export type GlucoseQuery = { from?: string; to?: string; limit?: number };

/** Repository errors are typed so the UI can show an honest state. */
export type GlucoseErrorKind = 'unconfigured' | 'unauthenticated' | 'offline' | 'not-found' | 'conflict' | 'schema-missing' | 'forbidden' | 'validation' | 'server';
export class GlucoseRepositoryError extends Error {
  kind: GlucoseErrorKind;
  constructor(kind: GlucoseErrorKind, message: string) { super(message); this.kind = kind; this.name = 'GlucoseRepositoryError'; }
}

export interface GlucoseRepository {
  /** `supabase` writes to Postgres under RLS; `demo` is an explicit in-memory session flag. */
  readonly mode: 'supabase' | 'local' | 'demo' | 'unconfigured';
  list(query?: GlucoseQuery): Promise<GlucoseReading[]>;
  create(draft: GlucoseDraft): Promise<GlucoseReading>;
  /** Optional atomic batch. Local storage writes one encrypted snapshot per import. */
  createMany?(drafts: GlucoseDraft[]): Promise<{ saved: GlucoseReading[]; skipped: number }>;
  update(id: string, draft: GlucoseDraft): Promise<GlucoseReading>;
  remove(id: string): Promise<void>;
}

// ---- Import adapters (research-gated; none is enabled in this branch) ----

export type ConnectionStatus =
  | { state: 'unsupported-platform'; reason: string }
  | { state: 'unavailable'; reason: string }
  | { state: 'needs-update'; reason: string }
  | { state: 'bluetooth-off'; reason: string }
  | { state: 'unsupported-device'; reason: string }
  | { state: 'ready'; reason: string }
  | { state: 'research-only'; reason: string }
  | { state: 'permission-required' }
  | { state: 'permission-denied'; reason?: string }
  | { state: 'disconnected' }
  | { state: 'syncing'; startedAt: string }
  | { state: 'connected'; lastSyncAt: string | null; stale: boolean };

export type ImportedSample = {
  sourceRecordId: string;
  provider: string;
  device: string | null;
  measuredAt: string;
  tzOffsetMinutes: number;
  value: string;
  unit: GlucoseUnit;
  /** Only finger-prick capillary blood samples are accepted (no CGM/interstitial). */
  specimen: 'capillary_blood' | 'interstitial_fluid' | 'plasma' | 'whole_blood' | 'unknown';
  mealContext?: MealContext;
};

export type ImportResult = { imported: number; skippedDuplicates: number; rejected: { sourceRecordId: string; reason: string }[]; cursor: string | null };

export interface GlucoseImportAdapter {
  readonly id: Exclude<GlucoseSourceType, 'manual'>;
  readonly label: string;
  /** Evidence level from the meter research; adapters stay disabled until hardware-tested. */
  readonly evidence: 'SUPPORTED' | 'REQUIRES HARDWARE TEST' | 'UNVERIFIED' | 'UNSUPPORTED';
  readonly enabled: boolean;
  status(): Promise<ConnectionStatus>;
  requestPermission(): Promise<ConnectionStatus>;
  readSince(cursor: string | null): Promise<{ samples: ImportedSample[]; cursor: string | null }>;
}

/** Client configuration: public project URL + publishable/anon key only, or the explicit demo flag. */
export type GlucoseStorage = { read(): Promise<string | null>; write(value: string): Promise<void> };
export type GlucoseConfig = { supabaseUrl: string | null; supabaseAnonKey: string | null; demo: boolean; demoSeed?: boolean; localStorage?: GlucoseStorage };
