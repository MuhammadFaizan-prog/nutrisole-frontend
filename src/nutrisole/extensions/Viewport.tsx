import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { MobileScroll, useScreenPortal, useKeyboardInsets } from '../../mobile';
import { View } from '../primitives';
import { colors, type Layer, type Scene } from './model';
import { fixedFooterStart, headerHeight } from './layout';
export type ViewportProps = { width: number; height: number; scene: Scene; render: (l: Layer, i: number) => ReactNode };
export default function Viewport({ width, height, scene, render }: ViewportProps) {
  const { screenRef } = useScreenPortal(); const [target, setTarget] = useState<HTMLElement | null>(null);
  const { bottomInset } = useKeyboardInsets();
  useEffect(() => setTarget(screenRef.current), [screenRef]);
  const scale = Math.min(width / 393, height / 852);
  const top = headerHeight(scene);
  const footerStart = fixedFooterStart(scene);
  const footerHeight = footerStart === null ? 0 : 818 - footerStart;
  const plane = (nodes: { l: Layer; i: number }[], offset = 0, h = scene.height) => <View style={{ width: 393, height: h, transform: [{ scale }], transformOrigin: 'top left' }}>{nodes.map(({ l, i }) => render({ ...l, y: l.y - offset }, i))}</View>;
  const nodes = scene.layers.map((l, i) => ({ l, i }));
  const view = <div data-testid={`screen-${scene.id}`} onPointerDownCapture={e => { if (e.target instanceof Element && e.target.closest('[role="button"]')) e.preventDefault(); }} style={{ position: 'absolute', inset: 0, zIndex: 3, background: colors.cream, overflow: 'hidden' }}>
    <div style={{ position: 'absolute', left: (width - 393 * scale) / 2, top: top * scale, width: 393 * scale, bottom: 34 + footerHeight * scale }}>
      <MobileScroll className="nutri-scroll">{plane(nodes.filter(({ l }) => l.y >= top && (footerStart === null || l.y < footerStart)), top, Math.max(scene.height - top, (height - top * scale) / scale))}</MobileScroll>
    </div>
    <div style={{ position: 'absolute', left: (width - 393 * scale) / 2, top: 0, width: 393 * scale, height: top * scale, background: colors.cream }}>{plane(nodes.filter(({ l }) => l.y < top), 0, top)}</div>
    {footerStart !== null && <div onPointerDownCapture={e => { if (e.target instanceof Element && e.target.closest('[role="button"]')) e.preventDefault(); }} style={{ position: 'absolute', left: (width - 393 * scale) / 2, bottom: bottomInset, width: 393 * scale, height: footerHeight * scale, background: colors.cream }}>{plane(nodes.filter(({ l }) => l.y >= footerStart), footerStart, footerHeight)}</div>}
  </div>;
  return target ? createPortal(view, target) : null;
}
