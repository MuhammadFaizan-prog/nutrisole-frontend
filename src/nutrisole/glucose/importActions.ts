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
import { initialImportState, type ImportUiState } from './import/view';
import { contextLabel } from './validation';
import { parseDisplayDate, parseDisplayTime } from './time';
import type { ImportBatch, TabularMapping } from './import/types';

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
  patch(ctx, { batch, busy: null, error: null, result: null });
  ctx.go('import-review');
}
async function run(ctx: Ctx, label: string, work: (progress: (p: string) => void) => Promise<ImportBatch | null>) {
  if (imp(ctx.s).busy) { notice(ctx, 'Please wait', imp(ctx.s).busy || 'An import is already running.'); return; }
  patch(ctx, { busy: label, error: null });
  try {
    const batch = await work(p => patch(ctx, { busy: p }));
    if (!batch) { patch(ctx, { busy: null }); return; }
    startBatch(ctx, batch);
  } catch (e) {
    const message = e instanceof ImportFileError || e instanceof Error ? e.message : 'The import failed.';
    patch(ctx, { busy: null, error: message });
    notice(ctx, 'Nothing imported', `${message}\nNothing was saved.`, [{ label: 'Enter the reading manually', action: () => ctx.go('add-reading') }]);
  }
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
      const go = () => void run(ctx, 'Scanning for glucose meters (10 s)…', async progress => {
        const st2 = await ble.requestPermission();
        if (st2.state !== 'ready') throw new Error(statusText(st2));
        progress('Scanning for meters (Glucose Service 0x1808)… Put the meter in pairing/transfer mode.');
        const found = await ble.scan(10);
        if (!found.length) throw new Error('No Bluetooth glucose meter was found. Put the meter in pairing/transfer mode, keep it close, and try again.');
        return await new Promise<ImportBatch | null>((resolve, reject) => {
          ctx.open({ title: 'Choose your meter', description: `${found.length} meter${found.length === 1 ? '' : 's'} found. The first connection asks to pair; enter the PIN shown on or printed on the meter.`, choices: found.map(d => ({ label: `${d.name || 'Unnamed meter'} · ${d.id}`, action: () => {
            const since = imp(ctx.s).lastSequence[d.id];
            const fetchFrom = (seq: number | null) => { patch(ctx, { busy: `Downloading from ${d.name || d.id}…` }); ble.download(d.id, seq).then(dl => {
              if (dl.lastSequence !== null) ctx.setState(v => ({ ...v, glucoseImport: { ...imp(v), lastSequence: { ...imp(v).lastSequence, [d.id]: dl.lastSequence! + 1 } } }));
              if (dl.outcome === 'failed' && !dl.records.length) reject(new Error(dl.message)); else resolve(glsToBatch(dl, d));
            }, reject); };
            if (since !== undefined) ctx.open({ title: 'Which readings?', choices: [{ label: 'New since last import', action: () => fetchFrom(since) }, { label: 'All stored readings', action: () => fetchFrom(null) }] });
            else fetchFrom(null);
          } })) });
        });
      });
      if (st.state === 'bluetooth-off' || st.state === 'unsupported-device') { notice(ctx, name, statusText(st)); return; }
      notice(ctx, 'Import from a Bluetooth meter', `NutriSole connects to strip meters that use the standard Bluetooth Glucose Profile and reads their stored readings. It needs the "Nearby devices" permission to find the meter. Nothing is sent anywhere.\n${beta}`, [{ label: st.state === 'ready' ? 'Find my meter' : 'Continue', action: go }]);
    });
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
    notice(ctx, `Why NutriSole asks for ${name}`, `NutriSole asks to READ blood glucose only, to show the readings your meter app saved there. It never writes to ${name} and never reads other health data. You choose the period, and you review every value before it is saved to your account.\n${st.state === 'permission-denied' ? 'Access was denied earlier. You can allow it again, or change it in settings.\n' : ''}${beta}`, [
      { label: 'Continue', action: () => void bridge.requestPermission().then(r => r.state === 'ready' ? pickRange() : notice(ctx, 'No access', `${statusText(r)}\nNothing was imported.`, bridge.openSettings ? [{ label: 'Open Health Connect settings', action: () => bridge.openSettings!() }] : undefined)) },
      { label: 'Not now', action: () => undefined },
    ]);
  });
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
  const ok = canConfirm(a);
  const p = a.provenance;
  const lines = [
    `${a.value} ${a.unit || '(unit?)'} · ${a.date || 'no date'} ${a.time || ''} · ${a.mealContext === 'unspecified' ? 'no context' : contextLabel(a.mealContext)}`,
    `Found in ${p.fileName || p.device || p.provider} · ${p.locator}: "${p.raw.slice(0, 120)}"`,
    `As found: ${a.original.value}${a.original.unit ? ` ${a.original.unit}` : ' (no unit written)'} · unit ${a.unitSource} · confidence ${Math.round(a.confidence * 100)}%`,
    ...a.allFlags.map(f => `⚠ ${flagText[f]}`), a.error && !a.allFlags.length ? `⚠ ${a.error}` : '', a.note ? `Note: ${a.note}` : '',
    ok.ok ? '' : `Cannot be saved yet: ${ok.reason}`,
  ].filter(Boolean);
  ctx.open({ title: a.decision === 'confirmed' ? 'Confirmed reading' : a.decision === 'rejected' ? 'Rejected reading' : 'Check this reading', description: lines.join('\n'), choices: [
    ...(ok.ok && a.decision !== 'confirmed' ? [{ label: a.allFlags.some(f => f !== 'meter-clock') ? 'I checked it · Confirm' : 'Confirm reading', action: () => setBatch(ctx, x => setDecision(x, id, 'confirmed')) }] : []),
    { label: 'Edit value, date & time', action: () => ctx.open({ title: 'Edit reading', description: `Original: ${a.original.value}${a.original.unit ? ` ${a.original.unit}` : ''} (kept for the record).`, fields: [{ key: 'value', label: 'Reading', value: a.value, numeric: true }, { key: 'date', label: 'Date (e.g. Oct 16, 2026)', value: a.date }, { key: 'time', label: 'Time (e.g. 8:15 AM)', value: a.time }, { key: 'note', label: 'Note', value: a.note, multiline: true }], save: v => {
      const date = (v.date || '').trim(); const time = (v.time || '').trim().toUpperCase().replace(/\s*(AM|PM)$/, ' $1');
      if (!parseDisplayDate(date)) return 'Use a date such as Oct 16, 2026.'; if (!parseDisplayTime(time)) return 'Use a time such as 8:15 AM.';
      setBatch(ctx, x => editCandidate(x, id, { value: (v.value || '').trim(), date, time, note: (v.note || '').trim() }));
    } }) },
    { label: `Unit: ${a.unit || 'unknown'} · change`, action: () => ctx.open({ title: 'Unit for this reading', description: 'Choose the unit printed on the report or meter. The value is not converted.', choices: (['mg/dL', 'mmol/L'] as GlucoseUnit[]).map(u => ({ label: u, selected: a.unit === u, action: () => setBatch(ctx, x => editCandidate(x, id, { unit: u })) })) }) },
    { label: `Context: ${a.mealContext === 'unspecified' ? 'not specified' : contextLabel(a.mealContext)} · change`, action: () => ctx.open({ title: 'Measurement context', choices: [...mealContexts.map(c => c.value), 'unspecified' as MealContext].map(c => ({ label: c === 'unspecified' ? 'Not specified' : contextLabel(c), selected: a.mealContext === c, action: () => setBatch(ctx, x => editCandidate(x, id, { mealContext: c })) })) }) },
    ...(a.decision !== 'rejected' ? [{ label: 'Reject (do not save)', action: () => setBatch(ctx, x => setDecision(x, id, 'rejected')) }] : [{ label: 'Undo reject', action: () => setBatch(ctx, x => setDecision(x, id, 'pending')) }]),
  ] });
}

function save(ctx: Ctx) {
  const ui = imp(ctx.s); const b = ui.batch; if (!b) return;
  const snap = ctx.store.getSnapshot();
  if (snap.mode === 'unconfigured') { notice(ctx, 'Database not configured', 'This build is not connected to the NutriSole database, so imported readings cannot be saved. Your review stays here.'); return; }
  if (snap.status === 'signed-out') { notice(ctx, 'Sign in to save', 'Imported readings are saved to your NutriSole account. Sign in first; your review stays here.', [{ label: 'Sign in', action: () => ctx.go('sign-in') }]); return; }
  const { drafts, blocked } = draftsToSave(b, snap.readings);
  if (!drafts.length) { notice(ctx, 'Nothing to save', blocked.length ? `The confirmed rows still need a fix:\n${blocked.slice(0, 4).map(x => `• ${x.reason}`).join('\n')}` : 'Confirm at least one reading first (tap a row, or use "Confirm all unflagged").'); return; }
  let submitted = false;
  notice(ctx, `Save ${drafts.length} reading${drafts.length === 1 ? '' : 's'}?`, [`${drafts.length} confirmed reading${drafts.length === 1 ? '' : 's'} will be saved ${snap.mode === 'demo' ? 'for this demo session only (not to a database)' : 'to your NutriSole account'}, each with its source (${b.title}).`, blocked.length ? `${blocked.length} confirmed row${blocked.length === 1 ? '' : 's'} still need a fix and will not be saved.` : '', 'Rows you did not confirm are not saved.'].filter(Boolean).join('\n'), [{ label: `Save ${drafts.length} reading${drafts.length === 1 ? '' : 's'}`, action: () => {
    if (submitted) return; submitted = true;
    patch(ctx, { saving: true });
    void ctx.store.importMany(drafts).then(res => {
      const msg = [`${res.saved.length} saved`, res.skipped ? `${res.skipped} already imported (skipped)` : '', res.failed.length ? `${res.failed.length} failed: ${res.failed[0].error}` : ''].filter(Boolean).join(' · ');
      if (res.saved.length && !res.failed.length) { patch(ctx, { saving: false, batch: null, result: msg }); ctx.go('glucose-overview'); notice(ctx, 'Readings saved', `${msg}.`); }
      else { const savedIds = new Set(res.saved.map(r => r.source.recordId)); setBatch(ctx, x => ({ ...x, candidates: x.candidates.filter(c => !savedIds.has(c.provenance.recordId)) })); patch(ctx, { saving: false, result: msg }); notice(ctx, res.saved.length ? 'Some readings not saved' : 'Readings not saved', `${msg}.${res.stoppedEarly ? `\n${res.stoppedEarly}` : ''}\nUnsaved rows stay on this screen.`); }
    });
  } }]);
}

/** Returns true when the action belonged to the import flow. */
export function importAction(action: string, ctx: Ctx): boolean {
  const p = () => importPlatform();
  if (action.startsWith('import-device:')) { deviceImport(ctx, action.slice(14) as 'health_connect' | 'healthkit' | 'ble_meter'); return true; }
  if (action.startsWith('import-row:')) { rowSheet(ctx, action.slice(11)); return true; }
  if (action.startsWith('import-bulk:')) { const kind = action.slice(12) as 'confirm-clean' | 'reject-all' | 'reject-flagged' | 'reset'; setBatch(ctx, b => bulk(b, kind, ctx.store.getSnapshot().readings)); return true; }
  switch (action) {
    case 'import-file': void run(ctx, 'Opening file…', async progress => { const f = await p().pickFile(); if (!f) return null; progress(`Reading ${f.name}…`); return fileToBatch(f, p().extractors, { onProgress: progress }); }); return true;
    case 'import-scan': void run(ctx, 'Opening camera…', async progress => { const f = await p().captureReport(); if (!f) return null; progress(`Reading the photo with ${p().ocrEngine}…`); return fileToBatch(f, p().extractors, { camera: true, onProgress: progress }); }); return true;
    case 'import-mapping': mappingSheet(ctx); return true;
    case 'import-save': save(ctx); return true;
    case 'import-nonglucose': { const b = imp(ctx.s).batch; notice(ctx, 'Other lab values', `${(b?.nonGlucose || []).map(n => `${n.label}: ${n.value}${n.unit ? ` ${n.unit}` : ''} (${n.locator})`).join('\n')}\nHbA1c, estimated average glucose and urine sugar are different measurements, so they are never imported as glucose readings.`); return true; }
    case 'import-notes': { const b = imp(ctx.s).batch; notice(ctx, 'About this import', (b?.notes || []).join('\n') || 'No notes.'); return true; }
    case 'import-cancel': notice(ctx, 'Discard this import?', 'Nothing from it has been saved. The file stays on your device.', [{ label: 'Discard import', action: () => { patch(ctx, { batch: null, error: null }); ctx.go('glucose-import'); } }]); return true;
    case 'import-help': notice(ctx, 'How importing works', `Every value is shown here first with what was found, where, and how sure the reader is. Confirm, edit or reject each row, or confirm all rows that have no warnings. Nothing is saved until you tap Save.\nText in photos and PDFs is read ${p().kind === 'web' ? 'in your browser with tesseract.js' : 'on this phone with ML Kit'}; the file is never uploaded.\nHbA1c and other lab values are listed separately and never saved as glucose readings.`); return true;
    default: return false;
  }
}
