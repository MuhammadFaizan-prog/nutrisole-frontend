// Exercises the installed standalone APK through Android's actual UI, without Metro.
// Run only on an isolated QA emulator: it creates, edits and deletes one synthetic reading.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { PROJECT_URL, PROJECT_KEY } from '../../src/nutrisole/glucose/publicProject.ts';
import { directoryScreens } from '../../native/responsive/directoryManifest.ts';

const adbPath = process.env.NUTRISOLE_ADB || 'adb';
const app = 'com.muhammadfaizan.nutrisole';
const out = path.resolve(process.argv[2] || 'dist-qa/native-smoke');
fs.mkdirSync(out, { recursive: true });
const adb = (...args) => execFileSync(adbPath, args, { timeout: 45_000, encoding: 'utf8', maxBuffer: 4e6 });
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const appUid = new RegExp(`package:${app.replaceAll('.', '\\.')} uid:(\\d+)`).exec(adb('shell', 'cmd', 'package', 'list', 'packages', '-U', app))?.[1];
assert.ok(appUid, 'Installed NutriSole has an Android UID');
// This is a dedicated QA emulator. Exclude earlier instrumentation/system failures,
// but keep errors from the app UID across each deliberate process restart.
adb('logcat', '-c');
const size = /(?:Physical|Override) size: (\d+)x(\d+)/.exec(adb('shell', 'wm', 'size'));
assert.ok(size, 'Android display size is available');
const [width, height] = size.slice(1).map(Number);
const decode = v => v.replaceAll('&amp;', '&').replaceAll('&quot;', '"').replaceAll('&apos;', "'").replaceAll('&#10;', '\n');
let currentXml = '';
let launcherAnrs = 0;
class AndroidUiFailure extends Error {}
const nodes = () => [...currentXml.matchAll(/<node\s+([^>]+)>/g)].map(m => Object.fromEntries([...m[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(x => [x[1], decode(x[2])])));
function observe(name, owner = app) {
  adb('shell', 'uiautomator', 'dump', '/sdcard/glucose-ui.xml');
  currentXml = adb('shell', 'cat', '/sdcard/glucose-ui.xml');
  fs.writeFileSync(path.join(out, `${name}.xml`), currentXml);
  // An isolated emulator's Pixel Launcher can ANR behind the instrumentation
  // activity. Record and close only that named system dialog, never an app ANR.
  if (nodes().some(n => n.package === 'android' && n.text === "Pixel Launcher isn't responding")) {
    if (++launcherAnrs > 2) throw new AndroidUiFailure('The emulator launcher repeatedly stopped responding');
    screenshot(`system-launcher-anr-${launcherAnrs}`);
    fs.writeFileSync(path.join(out, `system-launcher-anr-${launcherAnrs}.xml`), currentXml);
    const close = nodes().find(n => n['resource-id'] === 'android:id/aerr_close' || n.text === 'Close app');
    assert.ok(close, 'Pixel Launcher ANR exposes its close control');
    tapNode(close);
    adb('shell', 'am', 'force-stop', 'com.google.android.apps.nexuslauncher');
    return observe(name, owner);
  }
  if (nodes().some(n => /^android:id\/aerr_(?:close|wait|restart)$/.test(n['resource-id'] || '') || /(?:isn['’]t|is not) responding|keeps stopping/i.test(n.text || ''))) throw new AndroidUiFailure(`An Android crash or ANR dialog blocked ${name}`);
  assert.ok(currentXml.includes('<hierarchy'), `Android returned a UI hierarchy: ${name}`);
  if (owner) assert.ok(currentXml.includes(owner), `Expected app owns the visible UI: ${name}`);
  return currentXml;
}
async function visible(name, pattern, owner = app) {
  for (let attempt = 0; attempt < 12; attempt++) {
    try { if (pattern.test(observe(name, owner))) return; } catch (e) { if (e instanceof AndroidUiFailure || attempt === 11) throw e; }
    await pause(1000);
  }
  throw new Error(`Expected visible state ${pattern} on ${name}`);
}
function bounds(node) {
  const b = /\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]/.exec(node.bounds)?.slice(1).map(Number);
  return b && b[2] > b[0] && b[3] > b[1] && b[0] >= 0 && b[1] >= 0 && b[2] <= width && b[3] <= height ? b : null;
}
function tapNode(node) {
  const b = bounds(node);
  assert.ok(b, 'A visible control has nonempty on-screen bounds');
  adb('shell', 'input', 'tap', String(Math.round((b[0] + b[2]) / 2)), String(Math.round((b[1] + b[3]) / 2)));
}
async function control(name, predicate, owner = app) {
  for (let attempt = 0; attempt < 7; attempt++) {
    observe(name, owner);
    const node = nodes().find(n => predicate(n) && bounds(n) && n.enabled !== 'false');
    if (node) { tapNode(node); return; }
    adb('shell', 'input', 'swipe', String(width / 2), String(Math.round(height * .8)), String(width / 2), String(Math.round(height * .25)), '250');
  }
  throw new Error(`Control missing: ${name}`);
}
const id = suffix => n => (n['resource-id'] || '').endsWith(suffix);
const text = label => n => n.text === label || n['content-desc'] === label;
const open = route => adb('shell', 'am', 'start', '-W', '-a', 'android.intent.action.VIEW', '-d', `nutrisole://${route}`, app);
function screenshot(name) { fs.writeFileSync(path.join(out, `${name}.png`), execFileSync(adbPath, ['exec-out', 'screencap', '-p'], { timeout: 30_000, maxBuffer: 8e6 })); }
process.on('uncaughtExceptionMonitor', () => {
  try { screenshot('failure'); } catch {}
  try { fs.writeFileSync(path.join(out, 'failure-logcat.txt'), adb('logcat', '-d', `--uid=${appUid}`)); } catch {}
});

const email = process.env.GLUCOSE_TEST_USER_A_EMAIL; const password = process.env.GLUCOSE_TEST_USER_A_PASSWORD;
assert.ok(email?.endsWith('@example.invalid') && email.startsWith('glucose-') && password, 'Dedicated QA account configured');
const auth = await fetch(PROJECT_URL+'/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:PROJECT_KEY,'Content-Type':'application/json'},body:JSON.stringify({email,password})});
assert.equal(auth.status,200); const session = await auth.json();
// This account was created exclusively for this smoke test, never a user's account.
const cleared = await fetch(PROJECT_URL+'/rest/v1/glucose_readings?user_id=eq.'+session.user.id,{method:'DELETE',headers:{apikey:PROJECT_KEY,Authorization:'Bearer '+session.access_token}}); assert.equal(cleared.status,204);
open('sign-in');
await visible('account-sign-in', /screen-sign-in/);
await control('email', id('field-email')); adb('shell','input','text',email);
await control('password', id('field-password')); adb('shell','input','text',password);
adb('shell','input','keyevent','KEYCODE_BACK');
await control('sign-in',id('action-sign-in'));
await visible('signed-in-home', /screen-home/);
open('glucose-overview');
await visible('empty-account-history', /No readings yet/);
await control('add-reading', id('action-new-reading'));
await control('reading-input', id('field-reading'));
adb('shell', 'input', 'text', '111');
adb('shell', 'input', 'keyevent', 'KEYCODE_BACK');
await control('review-reading', id('action-review-reading'));
await visible('saved-manual-reading', /Saved to your account/);
assert.match(currentXml, /111/);
screenshot('saved-manual-reading');

adb('shell', 'am', 'force-stop', app);
open('glucose-overview');
await visible('history-after-restart', /111/);
await control('open-saved-reading', n => /action-open-reading-/.test(n['resource-id'] || ''));
await visible('persisted-reading-detail', /screen-reading-detail/);
assert.ok(nodes().some(n => n.text === '111'), 'Persisted manual value is 111');
assert.ok(nodes().some(n => n.text === 'mg/dL'), 'Persisted manual unit is mg/dL');
assert.match(currentXml, /Manual meter entry/);
await control('edit-reading', id('action-edit-reading'));
await control('edit-value', id('field-reading'));
adb('shell', 'input', 'keyevent', 'KEYCODE_MOVE_END');
adb('shell', 'input', 'keyevent', '67', '67', '67');
adb('shell', 'input', 'text', '112');
adb('shell', 'input', 'keyevent', 'KEYCODE_BACK');
await control('review-changes', id('action-review-reading'));
await visible('edited-reading', /Saved to your account/);
assert.match(currentXml, /112/);
await control('remove-test-reading', id('action-remove-reading'));
await control('confirm-remove', text('Delete reading'));
await visible('removed-test-reading', /Reading removed/);
adb('shell', 'am', 'force-stop', app);
open('glucose-overview');
await visible('empty-after-delete-and-restart', /No readings yet/);

// Select an actual synthetic photo through Android DocumentsUI, then review and
// save it through the same controls a person uses. No platform/parser mock.
const photo = 'glucose-qa-report.jpg';
adb('push', path.resolve('tests/glucose/fixtures/chughtai-style-photo.jpg'), `/sdcard/Download/${photo}`);
adb('shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', `file:///sdcard/Download/${photo}`);
open('glucose-import');
await visible('file-import-start', /screen-glucose-import/);
await control('attach-report', id('action-import-file'));
await visible('android-report-picker', /glucose-qa-report\.jpg/, null);
await control('select-report-photo', text(photo), null);
await visible('photo-ocr-review', /screen-import-review/);
assert.match(currentXml, /112 mg\/dL/);
screenshot('photo-ocr-review');
await control('check-photo-reading', n => /action-import-row-/.test(n['resource-id'] || ''));
await control('confirm-photo-reading', n => /^(I checked it · Confirm|Confirm reading)$/.test(n.text || ''));
await control('save-photo-reading', id('action-import-save'));
await visible('photo-reading-saved', /screen-glucose-overview/);
adb('shell', 'am', 'force-stop', app);
open('glucose-overview');
await visible('photo-history-after-restart', /112/);
assert.doesNotMatch(currentXml, /Sign in to see your readings/);
screenshot('photo-history-after-restart');
await control('open-imported-reading', n => /action-open-reading-/.test(n['resource-id'] || ''));
await control('edit-imported-reading', id('action-edit-reading'));
await control('correct-imported-value', id('field-reading'));
adb('shell','input','keyevent','KEYCODE_MOVE_END'); adb('shell','input','keyevent','67','67','67');
adb('shell','input','text','114'); adb('shell','input','keyevent','KEYCODE_BACK');
await control('save-imported-correction', id('action-review-reading'));
await visible('saved-imported-correction',/Saved to your account/); assert.match(currentXml,/114/);
screenshot('saved-imported-correction');

// A report with no collection time must be fixable through the visible Confirm form.
const incomplete = 'glucose-qa-missing-time.csv';
adb('push', path.resolve('tests/glucose/fixtures/missing-time.csv'), '/sdcard/Download/'+incomplete);
adb('shell','am','broadcast','-a','android.intent.action.MEDIA_SCANNER_SCAN_FILE','-d','file:///sdcard/Download/'+incomplete);
open('glucose-import'); await visible('incomplete-import-start', /screen-glucose-import/);
await control('attach-incomplete',id('action-import-file'));
await visible('incomplete-picker', /glucose-qa-missing-time/, null); await control('select-incomplete',text(incomplete),null);
await visible('incomplete-review',/screen-import-review/);
await control('confirm-incomplete',id('action-import-bulk-confirm-clean'));
await visible('editable-incomplete',/Check reading/);
await control('try-missing-time',text('Confirm reading'));
await visible('missing-time-error',/Enter the measurement time/);
screenshot('confirm-missing-time-error');
await control('fix-missing-time',n=>n['content-desc']==='Time'&&n.class==='android.widget.EditText');
adb('shell','input','text','09:25'); adb('shell','input','keyevent','KEYCODE_BACK');
await control('confirm-fixed-time',text('Confirm reading'));
await control('save-corrected-report',id('action-import-save'));
await visible('corrected-report-saved',/screen-glucose-overview/);
screenshot('corrected-report-saved');
// Capture entry is present. Physical camera/document scanner validation is separate.
const routes = [];
for (const screen of directoryScreens) {
  open(screen.route);
  await visible(`route-${screen.route}`, new RegExp(`resource-id="[^"]*screen-${screen.route}"`));
  const labels = nodes().map(n => n.text || n['content-desc']).filter(Boolean);
  routes.push({ route: screen.route, labels, xmlSha256: crypto.createHash('sha256').update(currentXml).digest('hex') });
  console.log(`Rendered ${screen.route}`);
}
open('glucose-import');
await visible('import-sources', /Attach a file/);
screenshot('import-sources');
open('flow-directory'); await control('account-sign-out', text('Sign out'));
await control('confirm-account-sign-out', text('Sign out'));
await visible('signed-out-form', /screen-sign-in/);
open('flow-directory'); await visible('signed-out-menu', /Sign in/); assert.doesNotMatch(currentXml, /Sign out/);
adb('shell','am','force-stop',app); open('glucose-overview');
await visible('signed-out-after-restart', /Sign in to see your readings/);
const errors = adb('logcat', '-d', `--uid=${appUid}`, '-s', 'ReactNativeJS:E', 'AndroidRuntime:E');
fs.writeFileSync(path.join(out, 'runtime-errors.txt'), errors);
assert.doesNotMatch(errors, /FATAL EXCEPTION|TypeError:|ReferenceError:|Unable to load script|Invariant Violation/);
fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ syntheticOnly: true, apkSourceCommit: process.env.NUTRISOLE_APK_SOURCE_SHA || null, smokeSourceCommit: process.env.GITHUB_SHA || null, systemLauncherAnrsDismissed: launcherAnrs, manualCreateRestartEditDelete: true, filePickerOcrReviewSaveRestart: true, missingTimeCorrection: true, importedReadingCorrection: true, signOutRestart: true, accountStorage: true, standaloneWithoutMetro: true, routes }, null, 2));
console.log(`Standalone account CRUD, report photo import, missing-time correction and ${routes.length} rendered routes passed.`);
