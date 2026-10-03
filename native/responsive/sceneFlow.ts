import type { Layer, Scene } from '../../src/nutrisole/extensions/model.ts';
export type FlowNode = { index: number; layer: Layer; children: FlowNode[]; actionLayer?: Layer };
export type FlowScene = { header: FlowNode[]; body: FlowNode[]; footer: FlowNode[] };
export function fixedColumnWidth(nodes: FlowNode[]) {
  const sourceWidth = Math.max(...nodes.map(n => n.layer.x + n.layer.w)) - Math.min(...nodes.map(n => n.layer.x));
  const controlWidth = Math.max(...nodes.map(n => n.layer.kind === 'toggle' ? 43 : n.layer.kind === 'icon' && n.layer.action ? 36 : 0));
  return Math.min(115, Math.max(sourceWidth, controlWidth));
}
export function compileScene(scene: Scene): FlowScene {
  const nodes: FlowNode[] = scene.layers.map((layer, index) => ({ layer, index, children: [] }));
  const containers = nodes.filter(n => n.layer.kind === 'surface' && n.layer.h > 4 || n.layer.kind === 'button' && n.layer.fill !== 'transparent' || n.layer.kind === 'input' && n.layer.leadingIcon);
  const roots: FlowNode[] = [];
  const overlays = nodes.filter(n => n.layer.kind === 'button' && n.layer.color === 'transparent');
  for (const node of nodes) {
    if (overlays.includes(node)) continue;
    const parent = containers.filter(c => c !== node && area(c.layer) > area(node.layer) + 4 && contains(c.layer, node.layer))
      .sort((a, b) => area(a.layer) - area(b.layer))[0];
    if (parent) parent.children.push(node); else roots.push(node);
  }
  for (const node of overlays) {
    const target = containers.filter(c => c.layer.kind === 'surface' && Math.abs(c.layer.y - node.layer.y) < 5 && Math.abs(c.layer.x - node.layer.x) < 6 && Math.abs(c.layer.h - node.layer.h) < 8)
      .sort((a, b) => area(a.layer) - area(b.layer))[0];
    if (target && !target.actionLayer) target.actionLayer = node.layer;
    else roots.push({ ...node, layer: { ...node.layer, color: '#123f2c' } });
  }
  // Keep each overlapping brand/header band together; never split its mark
  // from its wordmark at an arbitrary coordinate cutoff.
  const header = scene.id === 'sign-in' ? [] : flowBands(roots).filter(b => b.y < 88).flatMap(b => b.columns.flat());
  const body = roots.filter(n => !header.includes(n));
  const rawY = (l: Layer) => l.y < 100 ? l.y : 100 + (l.y - 100) / .95;
  const footerY = scene.id === 'assistant' ? Math.min(...body.filter(n => n.layer.field === 'assistantQuestion').map(n => n.layer.y))
    : scene.height <= 855 ? Math.min(...body.filter(n => n.layer.kind === 'button' && n.layer.fill === '#123f2c' && n.layer.w > 300 && rawY(n.layer) >= 730).map(n => n.layer.y)) : Infinity;
  return { header, body: body.filter(n => n.layer.y < footerY), footer: body.filter(n => n.layer.y >= footerY) };
}
function area(l: Layer) { return l.w * l.h; }
function contains(a: Layer, b: Layer) {
  return b.x >= a.x - 4 && b.x + b.w <= a.x + a.w + 8 && b.y >= a.y - 3 && (b.kind === 'text' ? b.y < a.y + a.h - 3 : b.y + b.h <= a.y + a.h + 14);
}
export type Band = { y: number; bottom: number; columns: FlowNode[][]; gap: number };
/** Source rectangles identify relationships; the renderer uses flowing rows/columns. */
export function flowBands(nodes: FlowNode[], origin = 0): Band[] {
  const groups: FlowNode[][] = [];
  for (const node of [...nodes].sort((a, b) => a.layer.y - b.layer.y || a.index - b.index)) {
    const last = groups.at(-1);
    const bottom = last ? Math.max(...last.map(n => n.layer.y + n.layer.h)) : -Infinity;
    if (last && node.layer.y < bottom - 3) last.push(node); else groups.push([node]);
  }
  let previousBottom = origin;
  return groups.map(group => {
    const y = Math.min(...group.map(n => n.layer.y));
    const bottom = Math.max(...group.map(n => n.layer.y + n.layer.h));
    const columns: FlowNode[][] = [];
    for (const node of [...group].sort((a, b) => a.layer.x - b.layer.x || a.layer.y - b.layer.y)) {
      const column = columns.at(-1);
      const right = column ? Math.max(...column.map(n => n.layer.x + n.layer.w)) : -Infinity;
      if (column && node.layer.x < right - 12) column.push(node); else columns.push([node]);
    }
    for (const column of columns) column.sort((a, b) => a.layer.y - b.layer.y || a.index - b.index);
    const gap = Math.max(0, Math.min(40, y - previousBottom));
    previousBottom = bottom;
    return { y, bottom, columns, gap };
  });
}
