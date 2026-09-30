import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { MobileScroll, BottomSheet, KeyboardInput, KeyboardTextarea, useKeyboard, useMobileDevice, useScreenPortal } from './mobile';
import NutriSole, { routes } from './nutrisole/NutriSole';
import type { AppRoute as Route, Sheet } from './nutrisole/types';
import './prototype.css';

export default function Prototype() {
  const { device } = useMobileDevice();
  const keyboard = useKeyboard();
  const { screenRef } = useScreenPortal();
  const query = new URLSearchParams(window.location.search).get('screen');
  const [requested, setRequested] = useState<Route>(routes.includes(query as Route) ? query as Route : 'onboarding');
  const [current, setCurrent] = useState<Route>(requested);
  const [resetToken, setResetToken] = useState(0);
  const [navigationToken, setNavigationToken] = useState(0);
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  useEffect(() => { setValues(Object.fromEntries((sheet?.fields || []).map(f => [f.key, f.value]))); setError(''); }, [sheet]);
  useEffect(() => { document.title = 'NutriSole · Mobile Frontend'; }, []);
  // Browser focus can scroll a clipped ancestor when a sheet input opens.
  // Restore its origin after closing; MobileScroll owns content scrolling.
  useEffect(() => {
    if (!sheet && !keyboard.visible) screenRef.current?.scrollTo({ top: 0, left: 0 });
  }, [sheet, keyboard.visible, current, screenRef]);
  useEffect(() => { document.body.classList.toggle('nutri-camera-mode', current === 'scan'); return () => document.body.classList.remove('nutri-camera-mode'); }, [current]);
  function open(next: Sheet) { keyboard.hide(); setSheet(next); }
  function save() { const message = sheet?.save?.(values); if (message) setError(message); else { keyboard.hide(); setSheet(null); } }
  return <>
    {createPortal(<aside className="nutri-review-toolbar" aria-label="Preview controls">
      <span className="nutri-review-brand">NutriSole</span>
      <select aria-label="Preview screen" value={current} onChange={e => { keyboard.hide(); setSheet(null); setRequested(e.target.value as Route); setNavigationToken(v => v + 1); }}>
        {routes.map(r => <option key={r} value={r}>{r.replaceAll('-', ' ')}</option>)}
      </select>
      <button onClick={() => { keyboard.hide(); setSheet(null); setResetToken(v => v + 1); }} aria-label="Reset demo">Reset</button>
    </aside>, document.body)}
    <MobileScroll className="nutri-scroll">
      <NutriSole width={device.geometry.screen.width} height={device.geometry.screen.height - (device.platform === 'android' ? device.geometry.safeArea.bottom : 0)} open={open} requestedRoute={requested} navigationToken={navigationToken} resetToken={resetToken} routeChanged={setCurrent} beforeNavigate={() => keyboard.hide()} />
    </MobileScroll>
    <BottomSheet open={Boolean(sheet)} onOpenChange={value => { if (!value) { keyboard.hide(); setSheet(null); } }} title={sheet?.title || 'Details'} description={sheet?.description} snap={sheet?.fields?.some(f => f.multiline) ? 0.76 : 0.64}>
      <div className="nutri-sheet-content" onPointerDownCapture={e => { if (e.target instanceof Element && e.target.closest('button')) e.preventDefault(); }}>
        {sheet?.fields?.map(f => <label className="nutri-field" key={f.key}><span>{f.label}</span>
          {f.multiline ? <KeyboardTextarea aria-label={f.label} value={values[f.key] || ''} maxLength={300} onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))} onBlur={e => { if (!(e.relatedTarget instanceof HTMLInputElement || e.relatedTarget instanceof HTMLTextAreaElement)) keyboard.hide(); }} /> : <KeyboardInput aria-label={f.label} inputMode={f.numeric ? 'decimal' : 'text'} value={values[f.key] || ''} maxLength={100} onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))} onBlur={e => { if (!(e.relatedTarget instanceof HTMLInputElement || e.relatedTarget instanceof HTMLTextAreaElement)) keyboard.hide(); }} />}
        </label>)}
        {sheet?.choices?.map(choice => <button key={choice.label} className={`nutri-choice ${choice.selected ? 'is-selected' : ''}`} onClick={() => { keyboard.hide(); setSheet(null); choice.action(); }}>{choice.label}{choice.selected ? ' ✓' : ''}</button>)}
        {error && <p role="alert" className="nutri-form-error">{error}</p>}
        {sheet?.save && <button className="nutri-sheet-primary" onClick={save}>Save</button>}
        <button className="nutri-sheet-cancel" onClick={() => { keyboard.hide(); setSheet(null); }}>{sheet?.save ? 'Cancel' : 'Close'}</button>
      </div>
    </BottomSheet>
  </>;
}
