import { colors, type Scene } from './model';
export function headerHeight(scene: Scene) { return scene.id === 'sign-in' ? 54 : scene.id === 'plan-generation' ? 88 : 100; }
export function fixedFooterStart(scene: Scene): number | null {
  if (scene.height > 855) return null;
  const candidates = scene.layers.filter(l => (l.kind === 'button' && l.fill === colors.green || scene.id === 'assistant' && l.kind === 'input') && l.y >= 700);
  return candidates.length ? Math.min(...candidates.map(l => l.y)) : null;
}
