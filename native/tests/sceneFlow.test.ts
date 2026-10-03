import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compileScene, fixedColumnWidth, type FlowNode } from '../responsive/sceneFlow.ts';
import { buildScene, initialExpansionState, extensionRoutes } from '../../src/nutrisole/extensions/model.ts';
const flatten = (nodes: FlowNode[]): FlowNode[] => nodes.flatMap(n => [n, ...flatten(n.children)]);
test('a selectable food is one growing card with its original action and content', () => {
  const flow = compileScene(buildScene('food-selector'));
  const apple = flow.body.find(n => n.actionLayer?.action === 'choose:food:Apple');
  assert.ok(apple, 'Apple selection must be attached to its card, not a detached rectangle');
  assert.ok(flatten(apple.children).some(n => n.layer.text === 'Apple'));
  assert.ok(flatten(apple.children).some(n => n.layer.kind === 'photo'));
});
test('account fields stay inside their labelled cards', () => {
  const flow = compileScene(buildScene('create-account'));
  const emailCard = flow.body.find(n => n.layer.kind === 'surface' && flatten(n.children).some(c => c.layer.field === 'email'));
  assert.ok(emailCard, 'Email input must move with its card when the Name card grows');
  assert.ok(flatten(emailCard.children).some(n => n.layer.text === 'Email'));
});
test('the assistant composer has its own footer, outside scrolling messages', () => {
  const flow = compileScene(buildScene('assistant'));
  assert.ok(flatten(flow.footer).some(n => n.layer.field === 'assistantQuestion'));
  assert.ok(flatten(flow.footer).some(n => n.layer.action === 'assistant-send'));
  assert.ok(!flatten(flow.body).some(n => n.layer.field === 'assistantQuestion'));
});
test('a brand mark and its wordmark stay in the same scroll region', () => {
  const flow = compileScene(buildScene('plan-generation'));
  const hasBrand = (nodes: FlowNode[]) => nodes.some(n => n.layer.asset === 'leaf-brand-mark') && nodes.some(n => n.layer.text === 'NutriSole');
  assert.ok(hasBrand(flow.header) || hasBrand(flow.body), 'A header cutoff must not separate the brand into two regions');
});
test('compact source switch and back artwork reserve their actual native control width', () => {
  const account = compileScene(buildScene('create-account'));
  const terms = account.body.find(n => n.layer.kind === 'toggle');
  assert.ok(terms);
  assert.equal(fixedColumnWidth([terms]), 43, 'Consent text must not overlap the native switch');
  const back = compileScene(buildScene('verify-email')).header.find(n => n.layer.action === 'back');
  assert.ok(back);
  assert.equal(fixedColumnWidth([back]), 36, 'The header must reserve the complete back touch target');
});
test('every extension scene retains every original action and input field', () => {
  for (const route of extensionRoutes) {
    const scene = buildScene(route, initialExpansionState());
    const flow = compileScene(scene);
    const all = flatten([...flow.header, ...flow.body, ...flow.footer]);
    const actions = new Set(all.flatMap(n => [n.layer.action, n.actionLayer?.action]).filter(Boolean));
    const fields = new Set(all.map(n => n.layer.field).filter(Boolean));
    for (const l of scene.layers) {
      if (l.action) assert.ok(actions.has(l.action), `${route}: lost ${l.action}`);
      if (l.kind === 'input') assert.ok(fields.has(l.field), `${route}: lost input ${l.field}`);
    }
  }
});
