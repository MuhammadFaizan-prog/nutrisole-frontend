// Glucose screen actions shared by web and native (called from extensions/useExpansion).
// Every save/delete goes through the repository-backed store; a sheet only says
// "saved" after the repository returned the stored row.
import type { ExpansionState } from '../extensions/model';
import type { AppRoute, Sheet } from '../types';
import type { GlucoseStore } from './store';
import type { GlucoseUnit } from './types';
import { mealContexts } from './types';
import { contextFromLabel, contextLabel, inputFromReading, validateGlucoseInput } from './validation';
import { formatDisplayDate, formatDisplayTime, instantToWallClock, nowDisplay, parseDisplayDate, parseDisplayTime, timeZoneLabel } from './time';
import { glucoseAdapters } from './adapters';
import { rangeLabels, type GlucoseRange } from './history';
import { importAction } from './importActions';
import { importPlatform } from './importActions';

type SetState = (fn: (s: ExpansionState) => ExpansionState) => void;
export type GlucoseActionContext = { s: ExpansionState; setState: SetState; store: GlucoseStore; go: (r: AppRoute) => void; back: () => void; open: (sheet: Sheet) => void };

export function inputFromState(s: ExpansionState) {
  return { value: s.fields.reading || '', unit: s.choices.unit as GlucoseUnit, date: s.choices.date, time: s.choices.time, tzOffsetMinutes: s.glucoseEditingId && s.glucoseEditOffset !== null ? s.glucoseEditOffset : undefined, tzName: s.glucoseEditingId ? s.glucoseEditTzName : undefined, mealContext: contextFromLabel(s.choices.context), note: s.fields.readingNote || '' };
}

/** Returns true when the action was a glucose action. */
export function glucoseAction(action: string, ctx: GlucoseActionContext): boolean {
  const { s, setState, store, go, open } = ctx;
  const snap = store.getSnapshot();
  const notice = (title: string, description: string, choices?: Sheet['choices']) => open({ title, description, choices });
  const blocked = () => {
    if (snap.mode === 'unconfigured') { notice('Database not configured', 'This build is not connected to the NutriSole database, so the reading cannot be saved. Nothing was stored. Your entry stays on this screen.'); return true; }
    if (snap.status === 'signed-out') { notice('Sign in to save', 'Glucose readings are saved to your NutriSole account. Sign in first; your entry was not saved.', [{ label: 'Sign in', action: () => go('sign-in') }]); return true; }
    return false;
  };
  if (importAction(action, ctx)) return true;
  if (action.startsWith('choose:glucoseRange:')) { const range = action.slice(20) as GlucoseRange; if (range in rangeLabels) setState(v => ({ ...v, choices: { ...v.choices, glucoseRange: range } })); return true; }
  if (action.startsWith('open-reading:')) { const id = action.slice(13); setState(v => ({ ...v, glucoseCurrentId: id, glucoseRemoved: false })); go('reading-detail'); return true; }
  if (action.startsWith('provider-info:')) {
    const adapter = glucoseAdapters.find(a => a.id === action.slice(14));
    if (adapter) void adapter.status().then(st => notice(adapter.label, `${'reason' in st ? st.reason : 'Not available.'}\nEvidence: ${adapter.evidence}. Nothing is connected and no data is imported.`, [{ label: 'Add reading manually', action: () => { startNew(ctx); } }]));
    return true;
  }
  switch (action) {
    case 'reading-unit': open({ title: 'Display unit', description: 'Changes how readings are shown. Each reading keeps the unit it was entered in.', choices: (['mg/dL', 'mmol/L'] as const).map(unit => ({ label: unit, selected: s.choices.displayUnit === unit, action: () => setState(v => ({ ...v, choices: { ...v.choices, displayUnit: unit, unit: v.glucoseEditingId ? v.choices.unit : unit } })) })) }); return true;
    case 'manual-source': notice('Manual meter entry', 'NutriSole does not measure glucose. Enter values exactly as your finger-prick meter shows them, in the same unit.'); return true;
    case 'new-reading': startNew(ctx); return true;
    case 'reading-date': open({ title: 'Measured on', fields: [{ key: 'date', label: 'Measured on', value: s.choices.date }], save: v => { if (!parseDisplayDate(v.date)) return 'Use a date such as Oct 16, 2026.'; setState(old => ({ ...old, choices: { ...old.choices, date: v.date.trim() } })); } }); return true;
    case 'reading-time': open({ title: 'Time', fields: [{ key: 'time', label: 'Time', value: s.choices.time }], save: v => { const t = (v.time || '').trim().toUpperCase().replace(/\s*(AM|PM)$/, ' $1'); if (!parseDisplayTime(t)) return 'Use a time such as 8:15 AM.'; setState(old => ({ ...old, choices: { ...old.choices, time: t } })); } }); return true;
    case 'reading-context': open({ title: 'Measurement context', description: 'Optional. A label for your own records, not a medical interpretation.', choices: [...mealContexts.map(c => c.label), 'Not specified'].map(label => ({ label, selected: s.choices.context === label, action: () => setState(v => ({ ...v, choices: { ...v.choices, context: label } })) })) }); return true;
    case 'review-reading': {
      if (snap.busy === 'saving') { notice('Saving…', 'This reading is already being saved.'); return true; }
      if (blocked()) return true;
      const result = validateGlucoseInput(inputFromState(s), { existing: snap.readings, editingId: s.glucoseEditingId });
      if (!result.ok) { notice('Check reading', result.error); return true; }
      const d = result.draft; const editingId = s.glucoseEditingId;
      const when = instantToWallClock(d.measuredAt, d.tzOffsetMinutes);
      const lines = [`${d.valueOriginal} ${d.unitOriginal}`, `${formatDisplayDate(when)} · ${formatDisplayTime(when)} · ${timeZoneLabel(d.tzName, d.tzOffsetMinutes)}`, contextLabel(d.mealContext), d.note ? `Note: ${d.note}` : '', 'Source: manual meter entry', snap.mode === 'demo' ? 'Demo mode: kept for this session only, not saved to a database.' : '', ...result.warnings.map(w => `⚠ ${w.message}`)].filter(Boolean);
      let submitted = false; // rapid double taps on the confirm button submit once
      notice(editingId ? 'Review changes' : 'Review manual reading', lines.join('\n'), [{ label: result.warnings.length ? 'I checked it · Save reading' : editingId ? 'Confirm & save changes' : 'Confirm & save reading', action: () => {
        if (submitted) return; submitted = true;
        void store.save(d, editingId).then(res => {
          if (res.ok && res.reading) { const id = res.reading.id; setState(v => ({ ...v, glucoseCurrentId: id, glucoseRemoved: false, glucoseEditingId: null, glucoseEditOffset: null, glucoseEditTzName: null, fields: { ...v.fields, reading: '', readingNote: '' } })); go('reading-detail'); }
          else if (!res.ok) notice('Reading not saved', `${res.error}\nYour entry is still on this screen. Nothing was stored.`, res.kind === 'unauthenticated' ? [{ label: 'Sign in', action: () => go('sign-in') }] : undefined);
        });
      } }]);
      return true;
    }
    case 'latest-reading': { const latest = snap.readings.at(-1); setState(v => ({ ...v, glucoseCurrentId: latest?.id || null, glucoseRemoved: false })); go('reading-detail'); return true; }
    case 'edit-reading': {
      const r = snap.readings.find(x => x.id === s.glucoseCurrentId);
      if (!r) { notice('No reading selected', 'Open a reading from your glucose history first.'); return true; }
      const c = instantToWallClock(r.measuredAt, r.tzOffsetMinutes); const input = inputFromReading(r, { date: formatDisplayDate(c), time: formatDisplayTime(c) });
      setState(v => ({ ...v, glucoseEditingId: r.id, glucoseEditOffset: r.tzOffsetMinutes, glucoseEditTzName: r.tzName, choices: { ...v.choices, unit: input.unit, date: input.date, time: input.time, context: r.mealContext === 'unspecified' ? 'Not specified' : contextLabel(r.mealContext) }, fields: { ...v.fields, reading: input.value, readingNote: input.note || '' } }));
      go('add-reading'); return true;
    }
    case 'remove-reading': {
      const r = snap.readings.find(x => x.id === s.glucoseCurrentId);
      if (!r) { notice('No reading selected', 'Open a reading from your glucose history first.'); return true; }
      let confirmed = false;
      notice('Delete this reading?', `${r.valueOriginal} ${r.unitOriginal} will be permanently deleted ${snap.mode === 'supabase' ? 'from your NutriSole account' : snap.mode === 'local' ? 'from this phone' : 'from this demo session'}. This cannot be undone.`, [{ label: 'Delete reading', action: () => {
        if (confirmed) return; confirmed = true;
        void store.remove(r.id).then(res => {
          if (res.ok) setState(v => ({ ...v, glucoseRemoved: true, glucoseCurrentId: null }));
          else notice('Reading not deleted', `${res.error}\nThe reading is unchanged.`);
        });
      } }]);
      return true;
    }
    case 'glucose-retry': void store.reload(); return true;
    case 'glucose-sign-in': go('sign-in'); return true;
    case 'provider-info': return glucoseAction('provider-info:health_connect', ctx);
    case 'permissions': notice('Import permissions', importPlatform().os === 'android' ? 'Android asks for camera access when scanning a report, Nearby devices when finding a Bluetooth strip meter, and read-only blood glucose access when importing from Health Connect. You can revoke each permission in Android Settings. Files and photos are read on this phone. Saved phone readings are encrypted and are not uploaded.' : 'Choose a file or photo to read it on this device. Device and health permissions are managed in the mobile app.', [{ label: 'Choose a source', action: () => go('glucose-import') }]); return true;
    default: return false;
  }
}

function startNew({ setState, go }: GlucoseActionContext) {
  const now = nowDisplay();
  setState(v => ({ ...v, glucoseEditingId: null, glucoseEditOffset: null, glucoseEditTzName: null, glucoseRemoved: false, choices: { ...v.choices, unit: v.choices.displayUnit || v.choices.unit, date: now.date, time: now.time, context: 'Not specified' }, fields: { ...v.fields, reading: '', readingNote: '' } }));
  go('add-reading');
}
