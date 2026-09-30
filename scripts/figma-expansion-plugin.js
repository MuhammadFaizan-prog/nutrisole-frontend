// Standard Figma development plugin. The six original frames are never mutated.
figma.showUI(__html__, { width: 430, height: 500, themeColors: true });
let running = false;
figma.ui.onmessage = async message => {
  if (message.type === 'inspect') { await inspectPage(); return; }
  if (message.type === 'focus') { const node = await figma.getNodeByIdAsync(message.id); if (node && node.type === 'FRAME' && node.parent === figma.currentPage && figma.currentPage.getPluginData('nutrisole-expansion') === 'v1') { figma.currentPage.selection = [node]; figma.viewport.scrollAndZoomIntoView([node]); } return; }
  if (message.type === 'export-qa' && !running) { await exportQA(); return; }
  if (message.type === 'refine' && !running) { await refineIcons(message.payload); return; }
  if (message.type !== 'build' || running) return;
  running = true; let page;
  try {
    const p = message.payload;
    if (!p || p.version !== 1 || p.scenes.length !== 32) throw new Error('Invalid expansion payload.');
    const existing = figma.root.children.find(n => n.getPluginData('nutrisole-expansion') === 'v1');
    if (existing && !(existing.id === '34:254' && existing.getPluginData('status') === 'failed')) throw new Error('An expansion page already exists. Inspect it before importing again; existing frames were not changed.');
    // Validate every colour before creating any Figma nodes. CSS shorthand is valid.
    for (const hex of Object.values(p.colors)) rgb(hex);
    for (const scene of [...p.scenes, ...p.stateScenes]) for (const layer of scene.layers) for (const key of ['fill', 'color', 'stroke']) if (layer[key]) rgb(layer[key]);
    const fonts = { regular: { family: 'Roboto', style: 'Regular' }, bold: { family: 'Roboto', style: 'SemiBold' }, serif: { family: 'Libre Caslon Display', style: 'Regular' }, serifBold: { family: 'Libre Caslon Text', style: 'Bold' } };
    const availableFonts = await figma.listAvailableFontsAsync();
    for (const key of Object.keys(fonts)) {
      const requested = fonts[key];
      const available = availableFonts.find(f => f.fontName.family === requested.family && f.fontName.style.replace(/\s/g, '').toLowerCase() === requested.style.replace(/\s/g, '').toLowerCase());
      if (!available) throw new Error(`Required font unavailable: ${requested.family} ${requested.style}. Nothing was imported.`);
      fonts[key] = available.fontName;
    }
    await Promise.all(Object.values(fonts).map(f => figma.loadFontAsync(f)));
    const originals = {};
    const originalNodes = {};
    for (const [name, id] of Object.entries(p.originalFrames)) {
      const node = await figma.getNodeByIdAsync(id);
      if (!node || node.type !== 'FRAME') throw new Error(`Original ${name} frame was not found. Open the existing NutriSole file; nothing was imported.`);
      originalNodes[name] = node; originals[name] = snapshot(node);
    }
    const imageHashes = {};
    for (const [name, base64] of Object.entries(p.assets)) imageHashes[name] = figma.createImage(decode(base64)).hash;
    page = existing || figma.createPage(); page.name = 'NutriSole · Expanded flows'; page.setPluginData('nutrisole-expansion', 'v1');
    await figma.setCurrentPageAsync(page);
    if (existing) {
      // Keep the failed attempt recoverable. No nodes or original screens are deleted.
      const prior = page.children.filter(n => n.getPluginData('recoveryArchive') !== 'v1');
      if (prior.length) { const recovery = figma.createFrame(); recovery.name = 'Recovery archive / incomplete first import'; recovery.resize(100, 100); recovery.x = -6000; recovery.y = -6000; recovery.clipsContent = false; page.appendChild(recovery); for (const child of prior) recovery.appendChild(child); recovery.visible = false; recovery.setPluginData('recoveryArchive', 'v1'); }
      page.setPluginData('recoveredFrom', '34:254');
    }
    page.setPluginData('status', 'building'); storeChunks(page, 'originalSnapshots', JSON.stringify(originals));
    const collection = figma.variables.createVariableCollection('NutriSole / Expansion');
    const mode = collection.modes[0].modeId; const tokens = {};
    for (const [name, hex] of Object.entries(p.colors)) { const variable = figma.variables.createVariable(`color/${name}`, collection, 'COLOR'); variable.scopes = ['FRAME_FILL', 'SHAPE_FILL', 'TEXT_FILL', 'STROKE_COLOR']; variable.setVariableCodeSyntax('iOS', `colors.${name}`); variable.setValueForMode(mode, { ...rgb(hex), a: 1 }); tokens[hex] = variable; }
    const paint = hex => {
      /** @type {SolidPaint} */
      const value = { type: 'SOLID', color: rgb(hex), opacity: hex === 'transparent' ? 0 : 1 };
      return tokens[hex] ? figma.variables.setBoundVariableForPaint(value, 'color', tokens[hex]) : value;
    };
    const library = figma.createFrame(); library.name = 'Expansion component library'; library.resize(2100, 880); library.x = 0; library.y = -1020; library.fills = [paint(p.colors.cream)]; library.layoutMode = 'HORIZONTAL'; library.layoutWrap = 'WRAP'; library.itemSpacing = 24; library.counterAxisSpacing = 24; library.paddingTop = 24; library.paddingBottom = 24; library.paddingLeft = 24; library.paddingRight = 24; library.primaryAxisSizingMode = 'FIXED'; library.counterAxisSizingMode = 'AUTO'; page.appendChild(library);
    const textStyles = {};
    for (const [name, font] of Object.entries(fonts)) { const style = figma.createTextStyle(); style.name = `NutriSole / Expansion / ${name}`; style.fontName = font; style.fontSize = 16; style.lineHeight = { unit: 'PIXELS', value: 20 }; textStyles[name] = style; }
    const masters = {};
    function master(name, w, h, fill, radius, label, color = p.colors.ink) {
      const c = figma.createComponent(); c.name = name; c.resize(w, h); c.fills = fill ? [paint(fill)] : []; c.cornerRadius = radius; c.layoutMode = 'VERTICAL'; c.primaryAxisSizingMode = 'FIXED'; c.counterAxisSizingMode = 'FIXED'; c.primaryAxisAlignItems = 'CENTER'; c.counterAxisAlignItems = 'CENTER'; c.clipsContent = false; library.appendChild(c);
      if (label !== undefined) { const t = figma.createText(); t.fontName = fonts.regular; t.fontSize = 16; t.characters = label; t.fills = [paint(color)]; c.appendChild(t); const prop = c.addComponentProperty('Label', 'TEXT', label); t.componentPropertyReferences = { characters: prop }; c.setPluginData('labelKey', prop); }
      if (label !== undefined && (name.startsWith('Button/') || name === 'Input')) {
        c.layoutMode = 'HORIZONTAL'; c.itemSpacing = 10; c.paddingLeft = 16; c.paddingRight = 16;
        const t = c.findOne(n => n.type === 'TEXT'); const showLabel = c.addComponentProperty('Show label', 'BOOLEAN', true); t.componentPropertyReferences = { ...t.componentPropertyReferences, visible: showLabel }; c.setPluginData('showLabelKey', showLabel);
        const slot = masters['Icon/Info'].createInstance(); slot.name = 'Icon slot'; slot.rescale(23 / 24); slot.visible = false; c.appendChild(slot);
        const iconKey = c.addComponentProperty('Icon', 'INSTANCE_SWAP', masters['Icon/Info'].id); const showIcon = c.addComponentProperty('Show icon', 'BOOLEAN', false); slot.componentPropertyReferences = { mainComponent: iconKey, visible: showIcon }; c.setPluginData('iconKey', iconKey); c.setPluginData('showIconKey', showIcon);
      }
      masters[name] = c; return c;
    }
    for (const [name, svg] of Object.entries(p.icons)) { const c = master(`Icon/${name}`, 24, 24, null, 0); c.clipsContent = false; const v = figma.createNodeFromSvg(svg); v.resize(24, 24); c.appendChild(v); }
    master('Surface', 353, 72, p.colors.card, 18);
    master('Button/Primary', 353, 54, p.colors.green, 17, 'Continue', '#fffdf9');
    master('Button/Secondary', 353, 54, p.colors.card, 17, 'Continue', p.colors.green);
    master('Button/Text', 353, 42, null, 0, 'Continue', p.colors.green);
    const input = master('Input', 345, 55, p.colors.card, 14, 'Enter value'); input.primaryAxisAlignItems = 'CENTER'; input.counterAxisAlignItems = 'MIN'; input.paddingLeft = 16; input.paddingRight = 16; input.strokes = [paint(p.colors.border)]; input.strokeWeight = .7;
    const toggleNodes = [];
    for (const on of [false, true]) {
      const c = master(`Toggle/selected=${on}`, 43, 26, on ? p.colors.green : '#d8dad4', 14); c.name = `Selected=${on ? 'On' : 'Off'}`; c.layoutMode = 'NONE'; const knob = figma.createEllipse(); knob.resize(20, 20); knob.x = on ? 19 : 3; knob.y = 3; knob.fills = [paint('#fffdf9')]; c.appendChild(knob); toggleNodes.push(c);
    }
    const toggleSet = figma.combineAsVariants(toggleNodes, library); toggleSet.name = 'Toggle';
    toggleSet.layoutMode = 'HORIZONTAL'; toggleSet.itemSpacing = 16; toggleSet.paddingTop = 16; toggleSet.paddingBottom = 16; toggleSet.paddingLeft = 16; toggleSet.paddingRight = 16; toggleSet.primaryAxisSizingMode = 'AUTO'; toggleSet.counterAxisSizingMode = 'AUTO';
    await toggleNodes[0].setReactionsAsync([reaction(toggleNodes[1].id, 'CHANGE_TO')]); await toggleNodes[1].setReactionsAsync([reaction(toggleNodes[0].id, 'CHANGE_TO')]);
    const radioNodes = [];
    for (const on of [false, true]) { const c = master(`Radio/selected=${on}`, 24, 24, on ? p.colors.green : null, 12); c.name = `Selected=${on ? 'On' : 'Off'}`; c.strokes = [paint(on ? p.colors.green : '#999c97')]; c.strokeWeight = 1; if (on) { const v = figma.createNodeFromSvg(p.icons.Check.replaceAll('#123f2c', '#ffffff')); v.resize(18, 18); c.appendChild(v); } radioNodes.push(c); }
    const radioSet = figma.combineAsVariants(radioNodes, library); radioSet.name = 'Radio'; radioSet.layoutMode = 'HORIZONTAL'; radioSet.itemSpacing = 16; radioSet.paddingTop = 16; radioSet.paddingBottom = 16; radioSet.paddingLeft = 16; radioSet.paddingRight = 16; radioSet.primaryAxisSizingMode = 'AUTO'; radioSet.counterAxisSizingMode = 'AUTO';
    for (const [name, hash] of Object.entries(imageHashes)) { const c = master(`Photo/${name}`, 96, 96, null, 14); c.fills = [{ type: 'IMAGE', imageHash: hash, scaleMode: 'FILL' }]; }
    // Figma prototype connections stay on one page. Use editable continuation
    // copies, preserving every original node and its prototype reactions.
    const continuations = {}; const clonedIds = {};
    let ci = 0;
    for (const [name, node] of Object.entries(originalNodes)) {
      const copy = node.clone(); page.appendChild(copy); copy.x = 16500 + (ci++ % 3) * 455; copy.y = Math.floor((ci - 1) / 3) * 932; copy.name = `Original continuation / ${name}`; continuations[name] = copy;
      const from = [node, ...node.findAll(() => true)]; const to = [copy, ...copy.findAll(() => true)];
      from.forEach((n, i) => { if (to[i]) clonedIds[n.id] = to[i].id; });
    }
    for (const copy of Object.values(continuations)) for (const node of [copy, ...copy.findAll(() => true)]) if (node.reactions && node.reactions.length) {
      const reactions = node.reactions.map(r => ({ ...r, actions: (r.actions || []).map(a => a.destinationId && clonedIds[a.destinationId] ? { ...a, destinationId: clonedIds[a.destinationId] } : a) }));
      await node.setReactionsAsync(reactions);
    }
    const frames = {}; const actions = []; const allScenes = [...p.scenes, ...p.stateScenes];
    let consumer = 0, staff = 0, states = 0;
    for (const scene of allScenes) {
      const f = figma.createFrame(); f.name = scene.title; f.resize(393, 852); f.fills = [paint(p.colors.cream)]; f.clipsContent = true; f.overflowDirection = scene.height > 855 ? 'VERTICAL' : 'NONE'; f.setPluginData('route', scene.id); page.appendChild(f);
      const index = scene.baseId ? states++ : scene.role === 'staff' ? staff++ : consumer++;
      f.x = (index % 5) * 455 + (scene.baseId ? 5100 : scene.role === 'staff' ? 2550 : 0); f.y = Math.floor(index / 5) * 932;
      frames[scene.id] = f;
      for (const l of scene.layers) {
        let n;
        if (l.kind === 'text') { n = figma.createText(); n.fontName = l.serif ? l.bold ? fonts.serifBold : fonts.serif : l.bold ? fonts.bold : fonts.regular; n.fontSize = l.size || 16; n.characters = l.text || ''; n.lineHeight = { unit: 'PIXELS', value: l.line || (l.size || 16) * 1.22 }; n.letterSpacing = { unit: 'PIXELS', value: l.serif ? -.65 : -.15 }; n.fills = [paint(l.color || p.colors.ink)]; n.textAlignHorizontal = (l.align || 'left').toUpperCase(); n.textAutoResize = 'HEIGHT'; n.resize(l.w, Math.max(l.h, 1));
        } else if (l.kind === 'photo') { n = masters[`Photo/${l.asset}`].createInstance(); n.resize(l.w, l.h); n.cornerRadius = l.radius || 0;
        } else if (l.kind === 'icon') { n = masters[`Icon/${l.icon}`].createInstance(); n.rescale(l.w / 24); if (Math.abs(n.height - l.h) > .01) n.resize(l.w, l.h); recolor(n, l.color || p.colors.green);
        } else if (l.kind === 'toggle' || l.kind === 'radio') { n = (l.kind === 'toggle' ? toggleNodes : radioNodes)[l.selected ? 1 : 0].createInstance(); n.resize(l.w, l.h);
        } else if (l.kind === 'button' && l.color === 'transparent') { n = figma.createFrame(); n.resize(l.w, l.h); n.fills = []; n.clipsContent = false;
        } else { const key = l.kind === 'input' ? 'Input' : l.kind === 'surface' ? 'Surface' : l.fill === p.colors.green ? 'Button/Primary' : l.fill === 'transparent' ? 'Button/Text' : 'Button/Secondary'; n = masters[key].createInstance(); n.resize(l.w, l.h); n.cornerRadius = l.radius || 0; n.fills = l.fill && l.fill !== 'transparent' ? [paint(l.fill)] : []; const labelKey = masters[key].getPluginData('labelKey'); if (labelKey) n.setProperties({ [labelKey]: l.secure && l.value ? '••••••••' : l.kind === 'input' ? l.value || l.placeholder || '' : l.text || '' }); const t = n.findOne(node => node.type === 'TEXT'); if (t) { t.fontName = l.bold ? fonts.bold : fonts.regular; t.fontSize = l.size || 16; t.fills = [paint(l.color || (l.kind === 'input' ? p.colors.muted : p.colors.ink))]; t.textAlignHorizontal = l.kind === 'input' ? 'LEFT' : 'CENTER'; } if (l.icon && l.kind === 'button' || l.secure) { n.setProperties({ [masters[key].getPluginData('iconKey')]: masters[`Icon/${l.icon || 'Eye'}`].id, [masters[key].getPluginData('showIconKey')]: true, [masters[key].getPluginData('showLabelKey')]: l.kind === 'input' }); const slot = n.findOne(node => node.type === 'INSTANCE' && node.name === 'Icon slot'); if (slot) recolor(slot, l.secure ? p.colors.muted : l.color || p.colors.green); } }
        if (l.kind === 'input') { n.paddingLeft = l.leadingIcon ? 52 : 16; n.strokes = l.strokeWidth === 0 ? [] : [paint(p.colors.border)]; n.strokeWeight = l.strokeWidth ?? .7; const label = n.findOne(t => t.type === 'TEXT'); if (label) label.layoutSizingHorizontal = 'FILL'; }
        if (l.kind === 'surface') { n.strokes = l.stroke || l.fill === p.colors.card ? [paint(l.stroke || p.colors.border)] : []; n.strokeWeight = l.strokeWidth ?? .6; }
        n.name = l.kind === 'text' ? (l.text || '').replaceAll('\n', ' ').slice(0, 70) : `${l.kind}/${l.text || l.icon || l.asset || 'surface'}`; f.appendChild(n); n.x = l.x; n.y = l.y;
        n.setPluginData('sceneLayer', l.id || String(scene.layers.indexOf(l))); n.setPluginData('layerKind', l.kind);
        if (l.disabled) n.opacity = .62;
        if (l.action && !l.disabled && l.kind !== 'toggle') actions.push({ node: n, scene: scene.baseId || scene.id, stateId: scene.id, action: l.action });
        if (l.kind === 'input') actions.push({ node: n, scene: scene.baseId || scene.id, stateId: scene.id, action: `fill:${scene.baseId || scene.id}` });
      }
    }
    const dialogFrames = {}; let di = 0;
    async function dialog(key, title, description, choices = []) {
      if (dialogFrames[key]) return dialogFrames[key];
      const f = figma.createFrame(); f.name = `Overlay / ${title}`; f.resize(353, 220 + choices.length * 64); f.x = 10500 + (di % 4) * 405; f.y = Math.floor(di++ / 4) * 550; f.cornerRadius = 22; f.fills = [paint(p.colors.card)]; f.layoutMode = 'VERTICAL'; f.paddingTop = 24; f.paddingBottom = 24; f.paddingLeft = 22; f.paddingRight = 22; f.itemSpacing = 16; f.primaryAxisSizingMode = 'AUTO'; f.counterAxisSizingMode = 'FIXED'; page.appendChild(f);
      for (const [value, size, font] of [[title, 22, fonts.bold], [description, 14, fonts.regular]]) { const t = figma.createText(); t.fontName = font; t.fontSize = size; t.characters = value; t.textAutoResize = 'HEIGHT'; t.resize(309, 24); t.lineHeight = { unit: 'PIXELS', value: size * 1.4 }; t.fills = [paint(p.colors.ink)]; f.appendChild(t); t.layoutSizingHorizontal = 'FILL'; }
      for (const [label, target] of [...choices, ['Close', null]]) { const n = masters[target ? 'Button/Primary' : 'Button/Text'].createInstance(); n.resize(309, 48); n.setProperties({ [masters[target ? 'Button/Primary' : 'Button/Text'].getPluginData('labelKey')]: label }); f.appendChild(n); n.layoutSizingHorizontal = 'FILL'; await n.setReactionsAsync([target && frames[target] ? reaction(frames[target].id) : { trigger: { type: 'ON_CLICK' }, actions: [{ type: 'CLOSE' }] }]); }
      dialogFrames[key] = f; return f;
    }
    for (const item of actions) {
      const { node, scene, action } = item; let reactions;
      if (action === 'back') reactions = [{ trigger: { type: 'ON_CLICK' }, actions: [{ type: 'BACK' }] }];
      else {
        let route = action.startsWith('go:') ? action.slice(3) : action.startsWith('fill:') ? action.slice(5) + '__filled' : p.selectionTargets[`${scene}|${action}`] || p.direct[action];
        const selectedFood = item.stateId.split('__food__')[1];
        if (selectedFood && ['nutrition-details', 'portion-confirmation'].includes(route)) route += `__food__${selectedFood}`;
        const target = frames[route] || continuations[route];
        // Selected chips already display their state. Figma rejects navigation
        // from a frame to that same frame, so those controls need no reaction.
        if (target) reactions = target.id === frames[item.stateId].id ? [] : [reaction(target.id)];
        else { let spec = p.dialogs[action] || [node.name.replace(/^[^/]*\//, ''), 'Frontend demo detail. This action does not call a backend, change the original six screens or import real provider data.', []]; if (selectedFood && ['save-meal', 'draft-meal'].includes(action)) spec = [spec[0], `${selectedFood} · Confirmed sample portion. ${action === 'draft-meal' ? 'Drafts are not consumed.' : 'Values are estimates.'}`, spec[2]]; const f = await dialog(action + (selectedFood ? `/${selectedFood}` : ''), ...spec); reactions = [reaction(f.id, 'OVERLAY')]; }
      }
      await node.setReactionsAsync(reactions);
    }
    page.flowStartingPoints = [{ nodeId: frames['flow-directory'].id, name: 'NutriSole · Consumer flows' }, { nodeId: frames['sign-in'].id, name: 'Account journey' }, { nodeId: frames['catalog-queue'].id, name: 'Catalog curator' }, { nodeId: frames['model-release'].id, name: 'Model administrator' }, { nodeId: frames['operations-audit'].id, name: 'Operations administrator' }, { nodeId: frames['report-triage'].id, name: 'Support curator' }];
    const unchanged = {};
    for (const [name, node] of Object.entries(originalNodes)) { unchanged[name] = originals[name] === snapshot(node); if (!unchanged[name]) throw new Error(`Preservation check failed: ${name}`); }
    const descendants = activeDescendants(page); const stats = { type: 'complete', pageId: page.id, primaryFrames: p.scenes.length, stateFrames: p.stateScenes.length, referenceContinuations: Object.keys(continuations).length, overlayFrames: Object.keys(dialogFrames).length, textNodes: descendants.filter(n => n.type === 'TEXT').length, instances: descendants.filter(n => n.type === 'INSTANCE').length, prototypeLinks: descendants.filter(n => n.reactions && n.reactions.length).length, originalScreensUnchanged: unchanged, fontFamilies: Object.values(fonts).map(f => f.family), wholeScreenImages: 0, frames: p.scenes.map(s => ({ route: s.id, title: s.title, id: frames[s.id].id })), recoveryArchivePreserved: !!existing };
    page.setPluginData('status', 'complete'); page.setPluginData('validation', JSON.stringify(stats)); figma.currentPage.selection = [frames['flow-directory']]; figma.viewport.scrollAndZoomIntoView([frames['flow-directory']]); figma.ui.postMessage(stats); figma.notify('NutriSole expanded flows created as editable layers.');
  } catch (error) { if (page) page.setPluginData('status', 'failed'); figma.ui.postMessage({ type: 'error', message: String(error), partialPageId: page && page.id, originalsWereNotMutated: true }); }
  finally { running = false; }
};
function rgb(hex) { if (hex === 'transparent') return { r: 0, g: 0, b: 0 }; if (/^#[0-9a-f]{3}$/i.test(hex)) hex = '#' + [...hex.slice(1)].map(c => c + c).join(''); if (!/^#[0-9a-f]{6}$/i.test(hex)) throw new Error(`Invalid colour: ${hex}`); return { r: parseInt(hex.slice(1, 3), 16) / 255, g: parseInt(hex.slice(3, 5), 16) / 255, b: parseInt(hex.slice(5, 7), 16) / 255 }; }
function activeDescendants(page) { return page.children.filter(n => n.getPluginData('recoveryArchive') !== 'v1').flatMap(n => [n, ...n.findAll(() => true)]); }
async function inspectPage() {
  const page = figma.root.children.find(n => n.getPluginData('nutrisole-expansion') === 'v1'); if (!page) { figma.ui.postMessage({ type: 'inspection', message: 'No expansion page found.' }); return; }
  await figma.setCurrentPageAsync(page); const nodes = activeDescendants(page); const originalSnapshots = JSON.parse(readChunks(page, 'originalSnapshots') || '{}'); const unchanged = {};
  for (const [name, value] of Object.entries(originalSnapshots)) { const id = JSON.parse(value).id; const original = await figma.getNodeByIdAsync(id); unchanged[name] = !!original && snapshot(original) === value; }
  const links = []; const brokenLinks = [];
  for (const node of nodes) for (const r of node.reactions || []) for (const a of r.actions || []) if (a.type === 'NODE') { const destination = await figma.getNodeByIdAsync(a.destinationId); links.push({ from: node.id, to: a.destinationId, navigation: a.navigation }); if (!destination) brokenLinks.push(node.id); }
  const stats = JSON.parse(page.getPluginData('validation') || '{}'); const result = { ...stats, type: 'inspection', status: page.getPluginData('status'), originalScreensUnchanged: unchanged, brokenLinks, navigationLinks: links.length, nativeTextNodes: nodes.filter(n => n.type === 'TEXT').length, nativeInstances: nodes.filter(n => n.type === 'INSTANCE').length, flowStartingPoints: page.flowStartingPoints };
  figma.ui.postMessage(result);
}
async function exportQA() {
  running = true;
  try {
    const page = figma.root.children.find(n => n.getPluginData('nutrisole-expansion') === 'v1' && n.getPluginData('status') === 'complete'); if (!page) throw new Error('Complete the import before exporting QA.');
    await figma.setCurrentPageAsync(page); const stats = JSON.parse(page.getPluginData('validation')); const files = [];
    for (let i = 0; i < stats.frames.length; i++) { const frame = await figma.getNodeByIdAsync(stats.frames[i].id); if (!frame || frame.type !== 'FRAME') throw new Error('Missing QA frame.'); const bytes = await frame.exportAsync({ format: 'PNG', constraint: { type: 'SCALE', value: 1 } }); files.push({ name: stats.frames[i].route + '.png', bytes: Array.from(bytes) }); figma.ui.postMessage({ type: 'progress', message: `Exported ${i + 1}/${stats.frames.length} native frames` }); }
    figma.ui.postMessage({ type: 'qa-files', files, report: stats });
  } catch (error) { figma.ui.postMessage({ type: 'error', message: String(error) }); } finally { running = false; }
}
async function refineIcons(payload) {
  running = true;
  try {
    const page = figma.root.children.find(n => n.getPluginData('nutrisole-expansion') === 'v1' && n.getPluginData('status') === 'complete'); if (!page || !payload || payload.version !== 1) throw new Error('A completed expansion is required.');
    await figma.setCurrentPageAsync(page); let count = 0;
    for (const scene of [...payload.scenes, ...payload.stateScenes]) {
      const frame = page.children.find(n => n.getPluginData('route') === scene.id); if (!frame || frame.type !== 'FRAME') throw new Error(`Missing frame: ${scene.id}`);
      for (let i = 0; i < scene.layers.length; i++) { const l = scene.layers[i]; if (l.kind !== 'icon') continue; const node = frame.children.find(n => n.getPluginData('sceneLayer') === (l.id || String(i))); if (!node || node.type !== 'INSTANCE') throw new Error('Missing native icon instance.'); if (node.getPluginData('iconScale') !== 'v2') { node.resize(24, 24); node.rescale(l.w / 24); if (Math.abs(node.height - l.h) > .01) node.resize(l.w, l.h); node.x = l.x; node.y = l.y; node.setPluginData('iconScale', 'v2'); count++; } }
    }
    const stats = JSON.parse(page.getPluginData('validation')); stats.iconScalingRefined = true; page.setPluginData('validation', JSON.stringify(stats)); figma.ui.postMessage({ type: 'refined', refinedIcons: count, pageId: page.id });
  } catch (error) { figma.ui.postMessage({ type: 'error', message: String(error) }); } finally { running = false; }
}
function reaction(destinationId, navigation = 'NAVIGATE') { return { trigger: { type: 'ON_CLICK' }, actions: [{ type: 'NODE', destinationId, navigation, transition: { type: 'DISSOLVE', duration: .15, easing: { type: 'EASE_OUT' } }, resetScrollPosition: true }] }; }
function recolor(node, hex) { for (const child of node.findAll(() => true)) { if (Array.isArray(child.strokes) && child.strokes.length) child.strokes = child.strokes.map(p => p.type === 'SOLID' ? { ...p, color: rgb(hex) } : p); if (Array.isArray(child.fills)) child.fills = child.fills.map(p => p.type === 'SOLID' ? { ...p, color: rgb(hex) } : p); } }
function snapshot(node) { return JSON.stringify({ id: node.id, x: node.x, y: node.y, width: node.width, height: node.height, name: node.name, reactions: node.reactions, children: node.findAll(() => true).map(n => ({ id: n.id, type: n.type, name: n.name, x: n.x, y: n.y, width: n.width, height: n.height, characters: n.characters, fills: n.fills, reactions: n.reactions })) }); }
function decode(input) { const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'; let bits = 0, value = 0; const bytes = []; for (const char of input) { if (char === '=') break; const index = chars.indexOf(char); if (index < 0) continue; value = (value << 6) | index; bits += 6; if (bits >= 8) { bits -= 8; bytes.push((value >> bits) & 255); } } return new Uint8Array(bytes); }
function storeChunks(node, key, value) { const count = Math.ceil(value.length / 16000); node.setPluginData(key + '/count', String(count)); for (let i = 0; i < count; i++) node.setPluginData(key + '/' + i, value.slice(i * 16000, (i + 1) * 16000)); }
function readChunks(node, key) { const count = Number(node.getPluginData(key + '/count')); return count ? Array.from({ length: count }, (_, i) => node.getPluginData(key + '/' + i)).join('') : node.getPluginData(key); }
