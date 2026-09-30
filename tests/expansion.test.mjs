import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import vm from 'node:vm';
import { stripTypeScriptTypes } from 'node:module';
import { extensionRoutes, initialExpansionState, buildScene } from '../src/nutrisole/extensions/model.ts';
const modelURL = new URL('../src/nutrisole/extensions/model.ts', import.meta.url).href;
const domainCode = stripTypeScriptTypes(fs.readFileSync(new URL('../src/nutrisole/extensions/domain.ts', import.meta.url), 'utf8')).replaceAll("'./model'", JSON.stringify(modelURL));
const { accountError, readingResult, saveReading, mealResult, assistantReply } = await import('data:text/javascript;base64,' + Buffer.from(domainCode).toString('base64'));

test('the six original screens and their shared artwork are unchanged', () => {
  const baseline = JSON.parse(fs.readFileSync('artifacts/expansion/six-screen-baseline.json', 'utf8'));
  for (const [file, hash] of Object.entries(baseline)) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), hash, file);
});
test('all 30 requested concepts use component layers and individual assets', () => {
  const concepts = JSON.parse(fs.readFileSync('artifacts/screen-coverage/concept-manifest.json', 'utf8')).concepts;
  assert.equal(concepts.length, 30);
  for (const concept of concepts) {
    assert.ok(extensionRoutes.includes(concept.id)); const scene = buildScene(concept.id);
    assert.ok(scene.layers.some(l => l.kind === 'text')); assert.ok(scene.layers.some(l => l.action));
    for (const l of scene.layers) { assert.ok([l.x, l.y, l.w, l.h].every(Number.isFinite)); assert.ok(l.w > 0 && l.h > 0); assert.ok(l.x >= 0 && l.x + l.w <= 393, `${concept.id}: ${l.text || l.kind}`); assert.ok(l.y >= 54, `status area: ${concept.id}`); if (l.asset) assert.ok(!l.asset.includes(concept.id), 'a whole reference screen cannot be an asset'); }
  }
});
test('account validation checks email, consent and matching passwords', () => {
  const s = initialExpansionState(); assert.match(accountError(s, 'create-account'), /name/);
  s.fields = { name: 'Alex', email: 'bad-email', password: 'demo-pass' }; assert.match(accountError(s, 'create-account'), /email/);
  s.fields.email = 'alex@example.org'; assert.match(accountError(s, 'create-account'), /Terms/); s.toggles.terms = true; assert.equal(accountError(s, 'create-account'), undefined);
  s.fields.newPassword = 'demo-pass'; s.fields.confirmPassword = 'other-pass'; assert.match(accountError(s, 'reset-password'), /match/);
});
test('manual readings validate values and deduplicate a reviewed record', () => {
  let s = initialExpansionState(); assert.match(readingResult(s).error, /positive/);
  s.fields.reading = '-1'; assert.ok(readingResult(s).error); s.fields.reading = '110'; const record = readingResult(s).record; assert.ok(record); s = saveReading(s, record); assert.equal(s.readings.length, 1);
  s.currentReading = null; assert.match(readingResult(s).error, /already/); s.currentReading = record; s.fields.reading = '111'; s = saveReading(s, readingResult(s).record); assert.equal(s.readings.length, 1); assert.equal(s.readings[0].value, 111);
  s.choices.unit = 'mmol/L'; s.fields.reading = '110'; assert.match(readingResult(s).error, /range/);
  s.choices.unit = 'mg/dL'; s.fields.reading = '110'; s.choices.date = 'Sep 31, 2026'; assert.match(readingResult(s).error, /date/);
});
test('portion calculations use the selected food and preserve drafts', () => {
  const s = initialExpansionState(); assert.equal(mealResult(s, false).meal.calories, 95);
  s.choices.food = 'Banana'; assert.equal(mealResult(s, true).meal.food, 'Banana'); assert.equal(mealResult(s, true).meal.draft, true);
  s.choices.portion = 'By weight'; s.fields.grams = '200'; assert.equal(mealResult(s, false).meal.calories, 178); s.fields.grams = '0'; assert.ok(mealResult(s, false).error);
});
test('assistant dose questions remain within the stated support boundary', () => { assert.match(assistantReply('Which insulin dose?'), /cannot diagnose/); assert.match(assistantReply('help with my plan'), /declared allergens/); });
test('recorded foot concerns visibly defer activity and substitution', () => { const s = initialExpansionState(); s.choices.comfort = 'Concern'; const scene = buildScene('activity-plan', s); assert.ok(scene.layers.some(l => l.text === 'Activity deferred')); assert.ok(scene.layers.some(l => l.text === 'Substitute' && l.disabled)); assert.ok(!scene.layers.some(l => l.action === 'complete-activity')); });

test('the Figma importer builds editable nodes and leaves six protected frames intact', async () => {
  const html = fs.readFileSync('artifacts/figma-expansion/ui.html', 'utf8');
  const payload = JSON.parse(html.match(/const payload = (.*);\n/)[1]);
  const nodes = new Map(); let serial = 1;
  const make = type => {
    const n = { id: `new:${serial++}`, type, name: '', x: 0, y: 0, width: 100, height: 100, children: [], reactions: [], fills: [], strokes: [], data: {}, resize(w, h) { this.width = w; this.height = h; }, appendChild(ch) { if (ch.parent) ch.parent.children = ch.parent.children.filter(n => n !== ch); this.children.push(ch); ch.parent = this; }, findAll(fn) { return this.children.flatMap(c => [c, ...c.findAll(() => true)]).filter(fn); }, findOne(fn) { return this.findAll(fn)[0] || null; }, setPluginData(k, v) { this.data[k] = v; }, getPluginData(k) { return this.data[k] || ''; }, async setReactionsAsync(r) { this.reactions = r; }, addComponentProperty(k, type, value) { return k; }, setProperties(props) { for (const t of this.findAll(n => n.type === 'TEXT')) if (t.componentPropertyReferences?.characters in props) t.characters = props[t.componentPropertyReferences.characters]; }, createInstance() { const clone = original => { const c = make(original === this ? 'INSTANCE' : original.type); for (const [k, value] of Object.entries(original)) if (['name', 'x', 'y', 'width', 'height', 'fills', 'strokes', 'characters', 'fontName', 'componentPropertyReferences', 'reactions'].includes(k)) c[k] = value; for (const child of original.children) c.appendChild(clone(child)); return c; }; return clone(this); } };
    n.clone = () => clone(n, n.type);
    n.rescale = function(scale) { this.resize(this.width * scale, this.height * scale); for (const child of this.children) { child.x *= scale; child.y *= scale; child.rescale(scale); } };
    const storeData = n.setPluginData; n.setPluginData = function(k, v) { assert.ok(Buffer.byteLength(v, 'utf8') <= 100000, 'Figma pluginData entries are limited to 100 kB'); storeData.call(this, k, v); };
    n.setReactionsAsync = async function(reactions) { for (const r of reactions) for (const a of r.actions || []) if (a.type === 'NODE' && a.navigation === 'NAVIGATE') { let source = this; while (source.parent && source.parent.type !== 'PAGE') source = source.parent; const destination = nodes.get(a.destinationId); assert.ok(destination); assert.notEqual(source.id, destination.id, 'Figma rejects navigating a frame to itself'); assert.equal(source.parent, destination.parent, 'prototype navigation stays on the same page'); } this.reactions = reactions; };
    for (const key of ['fills', 'strokes']) { let paints = []; Object.defineProperty(n, key, { enumerable: true, get: () => paints, set: value => { for (const paint of value) if (paint.type === 'SOLID') assert.ok(['r', 'g', 'b'].every(k => Number.isFinite(paint.color[k]) && paint.color[k] >= 0 && paint.color[k] <= 1), 'Figma paint channels must be finite numbers in [0, 1]'); paints = value; } }); }
    const append = n.appendChild;
    n.appendChild = function(ch) { assert.notEqual(this.type, 'INSTANCE', 'SDK instances cannot receive new children'); append.call(this, ch); };
    n.createInstance = () => clone(n, 'INSTANCE');
    nodes.set(n.id, n); return n;
  };
  const clone = (original, type) => { const c = make(type); for (const [k, value] of Object.entries(original)) if (['name', 'x', 'y', 'width', 'height', 'fills', 'strokes', 'characters', 'fontName', 'componentPropertyReferences', 'reactions'].includes(k)) c[k] = value; for (const child of original.children) { const copy = clone(child, child.type); c.children.push(copy); copy.parent = c; } return c; };
  const root = make('DOCUMENT'); const oldPage = make('PAGE'); root.appendChild(oldPage);
  for (const id of Object.values(payload.originalFrames)) { const n = make('FRAME'); nodes.delete(n.id); n.id = id; n.name = 'Original'; nodes.set(id, n); oldPage.appendChild(n); const t = make('TEXT'); t.characters = 'Protected original'.repeat(2000); n.appendChild(t); }
  const messages = []; const figma = {
    root, currentPage: oldPage, ui: { postMessage: m => messages.push(m) }, showUI() {}, notify() {}, viewport: { scrollAndZoomIntoView() {} }, async listAvailableFontsAsync() { return [{ family: 'Roboto', style: 'Regular' }, { family: 'Roboto', style: 'SemiBold' }, { family: 'Libre Caslon Display', style: 'Regular' }, { family: 'Libre Caslon Text', style: 'Bold' }].map(fontName => ({fontName})); }, async loadFontAsync() {}, async getNodeByIdAsync(id) { return nodes.get(id); }, async setCurrentPageAsync(p) { this.currentPage = p; }, createImage(bytes) { assert.ok(bytes.length > 10); return { hash: crypto.createHash('sha256').update(bytes).digest('hex') }; },
    createPage() { const p = make('PAGE'); root.appendChild(p); return p; }, createFrame: () => make('FRAME'), createComponent: () => make('COMPONENT'), createText: () => make('TEXT'), createEllipse: () => make('ELLIPSE'), createNodeFromSvg(svg) { assert.match(svg, /viewBox=/); const f = make('FRAME'); f.appendChild(make('VECTOR')); return f; }, combineAsVariants(items, parent) { const set = make('COMPONENT_SET'); parent.appendChild(set); items.forEach(n => set.appendChild(n)); return set; },
    variables: { createVariableCollection() { return { modes: [{ modeId: 'reference' }] }; }, createVariable() { return { setValueForMode() {}, setVariableCodeSyntax() {} }; }, setBoundVariableForPaint: p => p }, createTextStyle() { return {}; },
  };
  vm.runInNewContext(fs.readFileSync('artifacts/figma-expansion/code.js', 'utf8'), { figma, __html__: html, Uint8Array });
  await figma.ui.onmessage({ type: 'build', payload: { ...payload, colors: { ...payload.colors, cream: '#zzzzzz' } } }); assert.equal(messages.at(-1).type, 'error'); assert.equal(root.children.length, 1, 'invalid colours must fail before adding a page');
  await figma.ui.onmessage({ type: 'build', payload });
  const result = messages.at(-1); assert.equal(result.type, 'complete', JSON.stringify(result)); assert.equal(result.primaryFrames, 32); assert.equal(result.stateFrames, 53); assert.equal(result.referenceContinuations, 6); assert.ok(result.textNodes > 700); assert.ok(result.instances > 800); assert.ok(result.prototypeLinks > 300); assert.deepEqual(Object.values(result.originalScreensUnchanged), [true, true, true, true, true, true]); assert.equal(result.wholeScreenImages, 0);
  fs.writeFileSync('artifacts/expansion/importer-simulation.json', JSON.stringify({ mode: 'Mock SDK structural simulation; not a live Figma import or screenshot verification', ...result }, null, 2));
  await figma.ui.onmessage({ type: 'build', payload }); assert.equal(messages.at(-1).type, 'error'); assert.equal(root.children.length, 2, 'a repeated import must not duplicate the page');
  const failed = figma.currentPage; nodes.delete(failed.id); failed.id = '34:254'; nodes.set(failed.id, failed); failed.setPluginData('status', 'failed');
  await figma.ui.onmessage({ type: 'build', payload }); assert.equal(messages.at(-1).type, 'complete'); assert.equal(messages.at(-1).recoveryArchivePreserved, true); assert.equal(root.children.length, 2, 'recovery must use the same page');
  const archive = failed.children.find(n => n.getPluginData('recoveryArchive') === 'v1'); assert.ok(archive); assert.equal(archive.visible, false); assert.ok(archive.children.length > 30, 'unfinished nodes are retained, not deleted');
  assert.ok(Number(failed.getPluginData('originalSnapshots/count')) > 1, 'large preservation snapshots are stored in bounded chunks');
  await figma.ui.onmessage({ type: 'inspect' }); const live = messages.at(-1); assert.equal(live.status, 'complete'); assert.equal(live.brokenLinks.length, 0); assert.ok(live.navigationLinks > 300); assert.deepEqual(Object.values(live.originalScreensUnchanged), [true, true, true, true, true, true]);
});
