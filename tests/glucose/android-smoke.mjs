// Exercises the installed standalone APK through Android's actual UI, without Metro.
// Run only on an isolated QA emulator: it creates, edits and deletes one synthetic reading.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { directoryScreens } from '../../native/responsive/directoryManifest.ts';

const adbPath = process.env.NUTRISOLE_ADB || 'adb';
const app = 'com.muhammadfaizan.nutrisole';
const out = path.resolve(process.argv[2] || 'dist-qa/native-smoke');
fs.mkdirSync(out, { recursive: true });
const adb = (...args) => execFileSync(adbPath, args, { timeout: 45_000, encoding: 'utf8', maxBuffer: 4e6 });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const size = /(?:Physical|Override) size: (\d+)x(\d+)/.exec(adb('shell', 'wm', 'size'));
assert.ok(size, 'Android display size is available');
const [width, height] = size.slice(1).map(Number);
const decode = v => v.replaceAll('&amp;', '&').replaceAll('&quot;', '"').replaceAll('&apos;', "'").replaceAll('&#10;', '\n');
let currentXml = '';
const nodes = () => [...currentXml.matchAll(/<node\s+([^>]+)>/g)].map(m => Object.fromEntries([...m[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(x => [x[1], decode(x[2])])));
function observe(name) {
  adb('shell', 'uiautomator', 'dump', '/sdcard/glucose-ui.xml');
  currentXml = adb('shell', 'cat', '/sdcard/glucose-ui.xml');
  assert.ok(currentXml.includes(app), `NutriSole owns the visible UI: ${name}`);
  fs.writeFileSync(path.join(out, `${name}.xml`), currentXml);
  return currentXml;
}
async function visible(name, pattern) {
  for (let attempt = 0; attempt < 12; attempt++) {
    try { if (pattern.test(observe(name))) return; } catch (e) { if (attempt === 11) throw e; }
    await pause(1000);
  }
  throw new Error(`Expected visible state ${pattern} on ${name}`);
}
function tapNode(node) {
  const b = /\[(\d+),(\d+)\]\[(\d+),(\d+)\]/.exec(node.bounds)?.slice(1).map(Number);
  assert.ok(b && b[2] > b[0] && b[3] > b[1], 'A visible control has nonempty bounds');
  adb('shell', 'input', 'tap', String(Math.round((b[0] + b[2]) / 2)), String(Math.round((b[1] + b[3]) / 2)));
}
async function control(name, predicate) {
  for (let attempt = 0; attempt < 7; attempt++) {
    observe(name);
    const node = nodes().find(predicate);
    if (node) { tapNode(node); return; }
    adb('shell', 'input', 'swipe', String(width / 2), String(Math.round(height * .8)), String(width / 2), String(Math.round(height * .25)), '250');
  }
  throw new Error(`Control missing: ${name}`);
}
const id = suffix => n => (n['resource-id'] || '').endsWith(suffix);
const text = label => n => n.text === label || n['content-desc'] === label;
const open = route => adb('shell', 'am', 'start', '-W', '-a', 'android.intent.action.VIEW', '-d', `nutrisole://${route}`, app);
function screenshot(name) { fs.writeFileSync(path.join(out, `${name}.png`), execFileSync(adbPath, ['exec-out', 'screencap', '-p'], { timeout: 30_000, maxBuffer: 8e6 })); }

open('glucose-overview');
await visible('empty-phone-history', /No readings yet/);
assert.match(currentXml, /Saved on this phone/);
await control('add-reading', id('action-new-reading'));
await control('reading-input', id('field-reading'));
adb('shell', 'input', 'text', '111');
adb('shell', 'input', 'keyevent', 'KEYCODE_BACK');
await control('review-reading', id('action-review-reading'));
await control('confirm-reading', text('Confirm & save reading'));
await visible('saved-manual-reading', /Saved on this phone/);
assert.match(currentXml, /111/);
screenshot('saved-manual-reading');

adb('shell', 'am', 'force-stop', app);
open('glucose-overview');
await visible('history-after-restart', /111/);
assert.match(currentXml, /Manual meter entry/);
await control('open-saved-reading', n => /action-open-reading-/.test(n['resource-id'] || ''));
await control('edit-reading', id('action-edit-reading'));
await control('edit-value', id('field-reading'));
adb('shell', 'input', 'keyevent', 'KEYCODE_MOVE_END');
adb('shell', 'input', 'keyevent', '67', '67', '67');
adb('shell', 'input', 'text', '112');
adb('shell', 'input', 'keyevent', 'KEYCODE_BACK');
await control('review-changes', id('action-review-reading'));
await control('confirm-changes', text('Confirm & save changes'));
await visible('edited-reading', /Saved on this phone/);
assert.match(currentXml, /112/);
await control('remove-test-reading', id('action-remove-reading'));
await control('confirm-remove', text('Delete reading'));
await visible('removed-test-reading', /Reading removed/);
adb('shell', 'am', 'force-stop', app);
open('glucose-overview');
await visible('empty-after-delete-and-restart', /No readings yet/);

const routes = [];
for (const screen of directoryScreens) {
  open(screen.route);
  observe(`route-${screen.route}`);
  const labels = nodes().map(n => n.text || n['content-desc']).filter(Boolean);
  routes.push({ route: screen.route, labels, xmlSha256: crypto.createHash('sha256').update(currentXml).digest('hex') });
  console.log(`Rendered ${screen.route}`);
}
open('glucose-import');
await visible('import-sources', /Attach a file/);
screenshot('import-sources');
const errors = adb('logcat', '-d', '-s', 'ReactNativeJS:E', 'AndroidRuntime:E');
fs.writeFileSync(path.join(out, 'runtime-errors.txt'), errors);
assert.doesNotMatch(errors, /FATAL EXCEPTION|TypeError:|ReferenceError:|Unable to load script|Invariant Violation/);
fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ syntheticOnly: true, manualCreateRestartEditDelete: true, standaloneWithoutMetro: true, routes }, null, 2));
console.log(`Standalone phone storage CRUD and ${routes.length} rendered routes passed.`);
