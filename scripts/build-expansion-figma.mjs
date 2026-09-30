import fs from 'node:fs';
import path from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import * as lucide from 'lucide-react';
const root = process.cwd();
const model = await import('../src/nutrisole/extensions/model.ts');
const initial = model.initialExpansionState();
const scenes = model.extensionRoutes.map(id => model.buildScene(id, initial));
const assets = Object.fromEntries([...new Set(scenes.flatMap(s => s.layers.filter(l => l.asset).map(l => l.asset)))].map(name => {
  const file = path.join(name.startsWith('extension-') ? 'assets/expansion' : 'assets/source', name + '.png');
  return [name, fs.readFileSync(file).toString('base64')];
}));
const iconNames = [...new Set(['Eye', ...scenes.flatMap(s => s.layers.filter(l => l.icon).map(l => l.icon))])];
// Exact installed library SVGs, not reconstructed paths.
const icons = Object.fromEntries(iconNames.map(name => [name, renderToStaticMarkup(React.createElement(lucide[name], { size: 24, color: '#123f2c', strokeWidth: 1.6 }))]));
const direct = {
  'sign-in': 'flow-directory', 'create-account': 'verify-email', 'reset-password': 'sign-in',
  'verify-demo': 'sign-in', 'new-reading': 'add-reading', 'latest-reading': 'reading-detail',
  'edit-reading': 'add-reading', 'create-plan': 'plan-rationale', 'assistant-food': 'assistant',
  'assistant-plan': 'assistant', 'assistant-send': 'assistant',
};
const dialogs = {
  recover: ['Check your inbox', 'If an account exists, a recovery link would be sent. No email is sent by this frontend prototype.', [['Preview recovery link', 'reset-password']]],
  resend: ['Verification link', 'Preview the verified or expired-link state. No email is sent.', [['Valid link', 'sign-in'], ['Use another email', 'create-account']]],
  evidence: ['Assessment evidence', 'Sample colour: even red. Shape: whole apple. Surface: minor marks. Confidence 97%. Model v1.0 · Rubric v1.0. A photo cannot determine food safety.', [['Correct food label', 'food-selector'], ['Report assessment', 'report-output']]],
  market: ['Choose a market', 'Local retail, wholesale and online are demo selectors. No verified price, source or observation date is available.', [['Local retail · Demo', 'market-reference'], ['Wholesale · Demo', 'market-reference']]],
  'review-reading': ['Review manual reading', 'Sample entry: 110 mg/dL · Sep 30, 2026 · 8:15 AM · Pacific Time · Before a meal · Manual meter entry.', [['Confirm & save', 'reading-detail'], ['Edit value', 'add-reading']]],
  'remove-reading': ['Remove manual record?', 'This is a synthetic prototype record. Removal has no effect on the original six screens.', [['Remove record', 'glucose-overview']]],
  permissions: ['Review requested permissions', 'Choose what to share. Apple Health is not connected. The prototype requests no OS permissions and imports no records.', [['Manual entry', 'add-reading'], ['Review consent', 'privacy-data-rights']]],
  'choose-photo': ['Choose a sample photo', 'No real file is uploaded. Preview a supported image or retry state.', [['Clear single apple', 'analysis-result'], ['Blurred photo', 'capture-retry']]],
  'review-foot': ['Review answers', 'Shoe fit: Comfortable. Comfort: No concern. Mobility: Unrestricted. Rule set v1 · General information only.', [['See general guidance', 'foot-guidance'], ['Edit answers', 'foot-questionnaire']]],
  'substitute-activity': ['Substitute activity', 'A sample alternative is comfortable stretching. A recorded concern defers activity.', [['Choose alternative', 'activity-plan'], ['Review comfort', 'foot-questionnaire']]],
  'save-meal': ['Confirm portion', 'Apple · 182 g · ≈ 95 calories. Values are sample estimates.', [['Log meal', 'personal-history'], ['Edit portion', 'portion-confirmation']]],
  'draft-meal': ['Save a draft?', 'Drafts are saved for later and are not marked as consumed.', [['Save draft', 'personal-history']]],
  'review-report': ['Review shared report', 'Output: ANALYSIS-DEMO-17. Reason: Wrong food. Optional details only. No health history or photo is attached.', [['Submit demo report', 'report-status'], ['Edit report', 'report-output']]],
  'save-preferences': ['Preferences saved', 'Preferences apply to the demo. No health-provider data is imported.', [['Review reminders', 'reminders'], ['Explore flows', 'flow-directory']]],
  'save-reminders': ['Reminder preferences saved', 'Notifications remain inactive. No OS notification is scheduled.', [['Return to privacy', 'privacy-data-rights']]],
  export: ['Export my data', 'Demo export only. Added session readings, meals and report references can be reviewed in the frontend. No provider data is included.', []],
  retained: ['Retained records', 'Only new demo session records are included. Original screen fixtures are preserved.', []],
  'delete-account': ['Confirm demo deletion', 'A real account deletion requires reauthentication. No server account exists in this prototype.', [['Confirm demo deletion', 'sign-in']]],
  'catalog-save': ['Draft review saved', 'The draft remains unpublished. Source verification and observation evidence are required.', [['Back to queue', 'catalog-queue']]],
  'catalog-reject': ['Reject draft', 'A rejection reason is required. Original source evidence is retained.', [['Confirm sample rejection', 'catalog-queue']]],
  'release-evidence': ['Release evidence', 'Manifest present. Dataset licence and class thresholds need review. Safety regression pending. Candidate v1.1 cannot activate.', []],
  rollback: ['Rollback history', 'Active sample package v1.0. No earlier verified package is available. A real rollback requires administrator confirmation.', []],
  'filter-audit': ['Audit filters', 'Sample redacted metadata only. No health payload, credential or personal health record is exposed.', [['View filtered audit', 'operations-audit']]],
  'triage-save': ['Review saved', 'Sample report DEMO-104. Original analysis evidence is retained. No real support service is contacted.', [['View report status', 'report-status']]],
  'staff-workspace': ['Staff preview workspace', 'Select a role to view synthetic staff flows. This does not grant production access.', [['Catalog curator', 'catalog-queue'], ['Model administrator', 'model-release'], ['Operations administrator', 'operations-audit'], ['Support curator', 'report-triage']]],
};
// Selected states become editable frames. Other form/detail actions use native overlays.
const stateScenes = [];
const selectionTargets = {};
for (const scene of scenes) for (const l of scene.layers) {
  if (l.action?.startsWith('choose:')) {
    const [, key, value] = l.action.split(':'); const stateId = `${scene.id}__${key}__${value}`;
    if (!stateScenes.some(s => s.id === stateId)) {
      const state = model.initialExpansionState(); state.choices[key] = value;
      stateScenes.push({ ...model.buildScene(scene.id, state), id: stateId, baseId: scene.id, title: `${scene.title} · ${key}: ${value}` });
    }
    selectionTargets[`${scene.id}|${l.action}`] = stateId;
  }
}
for (const id of ['sign-in', 'create-account', 'reset-password', 'add-reading', 'report-output', 'report-triage', 'portion-confirmation']) {
  const state = model.initialExpansionState();
  state.fields = { email: 'alex@example.org', name: 'Alex', password: '••••••••', newPassword: '••••••••', confirmPassword: '••••••••', reading: '110', reportDetails: 'The food label needs review.', triageNote: 'Reviewed sample evidence.', amount: '1' };
  state.toggles.terms = true;
  stateScenes.push({ ...model.buildScene(id, state), id: `${id}__filled`, baseId: id, title: `${id.replaceAll('-', ' ')} · filled demo` });
}
for (const food of ['Banana', 'Tomato']) for (const id of ['nutrition-details', 'portion-confirmation']) {
  const state = model.initialExpansionState(); state.choices.food = food;
  stateScenes.push({ ...model.buildScene(id, state), id: `${id}__food__${food}`, baseId: id, title: `${id.replaceAll('-', ' ')} · ${food}` });
}
const payload = { version: 1, source: 'NutriSole frontend expansion', scenes, stateScenes, assets, icons, colors: model.colors, direct, dialogs, selectionTargets, originalFrames: { onboarding: '2:4', home: '2:5', scan: '2:6', 'log-meal': '2:8', 'weekly-plan': '2:9', profile: '2:10' } };
const out = 'artifacts/figma-expansion'; fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(`${out}/scene-manifest.json`, JSON.stringify({ ...payload, assets: Object.keys(assets), icons: Object.keys(icons) }, null, 2));
const template = fs.readFileSync('scripts/figma-expansion-ui.html', 'utf8');
fs.writeFileSync(`${out}/ui.html`, template.replace('/* PAYLOAD */', JSON.stringify(payload).replaceAll('<', '\u003c')));
fs.copyFileSync('scripts/figma-expansion-plugin.js', `${out}/code.js`);
fs.writeFileSync(`${out}/manifest.json`, JSON.stringify({ name: 'NutriSole · Add missing flows', id: 'nutrisole-expanded-flows-local', api: '1.0.0', main: 'code.js', ui: 'ui.html', editorType: ['figma'], documentAccess: 'dynamic-page', networkAccess: { allowedDomains: ['none'] } }, null, 2));
fs.writeFileSync('artifacts/expansion/scene-manifest.json', JSON.stringify(scenes, null, 2));
console.log(`${scenes.length} primary frames, ${stateScenes.length} state frames; ${Object.keys(assets).length} discrete photos and ${iconNames.length} library SVGs packaged.`);
