// Actions for "Add readings" (file / scan / device) and the review screen. Every path ends
// on the review screen; only "Save N confirmed" writes, through the same repository as
// manual entry.
import type { ExpansionState } from '../extensions/model';
import type { Sheet } from '../types';
import type { GlucoseActionContext } from './actions';
import type { GlucoseUnit, MealContext, ConnectionStatus } from './types';
import { mealContexts } from './types';
import { createImportPlatform } from './import/platform';
import type { ImportPlatform } from './import/platform.types';
import { fileToBatch, remapBatch, ImportFileError } from './import/fileImport';
import { assessBatch, bulk, canConfirm, draftsToSave, editCandidate, flagText, setDecision } from './import/review';
import { glsToBatch, healthConnectToBatch, healthKitToBatch } from './import/devices';
import { remap, setColumnUnit, setDateOrder } from './import/tabular';
import { IMPORT_PAGE_SIZE, initialImportState, type ImportUiState } from './import/view';
import { contextLabel } from './validation';
import { formatDisplayDate, formatDisplayTime } from './time';
import { findDate, findTime } from './import/dates';
import type { ImportBatch, TabularMapping } from './import/types';
import type { GlucoseStore } from './store';
import type { BleMeter } from './import/scan';
import type { GlsDownload } from './import/gls';

let platform: ImportPlatform | null = null;
export function importPlatform(): ImportPlatform { return (platform ??= createImportPlatform()); }
/** Tests inject a fake platform. */
export function setImportPlatform(p: ImportPlatform | null) { platform = p; }

type Ctx = GlucoseActionContext;
const imp = (s: ExpansionState): ImportUiState => s.glucoseImport ?? initialImportState();
const patch = (ctx: Ctx, p: Partial<ImportUiState>) => ctx.setState(v => ({ ...v, glucoseImport: { ...imp(v), ...p } }));
const setBatch = (ctx: Ctx, fn: (b: ImportBatch) => ImportBatch) => ctx.setState(v => { const cur = imp(v); return cur.batch ? { ...v, glucoseImport: { ...cur, batch: fn(cur.batch) } } : v; });
const notice = (ctx: Ctx, title: string, description: string, choices?: Sheet['choices']) => ctx.open({ title, description, choices });

function startBatch(ctx: Ctx, batch: ImportBatch) {
  ctx.setState(v => {
    const old = imp(v); const previous = old.batch?.id === batch.id ? new Map(old.batch.candidates.map(c => [c.provenance.recordId, c])) : null;
    return { ...v, glucoseImport: { ...old, page: previous ? old.page || 0 : 0, batch: { ...batch, candidates: batch.candidates.map(c => { const prior = previous?.get(c.provenance.recordId); return prior?.edited ? prior : prior ? { ...c, decision: prior.decision } : c; }) }, busy: null, error: null, result: null } };
  });
  ctx.go('import-review');
}
const jobs = new WeakMap<GlucoseStore, AbortController>();
const transfers = new WeakSet<GlucoseStore>();
function stopImport(ctx: Ctx) {
  jobs.get(ctx.store)?.abort(); jobs.delete(ctx.store); patch(ctx, { busy: null });
}
async function run(ctx: Ctx, label: string, work: (progress: (p: string) => void, signal: AbortSignal) => Promise<ImportBatch | null>) {
  if (jobs.has(ctx.store)) { notice(ctx, 'Import in progress', 'Stop the current import before starting another.'); return; }
  const control = new AbortController(); jobs.set(ctx.store, control);
  patch(ctx, { busy: label, error: null });
  try {
    const batch = await work(p => { if (!control.signal.aborted) patch(ctx, { busy: p }); }, control.signal);
    if (control.signal.aborted || !batch) return;
    startBatch(ctx, batch);
  } catch (e) {
    if (control.signal.aborted) return;
    const message = e instanceof ImportFileError || e instanceof Error ? e.message : 'The import failed.';
    patch(ctx, { busy: null, error: message });
    notice(ctx, 'Nothing imported', `${message}\nNothing was saved.`, [{ label: 'Enter the reading manually', action: () => ctx.go('add-reading') }]);
  } finally { if (jobs.get(ctx.store) === control) { jobs.delete(ctx.store); patch(ctx, { busy: null }); } }
}

function connectMeter(ctx: Ctx, device: BleMeter) {
  const ble = importPlatform().devices?.ble; if (!ble) return;
  if (transfers.has(ctx.store)) return;
  transfers.add(ctx.store);
  stopImport(ctx);
  patch(ctx, { foundMeters: [] });
  const batchId = `ble-${Date.now()}-${device.id}`;
  const toBatch = (r: GlsDownload) => {
    const b = glsToBatch(r, device);
    return { ...b, id: batchId, candidates: b.candidates.map(c => ({ ...c, id: `${batchId}-${c.provenance.recordId}` })) };
  };
  void run(ctx, `Connecting to ${device.name || 'strip meter'}…`, async (progress, signal) => {
    let showing = false; let published = 0;
    const result = await ble.download(device.id, null, { signal, onProgress: r => {
      if (signal.aborted) return;
      progress(`${r.records.length} reading${r.records.length === 1 ? '' : 's'} received · transferring…`);
      if (!showing || Date.now() - published >= 100) {
        // Stable IDs retain the user's edits and confirmation decisions while new
        // packets arrive. A cursor is never advanced merely because data arrived.
        const batch = toBatch(r);
        ctx.setState(v => {
          const current = imp(v); const existing = current.batch?.id === batchId ? new Map(current.batch.candidates.map(c => [c.provenance.recordId, c])) : null;
          return { ...v, glucoseImport: { ...current, page: existing ? current.page || 0 : 0, batch: { ...batch, candidates: batch.candidates.map(c => { const old = existing?.get(c.provenance.recordId); return old?.edited ? old : old ? { ...c, decision: old.decision } : c; }) } } };
        });
        if (!showing) ctx.go('import-review'); showing = true; published = Date.now();
      }
    } });
    if (result.outcome === 'failed' && !result.records.length) throw new Error(result.message);
    return toBatch(result);
  }).finally(() => { transfers.delete(ctx.store); });
}

const statusText = (st: ConnectionStatus) => ('reason' in st && st.reason) || ({ 'permission-required': 'Permission is needed.', 'permission-denied': 'Permission was denied.', disconnected: 'Not connected.' } as Record<string, string>)[st.state] || st.state;

function deviceImport(ctx: Ctx, kind: 'health_connect' | 'healthkit' | 'ble_meter') {
  const p = importPlatform();
  const name = kind === 'health_connect' ? 'Health Connect' : kind === 'healthkit' ? 'Apple Health' : 'Bluetooth meter';
  if (p.kind === 'web' || !p.devices) { notice(ctx, `${name} · available in the mobile app`, 'Device import needs the NutriSole Android/iOS app. On the web you can attach a file (CSV, Excel, PDF) or a photo of a report.', [{ label: 'Attach a file', action: () => importAction('import-file', ctx) }]); return; }
  const beta = 'Beta: not yet verified with real hardware. Every reading goes to the review screen first; nothing is saved automatically.';
  if (kind === 'ble_meter') {
    const ble = p.devices.ble; if (!ble) { notice(ctx, name, 'Bluetooth is not available in this build.'); return; }
    void ble.status().then(st => {
      if (st.state === 'bluetooth-off' || st.state === 'unsupported-device') { notice(ctx, name, statusText(st)); return; }
      notice(ctx, 'Connect a Bluetooth strip meter', 'Use a meter with the standard Bluetooth Glucose Service (0x1808). Put it in pairing/transfer mode; tap it as soon as it appears. Pair using the PIN on the meter. Every transferred reading needs your review.\nHardware compatibility still needs a test with your exact meter.', [{ label: 'Find my meter', action: () => {
        patch(ctx, { foundMeters: [] }); ctx.go('glucose-import');
        void run(ctx, 'Finding Bluetooth strip meters…', async (progress, signal) => {
          const permission = await ble.requestPermission();
          if (permission.state !== 'ready') throw new Error(statusText(permission));
          progress('Searching… Tap your meter as soon as it appears.');
          const found = await ble.scan(10, { signal, onFound: device => {
            if (!signal.aborted) ctx.setState(v => ({ ...v, glucoseImport: { ...imp(v), foundMeters: [...(imp(v).foundMeters || []).filter(d => d.id !== device.id), device] } }));
          } });
          if (!signal.aborted && !found.length) throw new Error('No compatible strip meter was found. Check its Bluetooth pairing mode and keep it near the phone.');
          return null;
        });
      } }]);
    }).catch(e => notice(ctx, 'Bluetooth unavailable', e instanceof Error ? e.message : 'Bluetooth could not start.'));
    return;
  }
  const bridge = kind === 'health_connect' ? p.devices.healthConnect : p.devices.healthKit;
  if (!bridge) { notice(ctx, name, kind === 'health_connect' ? 'Health Connect is an Android service and is not available on this device.' : 'Apple Health is only available on iPhone.'); return; }
  void bridge.status().then(st => {
    if (['unavailable', 'needs-update', 'unsupported-platform', 'unsupported-device'].includes(st.state)) { notice(ctx, name, `${statusText(st)}\nYou can still attach a file or enter readings manually.`, bridge.openSettings && st.state === 'needs-update' ? [{ label: 'Open Health Connect', action: () => bridge.openSettings!() }] : undefined); return; }
    const pickRange = () => ctx.open({ title: 'Import which period?', choices: [7, 30, 90].map(days => ({ label: `Last ${days} days`, action: () => void run(ctx, `Reading ${name}…`, async () => {
      const recs = await bridge.read(days);
      return kind === 'health_connect' ? healthConnectToBatch(recs as never) : healthKitToBatch(recs as never);
    }) })) });
    if (st.state === 'ready') { pickRange(); return; }
    // Rationale screen (shown before the OS permission sheet; Health Connect also links here).
    notice(ctx, `Why NutriSole asks for ${name}`, `NutriSole asks to READ blood glucose only, to show the readings your meter app saved there. It never writes to ${name} and never reads other health data. You choose the period, and you review every value before saving ${ctx.store.getSnapshot().mode === 'local' ? 'on this phone' : 'to your account'}.\n${st.state === 'permission-denied' ? 'Access was denied earlier. You can allow it again, or change it in settings.\n' : ''}${beta}`, [
      { label: 'Continue', action: () => void bridge.requestPermission().then(r => r.state === 'ready' ? pickRange() : notice(ctx, 'No access', `${statusText(r)}\nNothing was imported.`, bridge.openSettings ? [{ label: 'Open Health Connect settings', action: () => bridge.openSettings!() }] : undefined)).catch(e => notice(ctx, 'Permission could not be requested', e instanceof Error ? e.message : 'Try again in Health Connect settings.')) },
      { label: 'Not now', action: () => undefined },
    ]);
  }).catch(e => notice(ctx, `${name} unavailable`, e instanceof Error ? e.message : 'The health source could not start.'));
}

const roles: { key: 'value' | 'datetime' | 'date' | 'time' | 'unit' | 'context' | 'note'; label: string }[] = [
  { key: 'value', label: 'Glucose value' }, { key: 'datetime', label: 'Date & time (one column)' }, { key: 'date', label: 'Date' }, { key: 'time', label: 'Time' }, { key: 'unit', label: 'Unit (per row)' }, { key: 'context', label: 'Meal / context' }, { key: 'note', label: 'Notes' },
];
function mappingSheet(ctx: Ctx) {
  const b = imp(ctx.s).batch; const m = b?.table?.mapping; if (!b || !m) return;
  const col = (i: number | null) => (i === null ? 'not used' : m.header[i] || `column ${i + 1}`);
  const apply = (next: TabularMapping) => setBatch(ctx, batch => remapBatch(batch, next));
  ctx.open({ title: 'Column mapping', description: `Detected from the header row ${m.headerRow + 1}. ${m.reasons.join(' ')}\nChange any column; the rows update straight away.`, choices: [
    ...roles.map(r => ({ label: `${r.label}: ${col(m[r.key])}`, action: () => ctx.open({ title: r.label, choices: [...m.header.map((h, i) => ({ label: h || `Column ${i + 1}`, selected: m[r.key] === i, action: () => apply(remap(m, r.key, i)) })), ...(r.key === 'value' ? [] : [{ label: 'Not used', selected: m[r.key] === null, action: () => apply(remap(m, r.key, null)) }])] }) })),
    { label: `Unit for the whole value column: ${m.columnUnit || 'per row / detect'}`, action: () => ctx.open({ title: 'Unit for the value column', choices: [...(['mg/dL', 'mmol/L'] as GlucoseUnit[]).map(u => ({ label: u, selected: m.columnUnit === u, action: () => apply(setColumnUnit(m, u)) })), { label: 'Per row / detect', selected: m.columnUnit === null, action: () => apply(setColumnUnit(m, null)) }] }) },
    { label: `Date order: ${m.dateOrder}`, action: () => ctx.open({ title: 'Date order', description: 'How numeric dates like 03/04/2026 are read.', choices: (['DMY', 'MDY', 'YMD'] as const).map(o => ({ label: o === 'DMY' ? 'Day/Month/Year (DMY)' : o === 'MDY' ? 'Month/Day/Year (MDY)' : 'Year-Month-Day (YMD)', selected: m.dateOrder === o, action: () => apply(setDateOrder(m, o)) })) }) },
  ] });
}

function rowSheet(ctx: Ctx, id: string) {
  const b = imp(ctx.s).batch; if (!b) return;
  const a = assessBatch(b, ctx.store.getSnapshot().readings).find(x => x.id === id); if (!a) return;
  ctx.open({ title: 'Check reading', description: canConfirm(a).reason || 'Compare this reading with your report.',
    fields: [
      { key: 'value', label: 'Reading', value: a.value, numeric: true },
      { key: 'unit', label: 'Unit', value: a.unit || '', options: ['mg/dL', 'mmol/L'].map(value => ({ label: value, value })) },
      { key: 'date', label: 'Date', value: a.date, placeholder: 'DD/MM/YYYY' },
      { key: 'time', label: 'Time', value: a.time, placeholder: 'e.g. 08:15 or 8:15 AM' },
      { key: 'context', label: 'When was it taken?', value: a.mealContext, options: [{ label: 'Not specified', value: 'unspecified' }, ...mealContexts.map(c => ({ label: c.label, value: c.value }))] },
    ], saveLabel: 'Confirm reading', save: v => {
      const date = findDate((v.date || '').trim())?.date; const time = findTime((v.time || '').trim())?.time;
      if (!date) return 'Enter the measurement date, for example 16/10/2026.';
      if (!time) return 'Enter the measurement time. The report did not supply a usable time.';
      if (v.unit !== 'mg/dL' && v.unit !== 'mmol/L') return 'Choose the unit printed on your report.';
      const edited = editCandidate(b, id, { value: (v.value || '').trim(), unit: v.unit, date: formatDisplayDate(date), time: formatDisplayTime(time), mealContext: v.context as MealContext });
      const candidate = assessBatch(edited, ctx.store.getSnapshot().readings).find(c => c.id === id)!;
      const valid = canConfirm(candidate); if (!valid.ok) return valid.reason || 'Check this reading.';
      setBatch(ctx, current => setDecision(editCandidate(current, id, { value: candidate.value, unit: candidate.unit, date: candidate.date, time: candidate.time, mealContext: candidate.mealContext }), id, 'confirmed'));
    }, choices: [
      { label: 'View source text', action: () => notice(ctx, a.provenance.fileName || 'Source', a.provenance.raw, [{ label: 'Back to reading', action: () => rowSheet(ctx, id) }]) },
      { label: a.decision === 'rejected' ? 'Include reading' : 'Skip reading', action: () => setBatch(ctx, x => setDecision(x, id, a.decision === 'rejected' ? 'pending' : 'rejected')) },
    ],
  });
}

function save(ctx: Ctx) {
  const ui = imp(ctx.s); const b = ui.batch; if (!b) return;
  if (ui.busy || ui.saving || jobs.has(ctx.store)) { notice(ctx, 'Transfer in progress', 'Wait for the transfer to finish or stop it before saving the received readings.'); return; }
  const snap = ctx.store.getSnapshot();
  if (snap.mode === 'unconfigured') { notice(ctx, 'Database not configured', 'This build is not connected to the NutriSole database, so imported readings cannot be saved. Your review stays here.'); return; }
  if (snap.status === 'signed-out') { notice(ctx, 'Sign in to save', 'Imported readings are saved to your NutriSole account. Sign in first; your review stays here.', [{ label: 'Sign in', action: () => ctx.go('sign-in') }]); return; }
  const { drafts } = draftsToSave(b, snap.readings);
  if (!drafts.length) { const next = b.candidates.find(c => c.decision !== 'rejected'); if (next) rowSheet(ctx, next.id); else notice(ctx, 'Nothing selected', 'Include a reading before saving.'); return; }
  patch(ctx, { saving: true, error: null });
  void ctx.store.importMany(drafts).then(res => {
    const msg = [res.saved.length + ' saved', res.skipped ? res.skipped + ' already saved' : '', res.failed.length ? res.failed[0].error : '', res.stoppedEarly || ''].filter(Boolean).join(' · ');
    if ((res.saved.length || res.skipped) && !res.failed.length && !res.stoppedEarly) {
      patch(ctx, { saving: false, batch: null, result: msg }); ctx.go('glucose-overview');
    } else {
      const savedIds = new Set(res.saved.map(r => r.source.recordId));
      setBatch(ctx, x => ({ ...x, candidates: x.candidates.filter(c => !savedIds.has(c.provenance.recordId)) }));
      patch(ctx, { saving: false, error: msg });
      notice(ctx, 'Could not save all readings', msg + '. Your unsaved readings are still here.');
    }
  }).catch(() => { patch(ctx, { saving: false, error: 'Could not save. Please retry.' }); });
}

/** Returns true when the action belonged to the import flow. */
export function importAction(action: string, ctx: Ctx): boolean {
  const p = () => importPlatform();
  if (action === 'import-page:next' || action === 'import-page:previous') {
    ctx.setState(v => {
      const ui = imp(v); const last = Math.max(0, Math.ceil((ui.batch?.candidates.length || 0) / IMPORT_PAGE_SIZE) - 1);
      const current = Math.max(0, Math.min(last, Math.floor(ui.page || 0)));
      const page = Math.max(0, Math.min(last, current + (action === 'import-page:next' ? 1 : -1)));
      return { ...v, glucoseImport: { ...ui, page } };
    }); return true;
  }
  if (action.startsWith('import-device:')) { deviceImport(ctx, action.slice(14) as 'health_connect' | 'healthkit' | 'ble_meter'); return true; }
  if (action.startsWith('import-meter:')) { const device = imp(ctx.s).foundMeters?.find(d => d.id === action.slice(13)); if (device) connectMeter(ctx, device); return true; }
  if (action.startsWith('import-row:')) { rowSheet(ctx, action.slice(11)); return true; }
  if (action.startsWith('import-bulk:')) {
    const kind = action.slice(12) as 'confirm-clean' | 'reject-all' | 'reject-flagged' | 'reset';
    const current = imp(ctx.s).batch;
    if (current && kind === 'confirm-clean') {
      const updated = bulk(current, kind, ctx.store.getSnapshot().readings);
      const next = updated.candidates.find(c => c.decision === 'pending');
      setBatch(ctx, () => updated);
      if (next) rowSheet(ctx, next.id);
    } else setBatch(ctx, b => bulk(b, kind, ctx.store.getSnapshot().readings));
    return true;
  }
  switch (action) {
    case 'import-file': void run(ctx, 'Opening file…', async (progress, signal) => { const f = await p().pickFile(); if (!f || signal.aborted) return null; progress(`Reading ${f.name}…`); return fileToBatch(f, p().extractors, { onProgress: progress, signal }); }); return true;
    case 'import-scan': void run(ctx, 'Opening camera…', async (progress, signal) => { const f = await p().captureReport(); if (!f || signal.aborted) return null; progress('Reading the photo…'); return fileToBatch(f, p().extractors, { camera: true, onProgress: progress, signal }); }); return true;
    case 'import-stop': stopImport(ctx); return true;
    case 'import-mapping': mappingSheet(ctx); return true;
    case 'import-save': save(ctx); return true;
    case 'import-nonglucose': { const b = imp(ctx.s).batch; notice(ctx, 'Other lab values', `${(b?.nonGlucose || []).map(n => `${n.label}: ${n.value}${n.unit ? ` ${n.unit}` : ''} (${n.locator})`).join('\n')}\nHbA1c, estimated average glucose and urine sugar are different measurements, so they are never imported as glucose readings.`); return true; }
    case 'import-notes': { const b = imp(ctx.s).batch; notice(ctx, 'About this import', (b?.notes || []).join('\n') || 'No notes.'); return true; }
    case 'import-cancel': notice(ctx, 'Discard this import?', 'Nothing from it has been saved. The file stays on your device.', [{ label: 'Discard import', action: () => { stopImport(ctx); patch(ctx, { batch: null, error: null }); ctx.go('glucose-import'); } }]); return true;
    case 'import-help': notice(ctx, 'How importing works', `Every value is shown here first with its source. Confirm, edit or reject each row. OCR scores are not a guarantee of accuracy; compare every value and unit with the report or meter. Nothing is saved until you tap Save.\nPhotos and PDFs are read ${p().kind === 'web' ? 'in your browser' : 'on this phone'} with ${p().ocrEngine}; the file is never uploaded.\nHbA1c and other lab values are listed separately and never saved as glucose readings.`); return true;
    default: return false;
  }
}
